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
