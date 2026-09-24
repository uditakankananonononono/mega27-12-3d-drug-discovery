"""AutoDock Vina docking wrapper (real engine)."""
from __future__ import annotations
from dataclasses import dataclass

from vina import Vina


@dataclass
class DockResult:
    ligand_name: str
    best_affinity: float
    all_affinities: list
    n_poses: int


def dock_ligand(receptor_pdbqt: str, ligand_pdbqt: str, center, box_size,
                ligand_name: str = "ligand", exhaustiveness: int = 8,
                n_poses: int = 5, seed: int = 42,
                cpu: int = 1) -> tuple[DockResult, str]:
    """Dock one ligand. Returns (result, docked-pose PDBQT string)."""
    v = Vina(sf_name="vina", seed=seed, cpu=cpu, verbosity=0)
    v.set_receptor(receptor_pdbqt)
    v.set_ligand_from_file(ligand_pdbqt)
    v.compute_vina_maps(center=center, box_size=box_size)
    v.dock(exhaustiveness=exhaustiveness, n_poses=n_poses)
    affinities = [round(float(e), 3) for e in v.energies(n_poses=n_poses)[:, 0].tolist()]
    poses = v.poses(n_poses=1)
    return DockResult(ligand_name, affinities[0], affinities, len(affinities)), poses


def score_pose(receptor_pdbqt: str, ligand_pdbqt: str, center, box_size,
               seed: int = 42) -> float:
    """Score the input pose without sampling (Vina 'score-only')."""
    v = Vina(sf_name="vina", seed=seed, verbosity=0)
    v.set_receptor(receptor_pdbqt)
    v.set_ligand_from_file(ligand_pdbqt)
    v.compute_vina_maps(center=center, box_size=box_size)
    return float(v.score()[0])
