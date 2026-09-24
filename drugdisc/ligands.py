"""Curated real-drug screening set. Canonical SMILES are fetched live from
PubChem PUG-REST and cached; never hard-code chemistry by hand."""
from __future__ import annotations
import json
import time
from pathlib import Path

import requests

# name -> known Mpro activity class from published experimental literature:
#   "active": reported Mpro inhibitor / antiviral with Mpro mechanism evidence
#   "inactive": failed in Mpro assays or clinically ineffective vs Mpro mechanism
#   "unknown": diverse approved-drug controls
SCREEN_SET = {
    "nirmatrelvir": "active", "boceprevir": "active", "telaprevir": "active",
    "ebselen": "active", "carmofur": "active", "disulfiram": "active",
    "tideglusib": "active", "masitinib": "active",
    "lopinavir": "inactive", "atazanavir": "inactive", "darunavir": "inactive",
    "saquinavir": "inactive", "indinavir": "inactive", "nelfinavir": "inactive",
    "chloroquine": "inactive", "hydroxychloroquine": "inactive",
    "ritonavir": "unknown", "remdesivir": "unknown", "molnupiravir": "unknown",
    "favipiravir": "unknown", "camostat": "unknown", "nafamostat": "unknown",
    "ivermectin": "unknown", "nilotinib": "unknown",
}

PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name"


def fetch_smiles(name: str, timeout: int = 30) -> str:
    """Canonical/isomeric SMILES for a drug name from PubChem (live).
    PubChem renamed CanonicalSMILES to ConnectivitySMILES; accept either."""
    url = (f"{PUBCHEM}/{requests.utils.quote(name)}"
           f"/property/ConnectivitySMILES,IsomericSMILES/JSON")
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    props = resp.json()["PropertyTable"]["Properties"][0]
    for key in ("IsomericSMILES", "ConnectivitySMILES", "SMILES", "CanonicalSMILES"):
        if props.get(key):
            return props[key]
    raise KeyError(f"no SMILES property in PubChem response for {name}")


def fetch_screen_set(cache_path: str) -> dict:
    """Fetch (or load cached) name -> SMILES for the whole screening set."""
    cache = Path(cache_path)
    if cache.exists():
        return json.loads(cache.read_text())
    out = {}
    for name in SCREEN_SET:
        try:
            out[name] = fetch_smiles(name)
            time.sleep(0.25)
        except Exception as exc:  # network/name resolution failures are reported, not hidden
            print(f"  WARN: PubChem failed for {name}: {exc}")
    cache.write_text(json.dumps(out, indent=1))
    return out
