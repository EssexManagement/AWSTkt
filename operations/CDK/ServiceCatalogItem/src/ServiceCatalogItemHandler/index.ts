// import * as https from 'https';
////    lambda-to-handle-itops-user-input-to-service-catalog-item@1.0.0 build
////    npx esbuild --bundle index.ts --entry-names=index --minify --target=ES2020 --sourcemap --keep-names --format=cjs --sources-content=true --tree-shaking=true --outdir=dist
////
////    ✘ [ERROR] Could not resolve "https"
////        index.ts:1:23:
////          1 │ import * as https from 'https';
////            ╵                        ~~~~~~~
////    The package "https" wasn't found on the file system but is built into node.
////    Are you trying to bundle for `node`?
////    You can use "--platform=node" to do that, which will remove this error.

import { SFNClient, StartExecutionCommand } from '@aws-sdk/client-sfn';

//// ...................................................................

/**
 * Critical elements of Lambda's Input (that are UNIQUELY relevant to the SFn)..
 *  .. which will be used to -DEFINE- a.k.a. -CONSTRUCT- the JSON-input
 *  ..  to SFn-INVOCATION (to be SENT via `StepFunctionInputParams` below).
 */
interface LambdaInputThatDefinesInputJsonToSFn {
    Tier: string;
    AwsEnv: string;
    OtherTierExists: boolean;
    DeploymentReason: string;
    DestructionScope?: string;
    Body?: string;
    AccountId?: string;
    Region?: string;
    ServiceTimeout?: string, // example: "3600",
}

/**
 * This represents ANY valid JSON-input, that's passed as ..
 * .. input to the `1-click-end-2-end` StepFunc-INVOCATION.
 */
interface StepFunctionInputParams {
    Tier: string;
    aws_env: string;
    'run-rds-init'?: boolean;
    runRdsInit?: boolean;
    'skip-SchemaTableInitialization'?: boolean;
    'destroy-app-stacks-only'?: boolean;
    DestroyAppStacksOnly?: boolean;
    'destroy-all-stacks-NOT-pipelines'?: boolean;
    DestroyAppStacksNOTPipelines?: boolean;
    'destroy-all-stacks-incl-pipeline-stacks'?: boolean;
    DestroyAppStacksInclPipelineStacks?: boolean;
    /** `body` as STRINGIFIED-JSON .. In case we need to pass in COMPLEX-inputs -- in the future -- to the StepFunction */
    body?: string;
}

interface CloudFormationCustomResourceEvent {
    RequestType: 'Create' | 'Update' | 'Delete';
    RequestId: string, // "b44fecc5-9929-4aa1-a4f4-8b4f3230aa3f",
    ResponseURL: string, // example: "https://cloudformation-custom-resource-response-useast??.s3.amazonaws.com/arn%3Aaws%3Acloudformation%3Aus-east??%3A???%3Astack/SC-???-pp-???/??%7CStepFunctionExecutor%7C????X-Amz-Security-Token=???%3D%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=2025???&X-Amz-SignedHeaders=host&X-Amz-Expires=7200&X-Amz-Credential=ASI%2Fus-east??%2Fs3%2Faws4_request&X-Amz-Signature=???",
    ResourceProperties: LambdaInputThatDefinesInputJsonToSFn;
    ServiceToken: string,           // An ARN. Example: "arn:aws:lambda:??:??:function:CTF-Ops-Invoke_<StenFnName>",
    StackId: string,                // Stack! Example: "arn:aws:cloudformation:us-east??:??:stack/SC-??-pp-??/??",
    ResourceType: string,           // Name of Custom-Resource within CFT-Template.  Example: "Custom::StepFunctionExecutor"
    LogicalResourceId: string,      // Simple-String-variant of `ResourceType` (above).  Example: "StepFunctionExecutor",
    // ServiceTimeout: string,      // "3600",
}

interface CloudFormationResponse {
    Status: 'SUCCESS' | 'FAILED';
    Reason: string;
    StackId: string;
    RequestId: string;
    LogicalResourceId: string;
    Data?: Record<string, any>;
    // PhysicalResourceId: string;
}

// interface HandlerResponse {
//     PhysicalResourceId: string;
//     Data?: {
//         ExecutionArn: string;
//     };
// }

//// ...................................................................

