#!/usr/bin/env python3
"""12B constraint-guided placement: integrity gates + docking arms + locked RMSD analysis.
Prereg docs/PREREG_CONSTRAINT_GUIDED_12B_20260928.md (3d48644). Gates G1-G3 run BEFORE
any A2 outcome; script aborts if any gate fails."""
import json, math, os, re, shutil, subprocess, sys
from rdkit import Chem
from rdkit.Chem import rdFMCS, rdDetermineBonds
from vina import Vina

ROOT = '/home/sandbox/work/12'
COV = f'{ROOT}/studies/covalent'
OUT = f'{ROOT}/studies/constraint12b'
DEPTH, SIGMA = 3.0, 0.75
SEEDS = [77000, 77001, 77002]

JOBS = {
 '7vh8': dict(resname='4WI', warhead=30, sg=(-15.937, 18.658, -30.181),
              rec=f'{COV}/7vh8_rec_rigid.pdbqt', center=[-19.054, 15.539, -31.610],
              sdf=f'{COV}/nirmatrelvir.sdf', addsdf=f'{COV}/4WI.sdf', pdb=f'{COV}/7vh8.pdb'),
 '7c6s': dict(resname='U5G', warhead=27, sg=(-18.709, -22.655, 4.666),
              rec=f'{COV}/7c6s_rec_rigid.pdbqt', center=[-19.915, -21.076, 0.485],
              sdf=f'{COV}/boceprevir.sdf', addsdf=f'{COV}/U5G.sdf', pdb=f'{COV}/7c6s.pdb'),
}

def read_map(path):
    vals, head = [], []
    with open(path) as f:
        for line in f:
            if line.startswith(('GRID_', 'MACROMOLECULE', 'SPACING', 'NELEMENTS', 'CENTER')):
                head.append(line)
            else:
                vals += [float(x) for x in line.split()]
    return head, vals

def write_map(path, head, vals):
    with open(path, 'w') as f:
        f.writelines(head)
        for i in range(0, len(vals), 6):
            f.write(''.join('%13.5f' % v for v in vals[i:i+6]) + '\n')

