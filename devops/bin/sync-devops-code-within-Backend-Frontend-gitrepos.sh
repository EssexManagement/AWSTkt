#!/bin/bash -f

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

### ===============================================================================

# set noglob
set +o noglob

### Use  this script to keep BACKEND & FRONTEND gir-repos in sync.. ..
###         .. .. specifically RE: the PIPELINE related-files only.
### In an ideal-world, we use a single massive MONO-REPO for entire-project (covering FRONTED, BACKEND and another components)

### ===============================================================================

SrcPaths=(
    common/
    cdk_utils/
    ### --> app_pipeline Warning! Never overwrite the app-pipelines are they are UNIQUE!!
)

### Uncomment this line below, for debugging purposes.
# tar -C ${SRC_FLDR} -c  ${PIPELINE_FILES[@]} | tar -tv

### ===============================================================================

### Derived Variables

# Convert the string-value of variable "SRC_FLDR" by replacing all '/' and '~' and ' ' characters with '_'
DEST_FLDR_DIFF_CACHE=$(echo "${SRC_FLDR}" | tr '/~ ' '_')
DEST_FLDR_DIFF_CACHE="${DEST_FLDR}/.diff/${DEST_FLDR_DIFF_CACHE}"
### Attention: The path -UNDER- '.diff/' is actually the SRC/SOURCE-path !!!!!

###--------------------------------------------------------
###@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###--------------------------------------------------------

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

###--------------------------------------------------------
###@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###--------------------------------------------------------

### 1st param is a folder (The source) -- Currently this is IGNORED!
### 2nd param is also a folder (the destination)
### 3rd param is a simple-filename (under the source-folder a.k.a. param #1)
function myDiffCacheFilePath {
    SrcFldr="$1"
    DestFldr="$2"
    simpleFileName="$3"

    # echo "${DestFldr}/.diff/${DEST_FLDR_DIFF_CACHE}/${simpleFileName}"
    return "${DestFldr}/.diff/${DEST_FLDR_DIFF_CACHE}/${simpleFileName}"
}

### 1st param is a folder (The source)
### 2nd param is also a folder (the destination)
### 3rd param is OPTIONAL - a simple-filename or a SUB-folder (under the source-folder a.k.a. param #1)
function mydiff {
    SrcFldr="$1"
    DestFldr="$2"
    simpleFileName="$3"
    if [ ! -f ${simpleFileName} ]; then
        echo "mydiff() Bash-function can -NOT- handle 3rd-param being a FOLDER or SYMLINK"
        echo "   simpleFileName = '${simpleFileName}'"
        exit 55
    fi

    if [ "${simpleFileName}" == "" ]; then
        diff -q   "${SrcFldr}"   "${DestFldr}" >& "${TMPDIFFOUTP}"
    else
        if [ -d "${SrcFldr}/${simpleFileName}" ]; then
            diff -rwq   ${SrcFldr}/${simpleFileName}   ${DestFldr}/${simpleFileName} >& "${TMPDIFFOUTP}"
        else
            diff -wq    ${SrcFldr}/${simpleFileName}   ${DestFldr}/${simpleFileName} >& "${TMPDIFFOUTP}"
        fi
    fi
    if [ $? -ne 0 ]; then
        ### The file is DIFFERENT
        ExpectedDiffFilePath=$( myDiffCacheFilePath  ${SrcFldr}  ${DestFldr}  ${simpleFileName} )
        echo "ExpectedDiffFilePath = '${ExpectedDiffFilePath}'"
        diff -wq    ${TMPDIFFOUTP}   ${ExpectedDiffFilePath} >& /dev/null
        if [ $? -ne 0 ]; then
            ### The file is DIFFERENT in ways that was -NOT- anticipated.
            echo "🛑  src= '${SrcFldr}/${simpleFileName}' dest = '${DestFldr}/${simpleFileName}'"
            echo "    expected-diff= '${ExpectedDiffFilePath}' and actual-diff= '${TMPDIFFOUTP}'"
            echo ''
            return 41
        fi

        echo "🛑  ${simpleFileName}"
        # echo \
        # diff -rwq   ${SrcFldr}/${simpleFileName}   ${DestFldr}/${simpleFileName}
        echo \
        cp  -ip   ${SrcFldr}/${simpleFileName}   ${DestFldr}/${simpleFileName}
        echo ''
        return 1
    else
        return 0
    fi
}

### ===============================================================================

pushd ${SRC_FLDR} > /dev/null
echo ''

mydiff  ${SRC_FLDR}    ${DEST_FLDR}   constants.py
mydiff  ${SRC_FLDR}    ${DEST_FLDR}   .gitignore

YesItIsDifferent=0

for SrcPath in ${SrcPaths[@]}; do
    DevOpsFiles=$( ls ${SrcPath}/*.py )

    for aFile in ${DevOpsFiles[@]}; do
        mydiff   ${SRC_FLDR}    ${DEST_FLDR}      ${aFile}
        if [ $? -ne 0 ]; then
            YesItIsDifferent=1
        fi
    done

done

if [ ${YesItIsDifferent} -eq 0 ]; then
    printf "\nNo differences found.✅\n\n"
fi

popd

# EoInfo
