import time
import pytest
from drugdisc.dock import dock_ligand_with_timeout


def _slow_worker(*args):
    time.sleep(30)  # never finishes inside the test budget


def test_timeout_fires_hermetic():
    with pytest.raises(TimeoutError):
        dock_ligand_with_timeout("no_receptor.pdbqt", "no_ligand.pdbqt",
                                 [0, 0, 0], [20, 20, 20], timeout_s=1,
                                 worker=_slow_worker)


def _fake_worker(*args):
    args[-1].put((-7.5, [-7.5, -7.1]))


def test_worker_result_passes_through():
    best, all_aff = dock_ligand_with_timeout("r", "l", [0, 0, 0], [20, 20, 20],
                                             timeout_s=30, worker=_fake_worker)
    assert best == -7.5 and all_aff == [-7.5, -7.1]
