# Covalent branch run log (lane 12, item 6) - 2026-09-28

Prereg: docs/PREREG_COVALENT_BOUNDED_20260928.md (commit af8b5e5, pre-outcome).

## Part A: engine acquisition - SUCCESS within the 60-minute budget

Attempt order per prereg:
1. AutoDock-GPU v1.6 prebuilt linux_x64 OpenCL binary from the project's
   GitHub releases (SHA-256 8a22804c1fde62a59c030a45e8a9d9d960ff329d22e4927daf7464df393b8047).
   Binary runs but cannot dock: clGetPlatformIDs() returns -1001, no OpenCL
   platform is installed on this machine (ICD loader only, no vendor runtime,
   no GPU). Path abandoned.
2. AutoDock4 + AutoGrid4 compiled from the official project sources:
   - github.com/ccsb-scripps/AutoDock4 commit 192ecda05d7c566161046f0a1d604f3336e0cf3a
     -> autodock4 4.2.7.x, binary SHA-256
     7295aa259b8bdc167ca43b080f8f6877e3f611942b093d8c46ec566c05c16c80
   - github.com/ccsb-scripps/AutoGrid commit 6d2847beaeac8ff43ca99094707fd74e3ca1ff37
     -> autogrid4 4.2.8, binary SHA-256
     554cd9935584db3b4e9be022aef04cea3de21975ab70a36f3b3a5cdf20aacfc3
   - Build: autotools (autoreconf -i && ./configure && make -j4). The build's
     csh-only default_parameters.h generation step was replaced with a
     byte-faithful Python equivalent (same egrep/quoting rules), each repo's
     header generated from its own shipped .dat files (they differ: AutoGrid's
     ad4_shared adds Si and B atom parameters).
   - Binaries archived in repo at bin/ad4/ so the branch is reproducible if
     the scratch filesystem is rebuilt.
   Both binaries pass their own version/startup checks.

## Part B: self-redock audit (7VH8, 7C6S) - NOT STARTED at this checkpoint

RCSB identity verification at preregistration time (2026-09-28):
- 7VH8: SARS-CoV-2 main protease + PF-07321332 (nirmatrelvir), 1.59 A.
- 7C6S: SARS-CoV-2 main protease + boceprevir, 1.6 A.

## Part B protocol LOCKED pre-outcome (2026-09-28 ~05:09 IST), runs launched

Free-ligand inputs: the PDB component records 4WI (7VH8) and U5G (7C6S) are the
post-reaction adduct forms (imidate / gem-hydroxyl), so free nirmatrelvir and
free boceprevir 3D SDFs were taken from PubChem instead (recorded here as the
ligand provenance). Receptors: chain A ATOM records, altloc A kept (7VH8 Cys145
has two SG rotamers; the A rotamer is the adduct one per the LINK record);
residues failing meeko templates dropped (7VH8 TYR154 at 27.7 A from SG145,
7C6S ARG222 at 48.7 A; both far outside the 24 A box).

Classic-AutoDock4 wiring findings (why this differs from the AutoDock-GPU
reactive tutorial): AD4.2.7 has no derived-type support and its intnbp_r_eps
tables are indexed by parameter-library map_index, so (a) meeko's 3-character
flex types were renamed to 2 characters (1C3/1C2/1S4/1H5 -> X1/X2/X3/X4),
(b) the custom parameter library gives X1..X4 unique map_index values 100-103,
(c) because flex-atom type pairs get no default pair tables without maps,
intnbp_r_eps lines were generated for every X-type x ligand-type pair using
standard AD4 combining rules (Rij = Rii_X + Rii_L, epsij = sqrt(eps_X eps_L),
12-6), with the four meeko reactive-config pairs overriding: X3-C1 13-7
(1.8 A, eps 2.5, the S-C pseudo-bond), X1-C1 and X2-C1 12-6 (2.0 A), X4-C1
near-zero. Approximation noted: H-bond 12-10 directionality involving the
flex HG (X4) and SA (X3) is approximated as 12-6; the dominant terms for pose
placement are the pseudo-bond and the VdW field.

Locked protocol: per complex, 3 seeds (DPF seed pairs 77000+s / 88000+s,
s = 0,1,2), 10 LGA runs per seed, ga_num_evals 1,000,000, pop 150,
Solis-Wets local search (parameters in the committed DPFs). Grid: 24 A box,
center projected 5 A from CB along the CA-CB bond (meeko
--box_center_off_reactive_res), spacing 0.375 A. Locked success criterion
(from the prereg): best-energy pose heavy-atom RMSD <= 2.0 A against the
crystallographic ligand in at least 2 of 3 seeds = self-redock succeeds;
no superposition (receptor frame retained). RMSD analysis was not written or
run before this lock.