const sendResponse = async (event: any, response: CloudFormationResponse): Promise<void> => {
    const responseBody = JSON.stringify(response);
    const responseUrl = new URL(event.ResponseURL);
    // const parsedUrl = url.parse(event.ResponseURL);

    const result = await fetch(responseUrl, {
        method: 'PUT',
        body: responseBody,
        headers: {
            'Content-Type': '',
            'Content-Length': responseBody.length.toString()
        }
    });
    console.log('Available properties:', Object.keys(result));
    console.log( "http's response: Ok? "+ result?.ok +"  & status-code: "+ result?.status +" & textual-response: ");
    console.log( result?.body );

    if (!result.ok) {
        throw new Error(`HTTP ${result.status}: ${result.statusText}`);
    }
    console.log( 'Successfully sent response to '+ responseUrl.toString() );

    //// Following code needs `import http` module!!!
    // const requestOptions = {
    //     hostname: responseUrl.hostname,
    //     port: 443,
    //     path: responseUrl.pathname + responseUrl.search,
    //     method: 'PUT',
    //     headers: {
    //         'Content-Type': '',
    //         'Content-Length': responseBody.length
    //     }
    // };
    // return new Promise((resolve, reject) => {
    //     const request = https.request(requestOptions, (response) => {
    //         let responseData = '';
    //         response.on('data', (chunk) => {
    //             responseData += chunk;
    //         });

    //         response.on('end', () => {
    //             if (response.statusCode && response.statusCode >= 400) {
    //                 reject(new Error(`HTTP ${response.statusCode}: ${responseData}`));
    //             } else {
    //                 resolve(responseData);
    //             }
    //         });
    //     });

    //     request.on('error', (error) => {
    //         console.log('Error sending response:', error);
    //         reject(error);
    //     });

    //     request.write(responseBody);
    //     request.end();
    // });
};

//// ...................................................................

