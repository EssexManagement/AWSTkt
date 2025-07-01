import * as Path from 'path';
import * as fs from 'fs';

import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Stack, RemovalPolicy } from 'aws-cdk-lib';
import * as aws_iam from 'aws-cdk-lib/aws-iam';
import * as aws_lambda from 'aws-cdk-lib/aws-lambda';
import * as aws_lambda_nodejs from 'aws-cdk-lib/aws-lambda-nodejs';

import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import { PropagatedTagSource } from 'aws-cdk-lib/aws-ecs';

// =============================================================================================
// ..............................................................................................
// ==============================================================================================

interface StandardNodeJSLambdaConstructProps {
    tier : string,
    git_branch : string,
    lambdaSimpleName : string,
    fldrContainingLambdaCode : string,
    /** No Defaults.  Try using something like `${constants.CDK_APP_NAME}-Ops-${props.lambdaSimpleName}` */
    functionName : string,

    /** No default-value. None will be handled appropriately by CDK */
    description ? : string,
    /** Defaults to 'index.js' .. EVEN for TypeScript-projects (where you better do 'npm run build') */
    entry ? :string,
    /** Defaults to 'index.handler' .. EVEN for TypeScript-projects (where you better do 'npm run build') */
    handler ? :string,
}

// ..............................................................................................

export class StandardNodeJSLambdaConstruct extends Construct {

public readonly props: StandardNodeJSLambdaConstructProps;
public readonly myLogGrp :cdk.aws_logs.LogGroup;
public readonly myLambda :aws_lambda_nodejs.NodejsFunction;

constructor( cdk_scope: Construct,
    construct_id :string,
    props: StandardNodeJSLambdaConstructProps,
){
    super( cdk_scope, construct_id);
    const entry :string = props.entry ? props.entry : "index.js";
    const handler :string = props.handler ? props.handler : 'index.handler';

    //// --------------------------------------------------
    //// pre-requisites and constants
    //// --------------------------------------------------
    //// 1st create the Lambda that is invoked by the ServiceCatalogItem.
    const logsId = "logs-"+ props.lambdaSimpleName;
    const myLogGrp = new cdk.aws_logs.LogGroup( cdk_scope, logsId, {
        // logGroupClass = cdk.aws_logs.LogGroupClass.STANDARD,
        logGroupName: props.functionName,
        // logGroupName: `${constants.CDK_APP_NAME}-Ops-CR-${props.lambdaSimpleName}`,
        // logs.LogGroupClass.INFREQUENT_ACCESS Will --DENY-- features like Live Tail, metric extraction / Lambda insights, alarming,
        // !! WARNING !! it will also --DENY-- Subscription filters / Export to S3 (that Standard log-class provides)
        retention: RetentionDays.ONE_WEEK,
        removalPolicy: RemovalPolicy.DESTROY,
        // encryptionKey: encryption_key,
    })

    //// Create the lambda function that'll invoke the StepFunction
    const myLambda = new aws_lambda_nodejs.NodejsFunction( cdk_scope, props.lambdaSimpleName, {
        functionName: props.functionName,
        description: props.description,
        runtime: aws_lambda.Runtime.NODEJS_22_X,
        logGroup: myLogGrp,
        retryAttempts: 0,
        projectRoot: props.fldrContainingLambdaCode,
        entry: entry,
        handler: handler,
        code: aws_lambda.Code.fromAsset( props.fldrContainingLambdaCode +"dist/", {
            displayName: 'to build+deploy InvokeStepFunction-Lambda in '+ __filename,
            followSymlinks: cdk.SymlinkFollowMode.ALWAYS,
            deployTime: false,
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

    this.props = props;
    this.myLogGrp = myLogGrp;
    this.myLambda = myLambda;

}} // end of constructor & Class
//// EoF
