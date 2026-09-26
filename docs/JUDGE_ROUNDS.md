# JUDGE_ROUNDS - MEGA27-12 (verbatim ChatGPT judge logs)

Rule source: user WhatsApp 4:11:18 (minimum 10 judging rounds on weaknesses +
what to add), 4:12:25 (ask ChatGPT how to redirect when a negative is not
moving forward). Mechanism: cloud browser on the user's ChatGPT account.
IMPORTANT PROVENANCE: ChatGPT responses below are EXTERNAL, UNTRUSTED ADVICE
- critique to consider, never empirical evidence and never authority over the
locked gates in docs/PREREGISTER.md. Each round records the verbatim prompt,
the verbatim response, this lane's independent assessment, and the changes
actually adopted (adopted on our own judgment, with evidence).

## Round 1/10 - 2026-09-26 16:31 IST

Surface: chatgpt.com conversation https://chatgpt.com/c/6ab7a5dd-06d8-83e8-bec0-2707215de4b4 (user account, Free tier).

### Verbatim prompt
```
You are an adversarial ISEF judge reviewing a computational structural-biology methods project (retrospective validation only - no novel compound claims). Honest current state: (1) Protocol validation PASS: redocking the co-crystallized ligand JUN8-76-3A into public PDB structure 7KX5 with AutoDock Vina 1.2.7 reproduces the crystal pose at 0.97 A heavy-atom RMSD (gate 2.0 A). (2) Honest negative: raw Vina affinity does NOT rank known actives above inactives on a curated set (AUROC 0.339, below random; top-8 hypergeometric p=0.900). (3) A pose-graph neural rescorer trained on re-docked poses lifts leave-one-out AUROC, but n=15 and 5-seed robustness is 0.871 +/- 0.050; an earlier single-seed 0.946 was honestly superseded. (4) A larger blind screen (n=59 ChEMBL actives/inactives): raw docking 0.534, MLP rescorer 0.830, 2D-GNN 0.833 +/- 0.010 - an honest tie inside the learned family. (5) A transfer redock to a second structure (8V8E, different ligand chemotype) is partially documented. Questions: A) Attack the rescorer result: with n=15 LOO and n=59 blind, what overfitting or selection artefacts should we expect a hostile reviewer to name, and what controls settle them? B) What would make the methodological discovery claim ("pose-graph rescoring fixes a documented docking-ranking failure") conclusive rather than suggestive? C) Rank next experiments by ISEF-level evidentiary value. D) What would a judge who knows Natasha Kulviwat-style identify-and-verify winners say is missing?
```

