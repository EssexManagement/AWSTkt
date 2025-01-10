# All possible ways to create/manage/use Lambda-Layers

# HOW-TO - deploy the CDK-stacks

```bash
PYTHON_VERSION="3.12"
\rm -rf ~/.local

npm i --include-dev

pip install pipenv --user
pipenv lock --dev --python ${PYTHON_VERSION} --clear
pipenv sync --dev
# pipenv install --deploy --ignore-pipfile
                    ### --ignore-pipfile ==> Use `Pipfile.lock` and do -NOT- use `Pipfile`.
### !!! Stop using `venv` and plain `pip`
### python -m venv .venv
### source .venv/bin/activate
### pip install -r requirements.txt

GITHUB_REPOSITORY=$(git ls-remote --get-url | sed -e 's/..*github.com\/\(.*\)/\1/');

( unset BUILDPLATFORM; unset DOCKER_DEFAULT_PLATFORM; unset TARGETPLATFORM;
  pipenv run npx cdk synth --quiet --all --app "python3 cdk_pipeline_app.py"  -c tier=${TIER} -c git_repo=${GITHUB_REPOSITORY} --profile ${AWSPROFILE} --region ${AWSREGION}
)
```

Change above cmd tto remove ~~`cdk synth`~~ and use `cdk deploy` instead.


<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

# Scenarios / Use-Cases

1. No Layers deployed (a.k.a. brand new clean AWS-Account):
    1. (Sunny Day Scenario): This `cdk deploy` execution will do 2 things:
        1. deploy the Lambda-Layers as CDK-Constructs and then
        2. use THAT same CDK-construct REFERENCES within 𝜆-function-Construct's layers-param ALSO.
    1. (Rainy-Day Scenario): The `LambdaConfig` class's STATIC-methods `lookup_lambda_layer(..)` and `cache_lambda_layer(..)` should be ROBUST -- even if developer makes mistakes, given that the Layers are NOT deployed.<BR/>
        Basically, catch errors durin SYNTH itself.
    1. The `backend/lambda_layer/bin/get_lambda_layer_hashes.py` script (that uses boto3) must support all of these above scenarios.
1. Layers are already deployed:
    1. (Sunny Day Scenario):<BR/>
        The git-repo's `backend/lambda_layer/lambda_layer_hashes.py` has correct ARNs for the Lambda-Layers.<BR/>
        So, .. the Lambda-Layers should --NOT-- be re-deployed.<BR/>
        Also, the `LambdaConfig` class's STATIC-methods `lookup_lambda_layer(..)` and `cache_lambda_layer(..)` should be ROBUST -- and use cdk's `aws_lambda.LambdaLayer.from_layer_arn()`; No cdk-SYNTH or cdk-DEPLOY errors!!!
    1. (Rainy-Day Scenario):<BR/>
        The git-repo's `backend/lambda_layer/lambda_layer_hashes.py` has OUTDATED ARNs for the Lambda-Layers.<BR/>
        The `backend/lambda_layer/bin/get_lambda_layer_hashes.py` script should address this --automatically-- during "cdk-deploy"!

<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

# APPENDIX - Clean-up

```bash
TIER=.. .. ...            ### ❌❌❌
AWSPROFILE=.. .. ...      ### ❌❌❌
AWSREGION="us-east-1"     ### Should match the DEFAULT-region of the aove AWSPROFILE !!!

\rm -f "/tmp/${AWSPROFILE}-${AWSREGION}-all-LambdaLayers.json"
OutputFileName="backend/lambda_layer/lambda_layer_hashes.py"
ScriptCLIArgs=( ${AWSPROFILE} ${TIER} ${OutputFileName} )

### Download LATEST-VERSIONS information about the DEPLOYED Lambda-LAYERS
ScriptPath="backend/lambda_layer/bin/get_lambda_layer_hashes.py"
PYTHONPATH=${PWD}:${PYTHONPATH} PATH=${PWD}:$PATH pipenv run python3 "${ScriptPath}" ${ScriptCLIArgs[@]}

### Destroy
ScriptPath="backend/lambda_layer/bin/wipeout_deployed_lambda_layers.py"
PYTHONPATH=${PWD}:${PYTHONPATH} PATH=${PWD}:$PATH pipenv run python3 "${ScriptPath}" ${ScriptCLIArgs[@]}
```

Next:<BR/>
1. Check the AWS-Console for Lambda-LAYERS, to see if OLDER-versions still exist.
  * !!!! Pay attention to the VERSION-#s on the webpage !!!!
  * URL to console: https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/layers
1. If yes (older version#s exist), repeat -ALL- of the above commands (until ALL older versions are also deleted).
1. If you see -NO- change on the AWS-Console for Lambda-LAYERS .. STOP and contact the developer of this script.


<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

# APPENDIX - 100% sanity-checking CDK (before deploying)

The above `synth` command only sanity-checks the Pipeline-stack.<BR/>
The pipeline will deploy mnultiple Application-stacks!<BR/>
The following will sanity-check that the pipeline will not fail during cdk-synth.

```bash
( unset BUILDPLATFORM; unset DOCKER_DEFAULT_PLATFORM; unset TARGETPLATFORM;
  CPU_ARCH="$(uname -m)";  ### PICK ONE !!!
  CPU_ARCH="x86_64";       ### PICK ONE !!!
  pipenv run npx cdk synth --quiet --all --app "python3 layers_app.py"  -c tier=${TIER} -c CPU_ARCH=${CPU_ARCH} -c git_repo=${GITHUB_REPOSITORY} -c  AWSPROFILE=${AWSPROFILE} --profile ${AWSPROFILE} --region ${AWSREGION}
)
```

<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

/End