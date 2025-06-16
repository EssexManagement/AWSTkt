import { SFNClient, StartExecutionCommand } from '@aws-sdk/client-sfn';

import * as constants from "./constants";

import { CloudFormationResponse, sendResponse } from "@/common/CloudFormation-utils";

//// ...................................................................

/**
 * Critical elements of Lambda's Input (that are UNIQUELY relevant to the SFn)..
 *  .. which will be used to -DEFINE- a.k.a. -CONSTRUCT- the JSON-input
 *  ..  to SFn-INVOCATION (to be SENT via `StepFunctionInputParams` below).
 */
interface LambdaInputThatDefinesInputJsonToSFn {
    /** "Tier" is a free-form text field */
    Tier: string;
    /** `"AwsEnv" is picklist/dropdown with just 2 values "acct-nonprod" and "acct-prod" */
    AwsEnv: string;
    /** `"OtherTierExists" is picklist/dropdown with just 2 values "yes" and "No" */
    OtherTierExists: string;
    /** "DatabaseChange" is a picklist/dropdown whose values are listed inside private-variable named "DatabaseChange_List" */
    DatabaseChange: string;
    DeploymentReason: string;
    DestructionScope?: string;
    /** meant for stringified JSON -- optional; Currently NOT in use */
    Body?: string;
    /** (Manually specified) Explicit input provided by CloudFormation-service when invoking this Lambda. */
    AccountId ?: string;
    /** (Manually specified) Explicit input provided by CloudFormation-service when invoking this Lambda. */
    Region ?: string;
    /** example: "arn:aws:lambda:??:??:function:CTF-Ops-validate_SvcCtlg-inputs" */
    ServiceToken: string,
    /** Standard input provided by CloudFormation-service when invoking this Lambda. */
    ServiceTimeout ?: string, // example: "3600",
}

/**
 * Ensure this matches the `AllowedValues` for the CloudFormation-param `4xxDatabaseChange.
 * See `operations/CDK/ServiceCatalogItem/lib/ServiceCatalogItem-Deployer.template.yaml`
 */
const DatabaseChange_List = [
    "NO changes to RDS",
    "Simply Reload CTAPI data",

    "New Tier",
    "Wipe entire Database, and Reload everything",
]

/**
 * This represents ANY valid JSON-input, that's passed as ..
 * .. input to the `1-click-end-2-end` StepFunc-INVOCATION.
 */
interface StepFunctionInputParams {
    Tier: string;
    aws_env: string;

    "run-rds-init"  ?: boolean;
    "runRdsInit"    ?: boolean;
    "skip-SchemaTableInitialization" ?: boolean;

    "skip-sfn-after-backend-deploy" ?: boolean;
    "skipSFnAfterBackendDeploy" ?: boolean;

    "destroy-app-stacks-only"  ?: boolean;
    DestroyAppStacksOnly  ?: boolean;
    "destroy-all-stacks-NOT-pipelines"  ?: boolean;
    DestroyAppStacksNOTPipelines  ?: boolean;
    "destroy-all-stacks-incl-pipeline-stacks"  ?: boolean;
    DestroyAppStacksInclPipelineStacks  ?: boolean;

    /** `body` as STRINGIFIED-JSON .. In case we need to pass in COMPLEX-inputs -- in the future -- to the StepFunction */
    body?: string;
}

interface CloudFormationCustomResourceEvent {
    RequestType: "Create" | "Update" | "Delete";
    ServiceToken: string,           // An ARN. Example: "arn:aws:lambda:??:??:function:CTF-Ops-Invoke_<StenFnName>",
    ResponseURL: string, // example: "https://cloudformation-custom-resource-response-useast??.s3.amazonaws.com/arn%3Aaws%3Acloudformation%3Aus-east??%3A???%3Astack/SC-???-pp-???/??%7CStepFunctionExecutor%7C????X-Amz-Security-Token=???%3D%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=2025???&X-Amz-SignedHeaders=host&X-Amz-Expires=7200&X-Amz-Credential=ASI%2Fus-east??%2Fs3%2Faws4_request&X-Amz-Signature=???",
    StackId: string,                // Stack! Example: "arn:aws:cloudformation:us-east??:??:stack/SC-??-pp-??/??",
    RequestId: string, // "b44fecc5-9929-4aa1-a4f4-8b4f3230aa3f",
    LogicalResourceId: string,      // Simple-String-variant of `ResourceType` (above).  Example: "StepFunctionExecutor",
    PhysicalResourceId: string;     // Example: SC-924221118260-pp-spare5lnvly3q-StepFunctionExecutor-1RWZZ3CPMWLS1
    ResourceType: string,           // Name of Custom-Resource within CFT-Template.  Example: "Custom::StepFunctionExecutor"
    // ServiceTimeout: string,      // "3600",
    ResourceProperties: LambdaInputThatDefinesInputJsonToSFn;
}

// =============================================================================================
// ..............................................................................................
// ==============================================================================================

