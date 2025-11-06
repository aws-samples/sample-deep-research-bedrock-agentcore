/**
 * API Service for Deep Research Agent
 * Handles all HTTP requests to the BFF (Backend for Frontend)
 */

import { getApiBaseUrl, APP_CONFIG } from '../config/app.config';
import { fetchAuthSession } from 'aws-amplify/auth';

const API_BASE = getApiBaseUrl();

/**
 * Get current user ID from Cognito session
 */
async function getUserId() {
  // For local development, use mock user ID if provided
  if (process.env.REACT_APP_MOCK_USER_ID) {
    return process.env.REACT_APP_MOCK_USER_ID;
  }

  if (!APP_CONFIG.features.authentication) {
    return 'anonymous';
  }

  try {
    const session = await fetchAuthSession();
    return session.tokens?.idToken?.payload?.sub || 'anonymous';
  } catch (error) {
    console.error('Failed to get user ID:', error);
    return 'anonymous';
  }
}

/**
 * Create headers with user ID
 */
async function getHeaders(additionalHeaders = {}) {
  const userId = await getUserId();
  return {
    'x-user-id': userId,
    ...additionalHeaders
  };
}

class APIService {
  /**
   * Create a new research session
   * Supports both JSON payload and FormData (for PDF uploads)
   */
  async createResearch(payload) {
    // Check if payload is FormData (for PDF uploads)
    const isFormData = payload instanceof FormData;

    const headers = await getHeaders(
      isFormData ? {} : { 'Content-Type': 'application/json' }
    );

    const response = await fetch(`${API_BASE}/api/research`, {
      method: 'POST',
      headers,
      body: isFormData ? payload : JSON.stringify(payload)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || 'Failed to create research');
    }

    return response.json();
  }