Six docking runs (2 complexes x 3 seeds) launched detached at ~05:10 IST;
results and the RMSD audit land in results/covalent_redock.json on completion.
Inputs and DPFs committed under studies/covalent/.

## 2026-09-28 05:21 IST - 7c6s DPF bug found and fixed (pre-outcome)

First launch: all three 7c6s runs segfaulted during DPF parsing (exit 139,
DLG truncated after the X1-F intnbp_r_eps line). Root cause: the shared
intnbp_pairs.txt and the 7c6s template were generated from the 7vh8 ligand
type list and carried 7vh8-only types (F, N5). Atom type F is absent from the
7c6s ligand (boc_lig.pdbqt types: C C1 C2 C3 HD N N3 O5 O6 OA), and the
unbound-conformation internal-energy pass indexes pair tables by the ligand's
own type list, so the F/N5 pair lines crashed the run. No 7c6s docking
outcome was ever produced, so this fix precedes any outcome for that complex.

Fix: intnbp_pairs_7c6s.txt rebuilt for the 7c6s ligand's actual types. O5/O6
are derived from OA in AD4.1_bound_custom.dat (identical Rii 3.20, eps 0.200),
so the O5/O6 pair lines duplicate the locked OA values; the four reactive
overrides are unchanged (X3-C1 13-7 1.8 A/eps 2.5, X1-C1 and X2-C1 12-6 2.0 A,
X4-C1 near-zero). Coverage check: all 4 X types x all 10 7c6s ligand types =
40 lines, verified programmatically. The locked protocol (grid, box, seeds,
LGA runs x evals, RMSD criterion) is unchanged.

Second issue found on relaunch: the 7c6s seed DPFs had been generated with
{EVALS}/{NRUN} placeholders unsubstituted (the original run had substituted
them only in the 7vh8 DPFs); autodock4 exited 1 with "syntax error in
GA_NUM_EVALS line". Regenerated with ga_num_evals 1000000, ga_run 10, matching
the locked protocol and the 7vh8 DPFs. Relaunched 05:21 IST.

## 2026-09-28 05:41 IST - Part B outcomes: plain negative for both complexes (locked criterion)

Six runs completed (7vh8 seeds 0/1/2 ~05:12-05:15 IST; 7c6s seeds 0/1/2
~05:25-05:36 IST after the pre-outcome DPF fixes above; all exit 0, 10 docked
models per seed).

Analysis-machinery validation (before any RMSD number existed; the locked
criterion itself was never touched):
1. rmsd_analysis.py v1 crashed: its energy regex did not accept '+' signs or
   scientific notation. Fixed ('[-+]?[\d.]+(?:[eE][-+]?\d+)?').
2. v1 matched docked vs crystal atoms by NAME. This could never have worked:
   DLG ligand atom names are bare element symbols (non-unique across atoms),
   while the crystal adduct uses CCD names. Replaced pre-first-outcome with a
   coordinate-free deterministic chain (v2): docked serial -> free-ligand
   SMILES atom (DLG REMARK SMILES IDX table) -> crystal adduct atom (RDKit
   maximum common substructure; element comparison, any bond order,
   ringMatchesRingOnly; adduct connectivity perceived from crystal
   coordinates). RMSD is symmetry-corrected (minimum over MCS automorphism
   assignments, the standard docking-RMSD convention as in obrms). No
   coordinate-derived choice entered the matcher design.

Locked-criterion outcomes (results/covalent_redock.json):
- 7VH8: best-pose RMSD 14.789 / 21.936 / 22.199 A (seeds 0/1/2); 0/3 <= 2.0 A.
  Best-pose energies +4.12e6 / +4.13e6 / +4.17e6 kcal/mol.
- 7C6S: best-pose RMSD 10.830 / 6.926 / 9.376 A; 0/3 <= 2.0 A.
  Best-pose energies -0.94 / -1.91 / -2.30 kcal/mol.
- Verdict: self-redock FAILS for both complexes. Plain negative, reported as
  such in the queue and the paper. Atom-match coverage was complete
  (35/35 and 37/37 heavy atoms), so the negative is not a matching artifact.

