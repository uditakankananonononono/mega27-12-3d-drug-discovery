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
