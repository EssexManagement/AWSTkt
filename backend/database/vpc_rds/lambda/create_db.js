const AWS = require('aws-sdk')
const RDS = new AWS.RDSDataService()
 
exports.handler = async (event, context) => {
    console.log(JSON.stringify(event, null, 2))  // Log the entire event passed in

    // Get the sqlStatement string value
    // TODO: Implement a more secure way (e.g. "escaping") the string to avoid SQL injection
    var sqlStatement = event.sqlStatement;

    // The Lambda environment variables for the Aurora Cluster Arn, Database Name, and the AWS Secrets Arn hosting the master credentials of the serverless db
    var DBSecretsStoreArn = process.env.DBSecretsStoreArn;
    var DBAuroraClusterArn = process.env.DBAuroraClusterArn;
    var DatabaseName = process.env.DatabaseName;
    
    const params = {
      awsSecretStoreArn: DBSecretsStoreArn,
      dbClusterOrInstanceArn: DBAuroraClusterArn,
      sqlStatements: sqlStatement,
      database: DatabaseName
    }

    try {
      let dbResponse = await RDS.executeSql(params)
      console.log(JSON.stringify(dbResponse, null, 2))
      
      return JSON.stringify(dbResponse)

    } catch (error) {
        console.log(error)
      return error
    }
}

rds = boto3.resource ('rds')
rds.executeSql(para)