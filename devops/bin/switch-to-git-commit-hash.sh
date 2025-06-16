#!/bin/false

### !!!! ATTENTION !!!!
### !!!! ATTENTION !!!!
### Must be sourced (inside a bash-shell)!!!!  Never run this as a cli-cmd.
### !!!! ATTENTION !!!!
### !!!! ATTENTION !!!!

whether_to_switch_git_commithash="$1"
echo "whether_to_switch_git_commithash --> '${whether_to_switch_git_commithash}'"

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
OPS_SCRIPT_FOLDER="$( \cd "${SCRIPT_FOLDER}/../../operations/bin"; pwd  )"

  .   "${OPS_SCRIPT_FOLDER}/common-settings.sh"

###---------------------------------------------------------------
### @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
###---------------------------------------------------------------

showGitStatus() {
    printf '%.0s=' {1..50}; echo; git status; printf '%.0s=' {1..50}; echo; echo
}

showGitStatus

git status | head -1 | grep '^HEAD detached at [0-9a-z][0-9a-z]*' > /dev/null
    ### $ git status
    ###    HEAD detached at 21c6d53
    ###    nothing to commit, working tree clean
if [ $? -eq 0 ]; then
    SixCharGitHash=$( git status | head -1 | cut -d' ' -f 4 )
else
    git status | head -1 | grep '^On branch [0-9a-zA-Z_-][0-9a-zA-Z_-]*' > /dev/null
        ### $ git status
        ###     On branch T195
        ###     Your branch is up to date with 'origin/T195'.
    if [ $? -eq 0 ]; then
        # SixCharGitHash=$( git status | head -1 | cut -d' ' -f 3 )
        echo "We are already in a specific NAMED git-branch"
    else
        echo "!! ERROR !! ❌❌❌ 'git status' cli-cmd is returning UNEXPECTED output (inside CodeBuild-project) !!!"
        echo "Expecting something like: 'HEAD detached at 21c6d53' -- within CodeBuild-project"
        # echo "!! ERROR !! ❌❌❌ 'git status' cli-cmd is returning UNEXPECTED output (inside CodeBuild-project) !!!"
        # echo "Expecting something like: 'On branch T195'"

        exit 101
    fi
fi

OriginalTIER="${TIER}"
echo "TIER was originally '${OriginalTIER}' .."
if [[ ! -z ${SixCharGitHash+x} ]]; then
    echo -n "Running command --> $ "; echo \
    git branch --contains ${SixCharGitHash}
    git branch --contains ${SixCharGitHash}
        ### ---- AmazonLinux-on-CodeBuild ----
        ### $ git branch --contains eef6367
        ### * (HEAD detached at eef6367)
        ### dev
        ### ---- MacOS ----
        ### $ git branch --contains eef6367
        ### * dev
    if [ $? -ne 0 ]; then
        echo "Above cmd failed!!! ❌❌❌";
        exit 104
    fi

    lineCount=$( git branch --contains ${SixCharGitHash}  | grep -v "(HEAD detached at" | wc -l )
            ### Warning: This command will output branch-names in ALPHABETICAL-order.

    ### ------ Fix/Update the value of TIER variable.
    ### Sub-Scenario 1: This commit-HASH is in `main` as well as AT LEAST one other-branch.
    ###                 FYI: See SubSub-Scenario 1.1 below.
    ### Sub-Scenario 2: When a developer-branch was git-merged into --ANOTHER-- developer's branch (so, commit-HASH is in two places, and shows up as 2 rows in output)
    ### Sub-Scenario zzz: ALL-ELSE / otherwise (that is, unique commit-hash)
    if [ ${lineCount} -gt 1 ]; then
        if [ "${OriginalTIER}" == "main" ]; then
            echo "$0 - Sub-scenario 1"
            if [ ${lineCount} -eq 2 ]; then
                ### ASSUMPTION: there are ONLY 2 git-branches listed.
                ### If >= 3 rows, I don't think a human can identify the correct git-branch to switch too, either !!!
                TIER=$( git branch --contains ${SixCharGitHash} | grep -v "(HEAD detached at" | grep -v '^ *main *$' | head -1 | sed -e 's/[* ]\s*//g' )
            else
                echo "jq cmd failed as it is producing >3-lines of output!!! ❌❌❌";
                exit 121
            fi
        else
            echo "$0 - Sub-scenario 2 (it better be a Release#CommitHash-for-Stage/Prod or a DEVELOPER-Tier / TICKET-tier!!!)"
            ### assumption: Two developers decided to merge their branches, causing this chaos.
            ### So, we'll deploy the tier as originally specified when pipeline was created.
            TIER="${OriginalTIER}"
        fi
    else
        echo "$0 - Sub-scenario ALL-ELSE .."
        ### output was just 2 lines like:
        ###    * (HEAD detached at 2a7e251)
        ###    <someTierName>
        TIER=$( git branch --contains ${SixCharGitHash} | grep -v "(HEAD detached at" | grep -v '^ *dependabot *$' | sed -e 's/[* ]\s*//g' )
        #__ TIER=$( git branch --contains ${SixCharGitHash} | sed -e 's/\(\)//g' | cut -d' ' -f 5 )
        if [ $? -ne 0 ]; then
            echo "Above cmd failed!!! ❌❌❌";
            exit 131
        fi
    fi
    ### Scenario 1.1: --ONLY-- for `test|int|qa|stage|uat|prod` tiers, it's OK, if the evaluated value for `TIER` is `main`
    ### Else, it is a huge UN-expected problem.

    # if [[ "${OriginalTIER}" == "test" || "${OriginalTIER}" == "int" || "${OriginalTIER}" == "stage" || "${OriginalTIER}" == "uat" || "${OriginalTIER}" == "prod" ]]    &&    [ "${TIER}" == "main" ]; then
    if [[ "${UpperTiers[@]}" =~ "${OriginalTIER}" ]]    &&    [ "${TIER}" == "main" ]; then
        ### Scenario 1.1-A
        TIER="${OriginalTIER}"
        echo "Scenario: 1.1-A: RE-adjusted TIER back to be '${TIER}' in Scenario 1.1 !"
    else
        # if [[ "${OriginalTIER}" != "test" && "${OriginalTIER}" != "int" && "${OriginalTIER}" != "stage" && "${OriginalTIER}" != "uat" && "${OriginalTIER}" != "prod" ]]    &&    [ "${TIER}" == "main" ]; then
        if [[   !   "${UpperTiers[@]}" =~ "${OriginalTIER}" ]]    &&    [ "${TIER}" == "main" ]; then
            ### Scenario 1.1-B
            echo "!! oh. oh. !! Invalid calculated-TIER === '${TIER} and OriginalTIER === '${OriginalTIER}'' !";
            if [ "${TIER}" == "main" ]; then
                ### Scenario 1.1-BAA -- when manually-triggering a developer-tier's pipeline via AWS-Console.
                TIER="${OriginalTIER}"
                echo "Scenario: 1.1-BBB: RE-adjusted TIER back to be '${TIER}' in Scenario 1.1 !"
            else
                echo "!! Internal error 141 !! Invalid calculated-TIER === '${TIER} and OriginalTIER === '${OriginalTIER}''!!! ❌❌❌";
                exit 141
            fi
        else
            ### Scenario 1.1-??
            if [ "${TIER}" == "main" ] || [ "${TIER}" == "" ]; then
                echo "!! Internal error 146 !! Invalid calculated-TIER === '${TIER} and OriginalTIER === '${OriginalTIER}''!!! ❌❌❌";
                exit 146
            fi
        fi
        echo "TIER confirmed to be '${TIER}'"
    fi
