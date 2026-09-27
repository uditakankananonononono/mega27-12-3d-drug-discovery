"""Cross-structure rank transfer 7KX5 -> 8V8E, per
docs/PREREG_TRANSFER_8V8E_RANK_20260928.md (locked before any 8V8E campaign
dock). Resumable: one cache file per compound in results/transfer8v8e/;
stops at the wall-clock budget; re-invoke until the final JSON is written.

Result transport is crash-safe: the dock worker writes its result to
results/transfer8v8e/_partials/<CHEMBL_ID>.json before signalling the
parent, and the parent records the worker pid in _inflight.json. If the
invocation's wall-clock wrapper kills the parent mid-dock, the next
invocation adopts the orphaned worker's partial (or enforces the
preregistered 300 s timeout on it). Docking parameters are identical to
the 7KX5 campaign worker either way.
"""
import json, os, pathlib, signal, sys, threading, time
import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from drugdisc.prep import smiles_to_pdbqt
from drugdisc.dock import dock_ligand, dock_ligand_with_timeout

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
SRC = ROOT / "results/bigscreen"
OUT = ROOT / "results/transfer8v8e"
PARTIALS = OUT / "_partials"
INFLIGHT = OUT / "_inflight.json"
BUDGET = float(os.environ.get("T8V8E_BUDGET", "100"))
DOCK_TIMEOUT_S = 300
FINAL = ROOT / "results/transfer_8v8e_rank.json"


