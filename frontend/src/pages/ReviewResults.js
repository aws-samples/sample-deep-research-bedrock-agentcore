import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  AppLayout,
  ContentLayout,
  Header,
  SpaceBetween,
  Button,
  Alert,
  ColumnLayout,
  Box,
  StatusIndicator,
  ButtonDropdown,
  Spinner,
  Select
} from '@cloudscape-design/components';
import DocumentViewer from '../components/DocumentViewer';
import CommentSystem from '../components/CommentSystem';
import { api } from '../services/api';
import './ReviewResults.css';

export default function ReviewResults({ addNotification }) {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [markdown, setMarkdown] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [comments, setComments] = useState([]);
  const [selectedText, setSelectedText] = useState(null);
  const [selectionPosition, setSelectionPosition] = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [downloadLinks, setDownloadLinks] = useState(null);
  const clearSelectionRef = React.useRef(null);

  // Version management
  const [versions, setVersions] = useState({});
  const [, setCurrentVersion] = useState('draft');
  const [selectedVersion, setSelectedVersion] = useState('draft');

  // Load markdown document and session info
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);

        // Load session info
        const statusData = await api.getResearchStatus(sessionId);
        setSessionInfo(statusData);

        // Load versions
        try {
          const versionsData = await api.getVersions(sessionId);
          setVersions(versionsData.versions || {});
          setCurrentVersion(versionsData.current_version || 'draft');
          setSelectedVersion(versionsData.current_version || 'draft');
        } catch (err) {
          console.warn('Failed to load versions:', err);
        }

        // Load markdown content for selected version
        const markdownData = await api.getMarkdown(sessionId, selectedVersion);
        setMarkdown(markdownData.content);

        // Load comments
        const commentsData = await api.getComments(sessionId);
        setComments(commentsData.comments || []);

        // Load download links if research is completed
        if (statusData.status === 'completed') {
          const linksData = await api.getDownloadLinks(sessionId, selectedVersion);
          setDownloadLinks(linksData.downloads);
        }

        // Start review if not started yet
        if (statusData.status === 'completed' && (!statusData.review_status || statusData.review_status === 'not_started')) {
          try {
            await api.startReview(sessionId, selectedVersion);
            console.log('Review started automatically');
          } catch (err) {
            console.warn('Failed to start review:', err);
          }
        }

        setError(null);
      } catch (err) {
        console.error('Failed to load review data:', err);
        setError(err.message || 'Failed to load document');
      } finally {
        setLoading(false);
      }
    };

    if (sessionId) {
      loadData();
    }
  }, [sessionId, selectedVersion]);

  const handleTextSelect = (selection) => {
    setSelectedText(selection);
    setSelectionPosition(selection.position);
  };

  const handleClearSelection = () => {
    // Call the DocumentViewer's clear function
    if (clearSelectionRef.current) {
      clearSelectionRef.current();
    }
    // Clear local state
    setSelectedText(null);
    setSelectionPosition(null);
  };

  const handleAddComment = async (commentData) => {
    try {
      const newComment = {
        id: `comment_${Date.now()}`,
        sessionId,
        selectedText: commentData.selectedText,
        comment: commentData.comment,
        author: 'Current User', // TODO: Get from auth context
        timestamp: commentData.timestamp,
        status: 'pending',
        replies: []
      };

      // Save to backend
      await api.addComment(sessionId, newComment);

      // Update local state - DO NOT clear selection
      const updatedComments = [...comments, newComment];
      setComments(updatedComments);

      // Update review status with comment counts
      const pendingCount = updatedComments.filter((c) => c.status === 'pending').length;
      const resolvedCount = updatedComments.filter((c) => c.status === 'resolved').length;

      try {
        await api.updateReviewStatus(sessionId, {
          pending_comments_count: pendingCount,
          resolved_comments_count: resolvedCount,
          review_status: 'in_review'
        });
      } catch (err) {
        console.warn('Failed to update review status:', err);
      }

      // Keep selectedText and selectionPosition so highlight remains

      addNotification({
        type: 'success',
        content: 'Comment added successfully'
      });
    } catch (err) {
      console.error('Failed to add comment:', err);
      addNotification({
        type: 'error',
        content: `Failed to add comment: ${err.message}`
      });
    }
  };

  const handleDeleteComment = async (commentId) => {
    try {
      // Delete from backend
      await api.deleteComment(sessionId, commentId);

      // Update local state
      const updatedComments = comments.filter((c) => c.id !== commentId);
      setComments(updatedComments);

      // Update review status with comment counts
      const pendingCount = updatedComments.filter((c) => c.status === 'pending').length;
      const resolvedCount = updatedComments.filter((c) => c.status === 'resolved').length;

      try {
        await api.updateReviewStatus(sessionId, {
          pending_comments_count: pendingCount,
          resolved_comments_count: resolvedCount
        });
      } catch (err) {
        console.warn('Failed to update review status:', err);
      }

      addNotification({
        type: 'success',
        content: 'Comment deleted'
      });
    } catch (err) {
      console.error('Failed to delete comment:', err);
      addNotification({
        type: 'error',
        content: `Failed to delete comment: ${err.message}`
      });
    }
  };


  const handleDownload = (url, filename) => {
    window.open(url, '_blank');
    addNotification({
      type: 'success',
      content: `Downloading ${filename}...`
    });
  };

  const handleSmartEdit = async () => {
    // Placeholder for future implementation
    addNotification({
      type: 'info',
      content: 'Smart Edit feature is coming soon!'
    });
  };

  const getDownloadActions = () => {
    if (!downloadLinks) return [];

    const actions = [];
    if (downloadLinks.pdf?.url) {
      actions.push({ id: 'pdf', text: 'PDF Document (.pdf)' });
    }
    if (downloadLinks.docx?.url) {
      actions.push({ id: 'docx', text: 'Word Document (.docx)' });
    }
    if (downloadLinks.markdown?.url) {
      actions.push({ id: 'markdown', text: 'Markdown (.md)' });
    }
    return actions;
  };

  const handleDropdownItemClick = (event) => {
    if (!downloadLinks) return;

    const itemId = event.detail.id;
    if (itemId === 'pdf' && downloadLinks.pdf?.url) {
      handleDownload(downloadLinks.pdf.url, downloadLinks.pdf.filename);
    } else if (itemId === 'docx' && downloadLinks.docx?.url) {
      handleDownload(downloadLinks.docx.url, downloadLinks.docx.filename);
    } else if (itemId === 'markdown' && downloadLinks.markdown?.url) {
      handleDownload(downloadLinks.markdown.url, downloadLinks.markdown.filename);
    }
  };

  const getVersionOptions = () => {
    return Object.keys(versions).map(versionName => ({
      label: versionName === 'draft' ? 'Draft' : versionName.toUpperCase(),
      value: versionName,
      description: versions[versionName]?.created_at
        ? `Created: ${new Date(versions[versionName].created_at).toLocaleString()}`
        : undefined
    }));
  };

  if (loading) {
    return (
      <AppLayout
        navigationHide
        toolsHide
        content={
          <ContentLayout>
            <Box textAlign="center" padding="xxl">
              <Spinner size="large" />
              <Box variant="p" padding={{ top: 's' }}>
                Loading review document...
              </Box>
            </Box>
          </ContentLayout>
        }
      />
    );
  }

  if (error) {
    return (
      <AppLayout
        navigationHide
        toolsHide
        content={
          <ContentLayout>
            <Alert
              type="error"
              header="Failed to load review"
              action={
                <Button onClick={() => navigate(`/research/${sessionId}`)}>
                  Back to Research Details
                </Button>
              }
            >
              {error}
            </Alert>
          </ContentLayout>
        }
      />
    );
  }

  return (
    <AppLayout
      navigationHide
      toolsHide
      content={
        <ContentLayout
          header={
            <Header
              variant="h1"
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Select
                    selectedOption={getVersionOptions().find(opt => opt.value === selectedVersion) || null}
                    onChange={({ detail }) => setSelectedVersion(detail.selectedOption.value)}
                    options={getVersionOptions()}
                    selectedAriaLabel="Selected version"
                    placeholder="Select version"
                  />
                  <Button
                    iconName="arrow-left"
                    onClick={() => navigate(`/research/${sessionId}`)}
                  >
                    Back to Details
                  </Button>
                  <Button
                    iconName="gen-ai"
                    onClick={handleSmartEdit}
                    disabled={true}
                    variant="primary"
                  >
                    Smart Edit (Coming Soon)
                  </Button>
                  <ButtonDropdown
                    items={getDownloadActions()}
                    disabled={getDownloadActions().length === 0}
                    onItemClick={handleDropdownItemClick}
                  >
                    Download Report
                  </ButtonDropdown>
                </SpaceBetween>
              }
            >
              Review History
            </Header>
          }
        >
          <SpaceBetween size="l">
            {/* Session Info Bar */}
            {sessionInfo && (
              <Box
                padding="m"
                backgroundColor="background-container-content"
                borderRadius="default"
              >
                <ColumnLayout columns={4} variant="text-grid">
                  <div>
                    <Box variant="awsui-key-label">Research Topic</Box>
                    <Box>{sessionInfo.topic}</Box>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Status</Box>
                    <StatusIndicator
                      type={
                        sessionInfo.status === 'completed'
                          ? 'success'
                          : sessionInfo.status === 'failed'
                          ? 'error'
                          : 'in-progress'
                      }
                    >
                      {sessionInfo.status}
                    </StatusIndicator>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Comments</Box>
                    <Box>
                      {comments.filter((c) => c.status === 'pending').length} pending,{' '}
                      {comments.filter((c) => c.status === 'resolved').length} resolved
                    </Box>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Research Type</Box>
                    <Box>{sessionInfo.research_type || '-'}</Box>
                  </div>
                </ColumnLayout>
              </Box>
            )}

            {/* Main Content: Document + Comments Side by Side */}
            <div className="review-layout">
              <div className="document-panel">
                <DocumentViewer
                  markdown={markdown}
                  loading={false}
                  error={null}
                  onTextSelect={handleTextSelect}
                  onClearSelection={clearSelectionRef}
                  comments={comments}
                />
              </div>
              <div className="comments-panel">
                <CommentSystem
                  comments={comments}
                  onAddComment={handleAddComment}
                  onDeleteComment={handleDeleteComment}
                  onClearSelection={handleClearSelection}
                  selectedText={selectedText}
                  selectionPosition={selectionPosition}
                  sessionId={sessionId}
                />
              </div>
            </div>

          </SpaceBetween>
        </ContentLayout>
      }
    />
  );
}
