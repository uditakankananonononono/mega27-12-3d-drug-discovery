"""PRE-REGISTERED ablation + leakage study (judge round 1 adopted gates 2-3;
docs/JUDGE_ROUNDS.md, docs/PREREGISTER.md). Committed BEFORE running
2026-09-26.

Locked design:
- Data, scaffold splits, and statistics identical to
  studies/study12_scaffold_split.py (59 labeled records, Bemis-Murcko
  grouped splits, seeds 0-4, no scaffold crossing).
- Poses: every compound docked into the SAME 7KX5_A receptor/box/protocol
  as study12_analyze.py (exhaustiveness 8, n_poses 1, 120 s timeout),
  cached in results/ablation_poses/. Docking uses no label information.
  Compounds that fail to dock are excluded from pose-dependent arms only
  and are reported by name (declared now: no silent dropping).
- Arms (all learned arms trained on train scaffolds only):
  A raw Vina affinity (no training)
  B descriptor MLP (as scaffold_split; includes Vina-derived ligand
    efficiency feature)
  C leakage-controlled MLP: identical to B but WITHOUT the Vina-derived
    feature (7 RDKit-only descriptors)
  D ligand-only 2D-GNN: PoseGCN over the RDKit bond graph (no pose)
  E pose-graph GCN: PoseGCN over the docked-pose distance graph
  F full model: pose-graph GCN whose pooled embedding is concatenated with
    the 7 RDKit descriptors before the head
  G randomized-pose control: arm E with coordinates replaced by iid normal
    draws (same elements, same atom count; destroys geometry)
  H random-label control: arm D trained on labels permuted with seed 99
    (sanity check; expected AUROC ~0.5)
  I scaffold-matched shuffled-pose falsifier (judge round 2, committed
    BEFORE any ablation outcome): arm E with each compound's pose graph
    replaced by another compound's pose graph, permuted deterministically
    (seed 13) within Bemis-Murcko scaffold groups; singleton scaffolds are
    permuted among themselves. Labels unchanged. If arm E does not beat
    arm I, pose-GCN gains are generic pose statistics, not ligand-specific
    geometry. Pose-availability bias is reported descriptively (MW,
    rotatable bonds, logP, activity rate: pose-available vs all).
- Statistics: AUROC per arm per split; mean +/- bootstrap 95% CI across
  splits (splits overlap; CI is descriptive, declared). Paired DeLong on
  the seed-0 held-out compounds only for the decisive comparisons.
- GATES (locked):
  G-pose: pose-geometry contribution is supported ONLY if arm E beats arm D
    AND arm G on mean AUROC over the SAME pose-available held-out set,
    with seed-0 DeLong p < 0.01 vs arm D. If E does
    not beat D, the chemistry-only reading stands and the pose-geometry
    discovery claim (PREREGISTER G4) is withdrawn; pivot per PREREGISTER.
  G-leak: if arm C mean AUROC falls below arm B mean AUROC by more than
    0.05, the scaffold-split result is reported as substantially
    Vina-leakage-driven and claims are restated accordingly.
  G-sanity: arm H must not exceed AUROC 0.65 on any split; otherwise the
    whole evaluation harness is suspect and all learned-arm results are
    withheld pending debugging.
"""
import json, subprocess, time
from pathlib import Path
import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski
from sklearn.metrics import roc_auc_score
import torch, torch.nn as nn

from studies.study12_scaffold_split import (load_records, scaffolds,
                                            scaffold_split, delong_p)
from drugdisc.gnn_rescorer import PoseGCN, ELEMENTS, EL_IDX, pose_graph
from drugdisc.geometry import parse_pose_pdbqt

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
RES = ROOT / "results"
POSES = RES / "ablation_poses"
TIMEOUT = 120

def _dock_worker(receptor, pdbqt, center, size, name, queue):
    from drugdisc.dock import dock_ligand
    _, pose = dock_ligand(receptor, pdbqt, center, size, ligand_name=name,
                          exhaustiveness=8, n_poses=1, cpu=2)
    queue.put(pose)

def _dock_with_timeout(receptor, pdbqt, center, size, name):
    """Hard wall-clock timeout via a spawned child (Vina cannot be
    interrupted in-process); mirrors drugdisc.dock.dock_ligand_with_timeout
    but returns the pose string."""
    import multiprocessing as mp
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    proc = ctx.Process(target=_dock_worker,
                       args=(receptor, pdbqt, center, size, name, queue))
    proc.start(); proc.join(TIMEOUT)
    if proc.is_alive():
        proc.terminate(); proc.join()
        raise TimeoutError(f"dock>{TIMEOUT}s: {name}")
    if queue.empty():
        raise RuntimeError(f"dock child died: {name}")
    return queue.get()

