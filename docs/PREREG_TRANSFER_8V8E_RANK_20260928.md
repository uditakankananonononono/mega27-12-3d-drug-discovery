# Preregistration: cross-structure rank transfer, 7KX5 -> 8V8E (2026-09-28)

Queue item 4 (docs/QUEUE_20260927.md): "Cross-target transfer - PARTIAL ...
broader cross-protease transfer untested." Written before any campaign
compound was docked into 8V8E. Thresholds below are locked and will not move
after outcomes.

## Question
Does the campaign's affinity ranking survive a change of target structure?
The ensitrelvir redock pilot (results/redock_8V8E_transfer.json, RMSD 1.43 A,
gate PASS) validated the protocol on 8V8E (SARS-CoV-1 Mpro, room-temperature,
complete binding site) but tested one ligand only.

## Design
- Compound set: exactly the 52 committed campaign records in
  results/bigscreen/*.json (fixed; their 7KX5 affinities and ChEMBL labels
  are already committed). No re-selection after seeing 8V8E outcomes.
- Receptor: data/raw/8V8E_A_receptor.pdbqt (prepared in the pilot;
  VAL86/VAL125/CYS128/MET130 removed, none are contact residues).
- Box: data/raw/box_8v8e.json (center = ensitrelvir crystal centroid, 20 A).
- Docking: drugdisc.dock.dock_ligand_with_timeout, timeout 300 s, same
  worker/settings as the 7KX5 campaign (studies/study12_bigscreen.py).
  Resumable per-compound caches in results/transfer8v8e/<CHEMBL_ID>.json.
- Failures (timeout, unsupported element, worker error) are excluded from
  rank statistics and counted, never imputed.

## Locked gates
- PRIMARY: Spearman rho between 7KX5 and 8V8E best affinities over compounds
  docked in both structures. Rank transfer declared if rho >= 0.50;
  below 0.50 the campaign ranking is declared structure-specific. Exactly one
  threshold, fixed here.
- DESCRIPTIVE ONLY (no gate): top-10 retention (how many of the 7KX5
  affinity top-10 remain in the 8V8E top-10); raw-Vina AUROC of 8V8E
  affinities against the committed ChEMBL labels; failure/timeout counts;
  per-compound affinity deltas.
- This study does not reopen any withdrawn claim (the pose-geometry verdict
  stands) and makes no clinical or per-compound activity claim; it measures
  ranking robustness to the receptor structure.
