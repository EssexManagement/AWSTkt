# Attention !

This is for TICKET opened with AWS Tech-SUPPORT.

AWS Case # `173260180100988`

Opened on 2024-11-26 06:16:41

Tital: _CodeBuild unable to_

Severity: System impaired

<BR/><BR/><BR/><BR/>
<HR/><HR/><HR/><HR/>

# HOW-TO

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