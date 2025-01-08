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
pipenv sync
# pipenv install --deploy --ignore-pipfile
                    ### --ignore-pipfile ==> Use `Pipfile.lock` and do -NOT- use `Pipfile`.
### !!! Stop using `venv` and plain `pip`
### python -m venv .venv
### source .venv/bin/activate
### pip install -r requirements.txt

GITHUB_REPOSITORY=$(git ls-remote --get-url | sed -e 's/..*github.com\/\(.*\)/\1/');

( unset BUILDPLATFORM; unset DOCKER_DEFAULT_PLATFORM; unset TARGETPLATFORM;
  export CPU_ARCH="$(uname -m)";  ### PICK ONE !!!
  export CPU_ARCH="x86_64";       ### PICK ONE !!!
  pipenv run npx cdk synth --quiet --all --app "python3 pipeline_app.py"  -c tier=${TIER} -c git_repo=${GITHUB_REPOSITORY} --profile ${AWSPROFILE} --region ${AWSREGION}
)
```

Change above cmd tto remove ~~`cdk synth`~~ and use `cdk deploy` instead.


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