import {
  BedrockAgentCoreClient,
  InvokeAgentRuntimeCommand,
  ListEventsCommand,
  GetEventCommand,
} from '@aws-sdk/client-bedrock-agentcore';
import { config } from '../config';
import { AgentCoreInvokeRequest, AgentCoreInvokeResponse } from '../types';

const client = new BedrockAgentCoreClient({ region: config.aws.region });

/**
 * Invoke AgentCore Runtime to start research workflow
 */
export async function invokeResearchWorkflow(
  sessionId: string,
  request: AgentCoreInvokeRequest
): Promise<AgentCoreInvokeResponse> {
  try {
    console.log(`🚀 Invoking AgentCore Runtime for session ${sessionId}`);
    console.log('   ARN:', config.agentcore.runtimeArn);
    console.log('   Request:', JSON.stringify(request, null, 2));

    if (!config.agentcore.runtimeArn) {
      throw new Error('AGENTCORE_RUNTIME_ARN not configured');
    }

    // Prepare payload for AgentCore Runtime
    const payload = {
      topic: request.topic,
      research_config: request.researchConfig,
      session_id: sessionId,
      user_id: request.userId,
    };

    // Debug: Check reference materials with PDF
    const refMaterials = request.researchConfig?.reference_materials || [];
    if (refMaterials.length > 0) {
      console.log(`📎 Reference materials: ${refMaterials.length}`);
      refMaterials.forEach((ref: any, idx: number) => {
        if (ref.type === 'pdf' && ref.pdf_bytes_base64) {
          console.log(`   PDF ${idx}: ${ref.title}`);
          console.log(`   Base64 length: ${ref.pdf_bytes_base64.length} chars`);
          console.log(`   Estimated size: ${(ref.pdf_bytes_base64.length * 0.75 / 1024 / 1024).toFixed(2)} MB`);
        }
      });
    }

    // Validate userId is provided (no fallback!)
    if (!request.userId) {
      throw new Error('userId is required for invokeResearchWorkflow - authentication not provided');
    }

    const userId = request.userId;

    // Invoke AgentCore Runtime using InvokeAgentRuntimeCommand
    const response = await client.send(
      new InvokeAgentRuntimeCommand({
        agentRuntimeArn: config.agentcore.runtimeArn,
        qualifier: 'DEFAULT',
        contentType: 'application/json',
        accept: 'text/event-stream',
        payload: Buffer.from(JSON.stringify(payload)),
        runtimeUserId: userId,
        runtimeSessionId: sessionId,
      })
    );

    console.log(`✅ AgentCore Runtime invoked successfully`);
    console.log(`   Trace ID: ${response.traceId}`);

    // The workflow runs asynchronously and streams results
    // We return immediately and let the client poll for status
    return {
      session_id: sessionId,
      status: 'processing',
      trace_id: response.traceId,
    };
  } catch (error) {
    console.error('❌ Failed to invoke research workflow:', error);
    throw new Error(`Failed to invoke research workflow: ${error}`);
  }
}

/**
 * Check workflow status from AgentCore Runtime
 *
 * This would typically poll the AgentCore Runtime or check a status endpoint
 */
export async function checkWorkflowStatus(
  sessionId: string
): Promise<{ status: string; result?: any }> {
  try {
    // TODO: Implement actual status check
    // This might involve:
    // 1. Polling AgentCore Runtime status endpoint
    // 2. Checking DynamoDB for updates (if workflow writes there)
    // 3. Using EventBridge events

    console.log(`Checking workflow status for session ${sessionId}`);

    // Placeholder response
    return {
      status: 'processing',
    };
  } catch (error) {
    console.error('Failed to check workflow status:', error);
    throw new Error(`Failed to check workflow status: ${error}`);
  }
}

/**
 * Get workflow results from AgentCore Runtime
 */
