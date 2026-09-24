import numpy as np
from drugdisc.geometry import kabsch_rmsd, box_from_ligand


def test_kabsch_identical():
    p = np.random.default_rng(0).normal(size=(10, 3))
    assert kabsch_rmsd(p, p) < 1e-10


def test_kabsch_rotation_invariant():
    rng = np.random.default_rng(1)
    p = rng.normal(size=(15, 3))
    theta = 0.7
    rot = np.array([[np.cos(theta), -np.sin(theta), 0],
                    [np.sin(theta), np.cos(theta), 0], [0, 0, 1]])
    q = p @ rot + np.array([5.0, -3.0, 2.0])
    assert kabsch_rmsd(p, q) < 1e-6


def test_kabsch_translation_removed():
    # a constant shift is pure translation: removed by centering, RMSD ~ 0
    p = np.zeros((4, 3)); p[:, 0] = [0, 1, 2, 3]
    q = p.copy(); q[:, 1] += 2.0
    assert kabsch_rmsd(p, q) < 1e-6


def test_kabsch_known_distortion():
    # one point moved by +2 in y: mean-centered squared error = 4*(1/4)*... exact value
    p = np.zeros((4, 3)); p[:, 0] = [0, 1, 2, 3]
    q = p.copy(); q[0, 1] += 2.0
    # Kabsch finds the optimal rotation: RMSD must be > 0 and no worse than
    # identity alignment (equality unless a rotation helps, e.g. collinear sets)
    pc = p - p.mean(0); qc = q - q.mean(0)
    identity_rmsd = float(np.sqrt(((pc - qc) ** 2).sum() / 4))
    r = kabsch_rmsd(p, q)
    assert 1e-6 < r <= identity_rmsd + 1e-9


def test_box_from_ligand_bounds():
    coords = np.array([[0, 0, 0], [10, 4, 6]], dtype=float)
    center, size = box_from_ligand(coords)
    assert np.allclose(center, [5, 2, 3])
    assert all(20.0 <= s <= 30.0 for s in size)
    assert size[0] == size[1] == size[2]


def test_parse_pose_pdbqt_and_assignment_rmsd():
    from drugdisc.geometry import parse_pose_pdbqt, assignment_rmsd
    pose = """MODEL 1
REMARK VINA RESULT:    -7.123      0.000      0.000
ROOT
ATOM      1  C1  LIG A   1      10.000  10.000  10.000  1.00  0.00    +0.000 C
ATOM      2  O1  LIG A   1      11.200  10.000  10.000  1.00  0.00    +0.000 O
ATOM      3  H1  LIG A   1      10.000  11.000  10.000  1.00  0.00    +0.000 H
ENDROOT
ENDMDL"""
    coords, els = parse_pose_pdbqt(pose)
    assert coords.shape == (2, 3) and els == ["C", "O"]
    ref = coords.copy()
    ref[0] += np.array([0.3, 0.0, 0.0])  # distort one atom only
    r = assignment_rmsd(ref, els, coords, els)
    assert 0.05 < r < 0.3
    # atom order permutation must not change the result
    perm = [1, 0]
    r2 = assignment_rmsd(ref, els, coords[perm], [els[i] for i in perm])
    assert abs(r - r2) < 0.05
