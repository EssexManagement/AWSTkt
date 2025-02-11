#!/bin/bash -f

CognitoIdPIdToken="eyJjdHkiOiJKV1QiLCJlbmMiOiJBMjU2R0NNIiwiYWxnIjoiUlNBLU9BRVAifQ.SMzvbX59FVklzCwZTC4Ob8jOE9_vZ6pnCsL8mNkj5axmM-7Axu8ybQ7wPv31R6TvV0SNDKWs9QPo4-HxxlJwqI7pzI6o1vNhcEwKiqfHmmu6np2KNPD0qE_To3t73b3xYZFFLZ2xTmqpXmiMSXaQWcGx8Gocotau1MA1PAOYvZCdx7bsPA5WU6pJkfYNlYhdQUU-FIAx05yZLAhyMkJlNHee5ymKP0HijUchH4K8Yqq7tDZX-qIitfhdbdR4bqIEoKuD9Y1UfosaeXGr9S8wJ_7zb6B2iVdzF4owPrueTyHz3PuAD7GzLz6isTZRol9mnnTdWpcT2yC0rramuV9A2Q.qks9lz6B6-2p16UD.odUOpI6ZSytUWUCE4glp4b3KXsA0I33rs8fB6LUghrgOCYedDuiafbtKQe59xlFHgvfydZQUQSlWQ0b9JerqZCNs8unwfiR_iQY4k65SqYEzuaKbgOlbNpDxuevv3-rw2G1jTp95i5NyulPtzuGm-TjCObmCMQHl_8ubzEUpNAL7K0OddFg82sKkqSJLoFG450WgeU8vl9QWb-k6t7oA53qMmw1bnXumAvLL2MNTRai6oldnlPi97cSuzpQKlCNtThRQjRyjCspTf6mEqHqLTURNRuceH0yS40LpIZz-34hkw3HlHgnDQB6AOJVIHYKGSCSVc59UglzpW6PUxGAcmhoBw6cgNyrfjfoa0yEg--dKB59KBObsYLnQ-u3rhDwrrjfXz4I2qYTFkra1IjsngzzPAor3sbPUIKXlVkhT904IkXAZThD-eApb_G_8p978g_qF5f7BMREdWV393zQXnB-spraXeKOoRy2grdtx1v8NXZ4KFn7T5cnPOtkwN7bBQHymEOthRtf5MfUDoCHZOOibJ4fqSyt0zDIBfi7Yd3TS_mc26XaeAcua8uzsnF4eNkVVgywfbm4JfJ2WiYAQ3JUqDqv3cfQ0_gK1nMzUxew-wcTyQ7kNFkgYspKUB_R6f7TK5jjmNbzc6OoRD29mJsIiaYy106dIltOPvoYvH_zw_DCabNLqtTZ0wMW3kxtbDyOnwSBT_-JU8DshenT3aorcr-nFAvNrH3wwoX4hM4ibaUN-nZ4UUQ2ijr3Gj7c9pxCVHd0G0ONR2cvd7Ipt3Y3ke7hc4T501uBCjOjZzKpSRLSULDXdiDgVXWcM5Exasw2ugnM0SDuPf-VmuUPPt-tvhAdaGqGv-PCGSGmrpwU9wiyPsd6s9-nSToqJBO-WDBk_CtP5MKsn5lBTfLBQWp679o0hBwnnyO-0kaARxHZvN3Fqhw6fFLeoYKe0XErTVZSPoioaKLoFX21EsCYl2K--wg1ZWvKU_g_MuLxcSzfx35ZUfje-Twzrf5iuvf8laCF5brjnY7uqEAL7yZifgGf1zo6935GZjDcc4aqJqD3R3xwQKEA2ijE4PijwoZsSQO8bckaiTR6UVtAB9HtrzRr-bb6xlG2xMmVSDR66VjLXoFNJlxNXh6nfzua4l-yiy1LgnfVRTRzciSjQZsLo6lJvpSWHHiHGS1_pOtPbF5UJQjHDlR_8H9DQLQrIsylAmM7qNAOCxVvKx3On1gSnw0zI-WXP5u5miCqBAsHiRNm6nqoI8dISUgSyLoXx_ed5afqsIjbTupsvc_CvNfvhl0xWmqolJ2HmZw.tITyqxbwfR9DznpM3duiOQ"

DeveloperTier_APIGW_EndPt="https://6s3lsv5pre.execute-api.us-east-1.amazonaws.com"  ### Note: No trailing '/' chars allowed!

Tier="nccr-2166-waf"

# LambdaName="wakeup_db"
LambdaName="html_to_pdf"
# PayLoad="<html><body><h1>Hello nccr-team Tues Aug 27 12:49 PM ET</h1></body></html>"
# PayLoad="{\"somekey\":\"somevalue\",\"Tier\":\"$Tier\"}"
PayLoad="@/Users/seetamrajuus/Downloads/Non-Replicated-Downloads/html-simple.html"

# Origin="http://localhost/"
Origin="${DeveloperTier_APIGW_EndPt}"

### -----------------------------------
### derived variables
urlResponse_FileOutput="/tmp/${Tier}-${LambdaName}-response"
DeveloperTier_APIGW_EndPt="${DeveloperTier_APIGW_EndPt}/${Tier}"
API_URL="${DeveloperTier_APIGW_EndPt}/api/v1/${LambdaName}"

# URLQueryString="?file_name="${urlResponse_FileOutput:t}
# URLQueryString=""  ### Empty string implies NO QUery-String is passed.
URLQueryString="file_name=NCCR%20Data%20Platform%20Data%20Request%20Form.pdf&"

set -e
set -x
curl -X OPTIONS                                             \
        -H "Authorization: Bearer $CognitoIdPIdToken"       \
        -H "Origin: ${Origin}"                              \
        -H "Access-Control-Request-Method: POST"            \
        -H "Access-Control-Request-Headers: X-Requested-With" \
        --dump-header ${urlResponse_FileOutput}.pre-fetch.headers     \
        ${API_URL}
printf "\nPREFLIGHT OPTIONS-Request returned '$?'\n\n"

curl -X POST  \
        -H "Authorization: Bearer $CognitoIdPIdToken"       \
        -H "Origin: ${Origin}"                              \
        --data "${PayLoad}"                                 \
        -H "Content-Type: application/json"                 \
        --output ${urlResponse_FileOutput}                  \
        --dump-header ${urlResponse_FileOutput}.headers     \
        ${API_URL}${URLQueryString}
EXIT_CODE=$?
set +x

### --------------------------

printf "%.0s_" {1..100} ; echo ""
printf "Curl-CLI's EXIT_CODE = '${EXIT_CODE}'\n\n--PRE-FETCH--\n\n"
cat ${urlResponse_FileOutput}.pre-fetch.headers
echo ""; printf "%.0s_" {1..100} ; echo ""
cat ${urlResponse_FileOutput}.headers
cat ${urlResponse_FileOutput}
echo ""; printf "%.0s_" {1..100} ; echo ""

ls -la ${urlResponse_FileOutput}.base64
# base64 --decode < ${urlResponse_FileOutput} > ${urlResponse_FileOutput}.pdf
# ls -la ${urlResponse_FileOutput}.pdf

### EoInfo
