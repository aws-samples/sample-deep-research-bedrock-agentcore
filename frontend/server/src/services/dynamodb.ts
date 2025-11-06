import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import {
  DynamoDBDocumentClient,
  PutCommand,
  GetCommand,
  UpdateCommand,
  DeleteCommand,
  ScanCommand,
  QueryCommand,
} from '@aws-sdk/lib-dynamodb';
import { config } from '../config';
import { ResearchStatus, UserPreferences, ChatSession } from '../types';

const client = new DynamoDBClient({ region: config.aws.region });
const docClient = DynamoDBDocumentClient.from(client);

/**
 * Research Status Management (single source of truth)
 */
export async function createOrUpdateStatus(status: ResearchStatus): Promise<void> {
  await docClient.send(
    new PutCommand({
      TableName: config.dynamodb.statusTable,
      Item: {
        ...status,
        updated_at: new Date().toISOString(),
      },
    })
  );
}

export async function getStatus(sessionId: string): Promise<ResearchStatus | null> {
  const result = await docClient.send(
    new GetCommand({
      TableName: config.dynamodb.statusTable,
      Key: { session_id: sessionId },
    })
  );

  return (result.Item as ResearchStatus) || null;
}

export async function getStatusForUser(
  sessionId: string,
  userId: string
): Promise<ResearchStatus | null> {
  const status = await getStatus(sessionId);

  // User ownership validation - user_id must match exactly
  if (!status || status.user_id !== userId) {
    return null;
  }

  return status;
}

export async function updateStatus(
  sessionId: string,
  updates: Partial<ResearchStatus>
): Promise<void> {
  const updateExpression: string[] = [];
  const expressionAttributeNames: Record<string, string> = {};
  const expressionAttributeValues: Record<string, any> = {};

  Object.entries(updates).forEach(([key, value]) => {
    if (key !== 'session_id') {
      updateExpression.push(`#${key} = :${key}`);
      expressionAttributeNames[`#${key}`] = key;
      expressionAttributeValues[`:${key}`] = value;
    }
  });

  // Always update updated_at
  updateExpression.push('#updated_at = :updated_at');
  expressionAttributeNames['#updated_at'] = 'updated_at';
  expressionAttributeValues[':updated_at'] = new Date().toISOString();

  await docClient.send(
    new UpdateCommand({
      TableName: config.dynamodb.statusTable,
      Key: { session_id: sessionId },
      UpdateExpression: `SET ${updateExpression.join(', ')}`,
      ExpressionAttributeNames: expressionAttributeNames,
      ExpressionAttributeValues: expressionAttributeValues,
    })
  );
}

export async function listStatus(userId: string, limit: number = 50): Promise<ResearchStatus[]> {
  // Query by user_id using GSI
  const result = await docClient.send(
    new QueryCommand({
      TableName: config.dynamodb.statusTable,
      IndexName: 'user-id-index',
      KeyConditionExpression: 'user_id = :uid',
      ExpressionAttributeValues: {
        ':uid': userId,
      },
      Limit: limit,
      ScanIndexForward: false, // Most recent first
    })
  );

  return (result.Items as ResearchStatus[]) || [];
}

export async function deleteStatus(sessionId: string): Promise<void> {
  await docClient.send(
    new DeleteCommand({
      TableName: config.dynamodb.statusTable,
      Key: { session_id: sessionId },
    })
  );
}

/**
 * Comment Management (stored in Status table)
 */
export async function getComments(sessionId: string): Promise<any[]> {
  const status = await getStatus(sessionId);
  return status?.comments || [];
}

export async function addComment(sessionId: string, comment: any): Promise<void> {
  const status = await getStatus(sessionId);
  const comments = status?.comments || [];

  comments.push({
    ...comment,
    created_at: comment.created_at || new Date().toISOString(),
  });

  await updateStatus(sessionId, { comments });
}

export async function updateComment(sessionId: string, commentId: string, updates: any): Promise<void> {
  const status = await getStatus(sessionId);
  const comments = status?.comments || [];

  const updatedComments = comments.map((c: any) =>
    c.id === commentId ? { ...c, ...updates, updated_at: new Date().toISOString() } : c
  );

  await updateStatus(sessionId, { comments: updatedComments });
}

