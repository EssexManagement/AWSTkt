import os
from constructs import Construct
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_ecr,
    aws_ecr_assets,
    aws_lambda,
    aws_iam,
    CfnOutput,
    SymlinkFollowMode,
)
from constructs import Construct
from cdk_utils.CloudFormation_util import add_tags
import cdk_ecr_deployment

import constants
import common.cdk.constants_cdk as constants_cdk
from common.cdk.standard_lambda import StandardLambda

""" For each Lambda that uses a Container-Image.
    Step 1: Create a NEW ECR Repo - just for this Lambda
    Step 2: Build the Docker image.
    Step 3: push Container-Image into the above ECR repository
    Step 4: Create a Lambda function using the ARN to the container-image (that's already inside the above ECR repository)

    param # 1 : scope :Construct.
    param # 2 : construct_id :str
    param # 3 : tier :str - `dev|test|int|uat|stage|prod`
    param # 4 : aws_env :str - `DEVINT|dev|test|int|uat|stage|Prod|NONprod`
    param # 5 : git_branch :str - the git branch that is being deployed
    param # 6 : lambda_fullname :str - Must be a GLOBALLY/Account-wide UNIQUE-name of the Lambda-function
    param # 7 : container_img_codebase :str - path to the codebase for the container-image + where the `Dockerfile` is.
                Example: "./runtime_report"
    param # 8 : lambda_factory :StandardLambda - the factory that creates the Lambda function
                NOTE: This can be either `no_vpc_lambda_factory` or the `inside_vpc_lambda_factory` FACTORY-objects.
                NOTE: These 2 factory-objects are instantiated within `app_pipeline/deployment.py`
    param # 9 : (OPTIONAL) description :str -- Lambda's description as seen on AWS-Lambda-Console
    param # 10 : (OPTIONAL) environment :dict -- Lambda's RUNTIME environment-variables
    param # 11 : (OPTIONAL) memory_size :int -- Lambda's runtime's memory-size
    param # 12 : (OPTIONAL) timeout :int -- Lambda's timeout
    param # 13: (OPTIONAL) docker_platform :aws_ecr_assets.Platform -- default = aws_ecr_assets.Platform.LINUX_AMD64 | .LINUX_ARM64 | .custom(..)
    param # 14 : (OPTIONAL) how_many_old_versions_to_retain :int -- default = *LATEST* 2 container-images are retained and rest are AUTOMATICALLY deleted by AWS-ECR-Service (-NOT- by CDK)
"""
class CustomECRRepoLambdaConstruct(Construct):
    def __init__(self,
        scope: Construct,
        construct_id :str,
        tier :str,
        aws_env :str,
        git_branch :str,

        lambda_fullname :str,
        container_img_codebase :str,
        lambda_factory :StandardLambda,

        description: str = None,
        environment: dict = None,
        memory_size: int = None,
        timeout: int = None,

        docker_platform = aws_ecr_assets.Platform.LINUX_ARM64,
        # docker_platform = aws_ecr_assets.Platform.LINUX_AMD64,

        how_many_old_versions_to_retain :int = 2,
        # **kwargs
    ) -> None:
        super().__init__(scope, construct_id)

        stk = Stack.of(self)

        my_ecr_repo_name = lambda_fullname.lower()
        # my_ecr_repo_name = lambda_fullname.replace('[^\w]', '').lower()
        # platform_str = "arm64" if docker_platform == aws_ecr_assets.Platform.LINUX_ARM64 else "amd64"

        self.my_ecr_repo = aws_ecr.Repository( self, "MyECRRepo",
            repository_name = my_ecr_repo_name,
                    ### Repository name must start with a letter & can ONLY contain lowercase letters, numbers, and special characters _.-/
                    ### NOTE: Unlike CDK's default ECR-Rpo, --NO-- need to add AcctId and AWSRegion to repo-name!
                    ### the Repo's URI is --> ${AWSAccountID}.dkr.ecr.${AWSREGION}.amazonaws.com/${MyECRRepoName}
            empty_on_delete = True,
            removal_policy = RemovalPolicy.DESTROY,
            lifecycle_rules=[
                aws_ecr.LifecycleRule(
                    max_image_count = how_many_old_versions_to_retain,
                    description = f"{stk.stack_name} - {my_ecr_repo_name}: Keeps last {how_many_old_versions_to_retain} versions"
                )
            ],
            image_scan_on_push=True,
        )
        # Add tags to the ECR repository
        add_tags( a_construct = self.my_ecr_repo, tier=tier, aws_env=aws_env, git_branch=git_branch )

        ### !! Warning !! USES Default CDK-Repo.
        ### !! Warning !! sends to Default CDK-Repo ONLY.
        ### Build + push --Docker-- Container-image into CDK-owned ecr-repo
        ### FYI: technically: cdk-synth does NOT create the image. cdk-DEPLOY cmd creates + uploads the image.
        ### NOTE: Unlike aws_lambda.EcrImageCode.from_asset_image() which is Lambda-specific, aws_ecr_assets.DockerImageAsset() can be used for ECS, etc.. also;
        self.cdk_defaultrepo_image = aws_ecr_assets.DockerImageAsset( self, "MyECRImage",
            directory = container_img_codebase,
            asset_name = lambda_fullname.lower(),
                ### Note: No punctuations & whitespace allowed -- so do NOT use -> constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR
            # build_args = "cli args to pass to docker-cli command",

            platform = docker_platform,
            # platform = docker_platform,
            # target   : build stage to build;  AVoid this param.

            cache_disabled = True,
            follow_symlinks = SymlinkFollowMode.NEVER,
            # file = if the Dockerfile is -NOT- named `Dockerfile` .. or is in a SUB-SUB-folder ..
            # network_mode = aws_ecr_assets.NetworkMode.custom("?????"),
            # network_mode = aws_ecr_assets.NetworkMode.DEFAULT,
        )
        # self.cdk_defaultrepo_image.repository.node.apply_removal_policy(RemovalPolicy.DESTROY) ### SYNTH RuntimeError: Cannot apply RemovalPolicy: no child or not a CfnResource. Apply the removal policy on the CfnResource directly.

        # ### !! Warning !! USES Default CDK-Repo.
        # ### !! Warning !! sends to Default CDK-Repo ONLY.
        # ### Build + push --Docker-- Container-image into CDK-owned ecr-repo
        # ### FYI: technically: cdk-synth does NOT create the image. cdk-DEPLOY cmd creates + uploads the image.
        # ### Yes ✅ can support sophisticated docker-build-OVERRIDES !
        ### NOTE: aws_lambda.EcrImageCode.from_asset_image() which is Lambda-specific, WHILE (above) aws_ecr_assets.DockerImageAsset() can be used for ECS, etc.. also;
        # self.cdk_defaultrepo_image :aws_lambda.AssetImageCode = aws_lambda.EcrImageCode.from_asset_image(
        #     directory = container_img_codebase,
        #     # working_directory = ..
        #     # cmd = .. override the `CMD` within the Dockerfile
        #     # entrypoint = .. override the `ENTRYPOINT` within the Dockerfile
        #     asset_name = constants_cdk.BUILD_KICKOFF_TIMESTAMP_STR,
        #     # build_args = "cli args to pass to docker-cli command",
        #     platform = docker_platform,
        #     target   = platform_str,
        #     cache_disabled = False,
        #     follow_symlinks = SymlinkFollowMode.NEVER,
        #     # file = if the Dockerfile is -NOT- named `Dockerfile` .. or is in a SUB-SUB-folder ..
        #     # network_mode = aws_ecr_assets.NetworkMode.custom("?????"),
        #     # network_mode = aws_ecr_assets.NetworkMode.DEFAULT,
        # )
        # self.cdk_defaultrepo_image.repository.node.apply_removal_policy(RemovalPolicy.DESTROY) ### SYNTH RuntimeError: Cannot apply RemovalPolicy: no child or not a CfnResource. Apply the removal policy on the CfnResource directly.

        ecr_copier = cdk_ecr_deployment.ECRDeployment( scope=self, id="imgcloner",
            src = cdk_ecr_deployment.DockerImageName( self.cdk_defaultrepo_image.image_uri ),
                ### ${AWSAccountID}.dkr.ecr.${AWSREGION}.amazonaws.com/cdk-hnb659fds-container-assets-${AWSAccountId}-${AWSRegion}:3c11..ContainerImageHASH...6b09
            dest = cdk_ecr_deployment.DockerImageName(
                ### ${AWSAccountID}.dkr.ecr.${AWSREGION}.amazonaws.com/${MyECRRepoName}:3c11..ContainerImageHASH...6b09
                self.my_ecr_repo.repository_uri + ":" + self.cdk_defaultrepo_image.asset_hash
                ### Use the following if you suspect there MUCH more than "hash" in the URI for `self.cdk_defaultrepo_image`
                # self.cdk_defaultrepo_image.image_uri.replace(
                #     self.cdk_defaultrepo_image.repository.repository_uri,
                #     self.my_ecr_repo.repository_uri
                # )
            )
        )
        ### Source image ${AWSAccountID}.dkr.ecr.${AWSREGION}.amazonaws.com/${MyECRRepoName}:3c11..ContainerImageHASH...6b09
        ###         does not exist. Provide a valid source image.

        # Create Lambda function
        self.lambda_function :aws_lambda.Function = lambda_factory.create_container_image_lambda(
            scope = self,
            lambda_name = lambda_fullname,
            code = aws_lambda.EcrImageCode(
                # repository = my_ecr_repo,
                repository = self.my_ecr_repo,
                tag_or_digest = self.cdk_defaultrepo_image.asset_hash, ### !! ERROR !! invalid tag "cdkasset-2024-11-07 17:25:37 est-[0-9a-e]+": invalid reference format
                ### tag_or_digest = self.cdk_defaultrepo_image.image_tag, ### !! ERROR !! invalid tag "cdkasset-2024-11-07 17:25:37 est-[0-9a-e]+": invalid reference format
                ### cmd = .. override the `CMD` within the Dockerfile
                ### working_directory = ..
                ### entrypoint = .. override the `ENTRYPOINT` within the Dockerfile
            ),
            ecr_repo = self.my_ecr_repo,
            description = description,
            environment = environment,
            memory_size=memory_size,
            timeout=timeout,
        )
        self.lambda_function.node.add_dependency( self.my_ecr_repo )
        self.lambda_function.node.add_dependency( ecr_copier )

        # Grant Lambda function permission to pull from ECR
        self.my_ecr_repo.grant_pull(self.lambda_function)

        # Output the ECR repository URI and Lambda function ARN
        # CfnOutput( stk, "LambdaFunctionArn", value = self.lambda_function.function_arn )

### EoF
