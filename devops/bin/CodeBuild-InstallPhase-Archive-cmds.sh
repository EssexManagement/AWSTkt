#!/bin/bash -f

### This script will create a TAR file, if `TarCmd` (a.k.a. CLI-arg #1) is the string "True" (initial upper-case letter)

### ----------- define CONSTANTS -----------

TarCmd="$1"
subProjFolderPath="$2"
whether2UseAdvancedCaching="$3"

CodeBuild_FileCacheFldr="tmp/CodeBuild_FileCacheFldr"
    ### !! ATTENTION !! This ABOVE variable --MUST-- remain identical to the Python-variable inside `common/cdk/constants_cdk.py`
    ### CodeBuild only caches Folders. So, files-to-be-cached have to be put into a folder!
Fldrs2bArchivedBeforeCaching=(  .venv   node_modules )
    ### These 2 folders will be converted into ARCHIVE-FILES (tar-files to be specific).  These ARCHIVE-files will theb be cached as per variable above.

### ----------- Validate CLI-args -----------

if [ "${TarCmd}" != "create-tar" ] && [ "${TarCmd}" != "un-tar" ]; then
    echo "ERROR: 1st CLI-arg must be either 'create-tar' or 'un-tar'"
    exit 1
fi
if [ "${whether2UseAdvancedCaching}" != "True" ] && [ "${whether2UseAdvancedCaching}" != "False" ]; then
    echo "ERROR: 3rd CLI-arg must be either 'True' or 'False'"
    exit 1
fi

echo "Within script $0 .. .."
echo "  TarCmd = '${TarCmd}'"
echo "  subProjFolderPath = '${subProjFolderPath}'"
echo "  whether2UseAdvancedCaching = '${whether2UseAdvancedCaching}'"

if [ "${whether2UseAdvancedCaching}" == "False" ]; then
    echo "--NO-- advanced-caching (for node_modules and python's-venv)"
    exit 0
fi

### ----------- DEBUG-output -----------

pwd
# ls -la
printf '%.0s^' {1..40}; echo ''
ls -la ./tmp/.
printf '%.0s.' {1..40}; echo ''
mkdir -p ./${CodeBuild_FileCacheFldr}/   ### We need this, else .. (For the 1st time) a lot of code below will fail to create/read files under this.
ls -la ./${CodeBuild_FileCacheFldr}/
printf '%.0s_' {1..40}; echo ''

realPath=$( readlink ./${CodeBuild_FileCacheFldr}/node_modules.tar )
echo "(Sanity-Check/SAMPLE) realPath='${realPath}'"
if [ "${realPath}x" == "x" ]; then
    echo "Sanity-Check: the readlink command returned empty.  So, this must be a plain-file"
    ls -la ./${CodeBuild_FileCacheFldr}/node_modules.tar
else
    ls -la "${realPath}"
fi

### ----------- utility/tools -----------

### This function's return-values: '1' == Logical-True (a.k.a. Too-old), while '0' is Logical-False.
isFileTooOld() {
    f="$1"
    echo "checking if ${f} is more than 24 old .."
    # if ${f} does NOT exist, return 1/True (so that it will be re-created/updated)
    [ ! -f "${f}" ] && return 1

    file_age=$(find "${f}" -maxdepth 0 -mtime +1);
    echo "file_age='${file_age}'"
    if [ "${file_age}" == "${f}" ]; then
        echo "isFileTooOld(): ${f} is -OLDER- than 24 hours!";
        return 1
    else
        echo "isFileTooOld(): ${f} is fresh ( LESS-than 24h old)";
        return 0
    fi
}

### ------- create tarfile or untar (for the cached-folder within CodeBuild) -----------

for ddd in ${Fldrs2bArchivedBeforeCaching[@]}; do
    echo "------------ ddd = '${ddd}' --------------"
    realPath=$( readlink ./${CodeBuild_FileCacheFldr}/${ddd}.tar )
    echo "realPath='${realPath}'"
    date
    myFilePath="./${CodeBuild_FileCacheFldr}/${ddd}.tar"

    if [ "${TarCmd}" == "create-tar" ]; then
        if [ "${realPath}x" == "x" ]; then
            ### Symbolic-Link does -NOT- exist.  But, the file "ddd" itself may be a REAL but simple file
            (   cd ${subProjFolderPath}/ ;
                isFileTooOld ${myFilePath}
                if [ $? -eq 1 ]; then
                    pwd; echo "Updating ${myFilePath} ..";
                    tar -cf ${myFilePath} ./${ddd}
                fi
            )
        else
            ### file exists, so .. write to the exact-location where the SYMLINK is.
            (   cd ${subProjFolderPath}/ ;
                isFileTooOld ${myFilePath}
                if [ $? -eq 1 ]; then
                    pwd; echo "Updating ${myFilePath} ..";
                    tar -cf $( readlink "${myFilePath}" ) ./${ddd}
                fi
            )
        fi

    else  ### un-tar / extract-from-archive

        if [ "${realPath}x" == "x" ]; then
            ### Symbolic-Link does -NOT- exist.  But, the file "ddd" itself may be a REAL but simple file
            ( cd ${subProjFolderPath}/ ; tar -xf "${myFilePath}" ) ### will create ${subProjFolderPath}/${ddd}/
        else
            ( cd ${subProjFolderPath}/ ; tar -xf $( readlink "${myFilePath}" ) ) ### will create ${subProjFolderPath}/${ddd}/
        fi
    fi
    date
done

printf '%.0s.' {1..40}; echo ''
pwd
ls -la ./${CodeBuild_FileCacheFldr}/
printf '%.0s_' {1..40}; echo ''

### EoF
