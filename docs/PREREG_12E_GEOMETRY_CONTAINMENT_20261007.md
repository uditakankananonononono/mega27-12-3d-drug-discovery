# Preregistration 12E - geometry/containment audit of the 7C6S crystal-in-grid anomaly
Dated 2026-10-07, locked before any 12E score is read. Approved under the user's delegated
pick (WhatsApp 2026-10-07 8:39:11 PM IST, "You do what you want", relayed by main at
8:39:54 PM IST) to the 12E proposal sent earlier that evening.

## Question
D5 found the 7C6S crystal-fit pose implausible in the exact 12A grid (+18.80 kcal/mol,
vs a docked C1 range of -14.42 to -10.27), with two stated caveats: a 1.377 A rigid-fit
conformer mismatch and one crystal atom 0.274 A outside the 24 A box. 12E asks whether
input geometry and/or box containment explain that anomaly. It does not ask whether 12A
becomes supported; it changes no prior verdict, threshold, or result.

## Frozen inputs (four score-only runs per complex, both 7C6S and 7VH8)
Pose A: the committed D5 crystal-fit pose (studies/nativecov12d/d5/{tag}_crystalfit.pdbqt),
the exact artifact that produced the D5 scores.
Pose B: geometry-corrected pose - matched atoms placed at exact crystal coordinates using
the coordinate-identity mapping of amendment 2 (D7); unmatched atoms keep their Pose A
rigid-fit positions. Atom names, types, and charges are identical to Pose A by construction.
Box 0: the exact original 24 A maps (studies/nativecov12a/{tag}_rec_rigid.*).
Box 1: expanded maps regenerated with autogrid4 from the same receptor PDBQT, same
parameter file, same spacing (0.375 A), same gridcenter, and npts = 2*ceil((m + 1.0)/0.375)
where m is the largest absolute coordinate offset of any crystal-ligand heavy atom from the
gridcenter (the D3 atom set). The 1.0 A margin matches the locked D3 margin rule. This rule
is applied identically to both complexes; expected npts are 72 (7C6S, m = 12.274) and 68
(7VH8, m = 11.724). Only npts changes.
Scoring: autodock4 epdb, intermolecular energy only, same dpf protocol as D5 (about = pose
centroid, seed 12345, intelec). The receptor, score function, and all map values are
unchanged; no docking, search, seed search, or parameter tuning occurs.

## Gates and geometry checks (frozen)
G1 reproducibility: Pose A scored on Box 0 must reproduce the D5 epdb intermolecular
energies (-10.39 7VH8, +18.80 7C6S kcal/mol) within 0.01 kcal/mol. On failure, abort
before any other score is read.
G2 paired control: for 7VH8, Pose A and Pose B must remain plausible (see rule below) in
both boxes. If any 7VH8 run flips to implausible, the expansion/geometry procedure itself
is confounded; the 7C6S expanded and geometry arms are then uninterpretable and the outcome
is MACHINERY-CONFOUNDED.
Geometry audit (reported, not gated): per-atom outside-box counts and minimum margins for
both poses in both boxes; Pose B matched-atom RMSD to crystal must be 0.0 by construction;
the D4b mirror test (no mirror flag in any arm) is cited, not rerun.
Identity check: Pose B PDBQT lines must equal Pose A except for coordinate fields.

## Plausibility rule and classification table (frozen)
A pose is PLAUSIBLE under the D5 rule: epdb intermolecular energy <= 0 AND <= the worst
(highest) pooled docked C1 intermolecular energy for that complex. Otherwise IMPLAUSIBLE.
For 7C6S, reading Pose A Box 0 as the reference (expected IMPLAUSIBLE via G1):
- R1 CONTAINMENT-RESCUE: Pose A becomes PLAUSIBLE only in Box 1.
- R2 GEOMETRY-RESCUE: Pose B becomes PLAUSIBLE already in Box 0.
- R3 JOINT-RESCUE: only Pose B in Box 1 is PLAUSIBLE.
- R4 NO-RESCUE: no variant reaches PLAUSIBLE.
Score deltas are reported descriptively; classification uses only the plausibility rule.
G2 failure replaces the classification with MACHINERY-CONFOUNDED.

## Reading (frozen, pre-outcome)
R1/R2/R3 says the anomaly is explained by input geometry and/or containment and motivates a
separately preregistered confirmation redock proposal; it does not rescue or alter any 12A
verdict. R4 says geometry/containment does not explain it and motivates a separately
approved receptor/covalent-adduct preparation study. Neither outcome retroactively changes
12A-12D or proves a receptor-chemistry cause. 7VH8 exists in this study only as the paired
control. Judge-lane review is post-hoc and archived; it informs the next pivot, not 12E.
