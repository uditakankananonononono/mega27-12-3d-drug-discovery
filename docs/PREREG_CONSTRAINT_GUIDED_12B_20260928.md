# NEW dated preregistration: 12B constraint-guided placement (lane 12, item 6 pivot) - 2026-09-28, ~08:00 IST

Standing: lane 12 item 6 (covalent branch) closed as a plain negative at the
locked criterion for both parameterizations (outcome commits in git log:
7VH8 14.79/21.94/22.20 A, 7C6S 10.83/6.93/9.38 A, 0/3 seeds each). Pivot
order adjudicated by the parent 2026-09-28 07:22 IST: 12B constraint-guided
placement; 12A (native covalent engine) only if 12B fails; 12C rejected.
This prereg locks 12B before any execution. The failed reactive-marker
claim is never re-tuned; this is a different mechanism question.

## Question (locked)

Using the standard engine of this lane (AutoDock Vina 1.2.7 python package,
non-reactive), can a pharmacophore constraint built from the known
crystallographic covalent attachment geometry place the warhead so that
docked poses recover the crystallographic binding mode, where the
reactive-marker workaround could not?

## Complexes and inputs (locked, committed)

Same two complexes as item 6, identities RCSB-verified at item-6
preregistration:
- 7VH8: SARS-CoV-2 Mpro + nirmatrelvir (adduct component 4WI), 1.59 A.
- 7C6S: SARS-CoV-2 Mpro + boceprevir (adduct component U5G), 1.6 A.

Committed inputs (SHA-256):
- studies/covalent/7vh8.pdb   b8043882bac69b5cd8f3bb74123eabc0883b95b91020d29093b4f4b2d1bbf362
- studies/covalent/7c6s.pdb   ead0908d5415efd5d011e0af0225b9870595a906ef532ffce498d03f39033e29
- studies/covalent/nirmatrelvir.sdf (PubChem CID 155903259) 6e8ec0e3b71fd551a3a2d35f6c4b07535c65e592b60616b548cb25dd2961c3ac
- studies/covalent/boceprevir.sdf   (PubChem CID 10324367)  8b09b1b17e435b19fb30657bb5fca75e4f5805190b27e14994c4de17fb9e7e18
- studies/covalent/4WI.sdf 10e5799ab1a75309cf705b8435130455b65b0a26e70ca8181723accca18d13b7
- studies/covalent/U5G.sdf 2e774aae0bf0f902c20fb3f707332a1ca9f79738559fa1adddf86b12dc0f0110
- Receptor PDBQTs: committed studies/covalent/7vh8_rec_rigid.pdbqt,
  7c6s_rec_rigid.pdbqt (chain A, altloc A, item-6 preparation, unchanged).

## Crystallographic attachment geometry (recorded pre-outcome)

- 7VH8: Cys145 SG altloc A = (-15.937, 18.658, -30.181); nearest 4WI atom
  C3 at distance 1.814 A (the thioimidate carbon). SG altloc B is 4.25 A
  away and is not the adduct rotamer (item-6 LINK-record reading).
- 7C6S: Cys145 SG = (-18.709, -22.655, 4.666); nearest U5G atom C03 at
  distance 1.766 A (the hemithioketal carbon).
- Free-ligand warhead atoms (element-MCS mapping, full-molecule match
  35/35 and 37/37 atoms): nirmatrelvir SDF atom index 30 (nitrile carbon,
  triple bond to N); boceprevir SDF atom index 27 (keto carbonyl carbon,
  double bond to O). Atom indices are 0-based RDKit order of the committed
  SDFs.

## Constraint implementation (locked)

Standard-engine, non-reactive, grid-level pharmacophore:
1. Ligand preparation: meeko default (Vina) typing from the committed free
   SDFs. The single warhead atom is retyped to Cl. Declared approximation:
   Cl VdW (R 2.045 A, eps 0.276) approximates sp/sp2 carbon (R 2.000 A,
   eps 0.150); carbon carries no H-bond character to lose; no other Cl
   exists in either ligand (verified programmatically at prep time and
   recorded in the runlog), so the constraint map touches only the warhead
   atom. All other atoms keep their true types.
2. Maps: autogrid4 (bin/ad4/autogrid4, SHA-256
   554cd9935584db3b4e9be022aef04cea3de21975ab70a36f3b3a5cdf20aacfc3),
   same 24 A box as item 6 (npts 64, spacing 0.375 A; gridcenter
   -19.054 15.539 -31.610 for 7VH8, -19.915 -21.076 0.485 for 7C6S),
   maps for all ligand atom types including Cl.
3. The Cl map is modified numerically by adding, at every grid point p,
   E_add(p) = -3.0 * exp(-(d/0.75)^2) kcal/mol, d = distance from p to the
   crystallographic SG target above. Depth 3.0 kcal/mol and width 0.75 A
   are locked now; they are not tuned after any outcome. All other maps
   are byte-identical to the autogrid4 output.
4. Docking: vina 1.2.7, sf_name vina, maps loaded from the AD4 map set
   (load_maps), exhaustiveness 32, n_poses 20, cpu 2, seeds 77000+s for
   s = 0,1,2 (three seeds per complex), 300 s wall-clock cap per run
   (existing wrapper convention).

## Arms (locked)

- A2 CONSTRAINED (the test arm): warhead Cl-typed ligand + biased Cl map.
- A1 typing control (descriptive): warhead Cl-typed ligand + unmodified
  maps (depth 0). Isolates the typing approximation.
- A0 baseline (descriptive): true-type ligand + standard compute_vina_maps.
  Measures what the constraint adds over unconstrained standard docking.

## Integrity gates (locked; all before any A2 outcome is read)

- G1 map-pipeline equivalence: score-only of one fixed input pose via
  compute_vina_maps vs load_maps (unmodified maps) agrees within
  0.05 kcal/mol per complex.
- G2 modified-map audit: only the Cl map differs from autogrid4 output;
  verified byte-wise for every other map file.
- G3 RMSD machinery validation: the adapted matcher maps the crystal
  adduct onto itself (RMSD 0.0) for both complexes before any docked pose
  is analyzed.

## Decision rule (locked)

RMSD: best-energy pose, heavy atoms, symmetry-corrected minimum over MCS
automorphisms (item-6 v2 convention, adapted to Vina PDBQT poses; docked
atom order = input PDBQT order, input order = SDF order), no superposition
(receptor frame retained). Per complex: PASS iff best-energy-pose RMSD
<= 2.0 A vs the crystallographic ligand in >= 2 of 3 seeds.
- Both complexes PASS: 12B SUPPORTED - constraint-guided placement recovers
  the crystallographic binding mode where the reactive-marker workaround
  failed.
- One complex PASS: mixed, reported as measured; no gate inflation.
- Zero PASS: 12B NOT SUPPORTED, plain negative; 12A (native covalent
  engine) remains the only adjudicated pivot.

## Conduct

No threshold, parameter, seed, or criterion moves after any A2 outcome is
read. Post-hoc observations are labeled descriptive and cannot restore a
failed gate. Deliverables: runlog docs/CONSTRAINT_GUIDED_RUNLOG_20260928.md,
results/constraint_guided_12b.json, scripts under studies/constraint12b/
(script committed pre-outcome), queue item-6 addendum, paper paragraph
(reported as measured either way).
