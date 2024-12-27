#!/bin/bash -f

set -e

SCRIPT_FOLDER="$(dirname ${BASH_SOURCE[0]})"
SCRIPT_NAME="$(basename ${BASH_SOURCE[0]})"
CWD="$(pwd)"

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

srcDir="${1}"
echo "srcDir='${srcDir}' within $0"

zipFileName="${2}"
# zipFileName=etl-layer-${cpu_arch}.zip
echo "zipFileName='${zipFileName}' within $0"

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

pwd
workingDir="/tmp/${SCRIPT_NAME}/"
workingDir="${workingDir}/$$"
echo "workingDir='${workingDir}' within $0"
mkdir -p "${workingDir}"
cd "${workingDir}"
pwd
printf "%.0s*" {1..100} ; echo

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

cp -ip "${srcDir}/requirements.txt"   .

python -m venv .venv;
. .venv/bin/activate;
pip install --upgrade pip;

pip install -r requirements.txt

\rm -rf .venv/bin .venv/pyvenv.cfg .venv/include
mv .venv python
ls -la

### Create zip-file for lambda layer
zip -qry1 "${zipFileName}"  python/
ls -la "${zipFileName}"
# zip -qry1 "${srcDir}/${zipFileName}"  python/
# ls -la "${srcDir}/${zipFileName}"

### Cleanup
cd /tmp
\rm -rf "${workingDir}"

### EoScript
