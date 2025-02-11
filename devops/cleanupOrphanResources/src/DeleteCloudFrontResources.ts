
/**
 *  Write TypeScript code doing the equivalent of the following CLI commands:
 *
 *      aws cloudfront list-origin-request-policies --profile $AWSPROFILE --region $AWSREGION
 *
 *  Extract "ID" from the above output as follows:
 *
 *      jq ".OriginRequestPolicyList.Items[] | select(.OriginRequestPolicy.OriginRequestPolicyConfig.Name | startswith(\"FACTfrontend${TIER}frontendrequestpolicy\")).OriginRequestPolicy" ${RESPONSE}
 *
 *  Get the ETag value by getting the output of
 *
 *      aws cloudfront get-origin-request-policy --id ${ID} --profile $AWSPROFILE --region $AWSREGION | grep -i etag
 *
 *  Delete the AWS-CloudFront resource:
 *      aws cloudfront delete-origin-request-policy --id ${ID} --if-match ${ETag} --profile $AWSPROFILE --region $AWSREGION
 *
 */

import {
    CloudFrontClient,
    ListOriginRequestPoliciesCommand,
    GetOriginRequestPolicyCommand,
    DeleteOriginRequestPolicyCommand,
    ListResponseHeadersPoliciesCommand,
    GetResponseHeadersPolicyCommand,
    DeleteResponseHeadersPolicyCommand,
} from '@aws-sdk/client-cloudfront';
import { Logger } from '@aws-lambda-powertools/logger';

//// Create a logger instance
const logger = new Logger({
    serviceName: 'CloudFrontOriginRequestPolicy-DeletionLambda-PowerTools',
});

//// ...................................................................................

//// Defines the parameters to be passed into the following global-method
interface ResponseHeaderPolicy_DeleteRequest {
    /** The name pattern to match for the policy to be deleted */
    responseHeaderPolicyName :string;
    /** An initialized CloudFront client instance */
    client :CloudFrontClient;
    /** The deployment tier (e.g., 'dev', 'prod') */
    tier :string;
}

/**
 * Deletes a CloudFront Response-Header-Policy specified via param.  -NO- regexp!
 * The function performs the following steps:
 *      1. Lists all Response Header Policies & simultaneously Finds the policy matching the provided name
 *      2. Retrieves the policy's ETag
 *      3. Deletes the policy using its ID and ETag
 *
 * @param {ResponseHeaderPolicy_DeleteRequest} params - The parameters for the delete operation
 *
 * @returns {Promise<void>} Resolves when the policy is deleted successfully
 *
 * @throws None.  Only logs to PowerTools Logger.
 */

async function deleteResponseHeaderPolicy(
    props :ResponseHeaderPolicy_DeleteRequest
): Promise<void> {

    try {
        // List all origin request policies
        const listResponse = await props.client.send(new ListResponseHeadersPoliciesCommand({}));

        // Find the policy matching our naming pattern
        const policy = listResponse.ResponseHeadersPolicyList?.Items?.find(
            item => item.ResponseHeadersPolicy?.ResponseHeadersPolicyConfig?.Name?.startsWith(props.responseHeaderPolicyName)
        );

        if (!policy?.ResponseHeadersPolicy?.Id) {
            logger.info(`-NO- CloudFront's OriginRequestpolicy found matching pattern: ${props.responseHeaderPolicyName}`);
            return;
        }

        const policyId = policy.ResponseHeadersPolicy.Id;
        logger.info(`CloudFront's OriginRequestpolicy pattern: ${props.responseHeaderPolicyName} has ID = ${policyId}`);

        // Get the policy details to obtain ETag
        const getResponse = await props.client.send(new GetResponseHeadersPolicyCommand({
            Id: policyId
        }));

        const eTag = getResponse.ETag;
        if (!eTag) {
            logger.info(`-NO- ETag found for CloudFront's ResponseHeaderPolicy ID: ${policyId}`);
        }

        // Delete the policy
        await props.client.send(new DeleteResponseHeadersPolicyCommand({
            Id: policyId,
            IfMatch: eTag
        }));

        logger.info(`Successfully deleted -NO- CloudFront's ResponseHeaderPolicy: ${policyId}`);

    } catch (error) {
        logger.error(`-ERROR- when CloudFront's OriginRequestpolicy matching pattern: ${props.responseHeaderPolicyName}` );
        logger.error(String(error));
    }
}

export { deleteResponseHeaderPolicy };

//// ...................................................................................

//// Defines the parameters to be passed into the following global-method
interface OriginRequestPolicy_DeleteRequest {
    /** The name pattern to match for the policy to be deleted */
    originRequestPolicyName :string;
    /** An initialized CloudFront client instance */
    client :CloudFrontClient;
    /** The deployment tier (e.g., 'dev', 'prod') */
    tier :string;
}

/**
 * Deletes a CloudFront Origin-Request-Policy specified via param.  -NO- regexp!
 * The function performs the following steps:
 *      1. Lists all Origin Request Policies & simultaneously Finds the policy matching the provided name
 *      2. Retrieves the policy's ETag
 *      3. Deletes the policy using its ID and ETag
 *
 * @param {OriginRequestPolicy_DeleteRequest} params - The parameters for the delete operation
 *
 * @returns {Promise<void>} Resolves when the policy is deleted successfully
 *
 * @throws None.  Only logs to PowerTools Logger.
 */

async function deleteOriginRequestPolicy(
    props :OriginRequestPolicy_DeleteRequest
): Promise<void> {

    try {
        // List all origin request policies
        const listResponse = await props.client.send(new ListOriginRequestPoliciesCommand({}));

        // Find the policy matching our naming pattern
        const policy = listResponse.OriginRequestPolicyList?.Items?.find(
            item => item.OriginRequestPolicy?.OriginRequestPolicyConfig?.Name?.startsWith(props.originRequestPolicyName)
        );

        if (!policy?.OriginRequestPolicy?.Id) {
            logger.info(`-NO- CloudFront's OriginRequestpolicy found matching pattern: ${props.originRequestPolicyName}`);
            return;
        }

        const policyId = policy.OriginRequestPolicy.Id;
        logger.info(`CloudFront's OriginRequestpolicy pattern: ${props.originRequestPolicyName} has ID = ${policyId}`);

        // Get the policy details to obtain ETag
        const getResponse = await props.client.send(new GetOriginRequestPolicyCommand({
            Id: policyId
        }));

        const eTag = getResponse.ETag;
        if (!eTag) {
            logger.info(`-NO- ETag found for CloudFront's OriginRequestpolicy ID: ${policyId}`);
        }

        // Delete the policy
        await props.client.send(new DeleteOriginRequestPolicyCommand({
            Id: policyId,
            IfMatch: eTag
        }));

        logger.info(`Successfully deleted -NO- CloudFront's OriginRequestpolicy: ${policyId}`);

    } catch (error) {
        logger.error(`-ERROR- when CloudFront's OriginRequestpolicy matching pattern: ${props.originRequestPolicyName}` );
        logger.error(String(error));
    }
}

export { deleteOriginRequestPolicy };

//// ...................................................................................

//// EoF
