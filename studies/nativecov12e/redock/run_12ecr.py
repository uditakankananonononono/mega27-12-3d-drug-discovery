"""12E-CR confirmation redock - prereg docs/PREREG_12E_CONFIRMATION_REDOCK_20261007.md (locked at 989e2d0, pre-outcome).
Stages: gates (M1,G1-G5; no docking pose is read), dock (3 seeds x 2 complexes), analyze (frozen rule)."""
import sys, os, re, json, shutil, subprocess, hashlib, math
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = '/home/sandbox/work/12'
A12 = f'{ROOT}/studies/nativecov12a'
E12 = f'{ROOT}/studies/nativecov12e'
sys.path.insert(0, A12)
import numpy as np
from rdkit import Chem
from run_12a import (JOBS, build_matcher, sym_rmsd, lig_names, lig_pose_from_dlg, ocl_env, ADGPU, AG4, PARAMS, CAP)
from meeko.reactive import ReactiveAtomTyper

AD4 = f'{ROOT}/bin/ad4/autodock4'
MAPS = f'{HERE}/maps'          # regenerated Box 1 maps (gitignored with the 12E maps)
SPACING = 0.375
M1_REF = {'7c6s': -11.27, '7vh8': -12.56}     # committed 12E Pose B / Box 1 epdb energies
NPTS = {'7c6s': 72, '7vh8': 68}
CENTER = {'7c6s': (-19.915, -21.076, 0.485), '7vh8': (-19.054, 15.539, -31.610)}
TAGS = ['7c6s', '7vh8']        # test arm first

def sh(cmd, cwd, timeout=None, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)

def atom_lines(path):
    return [l for l in open(path) if l.startswith(('ATOM', 'HETATM'))]

def coords(lines):
    return np.array([[float(l[30:38]), float(l[38:46]), float(l[46:54])] for l in lines])

def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def build_input(tag):
    """redock input = 12A reactive ligand (types) with the committed 12E Pose B coordinates"""
    rea = open(f'{A12}/{tag}_lig_reactive.pdbqt').read().splitlines(keepends=True)
    pb = open(f'{E12}/{tag}_poseB.pdbqt').read().splitlines(keepends=True)
    assert len(rea) == len(pb)
    out = []
    for lr, lp in zip(rea, pb):
        if lr.startswith(('ATOM', 'HETATM')):
            assert lp.startswith(('ATOM', 'HETATM')) and lr[:30] == lp[:30] and lr[54:77] == lp[54:77], (lr, lp)
            out.append(lr[:30] + lp[30:54] + lr[54:])
        else:
            assert lr == lp or lr.split()[0] in ('REMARK',), (lr, lp)
            out.append(lr)
    p = f'{HERE}/{tag}_redock_input.pdbqt'
    open(p, 'w').write(''.join(out))
    return p

def regen_maps(tag):
    os.makedirs(MAPS, exist_ok=True)
    gpf = open(f'{A12}/{tag}_rec_rigid.gpf').read()
    gpf = gpf.replace('npts 64 64 64', f'npts {NPTS[tag]} {NPTS[tag]} {NPTS[tag]}')
    gpf = re.sub(r'^receptor ', f'receptor {A12}/', gpf, flags=re.M)
    gpf = re.sub(r'^parameter_file ', f'parameter_file {A12}/', gpf, flags=re.M)
    gp = f'{HERE}/{tag}_exp.gpf'
    open(gp, 'w').write(gpf)
    r = sh([AG4, '-p', gp, '-l', f'{HERE}/{tag}_exp.glg'], cwd=MAPS)  # relative map names so the fld lists bare filenames (as in 12A); cwd is the new redock/maps dir only
    return r.returncode

def epdb(tag, pose_path, center):
    gpf = open(f'{A12}/{tag}_rec_rigid.gpf').read()
    ltypes = re.search(r'^ligand_types (.*)$', gpf, re.M).group(1)
    maps = re.findall(r'^map (\S+)$', gpf, re.M)
    dpf = f"""autodock_parameter_version 4.2
outlev 1
parameter_file {A12}/boron-silicon-atom_par.dat
intelec
seed 12345
ligand_types {ltypes}
fld {MAPS}/{tag}_rec_rigid.maps.fld
""" + ''.join(f"map {MAPS}/{m}\n" for m in maps) + f"""elecmap {MAPS}/{tag}_rec_rigid.e.map
desolvmap {MAPS}/{tag}_rec_rigid.d.map
move {pose_path}
about {center[0]:.3f} {center[1]:.3f} {center[2]:.3f}
epdb
"""
    p = f'{HERE}/{tag}_M1.dpf'
    open(p, 'w').write(dpf)
    r = sh([AD4, '-p', p, '-l', f'{HERE}/{tag}_M1.dlg'], cwd=A12)
    txt = open(f'{HERE}/{tag}_M1.dlg').read()
    m = re.search(r'Final Intermolecular Energy\s*=\s*([+-]?[0-9.]+)', txt) or re.search(r'Total Intermolecular Interaction Energy\s*=\s*([+-]?[0-9.]+)', txt)
    return (float(m.group(1)) if m else None), r.returncode