  /**
   * Get research session status (for polling)
   */
  async getResearchStatus(sessionId) {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE}/api/research/${sessionId}`, { headers });

    if (!response.ok) {
      throw new Error('Failed to fetch research status');
    }

    return response.json();
  }

  /**
   * Get research results
   */
  async getResearchResults(sessionId) {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE}/api/research/${sessionId}/results`, { headers });

    if (!response.ok) {
      throw new Error('Failed to fetch research results');
    }

    return response.json();
  }

  /**
   * Get research history
   */
  async getResearchHistory(limit = 50) {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE}/api/research/history?limit=${limit}`, { headers });

    if (!response.ok) {
      throw new Error('Failed to fetch research history');
    }

    return response.json();
  }

  /**
   * Get presigned download links for research reports
   */
  async getDownloadLinks(sessionId, version = 'draft') {
    const headers = await getHeaders();
    const response = await fetch(
      `${API_BASE}/api/research/${sessionId}/download?version=${version}`,
      { headers }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get download links');
    }

    return response.json();
  }

  /**
   * Cancel ongoing research session
   */
  async cancelResearch(sessionId) {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE}/api/research/${sessionId}/cancel`, {
      method: 'PATCH',
      headers
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to cancel research');
    }

    return response.json();
  }

  /**
   * Delete research session
   */
  async deleteResearch(sessionId) {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE}/api/research/${sessionId}`, {
      method: 'DELETE',
      headers
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to delete research');
    }

    return response.json();
  }

  /**
   * Get health status
   */
  async getHealth() {
    const response = await fetch(`${API_BASE}/api/health`);
    return response.json();
  }

  /**
   * Get AgentCore Memory events for a research session
   */
  async getMemoryEvents(sessionId, maxResults = 100) {
    const headers = await getHeaders();
    const response = await fetch(
      `${API_BASE}/api/research/${sessionId}/memory/events?max_results=${maxResults}`,
      { headers }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get memory events');
    }

    return response.json();
  }

  /**
   * Get detailed event information from AgentCore Memory
   */
  async getEventDetails(sessionId, eventId) {
    const headers = await getHeaders();
    const response = await fetch(
      `${API_BASE}/api/research/${sessionId}/memory/events/${eventId}`,
      { headers }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get event details');
    }

    return response.json();
  }

  /**
   * Get markdown content for a research session
   */
  async getMarkdown(sessionId, version = 'draft') {
    const headers = await getHeaders();
    const response = await fetch(
      `${API_BASE}/api/research/${sessionId}/markdown?version=${version}`,
      { headers }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get markdown content');
    }

    return response.json();
  }

  /**
   * Get comments for a research session
   */
  async getComments(sessionId) {
    const headers = await getHeaders();
    const response = await fetch(
      `${API_BASE}/api/research/${sessionId}/comments`,
      { headers }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get comments');
    }

    return response.json();
  }

  /**
   * Add a comment to a research session
   */
  async addComment(sessionId, comment) {
    const headers = await getHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(
      `${API_BASE}/api/research/${sessionId}/comments`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify(comment)
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to add comment');
    }

    return response.json();
  }

  /**
   * Update a comment
   */
  async updateComment(sessionId, commentId, updates) {
    const headers = await getHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(
      `${API_BASE}/api/research/${sessionId}/comments/${commentId}`,
      {
        method: 'PUT',
        headers,
        body: JSON.stringify(updates)
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to update comment');
    }

    return response.json();
  }

  /**
   * Delete a comment
   */
  async deleteComment(sessionId, commentId) {
    const headers = await getHeaders();
    const response = await fetch(
      `${API_BASE}/api/research/${sessionId}/comments/${commentId}`,
      {
        method: 'DELETE',
        headers
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to delete comment');
    }

    return response.json();
  }

  /**
   * Add a reply to a comment
   */
  async addCommentReply(sessionId, commentId, reply) {
    const headers = await getHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(
      `${API_BASE}/api/research/${sessionId}/comments/${commentId}/replies`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify(reply)
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to add reply');
    }

    return response.json();
  }

  /**
   * Get versions for a research session
   */
  async getVersions(sessionId) {
    const headers = await getHeaders();
    const response = await fetch(
      `${API_BASE}/api/research/${sessionId}/versions`,
      { headers }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get versions');
    }

    return response.json();
  }

  /**
   * Create a smart edit request from review comments (placeholder - to be implemented)
   */
  async createSmartEditRequest(sessionId) {
    const headers = await getHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(
      `${API_BASE}/api/research/${sessionId}/smart-edit`,
      {
        method: 'POST',
        headers
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || error.message || 'Failed to create smart edit request');
    }

    return response.json();
  }

  /**
   * Get user preferences
   */
  async getUserPreferences() {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE}/api/preferences`, {
      headers
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get user preferences');
    }

    return response.json();
  }

  /**
   * Save user preferences
   */
  async saveUserPreferences(preferences) {
    const headers = await getHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(`${API_BASE}/api/preferences`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(preferences)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to save user preferences');
    }

    return response.json();
  }

  /**
   * Chat API Methods
   */

  /**
   * Send a chat message with streaming response
   */
  async sendChatMessage(data, onChunk, onToolStart, onComplete) {
    const headers = await getHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(`${API_BASE}/api/chat/message`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to send chat message');
    }

    // Handle Server-Sent Events (SSE) streaming
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullResponse = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));

          if (data.type === 'done') {
            // Final complete response
            if (onComplete) {
              onComplete(data);
            }
            return data;
          } else if (data.type === 'error') {
            throw new Error(data.error);
          } else if (data.type === 'tool_start') {
            // Tool usage event
            if (onToolStart) {
              onToolStart(data);
            }
          } else if (data.chunk) {
            // Streaming chunk
            fullResponse += data.chunk;
            if (onChunk) {
              onChunk(data.chunk);
            }
          }
        }
      }
    }

    return { response: fullResponse };
  }

  /**
   * Get chat history for a session
   */
  async getChatHistory(researchSessionId, chatSessionId, limit = 100) {
    const headers = await getHeaders();
    const response = await fetch(
      `${API_BASE}/api/chat/${researchSessionId}/history?session_id=${chatSessionId}&limit=${limit}`,
      { headers }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get chat history');
    }

    return response.json();
  }

  /**
   * Create a new chat session in DynamoDB
   */
  async createChatSession(sessionId, researchId, modelId, title) {
    const headers = await getHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(
      `${API_BASE}/api/chat/sessions`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({
          session_id: sessionId,
          research_id: researchId,
          model_id: modelId,
          title: title
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to create chat session');
    }

    return response.json();
  }

  /**
   * Get all chat sessions from DynamoDB
   */
  async getChatSessions() {
    const headers = await getHeaders();
    const response = await fetch(
      `${API_BASE}/api/chat/sessions`,
      { headers }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get chat sessions');
    }

    return response.json();
  }

  /**
   * Update a chat session in DynamoDB
   */
  async updateChatSession(sessionId, updates) {
    const headers = await getHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(
      `${API_BASE}/api/chat/sessions/${sessionId}`,
      {
        method: 'PATCH',
        headers,
        body: JSON.stringify(updates)
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to update chat session');
    }

    return response.json();
  }

  /**
   * Soft delete a chat session (mark as deleted in DynamoDB)
   * AgentCore Memory events are preserved
   */
  async deleteChatSession(sessionId) {
    const headers = await getHeaders();
    const response = await fetch(
      `${API_BASE}/api/chat/sessions/${sessionId}`,
      { method: 'DELETE', headers }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to delete chat session');
    }

    return response.json();
  }

  /**
   * Review API Methods
   */

  /**
   * Get all research reviews
   */
  async getReviews(limit = 50) {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE}/api/research/reviews?limit=${limit}`, {
      headers
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get reviews');
    }

    return response.json();
  }

  /**
   * Start a review for a research session
   */
  async startReview(sessionId, version, baseVersion) {
    const headers = await getHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(`${API_BASE}/api/research/${sessionId}/review`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        version,
        base_version: baseVersion
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to start review');
    }

    return response.json();
  }

  /**
   * Update review status
   */
  async updateReviewStatus(sessionId, updates) {
    const headers = await getHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(`${API_BASE}/api/research/${sessionId}/review`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(updates)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to update review status');
    }

    return response.json();
  }
}

export const api = new APIService();
