"""GNN pose-graph rescorer: the docked ligand as a molecular graph (atoms =
nodes, distance-cutoff edges), GCN embedding -> activity score. Pure PyTorch."""
from __future__ import annotations
import numpy as np
import torch
import torch.nn as nn

ELEMENTS = ["C", "N", "O", "S", "F", "P", "Cl", "Br", "I", "OTHER"]
EL_IDX = {e: i for i, e in enumerate(ELEMENTS)}


def pose_graph(coords, elements, cutoff: float = 4.0):
    """Node features (n, len(ELEMENTS)+1) and normalized adjacency (n, n) from a
    docked pose: one-hot element + degree, edges between atoms < cutoff apart."""
    coords = np.asarray(coords, float)
    n = len(coords)
    x = np.zeros((n, len(ELEMENTS) + 1), dtype=np.float32)
    for i, el in enumerate(elements):
        x[i, EL_IDX.get(el, EL_IDX["OTHER"])] = 1.0
    d = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=2)
    a = ((d < cutoff) & (d > 0)).astype(np.float32)
    x[:, -1] = a.sum(1) / max(n - 1, 1)  # normalized degree
    a += np.eye(n, dtype=np.float32)
    deg = a.sum(1); deg[deg == 0] = 1.0
    dinv = 1.0 / np.sqrt(deg)
    a_norm = (a * dinv[:, None]) * dinv[None, :]
    return x, a_norm


class PoseGCN(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 24, layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.weights = nn.ParameterList()
        self.biases = nn.ParameterList()
        dims = [in_dim] + [hidden] * layers
        for i in range(layers):
            w = torch.empty(dims[i], dims[i + 1])
            nn.init.xavier_uniform_(w)
            self.weights.append(nn.Parameter(w))
            self.biases.append(nn.Parameter(torch.zeros(dims[i + 1])))
        self.head = nn.Sequential(nn.Linear(hidden, 12), nn.ReLU(),
                                  nn.Dropout(dropout), nn.Linear(12, 1))

    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        h = x
        for w, b in zip(self.weights, self.biases):
            h = torch.relu(adj @ h @ w + b)
        return self.head(h.mean(dim=0)).squeeze(-1)


def loo_gnn_scores(graphs, labels, epochs: int = 120, lr: float = 5e-3, seed: int = 0):
    """Leave-one-out CV scores for the GCN over pose graphs."""
    y = np.asarray(labels, dtype=np.float32)
    n = len(y)
    out = np.zeros(n)
    for i in range(n):
        torch.manual_seed(seed)
        model = PoseGCN(graphs[0][0].shape[1])
        opt = torch.optim.Adam(model.parameters(), lr=lr)
        pw = torch.tensor(float((n - y.sum()) / max(y.sum(), 1)))
        lossf = nn.BCEWithLogitsLoss(pos_weight=pw)
        model.train()
        for _ in range(epochs):
            tot = 0.0
            for j in range(n):
                if j == i:
                    continue
                x, a = graphs[j]
                loss = lossf(model(torch.from_numpy(x), torch.from_numpy(a)),
                             torch.tensor(y[j]))
                opt.zero_grad(); loss.backward(); opt.step()
                tot += loss.item()
        model.eval()
        with torch.no_grad():
            x, a = graphs[i]
            out[i] = torch.sigmoid(model(torch.from_numpy(x), torch.from_numpy(a))).item()
    return out
