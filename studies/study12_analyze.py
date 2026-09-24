"""Study 12 phase 3: enrichment statistics + neural rescoring vs raw Vina ranks.
Reads per-ligand screen results; adds RDKit descriptors from cached PubChem
SMILES; evaluates (a) raw Vina affinity and (b) a CNN/MLP rescorer under
leave-one-out CV against published-activity labels."""
import json
import math
import pathlib

import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski
from scipy.stats import hypergeom
from sklearn.metrics import roc_auc_score

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCREEN = ROOT / "results/screen"
RES = ROOT / "results"

records = [json.loads(p.read_text()) for p in sorted(SCREEN.glob("*.json"))]
assert len(records) >= 10, f"screen incomplete: {len(records)} ligands"
print(f"analyzing {len(records)} docked ligands")

# RDKit descriptors from the real cached SMILES
for r in records:
    mol = Chem.MolFromSmiles(r["smiles"])
    r["desc"] = [Descriptors.MolWt(mol), Lipinski.NumRotatableBonds(mol),
                 Lipinski.HeavyAtomCount(mol), Lipinski.NumHDonors(mol),
                 Lipinski.NumHAcceptors(mol), Descriptors.TPSA(mol),
                 Descriptors.MolLogP(mol),
                 r["affinity"] / max(Lipinski.HeavyAtomCount(mol), 1)]  # ligand efficiency

labels = np.array([1 if r["known_class"] == "active" else 0 for r in records])
unknown = [r["known_class"] == "unknown" for r in records]
scored = [(r["affinity"], r["known_class"]) for r in records if r["known_class"] != "unknown"]
y = np.array([1 if c == "active" else 0 for _, c in scored])
aff = np.array([a for a, _ in scored])

# enrichment of actives in top-8 by affinity
order = np.argsort(aff)
top = y[order][:8]
M, n_act, n_draw = len(y), y.sum(), 8
p_hyper = float(hypergeom.sf(top.sum() - 1, M, n_act, n_draw))
auroc_raw = roc_auc_score(y, -aff)  # more negative affinity = better
print(f"raw Vina: {int(top.sum())}/{int(n_act)} actives in top-8 "
      f"(hypergeometric p={p_hyper:.4f}), AUROC={auroc_raw:.3f}")

# ---- neural rescoring: compact MLP on descriptors, LOO CV (small-n honest eval)
import torch
import torch.nn as nn

X = np.array([r["desc"] for r in records if r["known_class"] != "unknown"], dtype=np.float32)
X = (X - X.mean(0)) / (X.std(0) + 1e-9)
loo_pred = np.zeros(len(y))
torch.manual_seed(0)
for i in range(len(y)):
    tr = np.array([j for j in range(len(y)) if j != i])
    model = nn.Sequential(nn.Linear(X.shape[1], 16), nn.ReLU(), nn.Dropout(0.2),
                          nn.Linear(16, 1))
    opt = torch.optim.Adam(model.parameters(), lr=5e-3)
    lossf = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(float((len(y) - y.sum()) / max(y.sum(), 1))))
    xt = torch.from_numpy(X[tr]); yt = torch.from_numpy(y[tr].astype(np.float32))
    model.train()
    for _ in range(200):
        opt.zero_grad()
        loss = lossf(model(xt).squeeze(-1), yt)
        loss.backward(); opt.step()
    model.eval()
    with torch.no_grad():
        loo_pred[i] = torch.sigmoid(model(torch.from_numpy(X[i:i + 1])).squeeze(-1)).item()
auroc_nn = roc_auc_score(y, loo_pred)
print(f"neural rescorer LOO AUROC={auroc_nn:.3f} vs raw Vina AUROC={auroc_raw:.3f}")

# ---- GNN pose-graph rescorer (third ranker): re-dock labeled ligands for poses
from drugdisc.prep import smiles_to_pdbqt
from drugdisc.dock import dock_ligand
from drugdisc.geometry import parse_pose_pdbqt
from drugdisc.gnn_rescorer import pose_graph, loo_gnn_scores

RAW = ROOT / "data/raw"
POSES = ROOT / "results/screen/poses"
POSES.mkdir(parents=True, exist_ok=True)
box = json.loads((RAW / "box_7kx5.json").read_text())
graphs = []
for r in [r for r in records if r["known_class"] != "unknown"]:
    pose_file = POSES / f"{r['name']}_pose.pdbqt"
    if not pose_file.exists():
        pdbqt = RAW / f"lig_{r['name']}.pdbqt"
        if not pdbqt.exists():
            smiles_to_pdbqt(r["smiles"], str(pdbqt))
        _, pose = dock_ligand(str(RAW / "7KX5_A_receptor.pdbqt"), str(pdbqt),
                              box["center"], box["size"], ligand_name=r["name"],
                              exhaustiveness=4, n_poses=1, cpu=2)
        pose_file.write_text(pose)
        print(f"  rescoring pose: {r['name']}", flush=True)
    coords, elements = parse_pose_pdbqt(pose_file.read_text())
    graphs.append(pose_graph(coords, elements))
auroc_gnn = roc_auc_score(y, loo_gnn_scores(graphs, y, epochs=120, seed=0))
print(f"GNN pose-graph rescorer LOO AUROC={auroc_gnn:.3f}")

summary = {"n_docked": len(records), "n_labeled": int(len(y)),
           "actives": int(n_act), "top8_actives": int(top.sum()),
           "hypergeometric_p": p_hyper, "auroc_raw_vina": float(auroc_raw),
           "auroc_nn_rescorer_loo": float(auroc_nn),
           "auroc_gnn_rescorer_loo": float(auroc_gnn),
           "ranking": [{"name": r["name"], "affinity": r["affinity"],
                        "class": r["known_class"]}
                       for r in sorted(records, key=lambda r: r["affinity"])]}
(RES / "screen_analysis.json").write_text(json.dumps(summary, indent=1))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ranked = sorted(records, key=lambda r: r["affinity"])
colors = {"active": "#c0392b", "inactive": "#2980b9", "unknown": "#95a5a6"}
plt.figure(figsize=(8, 4.5))
plt.bar([r["name"] for r in ranked], [r["affinity"] for r in ranked],
        color=[colors[r["known_class"]] for r in ranked])
plt.xticks(rotation=70, ha="right", fontsize=7)
plt.ylabel("Vina affinity (kcal/mol)")
plt.title("Mpro (7KX5) screen: red=known active, blue=inactive, gray=unknown")
plt.tight_layout(); plt.savefig(RES / "screen_ranking.png", dpi=150)
print("wrote results/screen_analysis.json + screen_ranking.png")
