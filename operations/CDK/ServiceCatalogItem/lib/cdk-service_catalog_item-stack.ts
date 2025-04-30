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
    //// 1st create the Lambda that is invoked by the ServiceCatalogItem.
    const lambdaSimpleName = 'Invoke_1ClickEnd2End_SFn';
    const functionName = `${constants.CDK_APP_NAME}-Ops-${lambdaSimpleName}`;
    const logsId = "logs-"+ lambdaSimpleName;
    const myLogGrp = new cdk.aws_logs.LogGroup( this, logsId, {
        // logGroupClass = cdk.aws_logs.LogGroupClass.STANDARD,
        logGroupName: functionName,
        // logGroupName: `${constants.CDK_APP_NAME}-Ops-CR-${lambdaSimpleName}`,
        // logs.LogGroupClass.INFREQUENT_ACCESS Will --DENY-- features like Live Tail, metric extraction / Lambda insights, alarming,
        // !! WARNING !! it will also --DENY-- Subscription filters / Export to S3 (that Standard log-class provides)
        retention: RetentionDays.ONE_WEEK,
        removalPolicy: RemovalPolicy.DESTROY,
        // encryptionKey: encryption_key,
    })

    const fldrContainingLambdaCode = "./src/ServiceCatalogItemHandler/";
    //// Create the lambda function that'll invoke the StepFunction
    const invokeStepFunctionLambda = new aws_lambda_nodejs.NodejsFunction(this, lambdaSimpleName, {
        functionName: functionName,
        description: "CloudFormation custom-resource to invoke the '1-click-end-2-end' StepFunction with proper JSON input",
        runtime: aws_lambda.Runtime.NODEJS_22_X,
        logGroup: myLogGrp,
        retryAttempts: 0,
        projectRoot: fldrContainingLambdaCode,
        entry: "index.js",
        handler: 'index.handler',
        code: aws_lambda.Code.fromAsset( fldrContainingLambdaCode +"dist/", {
            displayName: 'to build+deploy InvokeStepFunction-Lambda in lib/cdk-service_catalog_item-stack.ts',
            followSymlinks: cdk.SymlinkFollowMode.ALWAYS,
            deployTime: true,
        }),
        timeout: cdk.Duration.minutes(5),
        architecture: aws_lambda.Architecture.ARM_64,
        // environment: {
        //     //// ValidationError: AWS_REGION environment variable is reserved by the lambda runtime.
        //     ////        It can --NOT-- be set manually. See https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html
        //     'AWS_ACCOUNT_ID': cdk.Stack.of(this).account,
        //     'AWS_REGION': cdk.Stack.of(this).region,
        //     'AWS_PARTITION': cdk.Stack.of(this).partition,
        // },
        insightsVersion: aws_lambda.LambdaInsightsVersion.VERSION_1_0_333_0,
        tracing: aws_lambda.Tracing.ACTIVE,
        recursiveLoop: aws_lambda.RecursiveLoop.TERMINATE,
        loggingFormat: aws_lambda.LoggingFormat.JSON,
        //// ERROR: ValidationError: To use ApplicationLogLevel and/or SystemLogLevel you must set LoggingFormat to 'JSON', got 'Text'.
        applicationLogLevelV2: cdk.aws_lambda.ApplicationLogLevel.INFO,
        // snapStart: NOT valid for TypeScript-λs !!!!
        runtimeManagementMode: aws_lambda.RuntimeManagementMode.AUTO, //// Automatically update to the most recent and secure runtime version!
        // bundling: {
        //     /// https://github.com/aws-powertools/powertools-lambda-typescript/blob/main/examples/app/cdk/example-stack.ts
        //     //// "npx esbuild index.ts --bundle --minify --target=ES2022 --sourcemap --keep-names --format=esm --sources-content=true \
        //     //// --tree-shaking=true --banner:js='import { createRequire } from \"module\";const require = createRequire(import.meta.url);' --platform=node --outfile=dist/index.js",
        //     minify: true,
        //     target: 'es2020',
        //     sourceMap: false,
        //     // keepNames: true,
        //     // forceDockerBundling: true, //// <------------- May NOT work inside AWS-CodeBuild.
        //     metafile: true,
        //     // sourceMapMode: SourceMapMode.INLINE,
        //     // tsconfig: './tsconfig.json',
        //     format: aws_lambda_nodejs.OutputFormat.CJS,
        //     sourcesContent: true,
        //     // mainFields: ['module', 'main', 'index.ts', 'src/index.ts', './ServiceCatalogItemHandler.ts', './src/ServiceCatalogItemHandler.ts'], //// @default []
        //     // externalModules: [], // we bundle all the dependencies
        //     esbuildArgs: {
        //         "--tree-shaking": "true",
        //     },
        //     banner: "import { createRequire } from 'module';const require = createRequire(import.meta.url);",
        // },
    });

    // Grant the Lambda permission to invoke StepFunctions
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

    // Create a custom resource provider to invoke our Lambda
    const provider = new cr.Provider(this, 'StepFunctionInvokeProvider', {
        onEventHandler: invokeStepFunctionLambda
    });

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
        productName: 'Application Tier Deployment',
        owner: 'Platform Team',
        description: 'Product for deploying application tiers via StepFunction',
        distributor: 'IT Operations',
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
    const portfolio = new aws_servicecatalog.Portfolio(this, 'DeploymentPortfolio', {
        displayName: 'Application Deployment Portfolio',
        providerName: 'Platform Team',
        description: 'Portfolio containing products for application deployment',
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
    const consoleDevOpsUser = aws_iam.Role.fromRoleName( this, "consoleIamDevOpsUser", consoleDevopsUserRoleName )
    const consolePowerUser  = aws_iam.Role.fromRoleName( this, "consoleIamPowerUser",  consolePowerUserRoleName )
    const consoleAdminUser  = aws_iam.Role.fromRoleName( this, "consoleIamAdminUser",  consoleAdminUserRoleName )

    // Grant access to these above console-uisers
    portfolio.giveAccessToRole(consoleDevOpsUser);
    portfolio.giveAccessToRole(consolePowerUser);
    portfolio.giveAccessToRole(consoleAdminUser);

    //// --------------------------------------------------
    // Output the Portfolio and Product IDs
    new cdk.CfnOutput(this, 'PortfolioId', {
        value: portfolio.portfolioId,
        description: 'The ID of the Service Catalog Portfolio'
    });

    new cdk.CfnOutput(this, 'ProductId', {
        value: product.productId,
        description: 'The ID of the Service Catalog Product'
    });

}} // end of constructor & Class
//// EoF
