# Pre-registration: hydration-aware scoring / explicit waters (lane 12, item 5)

Date: 2026-09-28 (committed before any hydration outcome is computed).
Lane 12 verdict item: "Hydration-aware scoring / explicit waters - NOT DONE."

## Scope and honest framing
Same scope as docs/PREREGISTER.md: retrospective methodological audit of the
existing open docking workflow on public Mpro reference structures. No
compound nomination, no new bioactive claim. All numeric cutoffs below are
locked now, before outcomes.

## Inputs (all already committed or public)
- Structures in data/raw: 6LU7, 6YB7, 7BB2, 7BQY, 7KX5, 7RFS, 8HUR, 8V8E.
- Docking box: data/raw/box_7kx5.json (unchanged).
- Committed ablation poses: results/ablation_poses/*.pdbqt (52/59 records;
  the 7 pose failures stay excluded from pose arms exactly as in
  studies/study12_ablation.py - no redocking for this item).
- Labels/splits/statistics: studies/study12_scaffold_split.py and
  studies/study12_ablation.py, unchanged.

## Part A - conserved hydration-site map (descriptive, no gate)
1. Binding-site residues: 7KX5 chain A residues with any atom within 8 A of
   the X7V ligand (heavy atoms).
2. Superposition: Kabsch on CA atoms of those residues, matched by residue
   number between 7KX5 chain A and each other structure's chain A; a
   structure is skipped and named if fewer than 20 residue-number-matched
   CA pairs exist.
3. Waters: HETATM HOH oxygens with chain ID A or blank; transformed into the
   7KX5 frame; kept if inside the docking box.
4. Clustering: greedy seed-based clustering at 1.5 A (seed = remaining point
   from the structure with most remaining points; cluster = all points
   within 1.5 A of the seed; single pass, no chaining). Conservation count
   = number of distinct structures contributing to a cluster.
5. Output: results/hydration_sites.json with all clusters and counts.
   Descriptive audit only.

## Part B - explicit-water redock (descriptive, no gate)
Redock X7V into 7KX5 with its 8 crystal waters retained as rigid receptor
atoms (meeko receptor prep on protein+HOH; same box, seed 42,
exhaustiveness 16, n_poses 9 as study12_redock.py). Report best affinity
and heavy-atom assignment RMSD against the committed apo redock in
results/redock_7KX5.json. n=1; no statistical claim, no gate.

## Part C - hydration-feature benchmark arm (gated)
Features per committed pose, from the Part A map only (protein structures;
no label information enters feature construction):
- h_occ: count of conserved sites (conservation >= 3 structures, locked)
  with any ligand heavy atom within 2.5 A (site occluded by the pose).
- h_br: count of conserved sites (conservation >= 3) whose nearest ligand
  N/O atom is 2.5-3.5 A away and which are not occluded (bridging
  geometry).
Arm J ("mlp9"): the leakage-controlled arm C feature set (7 RDKit
descriptors, no Vina-derived feature) plus h_occ and h_br, trained with the
identical MLP trainer, scaffold splits (seeds 0-4), and statistics of
studies/study12_ablation.py. Comparison arm: mlp7 rerun identically.

### Locked gate G-hyd
Hydration features are supported ONLY IF BOTH hold:
1. mean AUROC(mlp9) over the 5 scaffold splits > mean AUROC(mlp7) computed
   on the same pose-available held-out compounds of each split; AND
2. seed-0 paired DeLong p < 0.05 (same delong_p implementation, same
   seed-0 held-out pose subset as the committed ablation).
If either clause fails, the hydration-feature contribution is reported as
NOT SUPPORTED. Thresholds do not move after outcomes; no alternative
feature definitions, radii, or conservation cutoffs are tried after seeing
results. A supported gate still claims only a methodological feature
contribution on this 59-compound Mpro benchmark - nothing else.

### Declared limits (locked)
- The seed-0 held-out pose subset is small (committed ablation: 9
  positives, 5 negatives), so the DeLong test has low power; the mean-AUROC
  clause alone is descriptive.
- Sites derive from 8 public structures of one target; no generalization
  beyond this system is claimed.
- Pose availability bias is unchanged from the committed ablation and is
  reported there.

## Out of scope
No new docking campaign, no water-placement prediction software, no
free-energy perturbation, no compound-level claims, no generalization to
other targets.
