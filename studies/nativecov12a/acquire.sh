#!/bin/bash
set -x
cd /home/sandbox/work/12
echo "=== download adgpu binary ==="
curl -sL -o bin/adgpu/adgpu "https://github.com/ccsb-scripps/AutoDock-GPU/releases/download/v1.6/adgpu-v1.6_linux_x64_ocl_128wi" && chmod +x bin/adgpu/adgpu
sha256sum bin/adgpu/adgpu
echo "=== pocl debs ==="
mkdir -p /tmp/pocl-debs && cd /tmp/pocl-debs
# BFS over Depends
declare -A seen
queue="libpocl2 pocl-opencl-icd libpocl2-common libhwloc15 libclang-cpp11"
touch /tmp/pocl-debs/list.txt
while [ -n "$queue" ]; do
  pkg=$(echo $queue | cut -d' ' -f1)
  queue=$(echo $queue | cut -d' ' -f2- -s)
  [ -n "${seen[$pkg]}" ] && continue
  seen[$pkg]=1
  apt-get download "$pkg" >>/tmp/pocl-debs/dl.log 2>&1 && echo "$pkg" >> /tmp/pocl-debs/list.txt
  deps=$(apt-cache depends "$pkg" 2>/dev/null | grep -E '^\s+(PreDepends|Depends):' | awk '{print $2}' | grep -v '[<>]' | grep -v -E '^libc6$|^libstdc\+\+6$|^libgcc-s1$|^libzstd1$|^zlib1g$|^libxml2$|^libicu70$|^liblzma5$|^libncursesw6$|^libtinfo6$|^libedit2$|^libffi8$|^libbsd0$|^libmd0$')
  for d in $deps; do [ -z "${seen[$d]}" ] && queue="$queue $d"; done
done
echo "=== extract ==="
mkdir -p /home/sandbox/work/12/bin/pocl-prefix
for f in *.deb; do dpkg-deb -x "$f" /home/sandbox/work/12/bin/pocl-prefix; done
# vendored ICD with absolute path to the extracted libpocl (deb icd points at /usr)
mkdir -p /home/sandbox/work/12/bin/pocl-vendors
echo "/home/sandbox/work/12/bin/pocl-prefix/usr/lib/x86_64-linux-gnu/libpocl.so.2.8.0" > /home/sandbox/work/12/bin/pocl-vendors/pocl.icd
ls /home/sandbox/work/12/bin/pocl-prefix/etc/OpenCL/vendors/ 2>/dev/null
echo "=== smoke adgpu ==="
P=/home/sandbox/work/12/bin/pocl-prefix
export LD_LIBRARY_PATH=$P/usr/lib/x86_64-linux-gnu:$P/usr/lib/x86_64-linux-gnu/pocl:$LD_LIBRARY_PATH
export OCL_ICD_VENDORS=$P/etc/OpenCL/vendors/pocl.icd
/home/sandbox/work/12/bin/adgpu/adgpu --help 2>&1 | head -30
echo ACQUIRE_DONE
