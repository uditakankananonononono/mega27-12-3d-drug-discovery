"""Frozen analysis rules tested on synthetic poses, no docking or outcome data."""
import ast
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / 'studies/nativecov12e/redock/run_12ecr.py'


def analyze(tmp_path, test, control):
    tree = ast.parse(SCRIPT.read_text())
    fn = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'stage_analyze')
    here = tmp_path / 'redock'
    here.mkdir()
    (tmp_path / 'results').mkdir()
    values = {'7c6s': test, '7vh8': control}
    status = {f'{tag}_seed{s}': {'dlg': r is not None, 'timeout': r is None}
              for tag, rs in values.items() for s, r in enumerate(rs)}
    (here / 'dock_status.json').write_text(json.dumps(status))

    def pose(path, _names):
        tag = '7c6s' if '7c6s' in path else '7vh8'
        seed = int(path.split('_seed')[1].split('.')[0])
        return values[tag][seed], -1, 10

    env = dict(json=json, HERE=str(here), ROOT=str(tmp_path), TAGS=['7c6s', '7vh8'],
               JOBS={'7c6s': {}, '7vh8': {}}, build_matcher=lambda j: None,
               remap=lambda t: None, lig_names=lambda p: None,
               lig_pose_from_dlg=pose, fixpose=lambda p, r: r,
               sym_rmsd=lambda j, m, r: (r, 10))
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SCRIPT), 'exec'), env)
    env['stage_analyze']()
    return json.loads((tmp_path / 'results/native_covalent_12e_redock.json').read_text())


def test_threshold_uses_unrounded_rmsd(tmp_path):
    result = analyze(tmp_path, [2.0004, 2.0004, 1.5], [1.0, 1.0, 1.0])
    assert result['classification'] == 'NOT CONFIRMED'
    assert result['complexes']['7c6s']['seeds_passing'] == 1
    seed = result['complexes']['7c6s']['seeds']['0']
    assert seed['rmsd'] == 2.0
    assert seed['rmsd_full_precision'] == 2.0004


def test_exact_boundary_and_two_of_three(tmp_path):
    result = analyze(tmp_path, [2.0, 2.0, 2.1], [1.0, 2.0, 3.0])
    assert result['classification'] == 'CONFIRMED'


def test_control_discordance(tmp_path):
    result = analyze(tmp_path, [1.0, 1.0, 3.0], [3.0, 3.0, 1.0])
    assert result['classification'] == 'CONTROL-DISCORDANT'


def test_machinery_precedes_verdict(tmp_path):
    result = analyze(tmp_path, [1.0, None, None], [1.0, 1.0, 1.0])
    assert result['classification'] == 'MACHINERY-INCOMPLETE'
