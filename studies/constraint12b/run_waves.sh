#!/bin/bash
# 12B AD4 docking: 18 runs in waves of 6 (2-core box), 900s cap each (locked).
cd /home/sandbox/work/12/studies/constraint12b
AD4=/home/sandbox/work/12/bin/ad4/autodock4
jobs=()
for tag in 7vh8 7c6s; do
  for arm in A0 A1 A2; do
    d=.; [ "$arm" = A2 ] && d=biased_$tag
    for s in 0 1 2; do
      jobs+=("$d|12b_${tag}_${arm}_seed${s}.dpf|dock_ad4_${tag}_${arm}_seed${s}.dlg")
    done
  done
done
for ((w=0; w<3; w++)); do
  echo "WAVE $w start $(date -u +%H:%M:%S)" 
  pids=()
  for ((i=w*6; i<w*6+6; i++)); do
    IFS='|' read -r d dpf dlg <<< "${jobs[$i]}"
    ( cd "$d" && timeout 900 "$AD4" -p "$dpf" -l "/home/sandbox/work/12/studies/constraint12b/$dlg" > "${dlg%.dlg}.out" 2>&1; echo "rc=$? $dlg" >> waves_status.txt ) &
    pids+=($!)
  done
  wait "${pids[@]}"
  echo "WAVE $w done $(date -u +%H:%M:%S)"
done
echo ALL_DONE $(date -u +%H:%M:%S)
