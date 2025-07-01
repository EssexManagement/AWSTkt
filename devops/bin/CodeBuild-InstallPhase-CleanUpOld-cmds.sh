#!/bin/bash

### This script will delete OLD tarfiles/folders (whether in S3 or locally within CodeBuild-instance)
### These are folders/files defined in ${CachedFldrs2bCleanedPeriodically} (see contants below)

### If any error in any commands, exit
set -e

if [ $# != 4 ]; then
    echo "Usage: $0 <Tier> <subProjFolderPath>   <whether2UseAdvancedCaching>  <CodePipelineS3BktName>"
    exit 1
fi

### ----------- define CONSTANTS -----------

Tier="$1"
subProjFolderPath="$2"
whether2UseAdvancedCaching="$3"
CodePipelineS3BktName="$4"

echo "Within script $0 .. .."
echo "Tier = '${Tier}'"
echo "subProjFolderPath = '${subProjFolderPath}'"
echo "whether2UseAdvancedCaching = '${whether2UseAdvancedCaching}'"
echo "CodePipelineS3BktName = '${CodePipelineS3BktName}'"


MaxCacheAge="48" ### hours (just about 2 days)

ENTERPRISE_NAME="NIH-NCI"
CDKAppName="CTF"
ComponentName="backend"

CodeBuild_FileCacheFldr="." ### Project-root !!
# CodeBuild_FileCacheFldr="tmp/CodeBuild_FileCacheFldr"
    ### !! ATTENTION !! This ABOVE variable --MUST-- remain identical to the Python-variable inside `common/cdk/constants_cdk.py`
    ### CodeBuild only caches Folders. So, files-to-be-cached have to be put into a folder!

CachedFldrs2bCleanedPeriodically=(
    ### WARNING: NO ending slashes!!
    ### These folders below will be converted into ARCHIVE-FILES (tar-files to be specific).  These ARCHIVE-files will theb be cached as per variable above.
    .venv
    node_modules
    .pipenv
    .pip-cache.venv ### replaces ~/.cache/pip -- `XDG_CACHE_HOME`  https://pip.pypa.io/en/stable/topics/caching/
    ${HOME}/.local/share/virtualenvs
    # ./${CodeBuild_FileCacheFldr} ???
)

### ----------- Validate CLI-args -----------

if [ "${whether2UseAdvancedCaching}" != "True" ] && [ "${whether2UseAdvancedCaching}" != "False" ]; then
    echo "ERROR: 3rd CLI-arg must be either 'True' or 'False'"
    exit 1
fi

if [ "${whether2UseAdvancedCaching}" == "False" ]; then
    echo "--NO-- advanced-caching (for node_modules and python's-venv)"
    exit 0
fi

### ----------- Derived -----------

### If "Debug" is -NOT- defined as an environment variable, set to a default value
if [ -z "${Debug+x}" ]; then
    Debug="false"   ### | "true"
fi
Debug="true"

if [ ${subProjFolderPath} == "." ]; then
    InitialS3Prefix="${ENTERPRISE_NAME}/${CDKAppName}/${ComponentName}/${Tier}"
else
    InitialS3Prefix="${ENTERPRISE_NAME}/${CDKAppName}/${ComponentName}/${Tier}/${subProjFolderPath}"
fi
echo "InitialS3Prefix = '${InitialS3Prefix}'"

if [ ${OSTYPE} == "darwin24" ]; then
    AWSPROFILEREGION=( --profile "${AWSPROFILE}" --region "${AWSREGION}" )
else
    AWSPROFILEREGION=""
fi
echo "AWSPROFILEREGION = '${AWSPROFILEREGION[@]}'"

### ----------- utility/tools -----------

printDetailsOnFolders() {
    printf '%.0s.' {1..40}; echo ''
    echo ".. printing details on KEY-folders .."
    pwd
    ls -lad ./${CodeBuild_FileCacheFldr}/*.tar || true
    printf '%.0s.' {1..40}; echo ''
    ls -lad ${HOME}/.local/share/virtualenvs* || true
    printf '%.0s.' {1..40}; echo ''
    ls -lad .venv/lib/python3.12/site-packages/aws?cdk* || true
    printf '%.0s.' {1..40}; echo ''
    ls -lad .pip-cache.venv* || true
}

### ----------

### Very simple function. Use AWS-SDK to check if the s3-object exists.
checkIfS3ObjectExists() {
    FullS3ObjectKey="$1"
    CodePipelineS3BktName="$2"

    set +e
    aws s3api head-object \
        --bucket "${CodePipelineS3BktName}" \
        --key "${FullS3ObjectKey}" \
        ${AWSPROFILEREGION[@]} \
        > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "checkIfS3ObjectExists(): s3://${CodePipelineS3BktName}/${FullS3ObjectKey} exists"
        RETCODE=0
    else
        echo "checkIfS3ObjectExists(): s3://${CodePipelineS3BktName}/${FullS3ObjectKey} does NOT⚠️ exist"
        RETCODE=1
    fi
    return ${RETCODE}
}

### ----------

### For given --LOCAL-- path to a file, check if the CORRESPONDING S3-object exists.
checkIfCorrespondingS3ObjectExists() {
    myFilePath="$1"
    CodePipelineS3BktName="$2"
    if [ "${CodePipelineS3BktName}" == "None" ] || [ "${CodePipelineS3BktName}" == "undefined" ]; then
        echo "checkIfCorrespondingS3ObjectExists(): CodePipelineS3BktName = '${CodePipelineS3BktName}' .. so, --NOT-- checking if s3-object exists.⚠️"
        return 0
    fi
    echo "checkIfCorrespondingS3ObjectExists(): CodePipelineS3BktName = '${CodePipelineS3BktName}' .. so, checking if s3-object exists.⚠️"

    FullS3ObjectKey="${InitialS3Prefix}/${myFilePath}"
    echo "checkIfCorrespondingS3ObjectExists(): FullS3ObjectKey = '${FullS3ObjectKey}'"
    FullS3ObjectKey=$( echo $FullS3ObjectKey | sed -e 's|+/||g' | sed -e 's|///*||g' )
    echo "checkIfCorrespondingS3ObjectExists(): FullS3ObjectKey (Final) = '${FullS3ObjectKey}'"

    set +e
    checkIfS3ObjectExists "${FullS3ObjectKey}" "$2"
    return $?
}

### ----------

### Very simple function. Use AWS-SDK to check if the s3-object exists.
deleteOldS3Object() {
    FullS3ObjectKey="$1"
    CodePipelineS3BktName="$2"

    echo "deleteOldS3Object(): s3://${CodePipelineS3BktName}/${FullS3ObjectKey} .. .."
    set +e
    aws s3api delete-object \
        --bucket "${CodePipelineS3BktName}" \
        --key "${FullS3ObjectKey}" \
        ${AWSPROFILEREGION[@]} \
        > /dev/null 2>&1
    RETCODE=$?
    set -e
    echo "deleteOldS3Object(): s3://${CodePipelineS3BktName}/${FullS3ObjectKey} cmd-return-code: '${RETCODE}'"
    return ${RETCODE}
}

### ----------

### This function's return-values:
###     '1' == Logical-True (a.k.a. TOOOOO-OLD file)
###     '0' == Logical-False (recent/new file or NON-existent file).
isFileTooOld() {
    myFilePath="$1"
    CodePipelineS3BktName="$2"
    if [ "${CodePipelineS3BktName}" == "None" ] || [ "${CodePipelineS3BktName}" == "undefined" ]; then
        return 0
    fi
    echo "checking if '${myFilePath}' is more than '${MaxCacheAge}' hrs old (Bkt = ${CodePipelineS3BktName}).."

    FullS3ObjectKey="${InitialS3Prefix}/${myFilePath}"
    echo "isFileTooOld(): FullS3ObjectKey = '${FullS3ObjectKey}'"
    FullS3ObjectKey=$( echo $FullS3ObjectKey | sed -e 's|\.\.*/||g' | sed -e 's|///*|/|g' )
    echo "isFileTooOld(): FullS3ObjectKey (Final) = '${FullS3ObjectKey}'"

    [ ! -f "${myFilePath}" ] && [ ! -d "${myFilePath}" ] && return 1 ### TOOOOO-OLD file or NON-existent file
    # if ${myFilePath} does NOT exist --LOCALLY--, return 1/True (so that it will cause code to create it again)

    ### makes NO sense to check date of LOCAL-file, as it was DOWNLOADED by aws-cli a few minutes ago.
    ### The right way to find out when it was created .. is to run AWS-CLI on the s3-object(s)
    # ListOfCachedFiles=$(find "${myFilePath}" -maxdepth 0 -mtime +${MaxCacheAge});
    ### This "find" bash-cmd is given the FILE's path as arg#1.  So, its output is MAX 1 line of text!!!
    # echo "ListOfCachedFiles='${ListOfCachedFiles}'"
    # if [ "${ListOfCachedFiles}" == "${myFilePath}" ]; .. ..

    set +e
    checkIfS3ObjectExists "${FullS3ObjectKey}" "${CodePipelineS3BktName}"
    if [ $? -ne 0 ]; then
        set -e
        echo "isFileTooOld(): Skipping Get-Tags SDK-call, as s3-object does NOT exist."
        return 0 ### TOOOOO-OLD file or NON-existent file. This differs from the same bash-func in `InstallPhase-Archive-cmds.sh`
    fi

    set +e
    ResponseJson=$( aws s3api get-object-tagging \
        --bucket "${CodePipelineS3BktName}" \
        --key "${FullS3ObjectKey}" \
        ${AWSPROFILEREGION[@]}
    )
    if [ $? -ne 0 ]; then
        echo "isFileTooOld(): Error getting Object's-Tag at s3://${CodePipelineS3BktName}/${FullS3ObjectKey}"
        exit 2
    fi
    set -e
    echo "ResponseJson = ${ResponseJson}"
    FileTimeStamp=$( echo "${ResponseJson}" | jq -r '.TagSet[] | select(.Key=="CreatedBy-DevOps-Pipeline").Value' )
    echo "FileTimeStamp = '${FileTimeStamp}'"  ### This is # of secs since Epoch (generated by `date +%s` cli-cmd)
    NowTime=$(date +%s)
    RunTime=$(( NowTime - FileTimeStamp ))
    echo "RunTime = '${RunTime}'"
    AgeOfCachedFile=$(( RunTime / 3600 ))  ### Convert to # of hours
    echo "AgeOfCachedFile='${AgeOfCachedFile}'"
    if [ "${AgeOfCachedFile}" -gt ${MaxCacheAge}  ]; then
        echo "isFileTooOld(): ..../${myFilePath} is -OLDER- than ${MaxCacheAge} hours\!";
        return 1 ### TOOOOO-OLD file or NON-existent file
    else
        echo "isFileTooOld(): ..../${myFilePath} is fresh ( LESS-than ${MaxCacheAge} old)";
        return 0
    fi
}

### ----------- Sanity-Checks -----------

printf '%.0s^' {1..40}; echo ''
if [ "$Debug" == "true" ]; then
    printDetailsOnFolders
fi

pip cache dir
pip cache info

if [ ${CodeBuild_FileCacheFldr} != "." ]; then
    ### if it is NOT the project-root, then make sure the folder exists.
mkdir -p ./${CodeBuild_FileCacheFldr}/   ### We need this, else .. (For the 1st time) a lot of code below will fail to create/read files under this.
ls -la ./${CodeBuild_FileCacheFldr}/
printf '%.0s_' {1..40}; echo ''
fi

### -------- RE: CodeBuild's folders that are Cached, .. do they need cleanup? ------------

### NOTE: cache-cleanup -MUST- be done before doing any builds/cdk-synth/cdk-deploy within CodeBuild.
### FYI --- If cache is corrupted use AWS-CLI as: `aws codebuild invalidate-project-cache --project-name "${CBProjectName}"`
echo 'Checking cache age...';

for ddd in   ${CachedFldrs2bCleanedPeriodically[@]}; do
    set -e
    echo "------------ ddd = '${ddd}' --------------"
    set +e
    isFileTooOld ${ddd} ${CodePipelineS3BktName}
    if [ $? -eq 1 ]; then
        set -e
        \rm -rf "${ddd}"  ### remove the file/folder. No error if NON-existent

        FullS3ObjectKey="${InitialS3Prefix}/${myFilePath}"
        echo "$0 : FullS3ObjectKey = '${FullS3ObjectKey}'"
        FullS3ObjectKey=$( echo $FullS3ObjectKey | sed -e 's|+/||g' | sed -e 's|///*||g' )
        echo "$0 : FullS3ObjectKey (Final) = '${FullS3ObjectKey}'"

        set +e ### I do NOT care if the S3 object did NOT exist !
        deleteOldS3Object "${FullS3ObjectKey}" "${CodePipelineS3BktName}"
        set -e
    fi
    set -e
done

### EoF
