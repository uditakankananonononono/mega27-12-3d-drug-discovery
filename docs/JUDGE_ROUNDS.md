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

### Round 1 novelty implementation and verification (2026-09-26, after the locked gate)
- The judge's scaffold-generalization critique produced an actual new analysis:
  `studies/study12_scaffold_split.py`, pre-outcome commit `706c9ed` for the
  corrected paired DeLong test; raw Vina and a train-only-standardized
  descriptor MLP now receive identical Bemis-Murcko grouped test sets over
  five seeds. This turns an ordinary random-split rescoring claim into a
  falsifiable scaffold-transport test. The input is 59 unique labeled
  compounds, 39 scaffolds, with no train/test scaffold overlap in any of
  five splits, checked by running the source script and split inspection.
- Actual output (`results/scaffold_split.json`): Vina mean AUROC 0.5404,
  descriptor MLP mean AUROC 0.9212; bootstrap across five split AUROCs
  gave MLP 95% CI [0.8737, 0.9679]; paired DeLong on seed-0's 16
  independent held-out compounds p=1.94e-10. The **script's narrow gate**
  evaluates true. This is not proof of a pose-geometry mechanism: the MLP
  includes ligand descriptors and a Vina-derived feature, the five
  scaffold splits overlap, and the single seed-0 test is small. Do not
  call its tiny p-value a robust multi-split significance claim.
- Still open: ligand-only vs pose-contact-only GNN ablations, remove Vina
  leakage, 8V8E no-retrain transfer, standard target benchmark and
  external multi-target replication, and a novel validated discovery.
  Until these land, Round 1 is a concrete novelty-improving method step,
  not a completed project or the claimed G4 mechanistic discovery.


## Round 2/10 - 2026-09-26 17:43 IST

Surface: https://chatgpt.com/c/6ab7a5dd-06d8-83e8-bec0-2707215de4b4 (user account, Free tier). ChatGPT is external, untrusted critique - never empirical evidence, never authority over locked gates.

