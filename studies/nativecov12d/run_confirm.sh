#!/bin/bash
# 12D confirmation: 7VH8 C2 seed 77000, box 28.5 A (npts 76), all else as 12A
cd /home/sandbox/work/12/studies/nativecov12d
export LD_LIBRARY_PATH=/home/sandbox/work/12/bin/pocl-prefix/usr/lib/x86_64-linux-gnu:/home/sandbox/work/12/bin/pocl-prefix/usr/lib/x86_64-linux-gnu/pocl:$LD_LIBRARY_PATH
export OCL_ICD_VENDORS=/home/sandbox/work/12/bin/pocl-vendors/pocl.icd
export POCL_WORK_GROUP_METHOD=cbs
/home/sandbox/work/12/bin/adgpu/autodock_cpu_128wi --lfile 7vh8_lig_reactive.pdbqt --flexres 7vh8_rec_flex.pdbqt --ffile 7vh8_rec_rigid.maps.fld --import_dpf 7vh8_rec.reactive_config --nrun 10 --nev 1000000 --ngen 27000 --psize 150 --lsit 300 --seed 77000 --resnam dock_7vh8_C2_box28_seed0 > confirm.log 2>&1
echo "rc=$?" >> confirm.log
