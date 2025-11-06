import {
  BedrockAgentCoreClient,
  ListEventsCommand,
  ListSessionsCommand,
} from '@aws-sdk/client-bedrock-agentcore';
import { config } from '../config';

const client = new BedrockAgentCoreClient({ region: config.aws.region });

/**
 * Get chat history from AgentCore Memory
 * Uses the STM strategy to retrieve conversation history
 */
export async function getChatHistory(
  userId: string,
  sessionId: string,
  limit: number = 100
): Promise<any[]> {
  try {
    console.log(`📋 Getting chat history - userId: ${userId}, sessionId: ${sessionId}`);

    if (!config.agentcore.chatMemoryId) {
      throw new Error('AGENTCORE_CHAT_MEMORY_ID not configured');
    }

    const command = new ListEventsCommand({
      memoryId: config.agentcore.chatMemoryId,
      sessionId: sessionId,
      actorId: userId,
      includePayloads: true,
      maxResults: limit,
    });

    const response = await client.send(command);

    const messages: any[] = [];
    if (response.events) {
      console.log(`🔍 Processing ${response.events.length} events from AgentCore Memory`);

      for (const event of response.events) {
        try {
          // Parse payload
          let payload: any = event.payload;
          let parsedPayload: any = {};

          console.log(`🔍 Event ID: ${event.eventId}, payload type:`, typeof payload);

          // Handle Strands conversational format
          if (Array.isArray(payload) && payload.length > 0) {
            const firstItem = payload[0];

            // Check for conversational format (Strands)
            if (firstItem.conversational) {
              console.log(`🔍 Detected Strands conversational format`);
              const conversational = firstItem.conversational;
              const contentText = conversational.content?.text;

              if (contentText) {
                // Parse the nested JSON string
                const messageData = JSON.parse(contentText);
                const message = messageData.message;

                parsedPayload = {
                  role: message.role,
                  content: message.content[0]?.text || '',
                  timestamp: message.created_at
                };
                console.log(`🔍 Parsed from Strands format: role=${parsedPayload.role}`);
              }
            }
            // Check for blob format (research events)
            else if (firstItem.blob) {
              const blobStr = String(firstItem.blob);
              parsedPayload = JSON.parse(blobStr);
              console.log(`🔍 Parsed from blob:`, Object.keys(parsedPayload));
            }
          } else if (typeof payload === 'string') {
            parsedPayload = JSON.parse(payload);
            console.log(`🔍 Parsed from string:`, Object.keys(parsedPayload));
          } else {
            parsedPayload = payload;
            console.log(`🔍 Direct payload:`, Object.keys(parsedPayload || {}));
          }

          console.log(`🔍 Final parsed - Role: ${parsedPayload?.role}, Content length: ${(parsedPayload?.content || '').length}`);

          const timestamp = (event as any).createdAt || parsedPayload?.timestamp || new Date().toISOString();

          const message = {
            session_id: sessionId,
            timestamp: timestamp,
            role: parsedPayload?.role || 'user',
            content: parsedPayload?.content || parsedPayload?.message || '',
            model: parsedPayload?.model || '',
            message_id: event.eventId || 'unknown',
          };

          console.log(`✅ Added message: role=${message.role}, content=${message.content.substring(0, 50)}...`);
          messages.push(message);
        } catch (parseError) {
          console.warn('[AgentCore Memory] Failed to parse event:', parseError);
          console.warn('[AgentCore Memory] Event payload:', JSON.stringify(event.payload).substring(0, 200));
        }
      }
    }

    // Sort by timestamp
    messages.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

    // Merge consecutive messages with the same role (for multi-turn agent executions)
    const mergedMessages: any[] = [];
    for (const message of messages) {
      const lastMessage = mergedMessages[mergedMessages.length - 1];

      // If same role as previous message, merge content with newline
      if (lastMessage && lastMessage.role === message.role) {
        lastMessage.content += '\n\n' + message.content;
        lastMessage.timestamp = message.timestamp; // Use latest timestamp
        console.log(`🔗 Merged ${message.role} message into previous (multi-turn execution)`);
      } else {
        // Different role or first message - add as new message
        mergedMessages.push(message);
      }
    }

    console.log(`✅ Retrieved ${messages.length} messages (merged to ${mergedMessages.length}) from AgentCore Memory`);

    return mergedMessages;
  } catch (error: any) {
    console.error('[AgentCore Memory] Failed to get chat history:', error);
    throw error;
  }
}

/**
 * Get list of chat sessions for a user
 * Uses list_sessions API for efficient session retrieval
 */
export async function getChatSessions(
  userId: string,
  limit: number = 50
): Promise<any[]> {
  try {
    console.log(`📋 Getting chat sessions for userId: ${userId}`);

    if (!config.agentcore.chatMemoryId) {
      throw new Error('AGENTCORE_CHAT_MEMORY_ID not configured');
    }

    const command = new ListSessionsCommand({
      memoryId: config.agentcore.chatMemoryId,
      actorId: userId,
      maxResults: limit,
    });

    const response = await client.send(command);

    const sessions: any[] = [];
    if (response.sessionSummaries) {
      for (const summary of response.sessionSummaries) {
        // Get the last message for preview (get first few events from each session)
        let lastMessage = null;
        let messageCount = 0;

        try {
          const historyCommand = new ListEventsCommand({
            memoryId: config.agentcore.chatMemoryId,
            sessionId: summary.sessionId,
            actorId: userId,
            includePayloads: true,
            maxResults: 10, // Get last few messages for preview
          });

          const historyResponse = await client.send(historyCommand);

          if (historyResponse.events && historyResponse.events.length > 0) {
            messageCount = historyResponse.events.length;

            // Get the last event for preview
            const lastEvent = historyResponse.events[historyResponse.events.length - 1];
            let payload: any = lastEvent.payload;
            let parsedPayload: any = {};

            if (Array.isArray(payload) && payload.length > 0 && payload[0]?.blob) {
              const blobStr = String(payload[0].blob);
              parsedPayload = JSON.parse(blobStr);
            } else if (typeof payload === 'string') {
              parsedPayload = JSON.parse(payload);
            } else {
              parsedPayload = payload;
            }

            lastMessage = {
              content: parsedPayload?.content || parsedPayload?.message || '',
              timestamp: (lastEvent as any).createdAt || parsedPayload?.timestamp,
              role: parsedPayload?.role || 'user',
            };
          }
        } catch (historyError) {
          console.warn(`[AgentCore Memory] Failed to get history for session ${summary.sessionId}:`, historyError);
        }

        sessions.push({
          session_id: summary.sessionId,
          created_at: summary.createdAt?.toISOString() || new Date().toISOString(),
          message_count: messageCount,
          last_message: lastMessage,
        });
      }
    }

    // Sort by created_at descending
    sessions.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    console.log(`✅ Retrieved ${sessions.length} chat sessions from AgentCore Memory`);

    return sessions;
  } catch (error: any) {
    console.error('[AgentCore Memory] Failed to get chat sessions:', error);

    // If actor not found, return empty array (no sessions yet)
    if (error.name === 'ResourceNotFoundException' ||
        error.message?.includes('Actor') && error.message?.includes('not found')) {
      console.log(`ℹ️  No sessions found for actor ${userId} - returning empty array`);
      return [];
    }

    throw error;
  }
}
