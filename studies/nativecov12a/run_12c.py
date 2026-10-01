"""12C: sampling vs scoring on existing 12A poses (prereg docs/PREREG_12C_...)."""
import json, re, sys, os
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)) if False else os.path.dirname(__file__))
import run_12a as A
from run_12a import JOBS, build_matcher, sym_rmsd, lig_names, OUT

def all_models(path, names):
    models, energies, cur, cur_e = [], [], [], None
    for line in open(path):
        if not line.startswith('DOCKED: '): continue
        s = line[8:]
        if s.startswith('MODEL'): cur = []; cur_e = None
        elif 'Estimated Free Energy of Binding' in s:
            cur_e = float(re.search(r'=\s*(-?[0-9.eE+-]+?)\s*kcal/mol', s).group(1))
        elif s.startswith(('ATOM', 'HETATM')):
            cur.append((s[12:16].strip(), (float(s[30:38]), float(s[38:46]), float(s[46:54]))))
        elif s.startswith('ENDMDL'): models.append(cur); energies.append(cur_e)
    out = []
    for m, e in zip(models, energies):
        got, k = [], 0
        for nm, xyz in m:
            if k < len(names) and nm == names[k]: got.append(xyz); k += 1
        assert k == len(names)
        out.append(({i + 1: xyz for i, xyz in enumerate(got)}, e))
    return out

res = {}
for tag, j in JOBS.items():
    matcher = build_matcher(j)
    res[tag] = {}
    for arm in ('C1', 'C2'):
        names = lig_names(f'{OUT}/{tag}_lig_{"reactive" if arm=="C2" else "std"}.pdbqt')
        pool = []
        for s in (0, 1, 2):
            for pose, e in all_models(f'{OUT}/dock_{tag}_{arm}_seed{s}.dlg', names):
                r, _ = sym_rmsd(j, matcher, pose)
                pool.append((e, r, s))
        pool.sort(key=lambda x: x[0])
        rm = [p[1] for p in pool]
        i = min(range(len(pool)), key=lambda k: rm[k])
        res[tag][arm] = {'n_poses': len(pool), 'min_rmsd': round(rm[i], 3), 'min_rmsd_energy': pool[i][0],
                         'min_rmsd_energy_rank': i + 1, 'top1_rmsd': round(rm[0], 3),
                         'n_le_2.0': sum(r <= 2.0 for r in rm), 'n_le_3.0': sum(r <= 3.0 for r in rm),
                         'median_rmsd': round(sorted(rm)[len(rm)//2], 3),
                         'q1_sampling_adequate': rm[i] <= 2.0,
                         'q2_scoring_failure': (rm[i] <= 2.0 and i + 1 > 3)}
json.dump(res, open(os.path.join(os.path.dirname(__file__), '../../results/native_covalent_12c.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
