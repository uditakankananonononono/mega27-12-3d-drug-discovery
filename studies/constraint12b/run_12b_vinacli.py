#!/usr/bin/env python3
"""12B constraint-guided placement, ORIGINAL lock 3d48644, Vina 1.2.7 engine
built from source (option (b), parent adjudication 2026-09-28 09:15 IST).
The original prereg docs/PREREG_CONSTRAINT_GUIDED_12B_20260928.md stands and
has never had a valid execution; no new prereg required.

Pre-outcome machinery notes (documented in the runlog before any outcome):
- Root cause of the 08:02 blocker, now understood from the 1.2.7 source: with
  sf_name vina, load_maps (cache::read) discovers map files by X-Score type
  names (<prefix>.C_H.map, <prefix>.Cl_H.map, ...), not AD4 type names. The
  wheel was not defective; the source-built binary behaves identically.
- The locked AD4 map VALUES are unchanged. XS-named views are byte-identical
  copies so each ligand atom samples the map of its AD4 type, exactly the
  locked semantics: C_H/C_P <- C.map; N_P/N_D <- N.map; N_A/N_DA <- NA.map;
  O_P/O_D/O_A/O_DA <- OA.map; F_H <- F.map; Cl_H <- Cl.map (biased set:
  Cl_H carries the locked Gaussian well). The well stays on the Cl map only.
- CLI front-end (vina --maps / --score_only) is the same engine code paths as
  the locked python API (load_maps / score / dock). Seeds 77000+s,
  exhaustiveness 32, n_poses 20, cpu 2, 300 s cap per run, arms A0/A1/A2 and
  the G1-G3 / decision-rule formulations are exactly the locked ones.
Gates G1-G3 run BEFORE any A2 outcome; script aborts if any gate fails."""
import json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_12b import JOBS, OUT, SEEDS, build_matcher, sym_rmsd, g2_audit, g3_validate, read_map
from run_12b_ad4 import g1_pose, warhead_xyz, trilin

VINA = '/home/sandbox/work/12/src/AutoDock-Vina/build/linux/release/vina'
XS_FROM_AD4 = {'C_H': 'C', 'C_P': 'C', 'N_P': 'N', 'N_D': 'N', 'N_A': 'NA', 'N_DA': 'NA',
               'O_P': 'OA', 'O_D': 'OA', 'O_A': 'OA', 'O_DA': 'OA', 'F_H': 'F', 'Cl_H': 'Cl'}

def build_xs_views():
    """Byte-identical XS-named views of the locked AD4 map sets (values unchanged)."""
    for tag in JOBS:
        for kind, src_dir in (('std', OUT), ('biased', f'{OUT}/biased_{tag}')):
            d = f'{OUT}/xs{kind}_{tag}'
            os.makedirs(d, exist_ok=True)
            for xs, ad in XS_FROM_AD4.items():
                src = f'{src_dir}/{tag}_std.{ad}.map'
                if os.path.exists(src):
                    shutil.copyfile(src, f'{d}/{tag}_xs.{xs}.map')
    print('xs views built')


