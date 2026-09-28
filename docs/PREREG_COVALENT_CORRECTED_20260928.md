# Preregistration: corrected-parameterization covalent self-redock branch (lane 12, item 6 follow-up)

Dated 2026-09-28 IST. Committed before any outcome-producing run of this branch.
Parent authorization for the corrected-rerun branch received 2026-09-28 05:43 IST.

## Relationship to the locked result (read first)

The bounded locked-protocol audit (prereg PREREG_COVALENT_BOUNDED_20260928.md,
outcome commit 3158ea1) FAILED its locked criterion for both complexes and that
verdict stands permanently as the item-6 result: it is never rewritten,
superseded, or re-gated by anything in this branch. This document opens a NEW,
separate experiment whose outcomes are reported separately and labeled as the
corrected-parameterization branch.

## Why this branch exists

Post-hoc inspection of the locked run records (documented in
COVALENT_RUNLOG_20260928.md) found that the locked input generator wrote the
generic intnbp_r_eps pair minima between the flexible-sidechain marker atoms
(X1..X4) and ligand atom types as Rij = Rii_X + Rii_L. The standard AD4
combining rule is the arithmetic mean, Rij = (Rii + Rjj)/2 (engine evidence:
parse-time warnings that 8.00/7.09/7.50/7.20 A exceed the engine's 0.90-6.00 A
sanity range; 7VH8 docked energies of +4e6 kcal/mol are physically absurd).
The locked negative is therefore at least partly a parameterization artifact.
Whether the reactive-docking setup can self-redock at all under the standard
combining rule is an open question this branch answers.

## Locked protocol (identical to the bounded branch except ONE parameter class)

Everything below is copied unchanged from the locked bounded protocol; the ONLY
change is item (*):

- Complexes: 7VH8 (SARS-CoV-2 Mpro + nirmatrelvir, adduct 4WI) and 7C6S
  (Mpro + boceprevir, adduct U5G); identities verified against RCSB.
- Free-ligand inputs: PubChem 3D SDFs as recorded in the runlog; receptors:
  chain A, altloc A; flexible Cys145 sidechain; same PDBQTs.
- Grid: 24 A box, center projected 5 A from CB along the CA-CB bond,
  spacing 0.375 A.
- Search: 3 seeds per complex (DPF seed pairs 77000+s / 88000+s, s = 0,1,2),
  10 LGA runs per seed, ga_num_evals 1,000,000, pop 150, Solis-Wets local
  search (parameters as in the committed DPFs).
- (*) Generic X-pair intnbp_r_eps values use the standard AD4 arithmetic-mean
  combining rule Rij = (Rii + Rjj)/2 with epsij = sqrt(eps_i eps_j), 12-6.
  Concretely: X1/X2 (from C, Rii 4.00): C 4.00, C2 4.00, C3 4.00, F 3.545,
  HD 3.00, N 3.75, N3 3.75, N5 3.75, OA 3.60, O5 3.60, O6 3.60;
  X3 (from SA, Rii 4.00): C 4.00, C2 4.00, C3 4.00, F 3.545, HD 3.00, N 3.75,
  N3 3.75, N5 3.75, OA 3.60, O5 3.60, O6 3.60;
  X4 (from HD, Rii 2.00): C 3.00, C2 3.00, C3 3.00, F 2.545, HD 2.00, N 2.75,
  N3 2.75, N5 2.75, OA 2.60, O5 2.60, O6 2.60.
  The four hand-set reactive overrides are UNCHANGED: X3-C1 13-7 (1.8 A,
  eps 2.5), X1-C1 and X2-C1 12-6 (2.0 A), X4-C1 near-zero.
- Locked success criterion (unchanged): best-energy-pose heavy-atom RMSD
  <= 2.0 A against the crystallographic ligand in at least 2 of 3 seeds per
  complex counts as "self-redock succeeds" for that complex; a failure is
  reported as a plain negative. No superposition (receptor frame retained).
- Locked analysis (unchanged): studies/covalent/rmsd_analysis.py as committed
  at 3158ea1 (coordinate-free serial -> SMILES -> MCS matching,
  symmetry-corrected). No matcher changes after this lock; if the matcher
  crashes, engineering fixes are documented in the runlog before outcomes and
  never alter the criterion.

## Deliverables

results/covalent_redock_corrected.json, a runlog appendix, a queue addendum
line clearly marked as the corrected-branch outcome (the item-6 verdict line
keeps the locked negative), and a paper subsection addendum reporting this
branch either way (success or plain negative), with the parameterization
history stated plainly.

## Out of scope

No other parameter, input, seed, grid, or criterion changes. No activity
ranking, no cross-structure docking. Any further deviation requires a new
dated prereg before outcomes.
