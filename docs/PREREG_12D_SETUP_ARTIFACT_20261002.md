# Preregistration 12D - setup-artifact test of the 12A pose band (dated 2026-10-02)

Status: LOCKED 2026-10-02 01:57 IST on parent confirmation (commit 5701ab5), before any 12D quantity was computed.
Amendment 1 (below) was added at 02:00 IST before any amendment quantity was computed.
Nothing in the amendment has been computed at the time of this text.
The 12A verdict (NOT SUPPORTED) and 12C result (crystal pose never sampled, 0/30 <= 3.0 A
per arm, all poses 5.0-6.5 A) stay as measured. This is a new question and cannot restore
a failed 12A gate.

## Question
Is the 12A pose band explained by a setup artifact (reference frame, atom mapping, or
search-box placement) rather than by docking science?

## Diagnostics (engine-independent, cheap, analysis only; run per complex 7VH8 and 7C6S)
D1 matcher self-test: place the crystal adduct coordinates on the free-ligand serials via the
   12A matcher (MCS-matched heavy atoms), score with the 12A sym_rmsd function. Expected ~0.
   FAIL if > 0.05 A, or if fewer MCS-matched heavy atoms than the 12A analysis used (37 for
   nirmatrelvir/7VH8 and 37 as reported for both complexes).
D2 receptor frame: every heavy atom of studies/nativecov12a/<tag>_rec_atoms.pdb matched by
   (chain, resname, resnum, atom name) to the crystal PDB used for the crystal ligand
   (the same file). FAIL if any matched atom differs by > 0.05 A, or no match.
D3 search box: the grid box is centered at JOBS[tag]['center'] with edge 24 A (+/- 12 A). FAIL
   if any crystal ligand heavy atom lies outside the box on any axis (|coord - center| > 12 A)
   or within 1.0 A of an edge (edge margin < 1.0 A).
D4 offset signature (descriptive only, not a pass/fail): per arm, over the 30 sampled poses
   (12C pooling), report mean pose-to-crystal centroid offset vector, its magnitude, and the
   RMSD after translation-only centroid alignment; flags a common-direction offset when
   |mean offset| >= 0.8 x mean |offset|.

## Decision (locked)
ARTIFACT FOUND if D1, D2 or D3 FAILS for either complex. Then only the specific failed item
is corrected, and exactly one confirmation job is run: 7VH8 C2 seed 77000 with unchanged
search parameters (nrun 10, nev 1000000, ngen 27000, psize 150, lsit 300) and unchanged
official v1.6 CPU build and POCL cbs stack. CONFIRMED if its best-energy-pose RMSD <= 2.0 A
under the corrected setup; otherwise NOT CONFIRMED (artifact present but insufficient).
The confirmation costs about 6-7 h CPU unthrottled; it starts only after parent go-ahead.
NO ARTIFACT FOUND if D1-D3 pass for both complexes: the 12A negative stands as science,
12D stops, and no re-dock is run. D4 is reported either way and cannot change the verdict.
Thresholds above (0.05 A, 12 A half-edge, 1.0 A margin, 2.0 A, 0.8) are locked now.

## Pre-declared limits
- A confirmed artifact would not retroactively change the 12A preregistered verdict; it would
  justify a NEW dated prereg to re-run the 12A queue with the corrected setup.
- If a diagnostic cannot be computed (missing file, ambiguous atom naming) it is reported as
  MACHINERY-INCOMPLETE and treated as not passed for the artifact decision only if that
  item is the sole failure; otherwise the decision follows the computable items.
- Judge-lane review is post-hoc and archived; it informs the next pivot, not 12D numbers.

## Amendment 1 (2026-10-02, pre-outcome for these checks; from parent relay of an independent judge-lane review)
Diagnostics D1b, D3b, D4b, D5, D6 are added, all descriptive/diagnostic and locked below. They
run in parallel with the confirmation job (7VH8 C2 seed 77000, box 28.5 A = 76 grid points at
0.375 A spacing, built in studies/nativecov12d; receptor config verified canonically equal to the
12A config, only line order differs). The box edge was chosen after seeing D3 numbers (min margin
0.276 A / -0.274 A) and before any run; it gives 2.5 A margin.
D1b mapping hardening: for each arm's 30 poses (12C pooling) report best-mapping RMSD (sym_rmsd) vs
   the RMSD under the first MCS mapping only; also confirm DLG ligand atom-name order equals the
   PDBQT atom order used for serials. MAPPING SENSITIVE if median (first-mapping minus best) > 0.5 A.
D3b distances: crystal-adduct warhead carbon to box center, and to Cys145 SG, and warhead-SG distance.
D4b rigid alignment: per pose, Kabsch rotation+translation RMSD on matched atoms, and the same after
   inverting the pose through its centroid (mirror test). FLAG MIRROR if min mirrored RMSD <= 2.0 A and
   min unmirrored > 3.0 A. Report min and median per arm.
D5 crystal-in-grid: fit the standard (C1) free ligand to the crystal matched atoms (Kabsch), then score it
   with autodock4 energy evaluation in the same 12A rigid maps (24 A box, C1 setup). Report inter- and
   intra-molecular energy and RMSD of the fit. CRYSTAL POSE IMPLAUSIBLE IN GRID if inter-molecular energy
   > 0 kcal/mol (clash) or worse than the worst docked C1 pose's final intermolecular energy in the
   30 pooled poses. If autodock4 cannot evaluate it, D5 is MACHINERY-INCOMPLETE (no substitute).
D6 positive control: redock one non-covalent Mpro complex end to end through the same v1.6 CPU/POCL cbs
   engine with the 12A search parameters (nrun 10). PIPELINE OK if best-energy-pose RMSD <= 2.0 A;
   PIPELINE SUSPECT otherwise. The complex is chosen from the lane's existing 7KX5 redock set.
Early-kill rule: if D5 reports CRYSTAL POSE IMPLAUSIBLE or D6 reports PIPELINE SUSPECT, the box is not
the sole culprit; the confirmation job is stopped early and that is reported with the numbers.
No threshold moves after outcomes.