def dock_poses(records):
    POSES.mkdir(parents=True, exist_ok=True)
    box = json.loads((RAW / "box_7kx5.json").read_text())
    failed = []
    for r in records:
        pf = POSES / f"{r['name']}_pose.pdbqt"
        if pf.exists():
            continue
        pdbqt = RAW / f"lig_{r['name']}.pdbqt"
        if not pdbqt.exists():
            from drugdisc.prep import smiles_to_pdbqt
            smiles_to_pdbqt(r["smiles"], str(pdbqt))
        try:
            pose = _dock_with_timeout(str(RAW / "7KX5_A_receptor.pdbqt"), str(pdbqt),
                                      box["center"], box["size"], r["name"])
            pf.write_text(pose)
        except Exception as e:
            failed.append({"name": r["name"], "error": repr(e)[:200]})
        print(f"docked {r['name']} (failures so far: {len(failed)})", flush=True)
    return failed

def mol_graph(smiles):
    mol = Chem.MolFromSmiles(smiles)
    n = mol.GetNumAtoms()
    x = np.zeros((n, len(ELEMENTS) + 1), dtype=np.float32)
    a = np.zeros((n, n), dtype=np.float32)
    for atom in mol.GetAtoms():
        x[atom.GetIdx(), EL_IDX.get(atom.GetSymbol(), EL_IDX["OTHER"])] = 1.0
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        a[i, j] = a[j, i] = 1.0
    x[:, -1] = a.sum(1) / max(n - 1, 1)
    a += np.eye(n, dtype=np.float32)
    deg = a.sum(1); deg[deg == 0] = 1.0
    dinv = 1.0 / np.sqrt(deg)
    return x, (a * dinv[:, None]) * dinv[None, :]

def rdkit7(smiles):
    mol = Chem.MolFromSmiles(smiles)
    return [Descriptors.MolWt(mol), Lipinski.NumRotatableBonds(mol),
            Lipinski.HeavyAtomCount(mol), Lipinski.NumHDonors(mol),
            Lipinski.NumHAcceptors(mol), Descriptors.TPSA(mol),
            Descriptors.MolLogP(mol)]

class FusionGCN(nn.Module):
    def __init__(self, in_dim, n_desc):
        super().__init__()
        self.gcn = PoseGCN(in_dim)
        self.head = nn.Sequential(nn.Linear(24 + n_desc, 12), nn.ReLU(),
                                  nn.Dropout(0.2), nn.Linear(12, 1))
    def forward(self, x, adj, desc):
        h = x
        for w, b in zip(self.gcn.weights, self.gcn.biases):
            h = torch.relu(adj @ h @ w + b)
        z = torch.cat([h.mean(dim=0), desc])
        return self.head(z).squeeze(-1)

def train_gnn(graphs, descs, ytr, seed, kind, epochs=120):
    torch.manual_seed(seed)
    if kind == "fusion":
        model = FusionGCN(graphs[0][0].shape[1], descs.shape[1])
    else:
        model = PoseGCN(graphs[0][0].shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=5e-3)
    pw = torch.tensor(float((len(ytr) - ytr.sum()) / max(ytr.sum(), 1)))
    lossf = nn.BCEWithLogitsLoss(pos_weight=pw)
    yt = torch.from_numpy(ytr.astype(np.float32))
    model.train()
    for _ in range(epochs):
        tot = 0.0
        for j in range(len(ytr)):
            x, a = graphs[j]
            x, a = torch.from_numpy(x), torch.from_numpy(a)
            pred = model(x, a, torch.from_numpy(descs[j])) if kind == "fusion" else model(x, a)
            loss = lossf(pred, yt[j])
            opt.zero_grad(); loss.backward(); opt.step()
            tot += loss.item()
    model.eval()
    return model

def score_gnn(model, graphs, descs, kind):
    out = np.zeros(len(graphs))
    with torch.no_grad():
        for i, (x, a) in enumerate(graphs):
            x, a = torch.from_numpy(x), torch.from_numpy(a)
            p = model(x, a, torch.from_numpy(descs[i])) if kind == "fusion" else model(x, a)
            out[i] = torch.sigmoid(p).item()
    return out

