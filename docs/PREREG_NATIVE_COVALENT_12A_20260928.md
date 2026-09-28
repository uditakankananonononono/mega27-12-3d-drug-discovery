# NEW dated preregistration: 12A native covalent engine (lane 12, item 6 final pivot) - 2026-09-28, ~09:35 IST

Status: PRE-OUTCOME. Committed before any 12A engine acquisition, preparation,
gate, or docking run. Authorization: parent adjudication 2026-09-28 09:23 IST
("only then start 12A under a NEW dated prereg"), after the constraint-guided
question was declared machinery-exhausted (12B close-out commit ca0b751, four
documented machinery limitations). Pivot order record (2026-09-28 07:22 IST):
12B, then 12A (native covalent engine) only if 12B fails; 12C rejected. The
failed reactive-marker claim (item 6) is never re-tuned; 12B's constraint is
not re-run. This is a different mechanism question with a different engine.

## Question (locked)

Can a NATIVE covalent docking engine - one that explicitly models the reactive
near-attack geometry between the ligand warhead and the Cys145 SG (the
reactive-docking method implemented only in AutoDock-GPU, per the meeko
documentation) - recover the crystallographic binding mode of the two known
covalent complexes, where the reactive-marker workaround (item 6) failed and
the constraint-guided route (12B) could not be executed under locked,
verifiable conditions?

## Complexes, inputs, attachment geometry (carried over unchanged)

Same two complexes, committed inputs and SHA-256s as the item-6 and 12B
preregs: 7VH8 (Mpro + nirmatrelvir, adduct 4WI) and 7C6S (Mpro + boceprevir,
adduct U5G); committed files studies/covalent/{7vh8,7c6s}.pdb,
{nirmatrelvir,boceprevir,4WI,U5G}.sdf with the SHA-256s locked in prereg
3d48644. Attachment geometry carried over: 7VH8 Cys145 SG altloc A =
(-15.937, 18.658, -30.181), warhead = nirmatrelvir SDF atom index 30 (nitrile
carbon); 7C6S Cys145 SG = (-18.709, -22.655, 4.666), warhead = boceprevir SDF
atom index 27 (keto carbonyl carbon). Same 24 A boxes: npts 64, spacing
0.375 A, gridcenters (-19.054, 15.539, -31.610) and (-19.915, -21.076, 0.485).

## Engine and acquisition (locked, with pre-decided fallback order)

1. AutoDock-GPU v1.6 prebuilt linux_x64 OpenCL binary
   (adgpu-v1.6_linux_x64_ocl_128wi) from ccsb-scripps/AutoDock-GPU GitHub
   releases; URL and SHA-256 recorded in the runlog at acquisition; disclosed
   as a prebuilt binary. Runtime: CPU OpenCL via POCL (Ubuntu jammy
   libpocl2/pocl-opencl-icd 1.8-3, unprivileged .deb extraction).
2. If the prebuilt binary fails mechanically: build v1.6 from source
   (Makefile.OpenCL) against ocl-icd headers.
3. If v1.6 is unusable: v1.5.3 (the original covalent-capable release line).
4. If all fail mechanically: STOP; machinery-exhaustion report to parent. No
   further substitution is chosen locally.
Maps: autogrid4 4.2.8 already in the lane (bin/ad4/autogrid4, SHA-256
554cd9935584db3b4e9be022aef04cea3de21975ab70a36f3b3a5cdf20aacfc3), same
locked boxes. Preparation: meeko 0.8.0 - ligand reactive preparation marking
exactly the locked warhead atom; receptor preparation from the committed PDBs
(chain A, default altloc A, the item-6 policy) with reactive residue
A:145=SG and a flexible Cys145 sidechain, the method's standard preparation.

## Arms (locked)

- C2 NATIVE COVALENT (the test arm): reactive docking as above.
- C1 engine control (descriptive): the same ligands with standard
  non-reactive meeko preparation on the same engine, boxes and seeds.
  Isolates what the reactive machinery adds; no claim is gated on it.

## Search parameters (locked, mapped from item 6)

nrun 10 LGA runs per seed (item-6 ga_run 10), nev 1000000 (ga_num_evals),
ngen 27000, popsize 150, Solis-Wets local search lsit 300; all other ADGPU
v1.6 settings at defaults, recorded in the runlog. Seeds 77000+s for
s = 0,1,2 (three seeds per complex per arm). Wall-clock cap 3600 s per run
(CPU OpenCL speed unknown; item-6 AD4 runs took 3-11 min). A run exceeding
the cap is a machinery TIMEOUT, recorded and reported to parent: it is not a
docking failure and contributes no outcome. If fewer than 2 of 3 seeds
complete for a complex, that complex is MACHINERY-INCOMPLETE and reported to
parent for adjudication; the decision rule is never evaluated on partial
seeds.

