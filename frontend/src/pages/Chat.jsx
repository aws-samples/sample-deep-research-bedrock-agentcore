import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  AppLayout,
  SpaceBetween,
  Button,
  Container,
  Box,
  Alert,
  Select,
  ButtonGroup,
  StatusIndicator,
  PromptInput,
  LiveRegion,
  Modal,
  ExpandableSection
} from '@cloudscape-design/components';
import { ChatBubble, Avatar, SupportPromptGroup } from '@cloudscape-design/chat-components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import { api } from '../services/api';
import { LLM_MODELS } from '../utils/workflowStages';
import { formatModelName } from '../utils/formatters';
import './Chat.css';

const AUTHORS = {
  'user': {
    name: 'You',
    type: 'user'
  },
  'gen-ai': {
    name: 'AI Assistant',
    type: 'gen-ai'
  }
};

export default function Chat({ addNotification }) {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState([]);
  const [isGenAiResponseLoading, setIsGenAiResponseLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null); // Will be loaded from preferences
  const messagesContainerRef = useRef(null);
  const promptInputRef = useRef(null);
  const [feedbackStates, setFeedbackStates] = useState({});
  const [feedbackSubmitting, setFeedbackSubmitting] = useState({});

  // Research selection
  const [researchList, setResearchList] = useState([]);
  const [selectedResearch, setSelectedResearch] = useState(null);
  const [loadingResearch, setLoadingResearch] = useState(true);

  // Chat session history
  const [chatSessions, setChatSessions] = useState([]);
  const [currentChatSession, setCurrentChatSession] = useState(null);
  const [loadingChatSessions, setLoadingChatSessions] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true); // Open by default

  // Delete confirmation modal
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState(null);

  const suggestedPrompts = [
    {
      id: 'summarize',
      text: 'Summarize the key findings from this research'
    },
    {
      id: 'insights',
      text: 'What are the most important insights?'
    },
    {
      id: 'methodology',
      text: 'Explain the research methodology used'
    }
  ];

  const latestMessage = messages[messages.length - 1];

  // Load user preferences for default chat model
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        const prefs = await api.getUserPreferences();
        if (prefs.default_chat_model) {
          const modelOption = LLM_MODELS.find(m => m.value === prefs.default_chat_model);
          if (modelOption) {
            setSelectedModel(modelOption);
          } else {
            // Fallback to first model if preference not found
            setSelectedModel(LLM_MODELS[0]);
          }
        } else {
          // No preference set, use first model
          setSelectedModel(LLM_MODELS[0]);
        }
      } catch (error) {
        console.error('Failed to load user preferences:', error);
        // Fallback to first model on error
        setSelectedModel(LLM_MODELS[0]);
      }
    };

    loadPreferences();
  }, []);

  // Manual sync function - triggered by Apply button (applies both research and model)
  const handleApplyResearch = async () => {
    if (!currentChatSession || !selectedResearch) {
      addNotification({
        type: 'warning',
        content: 'Please select a research first'
      });
      return;
    }

    try {
      console.log(`[Chat] 🔄 Applying changes to session`);
      console.log(`[Chat]   Session: ${currentChatSession.session_id}`);
      console.log(`[Chat]   Research: ${selectedResearch.label}`);
      console.log(`[Chat]   Model: ${selectedModel.value}`);

      // Update backend with both research and model
      await api.updateChatSession(currentChatSession.session_id, {
        research_id: selectedResearch.value,
        research_session_id: selectedResearch.value,
        research_name: selectedResearch.label,
        title: selectedResearch.label,
        model_id: selectedModel.value
      });

      // Update currentChatSession
      const updatedSession = {
        ...currentChatSession,
        research_id: selectedResearch.value,
        research_session_id: selectedResearch.value,
        research_name: selectedResearch.label,
        title: selectedResearch.label,
        model_id: selectedModel.value
      };

      setCurrentChatSession(updatedSession);

      // Update session list
      setChatSessions(prev => prev.map(session =>
        session.session_id === currentChatSession.session_id
          ? updatedSession
          : session
      ));

      console.log(`[Chat] ✅ Changes applied successfully`);

      addNotification({
        type: 'success',
        content: `Updated to "${selectedResearch.label}" with ${selectedModel.label}`
      });
    } catch (error) {
      console.error('[Chat] ❌ Failed to apply changes:', error);
      addNotification({
        type: 'error',
        content: 'Failed to update session'
      });
    }
  };

  // Load research list
  useEffect(() => {
    const loadResearchList = async () => {
      try {
        setLoadingResearch(true);
        const response = await api.getResearchHistory(100);

        // Filter only completed research
        const completedResearch = response.sessions
          .filter(r => r.status === 'completed')
          .map(r => ({
            label: r.topic || r.session_id,
            value: r.session_id,
            description: `${r.research_type || 'general'} • ${new Date(r.created_at).toLocaleDateString()}`
          }));

        setResearchList(completedResearch);

        // Don't auto-select research - let user choose or let session sync handle it
      } catch (error) {
        console.error('Failed to load research list:', error);
        addNotification({
          type: 'error',
          content: 'Failed to load research list'
        });
      } finally {
        setLoadingResearch(false);
      }
    };

    loadResearchList();
  }, [addNotification]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load all chat sessions on mount (no longer filtered by research)
  useEffect(() => {
    loadChatSessions();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Keyboard shortcut: Ctrl+B or Cmd+B to toggle sidebar
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Check for Ctrl+B (Windows/Linux) or Cmd+B (Mac)
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault(); // Prevent browser's bookmark dialog
        setSidebarOpen(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const loadChatSessions = async () => {
    try {
      setLoadingChatSessions(true);

      // Get all chat sessions from DynamoDB (filtered by is_deleted = false)
      const response = await api.getChatSessions();
      const allSessions = response.sessions || [];

      // Show all sessions in one unified list (don't filter by research type)
      console.log(`[Chat] Loaded ${allSessions.length} total sessions`);

      setChatSessions(allSessions);
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
      setChatSessions([]);
    } finally {
      setLoadingChatSessions(false);
    }
  };

  const startNewChatSession = useCallback(async () => {
    try {
      // Generate UUID session ID (minimum 33 chars required by AgentCore)
      const chatSessionId = `chat-session-${crypto.randomUUID()}`;
      console.log('Creating new chat session:', chatSessionId);

      // Auto-select most recent research (first in list)
      const defaultResearch = researchList.length > 0 ? researchList[0] : null;

      if (!defaultResearch) {
        addNotification({
          type: 'warning',
          content: 'No research available. Please create a research first.'
        });
        return;
      }

      // Create session in DynamoDB with default research
      await api.createChatSession(
        chatSessionId,
        defaultResearch.value,
        selectedModel?.value || 'claude_haiku45',
        defaultResearch.label
      );

      const newSession = {
        session_id: chatSessionId,
        research_id: defaultResearch.value,
        research_session_id: defaultResearch.value,
        research_name: defaultResearch.label,
        model_id: selectedModel?.value || 'claude_haiku45',
        title: defaultResearch.label,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_deleted: false
      };

      // Set research selection to default
      setSelectedResearch(defaultResearch);

      setSessionId(chatSessionId);
      setMessages([]);
      setFeedbackStates({});
      setFeedbackSubmitting({});
      setCurrentChatSession(newSession);

      // Add new session to the list at the top
      setChatSessions(prev => [newSession, ...prev]);

      addNotification({
        type: 'success',
        content: `New chat session created for "${defaultResearch.label}"`
      });

      // Focus on prompt input
      setTimeout(() => {
        promptInputRef.current?.focus();
      }, 100);
    } catch (error) {
      console.error('Failed to create chat session:', error);
      addNotification({
        type: 'error',
        content: 'Failed to create chat session'
      });
    }
  }, [selectedModel, researchList, addNotification]);

  const loadChatSession = async (chatSession) => {
    try {
      console.log('[Chat] Loading session:', chatSession.session_id);
      console.log('[Chat] Research session:', chatSession.research_session_id);

      setCurrentChatSession(chatSession);
      setSessionId(chatSession.session_id);

      // Get research_session_id from session only (don't fallback to current selection)
      const researchSessionId = chatSession.research_session_id ||
                                 chatSession.research_id;

      // Sync research dropdown with session's research (always sync when loading session)
      if (researchSessionId) {
        const matchingResearch = researchList.find(r => r.value === researchSessionId);
        if (matchingResearch) {
          console.log('[Chat] Session loaded → Syncing dropdown to session research:', matchingResearch.label);
          setSelectedResearch(matchingResearch);
        } else if (researchList.length > 0) {
          // researchList is loaded but research not found
          console.warn('[Chat] Research not found in list:', researchSessionId);
          setSelectedResearch(null);
        } else {
          // researchList not loaded yet, clear for now
          console.log('[Chat] researchList not loaded yet, clearing selection');
          setSelectedResearch(null);
        }
      } else {
        // No research associated with this session
        console.log('[Chat] No research ID in session → Clearing dropdown');
        setSelectedResearch(null);
      }

      // Sync model dropdown with session's model
      if (chatSession.model_id) {
        const matchingModel = LLM_MODELS.find(m => m.value === chatSession.model_id);
        if (matchingModel) {
          console.log('[Chat] Session loaded → Syncing dropdown to session model:', matchingModel.label);
          setSelectedModel(matchingModel);
        }
      }

      if (!researchSessionId) {
        console.error('[Chat] No research session ID available');
        addNotification({
          type: 'error',
          content: 'Cannot load chat history: No research session ID'
        });
        return;
      }

      console.log('[Chat] Using research session:', researchSessionId);

      // Load messages for this chat session from AgentCore Memory
      const response = await api.getChatHistory(
        researchSessionId,
        chatSession.session_id,
        100
      );

      console.log('[Chat] Got history response:', response);
      const sessionMessages = response.messages || [];
      console.log('[Chat] Found', sessionMessages.length, 'messages');

      // Reverse the order since storage order is opposite of display order
      // Storage returns newest-first, but chat display needs oldest-first
      const reversedMessages = [...sessionMessages].reverse();

      // Convert to chat bubble format
      const formattedMessages = reversedMessages.map((msg, idx) => {
        // Clean up user messages: remove research context wrapper if present (for old messages)
        let content = msg.content;
        if (msg.role === 'user' && content) {
          // Remove various prefixes that might exist in old messages
          // 1. Research context wrapper: [Current Research: ...]
          if (content.startsWith('[Current Research:')) {
            const parts = content.split('\n\n');
            if (parts.length > 2) {
              content = parts[parts.length - 1];
            }
          }

          // 2. Remove "User Message: " prefix if present
          content = content.replace(/^User Message:\s*/i, '');

          // 3. Trim any extra whitespace
          content = content.trim();
        }

        return {
          type: 'chat-bubble',
          authorId: msg.role === 'user' ? 'user' : 'gen-ai',
          content: content,
          timestamp: new Date(msg.timestamp).toLocaleTimeString(),
          id: msg.message_id || `msg-${chatSession.session_id}-${idx}`,
          ...(msg.role === 'assistant' && {
            actions: 'feedback',
            contentToCopy: content,
            model: msg.model
          })
        };
      });

      console.log('[Chat] Formatted', formattedMessages.length, 'messages');
      setMessages(formattedMessages);
      setFeedbackStates({});
      setFeedbackSubmitting({});
    } catch (error) {
      console.error('Failed to load chat session:', error);
      addNotification({
        type: 'error',
        content: 'Failed to load chat session'
      });
    }
  };

  const handleDeleteSessionClick = (sessionId) => {
    setSessionToDelete(sessionId);
    setDeleteModalVisible(true);
  };

  const handleDeleteSessionConfirm = async () => {
    const sessionIdToDelete = sessionToDelete;
    const wasCurrentSession = currentChatSession?.session_id === sessionIdToDelete;

    // Optimistic update: close modal immediately for better UX
    setDeleteModalVisible(false);
    setSessionToDelete(null);

    // Optimistically remove from UI
    setChatSessions(prev => prev.filter(s => s.session_id !== sessionIdToDelete));

    // If deleting current session, clear it immediately
    if (wasCurrentSession) {
      setCurrentChatSession(null);
      setSessionId(null);
      setMessages([]);
    }

    try {
      console.log('Deleting session:', sessionIdToDelete);

      // Call API to delete session (in background)
      await api.deleteChatSession(sessionIdToDelete);

      addNotification({
        type: 'success',
        content: 'Chat session deleted'
      });

      // Don't auto-create a new session - let user decide what to do next
      // User can:
      // 1. Click "New Chat" button to start a new session
      // 2. Select an existing session from the sidebar
      // 3. Just browse without an active session
    } catch (error) {
      console.error('Failed to delete chat session:', error);

      // Rollback: add the session back
      await loadChatSessions();

      addNotification({
        type: 'error',
        content: `Failed to delete session: ${error.message}`
      });
    }
  };

  const handleDeleteSessionCancel = () => {
    setDeleteModalVisible(false);
    setSessionToDelete(null);
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    setTimeout(() => {
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
      }
    }, 0);
  }, [latestMessage?.content]);

  const handleSendMessage = async (messageText) => {
    const textToSend = messageText || prompt.trim();
    if (!textToSend || isGenAiResponseLoading || !selectedResearch || !currentChatSession) return;

    // Auto-collapse sidebar when sending a message
    setSidebarOpen(false);

    const userMessage = {
      type: 'chat-bubble',
      authorId: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMessage]);
    setPrompt('');
    setIsGenAiResponseLoading(true);

    // Add loading message
    const loadingMessage = {
      type: 'chat-bubble',
      authorId: 'gen-ai',
      content: '',
      timestamp: new Date().toLocaleTimeString(),
      avatarLoading: true
    };

    setTimeout(() => {
      setMessages(prev => [...prev, loadingMessage]);

      // Call API with streaming support
      let streamingContent = '';
      let toolCalls = [];

      console.log('[Chat] Sending message:', {
        session_id: sessionId,
        research_session_id: selectedResearch.value,
        message: textToSend,
        model_id: selectedModel.value
      });

      api.sendChatMessage(
        {
          session_id: sessionId,
          research_session_id: selectedResearch.value,
          message: textToSend,
          model_id: selectedModel.value,
          conversation_history: messages
        },
        // onChunk callback - update message as chunks arrive
        (chunk) => {
          streamingContent += chunk;
          setMessages(prev => {
            const newMessages = [...prev];
            const messageIndex = newMessages.length - 1;
            newMessages[messageIndex] = {
              type: 'chat-bubble',
              authorId: 'gen-ai',
              content: streamingContent,
              timestamp: new Date().toLocaleTimeString(),
              avatarLoading: true, // Still loading
              id: `msg-streaming`,
              model: selectedModel.value,
              toolCalls: toolCalls
            };
            return newMessages;
          });
        },
        // onToolStart callback - track tool usage
        (toolData) => {
          console.log('[Chat] Tool called:', toolData.tool_name);
          toolCalls.push({
            id: toolData.tool_id,
            name: toolData.tool_name,
            input: toolData.input,
            status: 'running'
          });

          // Update the message with tool info
          setMessages(prev => {
            const newMessages = [...prev];
            const messageIndex = newMessages.length - 1;
            if (newMessages[messageIndex]) {
              newMessages[messageIndex] = {
                ...newMessages[messageIndex],
                toolCalls: [...toolCalls]
              };
            }
            return newMessages;
          });
        },
        // onComplete callback - finalize message
        async (response) => {
          // Use streamingContent (already accumulated) instead of response.response
          // to avoid duplication issues
          setMessages(prev => {
            const newMessages = [...prev];
            const messageIndex = newMessages.length - 1;
            newMessages[messageIndex] = {
              type: 'chat-bubble',
              authorId: 'gen-ai',
              content: streamingContent,  // Use accumulated streaming content
              timestamp: new Date().toLocaleTimeString(),
              avatarLoading: false,
              id: `msg-${Date.now()}`,
              actions: 'feedback',
              contentToCopy: streamingContent,  // Use accumulated streaming content
              model: selectedModel.value,
              toolCalls: response.tool_calls || []
            };
            return newMessages;
          });
          setIsGenAiResponseLoading(false);

          // Update session in the list with new message count, last message, and research info
          setChatSessions(prev => {
            return prev.map(session => {
              if (session.session_id === sessionId) {
                return {
                  ...session,
                  research_id: selectedResearch.value,
                  research_name: selectedResearch.label,
                  title: selectedResearch.label,  // Update title with research name
                  message_count: session.message_count + 2, // user + assistant messages
                  last_message: {
                    content: textToSend,
                    timestamp: new Date().toISOString(),
                    role: 'user'
                  },
                  is_new: false
                };
              }
              return session;
            });
          });

          // Save research info to DynamoDB session (including title update)
          try {
            await api.updateChatSession(sessionId, {
              research_id: selectedResearch.value,
              research_name: selectedResearch.label,
              title: selectedResearch.label  // Update session title with research name
            });
          } catch (error) {
            console.error('[Chat] Failed to update session with research info:', error);
            // Don't show error to user, this is a background update
          }
        }
      )
        .catch(error => {
          console.error('Failed to send message:', error);
          setMessages(prev => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = {
              type: 'chat-bubble',
              authorId: 'gen-ai',
              content: 'Sorry, I encountered an error processing your message. Please try again.',
              timestamp: new Date().toLocaleTimeString(),
              avatarLoading: false,
              error: true
            };
            return newMessages;
          });
          setIsGenAiResponseLoading(false);
          addNotification({
            type: 'error',
            content: `Failed to send message: ${error.message}`
          });
        });
    }, 300);
  };

  const handleSupportPromptClick = ({ detail }) => {
    const prompt = suggestedPrompts.find(p => p.id === detail.id);
    if (prompt) {
      handleSendMessage(prompt.text);
    }
  };

  const handleFeedback = (messageId, feedbackType) => {
    setFeedbackSubmitting(prev => ({ ...prev, [messageId]: feedbackType }));

    setTimeout(() => {
      setFeedbackStates(prev => ({ ...prev, [messageId]: feedbackType }));
      setFeedbackSubmitting(prev => ({ ...prev, [messageId]: '' }));
    }, 2000);
  };

  const renderFeedbackActions = (msg) => {
    if (!msg.id) return null;

    const feedback = feedbackStates[msg.id];
    const submitting = feedbackSubmitting[msg.id];

    const items = [
      {
        type: 'group',
        text: 'Vote',
        items: [
          {
            type: 'icon-button',
            id: 'helpful',
            iconName: feedback === 'helpful' ? 'thumbs-up-filled' : 'thumbs-up',
            text: 'Helpful',
            disabled: !!feedback || submitting === 'not-helpful',
            disabledReason: submitting
              ? ''
              : feedback === 'helpful'
              ? '"Helpful" feedback has been submitted.'
              : '"Helpful" option is unavailable after "Not helpful" feedback submitted.',
            loading: submitting === 'helpful',
            popoverFeedback:
              feedback === 'helpful' ? (
                <StatusIndicator type="success">Feedback submitted</StatusIndicator>
              ) : (
                'Submitting feedback'
              )
          },
          {
            type: 'icon-button',
            id: 'not-helpful',
            iconName: feedback === 'not-helpful' ? 'thumbs-down-filled' : 'thumbs-down',
            text: 'Not helpful',
            disabled: !!feedback || submitting === 'helpful',
            disabledReason: submitting
              ? ''
              : feedback === 'not-helpful'
              ? '"Not helpful" feedback has been submitted.'
              : '"Not helpful" option is unavailable after "Helpful" feedback submitted.',
            loading: submitting === 'not-helpful',
            popoverFeedback:
              feedback === 'not-helpful' ? (
                <StatusIndicator type="success">Feedback submitted</StatusIndicator>
              ) : (
                'Submitting feedback'
              )
          }
        ]
      },
      {
        type: 'icon-button',
        id: 'copy',
        iconName: 'copy',
        text: 'Copy',
        popoverFeedback: <StatusIndicator type="success">Message copied</StatusIndicator>
      }
    ];

    return (
      <ButtonGroup
        ariaLabel="Chat actions"
        variant="icon"
        items={items}
        onItemClick={({ detail }) => {
          if (detail.id === 'copy') {
            navigator.clipboard.writeText(msg.contentToCopy || msg.content);
            return;
          }
          handleFeedback(msg.id, detail.id);
        }}
      />
    );
  };

  const renderChatBubbleAvatar = (authorId, loading) => {
    const author = AUTHORS[authorId];
    if (author.type === 'gen-ai') {
      return (
        <Avatar
          color="gen-ai"
          iconName="gen-ai"
          tooltipText={author.name}
          ariaLabel={author.name}
          loading={loading}
        />
      );
    }
    return <Avatar initials="U" tooltipText={author.name} ariaLabel={author.name} />;
  };

  return (
    <>
      {/* Delete Confirmation Modal */}
      <Modal
        visible={deleteModalVisible}
        onDismiss={handleDeleteSessionCancel}
        header="Delete chat session"
        closeAriaLabel="Close modal"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link" onClick={handleDeleteSessionCancel}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleDeleteSessionConfirm}>
                Delete
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween size="m">
          <Box variant="span">
            Are you sure you want to delete this chat session? This action cannot be undone.
          </Box>
          <Alert type="warning" statusIconAriaLabel="Warning">
            All messages in this conversation will be permanently removed from memory.
          </Alert>
        </SpaceBetween>
      </Modal>

      <AppLayout
        navigationHide
        toolsHide
        content={
        <div className="chat-page-layout">
          {/* Left Sidebar - Chat Sessions */}
          <div className={`chat-sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
            <div className="chat-sidebar-header">
              <Button
                variant="icon"
                iconName="add-plus"
                onClick={startNewChatSession}
                disabled={isGenAiResponseLoading}
                ariaLabel="New chat"
              />
            </div>
            <div className="chat-sidebar-content">
              {loadingChatSessions ? (
                <Box textAlign="center" padding={{ vertical: 'xxl' }} color="text-status-inactive">
                  <SpaceBetween size="s">
                    <Box>Loading chats...</Box>
                  </SpaceBetween>
                </Box>
              ) : chatSessions.length === 0 ? (
                <Box textAlign="center" padding={{ vertical: 'xxl', horizontal: 's' }} color="text-status-inactive">
                  <SpaceBetween size="s">
                    <Box fontSize="body-s">No previous chats</Box>
                    <Box fontSize="body-s" color="text-body-secondary">Click "+" to start</Box>
                  </SpaceBetween>
                </Box>
              ) : (
                <div className="chat-sessions-list">
                  {chatSessions.map((session) => (
                    <div
                      key={session.session_id}
                      className={`chat-session-item ${currentChatSession?.session_id === session.session_id ? 'active' : ''}`}
                    >
                      <div
                        className="chat-session-content"
                        onClick={() => loadChatSession(session)}
                        role="button"
                        tabIndex={0}
                        onKeyPress={(e) => e.key === 'Enter' && loadChatSession(session)}
                      >
                        <div className="chat-session-title">
                          {session.title || 'Chat Session'}
                        </div>
                        <div className="chat-session-preview">
                          {session.last_message?.content?.substring(0, 50) || 'New conversation'}
                          {session.last_message?.content?.length > 50 && '...'}
                        </div>
                        <div className="chat-session-meta">
                          <span>{new Date(session.created_at).toLocaleDateString()}</span>
                          {session.model_id && (
                            <>
                              <span className="meta-separator">•</span>
                              <span className="meta-model">{formatModelName(session.model_id)}</span>
                            </>
                          )}
                        </div>
                      </div>
                      <Button
                        variant="icon"
                        iconName="close"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSessionClick(session.session_id);
                        }}
                        ariaLabel="Delete session"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Main Chat Area */}
          <div className="chat-main">
            <div className="chat-container">
              <div className="chat-header">
                <SpaceBetween direction="horizontal" size="s" alignItems="center">
                  <Button
                    variant="icon"
                    iconName="menu"
                    onClick={() => setSidebarOpen(prev => !prev)}
                    ariaLabel="Toggle chat sessions"
                  />
                  <Box variant="h2" fontSize="heading-l">Research Chat</Box>
                </SpaceBetween>
                <SpaceBetween direction="horizontal" size="xs">
                  <Select
                    data-testid="research-select"
                    selectedOption={selectedResearch}
                    onChange={({ detail }) => setSelectedResearch(detail.selectedOption)}
                    options={researchList}
                    disabled={isGenAiResponseLoading || loadingResearch}
                    placeholder={loadingResearch ? "Loading research..." : "Select research"}
                    selectedAriaLabel="Selected research"
                    filteringType="auto"
                    empty="No completed research available"
                    loadingText="Loading research..."
                    statusType={loadingResearch ? "loading" : researchList.length === 0 ? "error" : "finished"}
                  />
                  <Select
                    selectedOption={selectedModel}
                    onChange={({ detail }) => setSelectedModel(detail.selectedOption)}
                    options={LLM_MODELS}
                    disabled={isGenAiResponseLoading}
                    placeholder="Select model"
                    selectedAriaLabel="Selected model"
                  />
                  <Button
                    onClick={handleApplyResearch}
                    disabled={!currentChatSession || !selectedResearch || isGenAiResponseLoading}
                    ariaLabel="Apply research and model to session"
                  >
                    Apply
                  </Button>
                </SpaceBetween>
              </div>

            <div style={{ position: 'relative', flexGrow: 1 }}>
              <div style={{ position: 'absolute', inset: 0 }}>
                <Container
                  fitHeight
                  disableContentPaddings
                  footer={
                    <>
                      <PromptInput
                        ref={promptInputRef}
                        onChange={({ detail }) => setPrompt(detail.value)}
                        onAction={({ detail }) => handleSendMessage(detail.value)}
                        value={prompt}
                        actionButtonAriaLabel={
                          !selectedResearch
                            ? 'Select research first'
                            : !currentChatSession
                            ? 'Start a chat session first'
                            : isGenAiResponseLoading
                            ? 'Send message button - suppressed'
                            : 'Send message'
                        }
                        actionButtonIconName="send"
                        ariaLabel={
                          !selectedResearch
                            ? 'Select research first'
                            : !currentChatSession
                            ? 'Start a chat session first'
                            : isGenAiResponseLoading
                            ? 'Prompt input - suppressed'
                            : 'Prompt input'
                        }
                        placeholder={
                          !selectedResearch
                            ? "Select a research first"
                            : !currentChatSession
                            ? "Start a chat session to begin"
                            : "Ask about this research..."
                        }
                        disabled={!selectedResearch || !currentChatSession}
                        autoFocus={!!selectedResearch && !!currentChatSession}
                      />
                      <Box color="text-body-secondary" margin={{ top: 'xs' }} fontSize="body-s">
                        {selectedResearch
                          ? 'AI responses are based on the selected research. AI can make mistakes. Verify important information.'
                          : 'Select a completed research to start chatting.'}
                      </Box>
                    </>
                  }
                >
                  <div style={{ position: 'relative', blockSize: '100%' }}>
                    <div
                      style={{ position: 'absolute', inset: 0, overflowY: 'auto' }}
                      ref={messagesContainerRef}
                      data-testid="chat-scroll-container"
                    >
                      <div className="messages" role="region" aria-label="Chat">
                        <LiveRegion hidden={true}>
                          {latestMessage?.content}
                        </LiveRegion>

                        {!selectedResearch ? (
                          <Box textAlign="center" padding={{ vertical: 'xxxl', horizontal: 'l' }} color="text-body-secondary">
                            <SpaceBetween size="l">
                              <SpaceBetween size="xs">
                                <Box variant="h2" fontWeight="normal">Select a research to start</Box>
                                <Box variant="p" color="text-body-secondary">
                                  Choose a completed research from the dropdown above to ask questions about it.
                                </Box>
                              </SpaceBetween>
                              {researchList.length === 0 && !loadingResearch && (
                                <Alert type="info" header="No research available">
                                  You don't have any completed research yet. Create a new research to get started.
                                </Alert>
                              )}
                            </SpaceBetween>
                          </Box>
                        ) : !currentChatSession ? (
                          <Box textAlign="center" padding={{ vertical: 'xxxl', horizontal: 'l' }} color="text-body-secondary">
                            <SpaceBetween size="l">
                              <SpaceBetween size="xs">
                                <Box variant="h2" fontWeight="normal">Start a conversation</Box>
                                <Box variant="p" color="text-body-secondary">
                                  Click the menu button to view chat history or click the + button to start a new chat session.
                                </Box>
                              </SpaceBetween>
                              <Alert type="info" header="No active session">
                                Select an existing chat session from the sidebar or create a new one to start chatting about "{selectedResearch?.label}".
                              </Alert>
                            </SpaceBetween>
                          </Box>
                        ) : messages.length === 0 ? (
                          <Box textAlign="center" padding={{ vertical: 'xxxl', horizontal: 'l' }} color="text-body-secondary">
                            <SpaceBetween size="l">
                              <SpaceBetween size="xs">
                                <Box variant="h2" fontWeight="normal">Ask about this research</Box>
                                <Box variant="p" color="text-body-secondary">
                                  {selectedResearch.label}
                                </Box>
                              </SpaceBetween>
                              <div className="support-prompts-container">
                                <SupportPromptGroup
                                  items={suggestedPrompts}
                                  onItemClick={handleSupportPromptClick}
                                  ariaLabel="Suggested prompts"
                                  alignment="vertical"
                                />
                              </div>
                            </SpaceBetween>
                          </Box>
                        ) : (
                          messages.map((message, index) => {
                            const author = AUTHORS[message.authorId];
                            // Clean up user messages: remove research context wrapper if present (for old messages)
                            let displayContent = message.content;
                            if (message.authorId === 'user' && displayContent) {
                              // Remove various prefixes that might exist in old messages
                              // 1. Research context wrapper: [Current Research: ...]
                              if (displayContent.startsWith('[Current Research:')) {
                                const parts = displayContent.split('\n\n');
                                if (parts.length > 2) {
                                  displayContent = parts[parts.length - 1];
                                }
                              }

                              // 2. Remove "User Message: " prefix if present
                              displayContent = displayContent.replace(/^User Message:\s*/i, '');

                              // 3. Trim any extra whitespace
                              displayContent = displayContent.trim();
                            }
                            return (
                              <SpaceBetween size="xs" key={message.id || `${message.authorId}-${index}-${message.timestamp}`}>
                                <ChatBubble
                                  avatar={renderChatBubbleAvatar(message.authorId, message.avatarLoading)}
                                  ariaLabel={`${author.name} at ${message.timestamp}`}
                                  type={author.type === 'gen-ai' ? 'incoming' : 'outgoing'}
                                  hideAvatar={message.hideAvatar}
                                  actions={message.actions === 'feedback' ? renderFeedbackActions(message) : null}
                                >
                                  <SpaceBetween size="xs">
                                    {displayContent && (
                                      message.authorId === 'gen-ai' ? (
                                        // Render AI messages with markdown support
                                        <div className="chat-message-markdown">
                                          <ReactMarkdown
                                            remarkPlugins={[remarkGfm]}
                                            rehypePlugins={[rehypeRaw, rehypeSanitize]}
                                            components={{
                                              // Custom styling for code blocks
                                              code({node, inline, className, children, ...props}) {
                                                return inline ? (
                                                  <code className="inline-code" {...props}>
                                                    {children}
                                                  </code>
                                                ) : (
                                                  <pre className="code-block">
                                                    <code className={className} {...props}>
                                                      {children}
                                                    </code>
                                                  </pre>
                                                );
                                              },
                                              // Links open in new tab
                                              a({node, children, href, ...props}) {
                                                return (
                                                  <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
                                                    {children}
                                                  </a>
                                                );
                                              }
                                            }}
                                          >
                                            {displayContent}
                                          </ReactMarkdown>
                                        </div>
                                      ) : (
                                        // Render user messages as plain text
                                        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
                                          {displayContent}
                                        </div>
                                      )
                                    )}
                                    {message.authorId === 'gen-ai' && !message.avatarLoading && !message.error && message.model && (
                                      <Box fontSize="body-s" color="text-status-inactive">
                                        {LLM_MODELS.find(m => m.value === message.model)?.label}
                                      </Box>
                                    )}
                                    {/* Show Sources (Tool Calls) */}
                                    {message.authorId === 'gen-ai' && message.toolCalls && message.toolCalls.length > 0 && (
                                      <ExpandableSection
                                        variant="footer"
                                        headerText={`Sources (${message.toolCalls.length})`}
                                      >
                                        <SpaceBetween size="s">
                                          {message.toolCalls.map((tool, idx) => (
                                            <Box key={tool.id || idx}>
                                              <SpaceBetween size="xxs">
                                                <Box variant="strong">{tool.name}</Box>
                                                {tool.input && Object.keys(tool.input).length > 0 && (
                                                  <Box fontSize="body-s" color="text-body-secondary">
                                                    <pre style={{
                                                      margin: 0,
                                                      whiteSpace: 'pre-wrap',
                                                      fontFamily: 'monospace',
                                                      fontSize: '12px'
                                                    }}>
                                                      {JSON.stringify(tool.input, null, 2)}
                                                    </pre>
                                                  </Box>
                                                )}
                                              </SpaceBetween>
                                            </Box>
                                          ))}
                                        </SpaceBetween>
                                      </ExpandableSection>
                                    )}
                                  </SpaceBetween>
                                </ChatBubble>
                              </SpaceBetween>
                            );
                          })
                        )}
                      </div>
                    </div>
                  </div>
                </Container>
              </div>
            </div>
            </div>
          </div>
        </div>
      }
      />
    </>
  );
}