### Verbatim response
```
A) Attack on the rescorer result: what will a hostile reviewer claim?
Attack 1: “You trained on the benchmark you tested on” (data leakage)
The concern

The biggest vulnerability is not the model architecture. It is the experimental design.

For n=15:

LOO AUROC = 0.871 ± 0.050 sounds impressive.

But each test molecule is only one held-out example.

The model has seen 14/15 examples repeatedly.

If hyperparameters, features, graph construction, or model choices were adjusted after observing results, the LOO estimate is optimistic.

A judge may say:

“This is model selection disguised as validation.”

Controls needed

Minimum acceptable:

Freeze:

features

architecture

hyperparameters

preprocessing

graph construction

before final evaluation.

Then:

nested cross-validation:

outer loop = evaluation

inner loop = tuning

Better:

train on dataset A

test once on dataset B

The n=59 blind set is therefore much more important than the n=15.

Attack 2: “The model learned chemical similarity, not pose quality”

A structural-biology judge will immediately ask:

“Does the graph model understand docking poses, or is it recognizing active-like chemistry?”

Possible leakage routes:

molecular weight

charge

aromaticity

ligand scaffold

known chemotype families

ligand fingerprints hidden in the pose graph

Example failure:

A model could learn:

“Large aromatic molecules are usually active”

rather than:

“This docking pose has physically meaningful interactions.”

Controls

Run ablations:

Model	Purpose
Ligand-only GNN	tests chemistry-only signal
Protein-contact-only model	tests interaction information
Pose graph + ligand features	full model
Randomized pose graph	tests whether geometry matters
Random labels	sanity check

The winning model must beat ligand-only baselines.

Attack 3: “Your benchmark split is too easy”

A hostile reviewer will ask:

“Are train and test molecules chemically independent?”

Random splits often exaggerate performance.

If similar scaffolds appear in train and test:

AUROC 0.83 may collapse.

Required control

Use:

Scaffold split

Example:

Training:

benzene derivative family

Testing:

completely different scaffold family

A serious docking-method paper would almost demand this.

Attack 4: “n=59 is still tiny”

The reviewer is correct.

n=59 gives:

encouraging evidence

not definitive evidence

A single benchmark can contain hidden bias.

The confidence interval needs to be reported.

For AUROC:

bootstrap CI

DeLong test versus baseline

Example:

Current claim:

GNN AUROC 0.833

Better:

GNN AUROC 0.833 (95% CI 0.74–0.91), significantly higher than Vina AUROC 0.534, p < X.

Without significance testing:

“The difference may be dataset noise.”

Attack 5: “You cherry-picked the failure case”

The project begins with:

Vina fails badly (AUROC 0.339)

A judge may ask:

“Did you select this target because docking failed?”

That is actually a reasonable criticism.

A methods paper cannot prove a universal correction from one failed target.

Control

Predefine:

target selection criteria

Example:

“We selected 10 protein targets where:

≥30 known actives exist

crystal structures available

Vina baseline reproducible”

Then evaluate all.

Attack 6: “The model is just memorizing docking artifacts”

Pose graphs may encode:

Vina energy components

docking box effects

protonation artifacts

crystal structure-specific patterns

Controls

Remove:

Vina score

docking rank

ligand identity

and test.

Also:

Use:

alternate docking engines

Example:

Vina-generated poses

GNINA-generated poses

DiffDock poses

If the model works only on Vina artifacts, the discovery is weaker.

B) What makes the discovery claim conclusive?

The claim needs to move from:

“My model improved my benchmark”

to:

“Pose geometry contains recoverable biological signal that standard scoring loses.”

That requires five things.

1. Multiple independent targets

Current:

one system

one protein family

Needed:

At least:

5–10 targets

different folds

different ligand classes

A judge wants:

“Is this a method or a case study?”

2. Locked prospective evaluation

The gold standard.

Before seeing results:

Register:

dataset

split

metric

model

Then run.

No tuning afterward.

3. Beat strong baselines

Current:

Raw Vina:
0.534

MLP:
0.830

GNN:
0.833

The uncomfortable interpretation:

“GNN does not beat the simpler learned baseline.”

The current result shows:

learning helps

but not:

pose graph is uniquely responsible.

Needed:

Compare against:

RF on fingerprints

XGBoost on descriptors

ChemBERTa embedding

ligand-only GNN

GNINA CNN scoring

4. Mechanistic interpretability

ISEF judges like this.

Show:

“The model prioritizes physically meaningful interactions.”

Examples:

hydrogen bonds

salt bridges

conserved pocket residues

buried hydrophobic contacts

Then validate:

remove those contacts → prediction decreases.

5. External validation

The strongest experiment:

Train:

7KX5 dataset

Test:

8V8E dataset

No retraining.

If it transfers:

that is your breakthrough evidence.

C) Ranked next experiments by ISEF evidentiary value
Tier 1 — Highest value
1. Complete 8V8E transfer validation ⭐⭐⭐⭐⭐

Current status:

“partially documented”

Finish this.

Question:

Does a model trained on one chemotype generalize to another?

Possible outcomes:

succeeds → major evidence

fails → valuable mechanistic finding

Either way, scientifically strong.

2. Scaffold-split evaluation ⭐⭐⭐⭐⭐

Probably the single most important missing analysis.

Current random splits may be flattering.

3. Multi-target retrospective benchmark ⭐⭐⭐⭐⭐

Even 5 targets is transformative.

Possible sources:

PDBbind subsets

ChEMBL activity sets

Tier 2
4. Ablation study ⭐⭐⭐⭐

Prove the graph matters.

Minimum:

ligand-only

pose-only

full graph

5. Statistical significance analysis ⭐⭐⭐⭐

Add:

bootstrap AUROC CI

DeLong test

permutation test

Tier 3
6. Architecture innovation ⭐⭐

Do not spend months inventing a more complex network.

Current bottleneck:

not architecture.

It is validation.

A simpler model with airtight validation beats a novel model with weak validation.

D) What would a Natasha Kulviwat-style identify-and-verify winner say is missing?

A top science-fair computational biology winner usually has this pattern:

1. Identify a real bottleneck

You have this:

docking scores often fail ranking.

Good.

2. Verify the bottleneck independently

Partial.

You showed:

Vina fails one curated set.

Need:

multiple targets.

3. Build the smallest intervention

Your intervention:

pose-graph rescoring.

Good.

4. Verify causality

Missing.

The judge asks:

“What exactly caused improvement?”

Currently unknown:

graph geometry?

molecular descriptors?

scaffold memorization?

dataset bias?

5. Produce a generalizable principle

The winning sentence is not:

“I made an AI rescoring model.”

Many students do that.

The winning sentence is:

“I discovered that docking failures arise because energetic scoring discards relational pose information, and I demonstrated that recovering this information improves ranking across chemically independent targets.”

You are not there yet.

Final judge ranking
Component	Current strength
Problem significance	Strong
Baseline failure demonstration	Strong
Reproducibility	Strong
ML novelty	Moderate
Validation rigor	Moderate
Generality	Weak
ISEF readiness	Promising but not closed
The one experiment that changes the project category:

A preregistered scaffold-split, multi-target, external validation where pose-graph rescoring beats Vina and ligand-only baselines.

If that succeeds, this becomes a methods contribution.

If not, the honest conclusion may still be valuable:

learned rescoring improves retrospective docking ranking, but pose graphs do not provide unique transferable information beyond chemical descriptors.

That negative result would still be scientifically credible. The danger is not failure; the danger is claiming a mechanism the experiments have not isolated.
```

