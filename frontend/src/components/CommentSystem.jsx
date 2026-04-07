import React, { useState } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  Button,
  Textarea,
  Cards,
  Badge,
  FormField,
  Alert
} from '@cloudscape-design/components';
import './CommentSystem.css';

export default function CommentSystem({
  comments = [],
  onAddComment,
  onDeleteComment,
  onClearSelection,
  selectedText,
  selectionPosition,
  sessionId,
  onCommentClick
}) {
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [newComment, setNewComment] = useState('');

  const handleCommentClick = (commentId) => {
    // Find the highlight in the document
    const highlightSpan = document.querySelector(`[data-comment-id="${commentId}"]`);
    if (highlightSpan) {
      // Scroll to the highlight
      highlightSpan.scrollIntoView({ behavior: 'smooth', block: 'center' });

      // Add temporary emphasis effect
      highlightSpan.style.transition = 'all 0.3s ease';
      highlightSpan.style.backgroundColor = '#ffc107';
      highlightSpan.style.transform = 'scale(1.05)';

      setTimeout(() => {
        highlightSpan.style.backgroundColor = '#fff3cd';
        highlightSpan.style.transform = 'scale(1)';
      }, 1000);
    }
  };

  const handleAddComment = () => {
    if (newComment.trim() && selectedText) {
      onAddComment({
        selectedText: selectedText.text,
        comment: newComment,
        position: selectionPosition,
        timestamp: new Date().toISOString()
      });
      setNewComment('');
      setShowCommentInput(false);
      // DO NOT call onClearSelection - keep the highlight
    }
  };


  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Group comments by status
  const pendingComments = comments.filter(c => c.status === 'pending');
  const resolvedComments = comments.filter(c => c.status === 'resolved');

  return (
    <div className="comment-system">
      <Container
        header={
          <Header
            variant="h2"
            counter={`(${comments.length})`}
            description="Review and annotate research document"
          >
            Comments
          </Header>
        }
      >
        <SpaceBetween size="l">
          {/* New Comment Input - Shows when text is selected */}
          {selectedText && (
            <div className="comment-input-section">
              <Alert
                type="info"
                header="Text selected"
                dismissible
                onDismiss={() => {
                  setShowCommentInput(false);
                  setNewComment('');
                  if (onClearSelection) {
                    onClearSelection();
                  }
                }}
              >
                <Box variant="p" fontSize="body-s">
                  <strong>Selected:</strong> "{selectedText.text.substring(0, 100)}
                  {selectedText.text.length > 100 ? '...' : ''}"
                </Box>
                {!showCommentInput ? (
                  <Button
                    iconName="add-plus"
                    onClick={() => setShowCommentInput(true)}
                    variant="primary"
                  >
                    Add Comment
                  </Button>
                ) : (
                  <SpaceBetween size="s">
                    <FormField label="Your comment">
                      <Textarea
                        value={newComment}
                        onChange={({ detail }) => setNewComment(detail.value)}
                        placeholder="Enter your review comment..."
                        rows={4}
                      />
                    </FormField>
                    <SpaceBetween direction="horizontal" size="xs">
                      <Button
                        variant="primary"
                        onClick={handleAddComment}
                        disabled={!newComment.trim()}
                      >
                        Save Comment
                      </Button>
                      <Button
                        variant="normal"
                        onClick={() => {
                          setShowCommentInput(false);
                          setNewComment('');
                        }}
                      >
                        Cancel
                      </Button>
                    </SpaceBetween>
                  </SpaceBetween>
                )}
              </Alert>
            </div>
          )}

          {/* Comments List */}
          {comments.length === 0 ? (
            <Box textAlign="center" padding="l" color="text-body-secondary">
              <Box variant="p">No comments yet</Box>
              <Box variant="small">
                Select text in the document to add your first comment
              </Box>
            </Box>
          ) : (
            <SpaceBetween size="m">
              {/* Pending Comments */}
              {pendingComments.length > 0 && (
                <div>
                  <Box variant="awsui-key-label" margin={{ bottom: 's' }}>
                    Pending Comments ({pendingComments.length})
                  </Box>
                  <Cards
                    cardDefinition={{
                      header: (comment) => (
                        <div
                          className="comment-card-header"
                          data-comment-card-id={comment.id}
                          onClick={() => handleCommentClick(comment.id)}
                          style={{ cursor: 'pointer' }}
                        >
                          <SpaceBetween direction="horizontal" size="xs">
                            <Badge color="blue">Pending</Badge>
                            <Box fontSize="body-s" color="text-body-secondary">
                              {formatTimestamp(comment.timestamp)}
                            </Box>
                          </SpaceBetween>
                        </div>
                      ),
                      sections: [
                        {
                          id: 'selected-text',
                          content: (comment) => (
                            <Box>
                              <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                                Selected Text
                              </Box>
                              <Box
                                padding="s"
                                backgroundColor="background-container-content"
                                borderRadius="default"
                              >
                                <Box
                                  fontSize="body-s"
                                  fontStyle="italic"
                                  color="text-body-secondary"
                                >
                                  "{comment.selectedText}"
                                </Box>
                              </Box>
                            </Box>
                          )
                        },
                        {
                          id: 'comment',
                          content: (comment) => (
                            <Box>
                              <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                                Comment
                              </Box>
                              <Box fontSize="body-m">{comment.comment}</Box>
                            </Box>
                          )
                        },
                        {
                          id: 'actions',
                          content: (comment) => (
                            <Button
                              iconName="remove"
                              variant="normal"
                              onClick={() => onDeleteComment(comment.id)}
                            >
                              Delete
                            </Button>
                          )
                        }
                      ]
                    }}
                    items={pendingComments}
                    cardsPerRow={[{ cards: 1 }]}
                  />
                </div>
              )}

              {/* Resolved Comments */}
              {resolvedComments.length > 0 && (
                <div>
                  <Box variant="awsui-key-label" margin={{ bottom: 's' }}>
                    Resolved Comments ({resolvedComments.length})
                  </Box>
                  <Cards
                    cardDefinition={{
                      header: (comment) => (
                        <div
                          className="comment-card-header"
                          data-comment-card-id={comment.id}
                          onClick={() => handleCommentClick(comment.id)}
                          style={{ cursor: 'pointer' }}
                        >
                          <SpaceBetween direction="horizontal" size="xs">
                            <Badge color="green">Resolved</Badge>
                            <Box fontSize="body-s" color="text-body-secondary">
                              {formatTimestamp(comment.timestamp)}
                            </Box>
                          </SpaceBetween>
                        </div>
                      ),
                      sections: [
                        {
                          id: 'selected-text',
                          content: (comment) => (
                            <Box>
                              <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                                Selected Text
                              </Box>
                              <Box
                                padding="s"
                                backgroundColor="background-container-content"
                                borderRadius="default"
                              >
                                <Box
                                  fontSize="body-s"
                                  fontStyle="italic"
                                  color="text-body-secondary"
                                >
                                  "{comment.selectedText}"
                                </Box>
                              </Box>
                            </Box>
                          )
                        },
                        {
                          id: 'comment',
                          content: (comment) => (
                            <Box>
                              <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                                Comment
                              </Box>
                              <Box fontSize="body-m" color="text-body-secondary">
                                {comment.comment}
                              </Box>
                            </Box>
                          )
                        }
                      ]
                    }}
                    items={resolvedComments}
                    cardsPerRow={[{ cards: 1 }]}
                  />
                </div>
              )}
            </SpaceBetween>
          )}
        </SpaceBetween>
      </Container>
    </div>
  );
}
