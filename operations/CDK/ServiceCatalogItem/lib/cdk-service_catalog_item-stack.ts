import * as Path from 'path';
import * as fs from 'fs';

import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Stack, RemovalPolicy } from 'aws-cdk-lib';
import * as aws_servicecatalog from 'aws-cdk-lib/aws-servicecatalog';
import * as aws_iam from 'aws-cdk-lib/aws-iam';
import * as aws_lambda from 'aws-cdk-lib/aws-lambda';
import * as aws_lambda_nodejs from 'aws-cdk-lib/aws-lambda-nodejs';
import * as cr from 'aws-cdk-lib/custom-resources';

import * as constants from '@/constants';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import { StandardNodeJSLambdaConstruct } from "@/common/StandardNodeJSLambdaConstruct";

// =============================================================================================
// ..............................................................................................
// ==============================================================================================

export class DeploymentServiceCatalogItemStack extends Stack {
constructor(scope: Construct,
    simpleStackName: string,
    fullStackName: string,
    tier:string,
    git_branch:string,
    props?: cdk.StackProps,
){
    super(scope, simpleStackName, {
        stackName: fullStackName,
        ...props
    });

    //// --------------------------------------------------
    //// pre-requisites and constants
    //// --------------------------------------------------
    var lambdaSimpleName;
    var functionName;
    var myLogGrp;
    var fldrContainingLambdaCode;

    //// -------------------------
    //// create the Lambda that validates Lambda-Input.
    lambdaSimpleName = 'validate_SvcCtlg-inputs';
    fldrContainingLambdaCode = "./src/ServiceCatalogParamsValidator/";
    functionName = `${constants.CDK_APP_NAME}-Ops-${lambdaSimpleName}`;
    const invokeValidatorLambdaConstruct = new StandardNodeJSLambdaConstruct(this, "Std"+lambdaSimpleName, {
        tier: tier,
        git_branch :git_branch,
        lambdaSimpleName: lambdaSimpleName,
        fldrContainingLambdaCode: fldrContainingLambdaCode,
        functionName: functionName,
        description: "Validate the end-user's input provided when Provisioning a NEW Service-Catalog-Product",
    })
    //// Create the lambda function that'll invoke the StepFunction
    const invokeInputValidatorLambda = invokeValidatorLambdaConstruct.myLambda;

    // Create a custom resource provider to invoke our Lambda
    const provider1 = new cr.Provider(this, 'InputValidationLambdaInvokeProvider', {
        onEventHandler: invokeInputValidatorLambda,
    });

    //// -------------------------
    //// create the Lambda that is invoked by the ServiceCatalogItem.
    lambdaSimpleName = 'Invoke_1ClickEnd2End_SFn';
    fldrContainingLambdaCode = "./src/ServiceCatalogItemHandler/";
    functionName = `${constants.CDK_APP_NAME}-Ops-${lambdaSimpleName}`;
    const invokeStepFunctionLambdaConstruct = new StandardNodeJSLambdaConstruct(this, "Std"+lambdaSimpleName, {
        tier: tier,
        git_branch :git_branch,
        lambdaSimpleName: lambdaSimpleName,
        fldrContainingLambdaCode: fldrContainingLambdaCode,
        functionName: functionName,
        description: "CloudFormation custom-resource to invoke the '1-click-end-2-end' StepFunction with proper JSON input",
    })
    //// Create the lambda function that'll invoke the StepFunction
    const invokeStepFunctionLambda = invokeStepFunctionLambdaConstruct.myLambda;

    // Create a custom resource provider to invoke our Lambda
    const provider2 = new cr.Provider(this, 'StepFunctionInvokeProvider', {
        onEventHandler: invokeStepFunctionLambda,
    });

    //// -------------------------
    //// Grant the 2nd Lambda permission .. .. to invoke a StepFunction
    const snfArnExpr = `arn:${cdk.Stack.of(this).partition}:states:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:stateMachine:CTF-devops-*`;
    console.log(`Granting This-Lambda, the permission to invoke StepFunctions: ${snfArnExpr}`);
    invokeStepFunctionLambda.addToRolePolicy(new aws_iam.PolicyStatement({
        actions: [
            'states:StartExecution',
            'states:DescribeExecution',
            'states:StopExecution'
        ],
        resources: [ snfArnExpr ]
    }));

    //// --------------------------------------------------
    //// The ServiceCatalog-Item is implemented via a CloudFormation-Template.
    //// Create a product based on that CloudFormation-Template.

    const filePath = './lib/ServiceCatalogItem-Deployer.template.yaml'
    // const absolutePath = Path.resolve(filePath);
    // const myCfnTemplateYaml = fs.readFileSync(absolutePath, 'utf8');
    // const myCfnTemplateYaml = FSUtils.loadYamlFile(  );

    // Create the CloudFormation template for the product
    // const cfnTemplate = new cdk.CfnResource(this, 'DeploymentTemplate', {
    //     type: 'AWS::CloudFormation::Stack',
    //     properties: {
    //       TemplateBody: myCfnTemplateYaml,
    //     }
    // });
    // new aws_servicecatalog.ProductStack(this, 'ProductStack', {
    // });

    // Create the product
    const product = new aws_servicecatalog.CloudFormationProduct(this, 'DeploymentProduct', {
        productName: 'CTF Tier-Deployment',
        description: 'Deploying a NEW/Existing Tier for Cancer-Trials-Finder',
        owner: 'Essex - Managed Service Provider reporting to subhashini.jagu@nih.gov',
        distributor: 'Essex Cloud-Native DevOps-CoE',
        supportEmail: constants.DefaultITSupportEmailAddress,
        productVersions: [{
            productVersionName: 'v1',
            cloudFormationTemplate: aws_servicecatalog.CloudFormationTemplate.fromAsset(filePath, {
                deployTime: true,
                followSymlinks: cdk.SymlinkFollowMode.ALWAYS,
                displayName: 'lib/ServiceCatalogItem-Deployer.template.yaml',
            }),
            validateTemplate :true,
            description: "Deployment of an entire TIER via DevOps-StepFunction named '1-click-end-to-end'",
            // cloudFormationTemplate: aws_servicecatalog.CloudFormationTemplate.fromProductStack(cfnTemplate)
        }],
    });

    //// --------------------------------------------------
    // Create a portfolio inside the ServiceCatalog Console
    const portfolio = new aws_servicecatalog.Portfolio(this, 'CTFDeployPortfolio', {
        displayName: 'Cancer-Trials-Finder Ops Portfolio',
        providerName: 'Essex Cloud-Native DevOps-CoE',
        description: 'Portfolio of products for Cancer-Trials-Finder',
    });


    // Associate the product with the portfolio
    portfolio.addProduct(product);

    //// --------------------------------------------------
    //// Allow actual IAM roles/users .. .. to provision via AWS-Console for ServiceCatalog

    // //// Following is a Sample principal for whom to provision the portfolio
    // const role = new aws_iam.Role(this, 'ServiceCatalogRole', {
    //     assumedBy: new aws_iam.ServicePrincipal('servicecatalog.amazonaws.com')
    // });

    const securityDetails = this.node.tryGetContext( "security" )
    const consoleRolesDetails = securityDetails[ "std-console-sso-roles" ];
    const consoleDevopsUserRoleName = consoleRolesDetails["DevOpsUser"][tier];
    const consoleAdminUserRoleName  = consoleRolesDetails["AdminUser"][tier];
    const consolePowerUserRoleName  = consoleRolesDetails["PowerUser"][tier];
    const consoleDevOpsUser = consoleDevopsUserRoleName ? aws_iam.Role.fromRoleName( this, "consoleIamDevOpsUser", consoleDevopsUserRoleName ) : undefined;
    const consolePowerUser  = consolePowerUserRoleName  ? aws_iam.Role.fromRoleName( this, "consoleIamPowerUser",  consolePowerUserRoleName )  : undefined;
    const consoleAdminUser  = consoleAdminUserRoleName  ? aws_iam.Role.fromRoleName( this, "consoleIamAdminUser",  consoleAdminUserRoleName )  : undefined;

    // Grant access to these above console-uisers
    if (consoleDevOpsUser) portfolio.giveAccessToRole(consoleDevOpsUser);
    if (consolePowerUser)  portfolio.giveAccessToRole(consolePowerUser);
    if (consoleAdminUser)  portfolio.giveAccessToRole(consoleAdminUser);

    // //// --------------------------------------------------
    // //// Why Output the Portfolio & Product IDs? ServiceCatalog-Items are to be used by Humans!!
    // new cdk.CfnOutput(this, 'PortfolioId', {
    //     value: portfolio.portfolioId,
    //     description: 'The ID of the Service Catalog Portfolio'
    // });
    // new cdk.CfnOutput(this, 'ProductId', {
    //     value: product.productId,
    //     description: 'The ID of the Service Catalog Product'
    // });

}} // end of constructor & Class
//// EoF
