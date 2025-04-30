import {
    EC2Client,
    DescribeNetworkInterfacesCommand,
    DescribeNetworkInterfacesCommandInput,
    DescribeSecurityGroupsCommand,
    DescribeSecurityGroupsCommandInput,
    DescribeSecurityGroupsCommandOutput,
    DeleteNetworkInterfaceCommand,
    DeleteNetworkInterfaceCommandInput,
    DeleteNetworkInterfaceCommandOutput,
} from "@aws-sdk/client-ec2";

import {
    LambdaClient,
    ListFunctionsCommand,
    GetFunctionCommand
} from "@aws-sdk/client-lambda";

//// .............................................................................

export
async function findOrphanEnisForSg(securityGroupId: string): Promise<string[]> {
    const ec2Client = new EC2Client({});

    const params: DescribeNetworkInterfacesCommandInput = {
        Filters: [{
            Name: 'group-id',
            Values: [securityGroupId]
        }]
    };

    try {
        const command = new DescribeNetworkInterfacesCommand(params);
        const response = await ec2Client.send(command);

        // Filter for ENIs that are not in use
        const orphanEnis = response.NetworkInterfaces
            ?.filter(eni => !eni.Attachment || eni.Status === 'available')
            .map(eni => eni.NetworkInterfaceId || '')
            .filter(id => id.trim() !== '');

        return orphanEnis || [];
    } catch (error) {
        console.error('Error finding orphan ENIs:', error);
        throw error;
    }
}

//// .............................................................................

export
async function listAllSecurityGroups(): Promise<string[]> {
    const ec2Client = new EC2Client({});
    const params: DescribeSecurityGroupsCommandInput = {
        MaxResults: 1000,
    };

    try {
        const command = new DescribeSecurityGroupsCommand(params); //// https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/client/ec2/command/DescribeSecurityGroupsCommand/
        const response = await ec2Client.send(command);

        // Extract security group IDs
        const securityGroupIds = response.SecurityGroups
            ?.map(group => group.GroupId || '')
            .filter(id => id.trim() !== '');

        return securityGroupIds || [];
    } catch (error) {
        console.error('Error listing security groups:', error);
        throw error;
    }
}

//// .............................................................................

export
async function findAllOrphanENIs(): Promise<string[]> {
    const allSGs = await listAllSecurityGroups();
    console.log(`All SGs are:`);
    console.log(allSGs);
    const orphanEnis: string[] = [];

    for (const SGid of allSGs) {
        const enis = await findOrphanEnisForSg(SGid);
        if ( enis && enis.length > 0 ) {
            console.log(`Orphan ENIs for SG '${SGid}' are:`);
            console.log(enis)
            // console.log(JSON.stringify(enis,undefined,4));
            orphanEnis.push(...enis);
        } else {
            console.log(`No orphan ENIs for SG '${SGid}'`);
        }
    }

    return orphanEnis;
}

//// .............................................................................

export
async function deleteAllOrphanENIs(): Promise<Number> {
    const allOrphanENIs = await findAllOrphanENIs();
    var numDeleted = 0
    for (const eniId of allOrphanENIs) {
        try {
            const ec2Client = new EC2Client({});
            const params: DeleteNetworkInterfaceCommandInput = {
                NetworkInterfaceId: eniId
            };
            const command = new DeleteNetworkInterfaceCommand(params); //// https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/client/ec2/command/DeleteNetworkInterfaceCommand/
            const response = await ec2Client.send(command);
            console.log(`Deleted ENI: ${eniId}`);
            numDeleted ++;
        } catch (error) {
            console.error(`Error deleting ENI ${eniId}:`, error);
        }
    }
    console.log(`Total # of ENIs deleted: ${numDeleted}`);
    return numDeleted;
}

//// .............................................................................

export
interface LambdaDetails {
    functionName: string;
    securityGroupIds: string[];
    subnetIds: string[];
}

//// ........................

/**
 * Find all the 𝜆s that are using a specific Security-Group (given SG-ID)
 * @param securityGroupId
 * @returns LambdaDetails[] which will never be undefined.
 */
export
async function findLambdasUsingSG(securityGroupId: string): Promise<LambdaDetails[]> {
    const lambdaClient = new LambdaClient({});
    const results: LambdaDetails[] = [];

    try {
        // List all Lambda functions
        const listCommand = new ListFunctionsCommand({});
        const listResponse = await lambdaClient.send(listCommand);

        // Process each function
        for (const func of listResponse.Functions || []) {
            if (!func.FunctionName) continue;

            // Get detailed function configuration
            const getCommand = new GetFunctionCommand({
                FunctionName: func.FunctionName
            });

            const funcDetails = await lambdaClient.send(getCommand);
            const vpcConfig = funcDetails.Configuration?.VpcConfig;

            // Check if function uses the specified security group
            if (vpcConfig?.SecurityGroupIds?.includes(securityGroupId)) {
                results.push({
                    functionName: func.FunctionName,
                    securityGroupIds: vpcConfig.SecurityGroupIds || [],
                    subnetIds: vpcConfig.SubnetIds || []
                });
            }
        }

        return results;

    } catch (error) {
        console.error('Error finding Lambda functions:', error);
        throw error;
    }
  }

//// .............................................................................

//// Example usage:
async function main() {
    try {
        const securityGroupId = 'sg-12345678';

        // Find orphan ENIs
        const orphanEnis = await findOrphanEnisForSg(securityGroupId);
        console.log('Orphan ENIs:', orphanEnis);

        // Find Lambda functions using the security group
        const lambdaFunctions = await findLambdasUsingSG(securityGroupId);
        console.log('Lambda functions using security group:', lambdaFunctions);
    } catch (error) {
        console.error('Error in main:', error);
    }
}

//EoF
