#!/usr/bin/env python3
"""Lane 12 item 6 Part B: self-redock RMSD audit (prereg PREREG_COVALENT_BOUNDED_20260928.md).
Reads the six DLGs, takes the best-energy docked pose per seed, computes heavy-atom
RMSD vs the crystallographic ligand (no superposition; receptor frame retained).
Locked criterion: RMSD <= 2.0 A in >= 2 of 3 seeds per complex."""
import json, math, re, sys

COV = '/tmp/cov'
COMPLEXES = {'7vh8': '4WI', '7c6s': 'U5G'}

def crystal_ligand(pdb, resname):
    atoms = {}
    for line in open(f'{COV}/{pdb}.pdb'):
        if line.startswith('HETATM') and line[17:20].strip() == resname and line[21] == 'A':
            name = line[12:16].strip()
            if name.startswith('H') or (len(name) > 1 and name[1] == 'H' and name[0].isdigit()):
                continue
            atoms[name] = tuple(float(line[30+i*8:38+i*8]) for i in range(3))
    return atoms

def best_pose(dlg):
    best_e, best = None, {}
    cur_e, cur = None, {}
    for line in open(dlg):
        if 'Estimated Free Energy of Binding' in line:
            m = re.search(r'=\s*(-?[\d.]+)', line)
            if m:
                if cur_e is None or float(m.group(1)) < cur_e:
                    pass
                cur_e = float(m.group(1))
        if line.startswith(('DOCKED: ATOM', 'DOCKED: HETATM')):
            name = line[16:20].strip() if False else line[12:20].split()[0] if False else None
        # parse model blocks
    return best_e, best

def parse_dlg_models(dlg):
    """Return list of (energy, {atom_name: xyz}) for each MODEL."""
    models = []
    energy = None
    atoms = {}
    in_model = False
    for line in open(dlg):
        if line.startswith('DOCKED: MODEL'):
            in_model, atoms = True, {}
        elif line.startswith('DOCKED: ENDMDL'):
            models.append((energy, atoms)); in_model = False; energy = None
        elif in_model:
            s = line[8:]  # strip 'DOCKED: '
            if 'Estimated Free Energy of Binding' in s:
                m = re.search(r'=\s*(-?[\d.]+)', s)
                if m: energy = float(m.group(1))
            elif s.startswith(('ATOM', 'HETATM')):
                name = s[12:16].strip()
                atoms[name] = tuple(float(s[30+i*8:38+i*8]) for i in range(3))
    return models

out = {}
for tag, resname in COMPLEXES.items():
    ref = crystal_ligand(tag, resname)
    seeds = {}
    for s in [0, 1, 2]:
        models = parse_dlg_models(f'{COV}/runs/{tag}_seed{s}.dlg')
        models = [(e, a) for e, a in models if e is not None and a]
        e_best, a_best = min(models, key=lambda t: t[0])
        common = [n for n in ref if n in a_best and not n.startswith('H')]
        rmsd = math.sqrt(sum((ref[n][i]-a_best[n][i])**2 for n in common for i in range(3)) / len(common))
        seeds[str(s)] = {'best_energy': e_best, 'rmsd': round(rmsd, 3), 'atoms_matched': len(common), 'n_models': len(models)}
    wins = sum(1 for v in seeds.values() if v['rmsd'] <= 2.0)
    out[tag] = {'ligand': resname, 'seeds': seeds, 'seeds_passing': wins,
                'redock_succeeds': wins >= 2}
print(json.dumps(out, indent=2))
