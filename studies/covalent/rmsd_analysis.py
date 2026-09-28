#!/usr/bin/env python3
"""Lane 12 item 6 Part B: self-redock RMSD audit (prereg PREREG_COVALENT_BOUNDED_20260928.md).
v2 (pre-first-outcome machinery fix): v1 matched atoms by NAME, which cannot work -
DLG ligand atom names are element symbols (non-unique) while the crystal adduct uses
CCD names. Matching is now coordinate-free and deterministic:
  docked serial -> free-ligand SMILES atom (DLG REMARK SMILES IDX) -> crystal adduct
  atom (maximum common substructure, RDKit; elements compared, any bond order,
  ringMatchesRingOnly). RMSD is symmetry-corrected: minimum over all MCS
  automorphism assignments (the standard docking-RMSD convention, as in obrms).
Locked criterion (unchanged): best-energy pose heavy-atom RMSD <= 2.0 A vs the
crystallographic ligand in >= 2 of 3 seeds per complex; no superposition
(receptor frame retained)."""
import json, math, re
from rdkit import Chem
from rdkit.Chem import rdFMCS, rdDetermineBonds

COV = '/tmp/cov'
COMPLEXES = {'7vh8': '4WI', '7c6s': 'U5G'}
ENERGY_RE = re.compile(r'=\s*([-+]?[\d.]+(?:[eE][-+]?\d+)?)')

def crystal_ligand(pdb, resname):
    """heavy atoms {name: xyz} + PDB block of the ligand for bond perception"""
    atoms, block = {}, []
    for line in open(f'{COV}/{pdb}.pdb'):
        if line.startswith('HETATM') and line[17:20].strip() == resname and line[21] == 'A':
            block.append(line)
            name = line[12:16].strip()
            elem = line[76:78].strip() or re.sub(r'[^A-Za-z]', '', name)
            if elem.upper().startswith('H'):
                continue
            atoms[name] = tuple(float(line[30+i*8:38+i*8]) for i in range(3))
    return atoms, ''.join(block)

def parse_dlg(dlg):
    """(best_energy, {serial: xyz} for UNL ligand atoms, smiles, serial_by_smiles_idx)"""
    models, energy, atoms, in_model = [], None, {}, False
    smiles, idx_pairs = None, []
    for line in open(dlg):
        if 'REMARK SMILES IDX' in line:
            idx_pairs += [int(x) for x in line.split('IDX', 1)[1].split()]
        elif 'REMARK SMILES ' in line and smiles is None:
            smiles = line.split('REMARK SMILES', 1)[1].split()[0]
        if line.startswith('DOCKED: MODEL'):
            in_model, atoms, energy = True, {}, None
        elif line.startswith('DOCKED: ENDMDL'):
            models.append((energy, atoms)); in_model = False
        elif in_model:
            s = line[8:]
            if 'Estimated Free Energy of Binding' in s:
                m = ENERGY_RE.search(s)
                if m: energy = float(m.group(1))
            elif s.startswith('ATOM') and s[17:20].strip() == 'UNL':
                atoms[int(s[6:11])] = tuple(float(s[30+i*8:38+i*8]) for i in range(3))
    models = [(e, a) for e, a in models if e is not None and a]
    e_best, a_best = min(models, key=lambda t: t[0])
    serial_by_smiles = {idx_pairs[i]: idx_pairs[i+1] for i in range(0, len(idx_pairs), 2)}
    return e_best, a_best, smiles, serial_by_smiles, len(models)

def adduct_mol(block):
    m = Chem.MolFromPDBBlock(block, sanitize=False, removeHs=False)
    try:
        rdDetermineBonds.DetermineBonds(m, charge=0)
    except Exception:
        rdDetermineBonds.DetermineConnectivity(m)
    m.UpdatePropertyCache(strict=False)
    Chem.FastFindRings(m)
    return m

def symmetry_corrected_rmsd(free_smiles, serial_by_smiles, pose, adduct, ref):
    free = Chem.MolFromSmiles(free_smiles)
    amol = adduct
    mcs = rdFMCS.FindMCS([free, amol], atomCompare=rdFMCS.AtomCompare.CompareElements,
                         bondCompare=rdFMCS.BondCompare.CompareAny,
                         ringMatchesRingOnly=True, timeout=60)
    q = Chem.MolFromSmarts(mcs.smartsString)
    heavy_free = {a.GetIdx()+1 for a in free.GetAtoms() if a.GetAtomicNum() > 1}
    ref_names = [a for a in amol.GetAtoms() if a.GetAtomicNum() > 1]
    best, npair = None, 0
    for fm in free.GetSubstructMatches(q, maxMatches=5000):
        for am in amol.GetSubstructMatches(q, maxMatches=5000):
            pairs = []
            for fi, ai in zip(fm, am):
                sidx = fi + 1  # RDKit idx -> 1-based SMILES idx
                if sidx not in serial_by_smiles: continue
                mi = amol.GetAtomWithIdx(ai).GetMonomerInfo()
                name = mi.GetName().strip() if mi is not None else None
                if name is None or name not in ref: continue
                serial = serial_by_smiles[sidx]
                if serial not in pose: continue
                pairs.append((ref[name], pose[serial]))
            if len(pairs) > npair or (len(pairs) == npair and best is not None and
                (r := math.sqrt(sum((p[0][i]-p[1][i])**2 for p in pairs for i in range(3))/len(pairs))) < best):
                r = math.sqrt(sum((p[0][i]-p[1][i])**2 for p in pairs for i in range(3))/len(pairs))
                if len(pairs) > npair or r < best:
                    best, npair = r, len(pairs)
    return best, npair

out = {}
for tag, resname in COMPLEXES.items():
    ref, block = crystal_ligand(tag, resname)
    amol = adduct_mol(block)
    seeds = {}
    for s in (0, 1, 2):
        e_best, pose, smiles, sbs, nmodels = parse_dlg(f'{COV}/runs/{tag}_seed{s}.dlg')
        rmsd, nmatch = symmetry_corrected_rmsd(smiles, sbs, pose, amol, ref)
        seeds[str(s)] = {'best_energy': e_best, 'rmsd': round(rmsd, 3),
                         'atoms_matched': nmatch, 'n_models': nmodels}
    wins = sum(1 for v in seeds.values() if v['rmsd'] <= 2.0)
    out[tag] = {'ligand': resname, 'seeds': seeds, 'seeds_passing': wins,
                'redock_succeeds': wins >= 2}
print(json.dumps(out, indent=2))
