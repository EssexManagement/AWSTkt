#!/bin/bash

### This script will create a TAR file, if `TarCmd` (a.k.a. CLI-arg #1) is the string "True" (initial upper-case letter)

### If any error in any commands, exit
set -e

if [ $# != 5 ]; then
    echo "Usage: $0 <Tier> <TarCmd> <subProjFolderPath>   <whether2UseAdvancedCaching> <CodePipelineS3BktName>"
    exit 1
fi

### ----------- define CONSTANTS -----------

Tier="$1"
TarCmd="$2"
subProjFolderPath="$3"
whether2UseAdvancedCaching="$4"
CodePipelineS3BktName="$5"

echo "Within script $0 .. .."
echo "Tier = '${Tier}'"
echo "TarCmd = '${TarCmd}'"
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
Fldrs2bArchivedBeforeCaching=(
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

if [ "${TarCmd}" != "create-tar" ] && [ "${TarCmd}" != "un-tar" ]; then
    echo "ERROR: 1st CLI-arg must be either 'create-tar' or 'un-tar'"
    exit 1
fi
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
        RETCODE=1
    else
        echo "checkIfS3ObjectExists(): s3://${CodePipelineS3BktName}/${FullS3ObjectKey} does NOT⚠️ exist"
        RETCODE=0
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

uploadAndTagNewS3Obj() {
    myFilePath="$1"
    CodePipelineS3BktName="$2"
    if [ "${CodePipelineS3BktName}" == "None" ] || [ "${CodePipelineS3BktName}" == "undefined" ]; then
        echo "uploadAndTagNewS3Obj(): CodePipelineS3BktName = '${CodePipelineS3BktName}' .. so, --NOT-- uploading to it.⚠️"
        return 0
    fi

    FullS3ObjectKey="${InitialS3Prefix}/${myFilePath}"
    echo "uploadAndTagNewS3Obj(): FullS3ObjectKey = '${FullS3ObjectKey}'"
    FullS3ObjectKey=$( echo $FullS3ObjectKey | sed -e 's|\.\.*/||g' | sed -e 's|///*|/|g' )
    echo "uploadAndTagNewS3Obj(): FullS3ObjectKey (Final) = '${FullS3ObjectKey}'"

    ### Upload and then Tag the s3-object.
    aws s3 cp --no-progress ${myFilePath} s3://${CodePipelineS3BktName}/${FullS3ObjectKey} ;

    TIMESTAMP=$(date +%s)
    echo "Tagging S3-object w/ TIMESTAMP = '${TIMESTAMP}'"
    set +e
    aws s3api put-object-tagging \
        --bucket "${CodePipelineS3BktName}" \
        --key "${FullS3ObjectKey}" \
        --tagging "TagSet=[{Key=CreatedBy-DevOps-Pipeline,Value=${TIMESTAMP}}]" \
        ${AWSPROFILEREGION[@]}
    if [ $? -ne 0 ]; then
        set -e
        echo "uploadAndTagNewS3Obj(): Error setting tag on s3://${CodePipelineS3BktName}/${FullS3ObjectKey}"
        exit 57
    fi
    set -e
    return 0
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

### -------- create tarfile or untar (for the cached-folder within CodeBuild) -----------

for ddd in ${Fldrs2bArchivedBeforeCaching[@]}; do
    set -e
    echo "------------ ddd = '${ddd}' --------------"
    if [ "${ddd:0:1}" == "/" ]; then
    ### if value of "ddd" starts with a '/' character
        myTARfilePath="${ddd}.tar"
        pathStartsWithSlash="true"
    else ### Example: ${HOME}/.local/share/virtualenvs  in the list of values of "Fldrs2bArchivedBeforeCaching"
        myTARfilePath="./${CodeBuild_FileCacheFldr}/${ddd}.tar"
        pathStartsWithSlash="false"
    fi
    echo "myTARfilePath = '${myTARfilePath}'"
    ### remove the leading "./" if it exists (up to two occurences)
    myTARfilePath=$( echo $myTARfilePath | sed -e 's|\.\.*/||g' | sed -e 's|\.\.*/||g' )
    echo "myTARfilePath (FINAL) = '${myTARfilePath}'"
    # if [ "${TarCmd}" == "un-tar" ] && [ ! -f "${myTARfilePath}" ] && [ ! -d "${myTARfilePath}" ]; then
    #     echo "${TarCmd} : File/Dir NOT found ${myTARfilePath} .. so, SKIPPING .."
    #     continue;
    # fi
    date
    if [ -L "${myTARfilePath}" ]; then
        realTarfPath=$( readlink "${myTARfilePath}" )
        echo "realTarfPath = '${realTarfPath}'"
        FullS3ObjectKey="${InitialS3Prefix}/${realTarfPath}"
    else
        FullS3ObjectKey="${InitialS3Prefix}/${myTARfilePath}"
    fi
    echo "41: FullS3ObjectKey = '${FullS3ObjectKey}'"
    FullS3ObjectKey=$( echo $FullS3ObjectKey | sed -e 's|\.\.*/||g' | sed -e 's|///*|/|g' )
    echo "42: FullS3ObjectKey (Final) = '${FullS3ObjectKey}'"

    if [ "${TarCmd}" == "create-tar" ]; then

        if [[ ! -d "${ddd}" && ! -f "${ddd}" ]]; then
            echo "create-tar: File/Dir NOT found ${ddd} .. so, SKIPPING .."
            continue
        fi

        if [ "${realTarfPath}x" == "x" ]; then
            ### Symbolic-Link does -NOT- exist.  But, the file "ddd" itself may be a REAL but simple file
            (
                ### If NOT already inside ${subProjFolderPath}, then cd into it.
                ### THat is .. if FULL-path of current-workingdir does NOT end with "${subProjFolderPath}", then cd into "${subProjFolderPath}"
                if [ ! $( pwd | grep "${subFldr}\$" ) ]; then
                    pwd
                    cd ${subProjFolderPath}/  ### in a new SHELL, change to where the cache-able folders/files are to be.
                fi
                # set +e
                # isFileTooOld ${myTARfilePath} ${CodePipelineS3BktName}
                # if [ $? -eq 1 ]; then
                #     set -e
                    if [ "${pathStartsWithSlash}" == "true" ]; then
                        (   cd /     ### go to '/' root path of machine (in a new shell)
                            pwd; echo "Updating LOCAL-filepath: ${myTARfilePath} .. ";
                            echo \
                            tar -cf ${myTARfilePath} ${ddd} ;
                            tar -cf ${myTARfilePath} ${ddd} ;
                            uploadAndTagNewS3Obj ${myTARfilePath} ${CodePipelineS3BktName} ;
                        )
                    else
                            pwd; echo "Updating LOCAL-filepath: ${PWD}/${myTARfilePath} .. ";
                            echo \
                            tar -cf ${myTARfilePath} ./${ddd} ;
                            tar -cf ${myTARfilePath} ./${ddd} ;
                            uploadAndTagNewS3Obj ${myTARfilePath} ${CodePipelineS3BktName} ;
                    fi
                # fi
                # set -e
            )
        else
            ### So, SYMLINK-file exists, .. write to the exact-location where the SYMLINK is.
            (
                ### If NOT already inside ${subProjFolderPath}, then cd into it.
                ### THat is .. if FULL-path of current-workingdir does NOT end with "${subProjFolderPath}", then cd into "${subProjFolderPath}"
                if [ ! $( pwd | grep "${subFldr}\$" ) ]; then
                    pwd
                    cd ${subProjFolderPath}/  ### in a new SHELL, change to where the cache-able folders/files are to be.
                fi
                # set +e
                # isFileTooOld ${myTARfilePath} ${CodePipelineS3BktName}
                # if [ $? -eq 1 ]; then
                #     set -e
                    pwd; echo "Updating LOCAL-filepath: ${PWD}/${myTARfilePath} a.k.a. ${realTarfPath} .. ";
                    tar -cf "${realTarfPath}" "./${ddd}" ;
                    uploadAndTagNewS3Obj ${myTARfilePath} ${CodePipelineS3BktName} ;
                # fi
                # set -e
            )
        fi

    else  ### un-tar / extract-from-archive (after downloading cached-file from S3-bucket)

        echo "43: untarring cached-files .."
        set +e
        checkIfS3ObjectExists "${FullS3ObjectKey}" "${CodePipelineS3BktName}"
        if [ $? -eq 0 ]; then
            set -e
            echo "uploadAndTagNewS3Obj(): Skipping s3-DOWNLOAD, as s3-object does NOT exist."
            continue ### next item in `Fldrs2bArchivedBeforeCaching`
        fi
        set -e

        if [ "${realTarfPath}x" == "x" ]; then

            ### Symbolic-Link does -NOT- exist.  But, the file "ddd" itself may be a REAL but simple file

            (
                ### If NOT already inside ${subProjFolderPath}, then cd into it.
                ### THat is .. if FULL-path of current-workingdir does NOT end with "${subProjFolderPath}", then cd into "${subProjFolderPath}"
                if [ ! $( pwd | grep "${subFldr}\$" ) ]; then
                    pwd
                    cd ${subProjFolderPath}/  ### in a new SHELL, change to where the cache-able folders/files are to be.
                fi
                echo \
                aws s3 cp --no-progress s3://${CodePipelineS3BktName}/${FullS3ObjectKey} ${myTARfilePath} ;   ### Download
                aws s3 cp --no-progress s3://${CodePipelineS3BktName}/${FullS3ObjectKey} ${myTARfilePath} ;   ### Download
                if [ "${pathStartsWithSlash}" == "true" ]; then
                    (   cd /     ### go to '/' root path of machine (in a new shell)
                        tar -xf "${myTARfilePath}" ; ### will create /${ddd}/.....
                        ls -lad ${ddd} || true
                    )
                else
                    tar -xf "${myTARfilePath}" ; ### will create ${subProjFolderPath}/${ddd}/.....
                    ls -lad ${ddd} || true
                fi
            )
        else
            ### use `realTarfPath` instead of `myTARfilePath`
            (
                ### If NOT already inside ${subProjFolderPath}, then cd into it.
                ### THat is .. if FULL-path of current-workingdir does NOT end with "${subProjFolderPath}", then cd into "${subProjFolderPath}"
                if [ ! $( pwd | grep "${subFldr}\$" ) ]; then
                    pwd
                    cd ${subProjFolderPath}/  ### in a new SHELL, change to where the cache-able folders/files are to be.
                fi
                echo \
                aws s3 cp --no-progress s3://${CodePipelineS3BktName}/${FullS3ObjectKey} ${realTarfPath} ;   ### Download to Symlink location
                aws s3 cp --no-progress s3://${CodePipelineS3BktName}/${FullS3ObjectKey} ${realTarfPath} ;   ### Download to Symlink location
                if [ "${pathStartsWithSlash}" == "true" ]; then
                    (   cd /     ### go to '/' root path of machine (in a new shell)
                        tar -xf "${realTarfPath}" ; ### will create ${subProjFolderPath}/${ddd}/
                        ls -lad ${ddd} || true
                    )
                else
                    tar -xf "${realTarfPath}" ; ### will create ${subProjFolderPath}/${ddd}/
                    ls -lad ${ddd} || true
                fi
            )
        fi
    fi
    if [ "${pathStartsWithSlash}" == "true" ]; then
        echo \
        ls -lad ${ddd}
        ls -lad ${ddd} || true
    else
        echo \
        ls -lad ${PWD}/${ddd}
        ls -lad ${PWD}/${ddd} || true
    fi
    date
done

# if [ "$Debug" == "true" ]; then
    printDetailsOnFolders
# fi
printf '%.0s_' {1..40}; echo ''

exit 0

### EoF
