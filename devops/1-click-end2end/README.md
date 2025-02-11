# FACTrial 1-click-end2end DevOps-process

# Overview

<HR/>
<HR/>
<HR/>
<HR/>

# Step 1: UPDATE configuration

Edit the files:
1.  [`devops/1-click-end2end/bin/constants.ts`](./bin/constants.ts)
    *   Warning: Make sure to keep this file IN-SYNC with the file [../../constants.py](../../constants.py)
1.  Per security guidance, upgrade the versions within `package.json` file

<HR/>
<HR/>
<HR/>
<HR/>


# Step 2: prepare your laptop

```bash
TIER="dev|int|stage|prod"
AWSPROFILE=....
AWSREGION=.....

\rm -rf .aws-sam/ node_modules/ package-lock.json
npm i --include-dev

npx cdk synth --context TIER="${TIER}" --quiet --profile ${AWSPROFILE} --region ${AWSREGION}
```

<HR/>

# Step 3: Deploy the tools

Quite possibly, someone already did the deployment, and so there should be NO changes.<BR/>
If `cdk deploy` commands notes that things have changed .. BEWARE!! Things may not go smoothly for rest of this file's instructions!

```bash
npx cdk deploy --all --context TIER="${TIER}"  --quiet --require-approval never --profile ${AWSPROFILE} --region ${AWSREGION}
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
