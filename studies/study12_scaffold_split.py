"""PRE-REGISTERED scaffold-split evaluation (judge round 1 adopted gate 1;
docs/JUDGE_ROUNDS.md, docs/PREREGISTER.md). Committed BEFORE running
2026-09-26.

Locked design:
- Data: the identical combined labeled set as study12_biganalyze.py
  (results/bigscreen/*.json + results/screen/*.json, labels active/inactive).
- Split: Bemis-Murcko scaffolds (RDKit MurckoScaffold) per SMILES; compounds
  grouped by scaffold; 5 split seeds; for each seed, scaffold groups are
  shuffled and assigned greedily to test until >=25% of compounds are in
  test; no scaffold crosses the boundary.
- Models on EACH split (this script): raw Vina affinity (no training) and
  descriptor MLP (same architecture/features as biganalyze, trained on
  train scaffolds only). The 2D-GNN arm and the ligand-only / pose-only
  ablations are deferred to a separate pre-registered follow-up script
  (same split seeds) so each script stays reviewable; declared here before
  any outcomes.
- Statistics: AUROC per model per split; 2000-bootstrap 95% CI on the mean
  AUROC across splits; DeLong p-value of each learned model vs raw Vina on
  the concatenated out-of-scaffold predictions.
- GATE (locked): the rescoring claim "learned rescoring beats raw docking
  under scaffold generalization" stands only if, for at least one learned
  model, the bootstrap 95% CI on mean scaffold-split AUROC excludes the raw
  Vina point estimate AND DeLong p < 0.01. Otherwise the learned-family
  advantage is reported as scaffold-memorization-bounded and the claim
  pivots per docs/PREREGISTER.md.
"""
import json
from pathlib import Path
import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.metrics import roc_auc_score

RES = Path(__file__).resolve().parents[1] / "results"

def load_records():
    records = []
    for p in sorted((RES / "bigscreen").glob("*.json")):
        r = json.loads(p.read_text())
        if r.get("label") in ("active", "inactive") and r.get("affinity") is not None:
            records.append({"name": r["chembl_id"], "smiles": r["smiles"],
                            "affinity": float(r["affinity"]), "label": r["label"]})
    for p in sorted((RES / "screen").glob("*.json")):
        r = json.loads(p.read_text())
        if r.get("known_class") in ("active", "inactive"):
            records.append({"name": r["name"], "smiles": r["smiles"],
                            "affinity": float(r["affinity"]), "label": r["known_class"]})
    return records

def scaffolds(records):
    out = []
    for r in records:
        mol = Chem.MolFromSmiles(r["smiles"])
        out.append(MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False))
    return out

def scaffold_split(scaf, seed, test_frac=0.25):
    rng = np.random.default_rng(seed)
    groups = {}
    for i, s in enumerate(scaf):
        groups.setdefault(s, []).append(i)
    order = list(groups.values())
    rng.shuffle(order)
    n = len(scaf); test = []
    for g in order:
        if len(test) < test_frac * n:
            test.extend(g)
    mask = np.zeros(n, dtype=bool); mask[test] = True
    return np.where(~mask)[0], np.where(mask)[0]

def descriptors(rs):
    X = []
    for r in rs:
        mol = Chem.MolFromSmiles(r["smiles"])
        X.append([Descriptors.MolWt(mol), Lipinski.NumRotatableBonds(mol),
                  Lipinski.HeavyAtomCount(mol), Lipinski.NumHDonors(mol),
                  Lipinski.NumHAcceptors(mol), Descriptors.TPSA(mol),
                  Descriptors.MolLogP(mol),
                  r["affinity"] / max(Lipinski.NumHHeavyAtomCount(mol), 1) if hasattr(Lipinski, 'NumHHeavyAtomCount') else r["affinity"] / max(Lipinski.HeavyAtomCount(mol), 1)])
    return np.array(X, dtype=np.float32)

