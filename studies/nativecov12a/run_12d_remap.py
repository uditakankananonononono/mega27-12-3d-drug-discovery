"""12D amendment 2 / D7: corrected PDBQT-serial -> SDF-index mapping by coordinate identity."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from rdkit import Chem
from run_12a import JOBS, build_matcher, sym_rmsd, lig_names, OUT, lig_pose_from_dlg
import run_12c_lib as L
res = {}
for tag, j in JOBS.items():
    matcher = build_matcher(j)
    X = Chem.MolFromMolFile(j['sdf'], removeHs=True).GetConformer().GetPositions()
    res[tag] = {}
    for arm in ('C1', 'C2'):
        v = 'reactive' if arm == 'C2' else 'std'
        lines = [l for l in open(f'{OUT}/{tag}_lig_{v}.pdbqt') if l.startswith(('ATOM', 'HETATM'))]
        P = np.array([[float(l[30:38]), float(l[38:46]), float(l[46:54])] for l in lines])
        perm = {}
        for i, l in enumerate(lines):
            if l.split()[-1].startswith('H') and not l.split()[-1].startswith(('Hg',)):
                continue
            d = np.linalg.norm(X - P[i], axis=1); k = int(d.argmin())
            assert d[k] < 1e-2, (tag, arm, i)
            perm[i + 1] = k + 1
        assert len(set(perm.values())) == len(perm)
        names = lig_names(f'{OUT}/{tag}_lig_{v}.pdbqt')
        def fix(pose): return {perm[s]: xyz for s, xyz in pose.items() if s in perm}
        seeds = {}; pool = []
        for s in (0, 1, 2):
            ms = L.all_models(f'{OUT}/dock_{tag}_{arm}_seed{s}.dlg', names)
            rr = []
            for pose, e in ms:
                r, n = sym_rmsd(j, matcher, fix(pose)); rr.append((e, r))
            rr.sort(key=lambda x: x[0]); pool += rr
            seeds[str(s)] = {'best_energy': rr[0][0], 'rmsd_corrected': round(rr[0][1], 3), 'atoms': n}
        pool.sort(key=lambda x: x[0]); rm = [p[1] for p in pool]
        wins = sum(1 for v_ in seeds.values() if v_['rmsd_corrected'] <= 2.0)
        res[tag][arm] = {'seeds': seeds, 'seeds_passing': wins, 'complex_pass': wins >= 2,
                         'pooled_min_rmsd': round(min(rm), 3), 'pooled_median': round(sorted(rm)[len(rm) // 2], 3),
                         'pooled_n_le_2': sum(r <= 2.0 for r in rm), 'top1_pooled_rmsd': round(rm[0], 3)}
json.dump(res, open(os.path.join(os.path.dirname(__file__), '../../results/native_covalent_12d_remap.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
