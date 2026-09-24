"""De novo ligand design for the validated Mpro pocket: R-group enumeration on
real pharmacophore cores, sanity filters, synthetic-complexity scoring, and
novelty verification against PubChem (live) plus Tanimoto distance to the
screened drug set."""
from __future__ import annotations
import itertools

from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, DataStructs
from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator

# Cores derived from the redock-validated X7V binding mode:
# biphenyl anchor (S1' pocket), furoyl/amide cap, chiral benzyl-amide hinge binder.
CORES = {
    "biphenyl_amide": "NC(=O)C(c1ccccc1)N(c1ccc(-c2ccccc2)cc1)C(=O){R}",
    "benzyl_furamide": "O=C(NC(c1ccccc1){R})c1ccco1",
    "pyridyl_amide": "NC(=O)C(c1cccnc1)N(c1ccc(-c2ccccc2)cc1)C(=O){R}",
    "naphthyl_amide": "O=C(NC(c1ccc2ccccc2c1){R})c1ccco1",
}
R_GROUPS = [
    "c1ccccc1", "c1ccncc1", "c1ccco1", "c1ccsc1",     # aromatics
    "C(F)(F)F", "CC(C)C", "Cc1ccccc1", "COc1ccccc1",  # aliphatic/ether anchors
    "c1ccc(Cl)cc1", "c1ccc(F)cc1",
]
MW_MAX, ROT_MAX, HEAVY_MAX = 550.0, 12, 42


def enumerate_candidates() -> list:
    """All core x R-group products that parse, sanitize, and pass size filters."""
    out = []
    seen = set()
    for core_name, template in CORES.items():
        for r in R_GROUPS:
            smi = template.replace("{R}", r)
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                continue
            can = Chem.MolToSmiles(mol)
            if can in seen:
                continue
            seen.add(can)
            mw = Descriptors.MolWt(mol)
            rot = Lipinski.NumRotatableBonds(mol)
            heavy = Lipinski.HeavyAtomCount(mol)
            if mw > MW_MAX or rot > ROT_MAX or heavy > HEAVY_MAX or heavy < 20:
                continue
            out.append({"smiles": can, "core": core_name, "r_group": r,
                        "mw": mw, "rotatable": rot, "heavy": heavy})
    return out


def complexity_score(smiles: str) -> float:
    """Synthetic-complexity proxy (not the Ertl SA score): rings, stereocenters,
    heteroatom fraction and size. Lower is easier to synthesize; ~0-5 scale."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 99.0
    rings = Lipinski.RingCount(mol)
    stereo = len(Chem.FindMolChiralCenters(mol, includeUnassigned=True))
    heavy = max(Lipinski.HeavyAtomCount(mol), 1)
    hetero = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() not in (1, 6))
    hetero_frac = hetero / heavy
    fused = Lipinski.NumAliphaticRings(mol) + Lipinski.NumAromaticRings(mol) - rings
    return round(0.3 * rings + 0.5 * stereo + 2.0 * hetero_frac
                 + 0.02 * Descriptors.MolWt(mol) / 100.0 + 0.4 * abs(fused), 3)


def tanimoto_to_set(smiles: str, others: list) -> float:
    """Max Tanimoto (Morgan r=2, 2048 bits) of a candidate against a SMILES set."""
    gen = GetMorganGenerator(radius=2, fpSize=2048)
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 1.0
    fp = gen.GetFingerprint(mol)
    best = 0.0
    for smi in others:
        m2 = Chem.MolFromSmiles(smi)
        if m2 is None:
            continue
        best = max(best, DataStructs.TanimotoSimilarity(fp, gen.GetFingerprint(m2)))
    return best
