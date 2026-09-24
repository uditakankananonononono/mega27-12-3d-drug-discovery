"""Pose geometry: Kabsch superposition RMSD and binding-box math."""
from __future__ import annotations
import numpy as np

KNOWN_ELEMENTS = {"C", "N", "O", "S", "F", "P", "Cl", "Br", "I", "B",
                "Si", "Se", "Zn", "Fe", "Mg", "Ca", "Na", "K", "Cu", "Mn"}


def kabsch_rmsd(p: np.ndarray, q: np.ndarray) -> float:
    """Minimum RMSD between two Nx3 point sets under optimal rigid superposition."""
    p = np.asarray(p, dtype=float); q = np.asarray(q, dtype=float)
    assert p.shape == q.shape and p.shape[1] == 3 and len(p) >= 2
    pc, qc = p - p.mean(0), q - q.mean(0)
    h = pc.T @ qc
    u, _, vt = np.linalg.svd(h)
    d = np.sign(np.linalg.det(u @ vt))
    corr = np.diag([1.0, 1.0, d])
    r = u @ corr @ vt
    pr = pc @ r
    return float(np.sqrt(((pr - qc) ** 2).sum() / len(p)))


def box_from_ligand(coords: np.ndarray, padding: float = 4.0,
                    min_size: float = 20.0, max_size: float = 30.0):
    """Docking box centered on a reference ligand: center + cubic size."""
    coords = np.asarray(coords, dtype=float)
    center = coords.mean(0)
    span = coords.max(0) - coords.min(0)
    size = float(np.clip(span.max() + 2 * padding, min_size, max_size))
    return center.tolist(), [size, size, size]


def parse_pose_pdbqt(pdbqt_text: str):
    """Heavy-atom (coords, elements) from a Vina pose PDBQT string (MODEL 1)."""
    coords, elements = [], []
    in_model = False
    for line in pdbqt_text.splitlines():
        if line.startswith("MODEL"):
            in_model = True
            continue
        if line.startswith("ENDMDL"):
            break
        if line.startswith(("ATOM", "HETATM")) and (in_model or "ROOT" in pdbqt_text):
            # element from the atom-name field: strip digits, leading letters
            name = line[12:16].strip()
            alpha = "".join(c for c in name if c.isalpha())
            el = alpha[:2].capitalize() if alpha[:2].capitalize() in KNOWN_ELEMENTS else alpha[:1]
            if el.upper() == "H" or not el:
                continue
            coords.append([float(line[30:38]), float(line[38:46]), float(line[46:54])])
            elements.append(el.capitalize())
    if not coords:
        raise ValueError("no heavy atoms parsed from pose")
    import numpy as np
    return np.array(coords), elements


def assignment_rmsd(ref_coords, ref_elements, mob_coords, mob_elements,
                    iters: int = 4) -> float:
    """Heavy-atom RMSD with per-element optimal assignment (Hungarian) refined
    under Kabsch superposition. Connectivity-free pose-RMSD estimate."""
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    ref_coords = np.asarray(ref_coords, float)
    mob_coords = np.asarray(mob_coords, float)
    assert sorted(ref_elements) == sorted(mob_elements), "element composition mismatch"
    mob = mob_coords.copy()
    for _ in range(iters):
        pairs = []
        for el in set(ref_elements):
            ri = [i for i, e in enumerate(ref_elements) if e == el]
            mi = [i for i, e in enumerate(mob_elements) if e == el]
            d = np.linalg.norm(ref_coords[ri][:, None, :] - mob[mi][None, :, :], axis=2)
            r, c = linear_sum_assignment(d)
            pairs += [(ri[a], mi[b]) for a, b in zip(r, c)]
        ri_all = np.array([a for a, _ in pairs])
        mi_all = np.array([b for _, b in pairs])
        # Kabsch-align mobile onto reference using current assignment
        p = ref_coords[ri_all]
        q = mob[mi_all]
        pc, qc = p - p.mean(0), q - q.mean(0)
        u, _, vt = np.linalg.svd(qc.T @ pc)
        d = np.sign(np.linalg.det(u @ vt))
        r_mat = u @ np.diag([1.0, 1.0, d]) @ vt
        mob = (mob - q.mean(0)) @ r_mat + p.mean(0)
    return float(np.sqrt(((ref_coords[ri_all] - mob[mi_all]) ** 2).sum() / len(ri_all)))
