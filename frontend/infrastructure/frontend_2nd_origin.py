"""frontend construct."""
from typing import Any
from aws_cdk import (
    Fn,
    Stack,
    Duration,
    RemovalPolicy,
    aws_kms,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_secretsmanager,
)

from constructs import Construct

import constants
import cdk_utils.CdkDotJson_util as CdkDotJson_util
from backend.infra.backend_security_construct import BackendWAFConstruct

class Frontend2ndOrigin(Construct):
    """Frontend Construct for APIGW as 2nd Origin
    """

    def __init__(self,
        scope: "Construct",
        id_: str,
        tier :str,
        distribution: cloudfront.Distribution,
        public_api_FQDN :str,
        x_origin_verify_hdr_token_value :str,
        # x_origin_verify_hdr_secret :aws_secretsmanager.ISecret,
    ) -> None:
        """Frontend Construct for APIGW as 2nd Origin

        Args:
            scope (Construct): _description_
            id_ (str): _description_
            aliasToCloudFrontDistribution: an FQDN a.k.a. full Domain-name of website.
            distribution (cloudfront.Distribution): The CloudFront distribution to the primary SPA-website (to attach a 2nd origin to)
            public_api_FQDN (str): the full-qualified domain-name for the Public-RestApi (example: qcyriwfh3g.execute-api.us-east-1.amazonaws.com )
        """
        super().__init__(scope, id_)

        stk = Stack.of(self)

        # TODO: Remove these lines.
        ### No good, as cannot invoke add_behavior() on it.
        # distribution : cloudfront.Distribution.IDistribution = cloudfront.Distribution.from_distribution_attributes(
        #     scope=self,
        #     id="ImportedDistribution",
        #     distribution_id=distribution_id,
        #     domain_name=alias2cfdistrib
        # )
        # backend_stateless_stack = f"{tier}-stateless"
        # imported_api_url = Fn.import_value(f"{backend_stateless_stack}-PublicAPIGWUrl")
        # public_api_FQDN = Fn.parse_domain_name(distribution.distribution_domain_name)

        if tier not in constants.UPPER_TIERS: ### Developer-branch tier
            referrer_policy=cloudfront.HeadersReferrerPolicy.NO_REFERRER
        else:
            referrer_policy=cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN
        my_security_headers_behavior = cloudfront.ResponseSecurityHeadersBehavior(
            ### https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_cloudfront.ResponseHeadersCorsBehavior.html
            content_type_options = cloudfront.ResponseHeadersContentTypeOptions(override=True),
            content_security_policy=cloudfront.ResponseHeadersContentSecurityPolicy(
                content_security_policy="default-src https:;'",
                override=True,
            ),
            strict_transport_security = cloudfront.ResponseHeadersStrictTransportSecurity(
                access_control_max_age=Duration.minutes(30),
                include_subdomains=True,
                override=True,
                # preload=True,
            ),
            referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                override=True,
                referrer_policy=referrer_policy,
            ),
            frame_options=cloudfront.ResponseHeadersFrameOptions(frame_option=cloudfront.HeadersFrameOption.DENY, override=True),
            # xss_protection=cloudfront.ResponseHeadersXSSProtection(protection=True, mode_block=False, override=True)
        )

        ### ------- Cloudfront-Options ---------
        if tier in constants.PROD_TIER:
            ### Do NOT allow localhost-CORS within PROD/UAT tiers.
            my_cors_behavior = None
        else:
            ### `dev`/|`test` Tier or Developer-branch tier
            my_cors_behavior = cloudfront.ResponseHeadersCorsBehavior(
                origin_override=True,    ### True -- can be very problematic. It can NOT conflict with "override" in rest of this file!!!
                access_control_allow_credentials=True,  ### Required param
                ### AccessControlAllowCredentials: When this is set to true, AccessControlAllowOrigins can --NOT-- be a wildcard ("*") according to CORS specifications. This combination might be causing the internal error.

                access_control_allow_origins=["*"],
                # access_control_allow_origins=["http://localhost:8080", f"https://{distribution.distribution_domain_name}"],
                # access_control_allow_origins=["http://localhost:8080", f"https://{distribution.distribution_domain_name}", alias2cfdistrib ],
                ### ❌ Circular dependency between resources: [frontendS3BucketAutoDeleteObjectsCustomResourceE571885D, frontendS3BucketPolicy3983F953, frontendCloudFrontDistribution9A9D1AD6, 2ndorigRHP02626231, frontenddeploywithinvalidationCustomResource256MiB79BD9A65]

                access_control_allow_methods=["ALL"],   ### Warning! '*' will Not work. You'll get a wierd Cloudformation error -- Internal error reported from downstream service during operation 'AWS::CloudFront::ResponseHeadersPolicy'.
                        ### https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-responseheaderspolicy-accesscontrolallowmethods.html
                access_control_allow_headers=[
                        # BackendWAFConstructWAFConstruct.origin_token_http_header_name(), ### Our own new custom-header. Look for it in this file.
                        "Authorization", "Accept", "Content-Type", "Origin",
                        "X-Amz-Invocation-Type", "X-Amz-Log-Type", "X-Amzn-Trace-Id", "X-Forwarded-For", "X-Amz-Security-Token", "X-Amz-User-Agent",
                        "X-Amz-Cors-Allow-Origin", "X-Amz-Cors-Allow-Methods", "X-Requested-With", "Access-Control-Allow-Origin"
                    ],
                        ### WARNING: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Access-Control-Allow-Headers
                        ### In requests with credentials, it is treated as the literal header name * without special semantics.
                        ### Note that the Authorization header can't be wildcarded and always needs to be listed explicitly.
                # access_control_allow_headers=["Content-Type", "Authorization"],
                # access_control_expose_headers=["*"],
                # access_control_max_age=Duration.minutes(30),
            )

        ### For api-origins, disable caching completely.
        # api_cache_policy = cloudfront.CachePolicy(
        #     self,
        #     "CFCachePol",
        #     cache_policy_name=stk.stack_name+'-'+stk.region,
        #     comment="CloudFront Cache-Policy for PublicAPIGW in tier="+tier,
        #     # header_behavior=cloudfront.CacheHeaderBehavior.allow_list("Authorization"),
        #     query_string_behavior=cloudfront.CacheQueryStringBehavior.all(),
        #     cookie_behavior=cloudfront.CacheCookieBehavior.all(),
        #     default_ttl=Duration.seconds(0),  ### Since this caching for APIGW-APIs, disable caching!!
        #     max_ttl=Duration.seconds(0),      ### Since this caching for APIGW-APIs, disable caching!!
        #     min_ttl=Duration.seconds(0)       ### Since this caching for APIGW-APIs, disable caching!!
        # )
        # api_cache_policy.node.add_dependency(x_origin_verify_hdr_secret)

        ### !!! WARNING !!! For API Gateway, you should use the managed policy "AllViewerExceptHostHeader".
        # my_origin_request_policy = cloudfront.OriginRequestPolicy( self, "request_policy",
        #     origin_request_policy_name = stk.stack_name+'-'+stk.region,
        #     header_behavior=cloudfront.OriginRequestHeaderBehavior.all(),
        #     query_string_behavior=cloudfront.OriginRequestQueryStringBehavior.all(),
        #     cookie_behavior=cloudfront.OriginRequestCookieBehavior.all(),
        # )

        # response_header_policy_id = self.node.get_context("apigw")["response-header-policy-id"]
        # my_response_headers_policy = cloudfront.ResponseHeadersPolicy.from_response_headers_policy_id(self,"RHP",response_header_policy_id)
        my_response_headers_policy = cloudfront.ResponseHeadersPolicy(
            scope=self,
            id="RHP",
            response_headers_policy_name="RHP-2ndOrigin-"+stk.stack_name,
            comment=f"{stk.stack_name} 2nd-origin to a APIGW-RestApi",
            cors_behavior=my_cors_behavior,
            # custom_headers_behavior=?,
            security_headers_behavior=my_security_headers_behavior,
        )

        ### ------ API as 2nd Origin -----
        api_origin_custom_headers={
            BackendWAFConstruct.origin_token_http_header_name(): x_origin_verify_hdr_token_value,
        } if x_origin_verify_hdr_token_value else None
        # api_origin_custom_headers={
        #     BackendWAFConstruct.origin_token_http_header_name(): Fn.join('', [
        #         '{{resolve:secretsmanager:',
        #         x_origin_verify_hdr_secret.secret_arn,
        #         ':SecretString}}'
        #     ]),
        # } if x_origin_verify_hdr_secret else None

        api_origin = origins.HttpOrigin(
            domain_name = public_api_FQDN,
            origin_path = f"/prod",
            # origin_path = f"/{tier}",
            custom_headers = api_origin_custom_headers
        )

        distribution.add_behavior(
            path_pattern="/api/v1/*",
            origin=api_origin,
            allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            # cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
            cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
            cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,  # Add this if not present
            origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                        ### !!! WARNING !!! For API Gateway, you should use the managed policy "AllViewerExceptHostHeader".
            response_headers_policy=my_response_headers_policy,
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ### Q is hallucinating re: handling ERROR-responses
            # origin_failover_criteria={
            #     'statusCodes': [500, 502, 503, 504]
            # }
        )