export const handler = async (event: CloudFormationCustomResourceEvent): Promise<CloudFormationResponse> => {

    console.log("Event:");
    console.log( event );
    // console.log("Event:", JSON.stringify(event, null, 2));
    // console.log("Environment-Variables passed to this Lambda");
    // console.log( process.env )

    //// ----------------------------------
    const sfnInputJson :LambdaInputThatDefinesInputJsonToSFn = event.ResourceProperties;
    //// Extract key inputs from Input-JSON
    const tier = sfnInputJson.Tier;
    const awsEnv = sfnInputJson.AwsEnv;
    const otherTierExists  = (sfnInputJson.OtherTierExists == "Yes");
    const databaseChange   = sfnInputJson.DatabaseChange;
    const deploymentReason = sfnInputJson.DeploymentReason;
    const destructionScope = sfnInputJson.DestructionScope;

    const body = undefined;
    // const body = sfnInputJson.Body || "";

    //// ----------------------------------
    const stepFunctionName = `${constants.CDK_APP_NAME}-${constants.CDK_DEVOPS_COMPONENT_NAME}-${tier}-sfn-1ClickEnd2End`;
    console.log( `StepFnName='${stepFunctionName}'` )

    //// ###############################################################
    console.log( `ServiceCatalogItem ACTION = '${event.RequestType}'`)
    if (event.RequestType == 'Delete') {
        const respJson :CloudFormationResponse = {
            Status: 'SUCCESS',
            Reason: "Delete request SKIPPED. Do Nothing.",
            StackId: event.StackId,
            RequestId: event.RequestId,
            PhysicalResourceId: event.PhysicalResourceId ?? event.RequestType+"-"+event.RequestId,
            LogicalResourceId: event.LogicalResourceId,
            Data: {
                sfnInputJson: sfnInputJson,
            }
        };
        console.log( respJson )
        await sendResponse(event, respJson ); //// Send a message to CloudFormation's CustomResource
        return respJson;
    }

    //// ###############################################################
    //// Determine the scenario based on inputs
    let inputParams: StepFunctionInputParams = {
        "Tier": tier,
        "aws_env": awsEnv
    };

    //// Scenario 1: New AWS-Account with -NO- other Tiers
    if (  !  otherTierExists) {
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
    else if (deploymentReason === "EXISTING Tier needs an update deployed. No issues exist.") {
        inputParams = {
            ...inputParams,
            "skip-SchemaTableInitialization": true,
        };
    }
    //// Scenario 4: Update existing Tier - has some issues
    else if (deploymentReason === "EXISTING Tier has some issues") {
        inputParams = {
            ...inputParams,
            "destroy-app-stacks-only": true,
            "DestroyAppStacksOnly": true,
            "skip-SchemaTableInitialization": true,
        };
    }
    // Scenario 5 & 6: Fatal problems
    else if ( (deploymentReason === "EXISTING Tier has FATAL-problems") ||
              (deploymentReason === "EXISTING Tier not needed, as git-branch is PR-Merged")
    ) {
        //// Scenarios 5 & 6

        if (destructionScope === "Destroy but .. RE-deploy ALL Stacks") {
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
        } else if (destructionScope === "Just WIPEOUT everything incl. Pipelines") {
            //// Scenario 6
            inputParams = {
                ...inputParams,
                "destroy-all-stacks-incl-pipeline-stacks": true,
                "DestroyAppStacksInclPipelineStacks": true,
            };
        }
    }

    if (DatabaseChange_List.indexOf(databaseChange) < 2) {
        /// do NOT invoke the `post-backend-deploy` stepfunc AFTER backend-pipeline is success.
        inputParams = {
            ...inputParams,
            "skip-sfn-after-backend-deploy": true,
            "skipSFnAfterBackendDeploy": true,
        };
        delete inputParams["run-rds-init"];
        delete inputParams["runRdsInit"];
    } else {
        delete inputParams["skip-sfn-after-backend-deploy"];
        delete inputParams["skipSFnAfterBackendDeploy"];
    }

    //// ----------------------------------
    // Construct the StepFunction ARN
    const accountId = process.env.AWS_ACCOUNT_ID ?? sfnInputJson.AccountId;
    const region = process.env.AWS_REGION ?? (process.env.AWS_DEFAULT_REGION ?? sfnInputJson.Region);
    const partition = process.env.AWS_PARTITION ?? 'aws';

    const stepFunctionArn = `arn:${partition}:states:${region}:${accountId}:stateMachine:${stepFunctionName}`;
    //// SECURITY: Code Scanning Alert: HIGH --> Below Line: logs sensitive data returned by `process.env` as clear text.
    // console.log(`Invoking StepFunction: ${stepFunctionArn} .. with JSON-input:`);
    console.log(`Invoking StepFunction: with JSON-input:`);
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
            PhysicalResourceId: event.PhysicalResourceId ?? event.RequestType+"-"+event.RequestId,
            LogicalResourceId: event.LogicalResourceId,
            Data: {
                ExecutionArn: result.executionArn!,
                sfnInputJson: sfnInputJson,
            }
        };
        console.log( respJson )
        await sendResponse(event, respJson ); //// Send a message to CloudFormation's CustomResource
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
            s = JSON.stringify(error)
        }
        // throw error;
        const respJson :CloudFormationResponse = {
            Status: 'FAILED',
            Reason: 'INTERNAL FAILURE - SvcCatalog Product-LAUNCH for '+ event.ResourceType,
            StackId: event.StackId,
            RequestId: event.RequestId,
            PhysicalResourceId: event.PhysicalResourceId ?? event.RequestType+"-"+event.RequestId,
            LogicalResourceId: event.LogicalResourceId,
            Data: {
                sfnInputJson: sfnInputJson,
                internalErrorMsg: s,
            }
        };
        console.log( respJson )
        await sendResponse(event, respJson ); //// Send a message to CloudFormation's CustomResource
        return respJson;
    }
};

//// EoF
