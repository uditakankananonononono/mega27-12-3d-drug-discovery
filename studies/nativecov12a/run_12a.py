#!/usr/bin/env python3
"""12A native covalent engine - prereg docs/PREREG_NATIVE_COVALENT_12A_20260928.md
(commit 6222c72, pre-outcome). Engine: AutoDock-GPU v1.6 prebuilt linux_x64
OpenCL binary + POCL CPU runtime. Reactive docking (meeko 0.8.0 preparation),
the only native covalent method family per the meeko docs. Gates G1-G4 run
BEFORE any C2 outcome; abort on gate failure. RMSD criterion and decision rule
carried over unchanged from item 6 / 12B (run_12b.py machinery)."""
import json, math, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_12b import JOBS, SEEDS, build_matcher, sym_rmsd, g3_validate, crystal_ligand
from run_12b_ad4 import best_pose_from_dlg

ROOT = '/home/sandbox/work/12'
OUT = f'{ROOT}/studies/nativecov12a'
ADGPU = f'{ROOT}/bin/adgpu/adgpu'
AG4 = f'{ROOT}/bin/ad4/autogrid4'
MKL = '/home/sandbox/.local/bin/mk_prepare_ligand.py'
MKR = '/home/sandbox/.local/bin/mk_prepare_receptor.py'
POCL = f'{ROOT}/bin/pocl-prefix'
SMARTS = {'7vh8': '[C]#[N]', '7c6s': '[CX3](=O)[CX3](=O)'}   # unique match, warhead at match idx 1
PARAMS = ['--nrun', '10', '--nev', '1000000', '--ngen', '27000', '--psize', '150', '--lsit', '300']
CAP = 3600

def ocl_env():
    e = dict(os.environ)
    e['LD_LIBRARY_PATH'] = f'{POCL}/usr/lib/x86_64-linux-gnu:{POCL}/usr/lib/x86_64-linux-gnu/pocl:' + e.get('LD_LIBRARY_PATH', '')
    e['OCL_ICD_VENDORS'] = f'{POCL}/etc/OpenCL/vendors/pocl.icd'
    return e

def sh(cmd, cwd=OUT, timeout=None, env=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                       env=env or ocl_env())
    return r

def lig_names(path):
    return [l[12:16].strip() for l in open(path) if l.startswith(('ATOM', 'HETATM'))]

def stage_prep():
    for tag, j in JOBS.items():
        # C2 reactive ligand (SMARTS locked; unique match, warhead at match index 1)
        r = sh(['python3', MKL, '-i', j['sdf'], '-o', f'{OUT}/{tag}_lig_reactive.pdbqt',
                '--reactive_smarts', SMARTS[tag], '--reactive_smarts_idx', '1'])
        assert r.returncode == 0, r.stderr[-2000:]
        # C1 control ligand: reuse the committed item-6/12B default meeko prep
        shutil.copyfile(f'{ROOT}/studies/constraint12b/{tag}_lig_true.pdbqt', f'{OUT}/{tag}_lig_std.pdbqt')
        # receptor atoms via prody (chain A protein; waters/hetero/adduct removed)
        sh(['python3', '-c', f'''
import prody
a = prody.parsePDB("{j['pdb']}")
sel = a.select("chain A and not water and not hetero")
prody.writePDB("{OUT}/{tag}_rec_atoms.pdb", sel)
'''])
        # reactive receptor prep: reactive residue A:145 SG, flex Cys145, locked box
        c = j['center']
        r = sh(['python3', MKR, '-i', f'{OUT}/{tag}_rec_atoms.pdb', '-o', f'{OUT}/{tag}_rec',
                '-p', '-g', '--default_altloc', 'A', '-s', 'A:145=SG',
                '--box_center', '%.3f' % c[0], '%.3f' % c[1], '%.3f' % c[2],
                '--box_size', '24', '24', '24'])
        assert r.returncode == 0, r.stderr[-3000:]
        # lock the GPF grid exactly (npts 64, spacing 0.375, locked gridcenter)
        gpf = f'{OUT}/{tag}_rec_rigid.gpf'
        txt = open(gpf).read()
        txt = re.sub(r'^npts .*$', 'npts 64 64 64', txt, flags=re.M)
        txt = re.sub(r'^spacing .*$', 'spacing 0.375', txt, flags=re.M)
        txt = re.sub(r'^gridcenter .*$', 'gridcenter %.3f %.3f %.3f' % tuple(c), txt, flags=re.M)
        open(gpf, 'w').write(txt)
        r = sh([AG4, '-p', os.path.basename(gpf), '-l', f'{tag}_rec.glg'])
        assert r.returncode == 0, 'autogrid failed: ' + (r.stdout + r.stderr)[-2000:]
    print('prep done')

