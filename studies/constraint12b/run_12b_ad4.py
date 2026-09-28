#!/usr/bin/env python3
"""12B constraint-guided placement, AD4 engine.
Amendment prereg docs/PREREG_CONSTRAINT_GUIDED_12B_AMENDMENT_ENGINE_20260928.md
(commit bab7ca0, pre-outcome). Gates G1-G3 run BEFORE any A2 outcome; abort on
any gate failure. RMSD machinery and decision rule carried over unchanged from
the original 12B lock (run_12b.py, commit bf923af)."""
import json, math, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_12b import JOBS, OUT, SEEDS, read_map, build_matcher, sym_rmsd, g2_audit, g3_validate

AD4 = '/home/sandbox/work/12/bin/ad4/autodock4'
PAR = f'{OUT}/AD4.1_bound.dat'
LIGTYPES = {'7vh8': {'true': ['C','F','HD','N','NA','OA'], 'cl': ['C','Cl','F','HD','N','NA','OA']},
            '7c6s': {'true': ['C','HD','N','OA'], 'cl': ['C','Cl','HD','N','OA']}}
TORSDOF = {'7vh8': 9, '7c6s': 11}

def dpf_text(tag, variant, s, mode, pose=None):
    j = JOBS[tag]
    types = LIGTYPES[tag][variant]
    L = ['autodock_parameter_version 4.2', 'outlev 1', f'parameter_file {PAR}', 'intelec',
         f'seed {77000+s} {88000+s}', 'ligand_types ' + ' '.join(types), f'fld {tag}_std.maps.fld']
    L += [f'map {tag}_std.{t}.map' for t in types]
    L += [f'elecmap {tag}_std.e.map', f'desolvmap {tag}_std.d.map',
          f'move {pose if mode == "epdb" else OUT + "/" + tag + "_lig_" + variant + ".pdbqt"}',
          'about %g %g %g' % tuple(j['center']),
          'tran0 random', 'quaternion0 random', 'dihe0 random', f'torsdof {TORSDOF[tag]}',
          'ga_pop_size 150', 'ga_num_evals 1000000', 'ga_num_generations 27000',
          'ga_elitism 1', 'ga_mutation_rate 0.02', 'ga_crossover_rate 0.8',
          'ga_window_size 10', 'ga_cauchy_alpha 0.0', 'ga_cauchy_beta 1.0', 'set_ga',
          'sw_max_its 300', 'sw_max_succ 4', 'sw_max_fail 4', 'sw_rho 1.0', 'sw_lb_rho 0.01',
          'ls_search_freq 0.06', 'set_sw1', 'unbound_model bound']
    L.append('epdb' if mode == 'epdb' else 'ga_run 10')
    if mode == 'dock': L.append('analysis')
    return '\n'.join(L) + '\n'

def run_ad4(dpf, dlg, cwd, timeout=900):
    with open(dlg, 'w') as fh:
        r = subprocess.run([AD4, '-p', dpf, '-l', os.path.basename(dlg)],
                           cwd=cwd, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout)
    assert r.returncode == 0, (dpf, r.returncode)

def g1_pose(tag):
    """Fixed Cl-typed gate pose: translate the ligand so the warhead (Cl) atom
    sits exactly on the locked SG target, making the expected well delta
    ~ -3.0 kcal/mol and the G1 gate sensitive (a centroid-anchored pose sits
    ~5 A away, where the expected delta is ~0 and the gate would be vacuous).
    Machinery refinement pre-outcome; the gate formulation is unchanged."""
    p = f'{OUT}/{tag}_g1_pose_cl.pdbqt'
    if not os.path.exists(p):
        sx, sy, sz = JOBS[tag]['sg']
        lines = open(f'{OUT}/{tag}_lig_cl.pdbqt').read().splitlines(keepends=True)
        pts = [(i, float(l[30:38]), float(l[38:46]), float(l[46:54]), l[77:79].strip())
               for i, l in enumerate(lines) if l.startswith(('ATOM', 'HETATM'))]
        cl = [q for q in pts if q[4] == 'Cl']
        assert len(cl) == 1
        _, wx, wy, wz, _ = cl[0]
        for i, x, y, z, _ in pts:
            l = lines[i]
            lines[i] = l[:30] + '%8.3f%8.3f%8.3f' % (x+sx-wx, y+sy-wy, z+sz-wz) + l[54:]
        open(p, 'w').write(''.join(lines))
    return p