def train_mlp(Xtr, ytr, seed):
    import torch, torch.nn as nn
    torch.manual_seed(seed)
    model = nn.Sequential(nn.Linear(Xtr.shape[1], 16), nn.ReLU(), nn.Dropout(0.2), nn.Linear(16, 1))
    opt = torch.optim.Adam(model.parameters(), lr=5e-3)
    pos = float((len(ytr) - ytr.sum()) / max(ytr.sum(), 1))
    lossf = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pos))
    xt = torch.from_numpy(Xtr); yt = torch.from_numpy(ytr.astype(np.float32))
    model.train()
    for _ in range(200):
        opt.zero_grad(); loss = lossf(model(xt).squeeze(-1), yt); loss.backward(); opt.step()
    model.eval()
    return model

def bootstrap_ci(vals, n_boot=2000, seed=0):
    rng = np.random.default_rng(seed); v = np.array(vals)
    boots = [np.mean(rng.choice(v, len(v), replace=True)) for _ in range(n_boot)]
    return float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))

def delong_p(y_true, s1, s2, seed=0):
    # fast bootstrap approximation of DeLong: paired resampling of AUROC diff
    rng = np.random.default_rng(seed); n = len(y_true); diffs = []
    y_true = np.asarray(y_true)
    for _ in range(2000):
        idx = rng.integers(0, n, n)
        if len(np.unique(y_true[idx])) < 2:
            continue
        diffs.append(roc_auc_score(y_true[idx], s1[idx]) - roc_auc_score(y_true[idx], s2[idx]))
    diffs = np.array(diffs)
    p = 2 * min(float((diffs <= 0).mean()), float((diffs >= 0).mean()))
    return p

def main():
    records = load_records()
    print(f"labeled records: {len(records)}", flush=True)
    y = np.array([1 if r["label"] == "active" else 0 for r in records])
    aff = np.array([r["affinity"] for r in records])
    scaf = scaffolds(records)
    print(f"unique scaffolds: {len(set(scaf))}", flush=True)
    Xraw = descriptors(records)
    out = {"n": len(records), "n_scaffolds": len(set(scaf)), "splits": []}
    oof = {"vina": -aff.copy(), "mlp": np.full(len(y), np.nan), "gnn2d": np.full(len(y), np.nan)}
    for seed in range(5):
        tr, te = scaffold_split(scaf, seed)
        X = (Xraw - Xraw[tr].mean(0)) / (Xraw[tr].std(0) + 1e-9)
        mlp = train_mlp(X[tr], y[tr], seed)
        import torch
        with torch.no_grad():
            oof["mlp"][te] = torch.sigmoid(mlp(torch.from_numpy(X[te])).squeeze(-1)).numpy()
        a_v = roc_auc_score(y[te], -aff[te]); a_m = roc_auc_score(y[te], oof["mlp"][te])
        out["splits"].append({"seed": seed, "n_train": int(len(tr)), "n_test": int(len(te)),
                              "auroc_vina": float(a_v), "auroc_mlp": float(a_m)})
        print(f"split {seed}: vina {a_v:.3f} mlp {a_m:.3f}", flush=True)
    mv = [s["auroc_vina"] for s in out["splits"]]; mm = [s["auroc_mlp"] for s in out["splits"]]
    out["mean_auroc_vina"] = float(np.mean(mv)); out["mean_auroc_mlp"] = float(np.mean(mm))
    out["ci95_mlp"] = bootstrap_ci(mm); out["ci95_vina"] = bootstrap_ci(mv)
    tested = ~np.isnan(oof["mlp"])
    out["delong_p_mlp_vs_vina"] = delong_p(y[tested], oof["mlp"][tested], (-aff)[tested])
    out["gate_pass"] = bool(out["ci95_mlp"][0] > out["mean_auroc_vina"] and out["delong_p_mlp_vs_vina"] < 0.01)
    json.dump(out, open(RES / "scaffold_split.json", "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("mean_auroc_vina", "mean_auroc_mlp", "ci95_mlp", "delong_p_mlp_vs_vina", "gate_pass")}, indent=1))

if __name__ == "__main__":
    main()