export async function deleteComment(sessionId: string, commentId: string): Promise<void> {
  const status = await getStatus(sessionId);
  const comments = status?.comments || [];

  const filteredComments = comments.filter((c: any) => c.id !== commentId);

  await updateStatus(sessionId, { comments: filteredComments });
}

export async function addCommentReply(sessionId: string, commentId: string, reply: any): Promise<void> {
  const status = await getStatus(sessionId);
  const comments = status?.comments || [];

  const updatedComments = comments.map((c: any) => {
    if (c.id === commentId) {
      return {
        ...c,
        replies: [...(c.replies || []), { ...reply, timestamp: new Date().toISOString() }],
      };
    }
    return c;
  });

  await updateStatus(sessionId, { comments: updatedComments });
}

/**
 * Version Management (stored in Status table)
 */
export async function getVersions(sessionId: string): Promise<Record<string, any>> {
  const status = await getStatus(sessionId);
  return status?.versions || {};
}

export async function getCurrentVersion(sessionId: string): Promise<string> {
  const status = await getStatus(sessionId);
  return status?.current_version || 'draft';
}

/**
 * User Preferences Management
 */
export async function getUserPreferences(userId: string): Promise<UserPreferences | null> {
  const result = await docClient.send(
    new GetCommand({
      TableName: config.dynamodb.userPreferencesTable,
      Key: { user_id: userId },
    })
  );

  return (result.Item as UserPreferences) || null;
}

export async function saveUserPreferences(preferences: UserPreferences): Promise<void> {
  const now = new Date().toISOString();

  await docClient.send(
    new PutCommand({
      TableName: config.dynamodb.userPreferencesTable,
      Item: {
        ...preferences,
        created_at: preferences.created_at || now,
        updated_at: now,
      },
    })
  );
}

/**
 * Chat Session Management (stored in User Preferences)
 * - Manages chat session metadata (research_id, model_id, etc.)
 * - Actual conversation messages are stored in AgentCore Memory
 * - Uses soft delete (is_deleted flag) to preserve AgentCore Memory data
 */

export async function getChatSessions(userId: string): Promise<ChatSession[]> {
  const preferences = await getUserPreferences(userId);

  if (!preferences || !preferences.chat_sessions) {
    return [];
  }

  // Filter out deleted sessions and sort by updated_at descending
  return preferences.chat_sessions
    .filter(session => !session.is_deleted)
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
}

export async function createChatSession(
  userId: string,
  sessionId: string,
  researchId: string | undefined,
  modelId: string,
  title?: string
): Promise<void> {
  const preferences = await getUserPreferences(userId);
  const now = new Date().toISOString();

  const newSession: ChatSession = {
    session_id: sessionId,
    research_id: researchId,
    model_id: modelId,
    title: title,
    created_at: now,
    updated_at: now,
    is_deleted: false,
  };

  const chatSessions = preferences?.chat_sessions || [];
  chatSessions.push(newSession);

  await saveUserPreferences({
    user_id: userId,
    ...preferences,
    chat_sessions: chatSessions,
    created_at: preferences?.created_at || now,
    updated_at: now,
  });
}

export async function updateChatSession(
  userId: string,
  sessionId: string,
  updates: Partial<ChatSession>
): Promise<void> {
  const preferences = await getUserPreferences(userId);

  if (!preferences || !preferences.chat_sessions) {
    throw new Error('User preferences or chat sessions not found');
  }

  const chatSessions = preferences.chat_sessions.map(session => {
    if (session.session_id === sessionId) {
      return {
        ...session,
        ...updates,
        updated_at: new Date().toISOString(),
      };
    }
    return session;
  });

  await saveUserPreferences({
    ...preferences,
    chat_sessions: chatSessions,
  });
}

export async function deleteChatSession(userId: string, sessionId: string): Promise<void> {
  // Soft delete - mark as deleted but keep in DynamoDB
  // AgentCore Memory events are preserved
  await updateChatSession(userId, sessionId, { is_deleted: true });
}

export async function getChatSessionById(userId: string, sessionId: string): Promise<ChatSession | null> {
  const sessions = await getChatSessions(userId);
  return sessions.find(s => s.session_id === sessionId) || null;
}
