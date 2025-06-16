#!/bin/bash -f

### Use  this script to keep the various FORKS (like em-fact, FACTrial and nci-fact) in sync.. ..
###         .. .. specifically RE: the PIPELINE related-files only.

# ensure CLI has 2 arguments, and set them to SRC_FLDR & DEST_FLDR respectively
if [ $# -ne 2 ]; then
    echo "Usage: $0   SRC_FLDR    DEST_FLDR"
    echo "Example:   SRC = ~/LocalDevelopment/EssexMgmt/FACTrial-BACKEND/         ### FACTrial on CRRI-Cloud's source-code"
    echo "Example:   DEST = ~/LocalDevelopment/EssexMgmt/EssexCloud-emfact-backend-cdk/ ### em-fact on Essex-Cloud's source-code"
    exit 1
fi
SRC_FLDR=$1
DEST_FLDR=$2
echo "SRC_FLDR = '${SRC_FLDR}'"
echo "DEST_FLDR = '${DEST_FLDR}'"
### linux? (Confirmed on MacOS):
while read -r -t 1; do read -r -t 1; done ### "read -r -t0" will return true if stdin-stream is NOT empty
read -p "Press <ENTER> .. .. to continue >> "

# set noglob
set +o noglob

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

### SECTION: Constants

set -e      ### for this initial part of script, any failures are bad!

### We must 'cd' so that '*' will work below!
cd ${SRC_FLDR} > /dev/null

Files2bCompared=(
    ./README*.md
    ./.gitignore

    ./cdk_backend_app.py
    ./cdk_frontend_app.py
    ./cdk_lambda_layers_app.py
    ./cdk_operations_pipeline_app.py
    ./cdk_pipelines_app.py
    ./cdk.json
    ./constants.py
    ./GlobalCdkConfig.py

    ./package.json
    # ./package-lock.json
    ./requirements.in
    # ./requirements.txt

    ./common/
    # ./common/__init__.py
    # ./common/cdk/__init__.py
    # ./common/cdk/constants_cdk.py
    # ./common/cdk/constants_cdk.py
    # ./common/cdk/mappings.py
    # ./common/cdk/retention_base.py
    # ./common/cdk/StandardBucket.py
    # ./common/cdk/standard_lambda.py
    # ./common/cdk/StandardCodeBuild.py
    # ./common/cdk/StandardCodePipeline.py

    ./cdk_utils

    ./api/config.py
    ./api/infrastructure*.py
    ./api/*.sh

    ./cognito/infrastructure.py
    ./cognito/src/*.py

    ./backend/common_aws_resources_stack.py
    # ./backend/database/
    ./backend/database/vpc_rds
    ./backend/database/README*
    ./backend/src
    ./backend/infra
    ./backend/lambda_layer

    ./backend/common_aws_resources_stack.py

    # ./backend/etl/__init__.py
    # ./backend/etl/infrastructure.py
    # ./backend/etl/runtime/
    # ./backend/etl/runtime/connectors/
    # ./backend/etl/runtime/database
    # ./backend/etl/runtime/utils/
    # ./backend/etl/runtime/exceptions/
    # ./backend/etl/runtime/common/
    # ./backend/etl/runtime/model/
    # ./backend/etl/runtime/rest_api/
    # ./backend/etl/tests/
    # ./backend/etl/tests/conftest.py
    # ./backend/etl/tests/unittests/
    # ./backend/etl/tests/unittests/test_utils/
    # ./backend/etl/scripts/

    ./app_pipeline/*.py

    ./devops
    # ./devops/pipeline.py
    # ./devops/bin/
    # ./devops/README*

    # ./devops/1-click-end2end/bin/
    # ./devops/1-click-end2end/lib/
    # ./devops/1-click-end2end/test/
    # ./devops/1-click-end2end/.*ignore
    # ./devops/1-click-end2end/cdk.json
    # ./devops/1-click-end2end/package*.json
    # ./devops/1-click-end2end/README.md
    # ./devops/1-click-end2end/tsconfig.json

    # ./devops/post-deployment/bin/
    # ./devops/post-deployment/lib/
    # ./devops/post-deployment/test/
    # ./devops/post-deployment/.*ignore
    # ./devops/post-deployment/cdk.json
    # ./devops/post-deployment/package*.json
    # ./devops/post-deployment/README.md
    # ./devops/post-deployment/tsconfig.json

    # ./devops/cleanup-stacks/bin/
    # ./devops/cleanup-stacks/lib/
    # ./devops/cleanup-stacks/test/
    # ./devops/cleanup-stacks/.*ignore
    # ./devops/cleanup-stacks/cdk.json
    # ./devops/cleanup-stacks/package*.json
    # ./devops/cleanup-stacks/README.md
    # ./devops/cleanup-stacks/tsconfig.json

    ./frontend/README*
    ./frontend/infrastructure

    ./docs/

    ./operations/bin
    ./operations/pipeline.py
    ./operations/CloudFormation
    ./operations/AWS-SAM
    ./operations/CDK

)

### Uncomment this line below, for debugging purposes.
# tar -C ${SRC_FLDR} -c  ${Files2bCompared[@]} | tar -tv

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
OPS_SCRIPT_FOLDER="$( \cd "${SCRIPT_FOLDER}/../../operations/bin"; pwd  )"

### .........................

    .     ${SCRIPT_FOLDER}/common/sync-folder-utility-functions.sh

#   .   "${OPS_SCRIPT_FOLDER}/common-settings.sh"

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

### wipe out all cdk.out/ node_modules/ __pycache__/
./devops/bin/clean.sh

###------------------


YesAtleastOneFileChanged=0

for aPath in ${Files2bCompared[@]} ; do
    # sleep 1
    ### if it is a Directory, recurse.  Else, do `diff`
    if [ -d  "${SRC_FLDR}/${aPath}" ]; then
        # compareFolders "${aPath}"
        myDirDiff  "${aPath}"   "${SRC_FLDR}"  "${DEST_FLDR}"
    else
        ### Just a plain file.
        myFileDiff   "${SRC_FLDR}"   "${DEST_FLDR}" "${aPath}"
    fi
done

if [ ${YesAtleastOneFileChanged} -eq 0 ]; then
    echo "No differences found.✅"
# else
#     while read -r -t 1; do read -r -t 1; done
#     read -p "⚠️⚠️⚠️ -- Ok to Copy files from ${SRC_FLDR} -to-> ${DEST_FLDR}? (y/n) >>" ANS
#     while read -r -t 1; do read -r -t 1; done
#     read -p "⚠️⚠️⚠️ -- (AGAIN a 2nd-time) Ok to Copy files from ${SRC_FLDR} -to-> ${DEST_FLDR}? (y/n) >>" ANS
#     echo ''; echo ''
#     if [ "${ANS}" == "y" ]; then
#         echo \
#         "tar -C ${SRC_FLDR} -c  ${Files2bCompared[@]} | tar -C ${DEST_FLDR} -xv"
#     else
#         echo "No files copied !!!"
#     fi
#     echo ''; echo ''
fi


# EoInfo
