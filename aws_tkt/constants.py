git_repo_name="AWSTkt"
git_repo_org_name="EssexManagement"
codestar_connection_arn=None

### -----------------------------------------

from aws_cdk import (
    aws_lambda,
    aws_codebuild,
)

CDK_APP_NAME = "AWSTkt"
CDK_APP_PYTHON_VERSION = aws_lambda.Runtime.PYTHON_3_12
LAMBDA_PYTHON_RUNTIME_VER_STR = aws_lambda.Runtime.PYTHON_3_12.name.replace("python","")
LAMBDA_PYTHON_RUNTIME = aws_lambda.Runtime.PYTHON_3_12
LAMBDA_PYTHON_RUNTIME_VER_STR = aws_lambda.Runtime.PYTHON_3_12.name.replace("python","")

CODEBUILD_BUILD_IMAGE = aws_codebuild.LinuxBuildImage.AMAZON_LINUX_2_ARM_3
CODEBUILD_BUILD_IMAGE_UBUNTU = aws_codebuild.LinuxBuildImage.STANDARD_7_0
CODEBUILD_EC2_SIZE    = aws_codebuild.ComputeType.X2_LARGE

### EoF
