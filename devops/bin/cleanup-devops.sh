#!/bin/bash -f

echo "Usage: $0 [--include-Pipfile.lock]"
sleep 5

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

RootDir_devopsPipelineCode="$( dirname "${SCRIPT_FOLDER}" )" ### Grand-Parent-folder of this script.
echo "RootDir_devopsPipelineCode = '${RootDir_devopsPipelineCode}'"


###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

### Sanity Checks

# Bash-flag to appropriately set `glob` (allow '*' to work)
set +o noglob

###---------------------------------------------------------------

### Do section

# echo ''; printf '%.0s=' {1..160}; echo ''; printf '%.0s=' {1..160}; echo ''; echo '';

\rm -rf ~/.cache/ ~/.local/ ~/.venv/ ~/node_modules ${RootDir_devopsPipelineCode}/node_modules

# Loop over each subfolder of RootDir_devopsPipelineCode and if subfolder does Not have a "Pipfile" skip it
for subfolder in "${RootDir_devopsPipelineCode}"/*; do
    if [ ! -d "${subfolder}" ]; then
        echo -n "skipping NON-dir '$( basename ${subfolder} )' ..  "
        continue
    fi

    # echo "Pipfile path for subfolder = '${subfolder}/Pipfile'"
    # ls -la "${subfolder}/Pipfile"
    if [ ! -f "${subfolder}/package.json" ] && [ ! -f "${subfolder}/Pipfile" ]; then
        echo -n "skipping '$( basename ${subfolder} )' as it does --NOT-- have package.json NOT Pipfile.lock ..  "
        continue
    fi

    echo ''; echo "👉🏾👉🏾👉🏾👉🏾👉🏾👉🏾👉🏾 ${subfolder} contains a devops-utility !"
    cd "${subfolder}"

    \rm -rf .venv/ .cache/  .local/  __pycache__/  cdk.out/  dist/ build/   node_modules/  cdk.out/
    \rm -rf *.egg-info *.dist-info .pytest_cache .mypy_cache .tox .coverage .coverage.* .hypothesis

    while read -r -t 1; do read -r -t 1; done ### "read -r -t0" will return true if stdin-stream is NOT empty
    read -p "Re-create the 'package-LOCK.json' ? [y/N] >> " ANSWER
    if [[ $ANSWER =~ ^[Yy]$ ]]; then
        npm i --include-dev
    fi

    if [ ! -z "${DELETE_Pipfile_LOCK+x}" ]; then
        \rm -f Pipfile.lock
        \rm -f requirements.txt
        find "${subfolder}" -name '__pycache__' -depth -5 -exec rm -rf {} \;

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