### Independent assessment (this lane, not the judge)
- The scaffold-split attack is the decisive one and is correct: random-split
  AUROC 0.83 on n=59 can be scaffold memorization. This becomes a locked
  gate BEFORE any further claim.
- The "GNN ties MLP" reading is already our own honest verdict (learned-
  family tie); the critique sharpens it: without ligand-only vs pose-only
  ablations, "pose geometry carries the signal" is unsupported. Adopted.
- Significance testing (bootstrap CI, DeLong vs raw Vina) is cheap and
  required; adopted.
- The 8V8E transfer (train on one chemotype, test on another, no
  retraining) is the strongest single generalization experiment available
  with existing data; adopted as the discovery-critical test.
- Multi-target expansion (5+ targets) is real but compute-heavy; staged
  after the four tests above, and only with locked selection criteria
  declared first (prevents the cherry-picking attack).

### Changes adopted from this round (locked 2026-09-26 before outcomes)
1. SCAFFOLD-SPLIT GATE: Bemis-Murcko scaffold split of the n=59 bigscreen
   set; GNN and MLP re-evaluated with bootstrap 95% CI + DeLong p vs raw
   Vina on the identical split. The rescoring claim stands only if the
   learned models beat Vina with CI excluding the Vina point estimate.
2. ABLATION TABLE (locked): ligand-only GNN / pose-contact-only / full
   pose graph / randomized-pose-graph / random labels, same split.
3. LEAKAGE CONTROL: Vina score and dock rank removed from rescorer
   features; re-evaluated on the same split.
4. TRANSFER TEST COMPLETED: train on the 7KX5-chemotype screen, evaluate
   once on 8V8E (ensitrelvir chemotype), no retraining; outcome reported
   either way (success = generalization evidence; failure = documented
   boundary, pivot per rule 6).
5. DISCOVERY CLAIM RESTATED (G4 in docs/PREREGISTER.md): the
   methodological discovery is now "pose-geometry signal survives scaffold
   split, ablation, leakage control, and cross-chemotype transfer" - all
   four required, none sufficient alone.
