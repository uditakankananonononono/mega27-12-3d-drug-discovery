"""12D diagnostics D1-D4 (prereg docs/PREREG_12D_SETUP_ARTIFACT_20261002.md, locked 5701ab5)."""
import json, os, sys, glob
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from run_12a import JOBS, build_matcher, sym_rmsd, lig_names, OUT
import run_12c_lib as L
res = {}
for tag, j in JOBS.items():
    free, amol, q, ref, sdf2name = matcher = build_matcher(j)
    r = {}
    # D1: crystal coordinates on free-ligand serials via MCS matches (take the match set giving the
    # most paired atoms; the sym_rmsd search picks the best mapping)
    pose, npair_max = {}, 0
    for fm in free.GetSubstructMatches(q, maxMatches=5000)[:1]:
        for am in amol.GetSubstructMatches(q, maxMatches=5000)[:1]:
            for fi, ai in zip(fm, am):
                nm = sdf2name.get(ai)
                if nm in ref: pose[fi + 1] = ref[nm]
    rm, npair = sym_rmsd(j, matcher, pose)
    r['D1_self_rmsd'] = None if rm is None else round(rm, 6); r['D1_atoms'] = npair
    r['D1_pass'] = rm is not None and rm <= 0.05
    # D2: receptor atoms vs crystal pdb
    cry = {}
    for l in open(j['pdb']):
        if l.startswith(('ATOM', 'HETATM')) and l[17:20].strip() != j['resname']:
            cry[(l[21], l[17:20].strip(), l[22:26].strip(), l[12:16].strip(), l[16].strip() or 'A' if False else l[12:16].strip())] = None
    cryx = {}
    for l in open(j['pdb']):
        if l.startswith('ATOM'):
            key = (l[21], l[17:20].strip(), l[22:26].strip(), l[12:16].strip())
            if key not in cryx: cryx[key] = (float(l[30:38]), float(l[38:46]), float(l[46:54]))
    nmatch = nmiss = 0; maxd = 0.0
    for l in open(f'{OUT}/{tag}_rec_atoms.pdb'):
        if l.startswith(('ATOM', 'HETATM')):
            key = (l[21], l[17:20].strip(), l[22:26].strip(), l[12:16].strip())
            xyz = (float(l[30:38]), float(l[38:46]), float(l[46:54]))
            if key in cryx:
                nmatch += 1; maxd = max(maxd, float(np.linalg.norm(np.array(xyz) - np.array(cryx[key]))))
            else: nmiss += 1
    r['D2_matched'] = nmatch; r['D2_unmatched'] = nmiss; r['D2_max_dev'] = round(maxd, 4)
    r['D2_pass'] = nmatch > 0 and maxd <= 0.05
    # D3 box
    c = np.array(j['center']); P = np.array(list(ref.values()))
    half = np.abs(P - c).max(axis=0)
    margin = 12.0 - half
    r['D3_max_abs_offset_xyz'] = [round(float(x), 3) for x in half]
    r['D3_min_margin'] = round(float(margin.min()), 3)
    r['D3_n_outside'] = int((np.abs(P - c) > 12.0).any(axis=1).sum()); r['D3_n_atoms'] = len(P)
    r['D3_pass'] = bool(margin.min() >= 1.0)
    # D4 descriptive
    d4 = {}
    cc = P.mean(axis=0)
    ref_idx = {}
    for arm in ('C1', 'C2'):
        names = lig_names(f'{OUT}/{tag}_lig_{"reactive" if arm=="C2" else "std"}.pdbqt')
        offs, tr = [], []
        for s in (0, 1, 2):
            for p, e in L.all_models(f'{OUT}/dock_{tag}_{arm}_seed{s}.dlg', names):
                pc = np.mean([v for v in p.values()], axis=0)
                offs.append(pc - cc)
                # translation-only: shift pose so its centroid matches crystal centroid (all ligand atoms)
                p2 = {k: tuple(np.array(v) - pc + cc) for k, v in p.items()}
                rr, _ = sym_rmsd(j, matcher, p2); tr.append(rr)
        offs = np.array(offs); mm = np.linalg.norm(offs.mean(axis=0)); ma = np.linalg.norm(offs, axis=1).mean()
        d4[arm] = {'mean_offset_vec': [round(float(x), 2) for x in offs.mean(axis=0)], 'mean_offset_mag': round(float(mm), 3),
                   'mean_abs_offset': round(float(ma), 3), 'ratio': round(float(mm / ma), 3),
                   'common_direction_flag': bool(mm >= 0.8 * ma),
                   'translation_aligned_rmsd_min': round(min(tr), 3), 'translation_aligned_rmsd_median': round(sorted(tr)[len(tr)//2], 3)}
    r['D4'] = d4
    res[tag] = r
res['ARTIFACT_FOUND'] = any(not (res[t]['D1_pass'] and res[t]['D2_pass'] and res[t]['D3_pass']) for t in JOBS)
json.dump(res, open(os.path.join(os.path.dirname(__file__), '../../results/native_covalent_12d.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