def remap(tag):
    j = JOBS[tag]
    X = Chem.MolFromMolFile(j['sdf'], removeHs=True).GetConformer().GetPositions()
    lines = atom_lines(f'{A12}/{tag}_lig_reactive.pdbqt')
    P = coords(lines)
    perm = {}
    for i, l in enumerate(lines):
        if l.split()[-1].startswith('H') and not l.split()[-1].startswith('Hg'):
            continue
        d = np.linalg.norm(X - P[i], axis=1); k = int(d.argmin())
        assert d[k] < 1e-2, (tag, i)
        perm[i + 1] = k + 1
    assert len(set(perm.values())) == len(perm)
    return perm

def fixpose(perm, pose):
    return {perm[s]: xyz for s, xyz in pose.items() if s in perm}

def stage_gates():
    rt = ReactiveAtomTyper()
    out = {}
    for tag in TAGS:
        j = JOBS[tag]; g = {}
        # build input first (G5 part), then maps and M1
        inp = build_input(tag)
        pb = f'{E12}/{tag}_poseB.pdbqt'
        g['G5_input_coords_equal_poseB'] = bool(np.array_equal(coords(atom_lines(inp)), coords(atom_lines(pb))))
        g['autogrid_rc'] = regen_maps(tag)
        fld = open(f'{MAPS}/{tag}_rec_rigid.maps.fld').read()
        n = int(NPTS[tag])
        g['G5_map_header_ok'] = bool(re.search(rf'#NELEMENTS {n} {n} {n}', fld) and '#SPACING 0.375' in fld
                                     and ('#CENTER %.3f %.3f %.3f' % CENTER[tag]) in fld)
        g['maps_sha_vs_12e_e_map_equal'] = sha(f'{MAPS}/{tag}_rec_rigid.e.map') == sha(f'{E12}/maps/{tag}_rec_rigid.e.map') if os.path.exists(f'{E12}/maps/{tag}_rec_rigid.e.map') else None
        e, rc = epdb(tag, pb, coords(atom_lines(pb)).mean(0))
        g['M1_epdb'] = e; g['M1_ref'] = M1_REF[tag]
        g['M1_pass'] = bool(e is not None and rc == 0 and abs(e - M1_REF[tag]) <= 0.01)
        if not g['M1_pass']:
            out[tag] = g; json.dump(out, open(f'{HERE}/gates_12ecr.json', 'w'), indent=1)
            raise SystemExit('M1 FAILED - abort before any docking')
        # G1
        lig = inp
        ll = atom_lines(lig)
        order1 = [i for i, l in enumerate(ll) if rt.reactive_to_order.get(l.split()[-1]) == 1]
        ref_rea = atom_lines(f'{A12}/{tag}_lig_reactive.pdbqt')
        from rdkit import Chem as C
        m = C.MolFromMolFile(j['sdf'], sanitize=False, removeHs=False)
        w = m.GetConformer().GetAtomPosition(j['warhead'])
        hit = [i for i, l in enumerate(ref_rea) if abs(float(l[30:38]) - w.x) < 1e-3 and abs(float(l[38:46]) - w.y) < 1e-3 and abs(float(l[46:54]) - w.z) < 1e-3]
        names_same = lig_names(inp) == lig_names(f'{A12}/{tag}_lig_reactive.pdbqt')
        flex = atom_lines(f'{A12}/{tag}_rec_flex.pdbqt')
        flex_res = sorted({(l[17:20].strip(), l[21].strip(), l[22:26].strip()) for l in flex})
        def o1(tp):
            t = tp[1:] if len(tp) > 1 and tp[0].isdigit() else tp
            return rt.reactive_to_order.get(t) == 1
        rec_o1 = [l for l in flex if o1(l.split()[-1])]
        g['G1'] = {'lig_order1': order1, 'warhead_coord_hit_in_12A_prep': hit, 'names_identical': names_same, 'flex_residues': flex_res,
                   'rec_order1_atoms': [(l[12:16].strip(), l[17:20].strip(), l[22:26].strip()) for l in rec_o1]}
        g['G1_pass'] = bool(len(order1) == 1 and hit == order1 and names_same and len(flex_res) == 1 and flex_res[0][0] == 'CYS'
                            and flex_res[0][2] == '145' and len(rec_o1) == 1 and rec_o1[0][12:16].strip() == 'SG'
                            and order1[0] == j['warhead'] if False else
                            len(order1) == 1 and hit == order1 and names_same and len(flex_res) == 1 and flex_res[0][0] == 'CYS'
                            and flex_res[0][2] == '145' and len(rec_o1) == 1 and rec_o1[0][12:16].strip() == 'SG')
        # G2
        cfg = open(f'{A12}/{tag}_rec.reactive_config').read()
        lt = ll[order1[0]].split()[-1]; st = rec_o1[0].split()[-1]
        pair = None; bad = []; nchk = 0
        for l in cfg.splitlines():
            f = l.split()
            if len(f) == 7 and f[0] == 'intnbp_r_eps':
                if {f[5], f[6]} == {lt, st}:
                    pair = f
                if f[3] == '13':
                    if not (abs(float(f[1]) - 1.8) <= 1e-6 and abs(float(f[2]) - 2.5) <= 1e-6):
                        bad.append(l)
                    continue
                b1 = rt.get_basetype_and_order(f[5])[0]; b2 = rt.get_basetype_and_order(f[6])[0]
                if b1 is None or b2 is None:
                    continue
                if b1 in ('HD', 'F') or b2 in ('HD', 'F'):
                    er, ee = 0.01, 0.001
                else:
                    rij, eps = rt.get_scaled_parm(f[5], f[6]); er, ee = rij * 0.5, eps * 0.1662   # meeko r13/r14 scaling 0.5, coeff_vdw 0.1662
                nchk += 1
                if abs(er - float(f[1])) > 1e-6 or abs(ee - float(f[2])) > 1e-6:
                    bad.append(l)
        g['G2'] = {'pair_line': pair, 'n_scaled_lines_checked': nchk, 'n_mismatch': len(bad), 'mismatch_examples': bad[:5]}
        g['G2_pass'] = bool(pair is not None and pair[3] == '13' and pair[4] == '7' and abs(float(pair[1]) - 1.8) <= 1e-6 and abs(float(pair[2]) - 2.5) <= 1e-6 and not bad and nchk > 0)
        # G4 coordinate-identity remap self-map
        matcher = build_matcher(j); free, amol, q, ref, sdf2name = matcher
        perm = remap(tag); inv = {v: k for k, v in perm.items()}
        fm = free.GetSubstructMatch(q); am = amol.GetSubstructMatch(q)
        selfpose = {inv[fi + 1]: ref[sdf2name[ai]] for fi, ai in zip(fm, am)
                    if (fi + 1) in inv and sdf2name.get(ai) in ref}
        r0, n0 = sym_rmsd(j, matcher, fixpose(perm, selfpose))
        g['G4_self_rmsd'] = r0; g['G4_atoms'] = n0; g['G4_pass'] = bool(r0 is not None and r0 < 1e-6 and n0 > 0)
        # informational: RMSD of the Pose B input pushed through the same remap (matched atoms at crystal coordinates)
        Pin = coords(atom_lines(inp))
        rin, nin = sym_rmsd(j, matcher, fixpose(perm, {i + 1: tuple(p) for i, p in enumerate(Pin)}))
        g['info_input_poseB_rmsd_through_pipeline'] = rin; g['info_input_atoms'] = nin
        out[tag] = g
    # G3 engine smoke on Box 1 maps
    env = ocl_env()
    for tag in TAGS:
        cfgp = f'{MAPS}/{tag}_rec.reactive_config'; shutil.copyfile(f'{A12}/{tag}_rec.reactive_config', cfgp)
        shutil.copyfile(f'{A12}/{tag}_rec_flex.pdbqt', f'{MAPS}/{tag}_rec_flex.pdbqt')
        cmd = [ADGPU, '--lfile', f'{A12}/{tag}_lig_reactive_anchor.pdbqt', '--flexres', f'{MAPS}/{tag}_rec_flex.pdbqt',
               '--ffile', f'{MAPS}/{tag}_rec_rigid.maps.fld', '--import_dpf', cfgp, '--resnam', f'{HERE}/smoke_{tag}',
               '--nrun', '1', '--nev', '10000', '--ngen', '100', '--seed', '77000']
        r = sh(cmd, cwd=MAPS, timeout=CAP, env=env)
        ok = r.returncode == 0 and os.path.exists(f'{HERE}/smoke_{tag}.dlg')
        txt = open(f'{HERE}/smoke_{tag}.dlg').read() if ok else ''
        out[tag]['G3_rc'] = r.returncode
        out[tag]['G3_pass'] = bool(ok and 'DOCKED:' in txt)
        out[tag]['G3_reactive_types_echoed'] = bool(re.search(r'\b1S4\b', r.stdout + txt))
    json.dump(out, open(f'{HERE}/gates_12ecr.json', 'w'), indent=1)
    print(json.dumps(out, indent=1, default=str))
    ok = all(out[t][k] for t in TAGS for k in ('M1_pass', 'G1_pass', 'G2_pass', 'G3_pass', 'G4_pass', 'G5_input_coords_equal_poseB', 'G5_map_header_ok'))
    assert ok, 'GATE FAILURE - no docking'

