"""Structure preparation: PDB parsing, receptor PDBQT via meeko CLI, ligand
PDBQT from SMILES via RDKit embedding + meeko."""
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path

import numpy as np

BACKBONE = {"N", "CA", "C", "O", "OXT"}


def parse_pdb_atoms(pdb_path: str):
    """Return list of atom dicts for ATOM/HETATM records."""
    atoms = []
    for line in open(pdb_path):
        rec = line[:6].strip()
        if rec not in ("ATOM", "HETATM"):
            continue
        atoms.append({
            "record": rec, "serial": int(line[6:11]), "name": line[12:16].strip(),
            "resname": line[17:20].strip(), "chain": line[21],
            "resseq": int(line[22:26]), "x": float(line[30:38]),
            "y": float(line[38:46]), "z": float(line[46:54]),
            "element": line[76:78].strip(),
        })
    return atoms


def hetatm_residues(pdb_path: str, resname: str, chain: str | None = None):
    """Heavy atoms of one HETATM residue type (e.g. ligand N3)."""
    out = [a for a in parse_pdb_atoms(pdb_path)
           if a["record"] == "HETATM" and a["resname"] == resname
           and a["element"] != "H"
           and (chain is None or a["chain"] == chain)]
    return out


def ligand_coords(pdb_path: str, resname: str, chain: str | None = None) -> np.ndarray:
    atoms = hetatm_residues(pdb_path, resname, chain)
    if not atoms:
        raise ValueError(f"no HETATM residue {resname} in {pdb_path}")
    return np.array([[a["x"], a["y"], a["z"]] for a in atoms])


def extract_protein_pdb(pdb_path: str, chain: str, out_path: str) -> int:
    """Write standard-residue ATOM records of one chain to a clean PDB."""
    n = 0
    with open(out_path, "w") as fh:
        for line in open(pdb_path):
            if line[:6].strip() == "ATOM" and line[21] == chain:
                fh.write(line)
                n += 1
        fh.write("TER\nEND\n")
    return n


def prepare_receptor(protein_pdb: str, out_pdbqt: str,
                     extra_args: list[str] | None = None) -> str:
    """Run meeko's receptor preparation (real CLI)."""
    cmd = ["mk_prepare_receptor.py", "--read_pdb", protein_pdb,
           "-o", out_pdbqt, "-p"]
    if extra_args:
        cmd += list(extra_args)
    subprocess.run(cmd,
                   check=True, capture_output=True, text=True, timeout=300)
    produced = Path(out_pdbqt)
    if not produced.exists():
        # meeko appends .pdbqt when -p is used with an .pdbqt-suffixed -o
        alt = Path(out_pdbqt + ".pdbqt")
        if alt.exists():
            alt.rename(produced)
    if not produced.exists():
        raise RuntimeError("receptor preparation produced no output")
    return out_pdbqt


def smiles_to_pdbqt(smiles: str, out_pdbqt: str, seed: int = 42) -> str:
    """SMILES -> 3D conformer (RDKit ETKDG+MMFF) -> PDBQT (meeko)."""
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from meeko import MoleculePreparation, PDBQTWriterLegacy

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"unparsable SMILES: {smiles}")
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    if AllChem.EmbedMolecule(mol, params) != 0:
        raise RuntimeError("3D embedding failed")
    AllChem.MMFFOptimizeMolecule(mol)
    prep = MoleculePreparation()
    setups = prep.prepare(mol)
    if len(setups) != 1:
        raise RuntimeError(f"expected 1 ligand setup, got {len(setups)}")
    pdbqt, is_ok, err = PDBQTWriterLegacy.write_string(setups[0])
    if not is_ok:
        raise RuntimeError(f"PDBQT write failed: {err}")
    Path(out_pdbqt).write_text(pdbqt)
    return out_pdbqt
