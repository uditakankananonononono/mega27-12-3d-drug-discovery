# MEGA27-12: Structure-Based 3D Drug Discovery

Real molecular docking with AutoDock Vina 1.2 (the actual engine, not a reimplementation),
pushed as far as a 1-2 GB CPU sandbox allows.

## Pipeline
1. **Protocol validation**: redock the N3 inhibitor into SARS-CoV-2 Mpro (PDB 6LU7)
   and measure heavy-atom RMSD against the crystal pose. Gate: RMSD < 2.0 A.
2. **Screening campaign**: dock a curated set of real approved/clinical drugs
   (canonical SMILES pulled live from PubChem) against Mpro; rank by Vina affinity.
3. **Enrichment analysis**: known Mpro actives (ebselen, carmofur, disulfiram,
   boceprevir, GC376, nirmatrelvir) must enrich the top ranks vs random expectation.
4. **CNN/GNN rescoring**: pose-graph neural rescoring trained on docked pose features,
   compared against raw Vina ranks for active enrichment.

Hermetic pytest suite (committed mini-receptor/ligand fixtures); live structure and
PubChem fetches only outside CI.

## Active compute state (2026-10-07, 23:25 IST)
The 12E-CR confirmation redock (locked prereg
docs/PREREG_12E_CONFIRMATION_REDOCK_20261007.md) is running, not stalled: the
driver process and first-seed engine are alive and consuming CPU whenever the
workspace is awake. This sandbox is suspended for most of each wall-clock
hour, so only about 70 seconds of compute advances per 16 wall-clock minutes.
At that throttle the six serial one-hour engine caps can stretch across days;
there is no credible wall-clock completion window. This state is deliberate:
a smaller grid or shorter search would be a different preregistration, so the
locked protocol stays unchanged and consumes no CPU while the workspace sleeps.
