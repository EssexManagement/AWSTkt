import sys
import json
from typing import Union, Optional
from aws_cdk import (
    CfnOutput,
    Tag, CfnTag,
    Fn,
    Names,
    Stack,
    App,
    CfnParameter,
    aws_ec2,
)
from constructs import Construct

import constants
import common.cdk.constants_cdk as constants_cdk
import common.cdk.aws_names as aws_names
from cdk_utils.CloudFormation_util import get_tags_as_array, get_tags_as_json
from cdk_utils.CdkDotJson_util import get_cdk_json_vpc_details, get_list_of_azs

from src.common_role_for_aws_code_build_stack import CommonRoleForAwsCodeBuild
from src.operations_rsrcs import OperationsResources
from src.vpc_w_subnets import VpcWithSubnetsConstruct
from src.vpc_end_points import VpcEndPointConstruct
from src.KMSKeysConstruct import KMSKeysConstruct, ExistingKMSKeyAccessMgrConstruct

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

class AWSLandingZoneStack(Stack):
    """
        For CloudOne, each Tier has its own VPC!!!
        Hence, `tier` is a parameter to the constructor.
        Valid-values of `tier` are: `dev` and upper-tiers.  As always, the `dev` LandingZone is shared by ALL the developer-specific tiers.

        This stack focuses on:
        (1) deploying a VPC, if NONE specified in cdk.json.
        (2) Then deploys subnets (all Private with NO egress)

        This class has 5 instance-properties:
            self.new_private_subnets :list[aws_ec2.CfnSubnet]
            self.new_private_subnet_ids :list[str]
            self.subnet_lkp :dict[str,aws_ec2.CfnSubnet]
            self.list_of_azs :list[str]
            self.subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]]
    """

    def __init__(self,
        app: App,
        construct_id: str,
        stknm: str,
        aws_env: str,
        git_branch: str,
        **kwargs
    ) -> None:
        super().__init__(
            scope = app,
            id = construct_id,
            stack_name = stknm,
            **kwargs
        )
        stk = Stack.of(self)

        # define stack-cloudformation-param named "cdkAppName"
        cdk_app_name_cfnp = CfnParameter(self, "cdkAppName",
            type="String",
            description="The name of the CDK app",
            default=constants.CDK_APP_NAME,
        )

        self.vpc_id_lkp :dict[str,str] = {};
        self.new_private_subnets :list[aws_ec2.CfnSubnet] = [];
        self.new_private_subnet_ids :list[str] = [];
        self.subnet_lkp :dict[str,aws_ec2.CfnSubnet] = {};
        self.list_of_azs :list[str] = []
        self.subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]] = {};

        acct_wide_vpc_details :dict[str,dict[str, Union[str,list[dict[str,str]]]]];
        # vpc_details_for_tier :dict[str, Union[str,list[dict[str,str]]]];
        [ acct_wide_vpc_details, _ ] = get_cdk_json_vpc_details( scope=self, aws_env=aws_env, tier=None )

        tier_based_info = constants_cdk.SUBNET_NAMES_LOOKUP[ aws_env ]
        # if tier_based_info is of type "list[str]", do nothing else, but if it is of type "dict[str,list[str]]", the tier_based_info = tier_based_info[tier], else .. raise exception
        if not isinstance(tier_based_info, list):
            if isinstance(tier_based_info, dict):
                for tier_in_this_acct in tier_based_info.keys():
                    print( f"tier_in_this_acct = '{tier_in_this_acct}'")
                    print( f"Creating VPC & subnets for tier '{tier_in_this_acct}'" )

                    vpc_full_name = aws_names.get_vpc_name( tier=tier_in_this_acct, aws_region=stk.region )
                    tags = get_tags_as_array(
                        tier = tier_in_this_acct,
                        aws_env = aws_env,
                        git_branch = git_branch,
                        component_name = constants.CDK_OPERATIONS_COMPONENT_NAME
                    )
                    tagsCfn :list[CfnTag] = []
                    for tag in tags:
                        tagsCfn.append(CfnTag( key = tag["Key"], value = tag["Value"] ))
                    tagsCfn.append(CfnTag(key = "Name", value = vpc_full_name))

                    vpc_con = VpcWithSubnetsConstruct( scope = self,
                        construct_id = "vpc-only-"+tier_in_this_acct,
                        tier = tier_in_this_acct,
                        aws_env = aws_env,
                        git_branch = git_branch,
                        cdk_app_name = cdk_app_name_cfnp,
                        tags = tags,
                        tagsCfn = tagsCfn,
                    )
                    self.vpc_id_lkp[tier_in_this_acct] = vpc_con.vpc_id
                [ retval_new_private_subnets, retval_new_private_subnet_ids,  retval_subnet_lkp,  retval_list_of_azs,    retval_subnet_per_az_lkp
                ] = VpcWithSubnetsConstruct.create_raw_subnets_for_acct(
                    scope = self,
                    aws_env = aws_env,
                    vpc_id_lkp = self.vpc_id_lkp,
                    acct_wide_vpc_details = acct_wide_vpc_details,
                    tags = tags,
                    tagsCfn = tagsCfn,
                )
                # copy all content from retval_*** into local-variables (which are used as return-values of this method)
                self.new_private_subnets.extend( retval_new_private_subnets )
                self.new_private_subnet_ids.extend( retval_new_private_subnet_ids )
                self.subnet_lkp |= retval_subnet_lkp
                self.list_of_azs.extend( retval_list_of_azs )
                self.subnet_per_az_lkp |= retval_subnet_per_az_lkp
            else:
                raise Exception(f"`constants_cdk.SUBNET_NAMES_LOOKUP` is of UNKNOWN type {type(tier_based_info)}, but it should be of type list[str] or dict[str,list[str]]")

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================


