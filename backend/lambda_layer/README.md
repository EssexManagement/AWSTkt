# Creating a new Lambda-layer

1. Just in case you have an active `venv` on current-shell -- as a precaution -- open a new bash-shell!!!
    * This is important, so that you do NOT mess up your existing .venv !!!!!
1. Create a new SUB-FOLDER under [`backend/lambda_layer`](../../backend/lambda_layer/).
1. `cd` into the sub-folder SPECIFIC to the 𝜆-layer.
    * This is important!!!!!
    * This is important!!!!!
    * This is important!!!!!
    * Example `cd "./numpy-etc"`
1. Create a mew `Pipfile`  ([See Example](./psycopg/Pipfile))
1. Run `\rm -rf ~/.cache/ ~/.local/ ~/.venv/ .cache/ .local/ .venv/ __pycache__/`
1. Run `pip install pipenv`
1. Run `pipenv lock --dev --clear --python ${PYTHON_VERSION}`
    * Note: set the value of the bash-variable called `PYTHON_VERSION` in above cli-command
    * It should match the constant defined within `common/cdk/constants_cdk.py`
1. Verify there is a NEW file named `Pipfile.lock`
1. `git commit` both these files.

<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

# Creating the "Hashes" file (for use by CDK-code)

Important: Run the following commands at the TOPMOST folder of this project !!!!!!!!

```bash
pipenv sync --dev
pipenv install boto3 regex

TIER="dev"
ScriptPath="backend/lambda_layer/bin/get_lambda_layer_hashes.py"
OutputFileName="backend/lambda_layer/lambda_layer_hashes.py"
ScriptCLIArgs=( ${AWSPROFILE} ${TIER} ${OutputFileName} )

PYTHONPATH=${PWD}:${PYTHONPATH} PATH=${PWD}:$PATH pipenv run python3 "${ScriptPath}" ${ScriptCLIArgs[@]}
```

<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

## Local-Testing

run each of the following commands --  AS IS !

```bash
cd ..??S-SUB-FOLDER-??..  ### <----------- Fix this !!!

PYTHON_VERSION="3.12"
\rm -rf ~/.local
LOCALDIR="/tmp/MyLambdaLayer"
mkdir "${LOCALDIR}"

pip install pipenv --user
pipenv lock --dev --python ${PYTHON_VERSION} --clear
pipenv sync --dev
# pipenv install --deploy --ignore-pipfile
                    ### --ignore-pipfile ==> Use `Pipfile.lock` and do -NOT- use `Pipfile`.
### !!! Stop using `venv` and plain `pip`
### python -m venv .venv
### source .venv/bin/activate
### pip install -r requirements.txt

pipenv run docker run --rm -u "657488410:1360859114"  \
    -v "${LOCALDIR}:/asset-output:delegated" \
    -v "$(pwd):/asset-input:delegated" \
    --env "PIP_ONLY_BINARY=:all:" \
    --env "PIP_TARGET=/asset-output/python" \
    --env "PIPENV_VENV_IN_PROJECT=1" \
    --env "HOME=/asset-input" \
    --env "PIPENV_HOME=/tmp/pipenv" \
    -w "/asset-input" \
    --entrypoint bash "public.ecr.aws/docker/library/python:3.12" \
    -c "pip install pipenv && \
        PYTHONPATH=/asset-output/python PATH=/asset-output/python/bin:$PATH pipenv sync --dev && \
        cd /asset-output && \
        rm -rf python/botocore &&   \
        find . -name '*.txt' -type f -delete && \
        find . -name '*.md'  -type f -delete && \
        ( find . -name \"datasets\"    -type d | xargs rm -rf ) &&  \
        ( find . -name \"examples\"    -type d | xargs rm -rf ) &&  \
        ( find . -name \"tests\"       -type d | xargs rm -rf ) &&  \
        ( find . -name \"*.dist-info\" -type d | xargs rm -rf )"
```

<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

# Case Details

We have been struggling for 3 FULL business days now, with `AWS CodeBuild`.

WHEN PROBLEM STARTED:<BR/>
since we created standard "`psycopg`" and "`pandas`" LambdaLayers and started using it across ALL lambdas (across multiple stacks deployed by same `cdk deploy` command)

THE ISSUE:<BR/>
cdk-synth INSIDE AWS-CODEBUILD project FAILS with no details (Docker exit-code only); FYI ONLY: cdk-synth from MacBook-Pro M1 is working just fine.

WHAT WE TRIED:<BR/>
No benefit in Changing BUILD-IMAGE between `Standard` and `AL2_ARM_3`.  No benefit in increasing CodeBuild-instance-size to `X2_LARGE`.  So, we stopped creating `x86_64` Layers & Lambdas. Instead ONLY focused on `arm64` only.


/End