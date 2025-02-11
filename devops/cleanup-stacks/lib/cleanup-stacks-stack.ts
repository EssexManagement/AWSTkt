import * as fs from 'fs';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as sfntask from 'aws-cdk-lib/aws-stepfunctions-tasks';

import * as constants from '../bin/constants';
import { error } from 'console';

export class CleanupStacksStack extends cdk.Stack {
constructor(scope: Construct,
    simpleStackName: string,
    fullStackName: string,
    tier:string,
    git_branch:string,
    props?: cdk.StackProps,
){
    super(scope, fullStackName, props);

    //// --------------------------------------------------
    //// pre-requisites and constants

    const stmc_name = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, "sfn-"+simpleStackName, constants.CDK_COMPONENT_NAME )
    const codepipelineSourceStageActionName = "BIAD_emFACT-frontend-cdk.git" //// Click on "View Details" under Source-STAGE of codepipeline

    //// --------------------------------------------------
    const bucketWipeoutLambdaName = `wipeout-bucket-${tier}`
    const bucketWipeoutLambda = cdk.aws_lambda.Function.fromFunctionName(this, bucketWipeoutLambdaName, bucketWipeoutLambdaName)
    console.log(`2nd lambda_ref='${bucketWipeoutLambda}'`)

    const cleanupOrphanRsrcsSIMPLELambdaName = `CleanupOrphanResources`
    const cleanupOrphanRsrcsLambdaName = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, cleanupOrphanRsrcsSIMPLELambdaName, constants.CDK_COMPONENT_NAME )
    const cleanupOrphanRsrcsLambda = cdk.aws_lambda.Function.fromFunctionName(this, cleanupOrphanRsrcsLambdaName, cleanupOrphanRsrcsLambdaName)
    console.log(`2nd lambda_ref='${cleanupOrphanRsrcsLambda}'`)

    //// ---------------------
    let failedStackDestroyerSfnName = "CleanupFAILEDStacksInSequence";
    const failedStackDestroyerSfn = cdk.aws_stepfunctions.StateMachine.fromStateMachineName(this, failedStackDestroyerSfnName, failedStackDestroyerSfnName)
    console.log(`postDeploySfn='${failedStackDestroyerSfnName}'`)

    let deleteStacksOnRequestSfnName = "DeleteStacksInSequence";
    const deleteStacksOnRequestSfn = cdk.aws_stepfunctions.StateMachine.fromStateMachineName(this, deleteStacksOnRequestSfnName, deleteStacksOnRequestSfnName)
    console.log(`postDeploySfn='${deleteStacksOnRequestSfnName}'`)

    //// --------------------------------------------------
    //// other basic-resources

    const snsTopicName = constants.get_SNS_TOPICNAME(tier, git_branch)
    // generate the ARN-string given the snsTopicName, by dynamically incorporating the current AWS-AccountId and AWS-Region
    const topicArn = `arn:${cdk.Stack.of(this).partition}:sns:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${snsTopicName}`;
    const snsTopic = cdk.aws_sns.Topic.fromTopicAttributes(this, snsTopicName+"lookup", {topicArn});

    const taskSNSTopicSuccess = new sfn.CustomState(this, snsTopicName+"Success", { stateJson: {
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:sns:publish",
        // "Resource": "arn:aws:states:::sns:publish",  ### Warning! This does -NOT- allow a Subject field.
        "Parameters": {
            "Subject": `Success ✅ ${tier}-TIER StepFn ${stmc_name}`, //// ${cdk.Stack.of(this).stackName}
            // "Subject.$": `States.Format("Success ✅ ${tier}-TIER StepFn {}", sfn.JsonPath.stringAt("$$.StateMachine.Name"))`,
            "Message.$": "$",
            // "Message.$": `States.Format('!! FAILURE !! in {} TIER within {} AWS-environment for Project {} - StepFunction ${cdk.Stack.of(this).stackName}. {}', '${tier}', '${aws_env}', '${thisStepFuncNAME}', States.JsonToString($) )`,
            "TopicArn": snsTopic.topicArn,
            // "TopicArn.$": `States.Format('arn:${cdk.Stack.of(this).partition}:sns:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:{}', $$.Execution.Input.SNSTopicName )`,
            // "MessageAttributes": {
            //     "TIER": { "StringValue": tier, "DataType": "String" },
            //     "AWSEnv": { "StringValue": aws_env, "DataType": "String" },
            //     "Sender": { "StringValue": thisStepFuncNAME, "DataType": "String" },
            //     "CONTENT": { "StringValue.$": "States.JsonToString($)", "DataType": "String" }
            // },
        },
    }})
    const taskSNSTopicAborted = new sfn.CustomState(this, snsTopicName+"Aborted", { stateJson: {
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:sns:publish",
        // "Resource": "arn:aws:states:::sns:publish",  ### Warning! This does -NOT- allow a Subject field.
        "Parameters": {
            "Subject": `!! FAILURE ❌❌ !! ${tier}-TIER StepFn ${stmc_name}`, //// ${cdk.Stack.of(this).stackName}
            "Message.$": "$",
            "TopicArn": snsTopic.topicArn,
        },
    }})
    // const taskSNSTopicSuccess = new sfntask.SnsPublish(this, snsTopicName, {
    //     topic: snsTopic,
    //     // message: sfn.JsonPath.format(""),
    //     message: sfn.TaskInput.fromJsonPathAt("$"),
    //     subject: sfn.JsonPath.format( <------ "Subject" Not supported
    //         `Success✅ in ${tier} environment - StepFunction {} -- for ${fullStackName}.`,
    //         sfn.JsonPath.stringAt("$$.StateMachine.Name"),
    //     ),
    // })
    // const taskSNSTopicAborted = new sfntask.SnsPublish(this, snsTopicName+"Aborted", {
    //     topic: snsTopic,
    //     message: sfn.TaskInput.fromJsonPathAt("$"),
    //     subject: sfn.JsonPath.format( <------ "Subject" Not supported
    //         `!! FAILURE❌❌ !! in ${tier} environment - StepFunction {} -- for ${fullStackName}.`,
    //         sfn.JsonPath.stringAt("$$.StateMachine.Name"),
    //     ),
    // })

    var logGroup = null;
    // if (tier == constants.DEV_TIER || tier == constants.INT_TIER) {
    //     //// Why?  cuz in DEVINT .. ..
    //     ////     AWS::Logs::ResourcePolicy: "Resource limit exceeded"
    //     logGroup = new cdk.aws_logs.LogGroup(this, stmc_name+"-Logs", {
    //         logGroupName: "/aws/vendedlogs/states/"+stmc_name,
    //         removalPolicy : cdk.RemovalPolicy.DESTROY,
    //         retention: cdk.aws_logs.RetentionDays.TWO_MONTHS,
    //         logGroupClass: cdk.aws_logs.LogGroupClass.INFREQUENT_ACCESS,
    //     })
    //     //// Apparently, by the time the StepFunc is being created/deployed, it should --ALREADY-- have permissions to write to this logs-group !!!!
    //     logGroup.addToResourcePolicy(new cdk.aws_iam.PolicyStatement({
    //         principals: [new cdk.aws_iam.ServicePrincipal('states.amazonaws.com')],
    //         actions: ['logs:CreateLogStream', 'logs:PutLogEvents'],
    //         resources: ['*'],
    //     }))
    // }

    //// --------------------------------------------------
    const succeed = new sfn.Succeed(this, "All OK!")
    const fail = new sfn.Fail(this, "Failure!")

    //// --------------------------------------------------
    // read the contents of the json-file at "./input-to-cleaner-sfn.json" into a json object -- synchronously
    let jsonInput_FS = fs.readFileSync('./lib/input-to-cleanupFAILEDStacksStepFn.json', 'utf8');
    jsonInput_FS = jsonInput_FS.replace(/{tier}/g, tier)
    jsonInput_FS = jsonInput_FS.replace(/{SNSTopicName}/g, snsTopicName)
    jsonInput_FS = jsonInput_FS.replace(/{app}/g, constants.CDK_APP_NAME)
    console.log(jsonInput_FS);
    const jsonObjectFS = JSON.parse(jsonInput_FS); // Parse the JSON data into a JavaScript object
    console.log(jsonObjectFS);

    // Create a StepFunction task to invoke another StateMachine called 'postDeploySfn' in a Synchronous manner
    const failedStackDestroyerSfnInvoke = new sfntask.StepFunctionsStartExecution(this, "Invoke "+failedStackDestroyerSfnName, {
        comment: "invoke ANOTHER StepFn that'll wipe out -FAILED- stacks in this tier: "+tier,
        // name: this is the NAME of the Execution!!!  And must be GLOBALLY-unique across all of AWS-Account.
        // Set "name" to the Execution-Id of the current StepFunction's execution
        stateMachine: failedStackDestroyerSfn,
        // associateWithParent: true, //// ERROR: Could not enable `associateWithParent` because `input` is taken directly from a JSON path. Use `sfn.TaskInput.fromObject` instead.
        integrationPattern: sfn.IntegrationPattern.RUN_JOB, /// The right way to synchronously invoke another StepFunc.
        input: sfn.TaskInput.fromObject(jsonObjectFS),
        // input: sfn.TaskInput.fromJsonPathAt("$"),
        resultPath: "$."+failedStackDestroyerSfnName,
    })

    // read the contents of the json-file at "./input-to-..-sfn.json" into a json object -- synchronously
    let jsonInput_DeleteStateLESSStksOnly = fs.readFileSync('./lib/input-to-DeleteStateLESSStacks-StepFn.json', 'utf8');
    jsonInput_DeleteStateLESSStksOnly = jsonInput_DeleteStateLESSStksOnly.replace(/{tier}/g, tier)
    jsonInput_DeleteStateLESSStksOnly = jsonInput_DeleteStateLESSStksOnly.replace(/{SNSTopicName}/g, snsTopicName)
    jsonInput_DeleteStateLESSStksOnly = jsonInput_DeleteStateLESSStksOnly.replace(/{app}/g, constants.CDK_APP_NAME)
    console.log(jsonInput_DeleteStateLESSStksOnly);
    const jsonObject_DeleteStateLESSStksOnly = JSON.parse(jsonInput_DeleteStateLESSStksOnly); // Parse the JSON data into a JavaScript object
    console.log(jsonObject_DeleteStateLESSStksOnly);

    // read the contents of the json-file at "./input-to-..-sfn.json" into a json object -- synchronously
    let jsonInput_DeleteAppStksOnly = fs.readFileSync('./lib/input-to-DeleteAppStacks-StepFn.json', 'utf8');
    jsonInput_DeleteAppStksOnly = jsonInput_DeleteAppStksOnly.replace(/{tier}/g, tier)
    jsonInput_DeleteAppStksOnly = jsonInput_DeleteAppStksOnly.replace(/{SNSTopicName}/g, snsTopicName)
    jsonInput_DeleteAppStksOnly = jsonInput_DeleteAppStksOnly.replace(/{app}/g, constants.CDK_APP_NAME)
    console.log(jsonInput_DeleteAppStksOnly);
    const jsonObject_DeleteAppStksOnly = JSON.parse(jsonInput_DeleteAppStksOnly); // Parse the JSON data into a JavaScript object
    console.log(jsonObject_DeleteAppStksOnly);

    // read the contents of the json-file at "./input-to-cleaner-sfn.json" into a json object -- synchronously
    let jsonInput_DeleteAllStks_NOTpipelineStks = fs.readFileSync('./lib/input-to-DeleteAllStacks-StepFn.json', 'utf8');
    jsonInput_DeleteAllStks_NOTpipelineStks = jsonInput_DeleteAllStks_NOTpipelineStks.replace(/{tier}/g, tier)
    jsonInput_DeleteAllStks_NOTpipelineStks = jsonInput_DeleteAllStks_NOTpipelineStks.replace(/{SNSTopicName}/g, snsTopicName)
    jsonInput_DeleteAllStks_NOTpipelineStks = jsonInput_DeleteAllStks_NOTpipelineStks.replace(/{app}/g, constants.CDK_APP_NAME)
    console.log(jsonInput_DeleteAllStks_NOTpipelineStks);
    const jsonObject_DeleteAllStks_NOTpipelines = JSON.parse(jsonInput_DeleteAllStks_NOTpipelineStks); // Parse the JSON data into a JavaScript object
    console.log(jsonObject_DeleteAllStks_NOTpipelines);

    // read the contents of the json-file at "./input-to-cleaner-sfn.json" into a json object -- synchronously
    let jsonInput_DeleteAllStksInclPipelineStks = fs.readFileSync('./lib/input-to-DeleteAllStacksInclPipelineStks-StepFn.json', 'utf8');
    jsonInput_DeleteAllStksInclPipelineStks = jsonInput_DeleteAllStksInclPipelineStks.replace(/{tier}/g, tier)
    jsonInput_DeleteAllStksInclPipelineStks = jsonInput_DeleteAllStksInclPipelineStks.replace(/{SNSTopicName}/g, snsTopicName)
    jsonInput_DeleteAllStksInclPipelineStks = jsonInput_DeleteAllStksInclPipelineStks.replace(/{app}/g, constants.CDK_APP_NAME)
    console.log(jsonInput_DeleteAllStksInclPipelineStks);
    const jsonObject_DeleteAllStksInclPipelineStks = JSON.parse(jsonInput_DeleteAllStksInclPipelineStks); // Parse the JSON data into a JavaScript object
    console.log(jsonObject_DeleteAllStksInclPipelineStks);

    // Create a StepFunction task to delete Lambda-Stks + Layer-Stks ONLY -- in a Synchronous manner
    const deleteStateLESSStksOnlySfn = new sfntask.StepFunctionsStartExecution(this, "Invoke "+deleteStacksOnRequestSfnName+" StateLESSStks", {
        comment: "invoke ANOTHER StepFn that'll wipe out StateLESS stacks in this tier: "+tier,
        // name: this is the NAME of the Execution!!!  And must be GLOBALLY-unique across all of AWS-Account.
        // Set "name" to the Execution-Id of the current StepFunction's execution
        stateMachine: deleteStacksOnRequestSfn,
        // associateWithParent: true, //// ERROR: Could not enable `associateWithParent` because `input` is taken directly from a JSON path. Use `sfn.TaskInput.fromObject` instead.
        integrationPattern: sfn.IntegrationPattern.RUN_JOB, /// The right way to synchronously invoke another StepFunc.
        input: sfn.TaskInput.fromObject(jsonObject_DeleteStateLESSStksOnly),
        // input: sfn.TaskInput.fromJsonPathAt("$"),
        resultPath: "$."+deleteStacksOnRequestSfnName,
    })

    // Create a StepFunction task to delete Application-Stacks (--NOT-- Pipelines) -- in a Synchronous manner
    const deleteAppStksOnlySfn = new sfntask.StepFunctionsStartExecution(this, "Invoke "+deleteStacksOnRequestSfnName+" AppStks", {
        comment: "invoke ANOTHER StepFn that'll wipe out StateLESS stacks in this tier: "+tier,
        // name: this is the NAME of the Execution!!!  And must be GLOBALLY-unique across all of AWS-Account.
        // Set "name" to the Execution-Id of the current StepFunction's execution
        stateMachine: deleteStacksOnRequestSfn,
        // associateWithParent: true, //// ERROR: Could not enable `associateWithParent` because `input` is taken directly from a JSON path. Use `sfn.TaskInput.fromObject` instead.
        integrationPattern: sfn.IntegrationPattern.RUN_JOB, /// The right way to synchronously invoke another StepFunc.
        input: sfn.TaskInput.fromObject(jsonObject_DeleteAppStksOnly),
        // input: sfn.TaskInput.fromJsonPathAt("$"),
        resultPath: "$."+deleteStacksOnRequestSfnName,
    })

    // Create a StepFunction task to delete ALL Stks -INCLUDING- PipelineStks --  in a Synchronous manner
    const deleteAllStks_NOTpipeline = new sfntask.StepFunctionsStartExecution(this, "Invoke "+deleteStacksOnRequestSfnName+" WipeAll", {
        comment: "invoke ANOTHER StepFn that'll wipe out All-stacks (EXCEPT pipeline) incl. RDS,Cognito,DDB,S3 in this tier: "+tier,
        // name: this is the NAME of the Execution!!!  And must be GLOBALLY-unique across all of AWS-Account.
        // Set "name" to the Execution-Id of the current StepFunction's execution
        stateMachine: deleteStacksOnRequestSfn,
        // associateWithParent: true, //// ERROR: Could not enable `associateWithParent` because `input` is taken directly from a JSON path. Use `sfn.TaskInput.fromObject` instead.
        integrationPattern: sfn.IntegrationPattern.RUN_JOB, /// The right way to synchronously invoke another StepFunc.
        input: sfn.TaskInput.fromObject(jsonObject_DeleteAllStks_NOTpipelines),
        // input: sfn.TaskInput.fromJsonPathAt("$"),
        resultPath: "$."+deleteStacksOnRequestSfnName,
    })

    // Create a StepFunction task to delete ALL Stks -INCLUDING- PipelineStks --  in a Synchronous manner
    const deleteAllStksInclPipelineStksSfn = new sfntask.StepFunctionsStartExecution(this, "Invoke "+deleteStacksOnRequestSfnName+" WipeAllInclPipeline", {
        comment: "invoke ANOTHER StepFn that'll wipe out E V E R Y T H I N G (incl. pipeline-stacks) "+tier,
        // name: this is the NAME of the Execution!!!  And must be GLOBALLY-unique across all of AWS-Account.
        // Set "name" to the Execution-Id of the current StepFunction's execution
        stateMachine: deleteStacksOnRequestSfn,
        // associateWithParent: true, //// ERROR: Could not enable `associateWithParent` because `input` is taken directly from a JSON path. Use `sfn.TaskInput.fromObject` instead.
        integrationPattern: sfn.IntegrationPattern.RUN_JOB, /// The right way to synchronously invoke another StepFunc.
        input: sfn.TaskInput.fromObject(jsonObject_DeleteAllStksInclPipelineStks),
        // input: sfn.TaskInput.fromJsonPathAt("$"),
        resultPath: "$."+deleteStacksOnRequestSfnName,
    })

    // create a pass state that increments inner_loop_counter, while retaining rest of Task's input as-is
    let taskName = "parameterized but hardcoded inputs to this WipeOut-Bucket Lambda-task below"
    const taskInput = {
        "tier": tier,
        "bucket-name": `fact-frontend-${tier}-frontendcloudfrontlogging.*`,
        "only-empty-the-bucket": "any-value here is-fine" //// that is, we do NOT want the bucket destroyed.
    }
    let taskInputAsStringifiedJson = JSON.stringify(taskInput)
    // taskInputAsStringifiedJson = taskInputAsStringifiedJson.replace(/{/g, '\\{').replace(/}/g, '\\}') //// not needed .replace(/"/g, '\\"')
    console.log(`taskInputAsStringifiedJson='${taskInputAsStringifiedJson}'`)
    const setVariables = new sfn.CustomState(this, taskName,{ stateJson: {
        "Type": "Pass",
        "Parameters": {
            //// Do NOT touch the following line!
            "output.$": "States.JsonMerge($, States.StringToJson('"+taskInputAsStringifiedJson+"'), false)",
        },
        "OutputPath": "$.output", //// This line means, we'll FORGET about the input, and create WHOLE NEW output-of-this-Pass-Task.  That's why NO ResultPath!!
        "Comment": taskName,
    }})

    //// --------------------------------------------------
    const invokeBucketWipeoutLambda = new sfntask.LambdaInvoke(this, "invoke lambda: "+bucketWipeoutLambdaName, {
        lambdaFunction: bucketWipeoutLambda,
        taskTimeout: sfn.Timeout.duration(cdk.Duration.seconds(900)),
        // integrationPattern: sfn.IntegrationPattern.RUN_JOB,
        resultSelector: {"StatusCode.$": "$.StatusCode"}, //// HTTP Response-code
        // resultSelector: {"StatusCode.$": "$.Payload.statusCode"}, //// The JSON-response-body returned by 𝜆-func
        resultPath: "$.wipeout_bucket_lambda",
        // outputPath: sfn.JsonPath.format("$.1stLambda_{}_{}", sfn.JsonPath.stringAt("$.outer_loop_counter"), ,sfn.JsonPath.stringAt("$.inner_loop_counter")),
    });

    const invokeCleanupOrphanRsrcsLambda = new sfntask.LambdaInvoke(this, "invoke lambda: "+cleanupOrphanRsrcsLambdaName, {
        lambdaFunction: cleanupOrphanRsrcsLambda,
        taskTimeout: sfn.Timeout.duration(cdk.Duration.seconds(900)),
        // integrationPattern: sfn.IntegrationPattern.RUN_JOB,
        resultSelector: {"StatusCode.$": "$.StatusCode"}, //// HTTP Response-code
        // resultSelector: {"StatusCode.$": "$.Payload.statusCode"}, //// The JSON-response-body returned by 𝜆-func
        resultPath: "$.wipeout_bucket_lambda",
        // outputPath: sfn.JsonPath.format("$.1stLambda_{}_{}", sfn.JsonPath.stringAt("$.outer_loop_counter"), ,sfn.JsonPath.stringAt("$.inner_loop_counter")),
    });

    const sample_lambda_invoke_response = {
        "ExecutedVersion": "$LATEST",
        "StatusCode": 200,
        "Payload": {
            "statusCode": 200,
            "body": "{\"randomNumber\":579}"
        },
        "SdkHttpMetadata": {
            "HttpStatusCode": 200,
            "AllHttpHeaders": {
                "X-Amz-Executed-Version": [ "$LATEST" ],
                "x-amzn-Remapped-Content-Length": [ "0" ],
                "Connection": [ "keep-alive" ],
                "x-amzn-RequestId": [ "b37f1999-9659-4b55-abe3-83fd6d2862b2" ],
                "Content-Length": [ "50" ],
                "Date": [ "Tue, 23 Jul 2024 04:09:56 GMT" ],
                "X-Amzn-Trace-Id": [ "root=1-669f2d13-c6867523289ee374e75f22bf;parent=644a89f7bc5b683d;sampled=1" ],
                "Content-Type": [ "application/json" ]
            },
            "HttpHeaders": {
                "Connection": "keep-alive",
                "Content-Length": "50",
                "Content-Type": "application/json",
                "Date": "Tue, 23 Jul 2024 04:09:56 GMT",
                "X-Amz-Executed-Version": "$LATEST",
                "x-amzn-Remapped-Content-Length": "0",
                "x-amzn-RequestId": "b37f1999-9659-4b55-abe3-83fd6d2862b2",
                "X-Amzn-Trace-Id": "root=1-669f2d13-c6867523289ee374e75f22bf;parent=644a89f7bc5b683d;sampled=1"
            }
        },
        "SdkResponseMetadata": {
            "RequestId": "b37f1999-9659-4b55-abe3-83fd6d2862b2"
        },
    } //// End sample_lambda_invoke_response

    //// --------------------------------------------------

    const checkWhetherToCleanupFailedStacks = new sfn.Choice(this, "Whether to wipe-out -FAILED- Backend+Frontend stacks?");

    const checkWhetherToDeleteStateLESSStacksOnly = new sfn.Choice(this, "Whether to delete Lambdas+Layer stacks only");
    const checkWhetherToDeleteAppStacksOnly = new sfn.Choice(this, "Whether to delete (app-stacks only) Backend+Frontend stacks?");
    const checkWhetherToDeleteAllStksInclPipelineStks = new sfn.Choice(this, "Whether to delete EVERY stack incl. Pipeline-stacks?");
    const checkWhetherToDeleteAllStks_NOTpipeline = new sfn.Choice(this, "Whether to delete EVERY stack (But NOT Pipelines) incl. RDS,Cognito,DDB,S3?");
    const checkWhetherToDeleteFrontendStack = new sfn.Choice(this, "Whether JSON-input to this StepFunc requires deletion of Frontend-stack");

    //// --------------------------------------------------
    setVariables.next(checkWhetherToDeleteFrontendStack)

    const failedStacksOnlyInputFlag = [
        "$.cleanupfailedstack",
        "$.cleanupfailedstacks",
        "$.cleanup-failed-stack",
        "$.cleanup-failed-stacks",
        "$.Cleanup-Failed-Stacks",
        "$.cleanupFailedStack",
        "$.cleanupFailedStacks",
    ];
    const statelessStacksOnlyInputFlag = [
        "$.delete-stateless-stacks-only",
        "$.DeleteStateLESSStacksOnly",
        "$.destroy-stateless-stacks-only",
        "$.DestroyStateLESSStacksOnly",
    ]
    const appStacksOnlyInputFlag = [
        "$.delete-app-stacks-only",
        "$.DeleteAppStacksOnly",
        "$.destroy-app-stacks-only",
        "$.DestroyAppStacksOnly"
    ];
    const allStksBUTNOTPipelinesInputFlag = [
        "$.delete-all-stacks-NOT-pipelines",
        "$.DeleteAppStacksNOTPipelines",
        "$.destroy-all-stacks-NOT-pipelines",
        "$.DestroyAppStacksNOTPipelines"
    ];
    const everyStacksIncludingPipelinesInputFlag = [
        "$.delete-all-stacks-incl-pipepines",
        "$.DeleteAppStacksInclPipelines",
        "$.DeleteAppStacksInclPipelineStacks",
        "$.destroy-all-stacks-incl-pipepines",
        "$.destroy-all-stacks-incl-pipepine-stacks",
        "$.DestroyAppStacksInclPipelines",
        "$.DestroyAppStacksInclPipelineStacks"
    ];

    //// --- Whether JSON-input to this StepFunc requires deletion of Frontend-stack
    Object.values( [ ...appStacksOnlyInputFlag, ...allStksBUTNOTPipelinesInputFlag, ...everyStacksIncludingPipelinesInputFlag ] )
        .flat().forEach(path => {
            checkWhetherToDeleteFrontendStack.when( sfn.Condition.isPresent( path ), invokeBucketWipeoutLambda );
    });
    checkWhetherToDeleteFrontendStack.otherwise( checkWhetherToCleanupFailedStacks )

    //// Note: No point wiping-out the buckets, unless we're trying to destroy-stacks.
    invokeBucketWipeoutLambda.next(checkWhetherToCleanupFailedStacks)
    invokeBucketWipeoutLambda.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })

    //// --- any FAILED stacks?
    failedStacksOnlyInputFlag.forEach(path => {
        checkWhetherToCleanupFailedStacks.when( sfn.Condition.isPresent( path ), failedStackDestroyerSfnInvoke );
    });
    checkWhetherToCleanupFailedStacks.otherwise( checkWhetherToDeleteStateLESSStacksOnly )

    failedStackDestroyerSfnInvoke.next( checkWhetherToDeleteStateLESSStacksOnly )
    failedStackDestroyerSfnInvoke.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })

    //// --- All-stateLESS-Stacks (Just the Lambda-Stacks and Lambda-LAYER-stacks/Common-Stk)
    statelessStacksOnlyInputFlag.forEach(path => {
        checkWhetherToDeleteStateLESSStacksOnly.when( sfn.Condition.isPresent( path ), deleteStateLESSStksOnlySfn );
    });
    checkWhetherToDeleteStateLESSStacksOnly.otherwise( checkWhetherToDeleteAppStacksOnly )

    deleteStateLESSStksOnlySfn.next(taskSNSTopicSuccess)
    deleteStateLESSStksOnlySfn.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })

    //// --- All-APPLICATION-Stacks (--NOT-- pipelines)
    appStacksOnlyInputFlag.forEach(path => {
        checkWhetherToDeleteAppStacksOnly.when( sfn.Condition.isPresent( path ), deleteAppStksOnlySfn );
    });
    checkWhetherToDeleteAppStacksOnly.otherwise( checkWhetherToDeleteAllStks_NOTpipeline )

    deleteAppStksOnlySfn.next(taskSNSTopicSuccess)
    deleteAppStksOnlySfn.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })

    //// --- delete ALL stacks incl. RDS,Cognito,DDB,S3 .. but -NOT- the pipelines
    allStksBUTNOTPipelinesInputFlag.forEach(path => {
        checkWhetherToDeleteAllStks_NOTpipeline.when( sfn.Condition.isPresent( path ), deleteAllStks_NOTpipeline );
    });
    checkWhetherToDeleteAllStks_NOTpipeline.otherwise( checkWhetherToDeleteAllStksInclPipelineStks )

    deleteAllStks_NOTpipeline.next(taskSNSTopicSuccess)
    deleteAllStks_NOTpipeline.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })

    //// --- totally wipe out ALL stacks incl. pipelines
    everyStacksIncludingPipelinesInputFlag.forEach(path => {
        checkWhetherToDeleteAllStksInclPipelineStks.when( sfn.Condition.isPresent( path ), deleteAllStksInclPipelineStksSfn );
    });
    checkWhetherToDeleteAllStksInclPipelineStks.otherwise( invokeCleanupOrphanRsrcsLambda )

    deleteAllStksInclPipelineStksSfn.next(taskSNSTopicSuccess)
    deleteAllStksInclPipelineStksSfn.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })


    //// Note: "Orphan" is legally NOT feasible, -UNTIL- we -COMPLETE- (successfully) the above destroy-stacks States/Steps.
    invokeCleanupOrphanRsrcsLambda.next( succeed )
    invokeCleanupOrphanRsrcsLambda.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })

    taskSNSTopicSuccess.next(succeed)
    taskSNSTopicAborted.next(fail)

    //// --------------------------------------------------
    const stmc = new sfn.StateMachine(this, stmc_name, {
        stateMachineName: stmc_name,
        comment: "(Usage: PRE-Deployment activities) Cleanup failed-stacks; Destroy stacks in proper-order ON REQUEST only.",
        definitionBody: sfn.DefinitionBody.fromChainable(setVariables),
        timeout: cdk.Duration.seconds(3 * 3600), //// invoke Backend-CodePipeline + Run above Lambdas + Frontend-CodePipeline + wait for BDDs.
        logs: logGroup ? { level: sfn.LogLevel.ALL, includeExecutionData: true, destination: logGroup } : undefined,
        tracingEnabled: true,
        removalPolicy: cdk.RemovalPolicy.DESTROY,
    })

    snsTopic.grantPublish(stmc.role)
    //// WARNING: The following grant() by the logGroup does NOT seem to work!!!
    // if (logGroup) { logGroup.grant(stmc.role, 'logs:CreateLogStream', 'logs:PutLogEvents') } //// since log-group is already-created at top of file, no need for 'logs:CreateLogGroup'
    // if (logGroup) { logGroup.grantWrite(stmc.role) }

} //// constructor
} //// class
