#!/bin/bash
cd /home/sandbox/work/12/studies/nativecov12d/d6
export LD_LIBRARY_PATH=/home/sandbox/work/12/bin/pocl-prefix/usr/lib/x86_64-linux-gnu:/home/sandbox/work/12/bin/pocl-prefix/usr/lib/x86_64-linux-gnu/pocl:$LD_LIBRARY_PATH
export OCL_ICD_VENDORS=/home/sandbox/work/12/bin/pocl-vendors/pocl.icd
export POCL_WORK_GROUP_METHOD=cbs
/home/sandbox/work/12/bin/adgpu/autodock_cpu_128wi --lfile X7V_ligand.pdbqt --ffile rec.maps.fld --nrun 10 --nev 1000000 --ngen 27000 --psize 150 --lsit 300 --seed 77000 --resnam d6_7kx5 > d6.log 2>&1
echo "rc=$?" >> d6.log