export async function getWorkflowResults(
  sessionId: string
): Promise<any> {
  try {
    // TODO: Implement actual results retrieval
    // This might involve:
    // 1. Fetching from S3 (if results are stored there)
    // 2. Reading from DynamoDB
    // 3. Calling AgentCore Runtime results endpoint

    console.log(`Getting workflow results for session ${sessionId}`);

    // Placeholder response
    return {
      session_id: sessionId,
      status: 'completed',
      report_file: `s3://bucket/reports/${sessionId}.docx`,
    };
  } catch (error) {
    console.error('Failed to get workflow results:', error);
    throw new Error(`Failed to get workflow results: ${error}`);
  }
}

/**
 * Query AgentCore Memory for a specific session
 * Uses list_events API to fetch all events for a research session
 */
export async function queryAgentCoreMemory(
  sessionId: string,
  actorId: string,
  maxResults: number = 100
): Promise<any[]> {
  try {
    console.log(`📋 Querying AgentCore Memory for session: ${sessionId}, actor: ${actorId}`);

    if (!config.agentcore.memoryId) {
      throw new Error('AGENTCORE_MEMORY_ID not configured');
    }

    const command = new ListEventsCommand({
      memoryId: config.agentcore.memoryId,
      sessionId: sessionId,
      actorId: actorId,
      includePayloads: true,
      maxResults: maxResults,
    });

    const response = await client.send(command);

    // Parse and return events
    const events: any[] = [];
    if (response.events) {
      for (const event of response.events) {
        try {
          // Payload is an array with blob structure: [{ blob: "..." }]
          let payload: any = event.payload;
          let parsedPayload: any = {};

          // Extract blob from array
          if (Array.isArray(payload) && payload.length > 0 && payload[0]?.blob) {
            const blobStr = String(payload[0].blob);
            parsedPayload = JSON.parse(blobStr);
          } else if (typeof payload === 'string') {
            parsedPayload = JSON.parse(payload);
          } else {
            parsedPayload = payload;
          }

          // Extract event_type from payload data
          const eventType = parsedPayload?.event_type || (event as any).eventType || 'unknown';
          const timestamp = (event as any).createdAt || parsedPayload?.timestamp || new Date().toISOString();

          events.push({
            eventId: event.eventId || 'unknown',
            type: eventType,
            timestamp: timestamp,
            dimension: parsedPayload?.dimension,
            aspect: parsedPayload?.aspect,
            data: parsedPayload || {},
            status: 'completed', // Events in memory are completed
          });
        } catch (parseError) {
          console.warn('Failed to parse event:', parseError);
        }
      }
    }

    // Sort events by timestamp
    events.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

    console.log(`✅ Retrieved ${events.length} events from AgentCore Memory`);

    // Log event types for debugging
    const eventTypes = events.map(e => e.type);
    console.log('Event types:', eventTypes);

    // Log first event for structure inspection
    if (events.length > 0) {
      console.log('Sample event:', JSON.stringify(events[0], null, 2));
    }

    return events;
  } catch (error) {
    console.error('❌ Failed to query AgentCore Memory:', error);
    throw new Error(`Failed to query AgentCore Memory: ${error}`);
  }
}

/**
 * Get detailed event content from AgentCore Memory
 */
export async function getEventDetails(eventId: string, sessionId: string, actorId: string): Promise<any> {
  try {
    console.log(`📋 Getting event details for: ${eventId}, session: ${sessionId}, actor: ${actorId}`);

    if (!config.agentcore.memoryId) {
      throw new Error('AGENTCORE_MEMORY_ID not configured');
    }

    if (!sessionId || !actorId) {
      throw new Error('sessionId and actorId are required for getEventDetails');
    }

    const command = new GetEventCommand({
      memoryId: config.agentcore.memoryId,
      eventId: eventId,
      sessionId: sessionId,
      actorId: actorId,
    });

    const response = await client.send(command);

    console.log(`✅ Retrieved event details`);

    return response.event;
  } catch (error) {
    console.error('❌ Failed to get event details:', error);
    throw new Error(`Failed to get event details: ${error}`);
  }
}