export const handler = async (event: CloudFormationCustomResourceEvent): Promise<CloudFormationResponse> => {

    console.log('Event:');
    console.log( event );
    // console.log('Event:', JSON.stringify(event, null, 2));
    console.log('Environment-Variables passed to this Lambda');
    console.log( process.env )

    //// ----------------------------------
    const sfnInputJson :LambdaInputThatDefinesInputJsonToSFn = event.ResourceProperties;
    //// Extract key inputs from Input-JSON
    const tier = sfnInputJson.Tier;
    const awsEnv = sfnInputJson.AwsEnv;
    const otherTierExists  = sfnInputJson.OtherTierExists == true;
    const deploymentReason = sfnInputJson.DeploymentReason;
    const destructionScope = sfnInputJson.DestructionScope;

    const body = undefined;
    // const body = sfnInputJson.Body || '';

    //// ----------------------------------
    const stepFunctionName = `CTF-devops-${tier}-sfn-1ClickEnd2End`;
    console.log( `StepFnName='${stepFunctionName}` )

    //// ###############################################################
    console.log( `ServiceCatalogItem ACTION = '${event.RequestType}'`)
    if (event.RequestType == 'Delete') {
        const respJson :CloudFormationResponse = {
            Status: 'SUCCESS',
            Reason: 'Delete request SKIPPED. Do Nothing.',
            StackId: event.StackId,
            RequestId: event.RequestId,
            // PhysicalResourceId: event.RequestId,
            LogicalResourceId: event.LogicalResourceId,
            Data: {
                sfnInputJson: sfnInputJson,
            }
        };
        await sendResponse(event, respJson )
        return respJson;
    }

    //// ###############################################################
    //// Determine the scenario based on inputs
    let inputParams: StepFunctionInputParams = {
        "Tier": tier,
        "aws_env": awsEnv
    };

    //// Scenario 1: New AWS-Account with no other Tiers
    if (!otherTierExists) {
        inputParams = {
            ...inputParams,
            "run-rds-init": true,
            "runRdsInit": true,
            "skip-SchemaTableInitialization": false,
            "body": body || '{ "force_update": "1" }',
        };
    }
    //// Scenario 2: Existing account, new Tier
    else if (deploymentReason === 'Not Applicable. NO existing Tier') {
        inputParams = {
            ...inputParams,
            "run-rds-init": true,
            "runRdsInit": true,
            "skip-SchemaTableInitialization": false,
            "body": body || '{ "force_update": "1" }',
        };
    }
    //// Scenario 3: Update existing Tier - no issues
    else if (deploymentReason === 'EXISTING Tier needs an update deployed. No issues exist.') {
        inputParams = {
            ...inputParams,
            "skip-SchemaTableInitialization": true,
        };
    }
    //// Scenario 4: Update existing Tier - has some issues
    else if (deploymentReason === 'EXISTING Tier has some issues') {
        inputParams = {
            ...inputParams,
            "destroy-app-stacks-only": true,
            "DestroyAppStacksOnly": true,
            "skip-SchemaTableInitialization": true,
        };
    }
    // Scenario 5 & 6: Fatal problems
    else if (deploymentReason === 'EXISTING Tier has FATAL-problems') {
        //// Scenarios 5 & 6

        if (destructionScope === 'Destroy & Re-deploy ALL Stacks') {
            //// Scenario 5
            inputParams = {
                ...inputParams,
                "destroy-all-stacks-NOT-pipelines": true,
                "DestroyAppStacksNOTPipelines": true,
                "run-rds-init": true,
                "runRdsInit": true,
                "skip-SchemaTableInitialization": false,
                "body": body || '{ "force_update": "1" }',
            };
        } else if (destructionScope === 'Wipe out every single Stack') {
            //// Scenario 6
            inputParams = {
                ...inputParams,
                "destroy-all-stacks-incl-pipeline-stacks": true,
                "DestroyAppStacksInclPipelineStacks": true,
            };
        }
    }

    //// ----------------------------------
    // Construct the StepFunction ARN
    const accountId = process.env.AWS_ACCOUNT_ID ?? sfnInputJson.AccountId;
    const region = process.env.AWS_REGION ?? (process.env.AWS_DEFAULT_REGION ?? sfnInputJson.Region);
    const partition = process.env.AWS_PARTITION ?? 'aws';

    const stepFunctionArn = `arn:${partition}:states:${region}:${accountId}:stateMachine:${stepFunctionName}`;
    console.log(`Invoking StepFunction: ${stepFunctionArn} .. with JSON-input:`);
    console.log(inputParams);
    // console.log(`With input: ${JSON.stringify(inputParams, null, 2)}`);

    //// ----------------------------------
    try {
        // Start the execution of the StepFunction
        const command = new StartExecutionCommand({
            stateMachineArn: stepFunctionArn,
            input: JSON.stringify(inputParams),
            name: `SvcCtlgItem1-${tier}-${event.RequestType}-${event.RequestId ?? Date.now()}`,
            traceHeader: `SvcCtlgItem1-${tier}-${event.RequestType}-${event.RequestId ?? Date.now()}`,
        });

        const sfnClient = new SFNClient({
            //// Normally, giving the IAM-Role for this Lambda permission to invoke StepFn is sufficient.
            //// Even so .. To avoid 𝜆-runtime errors like following, I am FORCED to do this!!!
            ////        "errorMessage": "Credential is missing",
            ////        "errorMessage": "Region is missing",
            region: region,
            credentials: {
                accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
                secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
                sessionToken: process.env.AWS_SESSION_TOKEN!,

            }
        });

        const result = await sfnClient.send(command);

        const respJson :CloudFormationResponse = {
            Status: 'SUCCESS',
            Reason: 'CREATE - SvcCatalog Product-LAUNCH started for '+ event.ResourceType,
            StackId: event.StackId,
            RequestId: event.RequestId,
            // PhysicalResourceId: event.RequestId,
            LogicalResourceId: event.LogicalResourceId,
            Data: {
                ExecutionArn: result.executionArn!,
                sfnInputJson: sfnInputJson,
            }
        };
        await sendResponse(event, respJson )
        return respJson;
    } catch (error) {
        //// print stacktrace
        console.trace()
        console.error('Error starting StepFunction execution:');
        console.error( error );
        var s :String;
        if ( error instanceof Error ) {
            console.error( error.message )
            s = error.message
        } else {
            s = new String(error)
        }
        // throw error;
        const respJson :CloudFormationResponse = {
            Status: 'FAILED',
            Reason: 'INTERNAL FAILURE - SvcCatalog Product-LAUNCH for '+ event.ResourceType,
            StackId: event.StackId,
            RequestId: event.RequestId,
            // PhysicalResourceId: event.RequestId,
            LogicalResourceId: event.LogicalResourceId,
            Data: {
                sfnInputJson: sfnInputJson,
                internalErrorMsg: s,
            }
        };
        await sendResponse(event, respJson )
        return respJson;
    }
};

//// EoF
