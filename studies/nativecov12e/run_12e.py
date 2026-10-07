"""12E geometry/containment audit - prereg docs/PREREG_12E_GEOMETRY_CONTAINMENT_20261007.md (locked pre-outcome)."""
import sys, os, re, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '../nativecov12a')
sys.path.insert(0, A)
import numpy as np
from rdkit import Chem
from run_12a import JOBS, build_matcher, lig_names, OUT

AD4 = '/home/sandbox/work/12/bin/ad4/autodock4'
AG4 = '/home/sandbox/work/12/bin/ad4/autogrid4'
D5 = os.path.join(HERE, '../nativecov12d/d5')
MAPS = os.path.join(HERE, 'maps')
SPACING = 0.375
MARGIN = 1.0
D5_SCORES = {'7vh8': -10.39, '7c6s': 18.80}

def kabsch(P, Q):
    pc, qc = P.mean(0), Q.mean(0)
    H = (P - pc).T @ (Q - qc)
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1, 1, d]); R = Vt.T @ D @ U.T
    X = (R @ (P - pc).T).T + qc
    return R, pc, qc, float(np.sqrt(((X - Q) ** 2).sum(1).mean()))

def pdbqt_coords(lines):
    idx = [i for i, l in enumerate(lines) if l.startswith(('ATOM', 'HETATM'))]
    P = np.array([[float(l[30:38]), float(l[38:46]), float(l[46:54])] for l in (lines[i] for i in idx)])
    return idx, P

def write_pose(lines, idx, P, path):
    out = lines[:]
    for k, i in enumerate(idx):
        x, y, z = P[k]
        out[i] = lines[i][:30] + '%8.3f%8.3f%8.3f' % (x, y, z) + lines[i][54:]
    open(path, 'w').write(''.join(out))

def epdb(tag, pose_path, maps_dir, prefix, center):
    """Score-only epdb against maps in maps_dir (original OUT or expanded MAPS)."""
    gpf = open(f'{OUT}/{tag}_rec_rigid.gpf').read()
    ltypes = re.search(r'^ligand_types (.*)$', gpf, re.M).group(1)
    maps = re.findall(r'^map (\S+)$', gpf, re.M)
    dpf = f"""autodock_parameter_version 4.2
outlev 1
parameter_file {OUT}/boron-silicon-atom_par.dat
intelec
seed 12345
ligand_types {ltypes}
fld {maps_dir}/{tag}_rec_rigid.maps.fld
""" + ''.join(f"map {maps_dir}/{m}\n" for m in maps) + f"""elecmap {maps_dir}/{tag}_rec_rigid.e.map
desolvmap {maps_dir}/{tag}_rec_rigid.d.map
move {pose_path}
about {center[0]:.3f} {center[1]:.3f} {center[2]:.3f}
epdb
"""
    p = f'{HERE}/{tag}_{prefix}.dpf'
    open(p, 'w').write(dpf)
    r = subprocess.run([AD4, '-p', p, '-l', f'{HERE}/{tag}_{prefix}.dlg'],
                       capture_output=True, text=True, cwd=OUT)
    txt = open(f'{HERE}/{tag}_{prefix}.dlg').read() if os.path.exists(f'{HERE}/{tag}_{prefix}.dlg') else r.stdout + r.stderr
    m = re.search(r'Final Intermolecular Energy\s*=\s*([+-]?[0-9.]+)', txt) or re.search(r'Total Intermolecular Interaction Energy\s*=\s*([+-]?[0-9.]+)', txt)
    return (float(m.group(1)) if m else None), r.returncode

