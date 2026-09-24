"""Pose featurization and neural rescoring (CNN/GNN) on top of raw Vina ranks.
Features come from the docked pose geometry + Vina energy decomposition; the
rescorer learns to rank known actives above inactives from the screening
campaign's own labels (known_class from published experimental literature)."""
from __future__ import annotations
import numpy as np

VDW_RADII = {"C": 1.7, "N": 1.55, "O": 1.52, "S": 1.8, "F": 1.47, "P": 1.8,
             "Cl": 1.75, "Br": 1.85, "I": 1.98, "H": 1.2}


def pose_descriptors(affinities, n_rotatable: int, n_heavy: int) -> np.ndarray:
    """Ligand-level descriptor vector from Vina outputs + ligand size."""
    aff = np.asarray(affinities, dtype=float)
    return np.array([
        aff.min(), aff.max(), aff.mean(), aff.std(),
        aff.max() - aff.min(),
        float(n_rotatable), float(n_heavy),
        aff.min() / max(float(n_heavy), 1.0),   # ligand-efficiency proxy
    ], dtype=np.float32)


def contact_features(pose_coords, pose_elements, receptor_atoms, cutoff: float = 4.5) -> np.ndarray:
    """Receptor-contact histogram: counts of ligand atoms within `cutoff` of
    receptor residues, binned by element pair class (C/N/O/other), plus
    hydrogen-bond-like contacts (N/O within 3.5 A of receptor N/O)."""
    pose_coords = np.asarray(pose_coords, float)
    rec_coords = np.array([[a["x"], a["y"], a["z"]] for a in receptor_atoms], float)
    rec_elements = [a["element"].capitalize() for a in receptor_atoms]
    d = np.linalg.norm(pose_coords[:, None, :] - rec_coords[None, :, :], axis=2)
    close = d < cutoff
    feats = []
    for el_class in (("C",), ("N", "O"), ("S", "F", "Cl", "Br", "I", "P")):
        mask = np.array([e in el_class for e in pose_elements])
        feats.append(float(close[mask].sum()))
    ligand_polar = np.array([e in ("N", "O") for e in pose_elements])
    rec_polar = np.array([e in ("N", "O") for e in rec_elements])
    feats.append(float((d[np.ix_(ligand_polar, rec_polar)] < 3.5).sum()))
    feats.append(float(close.any(axis=1).sum()))  # buried ligand atoms
    return np.array(feats, dtype=np.float32)


def build_feature_matrix(records, receptor_atoms) -> np.ndarray:
    """Stack pose_descriptors + contact_features for a list of screen records
    that carry parsed pose data."""
    rows = []
    for rec in records:
        desc = pose_descriptors(rec["all_affinities"], rec["n_rotatable"], rec["n_heavy"])
        contact = contact_features(rec["pose_coords"], rec["pose_elements"], receptor_atoms)
        rows.append(np.concatenate([desc, contact]))
    return np.stack(rows)
