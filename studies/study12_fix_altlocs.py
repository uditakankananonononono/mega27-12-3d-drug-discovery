"""Fix alternate-location records: per residue, keep the altloc with the most
atoms (blank counts as an altloc), strip altloc codes, renumber serials.
Needed because meeko template matching fails on sidechains split across
altlocs (7VU6 chain A: 22 bad residues, chain B: 12 before fixing)."""
import sys
from collections import defaultdict

def fix_altlocs(inp: str, out: str) -> dict:
    residues = defaultdict(lambda: defaultdict(list))  # reskey -> altloc -> lines
    order = []
    for line in open(inp):
        if line[:6].strip() != "ATOM":
            continue
        reskey = (line[21], line[22:26], line[26])  # chain, resseq, icode
        alt = line[16]
        if reskey not in residues:
            order.append(reskey)
        residues[reskey][alt].append(line)
    dropped = {}
    n_out = 0
    with open(out, "w") as fh:
        serial = 1
        for reskey in order:
            alts = residues[reskey]
            best = max(alts, key=lambda a: len(alts[a]))
            if len(alts) > 1:
                dropped[reskey] = {a: len(l) for a, l in alts.items()}
            for line in alts[best]:
                line = line[:6] + f"{serial:5d}" + line[11:16] + " " + line[17:]
                fh.write(line)
                serial += 1; n_out += 1
        fh.write("TER\nEND\n")
    return {"residues_with_altlocs": len(dropped), "atoms_written": n_out,
            "detail": {str(k): v for k, v in list(dropped.items())[:50]}}

if __name__ == "__main__":
    import json
    print(json.dumps(fix_altlocs(sys.argv[1], sys.argv[2]), indent=1))
