#!/bin/bash -f

### This script will create a TAR file, if `TarCmd` (a.k.a. CLI-arg #1) is the string "True" (initial upper-case letter)

### ----------- define CONSTANTS -----------

CodeBuild_FileCacheFldr="tmp/CodeBuild_FileCacheFldr"
    ### !! ATTENTION !! This ABOVE variable --MUST-- remain identical to the Python-variable inside `common/cdk/constants_cdk.py`
    ### CodeBuild only caches Folders. So, files-to-be-cached have to be put into a folder!

CachedFldrs2bCleanedPeriodically=(
    ./${CodeBuild_FileCacheFldr}/
    .venv/
    node_modules/
    ~/.local/share/virtualenvs/
    .pipenv/
)

### ----------- Validate CLI-args -----------
## Not applicable for this script.

### ----------- Sanity-Checks -----------

pwd
# ls -la
printf '%.0s^' {1..40};
ls -la tmp/.
printf '%.0s.' {1..40};
mkdir -p ${CodeBuild_FileCacheFldr}/   ### We need this, else .. (For the 1st time) a lot of code below will fail to create/read files under this.
ls -la ${CodeBuild_FileCacheFldr}/
printf '%.0s_' {1..40};

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

### -------- Does CodeBuild's folders that are Cached, .. do they need cleanup?

### NOTE: cache-cleanup -MUST- be done before doing any builds/cdk-synth/cdk-deploy within CodeBuild.
### FYI --- If cache is corrupted use AWS-CLI as: `aws codebuild invalidate-project-cache --project-name "${CBProjectName}"`
echo 'Checking cache age...';

for ddd in   ${CachedFldrs2bCleanedPeriodically[@]}; do
    echo "------------ ddd = '${ddd}' --------------"
    if [ -d "$ddd" ]; then
        isFileTooOld "${ddd}"
        if [ $? != 0 ]; then
            echo "Cache directory $ddd is -OLDER- than 24 hours, clearing...";
            \rm -rf "$ddd";
        else
            echo "Cache directory $ddd is fresh (less than 24 hours old)";
        fi
    else
        # if "$ddd" is a file, check if it more than 24 old
        isFileTooOld "${ddd}"
        if [ $? != 0 ]; then
            echo "Cache file $ddd is -OLDER- than 24 hours, clearing...";
            \rm -rf "$ddd";
        else
            echo "Cache file $ddd is fresh (less than 24 hours old)";
        fi
    fi
done


### EoF
