# Preregistration: bounded covalent docking branch (lane 12, queue item 6)

Dated 2026-09-28 IST. Committed before any covalent outcome-producing run.
Parent approval for the bounded-prereg plan received 2026-09-28 04:51 IST.

## Feasibility bound, recorded pre-outcome

- The lane pipeline runs AutoDock Vina 1.2.7 through its Python API. The Vina
  class exposes no reactive or covalent docking methods (verified by
  introspection on 2026-09-28).
- meeko 0.8.0 is installed; it can prepare reactive receptor and ligand inputs
  for AutoDock4-family engines but is not itself an engine.
- No autodock4, autogrid4, or AutoDock-GPU binaries are installed; no
  conda/mamba; no autodock-gpu distribution exists on PyPI (checked
  2026-09-28).
- Prebuilt AutoDock-GPU v1.6 linux_x64 binaries are published on the project's
  GitHub releases page (OpenCL and CUDA variants). Whether one runs on this
  machine (OpenCL runtime availability, map generation without a local
  autogrid4) is unknown at preregistration time.

## Locked scope

This branch is a bounded feasibility plus self-redock audit, NOT an
activity-prediction benchmark. Rationale: the lane's labeled set has no
curated covalent-mechanism labels, so no AUROC-style gate can be defined
honestly. No threshold in this document moves after outcomes.

## Plan

- Part A (engine acquisition). Attempt to obtain a runnable reactive-capable
  engine within a 60-minute total compute budget, in this order:
  (1) AutoDock-GPU v1.6 prebuilt linux_x64 binary plus a map-generation path
      (autogrid4 binary from an official project source, or a meeko-driven
      path);
  (2) AutoDock4/autogrid4 static binaries from official project sources.
  Binary provenance (URL + SHA-256) is logged in the run record. If neither
  option runs its own basic reactive-docking input, STOP: item 6 maps BOUNDED
  with this document as the record, and no further covalent work is done.
- Part B (only if Part A succeeds). Self-redock audit on two crystallographic
  covalent complexes, identities verified against RCSB at preregistration:
  7VH8 (SARS-CoV-2 Mpro + PF-07321332/nirmatrelvir, 1.59 A, nitrile warhead
  forming a thioimidate at Cys145) and 7C6S (SARS-CoV-2 Mpro + boceprevir,
  1.6 A, ketoamide warhead forming a hemithioketal at Cys145). Protocol: the
  engine's standard reactive-docking preparation with a flexible Cys145
  sidechain; three fixed seeds (0, 1, 2) per complex.
- Locked success criterion (descriptive): best-pose heavy-atom RMSD <= 2.0 A
  against the crystallographic ligand in at least 2 of 3 seeds counts as
  "self-redock succeeds" for that complex. This is the standard redock
  criterion, fixed here pre-outcome.
- Negative control (descriptive, no gate): the same ligand run through the
  lane's existing non-covalent Vina pipeline; report warhead displacement
  relative to the adduct geometry. No claim is gated on it.
- Honest limits, locked now: self-redock only; no cross-structure covalent
  docking; no activity ranking; no comparison to clinical performance of any
  drug; a Part B failure (RMSD above 2.0 A) is reported as a plain negative.

## Deliverables

- If Part A fails: queue item 6 maps BOUNDED, citing this document and the
  acquisition log; the paper's limitations record why no covalent branch
  exists.
- If Part B runs: results/covalent_redock.json, the queue item 6 verdict
  line with exact numbers, and a paper subsection reporting the audit either
  way (success or plain negative).