res = {}
for tag, j in JOBS.items():
    free, amol, q, ref, sdf2name = build_matcher(j)
    # crystal heavy atoms (D3 set) and containment metrics
    C = np.array(list(ref.values()))
    ctr = np.array(j['center'])
    offs = np.abs(C - ctr).max(0)
    maxoff = float(offs.max())
    npts = int(2 * np.ceil((maxoff + MARGIN) / SPACING))
    # Pose A: the committed D5 artifact, exact input to the D5 scores
    linesA = open(f'{D5}/{tag}_crystalfit.pdbqt').read().splitlines(keepends=True)
    idxA, PA = pdbqt_coords(linesA)
    # matched pdbqt-atom -> crystal pairs, same machinery as D5/D4b (first MCS match + coordinate identity)
    X = Chem.MolFromMolFile(j['sdf'], removeHs=True).GetConformer().GetPositions()
    # coordinate-identity mapping from the ORIGINAL C1 ligand (Pose A is a rigid fit,
    # so its coordinates cannot source the identity mapping)
    lines0 = open(f'{OUT}/{tag}_lig_std.pdbqt').read().splitlines(keepends=True)
    idx0, P0 = pdbqt_coords(lines0)
    perm = {}
    for k, i in enumerate(idx0):
        l = lines0[i]
        if l.split()[-1].startswith('H'):
            continue
        d = np.linalg.norm(X - P0[k], axis=1); mm = int(d.argmin())
        assert d[mm] < 1e-2, (tag, k)
        perm[k] = mm
    sdf2k = {m: k for k, m in perm.items()}
    fm = free.GetSubstructMatches(q, maxMatches=5000)[0]
    am = amol.GetSubstructMatches(q, maxMatches=5000)[0]
    pairs = [(sdf2k[fi], ref[sdf2name[ai]]) for fi, ai in zip(fm, am)
             if fi in sdf2k and sdf2name.get(ai) in ref]
    ks = [k for k, _ in pairs]; Q = np.array([c for _, c in pairs])
    # identity check: Pose A vs Pose B differ only in coordinate fields
    PB = PA.copy()
    for n, k in enumerate(ks):
        PB[k] = Q[n]
    fitB = float(np.sqrt(((PB[ks] - Q) ** 2).sum(1).mean()))
    # containment of both poses in both boxes (box1 halfwidth = npts*SPACING/2)
    half1 = npts * SPACING / 2.0
    def containment(P):
        o0 = np.abs(P - ctr) - 12.0
        o1 = np.abs(P - ctr) - half1
        return {'box0_n_outside': int((o0 > 0).any(1).sum()), 'box0_min_margin': round(float(-o0.max()), 3),
                'box1_n_outside': int((o1 > 0).any(1).sum()), 'box1_min_margin': round(float(-o1.max()), 3)}
    contA, contB = containment(PA), containment(PB)
    # expanded maps via autogrid4 (same receptor, spacing, center, parameter file; npts only)
    gpf = open(f'{OUT}/{tag}_rec_rigid.gpf').read()
    gpf = gpf.replace('npts 64 64 64', f'npts {npts} {npts} {npts}')
    gpf = gpf.replace('gridfld 7c6s_rec_rigid.maps.fld' if tag == '7c6s' else 'gridfld 7vh8_rec_rigid.maps.fld',
                      f'gridfld {MAPS}/{tag}_rec_rigid.maps.fld')
    gpf = re.sub(r'^receptor ', f'receptor {OUT}/', gpf, flags=re.M)
    gpf = re.sub(r'^parameter_file ', f'parameter_file {OUT}/', gpf, flags=re.M)
    gpf = re.sub(r'^map (\S+)$', lambda m: f'map {MAPS}/{m.group(1)}', gpf, flags=re.M)
    gpf = re.sub(r'^elecmap (\S+)$', lambda m: f'elecmap {MAPS}/{m.group(1)}', gpf, flags=re.M)
    gpf = re.sub(r'^dsolvmap (\S+)$', lambda m: f'dsolvmap {MAPS}/{m.group(1)}', gpf, flags=re.M)
    gp = f'{HERE}/{tag}_exp.gpf'
    open(gp, 'w').write(gpf)
    rg4 = subprocess.run([AG4, '-p', gp, '-l', f'{HERE}/{tag}_exp.glg'], capture_output=True, text=True, cwd=HERE)
    # G1: Pose A on Box 0 must reproduce D5
    eA0, rcA0 = epdb(tag, f'{D5}/{tag}_crystalfit.pdbqt', OUT, 'A_box0', PA.mean(0))
    g1 = (eA0 is not None) and abs(eA0 - D5_SCORES[tag]) <= 0.01
    res[tag] = {'npts_box1': npts, 'max_crystal_offset': round(maxoff, 3),
                'fit_rmsd_poseB_matched': round(fitB, 4), 'n_matched': len(ks),
                'containment_poseA': contA, 'containment_poseB': contB,
                'autogrid_rc': rg4.returncode, 'epdb': {'A_box0': {'e': eA0, 'rc': rcA0}},
                'g1_reproduce_d5': bool(g1)}
    if not g1:
        res[tag]['abort'] = 'G1 failed: Pose A/Box 0 did not reproduce D5; no further scores read'
        continue
    # write Pose B, then score the three remaining arms
    write_pose(linesA, idxA, PB, f'{HERE}/{tag}_poseB.pdbqt')
    eB0, rcB0 = epdb(tag, f'{HERE}/{tag}_poseB.pdbqt', OUT, 'B_box0', PB.mean(0))
    eA1, rcA1 = epdb(tag, f'{D5}/{tag}_crystalfit.pdbqt', MAPS, 'A_box1', PA.mean(0))
    eB1, rcB1 = epdb(tag, f'{HERE}/{tag}_poseB.pdbqt', MAPS, 'B_box1', PB.mean(0))
    res[tag]['epdb'].update({'B_box0': {'e': eB0, 'rc': rcB0}, 'A_box1': {'e': eA1, 'rc': rcA1},
                             'B_box1': {'e': eB1, 'rc': rcB1}})
    # identity check: Pose B lines equal Pose A except coordinate columns
    ident = all(la[:30] == lb[:30] and la[54:] == lb[54:]
                for la, lb in zip(linesA, open(f'{HERE}/{tag}_poseB.pdbqt').read().splitlines(keepends=True)))
    res[tag]['identity_poseB_vs_poseA'] = bool(ident)
    # plausibility vs pooled docked C1 (D5 rule)
    inters = []
    for s in (0, 1, 2):
        for l in open(f'{OUT}/dock_{tag}_C1_seed{s}.dlg'):
            m = re.search(r'Final Intermolecular Energy\s*=\s*(-?[0-9.]+)', l)
            if m:
                inters.append(float(m.group(1)))
    worst = max(inters)
    def plaus(e):
        return None if e is None else bool(e <= 0 and e <= worst)
    P = {k: plaus(v['e']) for k, v in res[tag]['epdb'].items()}
    res[tag]['docked_C1_worst'] = worst
    res[tag]['plausible'] = P
json.dump(res, open(os.path.join(HERE, '../../results/native_covalent_12e.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
