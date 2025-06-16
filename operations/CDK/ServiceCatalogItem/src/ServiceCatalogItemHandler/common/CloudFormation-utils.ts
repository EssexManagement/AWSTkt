// import * as https from 'https';

/**
 *    lambda-to-handle-itops-user-input-to-service-catalog-item@1.0.0 build
 *    npx esbuild --bundle index.ts --entry-names=index --minify --target=ES2020 --sourcemap --keep-names --format=cjs --sources-content=true --tree-shaking=true --outdir=dist
 *
 *    ✘ [ERROR] Could not resolve "https"
 *        index.ts:1:23:
 *          1 │ import * as https from 'https';
 *            ╵                        ~~~~~~~
 *    The package "https" wasn't found on the file system but is built into node.
 *    Are you trying to bundle for `node`?
 *    You can use "--platform=node" to do that, which will remove this error.
 */

//// ...................................................................

export type CustomResourceInvocationStatus = "SUCCESS" | "FAILED";

export interface CloudFormationResponse {
    Status: CustomResourceInvocationStatus;
    Reason: string;
    StackId: string;
    RequestId: string;
    LogicalResourceId: string;
    PhysicalResourceId: string;
    Data?: Record<string, any>;
    ValidationErrors ?: string[];
}

//// ...................................................................

export const sendResponse = async (event: any, response: CloudFormationResponse): Promise<void> => {
    const responseBodyAsStr = JSON.stringify(response);
    const responseUrl = new URL(event.ResponseURL);
    const u = responseUrl.toString();
    //// for security-reasons, from `u` remove the values for `Amz-Security-Token`, `X-Amz-Credential` and `X-Amz-Signature`
    const sanitizedUrl = u.replace(/(X-Amz-Security-Token|X-Amz-Credential|X-Amz-Signature)=([^&]+)/g, "$1=***");
    console.log( "About to .. contact "+ sanitizedUrl );

    const result = await fetch(responseUrl, {
        method: 'PUT',
        body: responseBodyAsStr,  //// must be Stringified-JSON only.
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': responseBodyAsStr.length.toString()
        }
    });
    console.log("Available properties:", Object.keys(result));
    console.log( "http's response: Ok? "+ result?.ok +"  & status-code: "+ result?.status +" & textual-response: ");
    console.log( result?.body );

    if (!result.ok) {
        throw new Error(`HTTP ${result.status}: ${result.statusText}`);
    }
    console.log( "Successfully sent response BACK to CloudFormation re: ServiceCatalogItem Launch/Termination" );

    //// Following code needs `import http` module!!!
    // const requestOptions = {
    //     hostname: responseUrl.hostname,
    //     port: 443,
    //     path: responseUrl.pathname + responseUrl.search,
    //     method: 'PUT',
    //     headers: {
    //         'Content-Type': '',
    //         'Content-Length': responseBodyAsStr.length
    //     }
    // };
    // return new Promise((resolve, reject) => {
    //     const request = https.request(requestOptions, (response) => {
    //         let responseData = '';
    //         response.on('data', (chunk) => {
    //             responseData += chunk;
    //         });

    //         response.on('end', () => {
    //             if (response.statusCode && response.statusCode >= 400) {
    //                 reject(new Error(`HTTP ${response.statusCode}: ${responseData}`));
    //             } else {
    //                 resolve(responseData);
    //             }
    //         });
    //     });

    //     request.on('error', (error) => {
    //         console.log('Error sending response:', error);
    //         reject(error);
    //     });

    //     request.write(responseBodyAsStr);
    //     request.end();
    // });
};

//// EoF