def bias_maps(tag, sg, center, spacing=0.375, n=65):
    """biased map set: copy all, add Gaussian well to Cl map only."""
    bdir = f'{OUT}/biased_{tag}'
    os.makedirs(bdir, exist_ok=True)
    for f in os.listdir(OUT):
        if f.startswith(f'{tag}_std.') and (f.endswith('.map') or f.endswith('.fld') or f.endswith('.xyz')):
            shutil.copy(f'{OUT}/{f}', f'{bdir}/{f}')
    head, vals = read_map(f'{bdir}/{tag}_std.Cl.map')
    assert len(vals) == n**3, (tag, len(vals))
    cx, cy, cz = center
    idx = 0
    for k in range(n):
        z = cz + (k - n//2) * spacing
        for j in range(n):
            y = cy + (j - n//2) * spacing
            for i in range(n):
                x = cx + (i - n//2) * spacing
                d2 = (x-sg[0])**2 + (y-sg[1])**2 + (z-sg[2])**2
                vals[idx] += -DEPTH * math.exp(-d2 / (SIGMA**2))
                idx += 1
    write_map(f'{bdir}/{tag}_std.Cl.map', head, vals)
    return bdir

def g2_audit(tag, bdir):
    diffs = []
    for f in sorted(os.listdir(bdir)):
        if f.endswith('.map') and not f.endswith('.Cl.map'):
            a = open(f'{OUT}/{f}', 'rb').read(); b = open(f'{bdir}/{f}', 'rb').read()
            if a != b: diffs.append(f)
    return diffs

def fixed_pose_score(tag, maps_prefix=None):
    """G1: same randomized in-box pose scored via compute_vina_maps vs load_maps.
    Pose made once per complex (pre-outcome machinery) and cached."""
    pose_pdbqt = f'{OUT}/{tag}_g1_pose.pdbqt'
    if not os.path.exists(pose_pdbqt):
        # translate the input ligand so its heavy-atom centroid sits at the box
        # center; deterministic, in-box by construction (vina randomize proved
        # unreliable for far-out-of-box inputs).
        cx, cy, cz = JOBS[tag]['center']
        lines = open(f'{OUT}/{tag}_lig_true.pdbqt').read().splitlines(keepends=True)
        pts = [(i, float(l[30:38]), float(l[38:46]), float(l[46:54]))
               for i, l in enumerate(lines) if l.startswith(('ATOM', 'HETATM'))]
        mx = sum(p[1] for p in pts)/len(pts); my = sum(p[2] for p in pts)/len(pts); mz = sum(p[3] for p in pts)/len(pts)
        dx, dy, dz = cx-mx, cy-my, cz-mz
        for i, x, y, z in pts:
            l = lines[i]
            lines[i] = l[:30] + '%8.3f%8.3f%8.3f' % (x+dx, y+dy, z+dz) + l[54:]
        open(pose_pdbqt, 'w').write(''.join(lines))
    v = Vina(sf_name='vina', seed=77000, verbosity=0)
    v.set_receptor(JOBS[tag]['rec'])
    v.set_ligand_from_file(pose_pdbqt)
    if maps_prefix:
        v.load_maps(maps_prefix)
    else:
        v.compute_vina_maps(center=JOBS[tag]['center'], box_size=[24, 24, 24])
    return float(v.score()[0])

# ---- RMSD machinery (item-6 v2 convention, adapted to vina pdbqt poses) ----
def crystal_ligand(j):
    atoms, block = {}, []
    for line in open(j['pdb']):
        if line.startswith('HETATM') and line[17:20].strip() == j['resname'] and line[21] == 'A':
            block.append(line)
            name = line[12:16].strip()
            elem = line[76:78].strip() or re.sub(r'[^A-Za-z]', '', name)
            if elem.upper().startswith('H'): continue
            atoms[name] = tuple(float(line[30+i*8:38+i*8]) for i in range(3))
    return atoms, ''.join(block)

def adduct_mol(block):
    m = Chem.MolFromPDBBlock(block, sanitize=False, removeHs=False)
    try: rdDetermineBonds.DetermineBonds(m, charge=0)
    except Exception: rdDetermineBonds.DetermineConnectivity(m)
    m.UpdatePropertyCache(strict=False); Chem.FastFindRings(m)
    return m

def adduct_sdf_to_crystal_names(j, ref):
    """adduct SDF heavy-atom order -> crystal atom names (order alignment verified at prereg)."""
    m = Chem.MolFromMolFile(j['addsdf'], removeHs=True)
    heavy = [a.GetIdx() for a in m.GetAtoms() if a.GetAtomicNum() > 1]
    names = [n for n in ref]
    assert len(heavy) == len(names), (len(heavy), len(names))
    return {sdf_idx: names[k] for k, sdf_idx in enumerate(heavy)}

def build_matcher(j):
    ref, block = crystal_ligand(j)
    amol = adduct_mol(block)
    free = Chem.MolFromMolFile(j['sdf'], removeHs=True)
    mcs = rdFMCS.FindMCS([free, amol], atomCompare=rdFMCS.AtomCompare.CompareElements,
                         bondCompare=rdFMCS.BondCompare.CompareAny, ringMatchesRingOnly=True, timeout=60)
    q = Chem.MolFromSmarts(mcs.smartsString)
    sdf2name = adduct_sdf_to_crystal_names(j, ref)
    return free, amol, q, ref, sdf2name

def pose_from_pdbqt(path, model_rank=0):
    """best-energy model's heavy atoms {serial among ATOM lines (1-based): xyz} + energy list."""
    models, cur, energies = [], [], []
    for line in open(path):
        if line.startswith('MODEL'):
            cur = []
        elif line.startswith('ENDMDL'):
            models.append(cur)
        elif line.startswith(('ATOM', 'HETATM')):
            cur.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
        elif line.startswith('REMARK VINA RESULT'):
            energies.append(float(line.split()[3]))
    order = sorted(range(len(energies)), key=lambda i: energies[i])
    best = models[order[model_rank]]
    return {k+1: xyz for k, xyz in enumerate(best)}, energies[order[0]]

def sym_rmsd(j, matcher, pose):
    free, amol, q, ref, sdf2name = matcher
    best, npair = None, 0
    for fm in free.GetSubstructMatches(q, maxMatches=5000):
        for am in amol.GetSubstructMatches(q, maxMatches=5000):
            pairs = []
            for fi, ai in zip(fm, am):
                if free.GetAtomWithIdx(fi).GetAtomicNum() == 1: continue
                name = sdf2name.get(ai)
                if name is None or name not in ref: continue
                serial = fi + 1
                if serial not in pose: continue
                pairs.append((ref[name], pose[serial]))
            if len(pairs) >= npair and pairs:
                r = math.sqrt(sum((p[0][i]-p[1][i])**2 for p in pairs for i in range(3)) / len(pairs))
                if len(pairs) > npair or r < (best if best is not None else 1e9):
                    best, npair = r, len(pairs)
    return best, npair

def g3_validate(tag, j, matcher):
    """crystal adduct mapped onto itself must give RMSD 0.0."""
    ref, _ = crystal_ligand(j)
    free, amol, q, _, sdf2name = matcher
    pose = {}
    fm = free.GetSubstructMatch(q); am = amol.GetSubstructMatch(q)
    for fi, ai in zip(fm, am):
        name = sdf2name.get(ai)
        if name in ref: pose[fi+1] = ref[name]
    r, n = sym_rmsd(j, matcher, pose)
    return r, n

def dock_arm(tag, arm, seed):
    j = JOBS[tag]
    v = Vina(sf_name='vina', seed=seed, cpu=2, verbosity=0)
    v.set_receptor(j['rec'])
    if arm == 'A0':
        v.set_ligand_from_file(f'{OUT}/{tag}_lig_true.pdbqt')
        v.compute_vina_maps(center=j['center'], box_size=[24, 24, 24])
    elif arm == 'A1':
        v.set_ligand_from_file(f'{OUT}/{tag}_lig_cl.pdbqt')
        v.load_maps(f'{OUT}/{tag}_std')
    else:
        v.set_ligand_from_file(f'{OUT}/{tag}_lig_cl.pdbqt')
        v.load_maps(f'{OUT}/biased_{tag}/{tag}_std')
    v.dock(exhaustiveness=32, n_poses=20)
    outp = f'{OUT}/dock_{tag}_{arm}_seed{seed-77000}.pdbqt'
    v.write_poses(outp, n_poses=20, overwrite=True)
    return outp

if __name__ == '__main__':
    stage = sys.argv[1]
    if stage == 'gates':
        out = {}
        for tag, j in JOBS.items():
            bdir = bias_maps(tag, j['sg'], j['center'])
            g2 = g2_audit(tag, bdir)
            s_vina = fixed_pose_score(tag)
            s_maps = fixed_pose_score(tag, maps_prefix=f'{OUT}/{tag}_std')
            matcher = build_matcher(j)
            r0, n0 = g3_validate(tag, j, matcher)
            out[tag] = {'G1_score_compute_vina': round(s_vina, 4), 'G1_score_load_maps': round(s_maps, 4),
                        'G1_absdiff': round(abs(s_vina - s_maps), 4), 'G1_pass': abs(s_vina - s_maps) <= 0.05,
                        'G2_noncl_diffs': g2, 'G2_pass': g2 == [],
                        'G3_self_rmsd': None if r0 is None else round(r0, 6), 'G3_atoms': n0,
                        'G3_pass': r0 is not None and r0 < 1e-6}
        json.dump(out, open(f'{OUT}/gates.json', 'w'), indent=1)
        print(json.dumps(out, indent=1))
        assert all(v['G1_pass'] and v['G2_pass'] and v['G3_pass'] for v in out.values()), 'GATE FAILURE - no outcomes may be read'
    elif stage == 'dock':
        done = []
        for tag in JOBS:
            for arm in ('A0', 'A1', 'A2'):
                for seed in SEEDS:
                    p = dock_arm(tag, arm, seed)
                    done.append(p)
                    print('docked', p, flush=True)
    elif stage == 'analyze':
        res = {}
        for tag, j in JOBS.items():
            matcher = build_matcher(j)
            arms = {}
            for arm in ('A0', 'A1', 'A2'):
                seeds = {}
                for s in (0, 1, 2):
                    pose, ebest = pose_from_pdbqt(f'{OUT}/dock_{tag}_{arm}_seed{s}.pdbqt')
                    r, n = sym_rmsd(j, matcher, pose)
                    seeds[str(s)] = {'best_energy': round(ebest, 3), 'rmsd': round(r, 3), 'atoms_matched': n}
                wins = sum(1 for v in seeds.values() if v['rmsd'] <= 2.0)
                arms[arm] = {'seeds': seeds, 'seeds_passing': wins, 'complex_pass': wins >= 2}
            res[tag] = arms
        both = all(res[t]['A2']['complex_pass'] for t in res)
        anyp = any(res[t]['A2']['complex_pass'] for t in res)
        res['verdict'] = {'A2_both_pass': both, 'A2_any_pass': anyp,
                          'rule': 'SUPPORTED iff both; one = mixed as measured; zero = NOT SUPPORTED',
                          'label': 'SUPPORTED' if both else ('MIXED' if anyp else 'NOT SUPPORTED')}
        json.dump(res, open(f'{ROOT}/results/constraint_guided_12b.json', 'w'), indent=1)
        print(json.dumps(res, indent=1))
