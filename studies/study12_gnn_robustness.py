"""GNN LOO robustness: multi-seed reruns of the committed benchmark to attach an
honest variance to the n=15 AUROC. Uses the same cached pose graphs as the analysis."""
import json, pathlib
import numpy as np
from drugdisc.geometry import parse_pose_pdbqt
from drugdisc.gnn_rescorer import pose_graph, loo_gnn_scores
from sklearn.metrics import roc_auc_score

ROOT = pathlib.Path(__file__).resolve().parent.parent
analysis = json.loads((ROOT / "results/screen_analysis.json").read_text())
labeled = [r for r in analysis["ranking"] if r["class"] in ("active", "inactive")]
y = np.array([1 if r["class"] == "active" else 0 for r in labeled])
POSES = ROOT / "results/screen/poses"
graphs = []
for r in labeled:
    coords, elements = parse_pose_pdbqt((POSES / f"{r['name']}_pose.pdbqt").read_text())
    graphs.append(pose_graph(coords, elements))
print(f"{len(graphs)} pose graphs, {int(y.sum())} actives", flush=True)

scores = {}
for seed in (0, 1, 2, 3, 4):
    s = roc_auc_score(y, loo_gnn_scores(graphs, y, epochs=120, seed=seed))
    scores[f"seed_{seed}"] = float(s)
    print(f"seed {seed}: LOO AUROC = {s:.3f}", flush=True)
vals = list(scores.values())
out = {"per_seed_auroc": scores, "mean": float(np.mean(vals)), "std": float(np.std(vals)),
       "min": float(np.min(vals)), "max": float(np.max(vals)),
       "committed_single_seed_value": analysis["auroc_gnn_rescorer_loo"],
       "note": "LOO is per-ligand (one pose graph per compound, held out whole); n=15"}
(ROOT / "results/gnn_robustness.json").write_text(json.dumps(out, indent=1))
print(f"mean {np.mean(vals):.3f} +- {np.std(vals):.3f} (range {np.min(vals):.3f}-{np.max(vals):.3f})")
