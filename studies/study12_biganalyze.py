"""Study 12 bigscreen analysis: raw Vina vs MLP vs 2D-GNN at n~70.

Combines the 50-compound balanced ChEMBL bigscreen (results/bigscreen/) with
the original 22-ligand literature screen (results/screen/) into one labeled
set. Evaluates three rankers under honest small-n protocol:
  (a) raw Vina affinity,
  (b) MLP on RDKit descriptors, leave-one-out CV,
  (c) 2D molecular-graph GCN (bond adjacency, pure PyTorch), LOO CV, 5 seeds.
The GNN here is a *molecular* graph network (no docked pose needed), distinct
from the pose-graph rescorer of study12_analyze.py; both are reported.
Writes results/bigscreen_analysis.json + bigscreen_auroc.png.
"""
import json
import pathlib

import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski
from sklearn.metrics import roc_auc_score

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"

# ---------- load both sources into one labeled set ----------
records = []
for p in sorted((RES / "bigscreen").glob("*.json")):
    r = json.loads(p.read_text())
    records.append({"name": r["chembl_id"], "smiles": r["smiles"],
                    "affinity": float(r["affinity"]), "label": r["label"],
                    "source": "bigscreen"})
for p in sorted((RES / "screen").glob("*.json")):
    r = json.loads(p.read_text())
    records.append({"name": r["name"], "smiles": r["smiles"],
                    "affinity": float(r["affinity"]), "label": r["known_class"],
                    "source": "screen22"})

labeled = [r for r in records if r["label"] in ("active", "inactive")]
print(f"combined: {len(records)} docked, {len(labeled)} labeled "
      f"({sum(r['label']=='active' for r in labeled)} active / "
      f"{sum(r['label']=='inactive' for r in labeled)} inactive)")

y = np.array([1 if r["label"] == "active" else 0 for r in labeled])
aff = np.array([r["affinity"] for r in labeled])
auroc_raw = roc_auc_score(y, -aff)
print(f"raw Vina AUROC (n={len(y)}): {auroc_raw:.3f}")

# ---------- descriptors ----------
for r in labeled:
    mol = Chem.MolFromSmiles(r["smiles"])
    r["desc"] = [Descriptors.MolWt(mol), Lipinski.NumRotatableBonds(mol),
                 Lipinski.HeavyAtomCount(mol), Lipinski.NumHDonors(mol),
                 Lipinski.NumHAcceptors(mol), Descriptors.TPSA(mol),
                 Descriptors.MolLogP(mol),
                 r["affinity"] / max(Lipinski.HeavyAtomCount(mol), 1)]

import torch
import torch.nn as nn

X = np.array([r["desc"] for r in labeled], dtype=np.float32)
X = (X - X.mean(0)) / (X.std(0) + 1e-9)

# ---------- MLP, LOO ----------
torch.manual_seed(0)
loo_mlp = np.zeros(len(y))
for i in range(len(y)):
    tr = np.array([j for j in range(len(y)) if j != i])
    model = nn.Sequential(nn.Linear(X.shape[1], 16), nn.ReLU(), nn.Dropout(0.2),
                          nn.Linear(16, 1))
    opt = torch.optim.Adam(model.parameters(), lr=5e-3)
    lossf = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor(float((len(y) - y.sum()) / max(y.sum(), 1))))
    xt = torch.from_numpy(X[tr]); yt = torch.from_numpy(y[tr].astype(np.float32))
    model.train()
    for _ in range(200):
        opt.zero_grad()
        loss = lossf(model(xt).squeeze(-1), yt)
        loss.backward(); opt.step()
    model.eval()
    with torch.no_grad():
        loo_mlp[i] = torch.sigmoid(model(torch.from_numpy(X[i:i+1])).squeeze(-1)).item()
auroc_mlp = roc_auc_score(y, loo_mlp)
print(f"MLP LOO AUROC: {auroc_mlp:.3f}", flush=True)

# ---------- 2D molecular-graph GCN (bond adjacency), LOO, 5 seeds ----------
from drugdisc.gnn_rescorer import PoseGCN, ELEMENTS, EL_IDX

def mol_graph(smiles: str):
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

graphs = [mol_graph(r["smiles"]) for r in labeled]

def loo_scores_seed(seed: int, epochs: int = 120) -> np.ndarray:
    n = len(y)
    out = np.zeros(n)
    for i in range(n):
        torch.manual_seed(seed)
        model = PoseGCN(graphs[0][0].shape[1])
        opt = torch.optim.Adam(model.parameters(), lr=5e-3)
        pw = torch.tensor(float((n - y.sum()) / max(y.sum(), 1)))
        lossf = nn.BCEWithLogitsLoss(pos_weight=pw)
        tr = [j for j in range(n) if j != i]
        model.train()
        for _ in range(epochs):
            opt.zero_grad()
            preds = torch.stack([model(torch.from_numpy(graphs[j][0]),
                                       torch.from_numpy(graphs[j][1])) for j in tr])
            loss = lossf(preds, torch.from_numpy(y[tr].astype(np.float32)))
            loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            out[i] = torch.sigmoid(model(torch.from_numpy(graphs[i][0]),
                                         torch.from_numpy(graphs[i][1]))).item()
    return out

seed_aurocs = []
for seed in range(5):
    s = loo_scores_seed(seed)
    a = roc_auc_score(y, s)
    seed_aurocs.append(float(a))
    print(f"  GNN seed {seed}: LOO AUROC={a:.3f}", flush=True)
gnn_mean = float(np.mean(seed_aurocs)); gnn_std = float(np.std(seed_aurocs))
print(f"2D-GNN LOO AUROC (5 seeds): {gnn_mean:.3f} +/- {gnn_std:.3f}")

summary = {
    "n_docked_total": len(records),
    "n_labeled": int(len(y)),
    "n_active": int(y.sum()), "n_inactive": int(len(y) - y.sum()),
    "sources": {"bigscreen": sum(r["source"] == "bigscreen" for r in records),
                "screen22": sum(r["source"] == "screen22" for r in records)},
    "auroc_raw_vina": float(auroc_raw),
    "auroc_mlp_loo": float(auroc_mlp),
    "auroc_gnn2d_loo_mean": gnn_mean,
    "auroc_gnn2d_loo_std": gnn_std,
    "auroc_gnn2d_loo_per_seed": seed_aurocs,
    "protocol": "balanced ChEMBL bigscreen (50) + literature screen (22); "
                "LOO CV for learned rankers; GNN = 2D bond-graph GCN, 5 seeds",
    "verdict": ("GNN beats raw Vina" if gnn_mean > auroc_raw
                else "GNN does NOT beat raw Vina at this n"),
}
(RES / "bigscreen_analysis.json").write_text(json.dumps(summary, indent=1))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6, 4))
names = ["raw Vina", "MLP (LOO)", "2D-GNN (LOO, 5 seeds)"]
vals = [auroc_raw, auroc_mlp, gnn_mean]
errs = [0, 0, gnn_std]
ax.bar(names, vals, yerr=errs, capsize=6,
       color=["#7f8c8d", "#2980b9", "#c0392b"])
ax.axhline(0.5, ls="--", c="k", lw=0.8)
ax.set_ylabel("AUROC"); ax.set_ylim(0, 1)
ax.set_title(f"Mpro bigscreen verdict (n={len(y)} labeled)")
plt.tight_layout(); plt.savefig(RES / "bigscreen_auroc.png", dpi=150)
print("wrote results/bigscreen_analysis.json + bigscreen_auroc.png")
