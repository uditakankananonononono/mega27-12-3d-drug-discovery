# Amendment preregistration: 12B engine substitution (Vina 1.2.7 -> autodock4 4.2.7.x) - 2026-09-28, ~08:05 IST

Status: PRE-OUTCOME. No docking outcome of any 12B arm exists at the time of
this amendment. This amendment was required by the parent's adjudication
message of 2026-09-28 08:02 IST, which approved option (a) from the blocker
report conditioned on this amendment landing before any arm executes. It
amends docs/PREREG_CONSTRAINT_GUIDED_12B_20260928.md (commit 3d48644);
everything not amended below carries over unchanged.

## (1) Reason for engine substitution (locked statement)

The Vina 1.2.7 python machinery cannot load or write AD4-format maps in this
environment, as documented in docs/CONSTRAINT_GUIDED_RUNLOG_20260928.md:
- v.load_maps(prefix) fails in C++ file discovery ("No *.map files with
  prefix") for absolute, relative, .fld-suffixed and minimal prefixes, with
  the map files present and the python-side glob guard passing.
- v.write_maps(...) segfaults (exit 139) even with force_even_voxels=True.
- pip install vina==1.2.5 failed: no installable wheel here.
The locked design element "maps loaded into Vina 1.2.7 via load_maps" is
therefore not executable as-is. This is a machinery failure, not an outcome.

## (2) Substitute engine (locked)

autodock4 4.2.7.x, the item-6 build: bin/ad4/autodock4, SHA-256
7295aa259b8bdc167ca43b080f8f6877e3f611942b093d8c46ec566c05c16c80
(autogrid4 companion, already used for the locked maps:
554cd9935584db3b4e9be022aef04cea3de21975ab70a36f3b3a5cdf20aacfc3).
Non-reactive, standard Lamarckian GA, rigid receptor, NO custom pair tables:
the standard project parameter file AD4.1_bound.dat is used (copied from the
build tree to studies/constraint12b/AD4.1_bound.dat, SHA-256
1f409f928669d639e99d05375eb4bfe9a65d8e87fc16b88fa199e3b70a642fab).
All 12B ligand atom types are standard AD4 types covered by this file
(7VH8: C F HD N NA OA Cl; 7C6S: C HD N OA Cl; Cl parameter line present:
atom_par Cl 4.09 0.276 ...).

## (3) Elements carried over unchanged from the original 12B lock

- Question, complexes, committed inputs and their SHA-256s (prereg 3d48644).
- Crystallographic attachment geometry and warhead atom identities.
- Constraint implementation: warhead C->Cl retyping (single Cl per ligand,
  asserted), Gaussian well E_add(p) = -3.0*exp(-(d/0.75)^2) kcal/mol added
  to the Cl map only, centered on the locked SG targets; depth/width locked,
  never tuned. Biased map sets already built pre-outcome at commit bf923af.
- Same 24 A boxes: npts 64, spacing 0.375 A, gridcenters
  (-19.054, 15.539, -31.610) 7VH8 and (-19.915, -21.076, 0.485) 7C6S.
- Same seeds: 77000+s for s = 0,1,2 (realized as DPF seed pairs
  77000+s / 88000+s, the item-6 convention).
- Same RMSD criterion and decision rule: best-energy pose, heavy atoms,
  symmetry-corrected minimum over MCS automorphisms (item-6 v2 convention),
  no superposition (receptor frame retained); PASS iff best-energy-pose
  RMSD <= 2.0 A in >= 2 of 3 seeds per complex; both PASS = SUPPORTED,
  one = mixed (reported as measured), zero = NOT SUPPORTED with 12A the
  only remaining adjudicated pivot.
- Arms: A2 constrained (Cl ligand + biased maps), A1 typing control
  (Cl ligand + unmodified maps), A0 baseline (true-type ligand +
  unmodified maps).
- No-threshold-movement conduct.

## Tooling-mapped parameters (locked now, engine substitution only)

- Search budget: vina exhaustiveness 32 / n_poses 20 is replaced by the
  item-6 locked AD4 search: ga_run 10 LGA runs per seed, ga_pop_size 150,
  ga_num_evals 1000000, ga_num_generations 27000, elitism 1, mutation 0.02,
  crossover 0.8, Solis-Wets local search (sw_max_its 300, max_succ 4,
  max_fail 4, rho 1.0, lb_rho 0.01, ls_search_freq 0.06), unbound_model
  bound, tran0/quaternion0/dihe0 random, torsdof 9 (7VH8) / 11 (7C6S) from
  the committed ligand PDBQTs, cluster analysis default rmstol 2.0 A.
  Best-energy pose per seed = docked model with the lowest estimated free
  energy across that seed's ga_run models.
- Wall-clock cap: 900 s per autodock4 invocation (replaces the 300 s vina
  wrapper convention; item-6 AD4 invocations took 3-11 min).

## Adapted integrity gates (locked; all before any A2 outcome is read)

- G1 (adapted to AD4 tooling) map-to-engine pathway verification: one fixed
  Cl-typed pose per complex (ligand translated so its heavy-atom centroid
  sits at the box center; written pre-outcome), evaluated score-only with
  autodock4 epdb under (i) the unmodified std map set, run twice - the two
  runs must agree exactly (determinism) - and (ii) the biased map set. The
  expected delta is computed numerically as the trilinear interpolation of
  (biased Cl map - unmodified Cl map) at the warhead coordinate from the
  committed map files. G1 passes iff the epdb runs are deterministic AND
  |(epdb_biased - epdb_unmodified) - expected_delta| <= 0.05 kcal/mol.
- G2 (unchanged): only the Cl map differs from autogrid4 output; byte-wise
  audit of every other map file.
- G3 (unchanged, engine-independent): the RMSD matcher maps the crystal
  adduct onto itself (RMSD 0.0) for both complexes before any docked pose
  is analyzed.

## (4) Disclosure (locked)

This is an engine substitution from the original 12B lock (which named Vina
1.2.7 as the standard engine). The paper paragraph for 12B must disclose the
substitution and its machinery reason explicitly, alongside the unchanged
constraint, seeds, and decision rule.

## Conduct

No threshold, parameter, seed, or criterion moves after any A2 outcome is
read. Post-hoc observations are labeled descriptive and cannot restore a
failed gate. If the AD4 arm also fails mechanically, no further substitution
is chosen locally; the parent picks between options (b) source build and
(c) pause. Deliverables unchanged: runlog, results/constraint_guided_12b.json,
scripts under studies/constraint12b/, queue item-6 addendum, paper paragraph
(reported as measured either way, with the substitution disclosed).
