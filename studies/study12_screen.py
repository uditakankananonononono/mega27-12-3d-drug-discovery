"""Study 12 phase 2: screening campaign. Dock the curated 24-drug set against
Mpro (7KX5), rank by Vina affinity, and measure enrichment of known actives.
Resumable: per-ligand results cached under results/screen/."""
import json
import pathlib
import numpy as np

from drugdisc.ligands import fetch_screen_set, SCREEN_SET
from drugdisc.prep import smiles_to_pdbqt
from drugdisc.dock import dock_ligand

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
OUT = ROOT / "results/screen"
OUT.mkdir(parents=True, exist_ok=True)

box = json.loads((RAW / "box_7kx5.json").read_text())
smiles_map = fetch_screen_set(str(RAW / "screen_smiles.json"))
print(f"SMILES resolved for {len(smiles_map)}/{len(SCREEN_SET)} ligands", flush=True)

results = []
for name, smi in sorted(smiles_map.items()):
    cache = OUT / f"{name}.json"
    if cache.exists():
        results.append(json.loads(cache.read_text()))
        print(f"  cached: {name}", flush=True)
        continue
    try:
        pdbqt = RAW / f"lig_{name}.pdbqt"
        if not pdbqt.exists():
            smiles_to_pdbqt(smi, str(pdbqt))
        res, _ = dock_ligand(str(RAW / "7KX5_A_receptor.pdbqt"), str(pdbqt),
                             box["center"], box["size"], ligand_name=name,
                             exhaustiveness=8, n_poses=5, cpu=2)
        rec = {"name": name, "smiles": smi, "affinity": res.best_affinity,
               "all_affinities": res.all_affinities, "known_class": SCREEN_SET[name]}
        cache.write_text(json.dumps(rec, indent=1))
        results.append(rec)
        print(f"  docked {name}: {res.best_affinity:.2f} kcal/mol ({SCREEN_SET[name]})", flush=True)
    except Exception as exc:
        print(f"  FAILED {name}: {exc}", flush=True)

if len(results) >= 10:
    # enrichment: known actives in top-8 ranks vs random expectation
    ranked = sorted(results, key=lambda r: r["affinity"])
    top = ranked[:8]
    actives_total = sum(1 for r in results if r["known_class"] == "active")
    actives_top = sum(1 for r in top if r["known_class"] == "active")
    expected = 8 * actives_total / len(results)
    enrichment = actives_top / expected if expected > 0 else 0.0
    summary = {"n_ligands": len(results), "actives_total": actives_total,
               "actives_in_top8": actives_top, "expected_by_chance": round(expected, 2),
               "enrichment_factor": round(enrichment, 2),
               "ranking": [{"name": r["name"], "affinity": r["affinity"],
                            "class": r["known_class"]} for r in ranked]}
    (ROOT / "results/screen_summary.json").write_text(json.dumps(summary, indent=1))
    print(f"enrichment: {actives_top}/{actives_total} actives in top-8 "
          f"(expected {expected:.1f} by chance, EF {enrichment:.1f}x)", flush=True)
    print("wrote results/screen_summary.json", flush=True)