def inbox_gate_pose(tag, margin=0.5):
    """Vina cache scoring hard-errors when any ligand atom lies outside the map
    grid box. The committed anchored gate pose (warhead exactly on the SG
    target) is used unchanged when fully in-box (7vh8); otherwise it is rotated
    rigidly ABOUT THE WARHEAD (warhead stays exactly on the SG target) by the
    first deterministic axis/angle candidate that brings every atom inside the
    box with margin. Rotation-invariance of the gate: every non-warhead atom
    samples byte-identical maps in the unmodified and biased sets, so their
    contributions cancel in the delta; the expected delta (warhead-only) is
    unchanged. Pre-outcome machinery accommodation, disclosed in the runlog and
    the G1 amendment addendum."""
    import math as _m
    j = JOBS[tag]
    p_in = f'{OUT}/{tag}_g1_pose_cl.pdbqt'
    lines = open(p_in).read().splitlines(keepends=True)
    pts = [(i, float(l[30:38]), float(l[38:46]), float(l[46:54])) for i, l in enumerate(lines)
           if l.startswith(('ATOM', 'HETATM'))]
    wh = warhead_xyz(p_in)
    cx, cy, cz = j['center']; half = 12.0 - margin
    def fits(cs):
        return all(abs(c[0]-cx) <= half and abs(c[1]-cy) <= half and abs(c[2]-cz) <= half for c in cs)
    coords = [(x, y, z) for _, x, y, z in pts]
    if fits(coords):
        return p_in
    axes = []
    for a in (-1, 1):
        axes += [(a,0,0),(0,a,0),(0,0,a)]
        for b in (-1, 1):
            axes += [(a,b,0),(a,0,b),(0,a,b),(a,b,b),(a,b,-b),(a,-b,b)]
    axes = [v for v in {(round(x,6),round(y,6),round(z,6)) for x,y,z in axes}]
    def rot(c, ax, th):
        ux, uy, uz = ax; n = _m.sqrt(ux*ux+uy*uy+uz*uz); ux, uy, uz = ux/n, uy/n, uz/n
        x, y, z = c[0]-wh[0], c[1]-wh[1], c[2]-wh[2]
        ct, st = _m.cos(th), _m.sin(th)
        d = ux*x+uy*y+uz*z
        rx = x*ct + (uy*z-uz*y)*st + ux*d*(1-ct)
        ry = y*ct + (uz*x-ux*z)*st + uy*d*(1-ct)
        rz = z*ct + (ux*y-uy*x)*st + uz*d*(1-ct)
        return (rx+wh[0], ry+wh[1], rz+wh[2])
    for deg in range(5, 181, 5):
        for ax in sorted(axes):
            cs = [rot(c, ax, _m.radians(deg)) for c in coords]
            if fits(cs):
                out_p = f'{OUT}/{tag}_g1_pose_cl_inbox.pdbqt'
                out_lines = list(lines)
                for (i, _, _, _), c in zip(pts, cs):
                    l = out_lines[i]
                    out_lines[i] = l[:30] + '%8.3f%8.3f%8.3f' % c + l[54:]
                open(out_p, 'w').write(''.join(out_lines))
                w2 = warhead_xyz(out_p)
                assert all(abs(w2[d]-j['sg'][d]) < 2e-3 for d in range(3)), (w2, j['sg'])
                print('inbox pose for', tag, ': rotation', deg, 'deg about', ax, '->', out_p)
                return out_p
    raise RuntimeError('no in-box rotation found for ' + tag)

