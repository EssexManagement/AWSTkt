import * as fs from 'fs';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as sfntask from 'aws-cdk-lib/aws-stepfunctions-tasks';

import * as constants from '../bin/constants';
import { error } from 'console';

export class OneClickEnd2EndStack extends cdk.Stack {
constructor(scope: Construct,
    simpleStackName: string,
    fullStackName: string,
    tier:string,
    git_branch:string,
    props?: cdk.StackProps,
) {
    super(scope, fullStackName, props);

    //// --------------------------------------------------
    //// pre-requisites and constants

    const stmc_name = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, "sfn-"+simpleStackName, constants.CDK_COMPONENT_NAME )
    const codepipelineSourceStageActionName = "BIAD_emFACT-frontend-cdk.git" //// Click on "View Details" under Source-STAGE of codepipeline

    //// --------------------------------------------------
    let preDeploySfnName = "sfn-CleanupStacks"
    //// let preDeploySfnName = "sfn-PRE-deployment"
    preDeploySfnName = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, preDeploySfnName, constants.CDK_COMPONENT_NAME )
    const preDeploySfn = cdk.aws_stepfunctions.StateMachine.fromStateMachineName(this, preDeploySfnName, preDeploySfnName)
    console.log(`preDeploySfn='${preDeploySfn}'`)

    let postBackendDeploySfnName = "sfn-PostDeployment"
    postBackendDeploySfnName = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, postBackendDeploySfnName, constants.CDK_COMPONENT_NAME )
    const postBackendDeploySfn = cdk.aws_stepfunctions.StateMachine.fromStateMachineName(this, postBackendDeploySfnName, postBackendDeploySfnName)
    console.log(`postBackendDeploySfn='${postBackendDeploySfn}'`)

    let componentName = "frontend"
    const frontendCodePipelineName = `${constants.CDK_APP_NAME}-${componentName}-pipeline-${tier}`;
    const frontendCodePipeline = cdk.aws_codepipeline.Pipeline.fromPipelineArn(this, frontendCodePipelineName,
              `arn:${cdk.Stack.of(this).partition}:codepipeline:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${frontendCodePipelineName}`    )
    console.log(`frontendCodePipeline='${frontendCodePipeline}'`)

    componentName = "backend"
    const backendCodePipelineName = `${constants.CDK_APP_NAME}-${componentName}-pipeline-${tier}`;
    const backendCodePipeline = cdk.aws_codepipeline.Pipeline.fromPipelineArn(this, backendCodePipelineName,
              `arn:${cdk.Stack.of(this).partition}:codepipeline:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${backendCodePipelineName}`     )
    console.log(`backendCodePipeline='${backendCodePipeline}'`)

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
    //       logGroupName: "/aws/vendedlogs/states/"+stmc_name,
    //       removalPolicy : cdk.RemovalPolicy.DESTROY,
    //       retention: cdk.aws_logs.RetentionDays.TWO_MONTHS,
    //       logGroupClass: cdk.aws_logs.LogGroupClass.INFREQUENT_ACCESS,
    //     })
    //     //// Apparently, by the time the StepFunc is being created/deployed, it should --ALREADY-- have permissions to write to this logs-group !!!!
    //     logGroup.addToResourcePolicy(new cdk.aws_iam.PolicyStatement({
    //       principals: [new cdk.aws_iam.ServicePrincipal('states.amazonaws.com')],
    //       actions: ['logs:CreateLogStream', 'logs:PutLogEvents'],
    //       resources: ['*'],
    //     }))
    // }

    //// --------------------------------------------------
    const succeed = new sfn.Succeed(this, "All OK!")
    const fail = new sfn.Fail(this, "Failure!")

    // const incrementInnerLoopCounter = new sfn.Pass(this, "Increment Inner-Loop-Counter only", {
    //   parameters: {
    //     "inner_loop_counter.$": sfn.JsonPath.mathAdd( sfn.JsonPath.numberAt("$.inner_loop_counter"), 1), //// scalar
    //     "outer_loop_counter.$": "$.outer_loop_counter",
    //   },
    //   // result: { "value": sfn.JsonPath.mathAdd( sfn.JsonPath.numberAt("$.inner_loop_counter"), 1), }, //// did NOT work.
    //   // result: { "value": { "inner_loop_counter.$": sfn.JsonPath.mathAdd( sfn.JsonPath.numberAt("$.inner_loop_counter"), 1), }}, //// json.  DID NOT WORK!!!
    //   // result: sfn.Result.fromString( sfn.JsonPath.mathAdd(sfn.JsonPath.numberAt('$.inner_loop_counter'), 1) ), //// <--- did NOT work.
    //   // result: sfn.Result.fromObject({"v.$": sfn.JsonPath.mathAdd(sfn.JsonPath.numberAt('$.inner_loop_counter'), 1) }), //// <--- did NOT work.
    //   resultPath: "$.inner_loop_counter",
    //   comment: "Increment the inner-loop-counter, while retaining rest of Task's input as-is",
    // });

    const deployBackend = new sfn.CustomState(this, "start "+backendCodePipelineName+" only",{ stateJson: {
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:codepipeline:startPipelineExecution",
        "Parameters": { //// REF: https://docs.aws.amazon.com/codepipeline/latest/APIReference/API_StartPipelineExecution.html
            "Name": backendCodePipelineName,
            // "ClientRequestToken.$": "$$.Execution.Id",
            // "sourceRevisions": [{ //// REF: https://docs.aws.amazon.com/codepipeline/latest/APIReference/API_SourceRevisionOverride.html
            //                       //// Java REF: https://sdk.amazonaws.com/java/api/latest/software/amazon/awssdk/services/codepipeline/model/SourceRevisionOverride.Builder.html
            //   "actionName": codepipelineSourceStageActionName, ///
            //   "revisionType": "COMMIT_ID", //// Valid Values: COMMIT_ID | IMAGE_DIGEST | S3_OBJECT_VERSION_ID | S3_OBJECT_KEY
            //   "revisionValue": "main | v2.3.4 | dev"
            // }],
            // "variables": [
            //   { "name": "CODEPIPELINE_VARIABLE_ONE", "value": "dummyvalue_1" },
            //   { "name": "CODEPIPELINE_VARIABLE_TWO", "value": "dummyvalue_2" },
            // ]
        },
        "ResultPath": "$."+backendCodePipelineName,
    }})

    const deployFrontend = new sfn.CustomState(this, "start "+frontendCodePipelineName+" only",{ stateJson: {
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:codepipeline:startPipelineExecution",
        "Parameters": { "Name": frontendCodePipelineName },
        "ResultPath": "$."+frontendCodePipelineName,
    }})

    const getStatusOfDeployBackend = new sfn.CustomState(this, "get status-of "+backendCodePipelineName+" only",{ stateJson: {
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:codepipeline:getPipelineExecution",
        "Parameters": {
            "PipelineExecutionId.$": "$."+backendCodePipelineName+".PipelineExecutionId",
            "PipelineName": backendCodePipelineName
        },
        "ResultSelector": { "Status.$": "$.PipelineExecution.Status" },
        "ResultPath": "$.Status"+backendCodePipelineName,
    }})

    const getStatusOfDeployFrontend = new sfn.CustomState(this, "get status-of "+frontendCodePipelineName+" only",{ stateJson: {
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:codepipeline:getPipelineExecution",
        "Parameters": {
            "PipelineExecutionId.$": "$."+frontendCodePipelineName+".PipelineExecutionId",
            "PipelineName": frontendCodePipelineName
        },
        "ResultSelector": { "Status.$": "$.PipelineExecution.Status" },
        "ResultPath": "$.Status"+frontendCodePipelineName,
    }})

    // write a CustomTask that invokes AWSInspector2 SDK for ListFindings, filtered for "findingType" == "CRITICAL"
    //// https://docs.aws.amazon.com/inspector/v2/APIReference/API_ListFindings.html
    const invokeAWSInspector2FindingsAPI = new sfn.CustomState(this, "invoke AWSInspector2 SDK for ListFindings, filtered for CRITICAL", { stateJson: {
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:inspector2:listFindings",
        "Parameters": {
            "FilterCriteria": {
                "AwsAccountId": [{ "Comparison": "EQUALS", "Value": this.account }],
                            /// Comparison functions: EQUALS | PREFIX | NOT_EQUALS  --> https://docs.aws.amazon.com/inspector/v2/APIReference/API_StringFilter.html#inspector2-Type-StringFilter-comparison
                "LambdaFunctionName": [{ "Comparison": "PREFIX", "Value": constants.CDK_APP_NAME }],
                "Severity": [
                    //// INFORMATIONAL | LOW | MEDIUM | HIGH | CRITICAL | UNTRIAGED
                    { "Comparison": "EQUALS", "Value": "CRITICAL" },
                    { "Comparison": "EQUALS", "Value": "HIGH" },
                    // { "Comparison": "EQUALS", "Value": "MEDIUM" }
                ],
                "FindingStatus": [{ "Comparison": "EQUALS", "Value": "ACTIVE" }],  //// ACTIVE | SUPPRESSED | CLOSED
            },
            "MaxResults": 10,  /// anything more than 1 finding that is CRITICAL|HIGH .. is trouble.
        },
        "ResultPath": "$.AWSInspector2",
    }})

    //// --------------------------------------------------
    // Create a StepFunction task to invoke another StateMachine called 'preDeploySfn' in a Synchronous manner
    const preDeploySfnInvoke = new sfntask.StepFunctionsStartExecution(this, "Invoke "+preDeploySfnName, {
        comment: "invoke a statemachine that will wipe-out Failed-stacks (as well as, optionally, successful-stacks) in this tier: "+tier,
        // name: this is the NAME of the Execution!!!  And must be GLOBALLY-unique across all of AWS-Account.
        // Set "name" to the Execution-Id of the current StepFunction's execution
        stateMachine: preDeploySfn,
        // associateWithParent: true, //// ERROR: Could not enable `associateWithParent` because `input` is taken directly from a JSON path. Use `sfn.TaskInput.fromObject` instead.
        integrationPattern: sfn.IntegrationPattern.RUN_JOB, /// The right way to synchronously invoke another StepFunc.
        input: sfn.TaskInput.fromJsonPathAt("$"),
        resultPath: "$."+preDeploySfnName,
    })

    // Somehow some stacks are NOT deleted by `DeleteStacksInParallel`.  Unknown cause. Bandage-fix: Re-run above StepFn.
    const preDeploySfnInvoke_again = new sfntask.StepFunctionsStartExecution(this, "Invoke-2nd "+preDeploySfnName, {
        comment: "invoke (2nd time) statemachine that will wipe-out Failed-stacks (as well as, optionally, successful-stacks) in this tier: "+tier,
        stateMachine: preDeploySfn,
        integrationPattern: sfn.IntegrationPattern.RUN_JOB, /// The right way to synchronously invoke another StepFunc.
        input: sfn.TaskInput.fromJsonPathAt("$"),
        resultPath: "$."+preDeploySfnName+"2nd",
    })

    let jsonDataPostDep = fs.readFileSync('./lib/input-to-PostSeploy-sfn.json', 'utf8');
    jsonDataPostDep = jsonDataPostDep.replace(/{tier}/g, tier)
    console.log(jsonDataPostDep);
    const jsonObjectPostDep = JSON.parse(jsonDataPostDep); // Parse the JSON data into a JavaScript object
    console.log(jsonObjectPostDep);

    // Create a StepFunction task to invoke another StateMachine called 'postBackendDeploySfn' in a Synchronous manner
    const postBackendDeploySfnInvoke = new sfntask.StepFunctionsStartExecution(this, "Invoke "+postBackendDeploySfnName, {
        comment: "invoke ANOTHER statemachine that will hydrate the database",
        // name: this is the NAME of the Execution!!!  And must be GLOBALLY-unique across all of AWS-Account.
        // Set "name" to the Execution-Id of the current StepFunction's execution
        stateMachine: postBackendDeploySfn,
        // associateWithParent: true, //// ERROR: Could not enable `associateWithParent` because `input` is taken directly from a JSON path. Use `sfn.TaskInput.fromObject` instead.
        integrationPattern: sfn.IntegrationPattern.RUN_JOB, /// The right way to synchronously invoke another StepFunc.
        input: sfn.TaskInput.fromObject(jsonObjectPostDep),
        // input: sfn.TaskInput.fromJsonPathAt("$"),
        resultPath: "$."+postBackendDeploySfnName,
    })

    let jsonDataPostDepWipeCleanDB = fs.readFileSync('./lib/input-to-PostSeploy-sfn-WipeCleanDB.json', 'utf8');
    jsonDataPostDepWipeCleanDB = jsonDataPostDepWipeCleanDB.replace(/{tier}/g, tier)
    console.log(jsonDataPostDepWipeCleanDB);
    const jsonObjectPostDepWipeCleanDB = JSON.parse(jsonDataPostDepWipeCleanDB); // Parse the JSON data into a JavaScript object
    console.log(jsonObjectPostDepWipeCleanDB);

    // Create a StepFunction task to invoke another StateMachine called 'postBackendDeploySfn' in a Synchronous manner
    const postBackendDeploySfnWipeCleanDBInvoke = new sfntask.StepFunctionsStartExecution(this, "Invoke "+postBackendDeploySfnName +"-WipeCleanDB", {
        comment: "invoke ANOTHER statemachine that will initialize the Database and hydrate it (WipeCleanDB)",
        // name: this is the NAME of the Execution!!!  And must be GLOBALLY-unique across all of AWS-Account.
        // Set "name" to the Execution-Id of the current StepFunction's execution
        stateMachine: postBackendDeploySfn,
        // associateWithParent: true, //// ERROR: Could not enable `associateWithParent` because `input` is taken directly from a JSON path. Use `sfn.TaskInput.fromObject` instead.
        integrationPattern: sfn.IntegrationPattern.RUN_JOB, /// The right way to synchronously invoke another StepFunc.
        input: sfn.TaskInput.fromObject(jsonObjectPostDepWipeCleanDB),
        // input: sfn.TaskInput.fromJsonPathAt("$"),
        resultPath: "$."+postBackendDeploySfnName,
    })

    //// --------------------------------------------------
    // Check whether All of the CodePipeline Executions have ended for the specific pipeline named "postBackendDeploySfnName"
    const waitAfterFrontendCodePipelineExecution = new sfn.Wait(this, "wait-state-1 after STARTING Pipeline "+frontendCodePipelineName, {
        time: sfn.WaitTime.duration(cdk.Duration.seconds(300)),
        comment: `after kicking OFF Pipeline ${frontendCodePipelineName} .. wait-in-loop to check if Pipeline ended`,
    })

    // Check whether All of the CodePipeline Executions have ended for the specific pipeline named "postBackendDeploySfnName"
    const waitAfterBackendCodePipelineExecution = new sfn.Wait(this, "wait-state-2 after STARTING Pipeline "+backendCodePipelineName, {
        time: sfn.WaitTime.duration(cdk.Duration.seconds(300)),
        comment: `after kicking OFF Pipeline ${backendCodePipelineName} .. wait-in-loop to check if Pipeline ended`,
    })

    // const waitAfterFirstLambdaFails = new sfn.Wait(this, "wait-state-1 after failure of "+bucketWipeoutLambdaName, {
    //     time: sfn.WaitTime.duration(cdk.Duration.seconds(60)),
    //     comment: "If 1st-Lambda failed, then wait a minute before starting all over again",
    // })

    const checkBackendPipelineStatus = new sfn.Choice(this, "What is "+backendCodePipelineName+" Pipeline Status");
    const checkWhetherToDeployFrontend = new sfn.Choice(this, "Skip "+frontendCodePipelineName+" DEPLOY-ment?");
    const checkFrontendPipelineStatus = new sfn.Choice(this, "What is "+frontendCodePipelineName+" Pipeline Status");
    const checkWhetherAnyAWSInspector2Findings = new sfn.Choice(this, "Any High+ AWS-Inspector Findings: cdk-hnb659fds-container-assets-");
    const whetherWipeCleanDB = new sfn.Choice(this, "Whether to WipeCleanDB during POST-Deploy SFn-invocation?", { comment: "post-deploy Sfn "+postBackendDeploySfnName+" .. whether it should WipeCleanDB when invoked?" })

    //// --------------------------------------------------
    preDeploySfnInvoke.next(preDeploySfnInvoke_again)
    //// for various FREAK-reasons, this stepfunction can fail.  So, retry it a 2nd time, this time any failure is bad.
    preDeploySfnInvoke.addCatch(preDeploySfnInvoke_again, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })

    // Somehow some stacks are NOT deleted by `DeleteStacksInParallel`.  Unknown cause. Bandage-fix: Re-run above StepFn.
    preDeploySfnInvoke_again.next(deployBackend)
    //// This is the 2nd retry; So, this time any failure is bad, and go to SNS-Aborted state.
    preDeploySfnInvoke_again.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })

    deployBackend.next(waitAfterBackendCodePipelineExecution)
    deployBackend.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })
    waitAfterBackendCodePipelineExecution.next(getStatusOfDeployBackend)
    getStatusOfDeployBackend.next(checkBackendPipelineStatus)
    getStatusOfDeployBackend.addCatch(taskSNSTopicAborted, {
      errors: [ "States.ALL" ],
      resultPath: "$.error",
    })

    checkBackendPipelineStatus.when(
        sfn.Condition.stringEquals("$.Status"+backendCodePipelineName+".Status", "InProgress"),
        waitAfterBackendCodePipelineExecution
    )
    checkBackendPipelineStatus.when(
        sfn.Condition.stringEquals("$.Status"+backendCodePipelineName+".Status", "Succeeded"),
        whetherWipeCleanDB
    )
    checkBackendPipelineStatus.otherwise( taskSNSTopicAborted )

    whetherWipeCleanDB.when(sfn.Condition.isPresent("$.run-rds-init"), postBackendDeploySfnWipeCleanDBInvoke )
    whetherWipeCleanDB.when(sfn.Condition.isPresent("$.runRdsInit"),   postBackendDeploySfnWipeCleanDBInvoke )
    whetherWipeCleanDB.otherwise( postBackendDeploySfnInvoke )

    postBackendDeploySfnInvoke.next(checkWhetherToDeployFrontend)
    postBackendDeploySfnInvoke.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })

    postBackendDeploySfnWipeCleanDBInvoke.next(checkWhetherToDeployFrontend)
    postBackendDeploySfnWipeCleanDBInvoke.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })

    checkWhetherToDeployFrontend.when(
        sfn.Condition.isPresent("$.skipFrontendDeployment"),
        invokeAWSInspector2FindingsAPI
    )
    checkWhetherToDeployFrontend.otherwise(deployFrontend)

    deployFrontend.next(waitAfterFrontendCodePipelineExecution)
    deployFrontend.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })
    waitAfterFrontendCodePipelineExecution.next(getStatusOfDeployFrontend)
    getStatusOfDeployFrontend.next(checkFrontendPipelineStatus)
    getStatusOfDeployFrontend.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        resultPath: "$.error",
    })

    checkFrontendPipelineStatus.when(
        sfn.Condition.stringEquals("$.Status"+frontendCodePipelineName+".Status", "InProgress"),
        waitAfterFrontendCodePipelineExecution,
    )
    checkFrontendPipelineStatus.when(
        sfn.Condition.stringEquals("$.Status"+frontendCodePipelineName+".Status", "Succeeded"),
        invokeAWSInspector2FindingsAPI,
    )
    checkFrontendPipelineStatus.otherwise( taskSNSTopicAborted )

    invokeAWSInspector2FindingsAPI.next( checkWhetherAnyAWSInspector2Findings )
    checkWhetherAnyAWSInspector2Findings.when(
        //// https://docs.aws.amazon.com/inspector/v2/APIReference/API_Finding.html#inspector2-Type-Finding-severity
        sfn.Condition.isPresent("$.AWSInspector2.Findings[0].Severity"),
        taskSNSTopicAborted
    )
    checkWhetherAnyAWSInspector2Findings.otherwise(taskSNSTopicSuccess)



    taskSNSTopicSuccess.next(succeed)
    taskSNSTopicAborted.next(fail)

    //// --------------------------------------------------
    const stmc = new sfn.StateMachine(this, stmc_name, {
        stateMachineName: stmc_name,
        comment: "Initiate Post-Deployment activities after completion of CI/CD pipeline(CodePipeline)",
        definitionBody: sfn.DefinitionBody.fromChainable(preDeploySfnInvoke),
        timeout: cdk.Duration.seconds(3 * 3600), //// invoke Backend-CodePipeline + Run above Lambdas + Frontend-CodePipeline + wait for BDDs.
        logs: logGroup ? { level: sfn.LogLevel.ALL, includeExecutionData: true, destination: logGroup } : undefined,
        tracingEnabled: true,
        removalPolicy: cdk.RemovalPolicy.DESTROY,
    })

    //// ---------------------------------------------------
    // add inline policy to existing IAM-Role of stmc, to allow stmc to invoke the 3 Lambdas
    stmc.addToRolePolicy(new cdk.aws_iam.PolicyStatement({
        sid: "AllowStepFuncToInvokeBothCodePipelines",
        actions: [
            'codepipeline:StartPipelineExecution',
            'codepipeline:RetryStageExecution', // in case BDDs fails, need the ability to wait a day and re-try.
            'codepipeline:GetJobDetails',
            'codepipeline:GetPipelineExecution',
            'codepipeline:ListPipelines',
            'codepipeline:ListTagsForResource',
            'codepipeline:TagResource',   // actually being used!!!
            'codepipeline:UntagResource', // actually being used!!!
            // 'codepipeline:PutApprovalResult', // !! future need !! where approval is done inside this End2End DevOps-flow
            // 'codepipeline:GetPipeline', // access to query the inner-details of a CodePipeline.
            // 'codepipeline:GetPipelineState',       //// With help of IAM Access-Analyzer, confirmed that this was NEVER used (1 month after this StepFn was created)
            // 'codepipeline:ListPipelineExecutions', //// With help of IAM Access-Analyzer, confirmed that this was NEVER used (1 month after this StepFn was created)
            // 'codepipeline:ListActionExecutions',   //// With help of IAM Access-Analyzer, confirmed that this was NEVER used (1 month after this StepFn was created)
            // 'codepipeline:StopPipelineExecution',  //// With help of IAM Access-Analyzer, confirmed that this was NEVER used (1 month after this StepFn was created)
        ],
        resources: [
            frontendCodePipeline.pipelineArn, // pipeline itself
            frontendCodePipeline.pipelineArn+'/*', // STAGE & ACTIONS of a pipeline
            backendCodePipeline.pipelineArn,  // pipeline itself
            backendCodePipeline.pipelineArn+'/*',  // STAGE & ACTIONS of a pipeline
        ],
    }))

    snsTopic.grantPublish(stmc.role)
    // FIX: error: not authorized to invoke inspector2:ListFindings on resource: arn:aws:inspector2:????:?????:/findings/list
    stmc.addToRolePolicy(new cdk.aws_iam.PolicyStatement({
        sid: "AllowAWSInspector2ListFindings",
        actions: ["inspector2:ListFindings"],
        resources: [`arn:${this.partition}:inspector2:${this.region}:${this.account}:/findings/list`]
    }))
    //// WARNING: The following grant() by the logGroup does NOT seem to work!!!
    // if (logGroup) { logGroup.grant(stmc.role, 'logs:CreateLogStream', 'logs:PutLogEvents') } //// since log-group is already-created at top of file, no need for 'logs:CreateLogGroup'
    // if (logGroup) { logGroup.grantWrite(stmc.role) }

} //// constructor
} //// class
