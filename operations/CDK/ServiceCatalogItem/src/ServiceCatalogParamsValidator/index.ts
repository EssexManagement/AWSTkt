import { CloudFormationResponse, sendResponse, CustomResourceInvocationStatus } from "@/common/CloudFormation-utils";
import { CustomResource, Stack } from "aws-cdk-lib";

// =============================================================================================
// ..............................................................................................
// ==============================================================================================

const AccountIdLookup: Record<string, string> = {
    "acct-nonprod": "924221118260",
    "acct-prod":    "230440247112",
};

/**
 * Critical elements of Lambda's Input (that are UNIQUELY relevant to the SFn)..
 *  .. which will be used to -DEFINE- a.k.a. -CONSTRUCT- the JSON-input
 *  ..  to SFn-INVOCATION (to be SENT via `StepFunctionInputParams` below).
 */
interface LambdaInputToBeValidated {

    /** "Tier" is a free-form text field */
    Tier: string;
    /** `"AwsEnv" is picklist/dropdown with just 2 values "acct-nonprod" and "acct-prod" */
    AwsEnv: string;
    /** `"OtherTierExists" is picklist/dropdown with just 2 values "yes" and "No" */
    OtherTierExists: string;
    /** "DatabaseChange" is a picklist/dropdown whose values are listed inside private-variable named "DatabaseChange_List" */
    DatabaseChange: string;
    /** "DeploymentReason" is a picklist/dropdown whose values are listed inside private-variable named "DeploymentReasonList" */
    DeploymentReason: string;
    /** "DestructionScope" is a picklist/dropdown whose values are listed inside private-variable named "DestructionScopeList" */
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

//// ...................................................................

/**
 * Ensure --EACH-- List below .. matches the `AllowedValues` for the CloudFormation-params.
 * See `operations/CDK/ServiceCatalogItem/lib/ServiceCatalogItem-Deployer.template.yaml`
 */

// --
const AwsEnvList = [
    "acct-nonprod",
    "acct-prod",
]
const DatabaseChange_List = [
    "NO changes to RDS",
    "Simply Reload CTAPI data",

    "New Tier",
    "Wipe entire Database, and Reload everything",
]
const DeploymentReasonList = [
    "Currently, Tier does NOT exist",

    "EXISTING Tier needs an update deployed. No issues exist",
    "EXISTING Tier not needed, as git-branch is PR-Merged",

    "EXISTING Tier has some issues",
    "EXISTING Tier has FATAL-problems",
    // "Not Applicable. Tier NOT deployed",
]
const DestructionScopeList = [
    "Not Applicable. Appln is needed",

    "Destroy but .. RE-deploy ALL Stacks",
    "Wipe out everything incl. Pipelines",
]

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
    ResourceProperties: LambdaInputToBeValidated;
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
    const endUserInputJson :LambdaInputToBeValidated = event.ResourceProperties;
    //// Extract key inputs from Input-JSON
    const tier = endUserInputJson.Tier;
    const awsEnv = endUserInputJson.AwsEnv;
    const otherTierExists  = (endUserInputJson.OtherTierExists == "Yes");
    const databaseChange   = endUserInputJson.DatabaseChange;
    const deploymentReason = endUserInputJson.DeploymentReason;
    const destructionScope = endUserInputJson.DestructionScope;

    const body = endUserInputJson.Body || "";

    //// ----------
    //// gather data

    const StackDestructionImplied :boolean =
        deploymentReason === DeploymentReasonList[2]  || /* "EXISTING Tier not needed, as git-branch is PR-Merged" */
        deploymentReason === DeploymentReasonList[3]  || /* "EXISTING Tier has some issues" */
        deploymentReason === DeploymentReasonList[4]     /* "EXISTING Tier has FATAL-problems" */;

    const userExplicitlyRequestedStackDestruction :boolean =
        destructionScope === DestructionScopeList[1] || /* "Destroy & Re-deploy ALL Stacks */
        destructionScope === DestructionScopeList[2]    /* "Wipe out everything incl. Pipelines" */ ;

    const AccountIdForAwsEnv = AccountIdLookup[awsEnv];

    const isNewTier = deploymentReason === "Currently, Tier does NOT exist";

    //// ----------------------------------
    const accountId = process.env.AWS_ACCOUNT_ID ?? endUserInputJson.AccountId;
    const region = process.env.AWS_REGION ?? (process.env.AWS_DEFAULT_REGION ?? endUserInputJson.Region);

    //// ###############################################################
    console.log( `ServiceCatalogItem ACTION = '${event.RequestType}'`)
    if (event.RequestType == 'Delete') {
        const respJson: CloudFormationResponse = generateResponseToCFTServiceCustomResource(
            /* Status: */ 'SUCCESS',
            /* Reason: */ "Delete request SKIPPED. Do Nothing.",
            /* validationErrors: */ undefined,
            event,
            endUserInputJson,
            accountId,
            region,
            body,
        );
        await sendResponse(event, respJson ); //// Send a message to CloudFormation's CustomResource
        return respJson;
    }

    //// ----------------------------------
    // Perform validation checks
    let validationErrors: string[] = [];

