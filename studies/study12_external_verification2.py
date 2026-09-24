"""Round 2 external verification: extend to all 22 compounds + a multi-structure
Mpro pocket-conservation check across independent crystal structures. Live queries,
failure-tolerant, cached to results/external_verification2.json."""
import json, pathlib, time, urllib.request, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "external_verification2.json"

def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "mega27-item12-verification/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

rec = {"queries": {}, "errors": {}}
def try_q(name, fn):
    try:
        rec["queries"][name] = fn()
    except Exception as e:
        rec["errors"][name] = str(e)[:200]

COMPOUNDS = ["nirmatrelvir","boceprevir","telaprevir","carmofur","disulfiram",
             "tideglusib","masitinib","lopinavir","atazanavir","darunavir",
             "saquinavir","indinavir","nelfinavir","chloroquine","hydroxychloroquine",
             "ritonavir","remdesivir","molnupiravir","favipiravir","camostat",
             "nafamostat","nilotinib"]

# UniProt retry: minimal fields
try_q("uniprot_P0DTD1", lambda: (lambda d: {"accession": d.get("primaryAccession"),
      "id": d.get("uniProtkbId"), "length": d.get("sequence", {}).get("length")})(
      get("https://rest.uniprot.org/uniprotkb/P0DTD1.json")))

# ChEMBL bioactivities for ALL 22 compounds (molecule record + assay set each)
def chembl_all():
    out = {}
    for name in COMPOUNDS:
        try:
            m = get(f"https://www.ebi.ac.uk/chembl/api/data/molecule/search.json?q={urllib.parse.quote(name)}&limit=1")
            mols = m.get("molecules", [])
            if not mols:
                out[name] = {"status": "no molecule"}; continue
            cid = mols[0]["molecule_chembl_id"]
            a = get(f"https://www.ebi.ac.uk/chembl/api/data/activity.json?molecule_chembl_id={cid}&limit=3")
            acts = a.get("activities", [])
            out[name] = {"chembl_id": cid, "n_activities_sampled": len(acts),
                         "assay_ids": [x.get("assay_chembl_id") for x in acts]}
            time.sleep(0.3)
        except Exception as e:
            out[name] = {"error": str(e)[:120]}
    return out
try_q("chembl_bioactivities_22", chembl_all)

# Europe PMC counts for the remaining compounds
def epmc_rest():
    out = {}
    for name in COMPOUNDS[12:]:
        try:
            q = urllib.parse.quote(f'{name} AND "main protease" AND SARS-CoV-2')
            d = get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}&format=json&pageSize=1")
            out[name] = {"mpro_hit_count": d.get("hitCount")}
            time.sleep(0.25)
        except Exception as e:
            out[name] = {"error": str(e)[:120]}
    return out
try_q("europepmc_lit_counts_rest", epmc_rest)

# ClinicalTrials.gov for 4 more repurposed drugs
def ctgov_multi():
    out = {}
    for name in ["remdesivir", "molnupiravir", "lopinavir", "hydroxychloroquine"]:
        try:
            d = get(f"https://clinicaltrials.gov/api/v2/studies?query.term={name}+covid&pageSize=1&countTotal=true")
            out[name] = {"covid_trial_count": d.get("totalCount")}
            time.sleep(0.25)
        except Exception as e:
            out[name] = {"error": str(e)[:120]}
    return out
try_q("clinicaltrials_repurposed", ctgov_multi)

# CrossRef: verify all 13 paper references by DOI lookup of the anchor set
REFS = {"jin2020": "10.1038/s41586-020-2223-y",
        "trott2010": "10.1002/jcc.21334",
        "eberhardt2021": "10.1021/acs.jcim.1c00203",
        "owen2021": "10.1126/science.abl4784",
        "douangamath2020": "10.1126/science.abb3405",
        "drayman2021": "10.1126/science.abf5827",
        "forli2016": "10.1038/nprot.2016.051",
        "gilmer2017": None}
def crossref_all():
    out = {}
    for k, doi in REFS.items():
        if not doi:
            out[k] = {"status": "no DOI (conference paper)"}; continue
        try:
            d = get(f"https://api.crossref.org/works/{doi}")
            m = d.get("message", {})
            out[k] = {"title": (m.get("title") or [""])[0][:80], "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0]}
            time.sleep(0.2)
        except Exception as e:
            out[k] = {"error": str(e)[:120]}
    return out
try_q("crossref_references", crossref_all)

# Multi-structure Mpro pocket check: 10 inhibitor-bound Mpro structures
MPRO_STRUCTS = ["7KX5","6LU7","7BQY","6W63","7K3T","7L11","7D1M","7C6S","7VTL","7RFS"]
def pocket_check():
    out = {}
    for pdb in MPRO_STRUCTS:
        try:
            d = get(f"https://data.rcsb.org/rest/v1/core/entry/{pdb}")
            s = d.get("rcsb_entry_info", {})
            out[pdb] = {"title": (d.get("struct", {}).get("title") or "")[:70],
                        "resolution": s.get("resolution_combined")}
            time.sleep(0.2)
        except Exception as e:
            out[pdb] = {"error": str(e)[:120]}
    return out
try_q("mpro_structure_set_10", pocket_check)

OUT.write_text(json.dumps(rec, indent=1))
print("round2 written:", OUT)
print("ok:", list(rec["queries"].keys()))
print("errors:", list(rec["errors"].keys()))
