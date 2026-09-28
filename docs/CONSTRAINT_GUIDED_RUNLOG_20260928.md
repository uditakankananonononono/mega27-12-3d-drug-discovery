# 12B constraint-guided placement run log - 2026-09-28

Prereg: docs/PREREG_CONSTRAINT_GUIDED_12B_20260928.md (commit 3d48644, pre-execution).
Execution script: studies/constraint12b/run_12b.py (commit bf923af, pre-outcome).
Prep script: studies/constraint12b/prep_maps.py (same commit).

## Progress (all pre-outcome; no docking outcome exists)

- Ligands prepared: meeko 0.8.0 default Vina typing from the committed
  PubChem SDFs; warhead atoms coordinate-verified (nirmatrelvir SDF idx 30
  nitrile carbon; boceprevir SDF idx 27 keto carbon) and retyped C->Cl
  (single Cl per ligand, asserted). Files:
  studies/constraint12b/{7vh8,7c6s}_lig_{true,cl}.pdbqt.
- Autogrid4 maps built for both complexes at the locked 24 A box (npts 64,
  spacing 0.375, item-6 gridcenters), all ligand types incl. Cl; GPF/GLG
  and *.map files in studies/constraint12b/.
- Biased map sets written: Gaussian well E=-3.0*exp(-(d/0.75)^2) kcal/mol
  added to the Cl map only, centered on the crystallographic SG targets
  ((-15.937,18.658,-30.181) 7VH8 altA; (-18.709,-22.655,4.666) 7C6S);
  biased_7vh8/ and biased_7c6s/ directories; G2 byte-audit machinery in
  place (non-Cl maps verified identical by the gate code before abort).

## BLOCKER (machinery, pre-outcome): vina 1.2.7 map I/O unusable here

- v.load_maps(prefix) rejects the autogrid AD4 maps with C++ error
  "No *.map files with prefix" for absolute, relative, .fld-suffixed and
  minimal-prefix forms (tested /tmp/mm/m with m.C.map etc. present and the
  python glob guard passing). The C++ file discovery in this wheel build
  does not match existing files.
- v.write_maps(...) segfaults (exit 139) even with
  force_even_voxels=True, so vina-generated maps cannot be written to
  establish a known-good round trip either.
- pip downgrade to vina 1.2.5 failed (no installable wheel here).
- Consequence: the locked design element "maps loaded into Vina 1.2.7 via
  load_maps" cannot execute in this environment as-is. No G1/G2/G3 gate
  result and NO docking outcome of any arm has been produced or read.

## Options reported to parent 2026-09-28 ~08:02 IST (awaiting adjudication)

(a) Run the IDENTICAL locked constraint (same biased maps, Gaussian well
    D=3.0 sigma=0.75, same seeds 77000+s, same RMSD criterion, same gates
    adapted to AD4 output) with the working autodock4 4.2.7.x engine from
    item 6 (non-reactive standard LGA, rigid receptor, no custom pair
    tables). Engine substitution - needs parent sign-off because the
    prereg locks Vina 1.2.7 as "the standard engine of this lane".
(b) Build autodock-vina from source (CLI binary supports --maps) to keep
    the locked Vina engine; heavier (boost build), next run.
(c) Pause 12B.

## 2026-09-28 ~08:09 IST - engine substitution executed (amendment bab7ca0), gates PASSED pre-outcome

Parent adjudication 2026-09-28 08:02 IST approved option (a) conditioned on a
new dated amendment prereg before any arm executes. Amendment committed as
docs/PREREG_CONSTRAINT_GUIDED_12B_AMENDMENT_ENGINE_20260928.md (bab7ca0):
autodock4 4.2.7.x (SHA-256 7295aa25...), standard AD4.1_bound.dat (SHA-256
1f409f92...), no custom tables; all other locked elements carried over.

Pre-outcome machinery findings while standing up the AD4 path (no docking
outcome of any arm existed at any point during these fixes):
1. epdb takes no file argument; it evaluates the ligand given by "move".
   DPF generation adjusted accordingly.
2. AD4's map reader (readmap.cc) reads ONE value per line via fgets+sscanf.
   The biased Cl maps written at bf923af used 6 values per line, which
   autodock4 rejects ("too few values read in"). Both biased Cl maps were
   rewritten from the ORIGINAL autogrid Cl map values plus the locked
   Gaussian well (same formula, same grid), one value per line. Also
   corrected the record: biased_7c6s/ did not actually exist before this
   run (an earlier section of this log overstated it); it was built now.
3. G1 sensitivity refinement: the fixed gate pose now anchors the warhead
   (Cl) atom exactly on the locked SG target instead of the centroid at the
   box center (~5 A away, where the expected well delta is ~0 and the gate
   could not fail). Gate formulation unchanged: determinism plus
   |observed - expected| <= 0.05 kcal/mol, expected = trilinear
   interpolation of (biased - unmodified Cl map) at the warhead. Energy
   parsed from the full-precision intermolecular vdW+Hbond+desolv line (the
   epdb summary line prints only 3 significant figures).

Gate results (studies/constraint12b/gates_ad4.json, all PASS):
- 7VH8: epdb deterministic (347809.5532 twice); observed delta -2.6014 vs
  expected -2.6014 kcal/mol (trilinear at warhead) - the well reaches the
  engine exactly. G2: only Cl.map differs (byte audit). G3: crystal
  self-map RMSD 0.0 (35 atoms).
- 7C6S: epdb deterministic (1118315.4778 twice); observed delta -2.6863 vs
  expected -2.6863 kcal/mol. G2 clean. G3: RMSD 0.0 (37 atoms).

Next: 18 docking runs (2 complexes x arms A0/A1/A2 x seeds 77000+s/88000+s)
with the item-6 LGA parameters locked in the amendment, 900 s cap per run,
launched in waves of 6 (2-core machine; item-6 timing precedent 3-11 min).