def worker_file(receptor, pdbqt, center, size, name, queue):
    """Same dock call as the 7KX5 campaign worker; also drops the result
    to a partial file first so an orphaned worker is adoptable."""
    res, _ = dock_ligand(receptor, pdbqt, center, size, ligand_name=name,
                         exhaustiveness=8, n_poses=5, cpu=2)
    PARTIALS.mkdir(exist_ok=True)
    (PARTIALS / f"{name}.json").write_text(json.dumps(
        {"best": res.best_affinity, "all": res.all_affinities}))
    queue.put((res.best_affinity, res.all_affinities))


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def main():
    OUT.mkdir(exist_ok=True)
    PARTIALS.mkdir(exist_ok=True)
    records = {json.loads(f.read_text())["chembl_id"]: json.loads(f.read_text())
               for f in sorted(SRC.glob("*.json"))}
    assert len(records) == 52, f"expected 52 committed campaign records, found {len(records)}"
    box = json.loads((RAW / "box_8v8e.json").read_text())
    t0 = time.time()

    def cache_for(cid, payload):
        rec = records[cid]
        out = {"chembl_id": cid, "smiles": rec["smiles"],
               "affinity_8v8e": payload["best"], "all_affinities_8v8e": payload["all"],
               "affinity_7kx5": rec.get("affinity"), "label": rec.get("label"),
               "best_potency_nM": rec.get("best_potency_nM")}
        (OUT / f"{cid}.json").write_text(json.dumps(out, indent=1))
        print(f"{cid}: {payload['best']} (adopted partial) [{len(list(OUT.glob('*.json')))}/52]", flush=True)

    def skip_for(cid, reason):
        rec = records[cid]
        out = {"chembl_id": cid, "smiles": rec["smiles"], "skipped": reason,
               "affinity_7kx5": rec.get("affinity"), "label": rec.get("label"),
               "best_potency_nM": rec.get("best_potency_nM")}
        (OUT / f"{cid}.json").write_text(json.dumps(out, indent=1))
        print(f"{cid}: {reason} [{len(list(OUT.glob('*.json')))}/52]", flush=True)

    def collect_partials():
        for p in list(PARTIALS.glob("*.json")):
            cid = p.stem
            if cid not in records:
                p.unlink(); continue
            if not (OUT / f"{cid}.json").exists():
                cache_for(cid, json.loads(p.read_text()))
            p.unlink()
            if INFLIGHT.exists() and json.loads(INFLIGHT.read_text()).get("chembl_id") == cid:
                INFLIGHT.unlink()

    collect_partials()

    # Adopt or enforce the timeout on a worker orphaned by a killed invocation.
    if INFLIGHT.exists():
        inf = json.loads(INFLIGHT.read_text())
        cid, pid, started = inf["chembl_id"], inf["pid"], inf["started"]
        if (OUT / f"{cid}.json").exists():
            INFLIGHT.unlink()
        elif not pid_alive(pid):
            skip_for(cid, "dock_worker_crashed")
            INFLIGHT.unlink()
        elif time.time() - started >= DOCK_TIMEOUT_S:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            skip_for(cid, f"dock_timeout_{DOCK_TIMEOUT_S}s")
            INFLIGHT.unlink()
        else:
            while time.time() - t0 <= BUDGET and pid_alive(pid) and not (PARTIALS / f"{cid}.json").exists():
                time.sleep(5)
            collect_partials()
            if not (OUT / f"{cid}.json").exists():
                if not pid_alive(pid):
                    skip_for(cid, "dock_worker_crashed")
                    INFLIGHT.unlink()
                elif time.time() - started >= DOCK_TIMEOUT_S:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    skip_for(cid, f"dock_timeout_{DOCK_TIMEOUT_S}s")
                    INFLIGHT.unlink()
                else:
                    print(f"{cid}: still docking (pid {pid}); invocation budget spent", flush=True)
                    return

    for cid, rec in records.items():
        cache = OUT / f"{cid}.json"
        if cache.exists() or time.time() - t0 > BUDGET:
            continue
        if "affinity" not in rec:
            skip_for(cid, "no_7kx5_affinity_in_committed_record")
            continue
        pdbqt = RAW / f"lig_{cid}.pdbqt"
        try:
            if not pdbqt.exists():
                smiles_to_pdbqt(rec["smiles"], str(pdbqt))
            pids, holder = [], {}
            def run():
                try:
                    holder["res"] = dock_ligand_with_timeout(
                        str(RAW / "8V8E_A_receptor.pdbqt"), str(pdbqt),
                        box["center"], box["size"], ligand_name=cid,
                        timeout_s=DOCK_TIMEOUT_S, worker=worker_file,
                        pid_sink=pids)
                except Exception as exc:
                    holder["err"] = exc
            th = threading.Thread(target=run, daemon=True)
            th.start()
            while not pids and th.is_alive():
                time.sleep(0.2)
            if pids:
                INFLIGHT.write_text(json.dumps(
                    {"chembl_id": cid, "pid": pids[0], "started": time.time()}))
            th.join()
            INFLIGHT.unlink(missing_ok=True)
            if "err" in holder:
                raise holder["err"]
            best, all_aff = holder["res"]
            partial = PARTIALS / f"{cid}.json"
            if partial.exists():
                partial.unlink()
            out = {"chembl_id": cid, "smiles": rec["smiles"],
                   "affinity_8v8e": best, "all_affinities_8v8e": all_aff,
                   "affinity_7kx5": rec["affinity"], "label": rec["label"],
                   "best_potency_nM": rec["best_potency_nM"]}
        except TimeoutError:
            out = {"chembl_id": cid, "smiles": rec["smiles"],
                   "skipped": f"dock_timeout_{DOCK_TIMEOUT_S}s",
                   "affinity_7kx5": rec["affinity"], "label": rec["label"],
                   "best_potency_nM": rec["best_potency_nM"]}
        except RuntimeError as exc:
            reason = "dock_worker_crashed" if "died without result" in str(exc) \
                else f"error_{type(exc).__name__}"
            out = {"chembl_id": cid, "smiles": rec["smiles"], "skipped": reason,
                   "affinity_7kx5": rec["affinity"], "label": rec["label"],
                   "best_potency_nM": rec["best_potency_nM"]}
        except Exception as exc:
            out = {"chembl_id": cid, "smiles": rec["smiles"],
                   "skipped": f"error_{type(exc).__name__}",
                   "affinity_7kx5": rec["affinity"], "label": rec["label"],
                   "best_potency_nM": rec["best_potency_nM"]}
        cache.write_text(json.dumps(out, indent=1))
        print(f"{cid}: {out.get('affinity_8v8e', out.get('skipped'))} [{len(list(OUT.glob('*.json')))}/52]", flush=True)

    caches = [json.loads(p.read_text()) for p in OUT.glob("*.json")]
    if len(caches) != 52:
        print(f"checkpointed; {52 - len(caches)} compounds remain")
        return
    docked = [c for c in caches if "affinity_8v8e" in c]
    skipped = [c for c in caches if "skipped" in c]
    final = {"prereg": "docs/PREREG_TRANSFER_8V8E_RANK_20260928.md",
             "n_committed_records": 52, "n_docked_both": len(docked),
             "n_skipped": len(skipped),
             "skipped": [{k: c[k] for k in ("chembl_id", "skipped")} for c in skipped]}
    if len(docked) < 2:
        final["status"] = "INSUFFICIENT_DOCKED_no_statistics"
        FINAL.write_text(json.dumps(final, indent=1))
        print("FINAL:", json.dumps(final, indent=1))
        return
    x = np.array([c["affinity_7kx5"] for c in docked])
    y = np.array([c["affinity_8v8e"] for c in docked])
    rho, p = spearmanr(x, y)
    top_7kx5 = {c["chembl_id"] for c in sorted(docked, key=lambda c: c["affinity_7kx5"])[:10]}
    top_8v8e = {c["chembl_id"] for c in sorted(docked, key=lambda c: c["affinity_8v8e"])[:10]}
    labeled = [c for c in docked if c.get("label") in ("active", "inactive")]
    from sklearn.metrics import roc_auc_score
    auroc_8v8e = float(roc_auc_score([c["label"] == "active" for c in labeled],
                                     [-c["affinity_8v8e"] for c in labeled]))
    final.update({"spearman_rho": float(rho), "spearman_p": float(p),
                  "gate_rank_transfer": "PASS_rho>=0.50" if rho >= 0.50 else "FAIL_structure_specific",
                  "top10_retention": len(top_7kx5 & top_8v8e),
                  "auroc_8v8e_raw_vina_descriptive": auroc_8v8e,
                  "auroc_7kx5_raw_vina_reference": 0.540})
    FINAL.write_text(json.dumps(final, indent=1))
    print("FINAL:", json.dumps(final, indent=1))


if __name__ == "__main__":
    main()
