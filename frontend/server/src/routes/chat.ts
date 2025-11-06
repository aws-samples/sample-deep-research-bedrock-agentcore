import { Router, Request, Response } from 'express';
import { getChatHistory } from '../services/agentcore-memory';
import { invokeChatAgent } from '../services/agentcore-chat';
import { loadResearchContext } from '../services/research-context';
import { config } from '../config';
import {
  getChatSessions,
  createChatSession,
  updateChatSession,
  deleteChatSession,
  getChatSessionById,
} from '../services/dynamodb';

const router = Router();

/**
 * POST /api/chat/message
 * Send a chat message and get AI response via AgentCore Runtime
 */
router.post('/message', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string || 'anonymous';
    const { session_id, research_session_id, message, model_id } = req.body;

    // Validate request
    if (!session_id || !research_session_id || !message) {
      return res.status(400).json({
        error: 'Missing required fields: session_id, research_session_id, message',
      });
    }

    console.log(`[Chat] User ${userId} - Session ${session_id} - Research ${research_session_id}`);
    console.log(`[Chat] Message: ${message}`);

    // Load research context
    let researchContext = null;
    if (research_session_id) {
      try {
        researchContext = await loadResearchContext(research_session_id);
        if (researchContext) {
          console.log(
            `[Chat] Loaded research context: ${researchContext.dimension_count} dimensions, ${researchContext.total_aspects} aspects`
          );
        } else {
          console.warn(`[Chat] Could not load research context for ${research_session_id}`);
        }
      } catch (error) {
        console.error('[Chat] Error loading research context:', error);
        // Continue without context
      }
    }

    // Update session updated_at in DynamoDB
    try {
      await updateChatSession(userId, session_id, {
        updated_at: new Date().toISOString(),
      });
    } catch (error) {
      console.warn('[Chat] Failed to update session timestamp:', error);
    }

    // Set headers for Server-Sent Events (SSE)
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    // Call Chat AgentCore Runtime and stream response in real-time
    // Messages are automatically saved to AgentCore Memory by the agent
    const stream = await invokeChatAgent(
      userId,
      session_id,
      message,
      model_id,
      research_session_id,
      researchContext  // Pass research context
    );

    // Stream chunks in real-time from AgentCore Runtime
    if (stream && typeof stream[Symbol.asyncIterator] === 'function') {
      let buffer = '';
      let chunkCount = 0;
      let lastChunkText = '';  // Track last chunk to detect duplicates

      for await (const chunk of stream as AsyncIterable<any>) {
        const chunkStr = Buffer.from(chunk).toString('utf-8');
        buffer += chunkStr;
        chunkCount++;

        // SSE events are separated by double newlines (\n\n)
        const events = buffer.split('\n\n');

        // Keep the last incomplete event in the buffer
        buffer = events.pop() || '';

        // Process complete events
        for (const event of events) {
          if (!event.trim()) continue;

          // Parse SSE format: "data: {json}"
          // An SSE event can have multiple lines, but we want to process each data line as a separate event
          const lines = event.split('\n');

          // Collect all data lines from this event
          const dataLines: string[] = [];
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              dataLines.push(line.substring(6)); // Remove "data: " prefix
            }
          }

          // Process each data line (each should be a complete JSON object)
          for (const jsonStr of dataLines) {
            if (!jsonStr.trim()) continue;

            try {
              // Parse the JSON data
              const data = JSON.parse(jsonStr);

              // Forward chunk, tool, or done event to frontend
              if (data.type === 'chunk') {
                // Debug: log chunk to detect duplicates
                if (data.chunk === lastChunkText) {
                  console.warn(`[Chat] ⚠️ Duplicate chunk detected: "${data.chunk.substring(0, 20)}..."`);
                  // Skip duplicate chunks
                  continue;
                }
                lastChunkText = data.chunk;

                console.log(`[Chat] 📤 Forwarding chunk #${chunkCount}: "${data.chunk.substring(0, 20)}..."`);
                res.write(`data: ${JSON.stringify({ chunk: data.chunk })}\n\n`);
              } else if (data.type === 'tool_start') {
                // Forward tool usage information to frontend
                console.log(`[Chat] 🔧 Tool called: ${data.tool_name}`);
                res.write(`data: ${JSON.stringify({
                  type: 'tool_start',
                  tool_id: data.tool_id,
                  tool_name: data.tool_name,
                  input: data.input
                })}\n\n`);
              } else if (data.type === 'done') {
                res.write(`data: ${JSON.stringify({
                  type: 'done',
                  session_id: data.session_id,
                  response: data.response,
                  model: data.model,
                  timestamp: data.timestamp,
                  tool_calls: data.tool_calls || []
                })}\n\n`);
              } else if (data.type === 'error') {
                console.error('[Chat] Error from AgentCore:', data.error);
                res.write(`data: ${JSON.stringify({ type: 'error', error: data.error })}\n\n`);
              }
            } catch (parseError) {
              console.error('[Chat] Failed to parse chunk:', parseError);
              console.error('[Chat] Raw chunk:', jsonStr.substring(0, 200));
            }
          }
        }
      }
    } else {
      console.error('[Chat] Invalid stream received');
      res.write(`data: ${JSON.stringify({ type: 'error', error: 'Invalid stream from AgentCore' })}\n\n`);
    }

    res.end();
  } catch (error: any) {
    console.error('[Chat] Failed to process message:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/chat/:researchSessionId/history
 * Get chat history from AgentCore Memory for a specific session
 */
router.get('/:researchSessionId/history', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string || 'anonymous';
    const { researchSessionId } = req.params;
    const sessionId = req.query.session_id as string;
    const limit = parseInt(req.query.limit as string) || 100;

    console.log(`[Chat] Get history for research ${researchSessionId}, session ${sessionId}, user ${userId}`);

    if (!sessionId) {
      return res.json({
        research_session_id: researchSessionId,
        messages: [],
        count: 0,
      });
    }

    // Check if session exists and is not deleted in DynamoDB
    const session = await getChatSessionById(userId, sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Session not found or deleted' });
    }

    // Get actual messages from AgentCore Memory
    const messages = await getChatHistory(userId, sessionId, limit);

    res.json({
      research_session_id: researchSessionId,
      session_id: sessionId,
      messages: messages,
      count: messages.length,
    });
  } catch (error: any) {
    console.error('[Chat] Failed to get chat history:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/chat/sessions
 * Get all chat sessions for a user from DynamoDB
 */
router.get('/sessions', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string || 'anonymous';

    console.log(`[Chat] Get sessions for user ${userId}`);

    // Get session metadata from DynamoDB (only non-deleted sessions)
    const sessions = await getChatSessions(userId);

    // Map research_id to research_session_id for frontend compatibility
    const mappedSessions = sessions.map(session => ({
      ...session,
      research_session_id: session.research_id
    }));

    res.json({
      sessions: mappedSessions,
      count: mappedSessions.length,
    });
  } catch (error: any) {
    console.error('[Chat] Failed to get chat sessions:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/chat/sessions
 * Create a new chat session in DynamoDB
 */
router.post('/sessions', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string || 'anonymous';
    const { session_id, research_id, model_id, title } = req.body;

    if (!session_id || !model_id) {
      return res.status(400).json({
        error: 'Missing required fields: session_id, model_id',
      });
    }

    console.log(`[Chat] Creating session ${session_id} for user ${userId}`);

    await createChatSession(userId, session_id, research_id, model_id, title);

    res.json({
      created: true,
      session_id,
    });
  } catch (error: any) {
    console.error('[Chat] Failed to create session:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * PATCH /api/chat/sessions/:sessionId
 * Update a chat session in DynamoDB
 */
router.patch('/sessions/:sessionId', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string || 'anonymous';
    const { sessionId } = req.params;
    const updates = req.body;

    console.log(`[Chat] Updating session ${sessionId} for user ${userId}:`, updates);

    // Update session in DynamoDB
    await updateChatSession(userId, sessionId, updates);

    res.json({
      updated: true,
      session_id: sessionId,
    });
  } catch (error: any) {
    console.error('[Chat] Failed to update session:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * DELETE /api/chat/sessions/:sessionId
 * Soft delete a chat session (mark as deleted in DynamoDB)
 * AgentCore Memory events are preserved
 */
router.delete('/sessions/:sessionId', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string || 'anonymous';
    const { sessionId } = req.params;

    console.log(`[Chat] Soft deleting session ${sessionId} for user ${userId}`);

    // Soft delete in DynamoDB (AgentCore Memory events preserved)
    await deleteChatSession(userId, sessionId);

    res.json({
      deleted: true,
      session_id: sessionId,
    });
  } catch (error: any) {
    console.error('[Chat] Failed to delete session:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;
