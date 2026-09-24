"""Study 12 phase 4 (discovery): dock the de novo candidate library in the
redock-validated protocol, rank, and verify the top candidate's novelty live
against PubChem. Output: MPRO-D1 with name, SMILES, predicted affinity, ligand
efficiency, complexity, Tanimoto distance to known drugs, novelty evidence."""
import json
import pathlib
import time

import requests

from drugdisc.denovo import enumerate_candidates, complexity_score, tanimoto_to_set
from drugdisc.prep import smiles_to_pdbqt
from drugdisc.dock import dock_ligand

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
RES = ROOT / "results"
OUT = RES / "denovo"
OUT.mkdir(parents=True, exist_ok=True)

box = json.loads((RAW / "box_7kx5.json").read_text())
cands = enumerate_candidates()
print(f"docking {len(cands)} de novo candidates (exhaustiveness 4)", flush=True)
for c in cands:
    cache = OUT / f"cand_{abs(hash(c['smiles'])) % 10**8}.json"
    if cache.exists():
        c.update(json.loads(cache.read_text()))
        continue
    try:
        pdbqt = OUT / f"lig_{abs(hash(c['smiles'])) % 10**8}.pdbqt"
        if not pdbqt.exists():
            smiles_to_pdbqt(c["smiles"], str(pdbqt))
        res, _ = dock_ligand(str(RAW / "7KX5_A_receptor.pdbqt"), str(pdbqt),
                             box["center"], box["size"],
                             ligand_name=c["core"], exhaustiveness=4, n_poses=3, cpu=2)
        c["affinity"] = res.best_affinity
        cache.write_text(json.dumps(c, indent=1))
        print(f"  {c['core']}: {res.best_affinity:.2f}", flush=True)
    except Exception as exc:
        print(f"  FAILED {c['core']}/{c['r_group']}: {exc}", flush=True)

docked = [c for c in cands if "affinity" in c]
docked.sort(key=lambda c: c["affinity"])
screen_smiles = json.loads((RAW / "screen_smiles.json").read_text())
known = list(screen_smiles.values())
best_screen = min(json.loads(p.read_text())["affinity"]
                  for p in (RES / "screen").glob("*.json"))
print(f"best screened drug affinity: {best_screen:.2f} kcal/mol")

for c in docked:
    c["tanimoto_max_vs_screen"] = tanimoto_to_set(c["smiles"], known)
    c["ligand_efficiency"] = c["affinity"] / c["heavy"]
    c["complexity"] = complexity_score(c["smiles"])

top = docked[0]
print(f"top de novo candidate: {top['smiles']} aff={top['affinity']:.2f} "
      f"tan={top['tanimoto_max_vs_screen']:.2f}")

# ---- live novelty verification against PubChem (exact structure)
def pubchem_exact(smiles: str):
    url = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/"
           f"{requests.utils.quote(smiles, safe='')}/cids/JSON")
    r = requests.get(url, timeout=30)
    if r.status_code == 404:
        return "NO_EXACT_MATCH"
    r.raise_for_status()
    return r.json()["IdentifierList"]["CID"]

novelty = {}
for c in docked[:5]:
    try:
        cids = pubchem_exact(c["smiles"])
        novelty[c["smiles"]] = {"status": "FOUND", "cids": cids}
    except Exception as exc:
        novelty[c["smiles"]] = {"status": "ERROR", "detail": str(exc)[:200]}
    time.sleep(0.3)
print("novelty check:", json.dumps(novelty, indent=1)[:400])

result = {
    "candidate_name": "MPRO-D1",
    "smiles": top["smiles"], "core": top["core"],
    "predicted_affinity_kcal_mol": top["affinity"],
    "ligand_efficiency": top["ligand_efficiency"],
    "complexity_score": top["complexity"],
    "tanimoto_max_vs_screened_drugs": top["tanimoto_max_vs_screen"],
    "best_screened_drug_affinity": best_screen,
    "beats_best_screened": top["affinity"] < best_screen,
    "novelty_pubchem": novelty.get(top["smiles"], {"status": "NOT_CHECKED"}),
    "library_size": len(docked),
    "falsifiable_prediction": (
        "MPRO-D1 docks within the validated 7KX5 Mpro protocol at the stated "
        "affinity and pose class; a crystal or ITC test of the synthesized "
        "compound decides it."),
    "top10": [{k: (round(v, 4) if isinstance(v, float) else v)
               for k, v in c.items() if k in (
                   "smiles", "core", "affinity", "ligand_efficiency",
                   "complexity", "tanimoto_max_vs_screen")} for c in docked[:10]],
}
(RES / "denovo_mpro_d1.json").write_text(json.dumps(result, indent=1))
print("wrote results/denovo_mpro_d1.json")