Post-hoc parameterization observation (recorded for the record; it cannot
restore or move the locked gate):
- The locked input generator computed intnbp_r_eps pair minima as
  Rij = Rii_X + Rii_L (the formula recorded in the 05:09 protocol lock). The
  standard AD4 combining rule is the arithmetic mean, Rij = (Rii + Rjj)/2
  (e.g., C-C 4.00 A, C-OA 3.60 A from this library), so every generic X-pair
  minimum in the runs was doubled (X1-C 8.00 A, X1-N 7.50 A, X1-OA 7.20 A,
  X4-C 6.00 A). The three reactive overrides (X3-C1 1.8 A 13-7, X1/X2-C1
  2.0 A, X4-C1 near-zero) were hand-set and are not affected by the formula.
- Engine-side evidence predates any outcome inspection: every DLG carries
  parse-time warnings "pairwise distance, Rij, 8.00, is not a very reasonable
  value for the equilibrium separation of two atoms! (0.90 Angstroms <= Rij
  <= 6.00 Angstroms)".
- Consequence visible in the outcomes: 7VH8 docked energies are physically
  absurd (+4.1e6 kcal/mol intermolecular; ligand internal energies up to
  +1.35e4), i.e. the doubled-Rij X atoms act as hard spheres centered on the
  warhead and repel the ligand from the pocket; 7C6S energies are near zero
  with poses 6.9-10.8 A out, consistent with the same repulsion.
- Honest reading: the measured negative is at least partly attributable to
  this locked parameterization error, not only to the reactive-docking
  method. Under the no-post-outcome-changes rule the runs above remain the
  locked-protocol outcome and the negative stands. A corrected-protocol
  rerun (arithmetic-mean Rij) would be a new experiment requiring its own
  dated prereg before any outcome; that decision belongs to the parent/user.

## Corrected-protocol branch (prereg PREREG_COVALENT_CORRECTED_20260928.md) - 2026-09-28 06:10 IST

Execution record:
- Corrected DPFs (arithmetic-mean combining rule: X1-C 4.00 A, X1-N 3.75 A,
  X1-OA 3.60 A, X4-C 3.00 A, etc.; the three hand-set reactive overrides
  unchanged) committed pre-outcome (commit 39b49d1).
- Same pinned seeds (77000/88000 + seed index), same archived binaries, same
  analysis script (v2, committed in 3158ea1) as the locked branch. Six runs
  (2 complexes x 3 seeds), all exit 0, 05:46-06:04 IST.
- Engine-side evidence that the correction was live: every locked DLG carried
  parse-time warnings that Rij 8.00/7.50/7.20 A lies outside the engine's
  0.90-6.00 A sanity range; the corrected DLGs carry no such warning.

Outcome:
- Every computed quantity is byte-identical to the locked branch: all DOCKED
  coordinates, all reported energies, all cluster tables, all six runs. The
  only differing DLG lines are header/footer timestamps, the initial
  pid/time seed line (superseded by the pinned DPF seeds), the DPF> intnbp
  echo lines, and the warnings themselves.
- results/covalent_redock_corrected.json therefore equals the locked JSON:
  7VH8 14.789/21.936/22.199 A, 7C6S 10.830/6.926/9.376 A; 0/3 seeds at or
  below 2.0 A per complex. Verdict under the unchanged locked criterion:
  FAIL - plain negative, reported separately from the locked outcome.

Interpretation correction (supersedes the post-hoc note above where the two
conflict):
- The intnbp X-pair minima are INERT in this engine configuration: the
  doubled locked values and the corrected arithmetic-mean values produced
  identical trajectories and energies everywhere. The post-hoc hypothesis
  recorded above - that the Rii-sum parameterization error contributed to
  the locked failure - is empirically falsified by this branch. The locked
  negative cannot be attributed to that error.
- What produces the failed poses, and 7VH8's reported +4.1e6 kcal/mol
  energies (identical on both branches), inside the reactive setup is
  unidentified. No further post-outcome parameter changes were run.
- The locked-protocol outcome and verdict (commit 3158ea1) stand unchanged;
  this branch is reported separately per the parent's 05:43 IST ruling.

## 12A native covalent engine: build and execution provenance (2026-10-01 15:23 IST)

