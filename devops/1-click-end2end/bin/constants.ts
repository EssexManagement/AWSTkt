//// FILE: devops/post-deployment/bin/constants.ts

import { env } from "process";

/// !!! WARNING !!! Keep this file --IN-SYNC-- with the Python-file `./constants.py`
/// !!! WARNING !!! Keep this file --IN-SYNC-- with the Python-file `./constants.py`
/// !!! WARNING !!! Keep this file --IN-SYNC-- with the Python-file `./constants.py`

export const ENTERPRISE_NAME = "NIH-NCI"
export const HUMAN_FRIENDLY_APP_NAME = "CancerTrialsFinder";
export const HUMAN_FRIENDLY_APP_VERSION = "2.0.0"; //// ❌❌❌ BE careful of defining it here, AS WELL AS in `./constants.py` PYTHON-file.
export const CDK_APP_NAME = "CTF";
export const CDK_DEVOPS_COMPONENT_NAME = "devops";
export const CDK_OPERATIONS_COMPONENT_NAME = "operations";

const THIS_COMPONENT_NAME = CDK_DEVOPS_COMPONENT_NAME;

//// ----------------------------------------------------------------
export const PROD_TIER = "prod"
export const UAT_TIER = "uat"
export const INT_TIER = "int"
export const DEV_TIER = "dev"
export const STANDARD_TIERS = [DEV_TIER, INT_TIER, UAT_TIER, PROD_TIER]

export const STD_UPPER_TIERS = [...STANDARD_TIERS] //// shallow-clone
STD_UPPER_TIERS.splice(STD_UPPER_TIERS.indexOf(DEV_TIER), 1) //// remove "dev" from STD_UPPER_TIERS
// console.log(`STD_UPPER_TIERS = ${STD_UPPER_TIERS}`)

export const GIT_BRANCH_FOR_UPPER_TIERS = "main"

export const cdkDeployableAssets_BucketNamePrefix = "cdk-hnb659fds-assets-" /// -AcctId-Region
export const cdkContainerAssets_RegistryNamePrefix = "cdk-hnb659fds-container-assets-"

//// ----------------------------------------------------------------
//// Attention: This represents an AWS-SES "Verified-emailaddress" --- for use by Cognito User-Pool's FROM-addr and REPLY-TO-addr.
export function get_COGNITO_FROM_EMAIL( tier :string ) {
    if (tier == PROD_TIER) {
        return "FACTSupport@mail.nih.gov"
        // return "matchbox-test@nih.gov"
    } else {
        return "FACTSupport@mail.nih.gov"
        // return"emfact@essexmanagement.com"  ### old.
    }
}
//// ----------------------------------------------------------------
export function get_COGNITO_REPLY_TO_EMAIL( tier :string ){
    if (tier == PROD_TIER) {
        return "FACTSupport@mail.nih.gov"
        // return "matchbox@nih.gov"
    } else {
        return "FACTSupport@mail.nih.gov"
        // return"emfact@essexmanagement.com"  ### old.
    }
}

//// ----------------------------------------------------------------
//// Standardized naming for Git-Branches
export function get_git_branch( tier :string ) {
    if (STD_UPPER_TIERS.indexOf(tier) >= 0 )
        return GIT_BRANCH_FOR_UPPER_TIERS
    else
        return tier
}

//// ----------------------------------------------------------------
export function get_SHARED_AWS_RESOURCE_PREFIX(
    tier :string,
    git_branch :string,
    componentName :string = THIS_COMPONENT_NAME,
) {
    return `${CDK_APP_NAME}-${componentName}-${tier}`
}
//// ----------------------------------------------------------------
export function get_FULL_AWS_RESOURCE_PREFIX(
    tier :string,
    git_branch :string,
    subComponent :string,
    componentName :string = THIS_COMPONENT_NAME,
) {
    return `${get_SHARED_AWS_RESOURCE_PREFIX(tier, git_branch, componentName)}-${subComponent}`
}

//// ----------------------------------------------------------------
export function get_SNS_TOPICNAME(tier :string, git_branch :string){
    return "Operations"
    // return CDK_APP_NAME+"-Ops"
    // if (tier == PROD_TIER) return CDK_APP_NAME+"-prod"
    // else if (tier == UAT_TIER) return CDK_APP_NAME+"-uat"
    // else if (tier == INT_TIER) return CDK_APP_NAME+"-int"
    // else if (tier == DEV_TIER) return CDK_APP_NAME+"-dev"
    // else return CDK_APP_NAME+"-dev"
    // else throw new Error(`Unable to determine SNS-Topic-name: Invalid tier value: ${tier}`)
}
// export const SNS_TOPIC = get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, "sns-topic")

//// ----------------------------------------------------------------

///EoF
