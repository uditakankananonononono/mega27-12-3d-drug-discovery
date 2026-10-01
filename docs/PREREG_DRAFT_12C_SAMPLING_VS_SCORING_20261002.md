# DRAFT preregistration 12C (dated 2026-10-02, written BEFORE any 12C quantity is computed) - NOT YET ADJUDICATED

Status: draft for parent adjudication. Nothing below has been computed. The 12A verdict
(NOT SUPPORTED, 0/4 arms) is final and is not revisited; this is a new question.

## Why (what informed the pivot)
- 12A: best-energy-pose RMSD 5.52-6.56 A in all 12 runs, C1 and C2 alike, while C2 energies
  were lower. Ranking by energy did not pick the crystal pose. Unknown: whether the crystal
  pose was ever SAMPLED (sampling failure) or sampled but not ranked first (scoring failure).
- Literature (current covalent-docking reviews and tools, e.g. PMC12753312 landscape review;
  CarsiDock-Cov, ScienceDirect S221138352500526X): pose-reproduction failures in covalent
  docking are usually split into sampling vs scoring, and rescoring of sampled poses is a
  standard remedy. Not used as a gate source; only to frame the question.
- Uses only existing material: the 12 committed DLG/XML files (10 runs x 3 seeds per arm per
  complex = 30 poses per arm per complex). No new docking, no new compute beyond analysis.
- Not yet done: ChatGPT steering (to be run per parent's standing instruction); this draft
  should be revised pre-outcome if it changes the design.

## Questions and locked rules (set before computing)
Q1 sampling: for each complex/arm, minimum symmetry-corrected RMSD (same function as 12A)
over all 30 sampled poses (every model in every run). Sampling ADEQUATE for an arm if min
RMSD <= 2.0 A. Reported per arm.
Q2 scoring: among arms with adequate sampling, rank of the lowest-RMSD pose within the 30 by
docking energy. Scoring FAILURE if that pose is not in the energy top 3.
Q3 rescoring (only if Q1 adequate in >= 1 complex): rescoring the 30 poses with the lane's
existing, already-trained rescorer (no retraining, no new features) and testing whether the
top-1 pose RMSD <= 2.0 A. SUPPORTED only if top-1 RMSD <= 2.0 A in both seeds-pooled arms of
at least one complex; otherwise NOT SUPPORTED.
Verdict labels: Q1 is descriptive (no pass/fail claim about the 12A criterion). Q3 is the only
claim. Thresholds above are locked; none moves after outcomes. Exhaustive per-arm numbers are
reported whatever they are, including if Q1 shows sampling never reaches 2.0 A.

## Caveats pre-declared
- Reference-pose RMSD function and symmetry correction identical to 12A (analysis code in
  studies/nativecov12a/run_12a.py). Pooling 3 seeds x 10 runs is a new analysis unit, not the
  12A criterion; it cannot restore the 12A verdict.
- If the rescorer lacks a defined input for covalent poses, Q3 is declared MACHINERY-INCOMPLETE
  rather than adapted.