This section describes the machinery already used by the locked 12A queue,
not a new scientific branch. No docked-pose RMSD or verdict has been read.
The preregistered engine fallback selected the official v1.6 source build
when the prebuilt OpenCL binary could not use this CPU device: the prebuilt
binary requests CL_DEVICE_TYPE_GPU. The upstream DEVICE=CPU build uses the
same official source tag without source modifications. Binary:
bin/adgpu/autodock_cpu_128wi, SHA-256
e43957cd600ab6f44d3ee7ec0340cd22dc8128d115e02eb9dd5ebcefc11ff5a8
(recomputed on 2026-10-01). Source tarball SHA-256, recorded at acquisition:
1d76c7fa6ac15069c69dec3a36e56f5d5585a9b6f66e8a2c7c83a646d48b0a40.
Original build record: d4a4a4263b60ad690db2ba416ca9c16f618eb504.

Runtime is the unprivileged POCL 1.8 CPU OpenCL stack. The default work-group
method crashed in the evolution loop, including a base non-covalent check;
this was not specific to the reactive channel. POCL_WORK_GROUP_METHOD=cbs
allowed the locked reactive smoke to finish. G1-G4 passed for both complexes
before the full docking queue (record 1b658ee603a83cd6eea7c4d7c5e8e1a3b09bd75c).
The analysis metadata's stale reference to the prebuilt binary is corrected
to this actual stack; no search parameter, threshold or verdict rule changes.

At this checkpoint 10 of 12 serial docking jobs have finished rc=0, with no
reported timeout and DLG/XML present: six 7VH8, three 7C6S C1, and 7C6S C2
seed 77000. Seed 77001 is active; seed 77002 is queued. Completed-job count
is execution progress only, not scientific success. VM pauses distort wall
and elapsed timing, so no reliable finish time is claimed. Final analysis
and manuscript results remain pending all 12 jobs.

## 12A result (2026-10-02 01:53 IST)

All 12 docking jobs finished rc=0, no timeouts, DLG/XML present (final job
7C6S C2 seed 77002, DLG run time 24061.884 s; checkpoint 3a830d2). Because
every seed completed, the prereg ("completed seeds") and the analysis code
(complete == 3) agree; no rule choice arose. Analysis: results/native_covalent_12a.json,
run with the locked rule, unchanged.

Best-energy-pose symmetry-corrected RMSD to the crystal pose (A), seeds 0/1/2:
- 7VH8 C1: 5.750 / 5.702 / 5.857 (0 of 3 pass at <= 2.0)
- 7VH8 C2: 5.804 / 5.607 / 5.752 (0 of 3)
- 7C6S C1: 5.531 / 6.043 / 6.038 (0 of 3)
- 7C6S C2: 5.522 / 6.556 / 5.692 (0 of 3)

Verdict by the locked rule: NOT SUPPORTED (zero complexes pass). Reactive
(C2) best energies were lower than standard (C1) in both complexes
(about -12.5 to -14.0 vs -9.8 to -11.3 kcal/mol), but poses were ~5.5-6.6 A
from the crystal, so the energy gain does not reproduce the crystal pose.
Thresholds and rule were not changed after outcomes. Follow-up requires a
new dated prereg.

## 12C result (2026-10-02 01:56 IST; prereg docs/PREREG_12C_SAMPLING_VS_SCORING_20261002.md, commit 1417524)

Q1 (sampling): crystal pose never sampled in any arm. Minimum RMSD over all 30 poses per arm:
7VH8 C1 5.427, 7VH8 C2 5.161, 7C6S C1 5.047, 7C6S C2 5.157 A. Poses <= 2.0 A: 0/30 in every arm; <= 3.0 A: 0/30.
Q2: not applicable (needs adequate sampling). Q3: not run (stop rule). Verdict: sampling failure, not scoring.
Observation (untested, hypothesis only): the narrow spread (all poses 5.0-6.5 A, none lower) fits a systematic
offset (reference frame, matcher or search-box placement) as much as a search failure; a new dated prereg would
be needed to test it. Script: studies/nativecov12a/run_12c.py; output: results/native_covalent_12c.json.

## 12D diagnostics (2026-10-02 01:57 IST; prereg locked in commit 5701ab5; script studies/nativecov12a/run_12d.py; results/native_covalent_12d.json)

D1 matcher self-test: PASS both (self RMSD 0.0 A; 35 atoms 7VH8, 37 atoms 7C6S).
D2 receptor frame: PASS both (2360 / 2323 atoms matched, max deviation 0.0 A).
D3 search box (24 A edge, +/-12 A): FAIL both by the locked margin rule (>= 1.0 A edge margin).
  7VH8: 0 atoms outside, min margin 0.276 A (z extent 11.724 A from center). 7C6S: 1 of 37 crystal
  atoms outside the box (y offset 12.274 A, margin -0.274 A).
