"""CLI smoke tests (hermetic): ladder reads committed records; novelty URL build."""
import json, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

def test_ladder_matches_committed_record():
    out = subprocess.run([sys.executable, "-m", "drugdisc.cli", "ladder"],
                         capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    rec = json.loads((ROOT / "results/screen_analysis.json").read_text())
    lines = [l for l in out.stdout.strip().splitlines() if l.strip()]
    assert len(lines) == len(rec["ranking"])
    assert rec["ranking"][0]["name"] in lines[0]

def test_novelty_rejects_missing_smiles_arg():
    out = subprocess.run([sys.executable, "-m", "drugdisc.cli", "novelty"],
                         capture_output=True, text=True, cwd=ROOT)
    assert out.returncode != 0