def run_vina(args, timeout=300):
    r = subprocess.run([VINA] + args, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError('vina failed: %s\n%s\n%s' % (args, r.stdout[-2000:], r.stderr[-2000:]))
    return r.stdout

def affinity(stdout):
    m = (re.search(r'Estimated Free Energy of Binding\s*:\s*(-?[0-9.eE+-]+)\s*\(kcal/mol\)', stdout)
         or re.search(r'Affinity:\s*(-?[0-9.eE+-]+)\s*\(kcal/mol\)', stdout))
    assert m, stdout[-1500:]
    return float(m.group(1))

def stage_gates():
    """Amended G1 (docs/PREREG_CONSTRAINT_GUIDED_12B_AMENDMENT_G1_20260928.md,
    committed pre-outcome): well-recovery gate. The anchored Cl-typed gate pose
    (warhead exactly on the locked SG target) is scored --score_only against the
    unmodified (twice; determinism) and biased XS map sets with the source-built
    binary; the observed delta must match the trilinear map-difference
    interpolation at the warhead within 0.05 kcal/mol (tolerance locked in the
    amendment). G2/G3 unchanged. Aborts before any arm on failure."""
    out = {}
    for tag, j in JOBS.items():
        g2 = g2_audit(tag, f'{OUT}/biased_{tag}')
        matcher = build_matcher(j)
        r0, n0 = g3_validate(tag, j, matcher)
        pose = inbox_gate_pose(tag)
        wh = warhead_xyz(pose)
        _, vu = read_map(f'{OUT}/{tag}_std.Cl.map')
        _, vb = read_map(f'{OUT}/biased_{tag}/{tag}_std.Cl.map')
        expected = trilin(vb, 65, j['center'], wh) - trilin(vu, 65, j['center'], wh)
        e = {}
        for label, kind in (('u1', 'std'), ('u2', 'std'), ('b', 'biased')):
            e[label] = affinity(run_vina(['--score_only', '--ligand', pose,
                                          '--maps', f'{OUT}/xs{kind}_{tag}/{tag}_xs',
                                          '--seed', '77000']))
        obs = e['b'] - e['u1']
        out[tag] = {'gate_pose': pose, 'warhead_xyz': [round(v, 3) for v in warhead_xyz(pose)],
                    'score_unmod_1': round(e['u1'], 4), 'score_unmod_2': round(e['u2'], 4),
                    'score_biased': round(e['b'], 4), 'observed_delta': round(obs, 4),
                    'expected_delta': round(expected, 4),
                    'G1_deterministic': abs(e['u1'] - e['u2']) < 1e-9,
                    'G1_abserr': round(abs(obs - expected), 4),
                    'G1_pass': abs(e['u1'] - e['u2']) < 1e-9 and abs(obs - expected) <= 0.05,
                    'G2_noncl_diffs': g2, 'G2_pass': g2 == [],
                    'G3_self_rmsd': None if r0 is None else round(r0, 6), 'G3_atoms': n0,
                    'G3_pass': r0 is not None and r0 < 1e-6}
    json.dump(out, open(f'{OUT}/gates_vinacli2.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))
    assert all(v['G1_pass'] and v['G2_pass'] and v['G3_pass'] for v in out.values()), 'GATE FAILURE - no outcomes may be read'

def stage_dock():
    fails = []
    for tag, j in JOBS.items():
        for arm in ('A0', 'A1', 'A2'):
            variant = 'true' if arm == 'A0' else 'cl'
            for s in SEEDS:
                outp = f'{OUT}/dock_vina_{tag}_{arm}_seed{s-77000}.pdbqt'
                logp = f'{OUT}/dock_vina_{tag}_{arm}_seed{s-77000}.log'
                if arm == 'A0':
                    args = ['--receptor', j['rec'], '--ligand', f'{OUT}/{tag}_lig_{variant}.pdbqt',
                            '--center_x', str(j['center'][0]), '--center_y', str(j['center'][1]),
                            '--center_z', str(j['center'][2]), '--size_x', '24', '--size_y', '24', '--size_z', '24']
                else:
                    kind = 'std' if arm == 'A1' else 'biased'
                    args = ['--ligand', f'{OUT}/{tag}_lig_{variant}.pdbqt',
                            '--maps', f'{OUT}/xs{kind}_{tag}/{tag}_xs']
                args += ['--exhaustiveness', '32', '--num_modes', '20', '--cpu', '2',
                         '--seed', str(s), '--out', outp]
                try:
                    log = run_vina(args, timeout=300)
                    open(logp, 'w').write(log)
                    print('done', tag, arm, s, flush=True)
                except Exception as e:
                    fails.append((tag, arm, s, str(e)[:400]))
    assert not fails, fails

def best_pose_vina(path):
    """First MODEL of a vina --out pdbqt = best-energy pose (vina writes poses
    ordered by affinity). Docked atom order = input order (locked convention)."""
    models, cur = [], None
    for line in open(path):
        if line.startswith('MODEL'):
            cur = {}
        elif line.startswith(('ATOM', 'HETATM')) and cur is not None:
            cur[int(line[6:11])] = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        elif line.startswith('ENDMDL'):
            models.append(cur); cur = None
    assert models and models[0], path
    # reindex to 1..N in input order
    return {k + 1: xyz for k, xyz in enumerate(models[0].values())}, len(models)

def stage_analyze():
    res = {}
    for tag, j in JOBS.items():
        matcher = build_matcher(j)
        arms = {}
        for arm in ('A0', 'A1', 'A2'):
            seeds = {}
            for s in (0, 1, 2):
                pose, nm = best_pose_vina(f'{OUT}/dock_vina_{tag}_{arm}_seed{s}.pdbqt')
                log = open(f'{OUT}/dock_vina_{tag}_{arm}_seed{s}.log').read()
                e = affinity(log.split('-----+------------+----------+----------')[-1]) if False else None
                m = re.search(r'^\s*1\s+(-?[0-9.eE+-]+)\s', log, re.M)
                seeds[str(s)] = {'best_energy': round(float(m.group(1)), 3) if m else None,
                                 'rmsd': round(sym_rmsd(j, matcher, pose)[0], 3),
                                 'atoms_matched': sym_rmsd(j, matcher, pose)[1], 'n_models': nm}
            wins = sum(1 for v in seeds.values() if v['rmsd'] <= 2.0)
            arms[arm] = {'seeds': seeds, 'seeds_passing': wins, 'complex_pass': wins >= 2}
        res[tag] = arms
    verdict = ('SUPPORTED' if all(res[t]['A2']['complex_pass'] for t in res)
               else 'NOT SUPPORTED' if not any(res[t]['A2']['complex_pass'] for t in res) else 'mixed')
    out = {'prereg': 'docs/PREREG_CONSTRAINT_GUIDED_12B_20260928.md',
           'engine': 'AutoDock Vina 1.2.7 built from source (option (b) adjudication 2026-09-28 09:15 IST); sf_name vina; AD4 map values via XS-named byte-identical views',
           'criterion': 'A2 best-energy-pose symmetry-corrected RMSD <= 2.0 A in >= 2/3 seeds per complex; both=SUPPORTED, one=mixed, zero=NOT SUPPORTED',
           'complexes': res, 'verdict': verdict}
    json.dump(out, open('/home/sandbox/work/12/results/constraint_guided_12b_vina.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))

if __name__ == '__main__':
    {'xsviews': build_xs_views, 'gates': stage_gates, 'dock': stage_dock, 'analyze': stage_analyze}[sys.argv[1]]()
