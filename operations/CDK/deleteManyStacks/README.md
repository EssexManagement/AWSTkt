# Tool to DELETE a large set of stacks via a StepFunction

Given a list of Stack-Name in "heirarchical-order" as to which can be deleted in Parallel and which MUST-BE deleted sequentially.<BR/>
If any of them are in FAILED-state, this StepFn will attempt to delete EACH SUCH SPECIFIC stack.

NOTE: You must ensure any dependencies are deleted first.  That's what sequencing is all about!

ATTENTION: if a NON-failed stack is using/referencing resources from within a Failed-Stack, YOU must MANUALLY destroy that NON-failed stack.

## Sample input to StepFunction

REF: [generic example](../../Scripts/StepFunctions/StacksMgmt/tools/cloud-only/stack-mgmt/(Input)%20myStepFunc_DeleteStacksRecursively-Imaginary.json)

REF: [FACTrial example](./test/sample-input-to-deleteStacksInSequence.json)

<BR/>
<BR/>
<BR/>
<HR/>
<HR/>

# Step 1: UPDATE configuration

Edit the files:
1.  [`./bin/constants.ts`](./bin/constants.ts)
    *   Warning: Make sure to keep this file IN-SYNC with the all other `constants.ts` (typescript) and `constants.py` (python)
1.  Per security guidance, upgrade the versions within `package.json` file

<BR/>
<BR/>
<HR/>
<HR/>


# Step 2: prepare your laptop

```bash
TIER="dev|int|stage|prod"   ### 👈🏾👈🏾 !! Pick one !!
AWSPROFILE=....
AWSREGION=.....

\rm -rf package-lock.json
\rm -rf node_modules/ cdk.out/
npm i --include-dev

npx cdk synth --context TIER="${TIER}" --quiet --profile ${AWSPROFILE} --region ${AWSREGION}
```

<BR/>
<BR/>
<HR/>
<HR/>

# Step 3: Deploy the tools

Quite possibly, someone already did the deployment, and so there should be NO changes.<BR/>
If `cdk deploy` commands notes that things have changed .. BEWARE!! Things may not go smoothly for rest of this file's instructions!

```bash
npx cdk deploy --all --context TIER="${TIER}" --quiet --profile ${AWSPROFILE} --region ${AWSREGION}
```

Note: difference between this above command and the command in preceding section: ~~`synth`~~ replaced with `deploy --all`<BR/>
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
This is because we need to deploy > 1 stack with this single command.

<BR/>
<BR/>
<BR/>
<BR/>
<HR/>
<HR/>
<HR/>
<HR/>

# APPENDIX -- AWS-official 'oobox' CDK TypeScript project HOW-TO

This is a blank project for CDK development with TypeScript.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

## Useful commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `npx cdk deploy`  deploy this stack to your default AWS account/region
* `npx cdk diff`    compare deployed stack with current state
* `npx cdk synth`   emits the synthesized CloudFormation template
