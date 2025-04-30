import {
    S3Client,
    ListBucketsCommand,
    ListObjectsV2Command,
    DeleteBucketCommand,
    DeleteObjectCommand,
    ListObjectVersionsCommand,
    DeleteObjectsCommand,
    ListMultipartUploadsCommand,
    AbortMultipartUploadCommand
} from "@aws-sdk/client-s3";

interface LambdaEvent {
    'tier': string;
    'bucket-name': string;
    'only-empty-the-bucket' :string;
}

export const lambdaHandler = async (event: LambdaEvent): Promise<any> => {
    // Get bucket name pattern from event
    console.log(event);
    const tier = event['tier'];
    let bucketNamePattern = event['bucket-name'];
    const emptybucketOnly = event['only-empty-the-bucket'] != undefined;
    console.log(`tier: ${tier}`);
    console.log(`Listing buckets matching pattern: '${bucketNamePattern}'`)
    bucketNamePattern = bucketNamePattern.replace(/{tier}/g, tier)
    console.log(`UPDATED pattern is: '${bucketNamePattern}'`)

    // Create S3 client
    const s3Client = new S3Client({});
    let countOfDeletedObjects = 0;

    // List all buckets
    const listBucketsResponse = await s3Client.send(new ListBucketsCommand({}));
    // console.log(listBucketsResponse);
    if (listBucketsResponse.Buckets) {
        // Extract bucket names
        const bucketNames = listBucketsResponse.Buckets!.map(bucket => bucket.Name);
        // console.log(bucketNames);
        const re = new RegExp(bucketNamePattern);  //// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_expressions#advanced_searching_with_flags

        // Filter bucket names matching the pattern
        const matchingBucketNames = bucketNames.filter(bucketName => re.test(bucketName!) );
        // const matchingBucketNames = bucketNames.filter(bucketName =>
        //     new RegExp(`^${bucketNamePattern.split('*').join('.*')}$`).test(bucketName!)
        // );

        console.log(matchingBucketNames)
        // console.log(`Listing objects in bucket: ${bucketName}`);

        // // List all objects in the bucket
        // const response = await s3Client.send(new ListObjectsV2Command({ Bucket: bucketName }));
        // console.log(response);

        // if (response.Contents) {
        //     // Print object keys
        //     countOfDeletedObjects += response.Contents!.length;
        //     for (const obj of response.Contents || []) {
        //         console.log(`Deleting object at S3-prefix '${obj.Key}' ..`);
        //         const response333 = await s3Client.send(new DeleteObjectCommand({Bucket: bucketName, Key: obj.Key!}))
        //     }
        // } else {
        //     console.log(`--NO-- objects found in bucket: ${bucketName}`);
        // }

        // // Now delete the bucket itself
        // console.log(`About to delete the bucket '${bucketName}' ..`)
        // const response22 = await s3Client.send(new DeleteBucketCommand({Bucket: bucketName}))
        // console.log(response22)
        for (const bucketName of matchingBucketNames) {
            console.log(`Cleaning bucket: ${bucketName}`);

            // 1. Delete all versions and delete markers
            let isVersionListTruncated = true;
            while (isVersionListTruncated) {
                const versionResponse = await s3Client.send(new ListObjectVersionsCommand({
                    Bucket: bucketName
                }));

                if (versionResponse.Versions?.length || versionResponse.DeleteMarkers?.length) {
                    const objectsToDelete = [
                        ...(versionResponse.Versions || []).map(version => ({
                            Key: version.Key!,
                            VersionId: version.VersionId
                        })),
                        ...(versionResponse.DeleteMarkers || []).map(marker => ({
                            Key: marker.Key!,
                            VersionId: marker.VersionId
                        }))
                    ];

                    if (objectsToDelete.length > 0) {
                        await s3Client.send(new DeleteObjectsCommand({
                            Bucket: bucketName,
                            Delete: { Objects: objectsToDelete }
                        }));
                        countOfDeletedObjects += objectsToDelete.length;
                    }
                }

                isVersionListTruncated = versionResponse.IsTruncated || false;
            } // end of while isVersionListTruncated

            // 2. Abort any multipart uploads
            const multipartUploads = await s3Client.send(new ListMultipartUploadsCommand({
                Bucket: bucketName
            }));

            if (multipartUploads.Uploads) {
                for (const upload of multipartUploads.Uploads) {
                    await s3Client.send(new AbortMultipartUploadCommand({
                        Bucket: bucketName,
                        Key: upload.Key,
                        UploadId: upload.UploadId
                    }));
                }
            }

            // 3. Delete current objects (your existing code, but handle pagination)
            let isTruncated = true;
            let continuationToken = undefined;

            while (isTruncated) {
                const listResponse :any = await s3Client.send(new ListObjectsV2Command({
                    Bucket: bucketName,
                    ContinuationToken: continuationToken
                }));

                if (listResponse.Contents && listResponse.Contents.length > 0) {
                    const deleteParams = {
                        Bucket: bucketName,
                        Delete: {
                            Objects: listResponse.Contents.map((obj: { Key: any; }) => ({ Key: obj.Key! }))
                        }
                    };

                    await s3Client.send(new DeleteObjectsCommand(deleteParams));
                    countOfDeletedObjects += listResponse.Contents.length;
                }

                isTruncated = listResponse.IsTruncated || false;
                continuationToken = listResponse.NextContinuationToken;
            } // end of while(isTruncated)

            if (  !  emptybucketOnly) {
                // Finally delete the bucket
                console.log(`About to delete the bucket '${bucketName}'..`);
                await s3Client.send(new DeleteBucketCommand({ Bucket: bucketName }));
            }
        } // for loop

        return {
            statusCode: 200,
            body: `Deleted ${countOfDeletedObjects} objects in buckets matching pattern: ${bucketNamePattern}`
        };
    } else {
        return {
            statusCode: 200,
            body: `NO buckets Found!! Matching the pattern: ${bucketNamePattern}`
        };
    }
};



// import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';

// /**
//  *
//  * Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
//  * @param {Object} event - API Gateway Lambda Proxy Input Format
//  *
//  * Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
//  * @returns {Object} object - API Gateway Lambda Proxy Output Format
//  *
//  */

// export const lambdaHandler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
//     try {
//         return {
//             statusCode: 200,
//             body: JSON.stringify({ }),
//         };
//     } catch (err) {
//         console.log(err);
//         return {
//             statusCode: 500,
//             body: JSON.stringify({
//                 message: 'some error happened',
//             }),
//         };
//     }
// };

