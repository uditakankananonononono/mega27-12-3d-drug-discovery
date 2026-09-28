#!/usr/bin/env python3
"""12B prep: meeko vina-typed ligands, warhead C->Cl retype, GPF+autogrid maps.
Prereg: docs/PREREG_CONSTRAINT_GUIDED_12B_20260928.md (committed 3d48644). Pre-outcome."""
import json, os, subprocess, sys
from rdkit import Chem
from meeko import MoleculePreparation, PDBQTWriterLegacy

ROOT = '/home/sandbox/work/12'
COV = f'{ROOT}/studies/covalent'
OUT = f'{ROOT}/studies/constraint12b'
AUTOGRID = f'{ROOT}/bin/ad4/autogrid4'

JOBS = {
 '7vh8': dict(sdf=f'{COV}/nirmatrelvir.sdf', warhead=30, rec=f'{COV}/7vh8_rec_rigid.pdbqt',
              center=(-19.054, 15.539, -31.610)),
 '7c6s': dict(sdf=f'{COV}/boceprevir.sdf', warhead=27, rec=f'{COV}/7c6s_rec_rigid.pdbqt',
              center=(-19.915, -21.076, 0.485)),
}

report = {}
for tag, j in JOBS.items():
    mol = Chem.MolFromMolFile(j['sdf'], removeHs=False)
    w = mol.GetAtomWithIdx(j['warhead'])
    assert w.GetSymbol() == 'C', (tag, w.GetSymbol())
    wxyz = mol.GetConformer().GetAtomPosition(j['warhead'])
    prep = MoleculePreparation()
    setups = prep.prepare(mol)
    pdbqt, is_ok, err = PDBQTWriterLegacy.write_string(setups[0])
    assert is_ok, err
    # coordinate-match the warhead among ATOM lines
    lines, hit = pdbqt.splitlines(keepends=True), []
    for i, ln in enumerate(lines):
        if ln.startswith(('ATOM', 'HETATM')):
            x, y, z = float(ln[30:38]), float(ln[38:46]), float(ln[46:54])
            if abs(x-wxyz.x) < 1e-3 and abs(y-wxyz.y) < 1e-3 and abs(z-wxyz.z) < 1e-3:
                hit.append(i)
    assert len(hit) == 1, (tag, len(hit))
    i = hit[0]
    old_type = lines[i][77:].strip()
    lines_cl = list(lines)
    lines_cl[i] = lines[i][:77] + 'Cl'.ljust(2) + '\n' if lines[i].endswith('\n') else lines[i][:77] + 'Cl'
    open(f'{OUT}/{tag}_lig_true.pdbqt', 'w').write(pdbqt)
    open(f'{OUT}/{tag}_lig_cl.pdbqt', 'w').write(''.join(lines_cl))
    types = sorted({ln[77:].strip() for ln in lines_cl if ln.startswith(('ATOM', 'HETATM'))})
    assert types.count('Cl') == 1 and old_type != 'Cl', (tag, types)
    report[tag] = {'warhead_sdf_idx': j['warhead'], 'warhead_xyz': [round(wxyz.x,3), round(wxyz.y,3), round(wxyz.z,3)],
                   'old_type': old_type, 'types': types}
    maplines = ''.join(f"map {OUT}/{tag}_std.{ty}.map\n" for ty in types)
    gpf = (f"npts 64 64 64\n"
           f"gridfld {OUT}/{tag}_std.maps.fld\nspacing 0.375\n"
           f"receptor_types A C HD N NA OA SA\n"
           f"ligand_types {' '.join(types)}\nreceptor {j['rec']}\n"
           f"gridcenter {j['center'][0]:.3f} {j['center'][1]:.3f} {j['center'][2]:.3f}\nsmooth 0.5\n"
           + maplines +
           f"elecmap {OUT}/{tag}_std.e.map\ndsolvmap {OUT}/{tag}_std.d.map\n"
           f"dielectric -0.1465\n")
    open(f'{OUT}/{tag}_std.gpf', 'w').write(gpf)
    r = subprocess.run([AUTOGRID, '-p', f'{OUT}/{tag}_std.gpf', '-l', f'{OUT}/{tag}_std.glg'],
                       capture_output=True, text=True)
    report[tag]['autogrid_rc'] = r.returncode
    assert r.returncode == 0, (tag, r.stdout[-2000:], r.stderr[-2000:])
    maps = sorted(f for f in os.listdir(OUT) if f.startswith(f'{tag}_std.') and f.endswith('.map'))
    report[tag]['maps'] = maps

print(json.dumps(report, indent=1))
