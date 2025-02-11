# FACTrial POST-Deployment SUB-process

# Usage

If --NO-- JSON-input is provided, then this StepFunction will run 𝜆s in the following sequence for ETL:-

1. ~~`RdsInstanceSetup`~~
    * (This is s--SKIPPED-- .. unless you do as shown in the "warning" below)
    * Note: This 𝜆 will wipe out everything in the database.  it currently handles `emfact_user` and `GRANTS`.
1. ~~`Rds_init`~~ a.k.a. ~~`SchemaTableInit`~~
    * (This is s--SKIPPED-- .. unless you do as shown in the "warning" below)
    * Note: This `Rds_init` 𝜆 will wipe out everything in the database
2. `refresh_ncit`
3. `etl_start_mp`

<BR/><BR/>

> !! WARNING !!<BR/>
> If you provide the following JSON as input, the 1st two 𝜆s will -ALSO- be executed !!!

Pick one of these two.  Both are equivalent.

> `{ "run-rds-init": true }`<BR/>
> `{ "runRdsInit":   true }`

<HR/><HR/><HR/><HR/>
<BR/><BR/><BR/><BR/>

# Manual DEPLOYMENT

ATTENTION: --ONLY-- use this section if you are --NOT-- using `cdk` to deploy this automatically.

## Step 1: UPDATE configuration

Edit the files:
1.  [`devops/post-deployment/bin/constants.ts`](./bin/constants.ts)
    *   Warning: Make sure to keep this file IN-SYNC with the file [../../constants.py](../../constants.py)
1.  Per security guidance, upgrade the versions within `package.json` file

<HR/>

## Step 2: prepare your laptop

```bash
TIER="dev|int|stage|prod"
AWSPROFILE=....
AWSREGION=.....

\rm -rf .aws-sam/ node_modules/ package-lock.json
npm i --include-dev

npx cdk synth --context TIER="${TIER}" --quiet --profile ${AWSPROFILE} --region ${AWSREGION}
```

<HR/>

## Step 3: Deploy the tools

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
