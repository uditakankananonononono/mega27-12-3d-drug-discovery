# 12E-CR workspace-loss recovery, 2026-10-09

The workspace reset erased all uncommitted docking outputs. Five jobs had logged successful completion, but none of their DLG/XML files survived. Those status observations are not usable pose measurements, and no classification was issued. The six jobs are rerun from the original locked protocol; no seeds, thresholds, search settings, or verdict rules change.

Dependencies and Box 1 maps were rebuilt. All pre-docking machinery gates passed again. Regenerated gate/smoke files retain this rerun's evidence; earlier committed versions remain in Git history. The runner now commits and pushes status and DLG/XML files after each completed job, reads back remote main, and stops on checkpoint failure before starting the next job. This is an artifact-durability change, not an outcome-dependent protocol adjustment.
