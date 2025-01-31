#!/bin/bash -f

### Use  this script to keep the various FORKS (like em-fact, FACTrial and nci-fact) in sync.. ..
###         .. .. specifically RE: the PIPELINE related-files only.

SRC_FLDR=~/LocalDevelopment/EssexMgmt/FACTrial-BACKEND/         ### FACTrial on CRRI-Cloud's source-code
DEST_FLDR=~/LocalDevelopment/EssexMgmt/EssexCloud-emfact-backend-cdk/ ### em-fact on Essex-Cloud's source-code

pushd ${SRC_FLDR}

# set noglob
set +o noglob

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

PipelineFiles=(
    ./README*.md
    ./.gitignore

    ./cdk_app.py
    ./cdk_pipelines_app.py
    ./cdk.json
    ./constants.py
    ./GlobalCdkConfig.py

    ./package.json
    # ./package-lock.json
    ./requirements.in
    # ./requirements.txt

    ./common/__init__.py
    ./common/cdk/__init__.py
    ./common/cdk/constants_cdk.py
    ./common/cdk/constants_cdk.py
    ./common/cdk/mappings.py
    ./common/cdk/retention_base.py
    ./common/cdk/StandardBucket.py
    ./common/cdk/standard_lambda.py
    ./common/cdk/StandardCodeBuild.py
    ./common/cdk/StandardCodePipeline.py

    ./cdk_utils/
    ./common/cdk/

    ./cognito/infrastructure.py
    ./cognito/src/*.py

    ./backend/sqs_cdk.py
    ./backend/common_aws_resources_stack.py
    ./backend/lambda_layer/psycopg/
    ./backend/lambda_layer/psycopg_pandas/
    ./backend/lambda_layer/bin/
    ./backend/database/vpc_rds/
    ./backend/database/vpc_rds/lambda/
    ./backend/etl/__init__.py
    ./backend/etl/infrastructure.py
    ./backend/etl/runtime/
    # ./backend/etl/runtime/connectors/
    # ./backend/etl/runtime/database
    # ./backend/etl/runtime/utils/
    # ./backend/etl/runtime/exceptions/
    # ./backend/etl/runtime/common/
    # ./backend/etl/runtime/model/
    # ./backend/etl/runtime/rest_api/
    ./backend/etl/tests/
    # ./backend/etl/tests/conftest.py
    # ./backend/etl/tests/unittests/
    # ./backend/etl/tests/unittests/test_utils/
    ./backend/etl/scripts/
    ./backend/common_aws_resources_stack.py
    ./backend/database/rds_init/
    # ./backend/database/rds_init/infrastructure.py
    # ./backend/database/rds_init/runtime/
    # ./backend/database/rds_init/runtime/model/
    # ./backend/database/rds_init/runtime/common/
    # ./backend/database/rds_init/runtime/rds_init_root_pkg/connectors/
    # ./backend/database/rds_init/runtime/rds_init_root_pkg/utils/
    # ./backend/database/rds_init/runtime/rds_init_root_pkg/csv_reader/
    # ./backend/database/rds_init/runtime_scripts/test_sql_install_handler.py
    # ./backend/database/rds_init/runtime/utils.py

    ./api/config.py
    ./api/config.py
    ./api/infrastructure*.py
    ./api/*.sh

    ./scripts/common-settings.sh

    ./app_pipeline/__init__.py
    ./app_pipeline/deployment.py
    ./app_pipeline/pipeline.py

    ./devops/pipeline.py
    ./devops/bin/
    ./devops/README*

    ./devops/1-click-end2end/bin/
    ./devops/1-click-end2end/lib/
    ./devops/1-click-end2end/test/
    ./devops/1-click-end2end/.*ignore
    ./devops/1-click-end2end/cdk.json
    ./devops/1-click-end2end/package*.json
    ./devops/1-click-end2end/README.md
    ./devops/1-click-end2end/tsconfig.json

    ./devops/post-deployment/bin/
    ./devops/post-deployment/lib/
    ./devops/post-deployment/test/
    ./devops/post-deployment/.*ignore
    ./devops/post-deployment/cdk.json
    ./devops/post-deployment/package*.json
    ./devops/post-deployment/README.md
    ./devops/post-deployment/tsconfig.json

    ./devops/cleanup-stacks/bin/
    ./devops/cleanup-stacks/lib/
    ./devops/cleanup-stacks/test/
    ./devops/cleanup-stacks/.*ignore
    ./devops/cleanup-stacks/cdk.json
    ./devops/cleanup-stacks/package*.json
    ./devops/cleanup-stacks/README.md
    ./devops/cleanup-stacks/tsconfig.json

    ./operations/bin/
    ./operations/pipeline.py
    ./operations/CloudFormation/*

    ./docs/

)

### Uncomment this line below, for debugging purposes.
# tar -C ${SRC_FLDR} -c  ${PipelineFiles[@]} | tar -tv

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
TMPDiffFILE=${TMPDIR}/tmp333.txt

rm -rf "${TMPFILE11}" "${TMPFILE22}" "${TMPDiffFILE}"

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

### wipe out all cdk.out/ node_modules/ __pycache__/
./devops/bin/clean.sh

compareFilesInSubFolder_2() {
    SubFldrPath="$1"
    SimpleFilename="$2"

    compareFilesAt "${SubFldrPath}/${SimpleFilename}"
    return $?
}

### ..............................................................................................

whetherToSaveFileDiffAsNormal() {
    FilePath="$1"
    TMPDiffFILE="$2"

    while read -r -t 1; do read -r -t 1; done ### "read -r -t0" will return true if stdin-stream is NOT empty
    read -p "Files differ! "c" to Copy // 'y' to reset this to NEW-NORMAL diff-output >>" ANS
    if [ "${ANS}" == "c" ] || [ "${ANS}" == "C" ]; then
        cp -ip "${SRC_FLDR}/${FilePath}" "${DEST_FLDR}/${FilePath}"
    fi
    if [ "${ANS}" == "y" ] || [ "${ANS}" == "Y" ]; then
        mkdir -p  $( dirname -- "${DEST_FLDR}/.diff/${FilePath}" )
        echo ''; echo \
        mv -i "${TMPDiffFILE}" "${DEST_FLDR}/.diff/${FilePath}"
        sleep 2;
        mv -i "${TMPDiffFILE}" "${DEST_FLDR}/.diff/${FilePath}"
    fi
    return 0
}

### ..............................................................................................

compareFilesAt() {
    FilePath="$1"

    if [ ! -f "${SRC_FLDR}/${FilePath}" ] && [ ! -f "${DEST_FLDR}/${FilePath}" ]; then
        echo "comparing: '${SRC_FLDR}/${FilePath}' '<-->' '${DEST_FLDR}/${FilePath}'"
        echo "Oh!oh! compareFilesInSubFolder() invoked with 2 params that are -NOT- simple filenames"
        return 1
    fi

    diff "${SRC_FLDR}/${FilePath}" "${DEST_FLDR}/${FilePath}" > "${TMPDiffFILE}"
    if [ $? -ne 0 ]; then
        # YesFileDidChange=1
        if [ ! -f "${DEST_FLDR}/.diff/${FilePath}" ]; then
            echo "comparing: '${SRC_FLDR}/${FilePath}' '<-->' '${DEST_FLDR}/${FilePath}'"
            whetherToSaveFileDiffAsNormal "${FilePath}" "${TMPDiffFILE}"
            return $?
        fi
        echo \
        diff -wq "${DEST_FLDR}/.diff/${FilePath}" "${TMPDiffFILE}"
        diff -wq "${DEST_FLDR}/.diff/${FilePath}" "${TMPDiffFILE}"
        if [ $? -ne 0 ]; then
            echo "comparing: '${SRC_FLDR}/${FilePath}' '<-->' '${DEST_FLDR}/${FilePath}'"
            read -p "Files differ! enter 'y' to reset this to NEW-NORMAL diff-output >>" ANS
            if [ "${ANS}" == "y" ] || [ "${ANS}" == "Y" ]; then
                whetherToSaveFileDiffAsNormal "${FilePath}" "${TMPDiffFILE}"
            else
                echo ''; echo "🛑  ${FilePath}"; echo '';
                return 1
            fi
        else
            echo '>'
        fi
    else
        echo -n '_'
    fi
    return 0
}



compareFolders() {
    aFilePath="$1"

    #__ echo "SUBFOLDER =  \"${SRC_PATH}/${aFilePath}\" .."
    # for anotherFile in $( \ls "${SRC_PATH}/${aFilePath}"/* ) ; do
    #    ${anotherFile} isa  FULL path !! Unlike the `for` stmt below
    for anotherFile in "${SRC_FLDR}/${aFilePath}"/* ; do
        if [ "${anotherFile}" == "__pycache__" ]; then continue; fi
        # diff -rwq  "${anotherFile}" "${SRC_FLDR}/${aFilePath}" >& /dev/null ### Reverse the comparison -- UNFORTUNATELY.
        # subSrcFile="${SRC_FLDR}/${aFilePath}/$( basename ${anotherFile} )"
        if [ -d  "${SRC_FLDR}/${aFilePath}/${anotherFile}" ]; then
            ### recursion
            echo ''; echo " ⁉️ recursion ⁉️ at ${aFilePath}/${anotherFile} .. "
            compareFolders "${aFilePath}/${anotherFile}"
        else
            compareFilesAt "${aFilePath}/${anotherFile}"
        fi
    done

}

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================


YesAtleastOneFileChanged=0

for aFilePath in ${PipelineFiles[@]} ; do
    # sleep 1
    if [ ! -e "${SRC_FLDR}/${aFilePath}" ]; then
        echo "🛑  ${aFilePath} does not exist in ${SRC_FLDR} !!"
        exit 88
    fi
    if [ ! -e "${DEST_FLDR}/${aFilePath}" ]; then
        mkdir -p $( dirname "${DEST_FLDR}/${aFilePath}" )
        cp -ipr  "${SRC_FLDR}/${aFilePath}"  "${DEST_FLDR}/${aFilePath}"
    else
        ### if it is a Directory, recurse.  Else, do `diff`

        if [ -d  "${SRC_FLDR}/${aFilePath}" ]; then
            compareFolders "${aFilePath}"
            exit 99
        else
            ### Just a plain file.
            # compareFilesInSubFolder "${SRC_FLDR}/${aFilePath}"  "${DEST_FLDR}/${aFilePath}"
            compareFilesAt "${aFilePath}"
            if [ $? -ne 0 ]; then
                YesAtleastOneFileChanged=1
                # echo "🛑  ${aFilePath}"
            fi
        fi
    fi
done

if [ ${YesFilesDidChange} -eq 0 ]; then
    echo "No differences found.✅"
else
    while read -r -t 1; do read -r -t 1; done
    read -p "⚠️⚠️⚠️ -- Ok to Copy files from ${SRC_FLDR} -to-> ${DEST_FLDR}? (y/n) >>" ANS
    while read -r -t 1; do read -r -t 1; done
    read -p "⚠️⚠️⚠️ -- (AGAIN a 2nd-time) Ok to Copy files from ${SRC_FLDR} -to-> ${DEST_FLDR}? (y/n) >>" ANS
    echo ''; echo ''
    if [ "${ANS}" == "y" ]; then
        echo \
        "tar -C ${SRC_FLDR} -c  ${PipelineFiles[@]} | tar -C ${DEST_FLDR} -xv"
    else
        echo "No files copied !!!"
    fi
    echo ''; echo ''
fi

popd

# EoInfo
