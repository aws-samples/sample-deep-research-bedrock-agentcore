import { BedrockAgentCoreClient, ListEventsCommand } from '@aws-sdk/client-bedrock-agentcore';
import { getStatus } from './dynamodb';
import { config } from '../config';

const client = new BedrockAgentCoreClient({ region: config.aws.region });

export interface ResearchContext {
  research_session_id: string;
  topic: string;
  research_type: string;
  research_depth: string;
  research_context?: string;
  dimensions: Array<{
    name: string;
    aspects: Array<{
      name: string;
      reasoning: string;
      key_questions: string[];
    }>;
  }>;
  dimension_count: number;
  total_aspects: number;
}

/**
 * Load research context from DynamoDB and AgentCore Memory
 *
 * This fetches the research structure (dimensions and aspects) that will be
 * provided to the chat agent for context-aware conversations.
 */
export async function loadResearchContext(
  researchSessionId: string
): Promise<ResearchContext | null> {
  try {
    console.log(`[ResearchContext] Loading context for session ${researchSessionId}`);

    // 1. Get metadata from DynamoDB
    const status = await getStatus(researchSessionId);
    if (!status || status.status !== 'completed') {
      console.warn(`[ResearchContext] Research not found or not completed: ${researchSessionId}`);
      return null;
    }

    // 2. Query AgentCore Memory for dimensions_identified event
    if (!config.agentcore.memoryId) {
      console.error('[ResearchContext] Research memory ID not configured');
      return null;
    }

    const command = new ListEventsCommand({
      memoryId: config.agentcore.memoryId,
      sessionId: researchSessionId,
      actorId: 'default_user', // Research agent uses this actor ID
      includePayloads: true,
      maxResults: 100,
    });

    const response = await client.send(command);

    // 3. Find dimensions_identified event
    let dimensionsEvent: any = null;

    for (const event of response.events || []) {
      try {
        const payload = event.payload;
        let parsedPayload: any = {};

        // Parse blob format payload
        if (Array.isArray(payload) && payload.length > 0 && payload[0]?.blob) {
          const blobStr = String(payload[0].blob);
          parsedPayload = JSON.parse(blobStr);
        } else if (typeof payload === 'string') {
          parsedPayload = JSON.parse(payload);
        } else {
          parsedPayload = payload;
        }

        if (parsedPayload.event_type === 'dimensions_identified') {
          dimensionsEvent = parsedPayload;
          break;
        }
      } catch (parseError) {
        console.debug('[ResearchContext] Failed to parse event:', parseError);
        continue;
      }
    }

    if (!dimensionsEvent) {
      console.warn(`[ResearchContext] No dimensions_identified event found for ${researchSessionId}`);
      return null;
    }

    // 4. Extract dimensions and aspects structure
    const dimensions = Object.entries(dimensionsEvent.aspects_by_dimension || {}).map(
      ([dimName, aspects]: [string, any]) => ({
        name: dimName,
        aspects: aspects.map((asp: any) => ({
          name: asp.name,
          reasoning: asp.reasoning,
          key_questions: asp.key_questions || [],
        })),
      })
    );

    const context: ResearchContext = {
      research_session_id: researchSessionId,
      topic: status.topic,
      research_type: status.research_type,
      research_depth: status.research_depth,
      research_context: status.research_context,
      dimensions,
      dimension_count: dimensionsEvent.dimension_count || dimensions.length,
      total_aspects:
        dimensionsEvent.total_aspects ||
        dimensions.reduce((sum, d) => sum + d.aspects.length, 0),
    };

    console.log(
      `[ResearchContext] ✅ Loaded: ${context.dimension_count} dimensions, ${context.total_aspects} aspects`
    );

    return context;
  } catch (error: any) {
    console.error('[ResearchContext] Failed to load:', error);
    return null;
  }
}