def stage_dock():
    st_p = f'{HERE}/dock_status.json'
    status = json.load(open(st_p)) if os.path.exists(st_p) else {}
    env = ocl_env()
    for tag in TAGS:
        for s in (0, 1, 2):
            key = f'{tag}_seed{s}'
            if status.get(key, {}).get('dlg'):
                continue
            out = f'{HERE}/dock_{key}'
            cmd = [ADGPU, '--lfile', f'{HERE}/{tag}_redock_input.pdbqt', '--flexres', f'{MAPS}/{tag}_rec_flex.pdbqt',
                   '--ffile', f'{MAPS}/{tag}_rec_rigid.maps.fld', '--import_dpf', f'{MAPS}/{tag}_rec.reactive_config'] + PARAMS + ['--seed', str(77000 + s), '--resnam', out]
            import time; t0 = time.time()
            try:
                r = sh(cmd, cwd=MAPS, timeout=CAP, env=env)
                status[key] = {'rc': r.returncode, 'timeout': False, 'dlg': r.returncode == 0 and os.path.exists(out + '.dlg'), 'wall_s': round(time.time() - t0, 1)}
            except subprocess.TimeoutExpired:
                status[key] = {'rc': None, 'timeout': True, 'dlg': False, 'wall_s': round(time.time() - t0, 1)}
            json.dump(status, open(st_p, 'w'), indent=1)
            print('done', key, status[key], flush=True)
    print('ALL_DONE')

