"""Hermetic prep tests on a committed mini-PDB fixture (no network, no meeko CLI)."""
import pathlib
import numpy as np
from drugdisc.prep import parse_pdb_atoms, hetatm_residues, extract_protein_pdb

FIX = pathlib.Path(__file__).parent / "fixtures" / "mini.pdb"


def test_parse_pdb_atoms_counts():
    atoms = parse_pdb_atoms(str(FIX))
    assert len(atoms) == 6
    assert atoms[0]["record"] == "ATOM"
    assert atoms[-1]["resname"] == "LIG"


def test_hetatm_filter():
    atoms = hetatm_residues(str(FIX), "LIG")
    assert len(atoms) == 2
    assert all(a["element"] != "H" for a in atoms)


def test_extract_protein(tmp_path):
    out = tmp_path / "prot.pdb"
    n = extract_protein_pdb(str(FIX), "A", str(out))
    assert n == 4
    text = out.read_text()
    assert "HETATM" not in text and "TER" in text
