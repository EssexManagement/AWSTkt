#!/bin/bash

set -e  ### Exit immediately if a command exits with non-zero status

### ----------- define CONSTANTS -----------

CodeBuild_FileCacheFldr="tmp/CodeBuild_FileCacheFldr"
    ### !! ATTENTION !! This ABOVE variable --MUST-- remain identical to the Python-variable inside `common/cdk/constants_cdk.py`
    ### CodeBuild only caches Folders. So, files-to-be-cached have to be put into a folder!

### ----------- Derived -----------

### If "Debug" is -NOT- defined as an environment variable, set to a default value
if [ -z "${Debug+x}" ]; then
    Debug="false"   ### | "true"
fi

### ----------- Validate CLI-args -----------

### ----------- DEBUG-output -----------

if [ "$Debug" == "true" ]; then
    pwd
    ls -la
    printf '%.0s^' {1..40}; echo ''

    ls -lad .venv/* || true
    ls -lad .venv/bin/* || true
    ls -la .venv/lib/python[0-9].[0-9]*/site-packages/ || true
    printf '%.0s.' {1..40}; echo ''

    ls -la ${HOME}/.local/share/virtualenvs || true
    printf '%.0s.' {1..40}; echo ''

        # ls -la ./tmp/.
        # printf '%.0s.' {1..40}; echo ''
    ls -lad ./${CodeBuild_FileCacheFldr}/* || true
    printf '%.0s,' {1..40}; echo ''
fi

### ----------- utility/tools -----------

### ----------- the main work -----------

if [ -f requirements.txt ]; then
    if [ -d .venv ]; then
        echo '.venv already exists.✅  So, we will NOT create a new one.';
    else
        echo -n '.venv MISSING !! ⚠️⚠️⚠️  Will -CREATE- one from scratch .. .. ';
        mkdir -p .venv;
        cd .venv;
        python -m venv .;
        cd ..;
        echo 'Done!'
    fi

    echo "NEXT: activating the .venv (sourcing '.venv/bin/activate') .. .."

    .   .venv/bin/activate;
    pip install -r requirements.txt;

elif [ -f Pipfile.lock ]; then
    echo "Now, running PIPENV commands (install and sync) .. .."

    pip install pipenv --user;
    pipenv sync --dev;

else
    echo 'Both requirements.txt and Pipfile.lock are MISSING';
    exit 111;
fi;

### Sanity check the project's python setup
printf '%.0s.' {1..40}; echo ''
echo "Sanity check using npx-cdk-cmd re: project's python setup .."

if [ -f requirements.txt ]; then
    npx cdk --version;
elif [ -f Pipfile.lock ]; then
    pipenv run npx cdk --version;
else
    echo 'Both requirements.txt and Pipfile.lock are MISSING';
    exit 111;
fi

if [ "$Debug" == "true" ]; then
    printf '%.0s_' {1..40}; echo ''
    echo $PATH
    printf '%.0s_' {1..40}; echo ''

    which python
    which python3
    which pip
    which pip3
    pip list | grep aws.cdk
    # pwd
fi

### EoF
