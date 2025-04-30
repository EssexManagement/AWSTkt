import * as fs from 'fs';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as sfntask from 'aws-cdk-lib/aws-stepfunctions-tasks';

import * as constants from '../bin/constants';
import { info } from 'console';

//// NOTE: This StepFunc deletes Stacks in-SEQUENCE (unlike the other one in this cdk-project)

export class CleanupFailedStacksInSequence extends cdk.Stack {
constructor(scope: Construct, id: string,
    tier: string,
    aws_env: string,
    git_branch: string,
    props?: cdk.StackProps,
) {
    super(scope, id, props);

    //// --------------------------------------------------
    //// pre-requisites and constants

    // const thisStepFuncNAME = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, "sfn-cleanup-FAILED-stacks", constants.CDK_DEVOPS_COMPONENT_NAME )
    const thisStepFuncNAME       = "CleanupFAILEDStacksInSequence"
    const secondOtherSfnNAME = "CleanupFAILEDStacksInParallel"

    //// --------------------------------------------------

    //// Add a new Stack Parameter to customize the StepFunc created in here.
    const cfnParam_StepFuncName = new cdk.CfnParameter(this, 'StepFuncName', {
        type: 'String',
        default: thisStepFuncNAME,
        description: "ATTENTION !! Not ARN.  Just name only."
    })

    //// Add a new Stack Parameter named "stepFuncToCleanupFailedStacksInParallel"
    const cfnParam_StepFuncToCleanupFailedStacksInParallel = new cdk.CfnParameter(this, 'StepFuncToCleanupFailedStacksInParallel', {
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

    // const taskSNSTopicSuccess = new sfntask.SnsPublish(this, snsTopicName, {
    //     topic: snsTopic,
    //     // message: sfn.JsonPath.format(""),
    //     message: sfn.TaskInput.fromJsonPathAt("$"),
    // })
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
    const fail = new sfn.Fail(this, "Failure!")

    const initializeLoop = new sfn.Pass(this, "Initialize Loop", {
        parameters: {
            "cleanupFailedStksSequence.$": "$.cleanupFailedStksSequence",
            "counter": 0,
            "maxIterations.$": "States.ArrayLength($.cleanupFailedStksSequence)"
        },
        resultPath: "$",
        comment: "set counter to zero and identity MAX # of iterations and identify which stacks to act on",
    });

    const lookAtCurrentItemInArray = new sfn.Pass(this, "look at CURRENT item in Array", {
        parameters: {
            "cleanupFailedStksSequence.$": "$.cleanupFailedStksSequence",
            "counter.$": "$.counter",
            "maxIterations.$": "$.maxIterations",
            "currentItem.$": "States.ArrayGetItem($.cleanupFailedStksSequence, $.counter)"
        },
        resultPath: "$",
        comment: "NOTE: we cannot MERGE this 'Pass-State' with preceeding 'Pass-State', since 'counter' must be ALREADY PRE-EXIST PRIOR to this 'Pass-State' !!",
    });

    const prepForStartSyncExecutionOfOtherStepFunc = new sfn.Pass(this, "Prep for StartSyncExecution", {
        inputPath: "$$.Execution.Input.SNSTopicName",
        resultPath: "$.currentItem.SNSTopicName",
        comment: "Before moving forward to StartSyncExecution task(below),_ENHANCE_ the INPUT-JSON, by inserting the SNS-Topic-Name (at appropriate location) for use by the other StepFunction.",
    });

    const INcrementCounter = new sfn.CustomState(this, "INcrement Counter", { stateJson: {
        "Type": "Pass",
        "Parameters": {
            "cleanupFailedStksSequence.$": "$.cleanupFailedStksSequence",
            "counter.$": "States.MathAdd($.counter, 1)",
            "maxIterations.$": "$.maxIterations"
        },
        "ResultPath": "$",
    } })

    //// --------------------------------------------------

    const deleteStack = new sfn.CustomState(this, "delete One-Single stack (as part of a sequence)", {
        stateJson: {
            "Type": "Task",
            "Resource": "arn:aws:states:::aws-sdk:cloudformation:deleteStack",
            "Parameters": {
              "StackName.$": "States.ArrayGetItem($.cleanupFailedStksSequence, $.counter)"
            },
            "ResultPath": null,
        }
    })

    const describeStack = new sfn.CustomState(this, "describe stack's status, specifically whether its successfully-deleted", {
        stateJson: {
            "Type": "Task",
            "Resource": "arn:aws:states:::aws-sdk:cloudformation:describeStacks",
            "Parameters": {
              "StackName.$": "States.ArrayGetItem($.cleanupFailedStksSequence, $.counter)"
            },
            "ResultPath": "$.StackDetails",
            "ResultSelector": {  "StackDetails.$": "States.ArrayGetItem($.Stacks, 0)"   },
        }
    })

    const invokeOtherStepFunc = new sfn.CustomState(this, "Invoke "+secondOtherSfnNAME, {
        stateJson: {
            "Type": "Task",
            "Resource": "arn:aws:states:::states:startExecution.sync:2",
            "Parameters": {
              "StateMachineArn": secondOtherSfnARN,
              "Input.$": "$.currentItem"
            },
            "Comment": "Assuming this current-item is a JSON-Array for PARALLEL-deletion of Stacks, then .. invoke the other StepFn to delete all the stacks in that JSON-Array in PARALLEL",
            "ResultPath": null,
        }
    })

    //// --------------------------------------------------

    const whetherJsonSequenceIsPresent = new sfn.Choice(this, "Is Input a Sequence-of-Stacks to be deleted?",
        { comment: "Within Input, '$.cleanupFailedStksSequence' is present" }
    );

    const isItAStackNameOrJSON = new sfn.Choice(this, "StackName or JSON?" )

    const ifNoSuchStack = new sfn.Choice(this, "if No such Stack?" )

    const ifDeleteStackInProgress = new sfn.Choice(this, "is delete-Stack in-progress?" )

    const isEndOfLoop = new sfn.Choice(this, "End of Loop (list of Stacks)?" )

    const waitAfterDeletingOneSingleStack = new sfn.Wait(this, "wait-state-1 after DELETING one-single stack", {
        time: sfn.WaitTime.duration(cdk.Duration.seconds(10)),
        comment: "Wait between DeleteStack & DescribeStack commands, cuz StepFn is very fast.",
    })

    const waitBetweenStatusChecksForStackDelete = new sfn.Wait(this, "wait-state-2 between STATUS-CHECKS for Stack-Delete", {
        time: sfn.WaitTime.duration(cdk.Duration.seconds(15)),
        comment: "Wait between STATUS-CHECKS for Stack-Delete.",
    })

    //// --------------------------------------------------
    whetherJsonSequenceIsPresent.when( sfn.Condition.isPresent("$.cleanupFailedStksSequence"), initializeLoop )
    whetherJsonSequenceIsPresent.otherwise( taskSNSTopicAborted )

    isItAStackNameOrJSON.when( sfn.Condition.isString("$.currentItem"),
        describeStack,
        { comment: "If currentItem is a simple string, then proceed to deleting the Stack whose name it is.", }
    )
    isItAStackNameOrJSON.otherwise( prepForStartSyncExecutionOfOtherStepFunc )

    ifNoSuchStack.when(
        sfn.Condition.stringMatches("$.describeStack.Cause", "Stack with id * does not exist (Service: CloudFormation, Status Code: 400, Request ID*"),
                    //// RegExp alert!  Do Not touch this hardcoded string.
        INcrementCounter,
        { comment: "If such a stack does NOT exist, this stepFn(or something else) successfully deleted this stack!", }
    )
    ifNoSuchStack.otherwise( taskSNSTopicAborted )

    isEndOfLoop.when(
        sfn.Condition.numberLessThanJsonPath("$.counter", "$.maxIterations"),
        lookAtCurrentItemInArray,
        { comment: "If more entries (in SEQUENCE-of-stacks to be deleted)", }
    )
    isEndOfLoop.otherwise( taskSNSTopicSuccess )

    ifDeleteStackInProgress.when(
        sfn.Condition.or(
            sfn.Condition.stringEquals("$.StackDetails.StackDetails.StackStatus", "DELETE_IN_PROGRESS"),
            sfn.Condition.stringEquals("$.StackDetails.StackDetails.StackStatus", "ROLLBACK_IN_PROGRESS"),
            sfn.Condition.stringEquals("$.StackDetails.StackDetails.StackStatus", "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS"),
        ),
        waitBetweenStatusChecksForStackDelete,
        { comment: "NOT-completed!", }
    )
    ifDeleteStackInProgress.when(
        sfn.Condition.or(
            sfn.Condition.stringEquals("$.StackDetails.StackDetails.StackStatus", "CREATE_FAILED"),
            sfn.Condition.stringEquals("$.StackDetails.StackDetails.StackStatus", "DELETE_FAILED"),
            sfn.Condition.stringEquals("$.StackDetails.StackDetails.StackStatus", "ROLLBACK_FAILED"),
            sfn.Condition.stringEquals("$.StackDetails.StackDetails.StackStatus", "UPDATE_FAILED"),
            sfn.Condition.stringEquals("$.StackDetails.StackDetails.StackStatus", "UPDATE_ROLLBACK_FAILED"),
            sfn.Condition.stringEquals("$.StackDetails.StackDetails.StackStatus", "IMPORT_ROLLBACK_FAILED"),
        ),
        deleteStack,
        { comment: "Done! Deleted", }
    )
    ifDeleteStackInProgress.otherwise( INcrementCounter ) //// Unlike 'DeleteStacksInSequence' .. here, a Stack in proper-state is a good thing. Move to next item in input-JSON!


    deleteStack.next(waitAfterDeletingOneSingleStack)
    deleteStack.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        // resultPath: "$.errorDeleteStack",
    })
    describeStack.next(ifDeleteStackInProgress)
    describeStack.addCatch(ifNoSuchStack, {  //// do NOT abort! Continue w/ StepFunction!!!
        errors: [ "States.ALL",  ],
        resultPath: "$.describeStack",
    })

    waitAfterDeletingOneSingleStack.next(describeStack)
    waitBetweenStatusChecksForStackDelete.next(describeStack)

    initializeLoop.next(lookAtCurrentItemInArray)
    lookAtCurrentItemInArray.next(isItAStackNameOrJSON)
    prepForStartSyncExecutionOfOtherStepFunc.next(invokeOtherStepFunc)
    invokeOtherStepFunc.next(INcrementCounter)
    invokeOtherStepFunc.addCatch(taskSNSTopicAborted, {
        errors: [ "States.ALL" ],
        // resultPath: "$.error"+secondOtherSfnNAME,
    })
    INcrementCounter.next(isEndOfLoop)

    taskSNSTopicSuccess.next(succeed)
    taskSNSTopicAborted.next(fail)

    //// --------------------------------------------------
    const stmc = new sfn.StateMachine(this, thisStepFuncNAME, {
        stateMachineName: thisStepFuncNAME,
        comment: "Given an ARRAY of Strings (StackNames) under the JSON-element named 'cleanupFailedStksSequence:', this will trigger 'DeleteStack()' AWS-API calls.. .. in SEQUENCE.  If any of the Array-items are NOT simple-strings (assumed to be JSON), it will trigger the COMPANION StepFunction (to delete the stacks-inside-that-JSON .. in PARALLEL).  Pass a 'SNSTopic:' topmost element as part of the Input-json, to dynamically configure where you receive error notifications.",
        definitionBody: sfn.DefinitionBody.fromChainable(whetherJsonSequenceIsPresent),
        timeout: cdk.Duration.seconds(3 * 3600), //// invoke Backend-CodePipeline + Run above Lambdas + Frontend-CodePipeline + wait for BDDs.
        logs: logGroup ? { level: sfn.LogLevel.ALL, includeExecutionData: true, destination: logGroup } : undefined,
        tracingEnabled: true,
        removalPolicy: cdk.RemovalPolicy.DESTROY,
    })

    //// ---------------------------------------------------
    // add inline policy to existing IAM-Role of stmc, to allow stmc to invoke the 3 Lambdas
    snsTopic.grantPublish(stmc.role)

    // secondOtherStepFn.grant(stmc.role) /// <-- does NOT cdk-synth!!  So, write inline policy.
    stmc.addToRolePolicy(new cdk.aws_iam.PolicyStatement({
        sid: "AllowInvokeSecondStepFn",
        actions: [ 'states:StartExecution', ],
        resources: [ secondOtherSfnARN ],
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
