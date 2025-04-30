from aws_cdk import (
    Tag, CfnTag,
    Fn,
    Names,
    Stack,
    RemovalPolicy,
    Duration,
    aws_iam,
    aws_ec2,
)

from constructs import Construct

import constants
from cdk_utils.CloudFormation_util import get_tags_as_array, get_tags_as_json

class VpcEndPointConstruct(Construct):
    """
        create VPC EndPoints within the VPC (MUTS BE pre-existing VPC)
    """

    def __init__(self, scope: Construct, construct_id: str,
        tier :str,
        aws_env :str,
        git_branch :str,
        vpcL2Construct :aws_ec2.IVpc,
        list_of_azs :list[str],
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        stk = Stack.of(self)

        print( f"tier = '{tier}' within "+ __file__ )
        print( f"git_branch = '{git_branch}' within "+ __file__ )
        print( f"aws_env = '{aws_env}' within "+ __file__ )

        print( f"list_of_azs = '{list_of_azs}' within "+ __file__ )

        # subnet_selection = aws_ec2.SubnetSelection( subnets = new_private_subnets )
        # subnet_selection_1perAZ = aws_ec2.SubnetSelection( one_per_az=True, subnets = new_private_L2subnets )
        subnet_selection_1perAZ = aws_ec2.SubnetSelection( availability_zones=list_of_azs, one_per_az=True, subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED )
        # subnet :aws_ec2.ISubnet;
        # print( subnet.subnet_id for subnet in subnet_selection_1perAZ.subnets )

        #   self.create_VPCEndPoints( vpc_cfn, tagsCfn, subnet_per_az_lkp )
        self.create_VPCEndPoints_for_Level2VpcConstruct( vpcL2Construct, tier, aws_env, git_branch, subnet_selection_1perAZ )


    ### ==========================================================================================
    ### ..........................................................................................
    ### ==========================================================================================

    def create_new_vpcendpoint(self,
        endpt_name :str,
        endpt_aws_service :aws_ec2.InterfaceVpcEndpointAwsService,
        vpc_cfn :aws_ec2.CfnVPC,
        subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]],
        # subnet_selection :aws_ec2.SubnetSelection,
        tagsCfn :list[CfnTag]
    ):
        one_subnetid_per_az :list[str] = []
        for az in subnet_per_az_lkp.keys():
            one_subnetid_per_az.append( subnet_per_az_lkp[az][0].attr_subnet_id )

        ### Create security group for the VPCEndPoint
        endpoint_sg = aws_ec2.CfnSecurityGroup(self, "EndPtSG"+endpt_name,
            vpc_id = vpc_cfn.ref,
            group_description = f"From {vpc_cfn.attr_cidr_block} to VPCEndpoint {endpt_aws_service.short_name}",
                                ### alloqwed chars:  a-zA-Z0-9. _-:/()#,@[]+=&;{}!$*
            security_group_ingress=[
                ### Allow HTTPS (443) from within VPC
                aws_ec2.CfnSecurityGroup.IngressProperty( ip_protocol="tcp", from_port=443, to_port=443, cidr_ip = vpc_cfn.attr_cidr_block )
            ],
            # security_group_egress for 0.0.0.0/0 is automatically generated
            tags=tagsCfn,
        )
        ### Create the VPC Endpoint
        endpt = aws_ec2.CfnVPCEndpoint(self, endpt_name,
            vpc_endpoint_type = "Interface",
            service_name = endpt_aws_service.name,
            # service_name=f"com.amazonaws.{Stack.of(self).region}.logs???",
            vpc_id = vpc_cfn.ref,
            private_dns_enabled = True,
            subnet_ids = one_subnetid_per_az,
            # dns_options = aws_ec2.CfnVPCEndpoint.DnsOptionsSpecificationProperty(..)
            security_group_ids = [endpoint_sg.attr_group_id],
            tags=tagsCfn,
        )
        return endpt

    ### -----------------------------------------------------------------------------------

    def create_VPCEndPoints(self,
        vpc_cfn :aws_ec2.CfnVPC,
        # vpcL2Construct :aws_ec2.IVpc,
        tagsCfn :list[CfnTag],
        subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]],
        # tier :str,
        # aws_env :str,
        # git_branch :str,
        # subnet_selection :aws_ec2.SubnetSelection,
    ):
        """
            Attention!  The 1st param is of type `aws_ec2.CfnVPC` which is RAW-CloudFormation Level-0-Construct !!
            Create VPCEndPoints / vpc-end-points / vpc endpoints -- for all AWS Services"
        """

        ### NIST 800-53 finding -- VPC Interface Endpoints are mandatory, else MEDIUM-finding
        self.create_new_vpcendpoint( endpt_name="CloudWatchLogsEndpoint",
            endpt_aws_service=aws_ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            vpc_cfn = vpc_cfn,  tagsCfn=tagsCfn, subnet_per_az_lkp=subnet_per_az_lkp,
        );
        self.create_new_vpcendpoint( endpt_name="EC2Endpoint",
            endpt_aws_service=aws_ec2.InterfaceVpcEndpointAwsService.EC2,
            vpc_cfn = vpc_cfn,  tagsCfn=tagsCfn, subnet_per_az_lkp=subnet_per_az_lkp,
        );
        self.create_new_vpcendpoint( endpt_name="EC2MessagesEndpoint",
            endpt_aws_service=aws_ec2.InterfaceVpcEndpointAwsService.EC2_MESSAGES,
            vpc_cfn = vpc_cfn,  tagsCfn=tagsCfn, subnet_per_az_lkp=subnet_per_az_lkp,
        );
        self.create_new_vpcendpoint( endpt_name="SSMEndpoint",
            endpt_aws_service=aws_ec2.InterfaceVpcEndpointAwsService.SSM,
            vpc_cfn = vpc_cfn,  tagsCfn=tagsCfn, subnet_per_az_lkp=subnet_per_az_lkp,
        );
        self.create_new_vpcendpoint( endpt_name="ECRApiEndpoint",
            endpt_aws_service=aws_ec2.InterfaceVpcEndpointAwsService.ECR,
            vpc_cfn = vpc_cfn,  tagsCfn=tagsCfn, subnet_per_az_lkp=subnet_per_az_lkp,
        );
        self.create_new_vpcendpoint( endpt_name="ECRDockerEndpoint",
            endpt_aws_service=aws_ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            vpc_cfn = vpc_cfn,  tagsCfn=tagsCfn, subnet_per_az_lkp=subnet_per_az_lkp,
        );
        self.create_new_vpcendpoint( endpt_name="SecretMgrEndpoint",
            endpt_aws_service=aws_ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            vpc_cfn = vpc_cfn,  tagsCfn=tagsCfn, subnet_per_az_lkp=subnet_per_az_lkp,
        );
        self.create_new_vpcendpoint( endpt_name="SSMMessagesEndpoint",
            endpt_aws_service=aws_ec2.InterfaceVpcEndpointAwsService.SSM_MESSAGES,
            # lookup_supported_azs = True, ### <--- Unique to this type of EndPt
            vpc_cfn = vpc_cfn,  tagsCfn=tagsCfn, subnet_per_az_lkp=subnet_per_az_lkp, ### <--- unique
        );
        self.create_new_vpcendpoint( endpt_name="SSMContactsEndpoint",
            endpt_aws_service=aws_ec2.InterfaceVpcEndpointAwsService.SSM_CONTACTS,
            # lookup_supported_azs = True, ### <--- Unique to this type of EndPt
            vpc_cfn = vpc_cfn,  tagsCfn=tagsCfn, subnet_per_az_lkp=subnet_per_az_lkp, ### <--- unique
        );
        self.create_new_vpcendpoint( endpt_name="SSMIncidentsEndpoint",
            endpt_aws_service=aws_ec2.InterfaceVpcEndpointAwsService.SSM_INCIDENTS,
            # lookup_supported_azs = True, ### <--- Unique to this type of EndPt
            vpc_cfn = vpc_cfn,  tagsCfn=tagsCfn, subnet_per_az_lkp=subnet_per_az_lkp, ### <--- unique
        );


    def create_VPCEndPoints_for_Level2VpcConstruct(self,
        vpcL2Construct :aws_ec2.IVpc,
        # subnet_per_az_lkp :dict[str,list[aws_ec2.CfnSubnet]],
        tier :str,
        aws_env :str,
        git_branch :str,
        subnet_selection :aws_ec2.SubnetSelection,
    ):
        """
            Attention: Assumes the 1st param is of type `aws_ec2.Vpc`  ... --NOT-- `aws_ec2.CfnVPC` !!
            Creates VPCEndPoints / vpc-end-points / vpc endpoints -- for all AWS Services"
        """

        ### NOTE: The proper way to pass a list of subnets to the upcoming VPCEndPt constructs is "aws_ec2.SubnetSelection"

        ### As of 2025-January for CDK-Version 2.173.4 .. Tagging of VPC Interface-EndPoints is --NOT-- supported in CDK.
        ### Hence the following workaround.
        tagsarr = []
        for k, v in get_tags_as_json(tier, aws_env, git_branch).items():
            tagsarr.append( CfnTag( key=k, value=v ) )

        list_of_endpts :list[aws_ec2.InterfaceVpcEndpoint] = []
        endpt = vpcL2Construct.add_interface_endpoint("CloudWatchLogsEndpoint",
            service=aws_ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            subnets=subnet_selection,
        ); list_of_endpts.append( endpt )
        endpt = vpcL2Construct.add_interface_endpoint("EC2Endpoint",
            service=aws_ec2.InterfaceVpcEndpointAwsService.EC2,
            subnets=subnet_selection,
        ); list_of_endpts.append( endpt )
        endpt = vpcL2Construct.add_interface_endpoint("EC2MessagesEndpoint",
            service=aws_ec2.InterfaceVpcEndpointAwsService.EC2_MESSAGES,
            subnets=subnet_selection,
        ); list_of_endpts.append( endpt )
        endpt = vpcL2Construct.add_interface_endpoint("SSMEndpoint",
            service=aws_ec2.InterfaceVpcEndpointAwsService.SSM,
            subnets=subnet_selection,
        ); list_of_endpts.append( endpt )
        endpt = vpcL2Construct.add_interface_endpoint("SSMMessagesEndpoint",
            service=aws_ec2.InterfaceVpcEndpointAwsService.SSM_MESSAGES,
            subnets=subnet_selection,
        ); list_of_endpts.append( endpt )
        endpt = vpcL2Construct.add_interface_endpoint("SSMContactsEndpoint",
            service=aws_ec2.InterfaceVpcEndpointAwsService.SSM_CONTACTS,
            # lookup_supported_azs = True, ### <--- Unique to this type of EndPt
            subnets=subnet_selection,
        ); list_of_endpts.append( endpt )
        endpt = vpcL2Construct.add_interface_endpoint("SSMIncidentsEndpoint",
            service=aws_ec2.InterfaceVpcEndpointAwsService.SSM_INCIDENTS,
            # lookup_supported_azs = True, ### <--- Unique to this type of EndPt
            subnets=subnet_selection,
        ); list_of_endpts.append( endpt )
        endpt = vpcL2Construct.add_interface_endpoint("ECRApiEndpoint",
            service=aws_ec2.InterfaceVpcEndpointAwsService.ECR,
            subnets=subnet_selection,
        ); list_of_endpts.append( endpt )
        endpt = vpcL2Construct.add_interface_endpoint("ECRDockerEndpoint",
            service=aws_ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            subnets=subnet_selection,
        ); list_of_endpts.append( endpt )
        endpt = vpcL2Construct.add_interface_endpoint("SecretMgrEndpoint",
            service=aws_ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            subnets=subnet_selection,
        ); list_of_endpts.append( endpt )
        ### As of 2025-January for CDK-Version 2.173.4 .. Tagging of VPC Interface-EndPoints is --NOT-- supported in CDK.
        ### Hence the following workaround.
        for ep in list_of_endpts:
            ep.apply_removal_policy( RemovalPolicy.DESTROY )
            endptCfn :aws_ec2.CfnVPCEndpoint = ep.node.default_child
            endptCfn.add_property_override("Tags",  get_tags_as_array(tier, aws_env, git_branch))

### EoF
