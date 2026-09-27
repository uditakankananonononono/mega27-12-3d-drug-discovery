# Covalent branch run log (lane 12, item 6) - 2026-09-28

Prereg: docs/PREREG_COVALENT_BOUNDED_20260928.md (commit af8b5e5, pre-outcome).

## Part A: engine acquisition - SUCCESS within the 60-minute budget

Attempt order per prereg:
1. AutoDock-GPU v1.6 prebuilt linux_x64 OpenCL binary from the project's
   GitHub releases (SHA-256 8a22804c1fde62a59c030a45e8a9d9d960ff329d22e4927daf7464df393b8047).
   Binary runs but cannot dock: clGetPlatformIDs() returns -1001, no OpenCL
   platform is installed on this machine (ICD loader only, no vendor runtime,
   no GPU). Path abandoned.
2. AutoDock4 + AutoGrid4 compiled from the official project sources:
   - github.com/ccsb-scripps/AutoDock4 commit 192ecda05d7c566161046f0a1d604f3336e0cf3a
     -> autodock4 4.2.7.x, binary SHA-256
     7295aa259b8bdc167ca43b080f8f6877e3f611942b093d8c46ec566c05c16c80
   - github.com/ccsb-scripps/AutoGrid commit 6d2847beaeac8ff43ca99094707fd74e3ca1ff37
     -> autogrid4 4.2.8, binary SHA-256
     554cd9935584db3b4e9be022aef04cea3de21975ab70a36f3b3a5cdf20aacfc3
   - Build: autotools (autoreconf -i && ./configure && make -j4). The build's
     csh-only default_parameters.h generation step was replaced with a
     byte-faithful Python equivalent (same egrep/quoting rules), each repo's
     header generated from its own shipped .dat files (they differ: AutoGrid's
     ad4_shared adds Si and B atom parameters).
   - Binaries archived in repo at bin/ad4/ so the branch is reproducible if
     the scratch filesystem is rebuilt.
   Both binaries pass their own version/startup checks.

## Part B: self-redock audit (7VH8, 7C6S) - NOT STARTED at this checkpoint

RCSB identity verification at preregistration time (2026-09-28):
- 7VH8: SARS-CoV-2 main protease + PF-07321332 (nirmatrelvir), 1.59 A.
- 7C6S: SARS-CoV-2 main protease + boceprevir, 1.6 A.

## Part B protocol LOCKED pre-outcome (2026-09-28 ~05:09 IST), runs launched

Free-ligand inputs: the PDB component records 4WI (7VH8) and U5G (7C6S) are the
post-reaction adduct forms (imidate / gem-hydroxyl), so free nirmatrelvir and
free boceprevir 3D SDFs were taken from PubChem instead (recorded here as the
ligand provenance). Receptors: chain A ATOM records, altloc A kept (7VH8 Cys145
has two SG rotamers; the A rotamer is the adduct one per the LINK record);
residues failing meeko templates dropped (7VH8 TYR154 at 27.7 A from SG145,
7C6S ARG222 at 48.7 A; both far outside the 24 A box).

Classic-AutoDock4 wiring findings (why this differs from the AutoDock-GPU
reactive tutorial): AD4.2.7 has no derived-type support and its intnbp_r_eps
tables are indexed by parameter-library map_index, so (a) meeko's 3-character
flex types were renamed to 2 characters (1C3/1C2/1S4/1H5 -> X1/X2/X3/X4),
(b) the custom parameter library gives X1..X4 unique map_index values 100-103,
(c) because flex-atom type pairs get no default pair tables without maps,
intnbp_r_eps lines were generated for every X-type x ligand-type pair using
standard AD4 combining rules (Rij = Rii_X + Rii_L, epsij = sqrt(eps_X eps_L),
12-6), with the four meeko reactive-config pairs overriding: X3-C1 13-7
(1.8 A, eps 2.5, the S-C pseudo-bond), X1-C1 and X2-C1 12-6 (2.0 A), X4-C1
near-zero. Approximation noted: H-bond 12-10 directionality involving the
flex HG (X4) and SA (X3) is approximated as 12-6; the dominant terms for pose
placement are the pseudo-bond and the VdW field.

Locked protocol: per complex, 3 seeds (DPF seed pairs 77000+s / 88000+s,
s = 0,1,2), 10 LGA runs per seed, ga_num_evals 1,000,000, pop 150,
Solis-Wets local search (parameters in the committed DPFs). Grid: 24 A box,
center projected 5 A from CB along the CA-CB bond (meeko
--box_center_off_reactive_res), spacing 0.375 A. Locked success criterion
(from the prereg): best-energy pose heavy-atom RMSD <= 2.0 A against the
crystallographic ligand in at least 2 of 3 seeds = self-redock succeeds;
no superposition (receptor frame retained). RMSD analysis was not written or
run before this lock.

Six docking runs (2 complexes x 3 seeds) launched detached at ~05:10 IST;
results and the RMSD audit land in results/covalent_redock.json on completion.
Inputs and DPFs committed under studies/covalent/.
