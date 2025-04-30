
/**
 *  When `./devops/cleanup-stacks` StepFunc is done deleting stacks .. ..
 *  .. sometimes, resources are left behind, either because "RemovalPolicy: RETAIN" or CDK-construct-code-changes caused CloudFormation-TEMPLATE's AWS-ResourceIds to change, while actual ResourceNames are the same.
 *
 *  This is a -FALL-BACK- to automate such scenarios across all tiers.
 */

import {
    CloudFrontClient,
} from '@aws-sdk/client-cloudfront';
import {  Context } from 'aws-lambda';
import { Logger } from '@aws-lambda-powertools/logger';

import { deleteOriginRequestPolicy, deleteResponseHeaderPolicy } from "./DeleteCloudFrontResources";
import { deleteAllOrphanENIs, findOrphanEnisForSg, findLambdasUsingSG, LambdaDetails } from './OrphanENIs';

////..........................................................................

const CDK_APP_NAME = "CTF";

//// Create a logger instance
const logger = new Logger({
    serviceName: 'CloudFrontOriginRequestPolicy-DeletionLambda-PowerTools',
});

////..........................................................................

const originRequestPolicyName_1 = (tier :string) => `${CDK_APP_NAME}frontend${tier}frontendrequestpolicy`;
const originRequestPolicyName_2 = (tier :string) => `${CDK_APP_NAME}-frontend-${tier}-us-east-1-OriginRequestPolicy`;
const listORP = (tier :string) => [
    originRequestPolicyName_1(tier),
    originRequestPolicyName_2(tier)
];

const responseHeaderPolicyName_1 = (tier :string) => `${tier}_X-Content-Type-Options_is_nosniff__Strict-Transport-Security`;
const responseHeaderPolicyName_2 = (tier :string) => `${tier}_X-Content-Type-Options_is_nosniff__Strict-Transport-SecurityExactDuplicate`;
const listRHP = (tier :string) => [
    responseHeaderPolicyName_1(tier),
    responseHeaderPolicyName_2(tier)
];

////..........................................................................

//// The expected event-json Type
interface MyLambdaEvent {
    tier: string;
}

interface MyLambdaResponse {
    statusCode: number;
    body: {
        message ? : string;
        error   ? : string;
        numDeleted ? : Number;
        details ? : unknown;
        originalEvent: MyLambdaEvent;
    };
}

////..........................................................................

/**
 * Attention: This Lambda is -NOT- meant to be invoked via a APIGW-RestApi!!!
 *
 * This is designed to be invoked by `./devops/cleanup-stacks/` StepFunction ONLY.
 *
 *  When `./devops/cleanup-stacks` StepFunc is done deleting stacks .. ..
 *  .. sometimes, resources are left behind, either because "RemovalPolicy: RETAIN" or CDK-construct-code-changes caused CloudFormation-TEMPLATE's AWS-ResourceIds to change, while actual ResourceNames are the same.
 *  This lambda represents a -FALL-BACK- .. to automate such scenarios across all tiers.
 *
 * Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
 * @param {Object} event - API Gateway Lambda Proxy Input Format
 *
 * Context doc: https://docs.aws.amazon.com/lambda/latest/dg/nodejs-prog-model-context.html
 * @param {Object} context
 *
 * Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
 * @returns {Object} object - API-Gateway-INTEGRATION friendly json-object
 */
export const lambdaHandler = async (
    event: MyLambdaEvent,
    context: Context
): Promise<MyLambdaResponse> => {

    const client = new CloudFrontClient({
        //// ATTENTION: No need to specify credentials/profile when `sam local invoke`.  Simply use the CLI-args `--profile .. --region ..`
        // profile: " .. "
        // credentials: { .. .. },
        // region: "us-??????",
    });
    var myLambdaResponse :MyLambdaResponse;

    // Get tier from Lambda Event
    const { tier } = event;
    if (tier == undefined) {
        const msg = "ERROR: Lambda-Input is missing 'tier' variable!"
        logger.error( msg );
        myLambdaResponse = {
            statusCode: 500,
            // body: JSON.stringify({
            body: {
                error: msg,
                originalEvent: event
            }
        };
    } else {
        logger.info(`-INFO- Lambda-Input: tier=${tier}`);
        logger.info("1st delete the ORPHAN origin-request-policies");
        for ( const originRequestPolicyName of listORP(tier) ) {
            await deleteOriginRequestPolicy({
                originRequestPolicyName,
                client,
                tier
            })
        }
        logger.info("2nd delete the ORPHAN response-header-policies");
        for ( const responseHeaderPolicyName of listRHP(tier) ) {
            await deleteResponseHeaderPolicy({
                responseHeaderPolicyName,
                client,
                tier
            })
        }
        logger.info("3rd delete the ORPHAN ENIs");
        const numDeleted = await deleteAllOrphanENIs();
        myLambdaResponse = {
            statusCode: 200,
            // body: JSON.stringify({
            body: {
                message: "Success",
                numDeleted: numDeleted,
                originalEvent: event
            }
        };
    }

    return myLambdaResponse;
};

//// ...................................................................................

//// "raw" typescript testing
async function main() {
    try {
        const client = new CloudFrontClient({
            //// ATTENTION: No need to specify credentials/profile when `sam local invoke`.  Simply use the CLI-args `--profile .. --region ..`
            // profile: " .. "
            // credentials: { .. .. },
            // region: "us-??????",
        });
        const tier = process.env.TIER || '';
        if (!tier) { throw new Error('TIER environment variable is required'); }
        await deleteOriginRequestPolicy({ originRequestPolicyName: originRequestPolicyName_1(tier), client, tier });
        await deleteOriginRequestPolicy({ originRequestPolicyName: originRequestPolicyName_2(tier), client, tier });
    } catch (error) {
        logger.error('Main execution error:');
        logger.error(String(error));
        process.exit(1);
    }
}
// Execute if running directly
if (require.main === module) {
    main();
}

//// EoF
