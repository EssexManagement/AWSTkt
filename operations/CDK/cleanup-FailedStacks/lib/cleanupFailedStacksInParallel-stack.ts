import * as fs from 'fs';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as sfntask from 'aws-cdk-lib/aws-stepfunctions-tasks';

import * as constants from '../bin/constants';
import { info } from 'console';

//// NOTE: This StepFunc deletes Stacks in-parallel (unlike the other one in this cdk-project)

export class CleanupFailedStacksInParallel extends cdk.Stack {
constructor(scope: Construct, id: string,
    tier: string,
    aws_env: string,
    git_branch: string,
    props?: cdk.StackProps,
) {
    super(scope, id, props);

    //// --------------------------------------------------
    //// pre-requisites and constants

    const thisStepFuncNAME = "CleanupFAILEDStacksInParallel"
    // const thisStepFuncNAME = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, thisStepFuncName, constants.CDK_DEVOPS_COMPONENT_NAME )
    const secondOtherSfnNAME = "CleanupFAILEDStacksInSequence"

    //// --------------------------------------------------

    //// Add a new Stack Parameter to customize the StepFunc created in here.
    const cfnParam_StepFuncName = new cdk.CfnParameter(this, 'StepFuncName', {
        type: 'String',
        default: thisStepFuncNAME,
        description: "ATTENTION !! Not ARN.  Just name only."
    })

    //// Add a new Stack Parameter named "stepFuncToCleanupFailedStacksInSequence"
    const cfnParam_StepFuncToCleanupFailedStacksInSequence = new cdk.CfnParameter(this, 'StepFuncToCleanupFailedStacksInSequence', {
        type: 'String',
        default: secondOtherSfnNAME,
        description: "ATTENTION !! Not ARN.  Just name only.  The __OTHER__ StepFunction that works with this one.  The _OTHER_ one deletes Stacks in PARALLEL (unlike this one).",
    })

    const cfnParam_TIER = new cdk.CfnParameter(this, 'TIER', {
        type: 'String',
        default: tier,
        description: "dev|test|int|uat|prod or FEATURE/DEVELOPER-specific TIER",
    })

    const cfnParam_AWSEnv = new cdk.CfnParameter(this, 'AWSEnv', {
        type: 'String',
        default: aws_env,
        description: "dev|test|int|uat|prod only",
    })

    //// --------------------------------------------------
    //// other basic-resources

    const snsTopicName = constants.get_SNS_TOPICNAME(tier, git_branch)
    // generate the ARN-string given the snsTopicName, by dynamically incorporating the current AWS-AccountId and AWS-Region
    const topicArn = `arn:${cdk.Stack.of(this).partition}:sns:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${snsTopicName}`;
    const snsTopic = cdk.aws_sns.Topic.fromTopicAttributes(this, snsTopicName+"lookup", {topicArn});
    const genericCloudFormationArn = `arn:${cdk.Stack.of(this).partition}:cloudformation:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:*`;

    const taskSNSTopicSuccess = new sfn.CustomState(this, snsTopicName+"Success", { stateJson: {
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:sns:publish",
        // "Resource": "arn:aws:states:::sns:publish",  ### Warning! This does -NOT- allow a Subject field.
        "Parameters": {
            "Subject": `Success ✅ ${tier} TIER (${aws_env}) StepFn ${thisStepFuncNAME}`, //// ${cdk.Stack.of(this).stackName}
            // "Subject.$": `States.Format("Success ✅ ${tier}-TIER (${aws_env}) StepFn {}", sfn.JsonPath.stringAt("$$.StateMachine.Name"))`,
            "Message.$": "$",
            // "Message.$": States.JsonToString($),
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
    // const taskSNSTopicSuccess = new sfntask.SnsPublish(this, snsTopicName, {
    //     topic: snsTopic,
    //     // message: sfn.JsonPath.format(""),
    //     message: sfn.TaskInput.fromJsonPathAt("$"),
    // })
    const taskSNSTopicAborted = new sfn.CustomState(this, snsTopicName+"Aborted", { stateJson: {
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:sns:publish",
        // "Resource": "arn:aws:states:::sns:publish",  ### Warning! This does -NOT- allow a Subject field.
        "Parameters": {
            "Subject": `!! FAILURE ❌❌ !! ${tier} TIER (${aws_env}) StepFn ${thisStepFuncNAME}`, //// ${cdk.Stack.of(this).stackName}
            "Message.$": "$",
            "TopicArn": snsTopic.topicArn,
        },
    }})

    const secondOtherSfnARN = `arn:${cdk.Stack.of(this).partition}:states:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:stateMachine:${secondOtherSfnNAME}`
    const secondOtherStepFn = cdk.aws_stepfunctions.StateMachine.fromStateMachineName(this, secondOtherSfnNAME, secondOtherSfnNAME)
    console.log(`Other StepFunc='${secondOtherStepFn.stateMachineArn}'`)

    //// --------------------------------------------------

    var logGroup = null;
    // if (tier == constants.DEV_TIER || tier == constants.INT_TIER) {
    //     //// Why?  cuz in DEVINT .. ..
    //     ////     AWS::Logs::ResourcePolicy: "Resource limit exceeded"
    //     logGroup = new cdk.aws_logs.LogGroup(this, thisStepFuncNAME+"-Logs", {
    //       logGroupName: "/aws/vendedlogs/states/"+thisStepFuncNAME,
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
    const succeedInMap = new sfn.Pass(this, "All OK inside Map!")
    const fail = new sfn.Fail(this, "Failure!")
    const failureInsideMap = new sfn.Fail(this, "FailureInsideMap!")

    const prepForStartSyncExecutionOfOtherStepFunc = new sfn.Pass(this, "Prep for StartSyncExecution", {
        inputPath: "$$.Execution.Input.SNSTopicName",
        resultPath: "$.currentItem.SNSTopicName",
        comment: "Before moving forward to StartSyncExecution task(below),_ENHANCE_ the INPUT-JSON, by inserting the SNS-Topic-Name (at appropriate location) for use by the other StepFunction.",
    });

    const extractStackNameFromArray_1 = new sfn.Pass(this, "extract StackName from input # 1", {
        outputPath: "$.StackDetails.Stacks[0].StackName",
    });

    const extractStackNameFromArray_2 = new sfn.Pass(this, "extract StackName from input # 2", {
        outputPath: "$.StackDetails.Stacks[0].StackName",
    });

    const deleteStack = new sfn.CustomState(this, "DELETE One-Single stack (as part of set of parallel deletionS)", {
        stateJson: {
            "Type": "Task",
            "Resource": "arn:aws:states:::aws-sdk:cloudformation:deleteStack",
            "Parameters": { "StackName.$": "$" },
            "ResultPath": null,
        }
    })

    const describeStack = new sfn.CustomState(this, "describe stack's status, specifically whether its successfully-deleted", {
        stateJson: {
            "Type": "Task",
            "Resource": "arn:aws:states:::aws-sdk:cloudformation:describeStacks",
            "Parameters": { "StackName.$": "$" },
            "ResultSelector": { "StackDetails.$": "$" },
            // "ResultPath": "$.StackDetails",
        }
    })

    const invokeOtherStepFunc = new sfn.CustomState(this, "Invoke "+secondOtherSfnNAME, {
        stateJson: {
            "Type": "Task",
            "Resource": "arn:aws:states:::states:startExecution.sync:2",
            "Parameters": {
                "StateMachineArn": secondOtherSfnARN,
                "Input.$": "$"
            },
            "Comment": "Assuming this current-item is a JSON for SEQUENTIAL-deletion of Stacks, then .. invoke the other StepFn to delete them in SEQUENCE",
            "ResultPath": null,
        }
    })

    //// --------------------------------------------------

    const whetherJsonParallelIsPresent = new sfn.Choice(this, "Is an array-json Input present?",
        { comment: "Within Input, '$.cleanupFailedStksParallel' is present" }
    );

    const isItAStackNameOrJSON = new sfn.Choice(this, "StackName or JSON?",
        { comment: "If Input to _MAP_ State is NOT a simple-string (perhaps it's JSON for deleting Stacks in SEQUENCE-or-PARALLEL??)", }
    )

    const ifNoSuchStack = new sfn.Choice(this, "if No such Stack?" )

    const ifDeleteStackInProgress = new sfn.Choice(this, "is delete-Stack in-progress?" )

    const waitAfterDeletingOneSingleStack = new sfn.Wait(this, "wait-state-1 after DELETING one-single stack", {
        time: sfn.WaitTime.duration(cdk.Duration.seconds(10)),
        comment: "Wait between DeleteStack & DescribeStack commands, cuz StepFn is very fast.",
    })

    const waitBetweenStatusChecksForStackDelete = new sfn.Wait(this, "wait-state-2 between STATUS-CHECKS for Stack-Delete", {
        time: sfn.WaitTime.duration(cdk.Duration.seconds(15)),
        comment: "Wait between STATUS-CHECKS for Stack-Delete.",
    })

    //// --------------------------------------------------

    const mapTask = new sfn.Map(this, "Map", {
        itemsPath: "$.cleanupFailedStksParallel",
        maxConcurrency: 9,
        // parameters: {
        //   "counter.$": "$$.Map.Item.Index",
        //   "cleanupFailedStksParallel.$": "$$.Map.Item.Value"
        // },
        // resultPath: "$.cleanupFailedStksParallel",
    })

    //// --------------------------------------------------

    whetherJsonParallelIsPresent.when( sfn.Condition.isPresent("$.cleanupFailedStksParallel"), mapTask )
    whetherJsonParallelIsPresent.otherwise( taskSNSTopicAborted )

    isItAStackNameOrJSON.when( sfn.Condition.isString("$"),
        describeStack, //// 1st let's check if it is in failed-state.
        { comment: "If currentItem is a simple string, then proceed to deleting the Stack whose name it is.", }
    )
    isItAStackNameOrJSON.otherwise( invokeOtherStepFunc )

    ifNoSuchStack.when(
        sfn.Condition.stringMatches("$.Cause", "Stack with id * does not exist (Service: CloudFormation, Status Code: 400, Request ID*"), //// RegExp alert!  Do Not touch this hardcoded string.
        succeedInMap,
        { comment: "If such a stack does NOT exist, this stepFn(or something else) successfully deleted this stack!", }
    )
    ifNoSuchStack.otherwise( failureInsideMap )

    describeStack.next(ifDeleteStackInProgress)
    describeStack.addCatch(ifNoSuchStack, {  //// do NOT abort! Continue w/ StepFunction!!!
        errors: [ "States.ALL",  ],
        resultPath: "$",
    })

    ifDeleteStackInProgress.when(
        sfn.Condition.or(
            // sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "CREATE_COMPLETE"),
            // sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "CREATE_IN_PROGRESS"),
            sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "DELETE_IN_PROGRESS"),
            sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "ROLLBACK_IN_PROGRESS"),
            sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS"),
        ),
        extractStackNameFromArray_1,
        { comment: "NOT-completed!", }
    )
    ifDeleteStackInProgress.when(
        sfn.Condition.or(
            sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "CREATE_FAILED"),
            sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "UPDATE_FAILED"),
            sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "DELETE_FAILED"),
            sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "ROLLBACK_FAILED"),
            sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "ROLLBACK_COMPLETE"),
            sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "UPDATE_ROLLBACK_COMPLETE"),
            sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "UPDATE_ROLLBACK_FAILED"),
            sfn.Condition.stringEquals("$.StackDetails.Stacks[0].StackStatus", "IMPORT_ROLLBACK_FAILED"),
        ),
        extractStackNameFromArray_1,
        { comment: "Ok! Failed-stack found. Wipe it out.", }
    )
    ifDeleteStackInProgress.otherwise( succeedInMap )

    extractStackNameFromArray_1.next(deleteStack)

    deleteStack.next(waitAfterDeletingOneSingleStack)
    deleteStack.addCatch(failureInsideMap, {
        errors: [ "States.ALL" ],
        // resultPath: "$",
    })

    invokeOtherStepFunc.next(succeedInMap)
    invokeOtherStepFunc.addCatch(failureInsideMap, {
        errors: [ "States.ALL" ],
        // resultPath: "$.error"+secondOtherSfnNAME,
    })

    mapTask.itemProcessor(isItAStackNameOrJSON)
    // mapTask.next(succeed)
    mapTask.next(taskSNSTopicSuccess)
    mapTask.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        // resultPath: "$.errordescribeStack",
    })

    waitAfterDeletingOneSingleStack.next(describeStack)
    waitBetweenStatusChecksForStackDelete.next(extractStackNameFromArray_2)

    extractStackNameFromArray_2.next(describeStack)

    taskSNSTopicSuccess.next(succeed)
    taskSNSTopicAborted.next(fail)

  //// --------------------------------------------------
    const stmc = new sfn.StateMachine(this, thisStepFuncNAME, {
        stateMachineName: thisStepFuncNAME,
        comment: "Given an ARRAY of Strings (StackNames) under the JSON-element named 'cleanupFailedStksParallel:', this will trigger 'DeleteStack()' AWS-API calls.. .. in Parallel.  If any of the Array-items are NOT simple-strings (assumed to be JSON), it will trigger the COMPANION StepFunction (to delete the stacks-inside-that-JSON .. in PARALLEL).  Pass a 'SNSTopic:' topmost element as part of the Input-json, to dynamically configure where you receive error notifications.",
        definitionBody: sfn.DefinitionBody.fromChainable(whetherJsonParallelIsPresent),
        timeout: cdk.Duration.seconds(3 * 3600), //// invoke Backend-CodePipeline + Run above Lambdas + Frontend-CodePipeline + wait for BDDs.
        logs: logGroup ? { level: sfn.LogLevel.ALL, includeExecutionData: true, destination: logGroup } : undefined,
        tracingEnabled: true,
        removalPolicy: cdk.RemovalPolicy.DESTROY,
    })

    //// ---------------------------------------------------
    // add inline policy to existing IAM-Role of stmc, to allow stmc to invoke the 3 Lambdas
    snsTopic.grantPublish(stmc.role)

    stmc.addToRolePolicy(new cdk.aws_iam.PolicyStatement({
        sid: "AllowInvokeSecondStepFn",
        actions: [ 'states:StartExecution', ],
        resources: [ secondOtherSfnARN, ],
    }))

    stmc.addToRolePolicy(new cdk.aws_iam.PolicyStatement({
        sid: "AllowStepFuncToDoAnyCloudFormationAction",
        actions: [ 'cloudformation:*', ],
        resources: [ genericCloudFormationArn, ],
    }))

    //// CloudFormation DEPLOY error:-
    ////        Resource handler returned message: "'arn:aws:iam::123456789012:role/emfact-devops-dev-Cleanup-CleanupFAILEDStacksInPara-nsBdyJYCLR3n'
    ////        is not authorized to create managed-rule.
    ////        (Service: AWSStepFunctions; Status Code: 400; Error Code: AccessDeniedException
    stmc.addToRolePolicy(new cdk.aws_iam.PolicyStatement({
        sid: "allowCreateManagedRule",
        actions: [
            "events:PutTargets",
            "events:PutRule",
            "events:DescribeRule",
        ],
        resources: [cdk.Fn.sub("arn:${AWS::Partition}:events:${AWS::Region}:${AWS::AccountId}:rule/StepFunctionsGetEventsForStepFunctionsExecutionRule")],
    }))

    //// WARNING: The following grant() by the logGroup does NOT seem to work!!!
    // logGroup.grant(stmc.role, 'logs:CreateLogStream', 'logs:PutLogEvents') //// since log-group is already-created at top of file, no need for 'logs:CreateLogGroup'
    // if (logGroup) { logGroup.grantWrite(stmc.role) }

} //// constructor
} //// class
