#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { CleanupFailedStacksInSequence } from '../lib/cleanupFailedStacksInSequence-stack';
import { CleanupFailedStacksInParallel } from '../lib/cleanupFailedStacksInParallel-stack';

import * as constants from './constants';

const THIS_COMPONENT_NAME = constants.CDK_OPERATIONS_COMPONENT_NAME

const app = new cdk.App();

//// ------------------------------------------------------------
//// Gather critical parameters from CLI-arguments

const tier = app.node.tryGetContext("TIER")
if (!tier) {
    console.error(`!! FATAL-ERROR !! cmd-line argument 'tier' is missing!   Please pass it as --> '--context TIER="dev"'\n\nAborting!`)
    process.exit(1)
}
const aws_env = (constants.STANDARD_TIERS.indexOf(tier) >= 0 ? tier : constants.DEV_TIER )//// ["dev", "int", "uat", "prod"]
const git_branch = constants.get_git_branch( tier )
console.log( `tier='${tier}' passed via CDK's CLI-arg`)
console.log( `aws_env='${aws_env}' passed via CDK's CLI-arg`)
console.log( `git_branch='${git_branch}' passed via CDK's CLI-arg`)

//// ------------------------------------------------------------
//// @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
//// ------------------------------------------------------------

//// Derived global variables.

let STACKNAME = "StepFn-CleanupFailedStacksInSequence"
// STACKNAME = `${constants.CDK_APP_NAME}-${THIS_COMPONENT_NAME}-${tier}-${STACKNAME}`
// STACKNAME = `${constants.CDK_APP_NAME}-devops-${tier}-${STACKNAME}`  // better way is shown in next line below.
// STACKNAME = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, STACKNAME, "devops" ) //// overriding THIS_COMPONENT_NAME as "devops"
console.log(`STACKNAME='${STACKNAME}'`)

//// ------------------------------------------------------------
/// CDK app begins here.
let stk1 = new CleanupFailedStacksInSequence(app, STACKNAME,
    tier,
    aws_env,
    git_branch,
    {
        /* If you don't specify 'env', this stack will be environment-agnostic.
        * Account/Region-dependent features and context lookups will not work,
        * but a single synthesized template can be deployed anywhere. */
        env: {
          /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
          account: process.env.CDK_DEPLOY_ACCOUNT || process.env.CDK_DEFAULT_ACCOUNT,
          region:  process.env.CDK_DEPLOY_REGION  || process.env.CDK_DEFAULT_REGION,
        },
    },
);

//// ------------------------------------------------------------

//// Derived global variables.

STACKNAME = "StepFn-CleanupFailedStacksInParallel"
// STACKNAME = `${constants.CDK_APP_NAME}-${THIS_COMPONENT_NAME}-${tier}-${STACKNAME}`
// STACKNAME = `${constants.CDK_APP_NAME}-devops-${tier}-${STACKNAME}`  // better way is shown in next line below.
// STACKNAME = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, STACKNAME, "devops" ) //// overriding THIS_COMPONENT_NAME as "devops"
console.log(`STACKNAME='${STACKNAME}'`)

//// ------------------------------------------------------------
/// CDK app begins here.
const stk2 = new CleanupFailedStacksInParallel(app, STACKNAME,
    tier,
    aws_env,
    git_branch,
    {
        /* If you don't specify 'env', this stack will be environment-agnostic.
        * Account/Region-dependent features and context lookups will not work,
        * but a single synthesized template can be deployed anywhere. */
        env: {
          /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
          account: process.env.CDK_DEPLOY_ACCOUNT || process.env.CDK_DEFAULT_ACCOUNT,
          region:  process.env.CDK_DEPLOY_REGION  || process.env.CDK_DEFAULT_REGION,
        },
    },
);

//// ------------------------------------------------------------
//// @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
//// ------------------------------------------------------------
//// FYI: `Tags.of(this).add()` method applies the tags to the entire stack, --INCLUDING-- ALL the (previously-defined) resources within that stack.

const stks :cdk.Stack[] = [ stk1, stk2 ]

stks.forEach( stk => {

    const CONTACT = constants.CONTACT_EMAIL

    stk.tags.setTag("PRODUCT",     constants.HUMAN_FRIENDLY_APP_NAME.toLowerCase()); //// CRRI rules.  Must be all lowercase.
    stk.tags.setTag("VERSION",     constants.HUMAN_FRIENDLY_APP_VERSION.toLocaleLowerCase()); //// CRRI rules.  Must be all lowercase.
    stk.tags.setTag("ENVIRONMENT", aws_env )
    stk.tags.setTag("application", constants.CDK_APP_NAME);
    stk.tags.setTag("component",   THIS_COMPONENT_NAME);
    stk.tags.setTag("tier", tier);
    stk.tags.setTag("env",  aws_env);
    stk.tags.setTag("git_branch", git_branch);

})

//// EoF
