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

# Loop over each subfolder of RootDir_LambdaLayers and if subfolder does Not have a "Pipfile" skip it
for subfolder in "${RootDir_LambdaLayers}"/*; do
    if [ ! -d "${subfolder}" ]; then
        echo -n "skipping NON-dir '$( basename ${subfolder} )' ..  "
        continue
    fi

    # echo "Pipfile path for subfolder = '${subfolder}/Pipfile'"
    # ls -la "${subfolder}/Pipfile"
    if [ ! -f "${subfolder}/Pipfile" ]; then
        continue
    fi

    echo ''; echo "👉🏾👉🏾👉🏾👉🏾👉🏾👉🏾👉🏾 ${subfolder} is a 𝜆-layer !"
    cd "${subfolder}"
    if [ ! -z "${DELETE_Pipfile_LOCK+x}" ]; then
        \rm -f Pipfile.lock
        \rm -f requirements.txt
    fi

    \rm -rf .venv/ .cache/  .local/  __pycache__/  cdk.out/  dist/ build/
    \rm -rf *.egg-info *.dist-info .pytest_cache .mypy_cache .tox .coverage .coverage.* .hypothesis
    cd - > /dev/null
done

### EoScript
