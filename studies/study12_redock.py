"""Study 12 phase 1: redocking validation. Dock JUN8-76-3A (X7V) back into its
own Mpro structure (7KX5) from a fresh ETKDG embedding; gate on heavy-atom
assignment-RMSD < 2.0 A vs the crystal pose."""
import json
import pathlib
import numpy as np
from rdkit import Chem

from drugdisc.prep import smiles_to_pdbqt, ligand_coords, hetatm_residues
from drugdisc.dock import dock_ligand
from drugdisc.geometry import parse_pose_pdbqt, assignment_rmsd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"

mol = Chem.MolFromMolFile(str(RAW / "X7V_ideal.sdf"), removeHs=True)
smiles = Chem.MolToSmiles(mol)
print("ligand SMILES:", smiles)
smiles_to_pdbqt(smiles, str(RAW / "X7V_ligand.pdbqt"))
print("ligand PDBQT written")

box = json.loads((RAW / "box_7kx5.json").read_text())
result, pose = dock_ligand(str(RAW / "7KX5_A_receptor.pdbqt"),
                           str(RAW / "X7V_ligand.pdbqt"),
                           box["center"], box["size"],
                           ligand_name="JUN8-76-3A", exhaustiveness=16,
                           n_poses=9, cpu=2)
print("affinities:", result.all_affinities)
(RAW / "X7V_redock_pose.pdbqt").write_text(pose)

ref_atoms = hetatm_residues(str(RAW / "7KX5.pdb"), "X7V", "A")
ref_coords = np.array([[a["x"], a["y"], a["z"]] for a in ref_atoms])
ref_elements = [a["element"].capitalize() for a in ref_atoms]
mob_coords, mob_elements = parse_pose_pdbqt(pose)
rmsd = assignment_rmsd(ref_coords, ref_elements, mob_coords, mob_elements)
print(f"redocking RMSD (heavy-atom assignment): {rmsd:.3f} A")
verdict = "PASS" if rmsd < 2.0 else "FAIL"
print(f"protocol validation gate (<2.0 A): {verdict}")
out = {"ligand": "JUN8-76-3A (X7V)", "structure": "7KX5",
       "best_affinity_kcal_mol": result.best_affinity,
       "all_affinities": result.all_affinities, "rmsd_A": rmsd,
       "gate": verdict, "exhaustiveness": 16}
(ROOT / "results/redock_7KX5.json").write_text(json.dumps(out, indent=1))
print("wrote results/redock_7KX5.json")
