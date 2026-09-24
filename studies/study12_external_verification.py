"""Item 12 external verification: query public databases/tools to independently
verify the screening labels, target identity, literature claims and clinical
context used in this project. Every query is live, cached to
results/external_verification.json, and failure-tolerant (errors recorded, not hidden)."""
import json, pathlib, time, urllib.request, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "external_verification.json"

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

# 1. UniProt: SARS-CoV-2 replicase polyprotein 1ab (P0DTD1) - Mpro source protein
def uniprot():
    d = get("https://rest.uniprot.org/uniprotkb/P0DTD1.json?fields=accession,id,protein_name,length,organism")
    return {"accession": d.get("primaryAccession"), "id": d.get("uniProtkbId"),
            "length": d.get("sequence", {}).get("length"),
            "organism": d.get("organism", {}).get("scientificName")}
try_q("uniprot_P0DTD1", uniprot)

# 2. RCSB PDB core metadata for 7KX5 (independent of our local copy)
def rcsb():
    d = get("https://data.rcsb.org/rest/v1/core/entry/7KX5")
    s = d.get("rcsb_entry_info", {})
    return {"title": d.get("struct", {}).get("title"),
            "resolution": s.get("resolution_combined"),
            "method": (d.get("exptl") or [{}])[0].get("method")}
try_q("rcsb_7KX5", rcsb)

# 3. PDBe ligand info for X7V
def pdbe():
    d = get("https://www.ebi.ac.uk/pdbe/api/pdb/entry/ligand_monomers/7KX5")
    ligs = d.get("7KX5", [])
    return {"ligands": [{"id": l.get("chem_comp_id"), "name": l.get("chem_comp_name")} for l in ligs][:5]}
try_q("pdbe_7KX5_ligands", pdbe)

# 4. ChEMBL: Mpro target + bioactivities for a sample of screened drugs
def chembl_target():
    d = get("https://www.ebi.ac.uk/chembl/api/data/target/search.json?q=SARS-CoV-2%20main%20protease&limit=3")
    return {"hits": [{"chembl_id": t.get("target_chembl_id"), "pref_name": t.get("pref_name")}
                     for t in d.get("targets", [])]}
try_q("chembl_mpro_target", chembl_target)

def chembl_bio():
    out = {}
    for name in ["nirmatrelvir", "boceprevir", "masitinib", "carmofur", "nelfinavir"]:
        try:
            m = get(f"https://www.ebi.ac.uk/chembl/api/data/molecule/search.json?q={urllib.parse.quote(name)}&limit=1")
            mols = m.get("molecules", [])
            if not mols:
                out[name] = {"status": "no molecule"}; continue
            cid = mols[0]["molecule_chembl_id"]
            a = get(f"https://www.ebi.ac.uk/chembl/api/data/activity.json?molecule_chembl_id={cid}&assay_type=B&limit=5")
            out[name] = {"chembl_id": cid,
                         "sample_activities": [{"target": x.get("target_pref_name"),
                                                "type": x.get("standard_type"),
                                                "value": x.get("standard_value"),
                                                "units": x.get("standard_units")} for x in a.get("activities", [])]}
            time.sleep(0.4)
        except Exception as e:
            out[name] = {"error": str(e)[:120]}
    return out
try_q("chembl_bioactivities", chembl_bio)

# 5. PubChem: per-compound CID + key properties (22 compounds -> 22 dataset records)
def pubchem_props():
    out = {}
    for name in COMPOUNDS:
        try:
            d = get("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
                    f"{urllib.parse.quote(name)}/property/MolecularWeight,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount/JSON")
            p = d["PropertyTable"]["Properties"][0]
            out[name] = p
            time.sleep(0.25)
        except Exception as e:
            out[name] = {"error": str(e)[:120]}
    return out
try_q("pubchem_properties_22", pubchem_props)

# 6. Europe PMC: literature counts per compound + Mpro
def europepmc():
    out = {}
    for name in COMPOUNDS[:12]:
        try:
            q = urllib.parse.quote(f'{name} AND "main protease" AND SARS-CoV-2')
            d = get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}&format=json&pageSize=1")
            out[name] = {"mpro_hit_count": d.get("hitCount")}
            time.sleep(0.25)
        except Exception as e:
            out[name] = {"error": str(e)[:120]}
    return out
try_q("europepmc_lit_counts", europepmc)

# 7. NCBI E-utilities: PubMed count for Mpro docking (field-size check)
def ncbi():
    d = get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term="
            "SARS-CoV-2+main+protease+docking&retmode=json")
    return {"pubmed_mpro_docking_count": int(d["esearchresult"]["count"])}
try_q("ncbi_pubmed_count", ncbi)

# 8. ClinicalTrials.gov v2: nirmatrelvir trial count
def ctgov():
    d = get("https://clinicaltrials.gov/api/v2/studies?query.term=nirmatrelvir&pageSize=1&countTotal=true")
    return {"nirmatrelvir_trial_count": d.get("totalCount")}
try_q("clinicaltrials_nirmatrelvir", ctgov)

# 9. AlphaFold DB: predicted model for Mpro region (P0DTD1)
def afdb():
    d = get("https://alphafold.ebi.ac.uk/api/prediction/P0DTD1")
    if isinstance(d, list) and d:
        return {"model_url": d[0].get("pdbUrl", "")[:80], "uniprot": d[0].get("uniprotAccession")}
    return {"status": "none"}
try_q("alphafold_P0DTD1", afdb)

# 10. CrossRef: verify the anchor reference DOI (Jin et al. Nature 2020)
def crossref():
    d = get("https://api.crossref.org/works/10.1038/s41586-020-2223-y")
    m = d.get("message", {})
    return {"title": (m.get("title") or [""])[0][:90], "journal": (m.get("container-title") or [""])[0]}
try_q("crossref_jin2020", crossref)

OUT.write_text(json.dumps(rec, indent=1))
print("external verification written:", OUT)
print("queries ok:", list(rec["queries"].keys()))
print("errors:", list(rec["errors"].keys()))
