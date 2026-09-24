"""Grow the Mpro label set from ChEMBL. Target discipline: CHEMBL4523582 (SARS-CoV-2
replicase polyprotein 1ab) filtered to assays whose description names 3CL/main
protease - whole-virus antiviral assays (e.g. CHEMBL4303835) are EXCLUDED, because a
cellular EC50 is not an Mpro label. Live queries, cached."""
import json, pathlib, time, urllib.request, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "chembl_label_set.json"

def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "mega27-item12/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

TARGET = "CHEMBL4523582"
MPRO_TERMS = ("3cl", "main protease", "mpro", "3c-like")

rows_all = []
url = (f"https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id={TARGET}"
       "&standard_type__in=IC50,Ki,Kd&limit=200")
while url and len(rows_all) < 600:
    d = get(url)
    rows_all.extend(d.get("activities", []))
    nxt = d.get("page_meta", {}).get("next"); url = ("https://www.ebi.ac.uk" + nxt) if nxt else None
    time.sleep(0.3)
print("rows pulled:", len(rows_all))

mpro_rows = [r for r in rows_all
             if any(t in (r.get("assay_description") or "").lower() for t in MPRO_TERMS)]
print("Mpro-specific rows:", len(mpro_rows))

compounds = {}
for r in mpro_rows:
    mol = r.get("molecule_chembl_id")
    val = r.get("standard_value")
    if not mol or val is None or r.get("standard_units") != "nM":
        continue
    try:
        v = float(val)
    except (TypeError, ValueError):
        continue
    rec = compounds.setdefault(mol, {"values_nM": [], "assays": set()})
    rec["values_nM"].append(v)
    rec["assays"].add(r.get("assay_chembl_id"))

label_records = []
for mol, rec in compounds.items():
    pot = min(rec["values_nM"])
    label_records.append({"chembl_id": mol, "best_potency_nM": pot,
                          "n_measurements": len(rec["values_nM"]),
                          "n_assays": len(rec["assays"]),
                          "label": "active" if pot < 10000 else "inactive"})
label_records.sort(key=lambda x: x["best_potency_nM"])
n_act = sum(1 for r in label_records if r["label"] == "active")
out = {"source_target": TARGET,
       "target_note": "SARS-CoV-2 replicase polyprotein 1ab, restricted to assays naming 3CL/main protease",
       "excluded": "CHEMBL4303835 whole-virus antiviral assays (cellular EC50 is not an Mpro label)",
       "n_rows_pulled": len(rows_all), "n_mpro_rows": len(mpro_rows),
       "n_compounds": len(label_records), "n_active_lt10uM": n_act,
       "threshold": "active if best measured potency < 10 uM",
       "records": label_records}
OUT.write_text(json.dumps(out, indent=1))
print(f"{len(label_records)} compounds, {n_act} active <10uM; wrote {OUT}")
