import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';

import dns from 'dns/promises';

async function resolveDns() {
    try {
        const FQDN = 'secretsmanager.us-east-1.amazonaws.com';
        console.log('Resolving DNS for:', FQDN);
        const addresses = await dns.resolve4( FQDN );
        console.log('IP addresses are:');
        console.log( addresses );
        console.log( '-'.repeat(80) )

        // For more detailed DNS information including TTL
        console.log('Resolving full DNS records for:', FQDN);
        const records = await dns.resolveAny( FQDN );
        console.log('Full DNS records:');
        console.log( records );
        console.log( '-'.repeat(80) )

        return addresses;
    } catch (error) {
        console.error('DNS resolution failed:', error);
        throw error;
    }
}

export const handler = async (event) => {
    const secretArn = "arn:aws:secretsmanager:us-east-1:924221118260:secret:ClinicalTrialFinder/prod/clinicaltrialsapi.cancer.gov-Niet96";
    const secretName = "ClinicalTrialFinder/prod/clinicaltrialsapi.cancer.gov";

    const ips = await resolveDns();

    // get value from secret manager
    console.log("initializing AWS-SDK client")
    const client = new SecretsManagerClient();
    console.log("Invoking GetSecretValue() ..")
    const command = new GetSecretValueCommand({SecretId: secretArn});
    const response = await client.send(command);
    console.log("GetSecretValue() response: received!");
    const secret = response.SecretString;
    console.log("secret's value successfully accessed.");

    const lambdaResponse = {
      statusCode: 200,
      body: JSON.stringify('Hello from Lambda!')
    };

    return lambdaResponse;
};