class AWSLandingZoneStack_part2(Stack):
    """
        -AFTER- that the VPC and Subnets are DEPLOYED SUCCESSFULLY, any subnet-lookups will now succeed.
        So, this allows deployment of VPCEndPoint etc.. that this stack deploys
    """

    def __init__(self,
        app: App,
        construct_id: str,
        stknm: str,
        aws_env: str,
        git_branch: str,
        # tier: str,
        # list_of_azs :list[str],
        # vpcL2Construct :aws_ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(
            scope = app,
            id = construct_id,
            stack_name = stknm,
            **kwargs
        )

        # vpc_details :dict[str,dict[str,dict[str,any]]];
        # vpc_ctx :any = self.node.try_get_context("vpc")
        # print( "vpc_ctx..............................")
        # print( json.dumps(vpc_ctx, indent=4, default=str) )
        # if vpc_ctx and aws_env in vpc_ctx:
        #     vpc_details = vpc_ctx[ aws_env ]
        # else:
        #     raise ValueError(f"cdk.json file is MISSING the JSON-details for aws_env=`{aws_env} (under `vpc`) /// FYI: tier='{tier}'.")
        # print( "vpc_details..............................")
        # print( json.dumps(vpc_details, indent=4, default=str) )
        # print( f"vpc_details aws_env={aws_env}..............................")
        # print( json.dumps(vpc_details, indent=4, default=str) )

        # if vpc_details and tier in vpc_details:
        #     vpc_details = vpc_details[tier]
        # print( f"vpc_details for tier={tier}..............................")
        # print( json.dumps(vpc_details, indent=4, default=str) )

        acct_wide_vpc_details :dict[str,dict[str, Union[str,list[dict[str,str]]]]];
        [ acct_wide_vpc_details, _ ] = get_cdk_json_vpc_details( scope=self, aws_env=aws_env, tier=None )

        for tier in acct_wide_vpc_details.keys():
            print( f"tier a.k.a. vpc_short_name = '{tier}'" )
            vpc_full_name = aws_names.get_vpc_name( tier=tier, aws_region=self.region )
            print( f"vpc_full_name = '{vpc_full_name}'" )

            vpc_details_for_tier :dict[str, Union[str,list[dict[str,str]]]];
            ### re-invoke get_cdk_json_vpc_details(), this time for EACH individual tier, for TIER-SPECIFIC details.
            [  _,  vpc_details_for_tier ] = get_cdk_json_vpc_details( scope=self, aws_env=aws_env, tier=tier )

            vpcL2Construct :aws_ec2.IVpc = aws_ec2.Vpc.from_lookup( scope=self, id="vpc-lookup-"+vpc_full_name, vpc_name=vpc_full_name )
            list_of_azs :list[str] = get_list_of_azs( tier=tier, vpc_details_for_tier=vpc_details_for_tier )
            self.vpc_con = VpcEndPointConstruct( scope = self,
                construct_id = "vpe-"+vpc_full_name,
                tier = tier,
                aws_env = aws_env,
                git_branch = git_branch,
                vpcL2Construct = vpcL2Construct,
                list_of_azs = list_of_azs,
            )

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

class OperationsPrerequisitesStack(Stack):

    def __init__(self,
        app: App,
        construct_id: str,
        stknm: str,
        aws_env :str,
        tier :str,
        **kwargs
    ) -> None:
        super().__init__(
            scope = app,
            id = construct_id,
            stack_name = stknm,
            **kwargs
        )

        CommonRoleForAwsCodeBuild(
            scope = self,
            construct_id = "CommonRoleForAwsCodeBuildStack",
        )
        OperationsResources(
            scope = self,
            construct_id = "OpsRsrcs",
            aws_env = aws_env,
        )

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

class FoundationalResourcesStack(Stack):

    def __init__(self,
        app: App,
        construct_id: str,
        stknm: str,
        aws_env: str,
        **kwargs
    ) -> None:
        super().__init__(
            scope = app,
            id = construct_id,
            stack_name = stknm,
            **kwargs
        )

    #     KMSKeysConstruct( scope=self,
    #         construct_id = "KMSKeysConstruct",
    #         aws_env = aws_env,
    #    )

        ExistingKMSKeyAccessMgrConstruct( scope=self,
            construct_id = "ExistingKMSKeyAccessMgrConstruct",
            aws_env = aws_env,
       )

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

