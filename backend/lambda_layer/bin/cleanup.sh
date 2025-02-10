#!/bin/bash -f

echo "Usage: $0 [--include-Pipfile.lock]"

if [ "$1" == "--include-Pipfile.lock" ]; then
    shift
    DELETE_Pipfile_LOCK="y"
else
    unset DELETE_Pipfile_LOCK
fi

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

### Constants

PYTHON_VERSION="3.12"

###---------------------------------------------------------------

### Derived Variables

SCRIPT_FOLDER="$(dirname ${BASH_SOURCE[0]})"
SCRIPT_NAME="$(basename ${BASH_SOURCE[0]})"
CWD="$(pwd)"

# .  "${SCRIPT_FOLDER}/settings.sh"

# if [ ! -z "${PROJECT_NAME+x}" ]; then
#     KNOWN_PROJ_ITEMS=~/LocalDevelopment/etc/cfn-lint-ignore_${PROJECT_NAME}.txt
#     echo "Will compare with KNOWN warnings stored in ${KNOWN_PROJ_ITEMS}"
# fi

RootDir_LambdaLayers="$( dirname "${SCRIPT_FOLDER}" )" ### Grand-Parent-folder of this script.
echo "RootDir_LambdaLayers = '${RootDir_LambdaLayers}'"


###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

### Sanity Checks

# Bash-flag to appropriately set `glob` (allow '*' to work)
set +o noglob

###---------------------------------------------------------------

### Do section

# echo ''; printf '%.0s=' {1..160}; echo ''; printf '%.0s=' {1..160}; echo ''; echo '';

\rm -rf ~/.cache/ ~/.local/ ~/.venv/

# Loop over each subfolder of RootDir_LambdaLayers and if subfolder does Not have a "Pipfile" skip it
for subfolder in "${RootDir_LambdaLayers}"/*; do
    if [ ! -d "${subfolder}" ]; then
        echo -n "skipping NON-dir '$( basename ${subfolder} )' ..  "
        continue
    fi

    # echo "Pipfile path for subfolder = '${subfolder}/Pipfile'"
    # ls -la "${subfolder}/Pipfile"
    if [ ! -f "${subfolder}/Pipfile" ] && [ ! -f "${subfolder}/requirements.in" ]; then
        echo -n "skipping '${subfolder}' as it is NOT a 𝜆-layer ..  "
        continue
    fi

    echo ''; echo "👉🏾👉🏾👉🏾👉🏾👉🏾👉🏾👉🏾 ${subfolder} is a 𝜆-layer !"
    cd "${subfolder}"

    \rm -rf .venv/ .cache/  .local/  __pycache__/  cdk.out/  dist/ build/
    \rm -rf *.egg-info *.dist-info .pytest_cache .mypy_cache .tox .coverage .coverage.* .hypothesis

    if [ ! -z "${DELETE_Pipfile_LOCK+x}" ]; then
        \rm -f Pipfile.lock
        \rm -f requirements.txt
        while read -r -t 1; do read -r -t 1; done ### "read -r -t0" will return true if stdin-stream is NOT empty
        read -p "Re-create the 'Pipfile.lock' ? [y/N] >> " ANSWER
        if [[ $ANSWER =~ ^[Yy]$ ]]; then
            pip install pipenv > /dev/null
            echo \
            pipenv lock --dev --clear --python ${PYTHON_VERSION}
            pipenv lock --dev --clear --python ${PYTHON_VERSION}
        fi
    fi

    cd - > /dev/null

done

### EoScript
