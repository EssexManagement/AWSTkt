# FACTrial ServiceCatalogItem DevOps-process

# Overview

<HR/>
<HR/>
<HR/>
<HR/>

# Step 1: UPDATE configuration

Edit the files:
1.  [`devops/ServiceCatalogItem/bin/constants.ts`](./bin/constants.ts)
    *   Warning: Make sure to keep this file IN-SYNC with the file [../../constants.py](../../constants.py)
1.  Per security guidance, upgrade the versions within `package.json` file

<HR/>
<HR/>
<HR/>
<HR/>


# Step 2: prepare your laptop

```bash
### ------ ATTENTION !!! Pick one of the 2 below -------
### ------ ATTENTION !!! Pick one of the 2 below -------
TIER="acct-nonprod"     ### <------ Pick one -------
TIER="acct-prod"        ### <------ Pick one -------
### ------ ATTENTION !!! Pick one of the 2 above -------
### ------ ATTENTION !!! Pick one of the 2 above -------

AWSPROFILE=....
AWSREGION=.....

\rm -rf package-lock.json
\rm -rf node_modules/ cdk.out/
npm i --include-dev
unset BUILDPLATFORM; unset DOCKER_DEFAULT_PLATFORM; unset TARGETPLATFORM;


CdkAppCmd="npx ts-node --prefer-ts-exts bin/cdk_app.ts"

### build TypeScript-based Lambda
( cd src/; \rm -rf package-lock.json build/ dist/ node_modules/; npm i --include-dev; npm run build )
### OLD way - ( cd src/ServiceCatalogItemHandler/; \rm -rf package-lock.json build/ dist/ node_modules/ ; npm i --include-dev; npm run build )

npx cdk synth \
        --context TIER="${TIER}"            \
        --app "${CdkAppCmd}"                \
        --quiet --profile ${AWSPROFILE} --region ${AWSREGION}

cfn-lint --include-experimental --ignore-check=W8001,W2001  cdk.out/*.yaml
```

<HR/>

# Step 3: Deploy the tools

Quite possibly, someone already did the deployment, and so there should be NO changes.<BR/>
If `cdk deploy` commands notes that things have changed .. BEWARE!! Things may not go smoothly for rest of this file's instructions!

```bash
npx cdk deploy \
        --all     --require-approval never  \
        --context TIER="${TIER}"            \
        --app "${CdkAppCmd}"                \
        --quiet --profile ${AWSPROFILE} --region ${AWSREGION}
```

<HR/>
<HR/>
<HR/>
<HR/>

# APPENDIX -- AWS-official 'oobox' CDK TypeScript project HOW-TO

The `cdk.json` file tells the CDK Toolkit how to execute your app.<BR/>
Example: Useful commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `npx cdk deploy`  deploy this stack to your default AWS account/region
* `npx cdk diff`    compare deployed stack with current state
* `npx cdk synth`   emits the synthesized CloudFormation template