def train_mlp(Xtr, ytr, seed):
    torch.manual_seed(seed)
    model = nn.Sequential(nn.Linear(Xtr.shape[1], 16), nn.ReLU(), nn.Dropout(0.2),
                          nn.Linear(16, 1))
    opt = torch.optim.Adam(model.parameters(), lr=5e-3)
    pw = torch.tensor(float((len(ytr) - ytr.sum()) / max(ytr.sum(), 1)))
    lossf = nn.BCEWithLogitsLoss(pos_weight=pw)
    xt = torch.from_numpy(Xtr); yt = torch.from_numpy(ytr.astype(np.float32))
    model.train()
    for _ in range(200):
        opt.zero_grad(); loss = lossf(model(xt).squeeze(-1), yt); loss.backward(); opt.step()
    model.eval()
    return model

def main():
    records = load_records()
    y = np.array([1 if r["label"] == "active" else 0 for r in records])
    aff = np.array([r["affinity"] for r in records])
    scaf = scaffolds(records)
    failed = dock_poses(records)
    ok = [i for i, r in enumerate(records)
          if (POSES / f"{r['name']}_pose.pdbqt").exists()]
    print(f"poses: {len(ok)}/{len(records)} docked; failures: {failed}", flush=True)

    graphs_2d = [mol_graph(r["smiles"]) for r in records]
    graphs_pose, graphs_rand = {}, {}
    rng = np.random.default_rng(7)
    for i in ok:
        coords, elements = parse_pose_pdbqt((POSES / f"{records[i]['name']}_pose.pdbqt").read_text())
        x, a = pose_graph(coords, elements)
        graphs_pose[i] = (x, a)
        rc = rng.normal(size=np.asarray(coords).shape)
        graphs_rand[i] = pose_graph(rc, elements)
    # Scaffold-matched shuffled pose assignment (seed 13), pre-outcome.
    scaf_arr = np.array(scaf)
    graphs_shuf = {}
    rngs = np.random.default_rng(13)
    ok_arr = np.array(ok)
    for group in [scaf_arr[ok_arr] == s_ for s_ in np.unique(scaf_arr[ok_arr])]:
        idx = ok_arr[group]
        if len(idx) == 1:
            continue
        perm = rngs.permutation(idx)
        while (perm == idx).any():
            perm = rngs.permutation(idx)
        for a, b in zip(idx, perm):
            graphs_shuf[a] = graphs_pose[b]
    singles = [i for i in ok if i not in graphs_shuf]
    if len(singles) == 1:
        # one leftover: borrow any other ok compound's pose (declared
        # scaffold-match exception) so every pose-available compound keeps
        # an arm-I graph and all arm test sets stay identical.
        others = [i for i in ok if i != singles[0]]
        graphs_shuf[singles[0]] = graphs_pose[int(rngs.choice(others))]
        singles = []
    if len(singles) > 1:
        perm = rngs.permutation(singles)
        while any(a == b for a, b in zip(singles, perm)):
            perm = rngs.permutation(singles)
        for a, b in zip(singles, perm):
            graphs_shuf[a] = graphs_pose[b]
    D7 = np.array([rdkit7(r["smiles"]) for r in records], dtype=np.float32)
    D8 = np.hstack([D7, (aff / D7[:, 2].clip(1)).reshape(-1, 1).astype(np.float32)])

    arms = ["vina", "mlp8", "mlp7", "gnn2d", "gnnpose", "fusion", "gnnrand", "gnnpose_shuf", "gnn2d_randlab"]
    out = {"n": len(records), "pose_failures": failed, "splits": [],
           "seed0_scores": {}}
    for seed in range(5):
        tr, te = scaffold_split(scaf, seed)
        trp = [i for i in tr if i in graphs_pose]; tep = [i for i in te if i in graphs_pose]
        res = {"seed": seed, "n_test": len(te), "n_test_pose": len(tep)}
        res["vina"] = roc_auc_score(y[te], -aff[te])
        for tag, D in (("mlp8", D8), ("mlp7", D7)):
            X = (D - D[tr].mean(0)) / (D[tr].std(0) + 1e-9)
            m = train_mlp(X[tr], y[tr], seed)
            with torch.no_grad():
                s = torch.sigmoid(m(torch.from_numpy(X[te])).squeeze(-1)).numpy()
            res[tag] = roc_auc_score(y[te], s)
            if seed == 0 and tag == "mlp8":
                out["seed0_scores"]["mlp8"] = s.tolist()
        gr_tr = [graphs_2d[i] for i in tr]; gr_te = [graphs_2d[i] for i in te]
        d_mu, d_sd = D7[tr].mean(0), D7[tr].std(0) + 1e-9
        Dn = ((D7 - d_mu) / d_sd).astype(np.float32)
        m = train_gnn(gr_tr, Dn[tr], y[tr], seed, "plain")
        score_2d = score_gnn(m, gr_te, Dn[te], "plain")
        res["gnn2d"] = roc_auc_score(y[te], score_2d)
        res["gnn2d_pose_subset"] = roc_auc_score(y[tep], score_2d[np.isin(te, tep)])
        if seed == 0:
            out["seed0_scores"]["gnn2d_pose_subset"] = score_2d[np.isin(te, tep)].tolist()
        rngl = np.random.default_rng(99)
        m = train_gnn(gr_tr, Dn[tr], y[tr][rngl.permutation(len(tr))], seed, "plain")
        res["gnn2d_randlab"] = roc_auc_score(y[te], score_gnn(m, gr_te, Dn[te], "plain"))
        for tag, GD, kind in (("gnnpose", graphs_pose, "plain"),
                              ("gnnrand", graphs_rand, "plain"),
                              ("gnnpose_shuf", graphs_shuf, "plain"),
                              ("fusion", graphs_pose, "fusion")):
            tri = [i for i in trp if i in GD]; tei = [i for i in tep if i in GD]
            m = train_gnn([GD[i] for i in tri], Dn[tri], y[tri], seed, kind)
            s = score_gnn(m, [GD[i] for i in tei], Dn[tei], kind)
            res[tag] = roc_auc_score(y[tei], s)
            if seed == 0:
                assert tei == tep, "arm test sets diverged; DeLong pairing broken"
                out["seed0_scores"][tag] = s.tolist()
                out["seed0_scores"]["y_pose"] = y[tep].tolist()
        out["splits"].append(res)
        print("split", seed, {k: round(v, 3) for k, v in res.items() if k in arms}, flush=True)
    summ = {}
    for a in arms:
        vals = [s[a] for s in out["splits"]]
        boots = [float(np.mean(np.random.default_rng(b).choice(vals, len(vals))))
                 for b in range(2000)]
        summ[a] = {"mean": float(np.mean(vals)),
                   "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]}
    s0 = out["seed0_scores"]
    yp = np.array(s0["y_pose"])
    out["summary"] = summ
    out["delong_seed0"] = {
        "gnnpose_vs_gnn2d": delong_p(yp, np.array(s0["gnnpose"]), np.array(s0["gnn2d_pose_subset"])),
        "gnnpose_vs_gnnrand": delong_p(yp, np.array(s0["gnnpose"]), np.array(s0["gnnrand"])),
        "fusion_vs_gnnpose": delong_p(yp, np.array(s0["fusion"]), np.array(s0["gnnpose"])),
        "gnnpose_vs_gnnpose_shuf": delong_p(yp, np.array(s0["gnnpose"]), np.array(s0["gnnpose_shuf"])),
    }
    out["gates"] = {
        "G_pose": bool(summ["gnnpose"]["mean"] > float(np.mean([s["gnn2d_pose_subset"] for s in out["splits"]]))
                       and summ["gnnpose"]["mean"] > summ["gnnrand"]["mean"]
                       and summ["gnnpose"]["mean"] > summ["gnnpose_shuf"]["mean"]
                       and out["delong_seed0"]["gnnpose_vs_gnn2d"] < 0.01),
        "G_leak": bool(summ["mlp8"]["mean"] - summ["mlp7"]["mean"] > 0.05),
        "G_sanity_ok": bool(all(s["gnn2d_randlab"] <= 0.65 for s in out["splits"])),
    }
    avail = np.zeros(len(records), dtype=bool); avail[ok] = True
    out["pose_availability"] = {
        "n_pose": int(avail.sum()), "n_total": len(records),
        "activity_rate_pose": float(y[avail].mean()), "activity_rate_all": float(y.mean()),
        "molwt_mean_pose": float(D7[avail, 0].mean()), "molwt_mean_all": float(D7[:, 0].mean()),
        "rotb_mean_pose": float(D7[avail, 1].mean()), "rotb_mean_all": float(D7[:, 1].mean()),
        "logp_mean_pose": float(D7[avail, 6].mean()), "logp_mean_all": float(D7[:, 6].mean())}
    json.dump(out, open(RES / "ablation.json", "w"), indent=1)
    print(json.dumps({"summary": {k: round(v["mean"], 3) for k, v in summ.items()},
                      "gates": out["gates"]}, indent=1))

if __name__ == "__main__":
    main()
