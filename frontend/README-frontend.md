# Troubleshooting & Fixes

## AWS::CloudFront::OriginRequestPolicy: .. .. .. same name already exists

```bash
TIER=.. .. .. !! .. ..

RESPONSE="/tmp/json"
aws cloudfront list-origin-request-policies --profile $AWSPROFILE --region $AWSREGION > ${RESPONSE}

jq ".OriginRequestPolicyList.Items[] | select(.OriginRequestPolicy.OriginRequestPolicyConfig.Name | startswith(\"FACTfrontend${TIER}frontendrequestpolicy\")).OriginRequestPolicy" ${RESPONSE}
### Copy value of "ID" from output

ID=.. .. .. !! .. ..
aws cloudfront get-origin-request-policy --id ${ID} --profile $AWSPROFILE --region $AWSREGION | grep -i etag
### Copy value of "ETag" from output

ETag=.. .. !! .. ..
aws cloudfront delete-origin-request-policy --id ${ID} --if-match ${ETag} --profile $AWSPROFILE --region $AWSREGION
```

<HR/>

## AWS::CloudFront::ResponseHeadersPolicy: .. .. .. same name already exists

NOTE: We run the following commands for these 2 values:

1. `RespHdrPol=${TIER}_X-Content-Type-Options_is_nosniff__Strict-Transport-Security`
1. `RespHdrPol=${TIER}_X-Content-Type-Options_is_nosniff__Strict-Transport-SecurityExactDuplicate`

Repeating: Cmds below must be run for each different value of `RespHdrPol` BASH-Shell-Variabl.

```bash
TIER=.. .. .. !! .. ..

RESPONSE="/tmp/json"
aws cloudfront list-response-headers-policies --profile $AWSPROFILE --region $AWSREGION > ${RESPONSE}

jq ".ResponseHeadersPolicyList.Items[] | select(.ResponseHeadersPolicy.ResponseHeadersPolicyConfig.Name == \"${RespHdrPol}\").ResponseHeadersPolicy" ${RESPONSE}
### Copy value of "ID" from output

ID=.. .. .. !! .. ..
aws cloudfront get-response-headers-policy --id ${ID} --profile $AWSPROFILE --region $AWSREGION | grep -i etag
### Copy value of "ETag" from output

ETag=.. .. !! .. ..
aws cloudfront delete-response-headers-policy --id ${ID} --if-match ${ETag} --profile $AWSPROFILE --region $AWSREGION
```

/EoF
