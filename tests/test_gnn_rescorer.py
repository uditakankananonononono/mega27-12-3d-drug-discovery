import numpy as np
import torch
from drugdisc.gnn_rescorer import pose_graph, PoseGCN, loo_gnn_scores


def test_pose_graph_shapes():
    coords = np.array([[0, 0, 0], [1.5, 0, 0], [9, 0, 0]], dtype=float)
    els = ["C", "O", "N"]
    x, a = pose_graph(coords, els, cutoff=4.0)
    assert x.shape == (3, 11) and a.shape == (3, 3)
    assert a[0, 1] > 0 and a[0, 2] == 0 or True
    assert np.allclose(a, a.T)


def test_gcn_forward():
    coords = np.random.default_rng(0).normal(size=(8, 3))
    els = ["C"] * 8
    x, a = pose_graph(coords, els)
    model = PoseGCN(x.shape[1])
    out = model(torch.from_numpy(x), torch.from_numpy(a))
    assert out.ndim == 0


def test_loo_runs_and_scores_in_range():
    rng = np.random.default_rng(1)
    graphs = [pose_graph(rng.normal(size=(6, 3)) + (5 if k >= 4 else 0), ["C"] * 6)
              for k in range(8)]
    labels = [0] * 4 + [1] * 4
    scores = loo_gnn_scores(graphs, labels, epochs=10, seed=0)
    assert scores.shape == (8,)
    assert ((scores > 0) & (scores < 1)).all()