    // ValidationCheck111: If NewTier, then validate the value of last 2 picklists.
    if ( isNewTier && StackDestructionImplied )
        validationErrors.push("ERROR: Invalid value chosen for 'DeploymentReason', as this tier perhaps does Not exist!");
    if ( isNewTier &&
        !  (destructionScope === DestructionScopeList[0] /* "Not Applicable. Appln is needed" */ )
    ) {
        validationErrors.push("ERROR: Invalid value chosen for 'DestructionScope', as this tier perhaps does Not exist!");
    }

    // Closely related ValidationChecks: If NOT NewTier, then validate the value of COMBINATION of values of `5xxxDeploymentReason` AS WELL AS `6xxxDestructionScope`
    if (   !   isNewTier &&
           ( userExplicitlyRequestedStackDestruction !==  (deploymentReason === DeploymentReasonList[4] /* "EXISTING Tier has FATAL-problems" */ ) )
    ) {
        validationErrors.push("ERROR: Invalid-Combination of values for 'DeploymentReason' and 'DestructionScope' -- for Tier that supposedly exists! #1");
    }
    if (   !   isNewTier &&
           !   StackDestructionImplied &&
           userExplicitlyRequestedStackDestruction
    ) {
        validationErrors.push("ERROR: Invalid-Combination of values for 'DeploymentReason' and 'DestructionScope' -- for Tier that supposedly exists! #2");
    }

    // IsWrongAccount: Validate that the AWS environment matches the current account ID
    if (AccountIdForAwsEnv !== accountId) {
        validationErrors.push(`ERROR: You are in the --WRONG-- AWS account !!! You chose '${awsEnv}' for AwsEnv-parameter which maps to account ${AccountIdForAwsEnv}`);
    }

    // If there are validation errors, return a FAILED response
    if (validationErrors.length > 0) {
        var s = "";
        validationErrors.forEach((error, index) => {
            s += `(${index + 1}): ${error}\n`;
        });
        const respJson: CloudFormationResponse = generateResponseToCFTServiceCustomResource(
            /* Status: */ 'FAILED',
            /* Reason: */ `${validationErrors.length} failures in Input-Validation:\n`+ s,
            validationErrors,
            event,
            endUserInputJson,
            accountId,
            region,
            body,
        );
        await sendResponse(event, respJson ); //// Send a message to CloudFormation's CustomResource
        return respJson;
    }

    //// ----------------------------------
    //// NO errors in validations.
    const respJson: CloudFormationResponse = generateResponseToCFTServiceCustomResource(
        /* Status: */ 'SUCCESS',
        /* Reason: */ 'Input-Validation ALL OK for '+ event.ResourceType,
        /* ValidationErrors: is meaningless if all OK */ undefined,
        event,
        endUserInputJson,
        accountId,
        region,
        body,
    )
    await sendResponse(event, respJson ); //// Send a message to CloudFormation's CustomResource
    return respJson;
};

// =============================================================================================
// ..............................................................................................
// ==============================================================================================

function generateResponseToCFTServiceCustomResource(
    status :CustomResourceInvocationStatus,
    reason :string,
    validationErrors: string[] | undefined,
    event: CloudFormationCustomResourceEvent,
    endUserInputJson: LambdaInputToBeValidated,
    accountId: string | undefined,
    region: string | undefined,
    body: string | undefined,
): CloudFormationResponse {

    const respJson: CloudFormationResponse = {
        Status: status,
        Reason: reason,
        ValidationErrors: validationErrors, //// <--------
        StackId: event.StackId,
        RequestId: event.RequestId,
        PhysicalResourceId: event.PhysicalResourceId ?? event.RequestType+"-"+event.RequestId,
        LogicalResourceId: event.LogicalResourceId,
        Data: {
            AccountId: accountId,
            Region: region,
            Tier: endUserInputJson.Tier,
            AwsEnv: endUserInputJson.AwsEnv,
            DatabaseChange: endUserInputJson.DatabaseChange,
            DeploymentReason: endUserInputJson.DeploymentReason,
            DestructionScope: endUserInputJson.DestructionScope,
            OtherTierExists: endUserInputJson.OtherTierExists,
            ServiceToken: endUserInputJson.ServiceToken,
            ServiceTimeout: endUserInputJson.ServiceTimeout,
            Body: body,
        }
    };

    if ((status != "SUCCESS") || (validationErrors && validationErrors.length > 0)){
        console.log("Validation failed ❌❌❌ !!");
        console.log( validationErrors) ;
    }
    //// To avoid security-scanners' compliant that sensitive-values are dumped to logs (example: AWS-AccountId 🤦🏾‍♂️) .. create a "clone"
    const clone :any = {
        Status: respJson.Status,
        Reason: respJson.Reason,
        StackId: respJson.StackId,
        RequestId: respJson.RequestId,
        PhysicalResourceId: respJson.PhysicalResourceId,
        LogicalResourceId: respJson.LogicalResourceId,
    };
    // clone["Data"] = "<Removed>";
    console.log(clone);

    return respJson;
}

//// EoF
