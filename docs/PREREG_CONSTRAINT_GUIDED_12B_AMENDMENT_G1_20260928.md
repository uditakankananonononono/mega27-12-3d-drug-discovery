# Amendment preregistration: 12B corrected G1 integrity gate (well recovery) - 2026-09-28, ~09:30 IST

Status: PRE-OUTCOME. No docking outcome of any 12B arm exists under the original
lock 3d48644 at the time of this amendment. Required by the parent's adjudication
of 2026-09-28 09:23 IST (option (ii): NEW dated amendment committed before any
arm executes). Amends docs/PREREG_CONSTRAINT_GUIDED_12B_20260928.md (3d48644);
everything not amended below carries over unchanged.

## (1) False premise in the locked G1, recorded exactly

Original-lock G1 presumed that score-only evaluation of one fixed input pose via
compute_vina_maps and via load_maps (the unmodified locked AD4 map set) would
agree within 0.05 kcal/mol per complex under sf=vina. Executed pre-outcome with
the source-built Vina 1.2.7 binary (commit 94f5be5), the comparison measured:
- 7VH8: compute_vina_maps 168.832 vs load_maps 6543.344 kcal/mol; abs diff
  6374.512 against the locked tolerance 0.05 - FAIL.
- 7C6S: compute_vina_maps 118.719 vs load_maps 5454.827 kcal/mol; abs diff
  5336.108 - FAIL.
The two paths are different potential sets evaluated differently (vina-computed
grids vs autogrid AD4-potential maps), so the comparison is invalid as a
pipeline-equivalence check: the gate's premise was false, not the constraint.
The runner aborted per locked conduct BEFORE any arm executed; no outcome of any
arm exists under that gate.

Root-cause record (corrections):
- The 08:02 engine-substitution amendment recorded "the Vina 1.2.7 python
  machinery cannot load AD4-format maps in this environment". Correction
  (runlog, 2026-09-28 ~09:20 IST): the wheel was NOT defective. With sf_name
  vina, load_maps (cache::read in the v1.2.7 source) discovers map files by
  X-Score type names (<prefix>.C_H.map, <prefix>.Cl_H.map, ...), not AD4 type
  names; the from-source build behaves identically. Map discovery is fixed by
  XS-named byte-identical views of the locked map sets (map VALUES untouched;
  committed as symlinks): C_H/C_P<-C, N_P/N_D<-N, N_A/N_DA<-NA,
  O_P/O_D/O_A/O_DA<-OA, F_H<-F, Cl_H<-Cl. The locked Gaussian well remains on
  the Cl map (Cl_H view) only.

## (2) Replacement G1 (locked now, before any gate run or arm execution)

Well-recovery gate, analogous to the AD4-amendment G1:
- Pose: the committed anchored Cl-typed gate pose per complex
  (studies/constraint12b/7vh8_g1_pose_cl.pdbqt, 7c6s_g1_pose_cl.pdbqt): the
  Cl-typed ligand translated so its single warhead Cl atom sits exactly on the
  locked crystallographic SG target. Anchoring at the constraint target makes
  the expected signal about -3.0 kcal/mol, so the gate is sensitive (a pose far
  from the target would have expected signal ~0 and the gate would be vacuous).
- Measurement: score-only evaluation of that pose with the source-built Vina
  1.2.7 binary (vina --score_only --maps) against (i) the unmodified XS map set,
  run twice - the two runs must agree exactly (determinism) - and (ii) the
  biased XS map set. Seed 77000 for all three scorings (scoring is
  deterministic; the seed is recorded for reproducibility).
- Expected delta: computed numerically as the trilinear interpolation of
  (biased Cl map - unmodified Cl map) at the warhead coordinate from the
  committed map files (65 grid points per axis, spacing 0.375 A, locked
  gridcenters) - the same formulation as the AD4 gate.
- PASS criterion (locked): the two unmodified scorings agree exactly AND
  |(E_biased - E_unmodified) - expected_delta| <= 0.05 kcal/mol.
- G2 (only-Cl-map-differs byte audit) and G3 (self-RMSD 0.0) are unchanged and
  rerun. Gate results are written to studies/constraint12b/gates_vinacli2.json;
  the failed-gate record gates_vinacli.json is preserved unchanged.

## (3) Elements carried over unchanged from the original 12B lock

Question; complexes; committed inputs and their SHA-256s; crystallographic
attachment geometry and warhead atom identities; constraint implementation
(warhead C->Cl retyping, single Cl per ligand asserted; Gaussian well
E_add(p) = -3.0*exp(-(d/0.75)^2) kcal/mol added to the Cl map only, centered on
the locked SG targets; depth/width locked, never tuned; biased map VALUES
unchanged - the XS views are byte-identical); same 24 A boxes (npts 64,
spacing 0.375 A, locked gridcenters); arms A0/A1/A2; seeds 77000+s for
s = 0,1,2; vina exhaustiveness 32, n_poses 20, cpu 2, 300 s wall-clock cap;
RMSD criterion and decision rule (best-energy pose, heavy atoms,
symmetry-corrected minimum over MCS automorphisms, no superposition, receptor
frame retained; PASS iff RMSD <= 2.0 A in >= 2 of 3 seeds per complex; both
PASS = SUPPORTED, one = mixed reported as measured, zero = NOT SUPPORTED with
12A the only adjudicated pivot). Engine: AutoDock Vina 1.2.7 built from source
(tag v1.2.7) - the originally locked engine version, now executable.

## (4) Disclosure (locked)

The paper must disclose the original-lock G1 false premise and this corrected
gate alongside the 12B result, including the map-naming root cause and the
correction that the wheel was not defective.

## Conduct

No threshold, parameter, seed, or criterion moves after any A2 outcome is read.
Gates run before any arm; the runner aborts on any gate failure. If this
corrected G1 FAILS (well not recovered), the constraint-guided question is
declared machinery-exhausted with all four failures documented (wheel-era map
discovery blocker; AD4 substitution constraint-delivery failure; original-lock
G1 false premise; corrected-G1 failure) and 12A starts only then, under a NEW
dated prereg, per the parent's 09:23 IST adjudication. Post-hoc observations are
labeled descriptive and cannot restore a failed gate. Deliverables unchanged:
runlog, results json, scripts under studies/constraint12b/, queue item-6
addendum, paper paragraph (reported as measured either way, with the gate
history disclosed).
