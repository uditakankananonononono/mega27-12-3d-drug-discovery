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


def _dock_worker(receptor, pdbqt, center, size, name, queue):
    res, _ = dock_ligand(receptor, pdbqt, center, size, ligand_name=name,
                         exhaustiveness=8, n_poses=5, cpu=2)
    queue.put((res.best_affinity, res.all_affinities))


def dock_ligand_with_timeout(receptor_pdbqt: str, ligand_pdbqt: str, center,
                             box_size, ligand_name: str = "ligand",
                             timeout_s: int = 300, worker=None,
                             pid_sink=None):
    """Dock one ligand in a spawned child process with a hard wall-clock
    timeout. Vina's torsion search can spin indefinitely on macrocycles; the
    python binding cannot be interrupted in-process, so the child is killed.
    Raises TimeoutError on timeout."""
    import multiprocessing as mp
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    target = worker or _dock_worker
    proc = ctx.Process(target=target,
                       args=(receptor_pdbqt, ligand_pdbqt, center, box_size,
                             ligand_name, queue))
    proc.start()
    if pid_sink is not None:
        pid_sink.append(proc.pid)
    proc.join(timeout_s)
    if proc.is_alive():
        proc.terminate(); proc.join()
        raise TimeoutError(f"vina dock exceeded {timeout_s}s")
    if queue.empty():
        raise RuntimeError("dock worker died without result")
    return queue.get()