def stage_analyze():
    status = json.load(open(f'{HERE}/dock_status.json'))
    res = {}
    for tag in TAGS:
        j = JOBS[tag]; matcher = build_matcher(j); perm = remap(tag)
        names = lig_names(f'{HERE}/{tag}_redock_input.pdbqt')
        seeds = {}; complete = 0
        for s in (0, 1, 2):
            key = f'{tag}_seed{s}'; st = status.get(key, {})
            if not st.get('dlg'):
                seeds[str(s)] = {'machinery': 'timeout' if st.get('timeout') else 'rc=%s' % st.get('rc')}; continue
            pose, e, nm = lig_pose_from_dlg(f'{HERE}/dock_{key}.dlg', names)
            r, n = sym_rmsd(j, matcher, fixpose(perm, pose))
            seeds[str(s)] = {'best_energy': e, 'rmsd': round(r, 3), 'atoms_matched': n, 'n_models': nm, 'wall_s': st.get('wall_s')}
            complete += 1
        wins = sum(1 for v in seeds.values() if v.get('rmsd', 99) <= 2.0)
        res[tag] = {'seeds': seeds, 'seeds_complete': complete, 'machinery_incomplete': complete < 2,
                    'seeds_passing': wins, 'complex_pass': (wins >= 2) if complete >= 2 else None}
    if any(res[t]['machinery_incomplete'] for t in TAGS):
        cls = 'MACHINERY-INCOMPLETE'
    elif not res['7c6s']['complex_pass']:
        cls = 'NOT CONFIRMED'
    elif res['7vh8']['complex_pass']:
        cls = 'CONFIRMED'
    else:
        cls = 'CONTROL-DISCORDANT'
    out = {'prereg': 'docs/PREREG_12E_CONFIRMATION_REDOCK_20261007.md (989e2d020d65236d08baaeee2658bb6012413595)',
           'criterion': 'best-energy-pose heavy-atom symmetry-corrected RMSD (coordinate-identity remap, no superposition) <= 2.0 A in >= 2/3 seeds',
           'complexes': res, 'classification': cls}
    json.dump(out, open(f'{ROOT}/results/native_covalent_12e_redock.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))

if __name__ == '__main__':
    {'gates': stage_gates, 'dock': stage_dock, 'analyze': stage_analyze}[sys.argv[1]]()
