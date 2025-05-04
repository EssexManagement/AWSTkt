"""frontend construct."""

from os import path, makedirs
import re

from aws_cdk import (
    Fn,
    Stack,
    Tags,
    Names,
    Duration,
    RemovalPolicy,
    aws_kms,
    aws_s3_deployment as s3_deployment,
    aws_s3,
    aws_logs,
    aws_cloudfront,
    aws_cloudfront_origins,
    # aws_certificatemanager as acm,
    # aws_route53 as route53,
    # aws_route53_targets as targets,
    # aws_logs as logs,
    # aws_apigateway as apigw,
)
from constructs import ( Construct, IConstruct )
import aws_solutions_constructs.aws_cloudfront_s3 as aws_cloudfront_s3

import constants
import common.cdk.constants_cdk as constants_cdk
import cdk_utils.CdkDotJson_util as CdkDotJson_util
from common.cdk.standard_logging import get_log_grp, LogGroupType

def dump_construct_tree(children_constructs :list[IConstruct], level :int = 0):
    for child_constr in children_constructs:
        print( f"!!!!!!!!!!!!!!!!!!!!! [level={level}] {'>>>'*level} child id = '{child_constr.node.id}' within scope='{child_constr.node.scope}' !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        if child_constr.node.children:
            dump_construct_tree( children_constructs = child_constr.node.children, level=level+1 )

class Frontend(Construct):
    """Frontend Construct

    Args:
        Construct (_type_): _description_
    """

    def __init__( self,
        scope: Construct,
        id_: str,
        tier :str,
        aws_env :str,
        git_branch :str,
        api_domain: str,
        root_domain :str,
        frontend_domain_name: str,
        public_api_FQDN :str,
    ) -> None:
        """_summary_

        Args:
            scope (StackLayer): _description_
            id_ (str): _description_
        """
        super().__init__(scope, id_)
        stk = Stack.of(self)

        ### ----------------------------------------------------
        effective_tier = tier if tier in constants.STD_TIERS else constants.DEV_TIER ### ["dev", "int", "uat", "prod"]
        print( f"tier='{tier}' within "+ __file__ )
        print( f"aws_env='{aws_env}' within "+ __file__ )
        print( f"git_branch='{git_branch}' within "+ __file__ )

        ### ----------------------------------------------------
        cloudfront_georestrictions = self.node.try_get_context("frontend_domain")["cloudfront_georestrictions"]
        print( f"cloudfront_georestrictions='{cloudfront_georestrictions}'" )

        logbkt_info_json = self.node.try_get_context("s3_access_logging_bucket")
        if logbkt_info_json and aws_env in logbkt_info_json:
            server_access_logs_bucket_name = logbkt_info_json[aws_env]
        else:
            server_access_logs_bucket_name = None
        print( f"server_access_logs_bucket_name='{server_access_logs_bucket_name}'" )
        server_access_logs_bucket = aws_s3.Bucket.from_bucket_name( scope=self, id="s3-access-logs", bucket_name=server_access_logs_bucket_name ) if server_access_logs_bucket_name else None
        print( f"server_access_logs_bucket='{server_access_logs_bucket}'" )

        ### ----------------------------------------------------
        web_acl_arn = CdkDotJson_util.lkp_waf_acl_for_cloudFront( self, effective_tier )
        print( f"web_acl_arn = '{web_acl_arn}'")

        encryption_key_arn = CdkDotJson_util.lkp_cdk_json_for_kms_key( scope, tier, None, CdkDotJson_util.AwsServiceNamesForKmsKeys.s3 )
        print( f"encryption_key_arn = '{encryption_key_arn}'" )
        if encryption_key_arn.find('alias/aws/s3') >= 0:
            encryption_key = None
        else:
            encryption_key = aws_kms.Key.from_key_arn(scope=scope, id="KmsKeyLkp", key_arn=encryption_key_arn)

        ### ----------------------------------------------------
        ui_build_folder = path.join(path.dirname(__file__), "../ui/dist")

        # Following warnings applies to BOTH `s3_bucket_props` and `logging_s3_bucket_props`
        # WARN AWS_SOLUTIONS_CONSTRUCTS_WARNING:  An override has been provided for the property: versioned.
        # WARN AWS_SOLUTIONS_CONSTRUCTS_WARNING:  An override has been provided for the property: removalPolicy. Default value: 'retain'. You provided: 'destroy'.

        ### ----------------------------------------------------




        ### https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logging-legacy-s3.html#AccessLogsBucketAndFileOwnership
        ### Above url clearly states that: for Amazon-CloudFront to log into our bucket, that bucket -MUST- have ACL enabled.
        ###     Repeat: "ACL enabled".

        ### FYI: NIST-800.53 requires us to --> allow Amazon-CloudFront-Service to log all internet-access (to our Distribution), into OUR OWN bucket.
        ###     https://docs.aws.amazon.com/securityhub/latest/userguide/cloudfront-controls.html#cloudfront-5
        ###     Repeat: "requires us"
        ### Amazon-CloudFront-Service does this logging (for us), via an AWS-owned Account, whose Canonical-ID = `c4c1ede66af53448b93c283ce9448c4ba468c9432aa01d700d3878632f77d2d0`.
        ###     REF: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logging-legacy-s3.html#AccessLogsBucketAndFileOwnership




        s3_bucket_props = aws_s3.BucketProps(
            auto_delete_objects = True,
            removal_policy = RemovalPolicy.DESTROY,
            ### Fix CloudFormation STACK-ERROR -> Bucket cannot have ACLs set with ObjectOwnership's BucketOwnerEnforced setting
            ### Fix cfn-lint ERROR -> E3045 A bucket with AccessControl set should also have OwnershipControl configured
            # access_control = aws_s3.BucketAccessControl.PRIVATE,
            block_public_access = aws_s3.BlockPublicAccess.BLOCK_ALL,
            # object_ownership = aws_s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            # access_control = aws_s3.BucketAccessControl.?, ### <-- ATTENTION !! Must NOT be set for logging bucket
            versioned = False,
            enforce_ssl = True,
            public_read_access = False,
            object_ownership = aws_s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            encryption = aws_s3.BucketEncryption.KMS if encryption_key else None,
            encryption_key = encryption_key,
            # server_access_logs_bucket = server_access_logs_bucket, ### Do --NOT-- specify.  `CloudFrontToS3` AWS-construct will automatically create a s3-logging bucket.
        )

        ### Per best practices, CloudFront's S3 bucket should have it's own S3-Logging-bucket.
        ### But per Security Guidelines, all buckets, NO EXCEPTIONS, should have "server_access_logs_bucket"
        logging_s3_bucket_props = aws_s3.BucketProps(
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
            # auto_delete_objects=True                if tier != "prod" else False,
            # removal_policy=RemovalPolicy.DESTROY    if tier != "prod" else RemovalPolicy.RETAIN,

            ### Fix CloudFormation STACK-ERROR -> Bucket cannot have ACLs set with ObjectOwnership's BucketOwnerEnforced setting
            ### Fix cfn-lint ERROR -> E3045 A bucket with AccessControl set should also have OwnershipControl configured
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            # object_ownership = aws_s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            # access_control = aws_s3.BucketAccessControl.PRIVATE, ### deprecated. ### <-- ATTENTION !! Must NOT be set for logging bucket
            versioned = False,
            enforce_ssl = True,
            public_read_access = False,
            object_ownership = aws_s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            encryption = aws_s3.BucketEncryption.KMS if encryption_key else None,
            encryption_key = encryption_key,
            server_access_logs_bucket = server_access_logs_bucket,
        )

        ### -------------------------------
        ### Common SECURITY-RELATED Headers that ALL Origins of CloudFront -MUST- have.
        ### https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-response-headers-policies.html#managed-response-headers-policies-cors-security
        response_headers_policy_name=tier+"_X-Content-Type-Options_is_nosniff__Strict-Transport-Security"
        comment=f"{tier} tier/env X-Content-Type-Options = nosniff & Strict-Transport-Security"

        # ### REF: JAVA-SDK https://sdk.amazonaws.com/java/api/latest/software/amazon/awssdk/services/cloudfront/model/ResponseHeadersPolicyCustomHeader.html
        # custom_headers_behavior=[aws_cloudfront.ResponseCustomHeadersBehavior(
        #     ### https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-response-headers-policies.html#managed-response-headers-policies-cors-security
        #     custom_headers=aws_cloudfront.ResponseCustomHeader(
        #         header="X-Content-Type-Options", value="nosniff", override=True
        #     ), ### "X-Content-Type-Options": "nosniff",
        # )],
        custom_headers_behavior = None

        ### For following `security_headers_behavior` REF:
        ###         https://sdk.amazonaws.com/java/api/latest/software/amazon/awssdk/services/cloudfront/model/ResponseHeadersPolicySecurityHeadersConfig.Builder.html#contentTypeOptions(software.amazon.awssdk.services.cloudfront.model.ResponseHeadersPolicyContentTypeOptions)
        ###         https://sdk.amazonaws.com/java/api/latest/software/amazon/awssdk/services/cloudfront/model/ResponseHeadersPolicySecurityHeadersConfig.Builder.html#contentSecurityPolicy(software.amazon.awssdk.services.cloudfront.model.ResponseHeadersPolicyContentSecurityPolicy)
        security_headers_behavior = aws_cloudfront.ResponseSecurityHeadersBehavior(
            ### https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-response-headers-policies.html#managed-response-headers-policies-cors-security
            ### Just setting `override` to True for `content_type_options`, will AUTOMATICALLY set the value `nosniff`
            ### https://sdk.amazonaws.com/java/api/latest/software/amazon/awssdk/services/cloudfront/model/ResponseHeadersPolicyContentTypeOptions.Builder.html
            content_type_options=aws_cloudfront.ResponseHeadersContentTypeOptions(override=True),
                                        ### "X-Content-Type-Options": "nosniff",
            strict_transport_security=aws_cloudfront.ResponseHeadersStrictTransportSecurity(
                                        ### "Strict-Transport-Security": 365*24*3600,
                    access_control_max_age=Duration.days(365),
                    override=True,
                    include_subdomains=True,
                    preload=True,
            ),

            # content_security_policy=aws_cloudfront.ResponseHeadersContentSecurityPolicy(content_security_policy=?????, override=True),
        )

        ### This "props" is used within CloudFrontToS3
        response_headers_policy_props=aws_cloudfront.ResponseHeadersPolicyProps(
            response_headers_policy_name=response_headers_policy_name,
            comment=comment,
            custom_headers_behavior=custom_headers_behavior,
            security_headers_behavior=security_headers_behavior,
        )

        ### This "policy" is used within `add_behavior()` re: APIGW
        response_headers_policy = aws_cloudfront.ResponseHeadersPolicy(scope=self, id="RespHdrsPolicy",
            response_headers_policy_name=response_headers_policy_name +'ExactDuplicate',
            comment=comment,
            custom_headers_behavior=custom_headers_behavior,
            security_headers_behavior=security_headers_behavior,
        )
        response_headers_policy.apply_removal_policy(  RemovalPolicy.DESTROY )


        ### -------------------------------
        cloudfront_s3 : aws_cloudfront_s3.CloudFrontToS3 = aws_cloudfront_s3.CloudFrontToS3( ### https://constructs.dev/packages/@aws-solutions-constructs/aws-cloudfront-s3/v/2.48.0?lang=java
            self,
            "frontend",
            bucket_props=s3_bucket_props,
            log_s3_access_logs=True,
            logging_bucket_props=logging_s3_bucket_props,  ### --WHEN-- logS3AccessLogs is false, supplying loggingBucketProps or existingLoggingBucketObj is invalid
            cloud_front_logging_bucket_props=logging_s3_bucket_props,
            # cloud_front_distribution_props= aws_cloudfront.DistributionProps(
            #   domain_names=frontend_domain,
            #   certificate=certificate
            # ),
            cloud_front_distribution_props= {
                ### REF: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distribution-distributionconfig.html
                ### Note: All LHS/Keys are in CamelCase + initial-character is LOWER-case within Python-cdk !!!!
                "priceClass": 'PriceClass_100',  ### for hardcoded JSON like this, can -NOT- use this --> aws_cloudfront.PriceClass.PRICE_CLASS_100.name,
                "webAclId": web_acl_arn,
                ### Following does NOT get recognized at all :-(
                # "restrictions": {
                #     "GeoRestriction": {
                #         ### raw JSON per https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distribution-georestriction.html#cfn-cloudfront-distribution-georestriction-restrictiontype
                #         "RestrictionType": "whitelist", ### whitelist | blacklist | none
                #         "Locations": cloudfront_georestrictions,
                #     },
                # }
            },
            insert_http_security_headers=False,
            response_headers_policy_props=response_headers_policy_props,
        )
        if cloudfront_s3.s3_logging_bucket:
            cloudfront_s3.s3_logging_bucket.apply_removal_policy(RemovalPolicy.DESTROY)
        if cloudfront_s3.cloud_front_logging_bucket:
            cloudfront_s3.cloud_front_logging_bucket.apply_removal_policy(RemovalPolicy.DESTROY)
        cloudfront_s3.cloud_front_logging_bucket_access_log_bucket.apply_removal_policy( RemovalPolicy.DESTROY )

        dump_construct_tree( children_constructs=cloudfront_s3.node.children )
        ### Make sure CustomResource to auto-delete objects completes successfully, before destruction of bucket starts.
        cft_node = cloudfront_s3.node.find_child("S3LoggingBucket")
        Tags.of(cft_node).add(key="ResourceName", value=stk.stack_name+'-CloudFrontS3LoggingBucket-'+Names.unique_id(scope))
        cft_node.node.find_child("AutoDeleteObjectsCustomResource").node.add_dependency( cft_node )
        # cft_node.node.add_dependency( cft_node.node.find_child("AutoDeleteObjectsCustomResource") )
        cft_node :IConstruct = cloudfront_s3.node.find_child("CloudfrontLoggingBucket")
        Tags.of(cft_node).add(key="ResourceName", value=stk.stack_name+'-CloudFrontAccessLoggingBucket-'+Names.unique_id(scope))
        cft_node.node.find_child("AutoDeleteObjectsCustomResource").node.add_dependency( cft_node )
        # cft_node.node.add_dependency( cft_node.node.find_child("AutoDeleteObjectsCustomResource") )

        ### Fix CloudFormation STACK-ERROR -> Bucket cannot have ACLs set with ObjectOwnership's BucketOwnerEnforced setting
        ### Fix cfn-lint ERROR -> E3045 A bucket with AccessControl set should also have OwnershipControl configured
        cloudfront_s3.cloud_front_logging_bucket._object_ownership = aws_s3.ObjectOwnership.OBJECT_WRITER
        # cloudfront_s3.cloud_front_logging_bucket_access_log_bucket._object_ownership = aws_s3.ObjectOwnership.OBJECT_WRITER

        distribution: aws_cloudfront.Distribution = (
            cloudfront_s3.cloud_front_web_distribution
        )
        cfn_distribution: aws_cloudfront.CfnDistribution = distribution.node.default_child
        Tags.of(cft_node).add(key="ResourceName", value=stk.stack_name+'-CloudFrontDistr-'+Names.unique_id(scope))

        loggrp: aws_logs.ILogGroup = get_log_grp( scope=scope,
            tier = tier,
            loggrp_type=LogGroupType.Misc,
            what_is_being_logged = "CloudFrontBktDplymnt",
            # log_group_name="/aws/lambda/"+ lambda_name + "CustRetnn",
        )
        # loggrp: logs.ILogGroup = logs.LogGroup( self, "LogsCustRetnnBktDplymnt",
        #     # log_group_name="/aws/lambda/"+ lambda_name + "CustRetnn",
        #     retention=constants_cdk.get_LOG_RETENTION( self, tier=tier, aws_env=aws_env ),
        #     removal_policy=RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE if tier == constants.PROD_TIER else RemovalPolicy.DESTROY,
        #     # do NOT use -> log_group_class=logs.LogGroupClass.INFREQUENT_ACCESS,   ### Will DENY features like Live Tail, metric extraction / Lambda insights, alarming, or Subscription filters / Export to S3 (that Standard log-class provides)
        # )

        cf_bkt_deploy = s3_deployment.BucketDeployment(     ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_s3_deployment/BucketDeployment.html
            self,
            "deploy_with_invalidation",
            sources=[s3_deployment.Source.asset(ui_build_folder)],
            destination_bucket=cloudfront_s3.s3_bucket_interface,   ### https://github.com/awslabs/aws-solutions-constructs/tree/main/source/patterns/@aws-solutions-constructs/aws-cloudfront-s3
            distribution=distribution,
            distribution_paths=["/*"],
            access_control=aws_s3.BucketAccessControl.PRIVATE,      ### https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_s3/BucketAccessControl.html#aws_cdk.aws_s3.BucketAccessControl
                    ### To address CFT-Stack-ERROR --> Bucket cannot have ACLs set with ObjectOwnership's BucketOwnerEnforced setting
            memory_limit=256,
            prune=True,  # default to True
            retain_on_delete=False,  # default to true
            log_group=loggrp,
            # log_retention=logs.RetentionDays.FIVE_DAYS,       ### [WARNING] aws-cdk-lib.aws_s3_deployment.BucketDeploymentProps#logRetention is deprecated.
        )

        ### ------ API as 2nd Origin -----
        api_origin = aws_cloudfront_origins.HttpOrigin(api_domain, origin_path="/prod")

        api_cache_policy = aws_cloudfront.CachePolicy(
            self,
            "apiCachePolicy"+tier,
            cache_policy_name=stk.stack_name+'-'+stk.region,
            comment="API Cache Policy for "+tier,
            query_string_behavior=aws_cloudfront.CacheQueryStringBehavior.all(),
            default_ttl=Duration.minutes(5),
            max_ttl=Duration.hours(1),
            header_behavior=aws_cloudfront.CacheHeaderBehavior.allow_list("Authorization"),
            # cookie_behavior=aws_cloudfront.CacheCookieBehavior.all(),
        )
        api_cache_policy.apply_removal_policy( RemovalPolicy.DESTROY )

        origin_request_policy = aws_cloudfront.OriginRequestPolicy(
            self,
            "request_policy",
            origin_request_policy_name = f"{stk.stack_name}-{stk.region}-OriginRequestPolicy",  ### Limited to [a-zA-Z_-]+
            comment = f"{constants.CDK_APP_NAME} SPA Origin-Request-Policy for "+tier,
            header_behavior=aws_cloudfront.OriginRequestHeaderBehavior.allow_list("Accept"),
        )

        distribution.add_behavior(
            path_pattern="/api/v1/*",
            origin=api_origin,
            allowed_methods=aws_cloudfront.AllowedMethods.ALLOW_ALL,
            cached_methods=aws_cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
            cache_policy=api_cache_policy,
            origin_request_policy=origin_request_policy,
            response_headers_policy=response_headers_policy,
            viewer_protocol_policy=aws_cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        )

        ### ------------------------
        # Add a georestriction to the distribution.
        # geo_restriction = aws_cloudfront.GeoRestriction(
        #     restriction_type=aws_cloudfront.GeoRestriction.allowlist("US")
        # )
        ### The following ConstructOR generates JSON with LOWER-initial-case `geoRestriction`, instead of UPPER-initial-case.
        # geo_restriction = cfn_distribution.GeoRestrictionProperty(
        #     restriction_type="whitelist",
        #     locations=cloudfront_georestrictions,
        # )
        # restrictions_props = cfn_distribution.RestrictionsProperty(geo_restriction=geo_restriction)
        ### !! Following Line  does --NOT-- work !!
        # cfn_distribution.add_property_override("DistributionConfig.Restrictions.GeoRestriction", restrictions_props)

        geo_restriction = {
            ### raw JSON per https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distribution-georestriction.html#cfn-cloudfront-distribution-georestriction-restrictiontype
            "RestrictionType": "whitelist", ### whitelist | blacklist | none
            "Locations": cloudfront_georestrictions,
        }
        cfn_distribution.add_property_override("DistributionConfig.Restrictions.GeoRestriction", geo_restriction)

        ### Following does NOT work (to set WAF-ACL) !!!!!!!!!!!!
        # if web_acl_arn:
        #     ### given the ARN to a WAF-ACL, apply it to the above APIGW
        #     cfn_distribution.add_property_override("DistributionConfig.WebACLId", web_acl_arn)
        #     # cloudfront_distribution_arn = Fn.sub(f"arn:{stk.partition}:cloudfront::{stk.account}:distribution/{distribution.distribution_id}")
        #     ### !!!!!! ATTENTION !!!!! the dynamic-expression for arn above, is converted into a complex series of Fn::Join and Fn::Ref.
        #     ### That is, it is NOT a simple String inside CloudFormation-Template.
        #     ### Since .. AWS::WAFv2::WebACLAssociation a.k.a. aws_wafv2.CfnWebACLAssociation .. .. only accepts SIMPLE String values..
        #     ### .. the following will FAIL !!!!!!!!!
        #     ### arn:aws:cloudfront::123456789012:distribution/1234567890123456
        #     # wafaclass = aws_wafv2.CfnWebACLAssociation(
        #     #     scope=self,
        #     #     id="wafv2CloudFRONT",
        #     #     web_acl_arn=web_acl_arn,
        #     #     resource_arn=cloudfront_distribution_arn,
        #     # )
        #     # wafaclass.add_dependency(cfn_distribution)

        custom_error_response = [
            {
                "ErrorCachingMinTTL": 10,
                "ErrorCode": 403,
                "ResponseCode": 200,
                "ResponsePagePath": "/index.html",
            }
        ]

        cfn_distribution.add_override( "Properties.DistributionConfig.CustomErrorResponses",   custom_error_response, )
        cfn_distribution.add_property_override(property_path="DistributionConfig.Comment", value=f"{constants.CDK_APP_NAME}-{tier}")

        ### ------------------------
        autogen_cloudfront_domain :str = distribution.distribution_domain_name
        print( f"autogen_cloudfront_domain = '{autogen_cloudfront_domain}'" )

        rt53_hosted_domain_name :str = re.sub( pattern="[a-zA-Z0-9]+\.", repl="", string=frontend_domain_name, count=1, )
        print( f"rt53_hosted_domain_name   = '{rt53_hosted_domain_name}'" )

        # hosted_zone = route53.HostedZone.from_lookup( self, "HostZone",
        #     domain_name=rt53_hosted_domain_name,
        #     private_zone=False,
        # )

        ###___ if tier in constants.GIT_STD_BRANCHES:
        ###___     frontend_domain_name = f"{constants.WEBSITE_DOMAIN_PREFIX}.{domain_name}"
        ###___ else:  ### developer specific tier
        ###___     frontend_domain_name = f"{tier}.{domain_name}"

        # certificate = acm.Certificate( scope=self, id="Certificate",
        #     domain_name=frontend_domain_name,
        #     validation=acm.CertificateValidation.from_dns(hosted_zone=hosted_zone),
        # )
        # Tags.of(certificate).add(key="ResourceName", value="ACMCert-"+frontend_domain_name)
        # # certificate = acm.DnsValidatedCertificate( ### Deprecated. Replaced by acm.Certificate()
        # #     hosted_zone=hosted_zone,
        # #     # domain_name=f"*.{domain_name}",  ### <<------ <<------ <<-------
        # # )

        # viewer_certificate = aws_cloudfront.ViewerCertificate.from_acm_certificate(
        #     certificate=certificate, aliases=[frontend_domain_name]
        # )

        # route53.CnameRecord( self, "CNameAlias-"+frontend_domain_name,
        #     zone=hosted_zone,
        #     record_name=frontend_domain_name,
        #     domain_name=autogen_cloudfront_domain,
        #     # target=route53.RecordTarget.from_alias(
        #     #     targets.CloudFrontTarget(distribution)
        #     # ),
        # )
        # Tags.of(certificate).add(key="ResourceName", value="DNSCNAME-"+frontend_domain_name)

        # ### Cloudformation reference: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distribution-distributionconfig.html#cfn-cloudfront-distribution-distributionconfig-aliases
        # cfn_distribution.add_override( "Properties.DistributionConfig.Aliases", [ frontend_domain_name ], )
        # cfn_distribution.add_override( "Properties.DistributionConfig.ViewerCertificate.AcmCertificateArn", certificate.certificate_arn, )
        # cfn_distribution.add_override( "Properties.DistributionConfig.ViewerCertificate.SslSupportMethod", "sni-only", )
        # cfn_distribution.add_override( "Properties.DistributionConfig.ViewerCertificate.MinimumProtocolVersion", "TLSv1.2_2021", )

        self.frontend_url = "https://"+ frontend_domain_name + "/" ### Attention: CloudFront requires the TRAILING '/' character!
        self.cloudfront_s3 = cloudfront_s3
        self.distribution = distribution
        self.cf_bkt_deploy = cf_bkt_deploy
        # self.viewer_cert = viewer_certificate

# EoF
