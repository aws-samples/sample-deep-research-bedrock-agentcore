import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  ColumnLayout,
  StatusIndicator,
  ProgressBar,
  Spinner,
  Alert,
  Button,
  ButtonDropdown,
  CopyToClipboard
} from '@cloudscape-design/components';
import { useResearchStatus } from '../hooks/useResearchStatus';
import {
  getProgressPercentage,
  formatElapsedTime
} from '../utils/workflowStages';
import { formatResearchType, formatDate } from '../utils/formatters';
import WorkflowVisualizer from '../components/WorkflowVisualizer';
import ResearchProgressTracker from '../components/ResearchProgressTracker';
import { api } from '../services/api';

export default function ResearchDetails({ addNotification }) {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [downloadLinks, setDownloadLinks] = useState(null);
  const [loadingLinks, setLoadingLinks] = useState(false);
  const [initialStatus, setInitialStatus] = useState(null);
  const [cancelling, setCancelling] = useState(false);

  const { status, loading, error } = useResearchStatus(sessionId, {
    onComplete: (data) => {
      // Only show notification if research just completed (was processing before)
      if (initialStatus && initialStatus !== 'completed') {
        addNotification({
          type: 'success',
          content: 'Research completed successfully!'
        });
      }
    },
    onError: (err) => {
      // Only show notification for actual errors, not initial load failures
      if (initialStatus) {
        addNotification({
          type: 'error',
          content: `Error during research: ${err.message}`
        });
      }
    }
  });

  // Track initial status to avoid showing notifications for already-completed research
  useEffect(() => {
    if (status && !initialStatus) {
      setInitialStatus(status.status);
    }
  }, [status, initialStatus]);

  // Fetch download links when research is completed
  useEffect(() => {
    if (status?.status === 'completed' && !downloadLinks && !loadingLinks) {
      setLoadingLinks(true);
      api.getDownloadLinks(sessionId)
        .then(data => {
          setDownloadLinks(data.downloads);
        })
        .catch(err => {
          console.error('Failed to fetch download links:', err);
          addNotification({
            type: 'warning',
            content: 'Download links are not yet available. Please try again in a moment.'
          });
        })
        .finally(() => {
          setLoadingLinks(false);
        });
    }
  }, [status?.status, sessionId, downloadLinks, loadingLinks, addNotification]);

  if (loading && !status) {
    return (
      <Container>
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" padding={{ top: 's' }}>
            Loading research session...
          </Box>
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container>
        <Alert type="error" header="Failed to load research">
          {error}
        </Alert>
      </Container>
    );
  }

  const handleDownload = (url, filename) => {
    window.open(url, '_blank');
    addNotification({
      type: 'success',
      content: `Downloading ${filename}...`
    });
  };

  const handleCancel = async () => {
    try {
      setCancelling(true);
      await api.cancelResearch(sessionId);
      addNotification({
        type: 'success',
        content: 'Research cancelled successfully'
      });
    } catch (error) {
      addNotification({
        type: 'error',
        content: `Failed to cancel research: ${error.message}`
      });
    } finally {
      setCancelling(false);
    }
  };

  const getDownloadActions = () => {
    if (!downloadLinks) return [];

    const actions = [];

    if (downloadLinks.pdf?.url) {
      actions.push({
        id: 'pdf',
        text: 'PDF Document (.pdf)'
      });
    }

    if (downloadLinks.docx?.url) {
      actions.push({
        id: 'docx',
        text: 'Word Document (.docx)'
      });
    }

    if (downloadLinks.markdown?.url) {
      actions.push({
        id: 'markdown',
        text: 'Markdown (.md)'
      });
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

  const isComplete = status?.status === 'completed';
  const isFailed = status?.status === 'failed';
  const isProcessing = status?.status === 'processing' || status?.status === 'pending';
  const isCancelling = status?.status === 'cancelling';
  const isCancelled = status?.status === 'cancelled';

  return (
    <SpaceBetween size="l">
      {/* Topic Header */}
      {status?.topic && (
        <Header variant="h1">
          {status.topic}
        </Header>
      )}

      {/* Session Information */}
      <Container
        header={
          <Header
            variant="h2"
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                {isComplete && (
                  <>
                    <Button
                      iconName="edit"
                      onClick={() => navigate(`/research/${sessionId}/review`)}
                      variant="primary"
                    >
                      Review Research
                    </Button>
                    <Button
                      iconName="share"
                      onClick={() => navigate(`/research/traces?session=${sessionId}`)}
                    >
                      View Trace
                    </Button>
                  </>
                )}
                {(isProcessing || isCancelling) && (
                  <Button
                    onClick={handleCancel}
                    loading={cancelling || isCancelling}
                    disabled={cancelling || isCancelling}
                    variant="normal"
                  >
                    {isCancelling ? 'Cancelling...' : 'Cancel Research'}
                  </Button>
                )}
                <ButtonDropdown
                  items={getDownloadActions()}
                  loading={loadingLinks}
                  disabled={!isComplete || loadingLinks || getDownloadActions().length === 0}
                  onItemClick={handleDropdownItemClick}
                >
                  Download Report
                </ButtonDropdown>
              </SpaceBetween>
            }
          >
            Research Details
          </Header>
        }
      >

        {/* Research Context */}
        {status?.research_context && (
          <Box margin={{ bottom: 'l' }}>
            <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>Research Context</Box>
            <Box
              padding="m"
              backgroundColor="background-container-content"
              borderRadius="default"
            >
              <Box fontSize="body-m" color="text-body-secondary" lineHeight="body-m">
                {status.research_context}
              </Box>
            </Box>
          </Box>
        )}
        {/* Research ID and Status */}
        <ColumnLayout columns={2} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">Research ID</Box>
            <Box display="flex" alignItems="center">
              <code style={{ fontSize: '13px', marginRight: '8px' }}>{sessionId}</code>
              <CopyToClipboard
                copyText={sessionId}
                copyButtonAriaLabel="Copy Research ID"
                copySuccessText="Research ID copied"
                variant="inline"
              />
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Status</Box>
            <Box>
              <StatusIndicator
                type={
                  isComplete ? 'success' :
                  isFailed ? 'error' :
                  isCancelled ? 'stopped' :
                  isCancelling ? 'warning' :
                  'in-progress'
                }
              >
                {isCancelling ? 'Cancelling (finishing current task...)' : status?.status || 'Unknown'}
              </StatusIndicator>
            </Box>
          </div>
        </ColumnLayout>

        {/* Timing Information */}
        <Box margin={{ top: 'm' }}>
          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Started</Box>
              <Box>
                {formatDate(status?.created_at)}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Completed</Box>
              <Box>
                {isComplete ? formatDate(status?.completed_at) : '-'}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Duration</Box>
              <Box>
                {isComplete && status?.elapsed_time ? formatElapsedTime(status.elapsed_time) : '-'}
              </Box>
            </div>
          </ColumnLayout>
        </Box>

        {/* Research Configuration */}
        <Box margin={{ top: 'm' }}>
          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Research Type</Box>
              <Box>
                {status?.research_type ? formatResearchType(status.research_type) : '-'}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Model</Box>
              <Box>
                {status?.model || '-'}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Research Depth</Box>
              <Box>
                {status?.research_depth || '-'}
              </Box>
            </div>
          </ColumnLayout>
        </Box>
      </Container>

      {/* Workflow Progress - Show stages visually */}
      {status?.current_stage && (
        <Container header={<Header variant="h2">Workflow Progress</Header>}>
          <SpaceBetween size="m">
            {/* Show progress bar only during processing */}
            {isProcessing && (
              <ProgressBar
                value={getProgressPercentage(status?.current_stage)}
                status="in-progress"
                resultText={`${getProgressPercentage(status?.current_stage)}% complete`}
              />
            )}
            <WorkflowVisualizer currentStage={status?.current_stage} />
          </SpaceBetween>
        </Container>
      )}

      {/* Error Message */}
      {isFailed && status?.error && (
        <Alert type="error" header="Research Failed">
          {status.error}
        </Alert>
      )}

      {/* Errors Summary */}
      {status?.errors && status.errors.length > 0 && (
        <Alert
          type="warning"
          header={`${status.errors.length} error(s) occurred during research`}
        >
          <SpaceBetween size="xs">
            {status.errors.map((error, idx) => (
              <Box key={idx}>
                <Box variant="strong">{error.node}</Box>
                {error.context && (
                  <Box fontSize="body-s" color="text-body-secondary">
                    {error.context.dimension && `Dimension: ${error.context.dimension}`}
                    {error.context.aspect && ` | Aspect: ${error.context.aspect}`}
                  </Box>
                )}
                <Box fontSize="body-s">{error.error}</Box>
                <Box fontSize="body-s" color="text-body-secondary">
                  {formatDate(error.timestamp)}
                </Box>
              </Box>
            ))}
          </SpaceBetween>
        </Alert>
      )}

      {/* Research Dimensions - includes dimensions and aspects */}
      {status?.aspects_by_dimension && (
        <Container header={<Header variant="h2">Research Dimensions</Header>}>
          <ResearchProgressTracker
            aspectsByDimension={status.aspects_by_dimension}
            researchByAspect={status.research_by_aspect}
          />
        </Container>
      )}

      {/* Results */}
      {isComplete && (
        <Container header={<Header variant="h2">Research Results</Header>}>
          <SpaceBetween size="l">
            {/* Download Links */}
            {downloadLinks && (
              <Box>
                <Box variant="awsui-key-label" margin={{ bottom: 's' }}>Download Research Report</Box>
                <SpaceBetween direction="horizontal" size="xs">
                  {downloadLinks.pdf?.url && (
                    <Button
                      iconName="download"
                      onClick={() => handleDownload(downloadLinks.pdf.url, downloadLinks.pdf.filename)}
                    >
                      PDF Document
                    </Button>
                  )}
                  {downloadLinks.docx?.url && (
                    <Button
                      iconName="download"
                      variant="normal"
                      onClick={() => handleDownload(downloadLinks.docx.url, downloadLinks.docx.filename)}
                    >
                      Word Document
                    </Button>
                  )}
                  {downloadLinks.markdown?.url && (
                    <Button
                      iconName="download"
                      variant="normal"
                      onClick={() => handleDownload(downloadLinks.markdown.url, downloadLinks.markdown.filename)}
                    >
                      Markdown
                    </Button>
                  )}
                </SpaceBetween>
              </Box>
            )}

            {loadingLinks && (
              <Box>
                <Spinner size="normal" /> Preparing download links...
              </Box>
            )}

            {/* S3 Report Location */}
            {status?.s3_uploads?.uploads?.docx?.s3_uri && (
              <Box>
                <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>S3 Location</Box>
                <Box display="flex" alignItems="center">
                  <Box
                    padding="xs"
                    backgroundColor="background-container-content"
                    borderRadius="default"
                    flex="1"
                  >
                    <code style={{
                      fontSize: '12px',
                      wordBreak: 'break-all',
                      color: 'var(--color-text-body-secondary)'
                    }}>
                      {status.s3_uploads.uploads.docx.s3_uri}
                    </code>
                  </Box>
                  <Box margin={{ left: 'xs' }}>
                    <CopyToClipboard
                      copyText={status.s3_uploads.uploads.docx.s3_uri}
                      copyButtonAriaLabel="Copy S3 URI"
                      copySuccessText="S3 URI copied"
                      variant="inline"
                    />
                  </Box>
                </Box>
              </Box>
            )}
          </SpaceBetween>
        </Container>
      )}
    </SpaceBetween>
  );
}
