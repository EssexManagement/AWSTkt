# Lambda to connect to RDS-Proxy // DB-Proxy

This project contains source code and supporting files for a serverless application that you can deploy with the SAM CLI. It includes the following files and folders.

- `template.yaml` - A template that defines the application's AWS resources.
- `src/` - Code for the application's Lambda function written in TypeScript.
- `events` - (Testign only) Invocation events that you can use to invoke the function.
- `src/tests` - Unit tests for the application code.

The application's' resources are defined in the `template.yaml` file in this project.

<HR/><HR/><HR/><HR/>
<BR/><BR/><BR/><BR/>


# Deploy the sample application

To build + deploy your application for the first time, run the following in your shell:

FYI - These below commands will have a series of user-prompts (see list below).

PRE-REQUISITES: Edit the file `template.json` and CHANGE the `Default` value of ALL the "Template-Parameters".

Only after that, run following commands:-

```bash
TIER="dev|int|stage|prod"  ### 👈🏾👈🏾 PICK on value !!!!!!!
AppName="FACT"  ### 👈🏾👈🏾 Fix this alue !!!!!!!
StackName="${AppName}-devops-${TIER}-AWSSAM-sample"

AWSPROFILE=.. ..
AWSREGION=.. ..

\rm -rf .aws-sam/   ~/.aws-sam/   ~/node_modules/  ./src/node_modules/
(cd src;    \rm -rf package-lock.json;   npm install --include-dev)
sam build

sam deploy --stack-name "${StackName}"      \
     --parameter-overrides Tier=${TIER} AppName="${AppName}" DateTimeStamp=$(date +"%Y-%M-%dT%H:%M:%S")   \
    --capabilities CAPABILITY_NAMED_IAM  --no-confirm-changeset --on-failure DELETE \
    --profile ${AWSPROFILE} --region ${AWSREGION}
```

## Cleanup / destroy the stack

```bash
## sam deploy --guided
sam delete --no-prompts  --stack-name "${StackName}"  --profile ${AWSPROFILE} --region ${AWSREGION}
```

## TESTING the 𝜆 on Laptop/GFE

FYI - The `sam build` CLI installs dependencies defined in `src/package.json`, compiles TypeScript with esbuild, creates a deployment package, and saves it in the `.aws-sam/build` folder.

Test locally and invoke them with the `sam local invoke` command.

```bash
sam local invoke \
	--parameter-overrides Tier=${TIER} AppName="${AppName}" DateTimeStamp=$(date +"%Y-%M-%dT%H:%M:%S") \
	--event events/event.json  --profile ${AWSPROFILE} --region ${AWSREGION}
```

<HR/><HR/><HR/><HR/>
<BR/><BR/><BR/><BR/>

# Troubleshooting RDS-Proxy connection failure

https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy.troubleshooting.html#rds-proxy-verifying

https://repost.aws/knowledge-center/rds-proxy-connection-issues

https://repost.aws/knowledge-center/lambda-rds-database-proxy

? Did the RDS-Proxy connect to the Aurora-instance?<BR/>
```bash
DBProxyName="AWSTkt-backend-${TIER}-stateful-aurorav2-pg-16"

aws rds describe-db-proxy-targets --db-proxy-name ${DBProxyName} --profile ${AWSPROFILE} --region ${AWSREGION}
```

Is the DB-Proxy READY-to-accept client connections?<BR/>

```bash
aws rds describe-db-proxies --db-proxy-name ${DBProxyName} --profile ${AWSPROFILE} --region ${AWSREGION}

aws rds describe-db-proxy-target-groups --db-proxy-name ${DBProxyName} --profile ${AWSPROFILE} --region ${AWSREGION}
```

The Full Policy to be associated with the RDS-Proxy:

```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": "kms:Decrypt",
			"Resource": !Sub "arn:aws:kms:${AWS::Region}:${AWS::AccountId}:alias/aws/secretsmanager",
			"Condition": {
				"StringEquals": {
					"kms:ViaService": !Sub "secretsmanager.${AWS::Region}.amazonaws.com"
				}
			}
		},
		{
			"Sid": "VisualEditor1",
			"Effect": "Allow",
			"Action": [
				"secretsmanager:GetResourcePolicy",
				"secretsmanager:GetSecretValue",
				"secretsmanager:DescribeSecret",
				"secretsmanager:ListSecretVersionIds"
			],
			"Resource": [
        !Sub "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${DBA}",
        !Sub "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${DBU}"
      ]
		},
		{
			"Sid": "VisualEditor2",
			"Effect": "Allow",
			"Action": [
				"secretsmanager:GetRandomPassword",
				"secretsmanager:ListSecrets"
			],
			"Resource": "*"
		}
	]
}```

<HR/><HR/><HR/><HR/>
<BR/><BR/><BR/><BR/>

# APPENDIX: Pre-Requisites

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* Node.js - [Install Node.js 20](https://nodejs.org/en/), including the NPM package management tool.
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

<HR/>
<HR/>
<HR/>
<HR/>

# APPENDIX: If you have an API

The SAM CLI can also emulate your application's API. Use the `sam local start-api` to run the API locally on port 3000.

```bash
sam local start-api
curl http://localhost:3000/
```

The SAM CLI reads the application template to determine the API's routes and the functions that they invoke. The `Events` property on each function's definition includes the route and method for each path.

```yaml
      Events:
        MyApiMethod:
          Type: Api
          Properties:
            Path: /myapi
            Method: get
```

## About template.yaml

The application template uses AWS Serverless Application Model (AWS SAM) to define application resources. AWS SAM is an extension of AWS CloudFormation with a simpler syntax for configuring common serverless application resources such as functions, triggers, and APIs. For resources not included in [the SAM specification](https://github.com/awslabs/serverless-application-model/blob/master/versions/2016-10-31.md), you can use standard [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html) resource types.

## Fetch, tail, and filter Lambda function logs

To simplify troubleshooting, SAM CLI has a command called `sam logs`. `sam logs` lets you fetch logs generated by your deployed Lambda function from the command line. In addition to printing the logs on the terminal, this command has several nifty features to help you quickly find the bug.

`NOTE`: This command works for all AWS Lambda functions; not just the ones you deploy using SAM.

```bash
sam logs -n MyLambdaFunction --stack-name ${StackName} --tail
```

You can find more information and examples about filtering Lambda function logs in the [SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-logging.html).

## Unit tests

Tests are defined in the `src/tests` folder in this project. Use NPM to install the [Jest test framework](https://jestjs.io/) and run unit tests.

```bash
cd src
npm install
npm run test
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond this samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)