## Integrity gates (locked; all before any C2 outcome is read)

- G1 preparation integrity: exactly one reactive atom per ligand, mapping to
  the locked warhead (nirmatrelvir idx 30 / boceprevir idx 27, verified with
  the item-6 element-MCS mapping machinery); receptor reactive atom exactly
  A:145 SG; flexible-residue list exactly Cys145. Asserted programmatically.
- G2 reactive-channel parameter audit: the meeko-written reactive config
  contains the scaled pairwise parameters for the two reactive atom types,
  matching meeko's ReactiveAtomTyper scaled-parameter computation to 1e-6
  (the 12B lesson: verify the bias channel numerically, pre-outcome).
- G3 engine smoke: the engine runs a minimal reactive input (nrun 1,
  nev 10000, one anchored near-attack input pose written pre-outcome) to
  completion (rc=0), echoing the reactive types; verifies binary, OpenCL
  runtime, maps and config reach the engine together.
- G4 RMSD machinery: the matcher maps each crystallographic adduct onto
  itself (RMSD 0.0) before any docked pose is analyzed.

## RMSD criterion and decision rule (locked, carried over unchanged)

Pose semantics (locked): reactive docking places the UNREACTED ligand in
near-attack geometry; the heavy-atom skeleton does not rearrange on bond
formation, so RMSD is computed against the crystallographic ADDUCT ligand
heavy atoms exactly as in item 6/12B, and 2.0 A remains the standard redock
threshold. Best-energy pose per seed (lowest estimated free energy across
that seed's nrun models), heavy atoms, symmetry-corrected minimum over MCS
automorphisms (item-6 v2 convention), no superposition (receptor frame
retained). Per complex: PASS iff best-energy-pose RMSD <= 2.0 A in >= 2 of
3 completed seeds. Both complexes PASS: 12A SUPPORTED. One PASS: mixed,
reported as measured; no gate inflation. Zero PASS: 12A NOT SUPPORTED, plain
negative; all adjudicated pivots are then exhausted and any further work
requires parent adjudication.

## Conduct

No threshold, parameter, seed, or criterion moves after any C2 outcome is
read. Post-hoc observations are labeled descriptive and cannot restore a
failed gate. Negatives are reported as measured. Deliverables: runlog section
in docs/COVALENT_RUNLOG_20260928.md, results/native_covalent_12a.json,
scripts under studies/nativecov12a/ (committed pre-outcome), queue item-6
addendum, paper subsection (reported as measured either way, prebuilt-binary
acquisition disclosed).

## Addendum 1 (pre-outcome machinery refinements, 2026-09-28 ~09:45 IST, committed BEFORE any gate result or arm execution)

Recorded pre-outcome, none touching any locked scientific element:
1. Ligand reactive preparation path: the meeko CLI/API writer paths proved
   unreliable for the committed SDFs in this environment (the CLI emitted
   duplicate outputs with divergent typing for boceprevir; the API writer
   produced non-finite charges with sanitize=False loading). The reactive
   ligand is instead built by retyping the committed item-6 preparation
   (coordinates and charges unchanged, verified line-by-line in G1) with
   meeko's canonical reactive typing scheme (order 1 = reactive atom,
   order 2 = one bond away, order 3 = two bonds away;
   meeko.reactive.assign_reactive_types_by_index semantics, read from source),
   applied by bond-order shells from the locked warhead index. The locked
   SMARTS remain on record above.
2. G2 formulation pinned to meeko's actual config semantics: the reactive
   config's pair lines are written by meeko's covalent builder with r_eq/eps
   scaling, not raw ReactiveAtomTyper.get_scaled_parm output. G2 is therefore
   implemented as: (a) the covalent pair line for the two locked order-1
   types (ligand warhead order-1 type, receptor 1S4) exists with the 13/7
   exponents and r_eq/eps equal to the preparation defaults (1.8 A, 2.5
   kcal/mol) within 1e-6; and (b) the receptor preparation is deterministic
   (a second independent preparation yields a byte-identical reactive
   config). This verifies the same locked property - the covalent channel
   numerically present and correct - with the engine's actual file format.
3. Receptor prep uses --delete_bad_res_from_box_radius 5.0: unmatched
   residues more than 5 A outside any box face are deleted (7VH8 TYR A:154
   is an incomplete sidechain ~33 A from the locked box; nothing near the
   box is affected, and any unmatched residue near the box raises an error
   instead).
4. --import_dpf carries "only partial support" per the engine's --help; the
   reactive_config is nonetheless the meeko-documented reactive-docking
   input for this engine. G3 (engine smoke) verifies the config is accepted
   and the reactive types reach a completed run.