fi

### ------ now do the actual `git switch` cmd

if [ -f cdk.json ]; then
    if [ "${whether_to_switch_git_commithash}" == "True" ] || [ "${whether_to_switch_git_commithash}" == "true" ]; then
        echo \
        jq ".context.\"git-source\".git_commit_hashes.${TIER}" cdk.json --raw-output
        jq ".context.\"git-source\".git_commit_hashes.${TIER}" cdk.json --raw-output
        if [ $? -ne 0 ]; then
            echo "Above cmd failed!!! ❌❌❌";
            exit 161
        fi
        JqOutput=$( jq ".context.\"git-source\".git_commit_hashes.${TIER}" cdk.json --raw-output )
        echo "JqOutput --> '${JqOutput}'"

        echo \
        git checkout --force ### to address ---> error: Your local changes to the following files would be overwritten by checkout: package-lock.json
        git checkout --force ### to address ---> error: Your local changes to the following files would be overwritten by checkout: package-lock.json
        if [ $? -ne 0 ]; then
            echo "Above cmd failed!!! ❌❌❌";
            exit 171
        fi

        if [ "${JqOutput}" == "null" ]; then
            echo "NOTE: TIER='${TIER}' is missing in cdk.json's git_commit_hashes section"
            ### 99% chance this is a DEVELOPER-tier
            ### Switch explicitly to the TIER, to support scenario where the pipeline is triggered from AWS-Console (and therefore `git status` will be `main` git-branch)
            echo \
            git switch --discard-changes "${TIER}"
            git switch --discard-changes "${TIER}"
        else
            if [ "${whether_to_switch_git_commithash}" == "True" ] || [ "${whether_to_switch_git_commithash}" == "true" ]; then
                echo "About to SWITCH git-branch (per cdk.json config) -- via 'git checkout' command .."
                ### TODO for "regular commit-hashes" & "git-tags" .. it's safer to do "git checkout" vs. "git switch"?
                echo \
                git checkout --force "${JqOutput}"
                git checkout --force "${JqOutput}"
            fi
        fi

    else
        echo "Lookup (within cdk.json) returned EMPTY !  Is this a Ticket/Developer-Tier?"
    fi ### if whether_to_switch_git_commithash ..

else
    ### For AWS-SAM sub-projects, etc ..
    echo "Missing cdk.json. So skipping all jq cmds .."
    ### Switch explicitly to the TIER, to support scenario where the pipeline is triggered from AWS-Console (and therefore `git status` will be `main` git-branch)
    echo \
    git switch --discard-changes "${TIER}"
    git switch --discard-changes "${TIER}"

fi ### if cdk.json exists

showGitStatus

### EoScript
