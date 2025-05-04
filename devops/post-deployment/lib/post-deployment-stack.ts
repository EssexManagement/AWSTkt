import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as sfntask from 'aws-cdk-lib/aws-stepfunctions-tasks';

import * as constants from '../bin/constants';
import { stat } from 'fs';

const THIS_COMPONENT_NAME = constants.CDK_DEVOPS_COMPONENT_NAME;

export class PostDeploymentStack extends cdk.Stack {
constructor(scope: Construct,
    simpleStackName: string,
    fullStackName: string,
    tier:string, git_branch:string,
    props?: cdk.StackProps,
) {
    super(scope, fullStackName, props);

    //// --------------------------------------------------
    //// pre-requisites and constants

    const stmc_name = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, "sfn-"+simpleStackName, THIS_COMPONENT_NAME )

    let dbAdminActivitiesFunctionName = 'devops_RDSInstanceSetup';
    dbAdminActivitiesFunctionName = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, /* sub .. COMPONENT-NAME */ dbAdminActivitiesFunctionName, /* COMPONENT-NAME override */ "backend");
    console.log(`functionName='${dbAdminActivitiesFunctionName}'`)
    const dbAdminActivitiesLambdaFunction = cdk.aws_lambda.Function.fromFunctionName(this, dbAdminActivitiesFunctionName, dbAdminActivitiesFunctionName)
    console.log(`1st lambda_ref='${dbAdminActivitiesLambdaFunction}'`)

    let schemaTableInitFunctionName = 'StatelessETL-Rds-Init-lambda';
    schemaTableInitFunctionName = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, /* sub .. COMPONENT-NAME */ schemaTableInitFunctionName, /* COMPONENT-NAME override */ "backend");
    console.log(`functionName='${schemaTableInitFunctionName}'`)
    const schemaTableInitLambdaFunction = cdk.aws_lambda.Function.fromFunctionName(this, schemaTableInitFunctionName, schemaTableInitFunctionName)
    console.log(`1st lambda_ref='${schemaTableInitLambdaFunction}'`)

    let dataLoaderInitialFunctionName = 'refresh_ncit';
    dataLoaderInitialFunctionName = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, /* sub .. COMPONENT-NAME */ dataLoaderInitialFunctionName, /* COMPONENT-NAME override */ "backend");
    const dataLoaderInitialFunction = cdk.aws_lambda.Function.fromFunctionName(this, dataLoaderInitialFunctionName, dataLoaderInitialFunctionName)
    console.log(`2nd lambda/dataLoaderInitialFunctionName ref='${dataLoaderInitialFunction}'`)

    let dataLoaderMoreFunctionName = 'etl_start_mp';
    dataLoaderMoreFunctionName = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, /* sub .. COMPONENT-NAME */ dataLoaderMoreFunctionName, /* COMPONENT-NAME override */ "backend");
    const dataLoaderMoreFunction = cdk.aws_lambda.Function.fromFunctionName(this, dataLoaderMoreFunctionName, dataLoaderMoreFunctionName)
    console.log(`3rd lambda/dataLoaderMoreFunctionName ref='${dataLoaderMoreFunction}'`)

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

    // create a StepFunction state of type PASS, to set the value of "inner-loop-counter" to 1
    // const very1stStep = new sfn.Pass(this, "Set Loop-Counters", {
    //     result: { value: {"inner_loop_counter": 1, "outer_loop_counter": 1} }, <--- we can NO longer FIXED-hardcode this anymore. We need StepFunction's input ALSO!!!
    //     comment: "Before the loop starts, set the counter-variables to track HOW MANY LOOPs",
    // });
    const taskInput :Record<string, any> = {"inner_loop_counter": 1, "outer_loop_counter": 1}
    let taskInputAsStringifiedJson = JSON.stringify(taskInput)
    const very1stStep = new sfn.CustomState(this, "Set Loop-Counters", {
        stateJson: {
            "Type": "Pass",
            "Parameters": {
                //// Do NOT touch the following line!  Instead .. .. Edit the definition of `taskInputAsStringifiedJson` above.
                "output.$": "States.JsonMerge($, States.StringToJson('"+taskInputAsStringifiedJson+"'), false)",
            },
            "OutputPath": "$.output", //// This line means, we'll FORGET about the input, and create WHOLE NEW output-of-this-Pass-Task.  That's why NO ResultPath!!
            "Comment": "Before the loop starts, set the counter-variables to track HOW MANY LOOPs",
        },
    })
    // create a pass state that increments inner_loop_counter, while retaining rest of Task's input as-is
    let counterName :string = "inner_loop_counter"
    // const stringifiedJson = JSON.stringify({counterName: {}}) <-- will Not replace `counterName` !!!
    var stringifiedJson = "'\\{\""+counterName+"\": {}\\}'"  //// Attention: We need the backslashes & single-quote, as this goes AS-IS INSIDE the Task-Definition.
    const incrementInnerLoopCounter = new sfn.CustomState(this, "Increment "+counterName+" only", {
        stateJson: {
            "Type": "Pass",
            "Parameters": {
                //// VERY DANGEROUS to touch the following very-fragile (but working) line-of-code!
                "output.$": "States.JsonMerge($, States.StringToJson(States.Format("+ stringifiedJson +", States.MathAdd($."+counterName+", 1))), false)",
                // OLD -> "output.$": "States.JsonMerge($, States.StringToJson(States.Format('\\{\""+counterName+"\": {}\\}', States.MathAdd($."+counterName+", 1))), false)",
            },
            "OutputPath": "$.output", //// This line means, we'll FORGET about the input, and create WHOLE NEW output-of-this-Pass-Task.  That's why NO ResultPath!!
            "Comment": "Increment the "+counterName+", while retaining rest of Task's input as-is",
        },
    })
    // const incrementInnerLoopCounter = new sfn.Pass(this, "Increment Inner-Loop-Counter only", {
    //     parameters: {
    //         "inner_loop_counter.$": sfn.JsonPath.mathAdd( sfn.JsonPath.numberAt("$.inner_loop_counter"), 1), //// scalar
    //         "outer_loop_counter.$": "$.outer_loop_counter",
    //     },
    //     // result: { "value": sfn.JsonPath.mathAdd( sfn.JsonPath.numberAt("$.inner_loop_counter"), 1), }, //// did NOT work.
    //     // result: { "value": { "inner_loop_counter.$": sfn.JsonPath.mathAdd( sfn.JsonPath.numberAt("$.inner_loop_counter"), 1), }}, //// json.  DID NOT WORK!!!
    //     // result: sfn.Result.fromString( sfn.JsonPath.mathAdd(sfn.JsonPath.numberAt('$.inner_loop_counter'), 1) ), //// <--- did NOT work.
    //     // result: sfn.Result.fromObject({"v.$": sfn.JsonPath.mathAdd(sfn.JsonPath.numberAt('$.inner_loop_counter'), 1) }), //// <--- did NOT work.
    //     resultPath: "$.inner_loop_counter",
    //     comment: "Increment the inner-loop-counter, while retaining rest of Task's input as-is",
    // });

    // create a pass state that increments OUTER!OUTER!_loop_counter, while retaining rest of Task's input as-is
    counterName = "outer_loop_counter"
    stringifiedJson = "'\\{\""+counterName+"\": {}\\}'"  //// Attention: We need the backslashes & single-quote, as this goes AS-IS INSIDE the Task-Definition.
    //// reuse the above stringifiedJson variable here too
    const incrementOuterLoopCounter = new sfn.CustomState(this, "Increment "+counterName+" only", {
        stateJson: {
            "Type": "Pass",
            "Parameters": {
                //// VERY DANGEROUS to touch the following very-fragile (but working) line-of-code!
                "output.$": "States.JsonMerge($, States.StringToJson(States.Format("+ stringifiedJson +", States.MathAdd($."+counterName+", 1))), false)",
                // OLD -> "output.$": "States.JsonMerge($, States.StringToJson(States.Format('\\{\""+counterName+"\": {}\\}', States.MathAdd($."+counterName+", 1))), false)",
            },
            "OutputPath": "$.output", //// This line means, we'll FORGET about the input, and create WHOLE NEW output-of-this-Pass-Task.  That's why NO ResultPath!!
            "Comment": "Increment the "+counterName+", while retaining rest of Task's input as-is",
        },
    })
    // const incrementOuterLoopCounter = new sfn.Pass(this, "Increment OUTER!OUTER-Loop-Counter only", {
    //   parameters: {
    //     // "inner_loop_counter.$": "$.inner_loop_counter",
    //     // "outer_loop_counter.$": sfn.JsonPath.mathAdd( sfn.JsonPath.numberAt("$.outer_loop_counter"), 1), //// scalar
    //     "output.$": "States.JsonMerge($, States.StringToJson(States.Format('\\{\"outer_loop_counter\": {}\\}', States.MathAdd($.outer_loop_counter, 1)), false)"
    //   },
    //   resultPath: "$.outer_loop_counter",
    //   comment: "Increment the OUTER!OUTER-loop-counter, while retaining rest of Task's input as-is",
    // });

    //// --------------------------------------------------
    const dbAdminActivitiesLambda = new sfntask.LambdaInvoke(this, "invoke lambda: "+dbAdminActivitiesFunctionName, {
        lambdaFunction: dbAdminActivitiesLambdaFunction,
        payload: sfn.TaskInput.fromJsonPathAt("$"),
        resultSelector: {"StatusCode.$": "$.StatusCode"}, //// HTTP Response-code
        // resultSelector: {"StatusCode.$": "$.Payload.statusCode"}, //// The JSON-response-body returned by 𝜆-func
        resultPath: "$.first_lambda",
        // outputPath: sfn.JsonPath.format("$.1stLambda_{}_{}", sfn.JsonPath.stringAt("$.outer_loop_counter"), ,sfn.JsonPath.stringAt("$.inner_loop_counter")),
    });

    const schemaTableInitLambda = new sfntask.LambdaInvoke(this, "invoke lambda: "+schemaTableInitFunctionName, {
        lambdaFunction: schemaTableInitLambdaFunction,
        payload: sfn.TaskInput.fromJsonPathAt("$"),
        resultSelector: {"StatusCode.$": "$.StatusCode"}, //// HTTP Response-code
        // resultSelector: {"StatusCode.$": "$.Payload.statusCode"}, //// The JSON-response-body returned by 𝜆-func
        resultPath: "$.first_lambda",
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
    const waitAfterFirstLambdaFails = new sfn.Wait(this, "wait-state-1 after failure of "+schemaTableInitFunctionName, {
        time: sfn.WaitTime.duration(cdk.Duration.seconds(60)),
        comment: "If 1st-Lambda failed, then wait a minute before starting all over again",
    })

    const dataLoaderInitialLambda = new sfntask.LambdaInvoke(this, "invoke lambda: "+dataLoaderInitialFunctionName, {
        lambdaFunction: dataLoaderInitialFunction,
        payload: sfn.TaskInput.fromJsonPathAt("$"),
        resultSelector: {"StatusCode.$": "$.StatusCode"}, //// HTTP Response-code
        // resultSelector: {"StatusCode.$": "$.Payload.statusCode"}, //// The JSON-response-body returned by 𝜆-func
        resultPath: "$.second_lambda",
        // outputPath: sfn.JsonPath.format("$.2ndLambda_{}_{}", sfn.JsonPath.stringAt("$.outer_loop_counter"), sfn.JsonPath.stringAt("$.inner_loop_counter")),
    });
    const waitAfterSecondLambdaFails = new sfn.Wait(this, "wait-state-2 after failure of "+dataLoaderInitialFunctionName, {
        time: sfn.WaitTime.duration(cdk.Duration.seconds(60)),
        comment: "If 2nd-Lambda failed, then wait a minute before starting all over again",
    })
    //// No issues if 𝜆's response-jSON is empty-json a.k.a. {} or null /// Any errors will return a response like:-
    const sample_ERROR_response_2 = {
        "errorMessage": "(psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint \"?????\"\nDETAIL:  Key (????)=(????) already exists.\n\n[SQL: )",
        "errorType": "IntegrityError",
        "requestId": "21c7884c-f239-494d-9ecc-274372f13321",
        "stackTrace": [
          "  File \"/var/task/log_decorator.py\", line 10, in wrapper\n    x = func(*args, **kwargs)\n",
          "  File \"/var/task/database/db_facade.py\", line 112, in write_thesaurus_to_db\n    mycode_df.to_sql(name=f'myfunc_{a_or_b}',\n",
          "  File \"/var/task/pandas/io/sql.py\", line 842, in to_sql\n    return pandas_sql.to_sql(\n",
          "  File \"/var/task/pandas/io/sql.py\", line 1567, in insert_records\n    raise err\n",
          "  File \"/var/task/pandas/io/sql.py\", line 1119, in insert\n    num_inserted = exec_insert(conn, keys, chunk_iter)\n",
          "  File \"/var/task/pandas/io/sql.py\", line 1010, in _execute_insert\n    result = conn.execute(self.table.insert(), data)\n",
          "  File \"/var/task/sqlalchemy/engine/base.py\", line 1408, in execute\n    return meth(\n",
          "  File \"/var/task/sqlalchemy/engine/default.py\", line 924, in do_execute\n    cursor.execute(statement, parameters)\n"
      ]
    }

    const dataLoaderMoreLambda = new sfntask.LambdaInvoke(this, "invoke lambda; "+dataLoaderMoreFunctionName, {
        lambdaFunction: dataLoaderMoreFunction,
        payload: sfn.TaskInput.fromJsonPathAt("$"),
        resultSelector: {"StatusCode.$": "$.StatusCode"}, //// HTTP Response-code
        // resultSelector: {"StatusCode.$": "$.Payload.statusCode"}, //// The JSON-response-body returned by 𝜆-func
        resultPath: "$.third_lambda",
        // outputPath: sfn.JsonPath.format("$.3rdLambda_{}_{}",sfn.JsonPath.stringAt("$.outer_loop_counter"), sfn.JsonPath.stringAt("$.inner_loop_counter")),
    });
    const waitAfterThirdLambdaFails = new sfn.Wait(this, "wait-state-3 after failure of "+dataLoaderMoreFunctionName, {
        time: sfn.WaitTime.duration(cdk.Duration.seconds(60)),
        comment: "If 3rd-Lambda failed, then wait a minute before starting all over again",
    })
    //// No issues if 𝜆's response-jSON is empty-json a.k.a. {} or null /// Any errors will return a response like:-
    const sample_ERROR_response_3 = {
      "errorMessage": "ERROR: unrecoverable exception caught ERROR: start=275: unrecoverable exception caught calling ?????????. duplicate key value violates unique constraint \"??????\"\nDETAIL:  Key (??????)=(????????) already exists.\n",
      "errorType": "Exception",
      "requestId": "e5f8cebf-5a2f-4bc5-93a3-d28aab3795a3",
      "stackTrace": [
          "  File \"/var/task/api_2.py\", line 227, in run_with_logging\n    raise exc\n",
          "  File \"/var/task/api_2.py\", line 221, in run_with_logging\n    func(*args, **kw)\n",
          "  File \"/var/task/api_2.py\", line 425, in process_mt\n    raise Exception(msg)\n"
      ]
    }

    //// --------------------------------------------------
    const whetherSkip2stLambda = new sfn.Choice(this, "Whether to SKIP the 1st lambda?", { comment: "SKIP 1st lambda "+schemaTableInitFunctionName+"?" })

    const chk_1stLambdaStatus = new sfn.Choice(this, "1st lambda Success?", { comment: "Did 1st lambda "+schemaTableInitFunctionName+" succeed?" })
    const chk_2ndLambdaStatus = new sfn.Choice(this, "2nd lambda Success?", { comment: "Did 2nd lambda "+dataLoaderInitialFunctionName+" succeed?" })
    const chk_3rdLambdaStatus = new sfn.Choice(this, "3rd lambda Success?", { comment: "Did 3rd Lambda "+dataLoaderMoreFunctionName+" succeed?" })

    const whetherToDoInnerLoopAgain = new sfn.Choice(this, "Loop-again or fail?", {comment: "Whether to (INNER) loop-back and retry .. or ABORT everything!??" })
    const whetherToDoOuterLoopAgain = new sfn.Choice(this, "Outer-Loop-again or fail?", {comment: "Whether to (OUTER) loop-back and retry .. or ABORT everything!??" })

    //// ---------------------------------------------------
    very1stStep.next( whetherSkip2stLambda )

    whetherSkip2stLambda.when(sfn.Condition.isPresent("$.run-1st-lambda"), dbAdminActivitiesLambda )
    whetherSkip2stLambda.when(sfn.Condition.isPresent("$.run-rds-init"),   dbAdminActivitiesLambda )
    whetherSkip2stLambda.when(sfn.Condition.isPresent("$.runRdsInit"),   dbAdminActivitiesLambda )
    whetherSkip2stLambda.otherwise( dataLoaderInitialLambda )

    dbAdminActivitiesLambda.next(schemaTableInitLambda)
    dbAdminActivitiesLambda.addCatch( taskSNSTopicAborted, {
        errors: [ "States.TaskFailed" ],
        resultPath: "$.error",
    })

    schemaTableInitLambda.next(chk_1stLambdaStatus)
    schemaTableInitLambda.addCatch(waitAfterFirstLambdaFails, {
        errors: [ "States.TaskFailed" ],
        resultPath: "$.error",
    })

    chk_1stLambdaStatus.when(sfn.Condition.numberEquals("$.first_lambda.StatusCode", 200), dataLoaderInitialLambda )  //// INTEGER!! matches `StatusCode`
    chk_1stLambdaStatus.when(sfn.Condition.stringEquals("$.first_lambda.StatusCode", "{}"), dataLoaderInitialLambda )   //// matches Payload-Response/Body
    chk_1stLambdaStatus.when(sfn.Condition.stringEquals("$.first_lambda.StatusCode", "null"), dataLoaderInitialLambda ) //// matches Payload-Response/Body
    chk_1stLambdaStatus.otherwise( waitAfterFirstLambdaFails )
    waitAfterFirstLambdaFails.next(incrementInnerLoopCounter)

    dataLoaderInitialLambda.next(chk_2ndLambdaStatus)
    dataLoaderInitialLambda.addCatch(waitAfterSecondLambdaFails, {
        errors: [ "States.TaskFailed" ],
        resultPath: "$.error",
    })

    chk_2ndLambdaStatus.when(sfn.Condition.numberEquals("$.second_lambda.StatusCode", 200), dataLoaderMoreLambda )  //// INTEGER!! matches `StatusCode`
    chk_2ndLambdaStatus.when(sfn.Condition.stringEquals("$.second_lambda.StatusCode", "{}"), dataLoaderMoreLambda )   //// matches Payload-Response/Body
    chk_2ndLambdaStatus.when(sfn.Condition.stringEquals("$.second_lambda.StatusCode", "null"), dataLoaderMoreLambda ) //// matches Payload-Response/Body
    chk_2ndLambdaStatus.otherwise( waitAfterSecondLambdaFails )
    waitAfterSecondLambdaFails.next(incrementInnerLoopCounter)

    dataLoaderMoreLambda.next(chk_3rdLambdaStatus)
    dataLoaderMoreLambda.addCatch(waitAfterThirdLambdaFails, {
        errors: [ "States.TaskFailed" ],
        resultPath: "$.error",
    })

    chk_3rdLambdaStatus.when(sfn.Condition.numberEquals("$.third_lambda.StatusCode", 200), taskSNSTopicSuccess )  //// INTEGER!! matches `StatusCode`
    chk_3rdLambdaStatus.when(sfn.Condition.stringEquals("$.third_lambda.StatusCode", "{}"), taskSNSTopicSuccess )   //// matches Payload-Response/Body
    chk_3rdLambdaStatus.when(sfn.Condition.stringEquals("$.third_lambda.StatusCode", "null"), taskSNSTopicSuccess ) //// matches Payload-Response/Body
    chk_3rdLambdaStatus.otherwise( waitAfterThirdLambdaFails)
    waitAfterThirdLambdaFails.next(incrementOuterLoopCounter)

    //// SUNNY-DAY-Scenario: iteration-1(1st-𝜆 + 2nd-𝜆)
    //// Typical-Scenario #One: iteration-1(1st-𝜆 FAILS) + iteration-2(1st-𝜆 + 2nd-𝜆)
    //// Typical-Scenario #Two: iteration-1(1st-𝜆 FAILS) + iteration-2(1st-𝜆 + 2nd-𝜆 FAILS) + iteration-3(1st-𝜆 + 2nd-𝜆 + 3rd-𝜆)
    //// Any longer scenarios are NOT supported.  Should be an indication of deep-problems.
    incrementInnerLoopCounter.next(whetherToDoInnerLoopAgain)
    whetherToDoInnerLoopAgain.when(sfn.Condition.numberLessThanEquals("$.inner_loop_counter", 3), dataLoaderInitialLambda)
    whetherToDoInnerLoopAgain.otherwise(taskSNSTopicAborted)

    incrementOuterLoopCounter.next(whetherToDoOuterLoopAgain)
    whetherToDoOuterLoopAgain.when(sfn.Condition.numberLessThanEquals("$.outer_loop_counter", 2), dataLoaderInitialLambda)
    whetherToDoOuterLoopAgain.otherwise(taskSNSTopicAborted)

    taskSNSTopicSuccess.next(succeed)
    taskSNSTopicAborted.next(fail)

    //// --------------------------------------------------
    const stmc = new sfn.StateMachine(this, stmc_name, {
        stateMachineName: stmc_name,
        comment: "Initiate Post-Deployment activities after completion of CI/CD pipeline(CodePipeline)",
        definitionBody: sfn.DefinitionBody.fromChainable(very1stStep),
        timeout: cdk.Duration.seconds(3 * 3600), //// invoke Backend-CodePipeline + Run above Lambdas + Frontend-CodePipeline + wait for BDDs.
        logs: logGroup ? { level: sfn.LogLevel.ALL, includeExecutionData: true, destination: logGroup } : undefined,
        tracingEnabled: true,
    })

    //// ---------------------------------------------------
    // add inline policy to existing IAM-Role of stmc, to allow stmc to invoke the 3 Lambdas
    stmc.addToRolePolicy(new cdk.aws_iam.PolicyStatement({
        sid: "AllowStepFuncToInvoke3Lambdas",
        actions: ['lambda:InvokeFunction'],
        resources: [
            dbAdminActivitiesLambdaFunction.functionArn,
            schemaTableInitLambdaFunction.functionArn,
            dataLoaderInitialFunction.functionArn,
            dataLoaderMoreFunction.functionArn,
        ],
    }))

    snsTopic.grantPublish(stmc.role)
    //// WARNING: The following grant() by the logGroup does NOT seem to work!!!
    // if (logGroup) { logGroup.grant(stmc.role, 'logs:CreateLogStream', 'logs:PutLogEvents') } //// since log-group is already-created at top of file, no need for 'logs:CreateLogGroup'
    // if (logGroup) { logGroup.grantWrite(stmc.role) }

} //// constructor
} //// class
