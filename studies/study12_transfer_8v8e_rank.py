"""Cross-structure rank transfer 7KX5 -> 8V8E, per
docs/PREREG_TRANSFER_8V8E_RANK_20260928.md (locked before any 8V8E campaign
dock). Resumable: one cache file per compound in results/transfer8v8e/;
stops at the wall-clock budget; re-invoke until the final JSON is written.
"""
import json, os, pathlib, sys, time
import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from drugdisc.prep import smiles_to_pdbqt
from drugdisc.dock import dock_ligand_with_timeout

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
SRC = ROOT / "results/bigscreen"
OUT = ROOT / "results/transfer8v8e"
BUDGET = float(os.environ.get("T8V8E_BUDGET", "90"))
FINAL = ROOT / "results/transfer_8v8e_rank.json"


def main():
    OUT.mkdir(exist_ok=True)
    records = sorted(SRC.glob("*.json"))
    assert len(records) == 52, f"expected 52 committed campaign records, found {len(records)}"
    box = json.loads((RAW / "box_8v8e.json").read_text())
    t0 = time.time()

    for f in records:
        rec = json.loads(f.read_text())
        cid = rec["chembl_id"]
        cache = OUT / f"{cid}.json"
        if cache.exists() or time.time() - t0 > BUDGET:
            continue
        smi = rec["smiles"]
        if "affinity" not in rec:
            cache.write_text(json.dumps(
                {"chembl_id": cid, "smiles": smi,
                 "skipped": "no_7kx5_affinity_in_committed_record",
                 "label": rec.get("label"),
                 "best_potency_nM": rec.get("best_potency_nM")}, indent=1))
            print(f"{cid}: excluded, no 7KX5 affinity", flush=True)
            continue
        pdbqt = RAW / f"lig_{cid}.pdbqt"
        try:
            if not pdbqt.exists():
                smiles_to_pdbqt(smi, str(pdbqt))
            best, all_aff = dock_ligand_with_timeout(
                str(RAW / "8V8E_A_receptor.pdbqt"), str(pdbqt),
                box["center"], box["size"], ligand_name=cid, timeout_s=300)
            out = {"chembl_id": cid, "smiles": smi, "affinity_8v8e": best,
                   "all_affinities_8v8e": all_aff,
                   "affinity_7kx5": rec["affinity"], "label": rec["label"],
                   "best_potency_nM": rec["best_potency_nM"]}
        except TimeoutError:
            out = {"chembl_id": cid, "smiles": smi, "skipped": "dock_timeout_300s",
                   "affinity_7kx5": rec["affinity"], "label": rec["label"],
                   "best_potency_nM": rec["best_potency_nM"]}
        except RuntimeError as exc:
            if "died without result" in str(exc):
                out = {"chembl_id": cid, "smiles": smi,
                       "skipped": "dock_worker_crashed",
                       "affinity_7kx5": rec["affinity"], "label": rec["label"],
                       "best_potency_nM": rec["best_potency_nM"]}
            else:
                out = {"chembl_id": cid, "smiles": smi,
                       "skipped": f"error_{type(exc).__name__}",
                       "affinity_7kx5": rec["affinity"], "label": rec["label"],
                       "best_potency_nM": rec["best_potency_nM"]}
        except Exception as exc:
            out = {"chembl_id": cid, "smiles": smi, "skipped": f"error_{type(exc).__name__}",
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
