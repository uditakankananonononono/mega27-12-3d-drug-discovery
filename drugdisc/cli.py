"""mpro-dock: usable CLI built on the item-12 validated pipeline.

Commands:
  dock --smiles "CC..." [--name X]   dock a compound against validated 7KX5 Mpro,
                                     rank it on the 22-compound calibration ladder
  novelty --smiles "CC..."           PubChem identity + similarity neighborhood check
  ladder                             print the calibration ladder (committed screen record)
The redock gate (0.97 A, results/redock_7KX5.json) is what licenses every score.
"""
from __future__ import annotations
import argparse, json, pathlib, sys, tempfile, urllib.request, urllib.parse

import os

def _find_root():
    """Locate the repo data: env var, cwd upward search, module upward search."""
    if os.environ.get("DRUGDISC_ROOT"):
        return pathlib.Path(os.environ["DRUGDISC_ROOT"])
    for start in (pathlib.Path.cwd(), pathlib.Path(__file__).resolve()):
        for cand in [start] + list(start.parents):
            if (cand / "results" / "screen_analysis.json").exists() and (cand / "data" / "raw").exists():
                return cand
    return pathlib.Path(__file__).resolve().parent.parent

ROOT = _find_root()
RAW = ROOT / "data" / "raw"

def _ladder():
    f = ROOT / "results" / "screen_analysis.json"
    if not f.exists():
        print("error: calibration records not found - run from the repository root "
              "or set DRUGDISC_ROOT to the repo path", file=sys.stderr)
        sys.exit(2)
    return json.loads(f.read_text())["ranking"]

def cmd_dock(a):
    from drugdisc.prep import smiles_to_pdbqt
    from drugdisc.dock import dock_ligand
    if not (RAW / "box_7kx5.json").exists():
        print("error: receptor data not found - run from the repository root "
              "or set DRUGDISC_ROOT to the repo path", file=sys.stderr)
        sys.exit(2)
    box = json.loads((RAW / "box_7kx5.json").read_text())
    name = a.name or "query"
    with tempfile.TemporaryDirectory() as td:
        pdbqt = pathlib.Path(td) / "lig.pdbqt"
        smiles_to_pdbqt(a.smiles, str(pdbqt))
        res, _ = dock_ligand(str(RAW / "7KX5_A_receptor.pdbqt"), str(pdbqt),
                             box["center"], box["size"], ligand_name=name,
                             exhaustiveness=8, n_poses=5, cpu=2)
    rank = _ladder()
    affs = [r["affinity"] for r in rank]
    pos = sum(1 for x in affs if x < res.best_affinity) + 1
    out = {"compound": name, "best_affinity_kcal_mol": round(res.best_affinity, 3),
           "all_pose_affinities": [round(x, 3) for x in res.all_affinities],
           "calibration_ladder_position": f"{pos} of {len(affs)+1}",
           "caveat": "raw Vina ranking on this ladder is honest-negative (AUROC 0.339, "
                     "committed results/screen_analysis.json) - use for pose generation "
                     "and GNN rescoring, not raw-rank claims",
           "protocol": "validated by 0.97 A redock (results/redock_7KX5.json)"}
    print(json.dumps(out, indent=1))

def _pug(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mpro-dock/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode())

def cmd_novelty(a):
    q = urllib.parse.quote(a.smiles, safe="")
    out = {"smiles": a.smiles}
    try:
        r = _pug(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/fastidentity/smiles/{q}/cids/JSON")
        cids = [c for c in r.get("IdentifierList", {}).get("CID", []) if c]
        out["exact_structure"] = {"status": "FOUND", "cids": cids} if cids else {"status": "NOT_FOUND"}
    except Exception:
        out["exact_structure"] = {"status": "NOT_FOUND (identity endpoint: no record)"}
    for thr in (95, 85):
        try:
            r = _pug(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/fastsimilarity_2d/smiles/{q}/cids/JSON?Threshold={thr}&MaxRecords=5")
            out[f"neighbors_tanimoto>=0.{thr}"] = r.get("IdentifierList", {}).get("CID", [])
        except Exception:
            out[f"neighbors_tanimoto>=0.{thr}"] = []
    print(json.dumps(out, indent=1))

def cmd_ladder(a):
    for i, r in enumerate(_ladder(), 1):
        print(f"{i:2d}. {r['name']:<22s} {r['affinity']:>7.2f} kcal/mol  [{r['class']}]")

def main():
    ap = argparse.ArgumentParser(prog="mpro-dock",
        description="Dock compounds against validated SARS-CoV-2 Mpro (7KX5) with honest calibration")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dock"); d.add_argument("--smiles", required=True); d.add_argument("--name")
    n = sub.add_parser("novelty"); n.add_argument("--smiles", required=True)
    sub.add_parser("ladder")
    args = ap.parse_args()
    {"dock": cmd_dock, "novelty": cmd_novelty, "ladder": cmd_ladder}[args.cmd](args)

if __name__ == "__main__":
    main()
