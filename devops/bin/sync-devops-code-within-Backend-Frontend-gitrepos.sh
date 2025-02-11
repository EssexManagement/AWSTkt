#!/bin/bash -f

### Use  this script to keep BACKEND & FRONTEND gir-repos in sync.. ..
###         .. .. specifically RE: the PIPELINE related-files only.
### In an ideal-world, we use a single massive MONO-REPO for entire-project (covering FRONTED, BACKEND and another components)

# ensure CLI has 2 arguments, and set them to SRC_FLDR & DEST_FLDR respectively
if [ $# -ne 2 ]; then
    echo "Usage: $0 SRC_FLDR DEST_FLDR"
    exit 1
fi
SRC_FLDR=$1
DEST_FLDR=$2
# SRC_FLDR=~/LocalDevelopment/EssexMgmt/FACTrial-BACKEND/         ### BACKEND-git-repo within FACTrial on CRRI
# DEST_FLDR=~/LocalDevelopment/EssexMgmt/FACTrial-frontend-cdk/   ### FRONTEND within -SAME- fork.
echo "SRC_FLDR = '${SRC_FLDR}'"
echo "DEST_FLDR = '${DEST_FLDR}'"
### linux? (Confirmed on MacOS):
while read -r -t 1; do read -r -t 1; done ### "read -r -t0" will return true if stdin-stream is NOT empty
read -p "Press <ENTER> .. .. to continue >> "

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

### SECTION: Constants

set -e      ### for this initial part of script, any failures are bad!

SrcPaths=(
    common/
    cdk_utils/
    devops/bin/
    ### --> app_pipeline Warning! Never overwrite the app-pipelines are they are UNIQUE!!
)

### Uncomment this line below, for debugging purposes.
# tar -C ${SRC_FLDR} -c  ${PIPELINE_FILES[@]} | tar -tv

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

### Define the temporary files (to save the output of JQ commands below)
###------------ SCRATCH-VARIABLES & FOLDERS ----------

# TMPROOTDIR="/tmp/${MyCompanyName}"
TMPROOTDIR="/tmp/devops"
if [ -z ${SCRIPTFOLDER+x}          ]; then SCRIPTFOLDER=$(dirname -- "$0");                   fi
if [ -z ${SCRIPTNAME+x}            ]; then SCRIPTNAME=$(basename -- "$0");                    fi
if [ -z ${SCRIPTFOLDER_FULLPATH+x} ]; then SCRIPTFOLDER_FULLPATH="$(pwd)/${SCRIPTFOLDER}";    fi
# echo "${SCRIPTFOLDER_FULLPATH}"
if [ -z ${TMPDIR+x}                ]; then TMPDIR="${TMPROOTDIR}/DevOps/${PROJECTID}/${SCRIPTNAME}"; fi

mkdir -p "${TMPROOTDIR}"
mkdir -p "${TMPDIR}"

touch ${TMPDIR}/junk ### To ensure rm commands (under noglob; see many lines below) always work.

TMPFILE11=${TMPDIR}/tmp1.txt
TMPFILE22=${TMPDIR}/tmp22.txt
TMPDIFFOUTP=${TMPDIR}/tmp333.txt

rm -rf "${TMPFILE11}" "${TMPFILE22}" "${TMPDIFFOUTP}"

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

### SECTION: Derived Variables

### Do -NOT- put any derived expressions before these lines.
SCRIPT_FOLDER="$(dirname ${BASH_SOURCE[0]})"
SCRIPT_NAME="$(basename ${BASH_SOURCE[0]})"
CWD="$(pwd)"

### .........................

   .     ${SCRIPT_FOLDER}/common/sync-folder-utility-functions.sh

    ### This above line re: `sync-folder-utility-functions.sh` .. requires BOTH `TMPFILE??` as well as `SCRIPT_FOLDER` variables to be defined!!

### .........................

# Convert the string-value of variable "SRC_FLDR" by replacing all '/' and '~' and ' ' characters with '_'
DEST_FLDR_DIFF_CACHE="${SRC_FLDR}"
DEST_FLDR_DIFF_CACHE=$( echo "${SRC_FLDR}" | sed -e "s|~|${HOME}|" )
DEST_FLDR_DIFF_CACHE=$( echo "${SRC_FLDR}" | tr ' ' '_' )
DEST_FLDR_DIFF_CACHE="$( removeUserHomeFldrFromPath "${DEST_FLDR_DIFF_CACHE}" )"
echo "DEST_FLDR_DIFF_CACHE = '${DEST_FLDR_DIFF_CACHE}'"
DEST_FLDR_DIFF_CACHE="${DEST_FLDR}/.diff"
# DEST_FLDR_DIFF_CACHE="${DEST_FLDR}/.diff/${DEST_FLDR_DIFF_CACHE}"
echo "DEST_FLDR_DIFF_CACHE = '${DEST_FLDR_DIFF_CACHE}'"
### Attention: The path -UNDER- '.diff/' is actually the SRC/SOURCE-path !!!!!

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

set +e  ### failures in `diff` and other commands is expected!!!

pushd ${SRC_FLDR} > /dev/null
echo ''

###------------------

myFileDiff  ${SRC_FLDR}    ${DEST_FLDR}   constants.py
myFileDiff  ${SRC_FLDR}    ${DEST_FLDR}   .gitignore

YesAtleastOneFileChanged=0

for srcSubFldr in ${SrcPaths[@]}; do
    myDirDiff  "${srcSubFldr}"   "${SRC_FLDR}"  "${DEST_FLDR}"
done

if [ ${YesAtleastOneFileChanged} -eq 0 ]; then
    printf "\nNo differences found.✅\n\n"
    exit 0
else
    exit 1
fi

popd

# EoInfo
