# Getting started

- [Getting started](#getting-started)
- [Deploy Utilities for DEVOPS-Pipeline](#deploy-utilities-for-devops-pipeline)
  - [Deploy a generic Lambda to wipe-out a single bucket.](#deploy-a-generic-lambda-to-wipe-out-a-single-bucket)
  - [Deploy a generic Lambda to sleep for a random # of secs](#deploy-a-generic-lambda-to-sleep-for-a-random--of-secs)
  - [Deploy a Tool to destroy-stacks for FACTrial](#deploy-a-tool-to-destroy-stacks-for-factrial)
  - [Deploy a Tool to "hydrate" RDS Post-deployment](#deploy-a-tool-to-hydrate-rds-post-deployment)
  - [Deploy entire DevOps toolchain (as a StepFunc)](#deploy-entire-devops-toolchain-as-a-stepfunc)
- [APPENDIX = How to UPGRADE Python-PyPi-Modules and Node.JS Packages](#appendix--how-to-upgrade-python-pypi-modules-and-nodejs-packages)
  - [CDK codebase](#cdk-codebase)
  - [App-specific codebase](#app-specific-codebase)
- [APPENDIX = When CodeBuild suddenly starts failing (Cache is corrupted)](#appendix--when-codebuild-suddenly-starts-failing-cache-is-corrupted)
- [APPENDIX: When WIP/"dirty" `dev` git-branch needs be merged into `main`](#appendix-when-wipdirty-dev-git-branch-needs-be-merged-into-main)
- [APPENDIX -- Old CloudFormation-based Deploy StepFunctions to explicitly-DELETE stacks -- in the proper-order](#appendix----old-cloudformation-based-deploy-stepfunctions-to-explicitly-delete-stacks----in-the-proper-order)


Run the commands below as is (Warning: You should currently be in the SAME folder as this README ../devops/README-devops file)

```bash
pushd ..
CLOUD_ENGG_GIT_REPO="cloud_eng"
git clone https://github.com/BIAD/${CLOUD_ENGG_GIT_REPO}.git
```

<HR/><HR/><HR/><HR/>
<BR/><BR/><BR/><BR/>

# Deploy Utilities for DEVOPS-Pipeline

## Deploy a generic Lambda to wipe-out a single bucket.

STEP 0: 👉🏾👉🏾👉🏾
```bash

pushd ${CLOUD_ENGG_GIT_REPO}/AWS-SAM/lambdas/wipeout-bucket/
```

&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; This will correctly `cd` into the appropriate SUB-folder within the above `git clone`-d  folder-tree above.<BR/>

STEP 1: Read thru' the README.md file inside that folder.<BR/>
STEP 2: Edit the `template.yaml` file inside that folder.<BR/>
STEP 3: Next, run the following commands.. .. changing the values for `AWSPROFILE` and `TIER` as appropriate

```bash

AWSREGION="us-east-1"

\rm -rf .aws-sam/   ~/.aws-sam/   ~/node_modules/  ./src/node_modules/
( cd src;    \rm -f package-lock.json;   npm install --include-dev )

sam build

AWSPROFILE="DEVINT"; TIER="dev"
StackName="wipeout-bucket-${TIER}"
sam deploy --stack-name "${StackName}" \
    --parameter-overrides Tier=${TIER}  DateTimeStamp="$(date +'%FT%T')"  \
    --capabilities CAPABILITY_NAMED_IAM  --on-failure DELETE --no-confirm-changeset \
    --profile ${AWSPROFILE} --region ${AWSREGION}

AWSPROFILE="DEVINT"; TIER="int"
StackName="wipeout-bucket-${TIER}"
.. repeat above sam deploy cli-cmd ..

AWSPROFILE="UAT"; TIER="uat"
StackName="wipeout-bucket-${TIER}"
.. repeat above sam deploy cli-cmd ..

AWSPROFILE="PROD"; TIER="prod"
StackName="wipeout-bucket-${TIER}"
.. repeat above sam deploy cli-cmd ..
```

<HR/><HR/>
<BR/><BR/>

## Deploy a generic Lambda to sleep for a random # of secs

STEP 0: 👉🏾👉🏾👉🏾
```bash
popd
pushd ${CLOUD_ENGG_GIT_REPO}/AWS-SAM/lambdas/sleep-random/
```

Now, repeat steps 1-to-3 from the above/previous section.. except that ..

```bash
StackName="SleepRandom"
```

<HR/><HR/>

```bash
popd
pushd ${CLOUD_ENGG_GIT_REPO}/CDK/deleteManyStacks/

\rm -rf node_modules/ cdk.out/ package-lock.json
npm i --include-dev

npx cdk synth --context TIER="${TIER}"  --quiet --profile ${AWSPROFILE} --region ${AWSREGION}
```

If everything is OK with above .. continue with following commands.

```bash
AWSREGION="us-east-1"

AWSPROFILE="DEVINT"; TIER="dev"
npx cdk deploy --all --context TIER="${TIER}"  --quiet --require-approval never --profile ${AWSPROFILE} --region ${AWSREGION}

AWSPROFILE="DEVINT"; TIER="int"
.. repeat above cdk-deploy cli-cmd ..

AWSPROFILE="UAT"; TIER="uat"
.. repeat above cdk-deploy cli-cmd ..

AWSPROFILE="PROD"; TIER="prod"
.. repeat above cdk-deploy cli-cmd ..
```

<HR/><HR/>
<BR/><BR/>

## Deploy a Tool to destroy-stacks for FACTrial

Back to FACTrial's backend-end git-repo (ideally, via `popd` command below)

```bash
popd
pushd ./devops/cleanup-stacks/

\rm -rf node_modules/ cdk.out/ package-lock.json
npm i --include-dev

npx cdk synth --context TIER="${TIER}"  --quiet --profile ${AWSPROFILE} --region ${AWSREGION}
```

If everything is OK with above .. continue with following commands.

```bash
AWSREGION="us-east-1"

AWSPROFILE="DEVINT"; TIER="dev"
npx cdk deploy --context TIER="${TIER}"  --quiet --require-approval never --profile ${AWSPROFILE} --region ${AWSREGION}

AWSPROFILE="DEVINT"; TIER="int"
npx cdk deploy --context TIER="${TIER}"  --quiet --require-approval never --profile ${AWSPROFILE} --region ${AWSREGION}

AWSPROFILE="UAT"; TIER="uat"
npx cdk deploy --context TIER="${TIER}"  --quiet --require-approval never --profile ${AWSPROFILE} --region ${AWSREGION}

AWSPROFILE="PROD"; TIER="prod"
npx cdk deploy --context TIER="${TIER}"  --quiet --require-approval never --profile ${AWSPROFILE} --region ${AWSREGION}
```

<HR/><HR/>
<BR/><BR/>

## Deploy a Tool to "hydrate" RDS Post-deployment

```bash
popd
pushd ./devops/post-deployment/

\rm -rf node_modules/ cdk.out/ package-lock.json
npm i --include-dev

npx cdk synth --context TIER="${TIER}"  --quiet --profile ${AWSPROFILE} --region ${AWSREGION}
```

If everything is OK with above .. continue with following commands.

If everything is OK with above .. run the `npx cdk deploy` commands from previous sub-section.

<HR/><HR/>
<BR/><BR/>

## Deploy entire DevOps toolchain (as a StepFunc)

```bash
popd
pushd ./devops/1-click-end2end

\rm -rf node_modules/ cdk.out/ package-lock.json
npm i --include-dev

npx cdk synth --context TIER="${TIER}"  --quiet --profile ${AWSPROFILE} --region ${AWSREGION}
```

If everything is OK with above .. run the `npx cdk deploy` commands from previous sub-section.

<HR/><HR/><HR/><HR/>
<BR/><BR/><BR/><BR/>

# APPENDIX = How to UPGRADE Python-PyPi-Modules and Node.JS Packages

## CDK codebase

1. Update `./requirements.in`  (found in the topmost folder of git-repo source-code)
    * This step should be done by an CI/CD-developer.
    * Follow instructions (see commented-lines) --INSIDE-- the above file.
    * Note: This should result in git detecting changes to 2 files: `requirements.in` and `requirements.txt`<BR/>&nbsp;
2. Update NodeJS `package.json` (found in the topmost folder of git-repo source-code)
    * This step should be done by an CI/CD-developer.
    * `npm i --include-dev`
    * Note: This should result in git detecting changes to 2 files: `./package.json` and `./package-lock.json`<BR/>&nbsp;
4. `cd ./devops` and then, chose one of the 2 options below.<BR/>&nbsp;
   1. OPTION 1: Automatically Update devops-pipeline related NodeJS packages.
       * Run `./bin/cleanup-devops.sh` and answer `y` to any questions.
       * Note: This should result in git detecting changes to -MULTIPLE- files: `devops/**/package.json` and `devops/**/package-lock.json`<BR/>&nbsp;
   2. OPTION 2: --MANUALLY-- Update devops-pipeline related NodeJS `*/package.json`
       * This step should be done by an CI/CD-developer.
       * `npm i --include-dev`
       * Note: This should result in git detecting changes to 2 files: `./package.json` and `./package-lock.json`<BR/>&nbsp;

## App-specific codebase

1. Update `api/runtime/requirements.in`
    * This step should be done by an Python Application-developer.
    * Follow instructions (see commented-lines) --INSIDE-- the above file.
    * Note: This should result in git detecting changes to 2 files: `requirements.in` and `requirements.txt`<BR/>&nbsp;
2. Update `api/runtime_report/requirements.in`
    * This step should be done by an Python Application-developer.
    * Follow instructions (see commented-lines) --INSIDE-- the above file.
    * Note: This should result in git detecting changes to 2 files: `requirements.in` and `requirements.txt`<BR/>&nbsp;
3. Update `tests/requirements.txt`
    * This step should be done by an Python Application-developer.

<HR/><HR/><HR/><HR/>
<BR/><BR/><BR/><BR/>

# APPENDIX = When CodeBuild suddenly starts failing (Cache is corrupted)

```bash
AWSPROFILE=.. .. ..
AWSREGION="us-east-1"

CBProjects=$( aws codebuild list-projects  --profile ${AWSPROFILE} --region ${AWSREGION} | jq '.projects[]' --raw-output )

for cbproj in ${CBProjects[@]}; do
    aws codebuild invalidate-project-cache --project-name ${cbproj}  --profile ${AWSPROFILE} --region ${AWSREGION};
done
```

<BR/> <BR/> <BR/> <BR/>
<HR/> <HR/> <HR/> <HR/>

# APPENDIX: When WIP/"dirty" `dev` git-branch needs be merged into `main`

```bash
git branch
git status
git stash push --include-untracked
git status
git switch dev; git fetch --all; git pull
git switch main; git fetch --all; git pull

git diff main dev --name-only
git merge dev --squash

git diff main dev --name-only
git diff main dev

git switch dev; git fetch --all; git pull
git stash pop
```

<BR/> <BR/> <BR/> <BR/>
<HR/> <HR/> <HR/> <HR/>

# APPENDIX -- Old CloudFormation-based Deploy StepFunctions to explicitly-DELETE stacks -- in the proper-order

STEP 0: 👉🏾👉🏾👉🏾
```bash
popd
pushd ${CLOUD_ENGG_GIT_REPO}/CDK/deleteManyStacks/
```

&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; This will correctly `cd` into the appropriate SUB-folder within the above `git clone`-d  folder-tree above.<BR/>

STEP 1: Read thru' the README.md file inside that folder.<BR/>
STEP 2: Edit the `template.yaml` file inside that folder.<BR/>
STEP 3: Next, run the following commands.. .. changing the values for `AWSPROFILE` and `TIER` as appropriate

```bash
AWSREGION="us-east-1"

\rm -rf cdk.out/ node_modules/ package-lock.json
npm i --include-dev

### synth
npx cdk synth --context TIER="${TIER}"  --quiet --profile ${AWSPROFILE} --region ${AWSREGION}

### deploy
AWSPROFILE="DEVINT"; TIER="dev"
npx cdk deploy --all --context TIER="${TIER}"  --quiet --require-approval never --profile ${AWSPROFILE} --region ${AWSREGION}

### "int" tier is NOT needed, as same StepFunction for "dev" is reused.

AWSPROFILE="UAT"; TIER="uat"
npx cdk deploy --all --context TIER="${TIER}"  --quiet --require-approval never --profile ${AWSPROFILE} --region ${AWSREGION}

AWSPROFILE="PROD"; TIER="prod"
npx cdk deploy --all --context TIER="${TIER}"  --quiet --require-approval never --profile ${AWSPROFILE} --region ${AWSREGION}
```


<HR/><HR/><HR/><HR/>

/EoF
