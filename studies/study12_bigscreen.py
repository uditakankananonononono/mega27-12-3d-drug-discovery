"""Study 12 phase 5: extended screen of ChEMBL Mpro-labeled compounds (balanced
sample) to grow the benchmark beyond n=15. Resumable per-compound cache under
results/bigscreen/. SMILES from ChEMBL molecule records (live, cached).

Eligibility rule (documented, applied at sampling): macrocycles - any ring of
12+ atoms - are EXCLUDED, because the validated protocol covers small
molecules only (X7V, MW ~500; ensitrelvir, MW ~480) and vina's torsion search
does not terminate on macrocycle closure spaces (observed: CHEMBL4846937,
22-membered ring, spun >300 s). Excluded compounds are listed in
results/bigscreen_exclusions.json with MW and max ring size. The inactive
pool is backfilled past exclusions to keep the 25+25 balance.
"""
import json, pathlib, time, urllib.request, urllib.parse
from rdkit import Chem
from rdkit.Chem import Descriptors
from drugdisc.prep import smiles_to_pdbqt
from drugdisc.dock import dock_ligand_with_timeout

DOCK_TIMEOUT_S = 300  # belt-and-braces; eligibility rule catches macrocycles first

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
OUT = ROOT / "results/bigscreen"; OUT.mkdir(parents=True, exist_ok=True)
SMI_CACHE = RAW / "chembl_smiles.json"

def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "mega27-item12/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def fetch_smiles(cid, smi_map):
    if cid not in smi_map:
        m = get(f"https://www.ebi.ac.uk/chembl/api/data/molecule/{cid}.json")
        smi = (m.get("molecule_structures") or {}).get("canonical_smiles")
        if smi:
            smi_map[cid] = smi
            SMI_CACHE.write_text(json.dumps(smi_map, indent=1))
            time.sleep(0.2)
    return smi_map.get(cid)

VINA_SUPPORTED = {"H", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"}

def unsupported_elements(smi: str) -> list[str]:
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return []
    return sorted({a.GetSymbol() for a in mol.GetAtoms()
                   if a.GetSymbol() not in VINA_SUPPORTED})

def macrocycle_ring_size(smi: str) -> int:
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return -1
    rings = mol.GetRingInfo().AtomRings()
    return max((len(r) for r in rings), default=0)

if __name__ == "__main__":
    labels = json.loads((ROOT / "results/chembl_label_set.json").read_text())["records"]
    actives = [r for r in labels if r["label"] == "active"]
    inactives = sorted([r for r in labels if r["label"] == "inactive"],
                       key=lambda r: -r["best_potency_nM"])
    smi_map = json.loads(SMI_CACHE.read_text()) if SMI_CACHE.exists() else {}

    # actives: first 25 as before (all already docked - none macrocyclic)
    sample = actives[:25]
    # inactives: first 25 ELIGIBLE (non-macrocycle), weakest potency first
    exclusions = []
    picked_ina = []
    for rec in inactives:
        if len(picked_ina) >= 25:
            break
        cid = rec["chembl_id"]
        smi = fetch_smiles(cid, smi_map)
        if not smi:
            exclusions.append({"chembl_id": cid, "reason": "no_smiles"})
            continue
        mr = macrocycle_ring_size(smi)
        if mr >= 12:
            mw = Descriptors.MolWt(Chem.MolFromSmiles(smi))
            exclusions.append({"chembl_id": cid, "reason": "macrocycle",
                               "max_ring_atoms": mr, "mw": round(mw, 1)})
            continue
        picked_ina.append(rec)
    sample += picked_ina
    (ROOT / "results/bigscreen_exclusions.json").write_text(json.dumps(
        {"rule": "exclude any ring >= 12 atoms (macrocycle) - outside the "
                 "validated small-molecule protocol; vina does not terminate "
                 "on macrocycle closure spaces",
         "excluded": exclusions}, indent=1))
    print(f"sample: {len(sample)} compounds "
          f"({len(exclusions)} excluded incl. macrocycles)", flush=True)

    box = json.loads((RAW / "box_7kx5.json").read_text())
    done = skip = fail = 0
    for rec in sample:
        cid = rec["chembl_id"]
        cache = OUT / f"{cid}.json"
        if cache.exists():
            done += 1; continue
        try:
            smi = fetch_smiles(cid, smi_map)
            if not smi:
                fail += 1; continue
            bad_el = unsupported_elements(smi)
            if bad_el:
                skip += 1
                cache.write_text(json.dumps({"chembl_id": cid, "smiles": smi,
                    "skipped": f"unsupported_element_{'_'.join(bad_el)}_no_vina_parameters",
                    "label": rec["label"],
                    "best_potency_nM": rec["best_potency_nM"]}, indent=1))
                print(f"  SKIPPED {cid}: unsupported elements {bad_el} "
                      f"(no vina parameters) [{done}/{len(sample)}]", flush=True)
                continue
            pdbqt = RAW / f"lig_{cid}.pdbqt"
            if not pdbqt.exists():
                smiles_to_pdbqt(smi, str(pdbqt))
            try:
                best, all_aff = dock_ligand_with_timeout(
                    str(RAW / "7KX5_A_receptor.pdbqt"), str(pdbqt),
                    box["center"], box["size"], ligand_name=cid,
                    timeout_s=DOCK_TIMEOUT_S)
            except TimeoutError:
                skip += 1
                cache.write_text(json.dumps({"chembl_id": cid, "smiles": smi,
                    "skipped": f"dock_timeout_{DOCK_TIMEOUT_S}s",
                    "label": rec["label"],
                    "best_potency_nM": rec["best_potency_nM"]}, indent=1))
                print(f"  SKIPPED {cid}: dock timeout [{done}/{len(sample)}]", flush=True)
                continue
            cache.write_text(json.dumps({"chembl_id": cid, "smiles": smi,
                "affinity": best, "all_affinities": all_aff,
                "label": rec["label"], "best_potency_nM": rec["best_potency_nM"]}, indent=1))
            done += 1
            print(f"  docked {cid}: {best:.2f} ({rec['label']}) [{done}/{len(sample)}]", flush=True)
        except Exception as exc:
            fail += 1
            print(f"  FAILED {cid}: {str(exc)[:100]}", flush=True)
    print(f"done={done} failed={fail} skipped={skip}", flush=True)