### Verbatim prompt and response
```
Adversarial ISEF judge round 2 for a retrospective SARS-CoV-2 Mpro docking methodology project. Scope is validation/benchmarking only, no design, optimization or nomination of new bioactive compounds. New work after round 1: 59 labeled compounds across 39 Bemis-Murcko scaffolds; five scaffold splits gave mean raw Vina AUROC 0.5404 and descriptor MLP AUROC 0.9212 (descriptive split bootstrap CI 0.8737-0.9679). This is NOT proof of pose geometry; MLP includes a Vina-derived feature and the five test splits overlap. Independent 8V8E reference-ligand transfer redock RMSD 1.4323 Å. A locked pre-outcome ablation will compare raw Vina, descriptor MLP with/without Vina feature, ligand-only 2D GNN, docked-pose graph GCN, pose+descriptor fusion, randomized pose, random-label sanity. Pose GCN must beat ligand-only and randomized-pose on the same pose-available compounds, paired seed-0 DeLong p<.01 against ligand-only. The script has not yet produced results. Attack weaknesses of this test and propose ONE concrete novelty-improving methodological falsifier I can preregister now without seeing the outcome, staying within retrospective benchmarks. Include an independent control, a failure interpretation, and the smallest feasible implementation. Don't prescribe abandoning existing locked gates or compound discovery.
Show more
Adversarial ISEF judge round 2
Current assessment

The project has improved substantially because the central question is now clearer:

Does docked pose geometry contain predictive information beyond ligand chemistry and docking score?

However, the current locked ablation plan is necessary but not sufficient. A hostile judge will argue that even a Pose-GCN win could still be explained by hidden dataset artifacts.

The key issue is identification, not performance.

You are trying to prove a causal statement:

“Pose geometry contributes transferable binding-relevant information.”

Your current test mostly asks:

“Can a graph model exploit information contained in docked poses?”

Those are not identical.

A) Weaknesses a hostile judge will attack in the planned ablation
1. The MLP result exposes a major confound

Your scaffold split result:

Raw Vina AUROC: 0.5404

Descriptor MLP: 0.9212

This is scientifically interesting, but it changes the burden of proof.

A judge will say:

“Before proving pose geometry matters, prove you are not just rediscovering ligand identity.”

The current benchmark is dominated by:

chemical descriptors

Vina-derived information

scaffold distribution

A Pose-GCN beating Vina does not demonstrate structural information.

It must beat:

ligand-only GNN

descriptor model

Vina-containing model

or at least demonstrate a complementary signal.

2. “Same compounds with available poses” creates a selection problem

Your requirement:

Pose GCN must beat ligand-only on same pose-available compounds

is good.

But the judge asks:

“Are compounds with successful docking poses systematically different?”

Examples:

easier-to-dock molecules

larger molecules

certain scaffolds

less flexible molecules

The pose subset itself may create bias.

Required reporting

Before modeling:

compare pose-available vs all compounds:

molecular weight

rotatable bonds

cLogP

scaffold counts

activity distribution

If they differ, acknowledge.

3. Randomized-pose control may be too weak

Randomizing coordinates can produce an obviously nonsensical graph.

A model may win simply because:

“real poses look chemically structured; random graphs look broken.”

That proves the model detects pose plausibility, not necessarily activity-relevant geometry.

A stronger falsifier is needed.

4. Seed-0 DeLong p<0.01 is vulnerable

This is a subtle statistical issue.

A single seed comparison can be unstable.

You already know:

Earlier:

0.946 → revised 0.871 ± 0.050

That is exactly why.

A judge will ask:

“Did you choose seed 0 because it succeeded?”

Even if you did not, seed dependence is real.

Better:

Predefine:

number of seeds

aggregation method

significance test

Example:

“Median AUROC over 5 seeds; DeLong on pooled predictions from locked seed ensemble.”

5. n=59 is still a small benchmark

Even with scaffold splitting, this remains a retrospective benchmark.

A judge will not reject it, but will expect language like:

“evidence of improved ranking on this benchmark”

not:

“solves docking scoring.”

B) ONE concrete novelty-improving methodological falsifier

I would preregister:

Pose-shuffling within scaffold-matched decoys (geometry necessity test)
Scientific question

Does the Pose-GCN use the correct ligand–protein interaction geometry, or merely generic properties of docked structures?

Experiment

For every compound:

Generate the normal docked pose graph.

This is the real condition:

Correct pose graph

Then create a matched falsifier:

Scaffold-preserving pose permutation

Randomly assign each ligand's docked pose graph to another ligand within the same Bemis-Murcko scaffold class or physicochemical neighborhood.

Example:

Compound A receives Compound B's pose geometry.

Preserve:

graph size distribution

ligand complexity

protein environment

dataset composition

Break:

ligand-specific geometry relationship

Train/test exactly as before.

Compare:

Model 1

Real pose graph

vs

Model 2

Scaffold-matched shuffled pose graph

Independent control

Include:

Descriptor-only MLP

Already planned.

Purpose:

Shows whether the information comes from chemistry alone.

Expected outcomes and interpretation
Outcome 1

Real pose graph > shuffled pose graph

Example:

Real:
AUROC 0.82

Shuffled:
AUROC 0.55

Interpretation:

Supports:

ligand-specific docking geometry contributes predictive information.

This is the strongest possible outcome.

Outcome 2

Real pose graph ≈ shuffled pose graph

Interpretation:

The GCN likely learns:

ligand size

contact count

docking artifacts

generic pose statistics

The pose graph is not demonstrating biological geometry.

Outcome 3

Shuffled beats real pose graph

Interpretation:

Possible leakage or dataset artifact.

The method is not learning intended information.

Smallest feasible implementation

This does not require:

new docking

new compounds

new datasets

architecture changes

Implementation:

Save existing pose graphs.

Add a permutation function.

Keep labels unchanged.

Retrain the identical GCN.

Compare AUROC.

Likely effort:

<1 week for a clean implementation.

Why this is higher-value than adding another model

A weaker project asks:

“Can my model get higher AUROC?”

A stronger project asks:

“What information source causes the improvement?”

Your current ablation answers:

“Does a pose model perform better?”

This falsifier answers:

“Does ligand-specific structural arrangement matter?”

That is the methodological discovery.

Updated judge view after this preregistration

If you obtain:

Pose-GCN > ligand-only GNN

Pose-GCN > randomized pose

Pose-GCN > scaffold-matched shuffled pose

External 8V8E transfer succeeds

Performance survives removal of Vina feature

then your claim becomes much stronger:

“Docked pose topology provides an independent ranking signal beyond ligand descriptors and docking score in retrospective Mpro benchmarks.”

If the falsifier fails, the project still has a valid conclusion:

“Retrospective docking improvement is driven by ligand-level information rather than recoverable pose geometry.”

That is exactly the kind of falsifiable methodological question ISEF judges tend to reward.
```

### Independent assessment and novelty foldback (adopted on this lane's own judgment)
- ADOPTED (committed BEFORE the ablation outcome, commits c6c5a99 / 728e7ce / c8a05b8): the scaffold-matched shuffled-pose falsifier as arm I of `studies/study12_ablation.py`. Each compound's pose graph is swapped with another compound's within its Bemis-Murcko scaffold group (deterministic seed 13, deranged; singleton scaffolds permuted among themselves; one declared exception path guarantees full coverage so all arm test sets stay identical for paired DeLong). Labels unchanged. The G-pose gate now additionally requires arm E (real pose) to beat arm I (shuffled pose) on mean AUROC across the same pose-available held-out compounds. If E does not beat I, any pose-GCN gain is generic pose statistics, not ligand-specific geometry, and the pose-geometry claim is withdrawn per the pivot ladder.
- ADOPTED (same commits): pose-availability bias is now reported descriptively in the output (activity rate, MW, rotatable bonds, logP: pose-available vs all compounds), answering the "are dockable compounds systematically different" attack without changing any gate.
- NOT ADOPTED as a gate change: replacing the locked seed-0 DeLong with a pooled-seed test. The judge's seed-dependence point is fair, but the seed-0 DeLong and thresholds were locked before outcomes; moving them now would be goalpost-shifting. Mitigation within the lock: mean AUROC across all 5 splits (already computed) is reported alongside, and the seed-0 DeLong is interpreted only together with the cross-split means.
- NOT ADOPTED: the judge's round-1-style advice to broaden to multi-target external validation remains future work (G2 gate), not this round's change.
This concrete novelty change (arm I falsifier + availability audit) is why this round counts toward the 10-round minimum under the 5:00:38 PM user rule.