def warhead_xyz(pose_path):
    for l in open(pose_path):
        if l.startswith(('ATOM', 'HETATM')) and l[77:79].strip() == 'Cl':
            return (float(l[30:38]), float(l[38:46]), float(l[46:54]))
    raise ValueError('no Cl in ' + pose_path)

def epdb_energy(dlg):
    """Full-precision intermolecular vdW+Hbond+desolv energy from the epdb report
    (the summary line prints only 3 significant figures, which cannot resolve
    the -3.0 kcal/mol well delta against a clash-dominated total)."""
    for l in open(dlg):
        if l.startswith('Total Intermolecular vdW + Hbond + desolv Energy'):
            return float(re.search(r'=\s*(-?[0-9.eE+-]+?)\s*kcal/mol', l).group(1))
    raise ValueError('no epdb energy in ' + dlg)

def trilin(vals, n, center, p, spacing=0.375):
    g = [(p[d]-center[d])/spacing + n//2 for d in range(3)]
    i0 = [int(math.floor(x)) for x in g]
    f = [g[d]-i0[d] for d in range(3)]
    t = 0.0
    for dk in (0, 1):
        for dj in (0, 1):
            for di in (0, 1):
                w = (f[0] if di else 1-f[0]) * (f[1] if dj else 1-f[1]) * (f[2] if dk else 1-f[2])
                t += w * vals[(i0[2]+dk)*n*n + (i0[1]+dj)*n + i0[0]+di]
    return t

def stage_gates():
    out = {}
    for tag, j in JOBS.items():
        bdir = f'{OUT}/biased_{tag}'
        g2 = g2_audit(tag, bdir)
        pose = g1_pose(tag)
        wh = warhead_xyz(pose)
        _, vu = read_map(f'{OUT}/{tag}_std.Cl.map')
        _, vb = read_map(f'{bdir}/{tag}_std.Cl.map')
        n = 65
        expected = trilin(vb, n, j['center'], wh) - trilin(vu, n, j['center'], wh)
        e = {}
        for label, d in (('u1', OUT), ('u2', OUT), ('b', bdir)):
            dpf = f'{d}/g1_{tag}_{label}.dpf'
            open(dpf, 'w').write(dpf_text(tag, 'cl', 0, 'epdb', pose=pose))
            run_ad4(dpf, f'{d}/g1_{tag}_{label}.dlg', d)
            e[label] = epdb_energy(f'{d}/g1_{tag}_{label}.dlg')
        matcher = build_matcher(j)
        r0, n0 = g3_validate(tag, j, matcher)
        obs_delta = e['b'] - e['u1']
        out[tag] = {'epdb_unmod_1': round(e['u1'], 4), 'epdb_unmod_2': round(e['u2'], 4),
                    'epdb_biased': round(e['b'], 4), 'observed_delta': round(obs_delta, 4),
                    'expected_delta': round(expected, 4),
                    'G1_deterministic': abs(e['u1']-e['u2']) < 1e-9,
                    'G1_abserr': round(abs(obs_delta-expected), 4),
                    'G1_pass': abs(e['u1']-e['u2']) < 1e-9 and abs(obs_delta-expected) <= 0.05,
                    'G2_noncl_diffs': g2, 'G2_pass': g2 == [],
                    'G3_self_rmsd': None if r0 is None else round(r0, 6), 'G3_atoms': n0,
                    'G3_pass': r0 is not None and r0 < 1e-6}
    json.dump(out, open(f'{OUT}/gates_ad4.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))
    assert all(v['G1_pass'] and v['G2_pass'] and v['G3_pass'] for v in out.values()), 'GATE FAILURE - no outcomes may be read'

def stage_write_dpfs():
    for tag in JOBS:
        for arm, variant in (('A0', 'true'), ('A1', 'cl'), ('A2', 'cl')):
            d = OUT if arm != 'A2' else f'{OUT}/biased_{tag}'
            for s in (0, 1, 2):
                open(f'{d}/12b_{tag}_{arm}_seed{s}.dpf', 'w').write(dpf_text(tag, variant, s, 'dock'))
    print('dpfs written')

def stage_dock():
    procs = []
    for tag in JOBS:
        for arm in ('A0', 'A1', 'A2'):
            d = OUT if arm != 'A2' else f'{OUT}/biased_{tag}'
            for s in (0, 1, 2):
                dpf = f'12b_{tag}_{arm}_seed{s}.dpf'
                dlg = f'{OUT}/dock_ad4_{tag}_{arm}_seed{s}.dlg'
                fh = open(dlg, 'w')
                procs.append((subprocess.Popen(['timeout', '900', AD4, '-p', dpf, '-l', dlg],
                                               cwd=d, stdout=fh, stderr=subprocess.STDOUT), fh, dlg))
    fails = []
    for p, fh, dlg in procs:
        rc = p.wait(); fh.close()
        print('done rc=%d %s' % (rc, dlg), flush=True)
        if rc != 0: fails.append((dlg, rc))
    assert not fails, fails

def best_pose_from_dlg(path):
    models, energies, cur, cur_e = [], [], [], None
    for line in open(path):
        if not line.startswith('DOCKED: '): continue
        s = line[8:]
        if s.startswith('MODEL'): cur = []; cur_e = None
        elif 'Estimated Free Energy of Binding' in s:
            cur_e = float(re.search(r'=\s*(-?[0-9.eE+-]+?)\s*kcal/mol', s).group(1))
        elif s.startswith(('ATOM', 'HETATM')):
            cur.append((float(s[30:38]), float(s[38:46]), float(s[46:54])))
        elif s.startswith('ENDMDL'):
            models.append(cur); energies.append(cur_e)
    assert models and all(e is not None for e in energies), path
    order = sorted(range(len(energies)), key=lambda i: energies[i])
    best = models[order[0]]
    return {k+1: xyz for k, xyz in enumerate(best)}, energies[order[0]], len(models)

def stage_analyze():
    res = {}
    for tag, j in JOBS.items():
        matcher = build_matcher(j)
        arms = {}
        for arm in ('A0', 'A1', 'A2'):
            seeds = {}
            for s in (0, 1, 2):
                pose, ebest, nmodels = best_pose_from_dlg(f'{OUT}/dock_ad4_{tag}_{arm}_seed{s}.dlg')
                r, npair = sym_rmsd(j, matcher, pose)
                seeds[str(s)] = {'best_energy': round(ebest, 3), 'rmsd': round(r, 3),
                                 'atoms_matched': npair, 'n_models': nmodels}
            wins = sum(1 for v in seeds.values() if v['rmsd'] <= 2.0)
            arms[arm] = {'seeds': seeds, 'seeds_passing': wins, 'complex_pass': wins >= 2}
        res[tag] = arms
    verdict = ('SUPPORTED' if all(res[t]['A2']['complex_pass'] for t in res)
               else 'NOT SUPPORTED' if not any(res[t]['A2']['complex_pass'] for t in res) else 'mixed')
    out = {'prereg': 'docs/PREREG_CONSTRAINT_GUIDED_12B_20260928.md',
           'amendment': 'docs/PREREG_CONSTRAINT_GUIDED_12B_AMENDMENT_ENGINE_20260928.md',
           'engine': 'autodock4 4.2.7.x (amendment: substitution from Vina 1.2.7, machinery failure)',
           'criterion': 'A2 best-energy-pose symmetry-corrected RMSD <= 2.0 A in >= 2/3 seeds per complex; both=SUPPORTED, one=mixed, zero=NOT SUPPORTED',
           'complexes': res, 'verdict': verdict}
    json.dump(out, open('/home/sandbox/work/12/results/constraint_guided_12b.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))

if __name__ == '__main__':
    {'gates': stage_gates, 'write_dpfs': stage_write_dpfs, 'dock': stage_dock, 'analyze': stage_analyze}[sys.argv[1]]()
