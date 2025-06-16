/**
 *  monolithic JavaScript lambda, that I will manually configure to run ..
 *  .. inside a specific VPC, specific-subnet and Specific SG, so that ..
 *  ..  it will help me to test egress a.k.a. outbound network connectivity from within that VPC+Subnet+SG combo.
 */

// export const helloFromLambdaHandler = async () => {
//     // If you change this message, you will need to change hello-from-lambda.test.mjs
//     const message = 'Hello from Lambda!';
//     // All log statements are written to CloudWatch
//     console.info(`${message}`);
//     return message;
// }

// const https = require('https');
// const dns = require('dns');
// const { promisify } = require('util');
// const { exec } = require('child_process');

//// ES module imports:
import https from 'https';
import * as dns from 'dns';
import { promisify } from 'util';
import { exec } from 'child_process';

const execPromise = promisify(exec);
const dnsLookupPromise = promisify(dns.lookup);

// List of endpoints to test connectivity to
const ENDPOINTS_TO_TEST = [
    { url: 'https://api.amazonaws.com', name: 'AWS API' },
    { url: 'https://dynamodb.us-east-1.amazonaws.com', name: 'DynamoDB' },
    { url: 'https://s3.amazonaws.com', name: 'S3' },
    { url: 'https://secretsmanager.us-east-1.amazonaws.com', name: 'Secrets Manager' },
    { url: 'https://www.google.com', name: 'Google (Internet)' },
    { url: 'https://www.whitehouse.gov', name: "USA President's WhiteHouse website" },
    { url: 'https://www.example.com', name: 'Example.com (Internet)' }
];

// Function to test HTTP connectivity to an endpoint
async function testHttpConnectivity(endpoint) {
    return new Promise((resolve) => {
        const startTime = Date.now();

        try {
            const req = https.get(endpoint.url, (res) => {
                const endTime = Date.now();
                resolve({
                    endpoint: endpoint.name,
                    url: endpoint.url,
                    status: res.statusCode,
                    latency: endTime - startTime,
                    success: res.statusCode >= 200 && res.statusCode < 400
                });
            });

            req.on('error', (error) => {
                resolve({
                    endpoint: endpoint.name,
                    url: endpoint.url,
                    error: error.message,
                    success: false
                });
            });

            req.setTimeout(5000, () => {
                req.abort();
                resolve({
                    endpoint: endpoint.name,
                    url: endpoint.url,
                    error: 'Timeout after 5 seconds',
                    success: false
                });
            });
        } catch (error) {
            resolve({
                endpoint: endpoint.name,
                url: endpoint.url,
                error: error.message,
                success: false
            });
        }
    });
}

// Function to test DNS resolution
async function testDnsResolution(hostname) {
    try {
        const result = await dnsLookupPromise(hostname);
        return {
            hostname,
            ip: result.address,
            success: true
        };
    } catch (error) {
        return {
            hostname,
            error: error.message,
            success: false
        };
    }
}

// Function to get network configuration
async function getNetworkConfig() {
    try {
        // Get network interfaces
        const { stdout: ifconfigOutput } = await execPromise('ifconfig || ip addr');

        // Get routing table
        const { stdout: routeOutput } = await execPromise('netstat -rn || ip route');

        // Get DNS configuration
        const { stdout: resolvOutput } = await execPromise('cat /etc/resolv.conf');

        return {
          interfaces: ifconfigOutput,
          routes: routeOutput,
          dns: resolvOutput
        };
    } catch (error) {
        return {
            error: error.message
        };
    }
}

// Main handler function
export const handler = async (event, context) => {
    console.log('Starting network connectivity tests');

    try {
        // Get Lambda environment info
        const environment = {
            region: process.env.AWS_REGION,
            functionName: process.env.AWS_LAMBDA_FUNCTION_NAME,
            functionVersion: process.env.AWS_LAMBDA_FUNCTION_VERSION,
            memoryLimitInMB: process.env.AWS_LAMBDA_FUNCTION_MEMORY_SIZE,
            logGroupName: process.env.AWS_LAMBDA_LOG_GROUP_NAME,
            logStreamName: process.env.AWS_LAMBDA_LOG_STREAM_NAME
        };

        // Get network configuration
        const networkConfig = await getNetworkConfig();

        // Test DNS resolution for each endpoint
        const dnsResults = await Promise.all(
            ENDPOINTS_TO_TEST.map(endpoint => {
                const hostname = new URL(endpoint.url).hostname;
                return testDnsResolution(hostname);
            })
        );

        // Test HTTP connectivity to each endpoint
        const connectivityResults = await Promise.all(
            ENDPOINTS_TO_TEST.map(endpoint => testHttpConnectivity(endpoint))
        );

        // Compile results
        const results = {
            timestamp: new Date().toISOString(),
            environment,
            networkConfig,
            dnsResults,
            connectivityResults,
            summary: {
                totalTests: connectivityResults.length,
                successfulTests: connectivityResults.filter(r => r.success).length,
                failedTests: connectivityResults.filter(r => !r.success).length
            }
        };

        console.log('Network connectivity test results:', JSON.stringify(results, null, 2));

        return {
            statusCode: 200,
            body: JSON.stringify(results, null, 2),
            headers: { 'Content-Type': 'application/json' }
        };
    } catch (error) {
        console.error('Error during network connectivity tests:', error);

        return {
            statusCode: 500,
            body: JSON.stringify({
                error: error.message,
                stack: error.stack
            }),
            headers: { 'Content-Type': 'application/json' }
        };
    }
};

//// EoF
