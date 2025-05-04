#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { PostDeploymentStack } from '../lib/post-deployment-stack';

import * as constants from './constants';

const THIS_COMPONENT_NAME = constants.CDK_DEVOPS_COMPONENT_NAME;

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
//// Derived global variables.

let SIMPLE_STACKNAME = "PostDeployment"
// const STACKNAME = `${constants.CDK_APP_NAME}-${THIS_COMPONENT_NAME}-${tier}-${STACKNAME}`
// const STACKNAME = `${constants.CDK_APP_NAME}-devops-${tier}-${STACKNAME}`  // better way is shown in next line below.
const STACKNAME = constants.get_FULL_AWS_RESOURCE_PREFIX(tier, git_branch, SIMPLE_STACKNAME, THIS_COMPONENT_NAME )
console.log(`STACKNAME='${STACKNAME}'`)

//// ------------------------------------------------------------
/// CDK app begins here.
const stk = new PostDeploymentStack(app,
  SIMPLE_STACKNAME,
  STACKNAME,
  tier,
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
//// FYI: `Tags.of(this).add()` method applies the tags to the entire stack, --INCLUDING-- ALL the (previously-defined) resources within that stack.

const effective_tier :string = (constants.STANDARD_TIERS.indexOf(tier) >= 0) ? tier : constants.DEV_TIER;
//// `Runtime` CBIIT-Tag is only for EC2-based instances (incl. EC2-based-RDS)
cdk.Tags.of(stk).add("PRODUCT", constants.HUMAN_FRIENDLY_APP_NAME.toLowerCase())
cdk.Tags.of(stk).add("Project", constants.HUMAN_FRIENDLY_APP_NAME.toLowerCase())            //// CBIIT required Tag
cdk.Tags.of(stk).add("ApplicationName", constants.HUMAN_FRIENDLY_APP_NAME.toLowerCase())    //// CBIIT required Tag
cdk.Tags.of(stk).add("ENVIRONMENT",  aws_env)
cdk.Tags.of(stk).add("EnvironmentTier",  effective_tier.toUpperCase())                     //// CBIIT
cdk.Tags.of(stk).add("VERSION",     constants.HUMAN_FRIENDLY_APP_VERSION.toLocaleLowerCase()); //// CRRI rules.  Must be all lowercase.
cdk.Tags.of(stk).add("application", constants.CDK_APP_NAME)
cdk.Tags.of(stk).add("component",   THIS_COMPONENT_NAME )
cdk.Tags.of(stk).add("ResourceFunction", "devops" )                            //// CBIIT required Tag
cdk.Tags.of(stk).add("tier",  tier)
cdk.Tags.of(stk).add("ResourceName",  stk.stackName )                              //// CBIIT required Tag
cdk.Tags.of(stk).add("aws_env",  aws_env)
cdk.Tags.of(stk).add("git_branch", git_branch)

////// Currently, we do --NOT-- have access to `constants_cdk`
// if (constants.STANDARD_TIERS.indexOf(tier) >= 0) {
//     cdk.Tags.of(stk).add("BUILD", constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR)
//     cdk.Tags.of(stk).add("CreateDate", constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR)     //// CBIIT required Tag
//     cdk.Tags.of(stk).add("CreatedBy", support_email)                                  //// CBIIT required Tag
// }

//// EoF
