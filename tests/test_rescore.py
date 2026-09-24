import numpy as np
from drugdisc.rescore import pose_descriptors, contact_features


def test_pose_descriptors_values():
    d = pose_descriptors([-9.0, -8.5, -8.7], n_rotatable=5, n_heavy=30)
    assert d[0] == -9.0 and d[1] == -8.5
    assert abs(d[7] - (-9.0 / 30.0)) < 1e-6
    assert d.shape == (8,)


def test_contact_features_counts():
    pose_coords = np.array([[0, 0, 0], [10, 0, 0]], dtype=float)
    pose_elements = ["O", "C"]
    receptor = [
        {"x": 1.0, "y": 0.0, "z": 0.0, "element": "N"},   # 1 A from ligand O -> hbond
        {"x": 50.0, "y": 0.0, "z": 0.0, "element": "C"},  # far away
    ]
    f = contact_features(pose_coords, pose_elements, receptor)
    assert f[3] == 1.0          # one N/O-N/O contact within 3.5 A
    assert f[4] == 1.0          # one buried ligand atom (the O)
    assert f.sum() == 1 + 1 + 1  # polar-class count includes the O contact
