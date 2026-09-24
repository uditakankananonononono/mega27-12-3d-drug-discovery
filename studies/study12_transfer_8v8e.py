"""Study 12 transfer pilot: redock ensitrelvir (7YY) into 8V8E chain A.

Same validated protocol as study12_redock.py (7KX5/X7V, RMSD 0.97 A) applied
to an independent structure and ligand chemotype: room-temperature WT
SARS-CoV-2 Mpro catalytic domains (residues 6-190) in complex with
ensitrelvir (S-217622, non-covalent, 2.0 A). Gate: heavy-atom
assignment-RMSD < 2.0 A vs the crystal pose.

Structure selection audit (data/raw/transfer_structure_audit.json): 7VU6 and
8HUR deposits truncate binding-site sidechains (ARG188 at 3.6 A from the
ligand, plus LEU50/GLU47 in 7VU6-A); 8V8E chain A has a complete binding
site (HIS41, MET49, CYS145, HIS163, GLU166, ARG188, GLN189 all full
sidechains). Four incomplete residues were removed by meeko --allow_bad_res:
VAL86 (9.7 A from ligand), VAL125/CYS128/MET130 (14.5-14.7 A); none are
ensitrelvir contact residues.
"""
import json
import pathlib
import subprocess
import numpy as np

from drugdisc.prep import (extract_protein_pdb, prepare_receptor,
                           smiles_to_pdbqt, hetatm_residues)
from drugdisc.dock import dock_ligand
from drugdisc.geometry import parse_pose_pdbqt, assignment_rmsd
from study12_fix_altlocs import fix_altlocs

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
SMILES_7YY = ("Cn1cc2cc(c(cc2n1)Cl)NC3=NC(=O)N(C(=O)N3Cc4cc(c(cc4F)F)F)"
              "Cc5ncn(n5)C")  # RCSB CCD 7YY = ensitrelvir

n_at = extract_protein_pdb(str(RAW / "8V8E.pdb"), "A", str(RAW / "8V8E_A.pdb"))
print(f"chain A protein atoms: {n_at}")
fix = fix_altlocs(str(RAW / "8V8E_A.pdb"), str(RAW / "8V8E_A_fixed.pdb"))
print("altloc fix:", fix["residues_with_altlocs"], "residues")
prepare_receptor(str(RAW / "8V8E_A_fixed.pdb"),
                 str(RAW / "8V8E_A_receptor.pdbqt"),
                 extra_args=["--allow_bad_res"])
print("receptor prepared (bad residues removed: VAL86, VAL125, CYS128, MET130)")

smiles_to_pdbqt(SMILES_7YY, str(RAW / "7YY_ligand.pdbqt"))
print("ligand PDBQT written")

ref_atoms = hetatm_residues(str(RAW / "8V8E.pdb"), "7YY", "A")
ref_coords = np.array([[a["x"], a["y"], a["z"]] for a in ref_atoms])
ref_elements = [a["element"].capitalize() for a in ref_atoms]
print(f"crystal ligand heavy atoms: {len(ref_atoms)}")

center = ref_coords.mean(0).tolist()
box = {"center": center, "size": [20.0, 20.0, 20.0]}
(RAW / "box_8v8e.json").write_text(json.dumps(box, indent=1))

result, pose = dock_ligand(str(RAW / "8V8E_A_receptor.pdbqt"),
                           str(RAW / "7YY_ligand.pdbqt"),
                           box["center"], box["size"],
                           ligand_name="ensitrelvir", exhaustiveness=16,
                           n_poses=9, cpu=2)
print("affinities:", result.all_affinities)
(RAW / "7YY_8V8E_redock_pose.pdbqt").write_text(pose)

mob_coords, mob_elements = parse_pose_pdbqt(pose)
rmsd = assignment_rmsd(ref_coords, ref_elements, mob_coords, mob_elements)
print(f"transfer redocking RMSD (heavy-atom assignment): {rmsd:.3f} A")
verdict = "PASS" if rmsd < 2.0 else "FAIL"
print(f"protocol transfer gate (<2.0 A): {verdict}")
out = {"ligand": "ensitrelvir (7YY, S-217622)", "structure": "8V8E chain A",
       "resolution_A": 2.0, "temperature": "room temperature", "covalent": False,
       "construct": "catalytic domains (residues 6-190)",
       "removed_incomplete_residues": {"VAL86": 9.7, "VAL125": 14.6,
                                       "CYS128": 14.7, "MET130": 14.5},
       "best_affinity_kcal_mol": result.best_affinity,
       "all_affinities": result.all_affinities, "rmsd_A": rmsd,
       "gate": verdict, "exhaustiveness": 16,
       "reference": "7KX5/X7V redock RMSD 0.97 A (results/redock_7KX5.json)"}
(ROOT / "results/redock_8V8E_transfer.json").write_text(json.dumps(out, indent=1))
print("wrote results/redock_8V8E_transfer.json")
