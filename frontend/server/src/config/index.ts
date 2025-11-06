import dotenv from 'dotenv';
import { SSMClient, GetParameterCommand } from '@aws-sdk/client-ssm';

dotenv.config();

const AWS_REGION = process.env.AWS_REGION || 'us-west-2';
const PROJECT_NAME = process.env.PROJECT_NAME || 'deep-research-agent';
const ENVIRONMENT = process.env.ENVIRONMENT || 'dev';

// Initial config with environment variables (fallback)
export const config = {
  server: {
    port: parseInt(process.env.PORT || '8000', 10),
    nodeEnv: process.env.NODE_ENV || 'development',
  },
  aws: {
    region: AWS_REGION,
  },
  dynamodb: {
    sessionsTable: process.env.DYNAMODB_SESSIONS_TABLE || '',
    statusTable: process.env.DYNAMODB_RESEARCH_STATUS_TABLE || '',
    userPreferencesTable: process.env.DYNAMODB_USER_PREFERENCES_TABLE || '',
  },
  agentcore: {
    runtimeId: process.env.AGENTCORE_RUNTIME_ID || '',
    runtimeArn: process.env.AGENTCORE_RUNTIME_ARN || '',
    memoryId: process.env.AGENTCORE_MEMORY_ID || '',
    chatRuntimeId: process.env.AGENTCORE_CHAT_RUNTIME_ID || '',
    chatRuntimeArn: process.env.AGENTCORE_CHAT_RUNTIME_ARN || '',
    chatMemoryId: process.env.AGENTCORE_CHAT_MEMORY_ID || '',
  },
  s3: {
    outputsBucket: process.env.S3_OUTPUTS_BUCKET || '',
  },
  cors: {
    origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
  },
  auth: {
    enabled: process.env.ENABLE_AUTH === 'true',
    cognitoUserPoolId: process.env.COGNITO_USER_POOL_ID || '',
    cognitoClientId: process.env.COGNITO_CLIENT_ID || '',
  },
};

/**
 * Load configuration from AWS Systems Manager Parameter Store
 * Falls back to environment variables if SSM parameters are not available
 */
export async function loadConfigFromSSM(): Promise<void> {
  const ssmClient = new SSMClient({ region: AWS_REGION });

  const parameters = [
    // Research Agent
    { path: `/${PROJECT_NAME}/${ENVIRONMENT}/agentcore/runtime-arn`, key: 'runtimeArn' },
    { path: `/${PROJECT_NAME}/${ENVIRONMENT}/agentcore/runtime-id`, key: 'runtimeId' },
    { path: `/${PROJECT_NAME}/${ENVIRONMENT}/agentcore/memory-id`, key: 'memoryId' },
    // Chat Agent
    { path: `/${PROJECT_NAME}/${ENVIRONMENT}/agentcore/chat-runtime-arn`, key: 'chatRuntimeArn' },
    { path: `/${PROJECT_NAME}/${ENVIRONMENT}/agentcore/chat-runtime-id`, key: 'chatRuntimeId' },
    { path: `/${PROJECT_NAME}/${ENVIRONMENT}/agentcore/chat-memory-id`, key: 'chatMemoryId' },
    // DynamoDB Tables
    { path: `/${PROJECT_NAME}/${ENVIRONMENT}/dynamodb/status-table`, key: 'statusTable' },
    { path: `/${PROJECT_NAME}/${ENVIRONMENT}/dynamodb/user-preferences-table`, key: 'userPreferencesTable' },
    // S3
    { path: `/${PROJECT_NAME}/${ENVIRONMENT}/s3/outputs-bucket`, key: 'outputsBucket' },
  ];

  console.log('🔄 Loading configuration from Parameter Store...');

  for (const param of parameters) {
    try {
      const command = new GetParameterCommand({ Name: param.path });
      const response = await ssmClient.send(command);

      if (response.Parameter?.Value) {
        // Update config based on parameter key
        if (param.key === 'runtimeArn') {
          config.agentcore.runtimeArn = response.Parameter.Value;
        } else if (param.key === 'runtimeId') {
          config.agentcore.runtimeId = response.Parameter.Value;
        } else if (param.key === 'memoryId') {
          config.agentcore.memoryId = response.Parameter.Value;
        } else if (param.key === 'chatRuntimeArn') {
          config.agentcore.chatRuntimeArn = response.Parameter.Value;
        } else if (param.key === 'chatRuntimeId') {
          config.agentcore.chatRuntimeId = response.Parameter.Value;
        } else if (param.key === 'chatMemoryId') {
          config.agentcore.chatMemoryId = response.Parameter.Value;
        } else if (param.key === 'statusTable') {
          config.dynamodb.statusTable = response.Parameter.Value;
        } else if (param.key === 'userPreferencesTable') {
          config.dynamodb.userPreferencesTable = response.Parameter.Value;
        } else if (param.key === 'outputsBucket') {
          config.s3.outputsBucket = response.Parameter.Value;
        }
        console.log(`  ✅ Loaded ${param.key} from ${param.path}`);
      }
    } catch (error: any) {
      console.warn(`  ⚠️  Failed to load ${param.path}: ${error.message}`);
      console.warn(`     Using environment variable fallback for ${param.key}`);
    }
  }

  console.log('✅ Configuration loaded');
}

export function validateConfig() {
  const required = [
    { key: 'AWS_REGION', value: config.aws.region },
    { key: 'DYNAMODB_RESEARCH_STATUS_TABLE', value: config.dynamodb.statusTable },
    { key: 'AGENTCORE_RUNTIME_ARN', value: config.agentcore.runtimeArn },
    { key: 'AGENTCORE_CHAT_RUNTIME_ARN', value: config.agentcore.chatRuntimeArn },
  ];

  const missing = required.filter(({ value }) => !value);

  if (missing.length > 0) {
    throw new Error(
      `Missing required configuration: ${missing.map(({ key }) => key).join(', ')}`
    );
  }

  console.log('📋 Configuration:');
  console.log(`   AWS Region: ${config.aws.region}`);
  console.log(`   Status Table: ${config.dynamodb.statusTable}`);
  console.log(`   Research Agent Runtime ARN: ${config.agentcore.runtimeArn}`);
  console.log(`   Research Agent Runtime ID: ${config.agentcore.runtimeId || 'N/A'}`);
  console.log(`   Chat Agent Runtime ARN: ${config.agentcore.chatRuntimeArn}`);
  console.log(`   Chat Agent Runtime ID: ${config.agentcore.chatRuntimeId || 'N/A'}`);
  console.log(`   S3 Outputs Bucket: ${config.s3.outputsBucket || 'N/A'}`);
}
