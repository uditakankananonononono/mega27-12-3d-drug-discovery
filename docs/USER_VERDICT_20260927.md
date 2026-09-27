# User verdict archive, 2026-09-27 (lane 12 = "MEGA27-12: 3D Drug Discovery - Mpro")

Provenance: inbound WhatsApp wamid.HBgMOTE4MTM0MDk4NTcxFQIAEhgWM0VCMEFGRDY4MzY4OTkxNzFEQURGRAA=,
received 2026-09-27 12:02:56 IST, author = user (+918134098571). Full-message body SHA256:
0795f5ff4a86b44e7edd301caa8c9c4ce17abbda034f0a0b29ae7b40ff76a6a6.
Header directive (verbatim, first line of the original message): "IGNORE ABOUT ISEF DELIVERABLES,
IMPROVE PAGE COUNT". Effect: page-length weaknesses fleet-wide are superseded; grow pages with
substantive content; 12-slide storyboard deliverables dropped.

## Verbatim section for this lane
10. MEGA27-12: 3D Drug Discovery — Mpro
Weaknesses (20) — computational only:

Raw Vina AUROC 0.339 — below chance on 15 compounds.

GNN n=15 result was single-seed luck (0.946 → 0.871 ± 0.050).

Bigscreen n=59 shows MLP ≈ GNN (0.83 both).

n=15 leave-one-out CIs are wide.

Only 15 labeled compounds in the primary benchmark.

Covalent warheads scored as reversible — chemistry blind.

Ebselen excluded (no Se parameters).

Ivermectin SMILES unresolved.

Rigid receptor — induced fit unmodeled.

Water-mediated interactions absent.

Cross-target transfer untested.

Exhaustiveness 8 can miss deep minima.

Label set includes failed clinical drugs (assay heterogeneity).

Comparator encodings may be direction-confused.

"Benchmark break" framing is small-n.

Bigscreen excludes 17 macrocycles — scope narrow.

MPRO-D1 does not beat nilotinib on affinity.

Tool count 40 — meets gate but inflated.

GNN at n=15 was pose-graph; at n=59 was 2D bond-graph — architectures not merged.

No cross-validation of MPRO-D1's docking pose class.

Additions (computational):

Grow labeled set to ≥50 compounds.

Add explicit water molecules or hydration-aware scoring.

Add covalent docking branch.

Add cross-target transfer (e.g., another protease).

Report DeLong CIs for all AUROC comparisons.

Merge n=15 and n=59 architectures into one benchmark.

Simplify to benchmark + one honest negative + one candidate.

Reduce to 12 slides.


## Verbatim cross-cutting themes

Cross-Cutting Computational Themes
Recurring weaknesses:

Dataset/tool count inflation (nested records counted as independent).

Long papers (47-58 pages) — not ISEF-ready.

Negative-heavy narratives that obscure positive contributions.

Single-seed headline numbers.

Ad hoc gates/thresholds rather than theoretically derived.

Homology leakage in random-split benchmarks.

No leave-family-out CV in most projects.

CIs often overlapping — point-estimate wins only.

Universal computational additions:

One primary question per paper.

One locked primary endpoint.

Cluster-level bootstrap CIs everywhere.

Leave-family-out CV as the primary protocol.

12-slide storyboard as the ISEF deliverable.

One-page summary card.