def reactive_types(pdbqt):
    ts = set()
    for l in open(pdbqt):
        if l.startswith(('ATOM', 'HETATM')):
            t = l[77:79].strip()
            if re.match(r'^[A-Z][a-z]?\d$', t):
                ts.add(t)
    return ts

def stage_gates():
    from meeko.reactive import ReactiveAtomTyper
    rt = ReactiveAtomTyper()
    out = {}
    for tag, j in JOBS.items():
        # G1 preparation integrity
        lig = f'{OUT}/{tag}_lig_reactive.pdbqt'
        names = lig_names(lig)
        rtypes = [(i + 1, l[77:79].strip()) for i, l in enumerate(open(lig))
                  if l.startswith(('ATOM', 'HETATM')) and re.match(r'^[A-Z][a-z]?\d$', l[77:79].strip())]
        g1_lig = (len(rtypes) == 1 and rtypes[0][0] == j['warhead'] + 1)
        flex = f'{OUT}/{tag}_rec_flex.pdbqt'
        flex_res = sorted({l[17:26].strip() for l in open(flex) if l.startswith(('ATOM', 'HETATM'))})
        rec_rt = reactive_types(flex)
        fld_maps = set(re.findall(r'variable \d+ \S+\.(\w+)\.map', open(f'{OUT}/{tag}_rec_rigid.maps.fld').read())) \
            if os.path.exists(f'{OUT}/{tag}_rec_rigid.maps.fld') else set()
        types_needed = {l[77:79].strip() for l in open(lig) if l.startswith(('ATOM', 'HETATM'))} | \
                       {l[77:79].strip() for l in open(f'{OUT}/{tag}_lig_std.pdbqt') if l.startswith(('ATOM', 'HETATM'))}
        base_needed = {rt.reactive_to_std_atype_mapping.get(t, t) for t in types_needed}
        g1 = g1_lig and flex_res == ['145 A'] and len(rec_rt) == 1
        # G2 reactive-channel scaled-parameter audit (1e-6)
        cfg = open(f'{OUT}/{tag}_rec.reactive_config').read()
        lt, st = rtypes[0][1], sorted(rec_rt)[0]
        rij, eps = rt.get_scaled_parm(lt, st)
        nums = [float(x) for x in re.findall(r'-?\d+\.\d+(?:[eE][+-]?\d+)?', cfg)]
        g2 = any(abs(v - rij) <= 1e-6 for v in nums) and any(abs(v - eps) <= 1e-6 for v in nums)
        # G4 self-RMSD (engine-independent)
        matcher = build_matcher(j)
        r0, n0 = g3_validate(tag, j, matcher)
        out[tag] = {'G1_lig_reactive_atom': rtypes, 'G1_flex_residues': flex_res,
                    'G1_rec_reactive_types': sorted(rec_rt), 'G1_pass': g1,
                    'G2_scaled_rij_expected': rij, 'G2_scaled_eps_expected': eps, 'G2_pass': g2,
                    'G4_self_rmsd': None if r0 is None else round(r0, 6), 'G4_atoms': n0,
                    'G4_pass': r0 is not None and r0 < 1e-6,
                    'map_types_present': sorted(fld_maps), 'types_needed': sorted(base_needed)}
    json.dump(out, open(f'{OUT}/gates_12a_pre.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))
    assert all(v['G1_pass'] and v['G2_pass'] and v['G4_pass'] for v in out.values()), 'GATE FAILURE - no outcomes may be read'

def anchor_pose(tag, j):
    """G3 smoke input: reactive ligand translated so its warhead sits on the
    crystallographic adduct warhead position (near-attack placement)."""
    p = f'{OUT}/{tag}_lig_reactive_anchor.pdbqt'
    if os.path.exists(p):
        return p
    matcher = build_matcher(j)
    add, _ = crystal_ligand(j)
    free2add = matcher['free2add'] if isinstance(matcher, dict) and 'free2add' in matcher else None
    # find adduct atom name paired with the free warhead via the MCS matcher
    wname = None
    if free2add:
        wname = free2add.get(j['warhead'])
    if wname is None:
        # fallback: nearest adduct atom to the locked SG target is the warhead
        sx, sy, sz = j['sg']
        wname = min(add, key=lambda n: sum((add[n][d] - (sx, sy, sz)[d]) ** 2 for d in range(3)))
    tx, ty, tz = add[wname]
    lines = open(f'{OUT}/{tag}_lig_reactive.pdbqt').read().splitlines(keepends=True)
    pts = [(i, float(l[30:38]), float(l[38:46]), float(l[46:54])) for i, l in enumerate(lines)
           if l.startswith(('ATOM', 'HETATM'))]
    wx, wy, wz = pts[j['warhead']][1:]
    for i, x, y, z in pts:
        l = lines[i]
        lines[i] = l[:30] + '%8.3f%8.3f%8.3f' % (x + tx - wx, y + ty - wy, z + tz - wz) + l[54:]
    open(p, 'w').write(''.join(lines))
    return p

def stage_smoke():
    """G3 engine smoke: minimal reactive run on the anchored near-attack input."""
    res = {}
    for tag, j in JOBS.items():
        pose = anchor_pose(tag, j)
        cmd = [ADGPU, '--lfile', pose, '--flexres', f'{OUT}/{tag}_rec_flex.pdbqt',
               '--ffile', f'{OUT}/{tag}_rec_rigid.maps.fld',
               '--import_dpf', f'{OUT}/{tag}_rec.reactive_config',
               '--resnam', f'smoke_{tag}', '--nrun', '1', '--nev', '10000', '--ngen', '100',
               '--seed', '77000']
        r = sh(cmd, timeout=CAP)
        dlg = f'{OUT}/smoke_{tag}.dlg'
        ok = r.returncode == 0 and os.path.exists(dlg)
        nmodels = 0
        if ok:
            try:
                _, _, nmodels = best_pose_from_dlg(dlg)
            except Exception:
                ok = False
        res[tag] = {'rc': r.returncode, 'n_models': nmodels, 'G3_pass': ok and nmodels >= 1}
    json.dump(res, open(f'{OUT}/gates_12a_smoke.json', 'w'), indent=1)
    print(json.dumps(res, indent=1))
    assert all(v['G3_pass'] for v in res.values()), 'SMOKE FAILURE - engine machinery not verified'

def lig_pose_from_dlg(path, names):
    """Best-energy LIGAND pose from a DLG that may also carry flex-residue
    atoms: two-pointer match of DOCKED: ATOM lines against the input ligand
    atom-name sequence (DLG writes ligand atoms in input order)."""
    models, energies, cur, cur_e = [], [], [], None
    for line in open(path):
        if not line.startswith('DOCKED: '):
            continue
        s = line[8:]
        if s.startswith('MODEL'):
            cur = []; cur_e = None
        elif 'Estimated Free Energy of Binding' in s:
            cur_e = float(re.search(r'=\s*(-?[0-9.eE+-]+?)\s*kcal/mol', s).group(1))
        elif s.startswith(('ATOM', 'HETATM')):
            cur.append((s[12:16].strip(), (float(s[30:38]), float(s[38:46]), float(s[46:54]))))
        elif s.startswith('ENDMDL'):
            models.append(cur); energies.append(cur_e)
    assert models and all(e is not None for e in energies), path
    order = sorted(range(len(energies)), key=lambda i: energies[i])
    best = models[order[0]]
    got, k = [], 0
    for nm, xyz in best:
        if k < len(names) and nm == names[k]:
            got.append(xyz); k += 1
    assert k == len(names), (path, k, len(names))
    return {i + 1: xyz for i, xyz in enumerate(got)}, energies[order[0]], len(models)

def stage_dock():
    status = {}
    for tag, j in JOBS.items():
        for arm in ('C1', 'C2'):
            for s in (0, 1, 2):
                key = f'{tag}_{arm}_seed{s}'
                out = f'{OUT}/dock_{key}'
                if arm == 'C2':
                    cmd = [ADGPU, '--lfile', f'{OUT}/{tag}_lig_reactive.pdbqt',
                           '--flexres', f'{OUT}/{tag}_rec_flex.pdbqt',
                           '--ffile', f'{OUT}/{tag}_rec_rigid.maps.fld',
                           '--import_dpf', f'{OUT}/{tag}_rec.reactive_config']
                else:
                    cmd = [ADGPU, '--lfile', f'{OUT}/{tag}_lig_std.pdbqt',
                           '--ffile', f'{OUT}/{tag}_rec_rigid.maps.fld']
                cmd += PARAMS + ['--seed', str(77000 + s), '--resnam', out]
                try:
                    r = sh(cmd, timeout=CAP)
                    status[key] = {'rc': r.returncode, 'timeout': False,
                                   'dlg': os.path.exists(out + '.dlg')}
                except subprocess.TimeoutExpired:
                    status[key] = {'rc': None, 'timeout': True, 'dlg': False}
                json.dump(status, open(f'{OUT}/dock_status.json', 'w'), indent=1)
                print('done', key, status[key], flush=True)
    print('ALL_DONE')

def stage_analyze():
    res = {}
    status = json.load(open(f'{OUT}/dock_status.json'))
    for tag, j in JOBS.items():
        matcher = build_matcher(j)
        arms = {}
        for arm in ('C1', 'C2'):
            variant = 'reactive' if arm == 'C2' else 'std'
            names = lig_names(f'{OUT}/{tag}_lig_{variant}.pdbqt')
            seeds, complete = {}, 0
            for s in (0, 1, 2):
                key = f'{tag}_{arm}_seed{s}'
                st = status.get(key, {})
                if not st.get('dlg'):
                    seeds[str(s)] = {'machinery': 'timeout' if st.get('timeout') else 'rc=%s' % st.get('rc')}
                    continue
                pose, ebest, nm = lig_pose_from_dlg(f'{OUT}/dock_{key}.dlg', names)
                r, npair = sym_rmsd(j, matcher, pose)
                seeds[str(s)] = {'best_energy': round(ebest, 3), 'rmsd': round(r, 3),
                                 'atoms_matched': npair, 'n_models': nm}
                complete += 1
            wins = sum(1 for v in seeds.values() if v.get('rmsd', 99) <= 2.0)
            arms[arm] = {'seeds': seeds, 'seeds_complete': complete,
                         'machinery_incomplete': complete < 2,
                         'seeds_passing': wins, 'complex_pass': wins >= 2 and complete == 3}
        res[tag] = arms
    incomplete = any(res[t]['C2']['machinery_incomplete'] for t in res)
    verdict = ('MACHINERY-INCOMPLETE' if incomplete
               else 'SUPPORTED' if all(res[t]['C2']['complex_pass'] for t in res)
               else 'NOT SUPPORTED' if not any(res[t]['C2']['complex_pass'] for t in res) else 'mixed')
    out = {'prereg': 'docs/PREREG_NATIVE_COVALENT_12A_20260928.md',
           'engine': 'AutoDock-GPU v1.6 prebuilt linux_x64 OpenCL + POCL CPU runtime; meeko 0.8.0 reactive preparation (disclosed prebuilt binary)',
           'criterion': 'C2 best-energy-pose symmetry-corrected RMSD <= 2.0 A in >= 2/3 completed seeds per complex; both=SUPPORTED, one=mixed, zero=NOT SUPPORTED; <2 complete seeds = MACHINERY-INCOMPLETE',
           'complexes': res, 'verdict': verdict}
    json.dump(out, open(f'{ROOT}/results/native_covalent_12a.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))

if __name__ == '__main__':
    {'prep': stage_prep, 'gates': stage_gates, 'smoke': stage_smoke,
     'dock': stage_dock, 'analyze': stage_analyze}[sys.argv[1]]()
