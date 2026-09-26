# MEGA27-12 Revival Preregistration (locked 2026-09-26, before any new outcome)

Locked under standing rules verified in WhatsApp channel history 4:11:18 / 4:11:49 / 4:12:25 / 4:14:37.

## Scope and honest framing
This lane is retrospective validation and enrichment benchmarking of an open,
reproducible docking workflow on well-studied public reference systems, plus
methodological discovery. It does not design, optimize, or nominate novel
bioactive compounds; any compound-level observation must be verifiable in
prior published literature.

## Locked gates (declared before outcomes)
- G1 protocol validation: redock a reference co-crystallized ligand into its
  own public PDB structure; PASS if heavy-atom RMSD < 2.0 A, reported with
  the exact software version and seed.
- G2 retrospective enrichment: on a standard public actives/decoys benchmark
  set (DUD-E or LIT-PCBA), PASS if logAUC or EF1% of the pipeline exceeds
  the published reference numbers for the same engine on the same target
  subset (named numbers cited with URLs).
- G3 benchmark beat: a documented rescoring stage (pose features + simple
  learned ranker) must beat raw docking-score ranking on the identical
  locked split, paired bootstrap CI on the enrichment metric excluding zero.
- G4 discovery (methodological): a pre-declared, falsifiable claim about the
  pipeline (e.g., which pose-feature family drives enrichment gains, or a
  quantified failure-mode map) that survives a locked control (e.g.,
  shuffled-feature ablation). Compound-level claims only if already
  published; cite the source.
- Judge: >= 10 ChatGPT weakness/improvement rounds, verbatim logs in
  docs/JUDGE_ROUNDS.md; negatives pivot per rule 6 (ChatGPT redirection
  options ranked, strongest chosen, logged the same way).
- ISEF archetype (rule 7): maps to computational-method + validation winners;
  judge rounds ask what a judge who knows those projects would say is missing.

## Pivot ladder (if a gate fails)
P1 different public target subset within the same benchmark family;
P2 different rescoring feature set; P3 discovery reframed to the validated
failure-mode map; P4 full negative write-up only after P1-P3 exhausted,
and even then the lane stays open per rule 4.
