"""Study 12 phase 5: extended screen of ChEMBL Mpro-labeled compounds (balanced
sample) to grow the benchmark beyond n=15. Resumable per-compound cache under
results/bigscreen/. SMILES from ChEMBL molecule records (live, cached)."""
import json, pathlib, time, urllib.request, urllib.parse
from drugdisc.prep import smiles_to_pdbqt
from drugdisc.dock import dock_ligand

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
OUT = ROOT / "results/bigscreen"; OUT.mkdir(parents=True, exist_ok=True)
SMI_CACHE = RAW / "chembl_smiles.json"

labels = json.loads((ROOT / "results/chembl_label_set.json").read_text())["records"]
actives = [r for r in labels if r["label"] == "active"]
inactives = [r for r in labels if r["label"] == "inactive"]
# balanced sample: 25 strongest actives + 25 inactives (weakest potency)
sample = actives[:25] + sorted(inactives, key=lambda r: -r["best_potency_nM"])[:25]
print(f"sample: {len(sample)} compounds", flush=True)

def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "mega27-item12/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

smi_map = json.loads(SMI_CACHE.read_text()) if SMI_CACHE.exists() else {}
box = json.loads((RAW / "box_7kx5.json").read_text())
done = skip = fail = 0
for rec in sample:
    cid = rec["chembl_id"]
    cache = OUT / f"{cid}.json"
    if cache.exists():
        done += 1; continue
    try:
        if cid not in smi_map:
            m = get(f"https://www.ebi.ac.uk/chembl/api/data/molecule/{cid}.json")
            smi = (m.get("molecule_structures") or {}).get("canonical_smiles")
            if not smi:
                fail += 1; continue
            smi_map[cid] = smi
            SMI_CACHE.write_text(json.dumps(smi_map, indent=1))
            time.sleep(0.2)
        smi = smi_map[cid]
        pdbqt = RAW / f"lig_{cid}.pdbqt"
        if not pdbqt.exists():
            smiles_to_pdbqt(smi, str(pdbqt))
        res, _ = dock_ligand(str(RAW / "7KX5_A_receptor.pdbqt"), str(pdbqt),
                             box["center"], box["size"], ligand_name=cid,
                             exhaustiveness=8, n_poses=5, cpu=2)
        cache.write_text(json.dumps({"chembl_id": cid, "smiles": smi,
            "affinity": res.best_affinity, "all_affinities": res.all_affinities,
            "label": rec["label"], "best_potency_nM": rec["best_potency_nM"]}, indent=1))
        done += 1
        print(f"  docked {cid}: {res.best_affinity:.2f} ({rec['label']}) [{done}/{len(sample)}]", flush=True)
    except Exception as exc:
        fail += 1
        print(f"  FAILED {cid}: {str(exc)[:100]}", flush=True)
print(f"done={done} failed={fail}", flush=True)
