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
python -m venv .venv
source .venv/bin/activate
npm i
pip install -r requirements.txt

GITHUB_REPOSITORY=$(git ls-remote --get-url | sed -e 's/..*github.com\/\(.*\)/\1/');

( unset BUILDPLATFORM; unset DOCKER_DEFAULT_PLATFORM; unset TARGETPLATFORM;
  export CPU_ARCH="$(uname -m)";  ### PICK ONE !!!
  export CPU_ARCH="x86_64";       ### PICK ONE !!!
  npx cdk synth --quiet --all --app "python3 pipeline_app.py"  -c tier=${TIER} -c git_repo=${GITHUB_REPOSITORY} --profile ${AWSPROFILE} --region ${AWSREGION}
)

( unset BUILDPLATFORM; unset DOCKER_DEFAULT_PLATFORM; unset TARGETPLATFORM;
  npx cdk deploy --require-approval never  --quiet --all --app "python3 pipeline_app.py"  -c tier=${TIER} -c git_repo=${GITHUB_REPOSITORY} --profile ${AWSPROFILE} --region ${AWSREGION}
)
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