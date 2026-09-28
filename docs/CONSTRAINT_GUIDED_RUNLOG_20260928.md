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