D4 (descriptive): common-direction offset flag true for 7VH8 C2 and both 7C6S arms, false for 7VH8 C1;
  mean offset magnitudes 0.81-1.78 A; translation-only-aligned RMSD still 4.88-6.10 A (min 4.882), so a pure
  translation does not explain the band.
Locked decision: ARTIFACT FOUND (D3). Honest reading: the box clips or nearly clips the crystal ligand, a real setup
limit, but translation-aligned RMSDs show it is unlikely to be the whole explanation. The confirmation job tests it.

## 12D amendment 2 result: RMSD atom-mapping defect found, corrected reanalysis (2026-10-02 02:01 IST)

Defect: sym_rmsd looks up docked poses by (SDF heavy-atom index + 1) but poses are keyed by PDBQT ATOM serial; the PDBQT atom
order differs from the SDF order (verified by exact coordinate identity, 35/35 and 37/37 heavy atoms unique, non-identity
permutation). The 12A G4/12D D1 self-tests used the same convention, so they passed vacuously. Prereg: amendment 2 (commit 60f1582,
written before any corrected RMSD). Script: studies/nativecov12a/run_12d_remap.py; output: results/native_covalent_12d_remap.json.
Original 12A numbers (verdict NOT SUPPORTED) and 12C numbers remain in the record unedited.

Corrected best-energy-pose RMSD (A), seeds 0/1/2 [pass count at <= 2.0 A]:
- 7VH8 C1: 1.157 / 1.329 / 1.524 [3/3]; C2: 1.404 / 1.180 / 1.181 [3/3]
- 7C6S C1: 2.879 / 1.173 / 1.663 [2/3]; C2: 2.502 / 4.478 / 2.732 [0/3]
Pooled 30-pose minimum RMSD: 7VH8 C1 1.157, C2 1.173; 7C6S C1 1.173, C2 2.502.
Reading under the unchanged 12A criterion (C2, >= 2 of 3 seeds, per complex): 7VH8 pass, 7C6S fail = MIXED. Whether the corrected analysis
supersedes the original verdict is a parent adjudication. The box-widening confirmation job (7VH8 C2 box 28.5 A) was stopped by the
amendment-2 early-kill rule before completing; its premise is superseded. The 7VH8 result does not depend on the box (crystal inside
the 24 A box), although 7C6S has one crystal atom outside it, which may bear on its C2 result.

## 12B / item-6 sym_rmsd audit (2026-10-02 17:37 IST)

Same PDBQT-serial vs SDF-index defect applies to the 12B code path (run_12b.sym_rmsd, run_12b_ad4, run_12b_vinacli; 12B ligand
PDBQT is byte-identical to the 12A C1 ligand). Re-scored all 18 existing 12B AD4 DLG best-energy poses with the coordinate-identity
remap (no new docking): 7VH8 corrected 14.7-22.9 A (original 14.6-23.4), 7C6S corrected 6.9-9.6 A (original 6.9-8.6); no seed reaches 2.0 A in any
arm; the 12B verdict (not supported / machinery-exhausted) is unchanged. Note the 7VH8 12B energies are ~4e6 kcal/mol (clash-dominated), so those
poses were never credible regardless of mapping. Item 6 (studies/covalent/rmsd_analysis.py) uses its own serial_by_smiles mapping parsed from the
DLG, not this code path; not recomputed, so not shown affected. Not audited: Vina-CLI 12B gates (gates_vinacli*.json used coordinates for
energy checks, not RMSD).

## 12D D6 positive control (2026-10-02 19:42 IST; amendment 1 rule, locked pre-run)

7KX5 / X7V non-covalent redock through the same v1.6 DEVICE=CPU + POCL cbs engine, 12A search parameters (nrun 10, nev 1e6, ngen 27000,
psize 150, lsit 300), seed 77000, 20 A box, rc=0, DLG run time 6965.343 s. Best-energy pose (-10.78 kcal/mol) heavy-atom assignment
RMSD 1.004 A vs the crystal; 4 of 10 poses <= 2.0 A. Verdict by the locked rule: PIPELINE OK. Reading: the engine and search pipeline
recover a known pose, consistent with the corrected 12A analysis and against a pipeline-wide failure. Files: studies/nativecov12d/d6/,
results/native_covalent_12d_d6.json. D5 (crystal-in-grid) not run.
