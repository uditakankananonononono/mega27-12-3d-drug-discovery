# MEGA27-12: Structure-Based 3D Drug Discovery

Real molecular docking with AutoDock Vina 1.2 (the actual engine, not a reimplementation),
pushed as far as a 1-2 GB CPU sandbox allows.

## Pipeline
1. **Protocol validation**: redock a co-crystal ligand into SARS-CoV-2 Mpro and measure
   heavy-atom RMSD against the crystal pose. Gate: RMSD < 2.0 A. Committed result
   (results/redock_7KX5.json): 7KX5 / JUN8-76-3A, RMSD 0.97 A, PASS. No 6LU7/N3 redock
   result is committed. The covalent redocks (results/covalent_redock_corrected.json)
   did not pass (e.g. 7vh8: 0 of 3 seeds, RMSD 14.8-22.2 A).
2. **Screening campaign**: dock a curated set of 22 approved/clinical drugs
   (canonical SMILES pulled live from PubChem) against Mpro; rank by Vina affinity.
3. **Enrichment analysis**: known Mpro actives are scored against the ranking. Result
   (results/screen_summary.json): 2 of 7 actives in the top 8 vs 2.55 expected by chance,
   enrichment factor 0.79; raw-Vina AUROC 0.34 (results/screen_analysis.json). This is a
   negative result: Vina ranking does not enrich the known actives in this set.
4. **CNN/GNN rescoring**: pose-graph neural rescoring trained on docked pose features,
   compared against raw Vina. Leave-one-out AUROC on the 15 labeled ligands: GNN 0.95,
   NN 0.68 vs raw Vina 0.34 (results/screen_analysis.json); on the 59-label combined set
   GNN 0.83 vs raw Vina 0.53 (results/bigscreen_analysis.json). Small-n, not external validation.

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
