import {
  BedrockAgentCoreClient,
  InvokeAgentRuntimeCommand,
} from '@aws-sdk/client-bedrock-agentcore';
import { config } from '../config';
import type { ResearchContext } from './research-context';

const client = new BedrockAgentCoreClient({ region: config.aws.region });

/**
 * Invoke Chat AgentCore Runtime to process a chat message
 */
export async function invokeChatAgent(
  userId: string,
  sessionId: string,
  message: string,
  modelId?: string,
  researchSessionId?: string,
  researchContext?: ResearchContext | null
): Promise<any> {
  return invokeChatAgentStreaming(userId, sessionId, message, modelId, researchSessionId, researchContext);
}

/**
 * Invoke Chat Agent and return the full response (non-streaming)
 */
export async function invokeChatAgentNonStreaming(
  userId: string,
  sessionId: string,
  message: string,
  modelId?: string,
  researchSessionId?: string,
  researchContext?: ResearchContext | null
): Promise<any> {
  try {
    console.log(`🚀 Invoking Chat AgentCore Runtime`);
    console.log(`   User: ${userId}, Session: ${sessionId}`);
    console.log(`   ARN: ${config.agentcore.chatRuntimeArn}`);

    if (!config.agentcore.chatRuntimeArn) {
      throw new Error('AGENTCORE_CHAT_RUNTIME_ARN not configured');
    }

    // Prepare payload for Chat Agent
    const payload = {
      user_id: userId,
      session_id: sessionId,
      message: message,
      model_id: modelId,
      research_session_id: researchSessionId,
      research_context: researchContext,
    };

    console.log('   Payload:', JSON.stringify({...payload, research_context: researchContext ? 'present' : 'null'}, null, 2));

    // Invoke Chat AgentCore Runtime
    const response = await client.send(
      new InvokeAgentRuntimeCommand({
        agentRuntimeArn: config.agentcore.chatRuntimeArn,
        qualifier: 'DEFAULT',
        contentType: 'application/json',
        accept: 'text/event-stream', // Accept streaming response
        payload: Buffer.from(JSON.stringify(payload)),
        runtimeUserId: userId,
        runtimeSessionId: sessionId,
      })
    );

    console.log(`✅ Chat AgentCore Runtime invoked successfully`);
    console.log(`   Trace ID: ${response.traceId}`);
    console.log(`   Status Code: ${response.statusCode}`);

    // Parse response payload using SDK's transformToString method
    let result: any = {};
    if (response.response) {
      console.log('   Reading response stream...');
      // Use SDK's built-in method to convert stream to string
      const payloadStr = await response.response.transformToString();
      console.log(`   Response payload length: ${payloadStr.length}`);
      console.log(`   Response payload: ${payloadStr.substring(0, 200)}...`);

      result = JSON.parse(payloadStr);

      // If the response has a body (from lambda_handler), extract it
      if (result.body) {
        result = typeof result.body === 'string' ? JSON.parse(result.body) : result.body;
      }
    } else {
      console.warn('⚠️ No response payload received');
    }

    return {
      ...result,
      trace_id: response.traceId,
    };
  } catch (error: any) {
    console.error('❌ Failed to invoke Chat AgentCore Runtime:', error);
    throw new Error(`Failed to invoke Chat AgentCore Runtime: ${error.message}`);
  }
}

/**
 * Invoke Chat Agent and stream the response
 */
export async function invokeChatAgentStreaming(
  userId: string,
  sessionId: string,
  message: string,
  modelId?: string,
  researchSessionId?: string,
  researchContext?: ResearchContext | null
): Promise<ReadableStream> {
  try {
    console.log(`🚀 Invoking Chat AgentCore Runtime (Streaming)`);
    console.log(`   User: ${userId}, Session: ${sessionId}`);
    if (researchContext) {
      console.log(`   Research context: ${researchContext.dimension_count} dimensions, ${researchContext.total_aspects} aspects`);
    }

    if (!config.agentcore.chatRuntimeArn) {
      throw new Error('AGENTCORE_CHAT_RUNTIME_ARN not configured');
    }

    const payload = {
      user_id: userId,
      session_id: sessionId,
      message: message,
      model_id: modelId,
      research_session_id: researchSessionId,
      research_context: researchContext,
    };

    // Invoke Chat AgentCore Runtime
    const response = await client.send(
      new InvokeAgentRuntimeCommand({
        agentRuntimeArn: config.agentcore.chatRuntimeArn,
        qualifier: 'DEFAULT',
        contentType: 'application/json',
        accept: 'text/event-stream',
        payload: Buffer.from(JSON.stringify(payload)),
        runtimeUserId: userId,
        runtimeSessionId: sessionId,
      })
    );

    console.log(`✅ Chat AgentCore Runtime invoked - streaming response`);
    console.log(`   Trace ID: ${response.traceId}`);

    // Return the raw stream
    return response.response as any;
  } catch (error: any) {
    console.error('❌ Failed to invoke Chat AgentCore Runtime:', error);
    throw new Error(`Failed to invoke Chat AgentCore Runtime: ${error.message}`);
  }
}
