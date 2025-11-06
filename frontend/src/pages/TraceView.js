import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  ColumnLayout,
  StatusIndicator,
  KeyValuePairs,
  Button,
  Select,
  Grid,
  Alert,
  Spinner
} from '@cloudscape-design/components';
import { WorkflowNode } from '../components/WorkflowNode';
import { createFlowElements } from '../utils/flowLayoutUtils';
import { api } from '../services/api';

// Define custom node types
const nodeTypes = {
  workflowNode: WorkflowNode,
};

export default function TraceView() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionIdFromUrl = searchParams.get('session');

  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [sessionError, setSessionError] = useState(null);
  const [memoryEvents, setMemoryEvents] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [showFullContent, setShowFullContent] = useState(false);
  const [showSources, setShowSources] = useState(false);

  // Fetch research sessions on mount
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        setLoadingSessions(true);
        const response = await api.getResearchHistory(100); // Get more sessions

        if (response.sessions && response.sessions.length > 0) {
          // Filter completed sessions only
          const completedSessions = response.sessions.filter(
            s => s.status === 'completed'
          );
          setSessions(completedSessions);

          // If URL has session parameter, auto-select that session
          if (sessionIdFromUrl) {
            const targetSession = completedSessions.find(
              s => s.session_id === sessionIdFromUrl
            );
            if (targetSession) {
              setSelectedSession({
                label: targetSession.topic,
                value: targetSession.session_id,
                sessionData: targetSession
              });
              return;
            }
          }

          // Otherwise, auto-select first completed session
          if (completedSessions.length > 0) {
            setSelectedSession({
              label: completedSessions[0].topic,
              value: completedSessions[0].session_id,
              sessionData: completedSessions[0]
            });
          }
        }
      } catch (error) {
        console.error('Failed to fetch research sessions:', error);
        setSessionError(error.message);
      } finally {
        setLoadingSessions(false);
      }
    };

    fetchSessions();
  }, [sessionIdFromUrl]);

  // Fetch AgentCore Memory events when session changes
  useEffect(() => {
    if (selectedSession?.value) {
      const fetchMemoryEvents = async () => {
        setLoadingEvents(true);
        try {
          console.log(`Fetching AgentCore Memory events for session: ${selectedSession.value}`);

          // Call BFF API to get memory events
          const response = await api.getMemoryEvents(selectedSession.value, 100);

          console.log(`Fetched ${response.events.length} events from AgentCore Memory`);
          console.log('Events data:', response.events);

          // Log event types
          console.log('Event types:', response.events.map(e => e.type));

          // Log first event in detail
          if (response.events.length > 0) {
            console.log('First event detail:', JSON.stringify(response.events[0], null, 2));
          }

          // Update with fetched events (empty array if none)
          setMemoryEvents(response.events || []);
        } catch (error) {
          console.error('Failed to fetch AgentCore Memory events:', error);
          // Set empty array on error
          setMemoryEvents([]);
        } finally {
          setLoadingEvents(false);
        }
      };

      fetchMemoryEvents();
    }
  }, [selectedSession]);

  // Create session options for dropdown
  const sessionOptions = sessions.map(session => ({
    label: session.topic,
    value: session.session_id,
    description: `${session.status} - ${new Date(session.created_at).toLocaleDateString()} (${(session.elapsed_time / 60).toFixed(1)} min)`,
    sessionData: session
  }));

  // Create flow elements from events - update when memoryEvents or selectedSession changes
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => createFlowElements(
      memoryEvents,
      selectedSession?.sessionData?.dimensions || []
    ),
    [memoryEvents, selectedSession]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes and edges when flow elements change
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // Handle node click
  const onNodeClick = useCallback((event, node) => {
    console.log('Node clicked:', node.data.event);
    console.log('Event type:', node.data.event?.type);
    console.log('Event data:', node.data.event?.data);
    setSelectedNode(node.data.event);
  }, []);

  // Close detail panel
  const closeDetailPanel = () => {
    setSelectedNode(null);
  };

  // Extract URLs and sources from markdown content
  const extractSourcesFromContent = (content) => {
    if (!content) return [];

    // Remove code blocks to avoid extracting URLs from code examples
    let contentWithoutCode = content;

    // Remove fenced code blocks (```...```)
    contentWithoutCode = contentWithoutCode.replace(/```[\s\S]*?```/g, '');

    // Remove inline code (`...`)
    contentWithoutCode = contentWithoutCode.replace(/`[^`]+`/g, '');

    const sources = [];
    const seenUrls = new Set();

    // Extract inline reference style: [https://...]
    const inlineRefRegex = /\[(https?:\/\/[^\]]+)\]/g;
    let match;
    while ((match = inlineRefRegex.exec(contentWithoutCode)) !== null) {
      const url = match[1];
      if (!seenUrls.has(url)) {
        seenUrls.add(url);
        // Extract domain name as title
        const domain = url.replace(/^https?:\/\//, '').split('/')[0];
        sources.push({
          type: 'inline-ref',
          title: domain,
          url: url
        });
      }
    }

    // Extract markdown links: [text](url)
    const markdownLinkRegex = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
    while ((match = markdownLinkRegex.exec(contentWithoutCode)) !== null) {
      const url = match[2];
      if (!seenUrls.has(url)) {
        seenUrls.add(url);
        sources.push({
          type: 'link',
          title: match[1],
          url: url
        });
      }
    }

    // Extract citation-style references: [1]: https://...
    const citationRegex = /^\[(\d+)\]:\s*(https?:\/\/[^\s]+)/gm;
    while ((match = citationRegex.exec(contentWithoutCode)) !== null) {
      const url = match[2];
      if (!seenUrls.has(url)) {
        seenUrls.add(url);
        sources.push({
          type: 'citation',
          title: `[${match[1]}]`,
          url: url
        });
      }
    }

    return sources;
  };

  // Download content as markdown file
  const downloadContent = (content, filename) => {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Format event metadata (without full content)
  const formatEventMetadata = (data, sourcesCount = null) => {
    if (!data) return {};

    const metadata = {};

    // Common fields
    if (data.event_type) metadata['Event Type'] = data.event_type;
    if (data.timestamp) metadata['Timestamp'] = new Date(data.timestamp).toLocaleString();

    // Dimension/Aspect specific
    if (data.dimension) metadata['Dimension'] = data.dimension;
    if (data.aspect) metadata['Aspect'] = data.aspect;

    // Dimension document specific
    if (data.filename) metadata['Filename'] = data.filename;
    if (data.content_size_bytes) {
      const sizeKB = (data.content_size_bytes / 1024).toFixed(2);
      metadata['Content Size'] = `${sizeKB} KB`;
    }

    // Metrics
    if (data.word_count) metadata['Word Count'] = data.word_count;
    if (data.aspect_count) metadata['Aspect Count'] = data.aspect_count;

    // Use actual extracted sources count if available, otherwise use stored count
    if (sourcesCount !== null && sourcesCount > 0) {
      metadata['Sources Count'] = sourcesCount;
    } else if (data.citations_count !== undefined) {
      metadata['Citations Count'] = data.citations_count;
    }

    if (data.reference_count) metadata['Reference Count'] = data.reference_count;
    if (data.dimension_count) metadata['Dimension Count'] = data.dimension_count;
    if (data.total_aspects) metadata['Total Aspects'] = data.total_aspects;

    // Research output title
    if (data.research_content) {
      metadata['Research Title'] = data.research_content.title || 'N/A';
    }

    // Dimension list (only for dimensions_identified, not for individual dimension display)
    if (data.dimensions && Array.isArray(data.dimensions) && !data.aspect) {
      metadata['Total Dimensions'] = data.dimensions.length;
    }

    // Reference materials count
    if (data.reference_materials && Array.isArray(data.reference_materials)) {
      metadata['Reference Materials'] = `${data.reference_materials.length} materials`;
    }

    // Output files
    if (data.output_files) {
      metadata['Output Files'] = Object.keys(data.output_files).join(', ');
    }

    // Note: aspects array is displayed separately in dedicated section, not in metadata
    // Exclude it from metadata to avoid rendering issues

    return metadata;
  };

  return (
    <Grid gridDefinition={selectedNode ? [{ colspan: 8 }, { colspan: 4 }] : [{ colspan: 12 }]}>
      {/* Main Flow View */}
      <SpaceBetween size="l">
        {/* Header with Session Selector */}
        <Container
          header={
            <Header
              variant="h1"
              description="Visualize research workflow execution as a DAG"
              actions={
                selectedSession && (
                  <Button
                    iconName="external"
                    onClick={() => navigate(`/research/${selectedSession.value}`)}
                  >
                    View Research Details
                  </Button>
                )
              }
            >
              Research Trace View
            </Header>
          }
        >
          <SpaceBetween size="m">
            {sessionError && (
              <Alert type="error" header="Failed to load sessions">
                {sessionError}
              </Alert>
            )}

            <Box>
              <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                Select Research Session
              </Box>
              <Select
                selectedOption={selectedSession}
                onChange={({ detail }) => setSelectedSession(detail.selectedOption)}
                options={sessionOptions}
                placeholder={loadingSessions ? "Loading sessions..." : "Choose a research session"}
                loadingText="Loading sessions..."
                statusType={loadingSessions ? "loading" : sessionOptions.length === 0 ? "error" : "finished"}
                empty="No completed research sessions found"
                expandToViewport
                disabled={loadingSessions}
              />
            </Box>

            {/* Session Summary */}
            {selectedSession && selectedSession.sessionData && (
              <ColumnLayout columns={4} variant="text-grid">
                <div>
                  <Box variant="awsui-key-label">Status</Box>
                  <StatusIndicator type="success">
                    {selectedSession.sessionData.status}
                  </StatusIndicator>
                </div>
                <div>
                  <Box variant="awsui-key-label">Duration</Box>
                  <Box>{selectedSession.sessionData.elapsed_time ? (selectedSession.sessionData.elapsed_time / 60).toFixed(1) : 'N/A'} minutes</Box>
                </div>
                <div>
                  <Box variant="awsui-key-label">Dimensions</Box>
                  <Box>{selectedSession.sessionData.dimensions?.length || 0}</Box>
                </div>
                <div>
                  <Box variant="awsui-key-label">Total Events</Box>
                  <Box>
                    {loadingEvents ? <Spinner size="normal" /> : memoryEvents.length}
                  </Box>
                </div>
              </ColumnLayout>
            )}
          </SpaceBetween>
        </Container>

        {/* Workflow DAG */}
        <Container
          header={
            <Header variant="h2">
              Workflow Graph
              {loadingEvents && <Spinner size="normal" />}
            </Header>
          }
        >
          {loadingEvents ? (
            <Box textAlign="center" padding="xxl">
              <Spinner size="large" />
              <Box variant="p" padding={{ top: 's' }}>
                Loading workflow events from AgentCore Memory...
              </Box>
            </Box>
          ) : (
            <>
              <div style={{ width: '100%', height: '750px', background: 'linear-gradient(to bottom, #f9fafb 0%, #f3f4f6 100%)' }}>
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onNodeClick={onNodeClick}
                  nodeTypes={nodeTypes}
                  nodesDraggable={false}
                  nodesConnectable={false}
                  nodesFocusable={false}
                  edgesFocusable={false}
                  elementsSelectable={true}
                  deleteKeyCode={null}
                  defaultViewport={{ x: 20, y: 50, zoom: 0.85 }}
                  minZoom={0.3}
                  maxZoom={1.5}
                  attributionPosition="bottom-left"
                >
                  <Background color="#d1d5db" gap={20} size={1} />
                  <Controls showInteractive={false} />
                  <MiniMap
                    nodeColor={(node) => {
                      if (node.data?.type === 'aspect_analysis') return '#0972d3';
                      if (node.data?.type === 'aspect_research_complete') return '#8b46ff';
                      if (node.data?.type === 'dimension_document_complete') return '#ff6b00';
                      return '#037f0c';
                    }}
                    maskColor="rgba(0, 0, 0, 0.1)"
                  />
                </ReactFlow>
              </div>
              <Box margin={{ top: 's' }}>
                <Alert type="info">
                  Click on any node to view detailed event information in the side panel
                </Alert>
              </Box>
            </>
          )}
        </Container>
      </SpaceBetween>

      {/* Detail Panel (Right Side) */}
      {selectedNode && (() => {
        // Extract sources and content based on event type
        const eventType = selectedNode.type;

        // Research aspect content
        const hasResearchContent = selectedNode.data?.research_content?.content;
        const researchContent = hasResearchContent ? selectedNode.data.research_content.content : null;

        // Dimension summary content (dimension_document_complete or dimension_summary type)
        const hasDimensionContent = selectedNode.data?.markdown_content ||
                                    (selectedNode.type === 'dimension_document_complete' && selectedNode.data?.markdown_content);
        const dimensionContent = selectedNode.data?.markdown_content || null;

        // Unified content variable
        const content = researchContent || dimensionContent;
        const hasContent = !!content;

        // Extract sources from content
        const sources = content ? extractSourcesFromContent(content) : [];

        // Dimensions identified data (full breakdown)
        const hasDimensionsData = selectedNode.data?.dimensions && selectedNode.data?.aspects_by_dimension;

        // Single dimension data (dimension_start nodes)
        const hasSingleDimensionData = selectedNode.data?.dimension && selectedNode.data?.aspects && !selectedNode.data?.dimensions;

        return (
          <Container
            header={
              <Header
                variant="h2"
                actions={
                  <Button onClick={closeDetailPanel} iconName="close">
                    Close
                  </Button>
                }
              >
                Event Details
              </Header>
            }
          >
            <SpaceBetween size="m">
              {/* Event Metadata */}
              <Box>
                <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                  Metadata
                </Box>
                <KeyValuePairs
                  columns={1}
                  items={Object.entries(formatEventMetadata(selectedNode.data, sources.length))
                    .filter(([key, value]) => {
                      // Exclude complex objects and arrays from metadata display
                      return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean';
                    })
                    .map(([key, value]) => ({
                      label: key,
                      value: String(value)
                    }))}
                />
              </Box>

              {/* Dimensions & Aspects Breakdown (for dimensions_identified) */}
              {hasDimensionsData && (
                <Box>
                  <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                    Dimensions & Aspects
                  </Box>
                  <Box
                    padding="m"
                    backgroundColor="background-container-content"
                    borderRadius="default"
                  >
                    <SpaceBetween size="m">
                      {selectedNode.data.dimensions.map((dimension, idx) => {
                        const aspects = selectedNode.data.aspects_by_dimension[dimension] || [];
                        return (
                          <Box key={idx}>
                            <SpaceBetween size="xs">
                              <Box fontSize="body-m" fontWeight="bold" color="text-heading-default">
                                {idx + 1}. {dimension}
                              </Box>
                              <Box padding={{ left: 'm' }}>
                                <SpaceBetween size="xxs">
                                  {aspects.map((aspect, aspectIdx) => {
                                    // Handle both string and object formats
                                    const aspectName = typeof aspect === 'string' ? aspect : (aspect?.name || 'Unknown');
                                    return (
                                      <Box key={aspectIdx} fontSize="body-s" color="text-body-secondary">
                                        • {aspectName}
                                      </Box>
                                    );
                                  })}
                                </SpaceBetween>
                              </Box>
                            </SpaceBetween>
                          </Box>
                        );
                      })}
                    </SpaceBetween>
                  </Box>
                </Box>
              )}

              {/* Single Dimension Aspects (for dimension_start nodes) */}
              {hasSingleDimensionData && (() => {
                // Get detailed aspect info from dimensions_identified event
                const dimensionsIdentifiedEvent = selectedNode.data.dimensions_identified_event;
                const currentDimension = selectedNode.data.dimension;

                // Try to get detailed aspects from dimensions_identified event
                let detailedAspects = null;
                if (dimensionsIdentifiedEvent?.data?.aspects_by_dimension) {
                  detailedAspects = dimensionsIdentifiedEvent.data.aspects_by_dimension[currentDimension];
                }

                return (
                  <Box>
                    <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                      Aspects in this Dimension
                    </Box>
                    <Box
                      padding="m"
                      backgroundColor="background-container-content"
                      borderRadius="default"
                    >
                      <SpaceBetween size="m">
                        {detailedAspects && Array.isArray(detailedAspects) ? (
                          // Show detailed aspect information
                          detailedAspects.map((aspect, idx) => {
                            const aspectName = typeof aspect === 'string' ? aspect : (aspect?.name || 'Unknown');
                            const aspectReasoning = typeof aspect === 'object' ? aspect?.reasoning : null;
                            const aspectQuestions = typeof aspect === 'object' ? aspect?.key_questions : null;

                            return (
                              <Box key={idx}>
                                <SpaceBetween size="xs">
                                  <Box fontSize="body-m" fontWeight="bold" color="text-heading-default">
                                    {idx + 1}. {aspectName}
                                  </Box>
                                  {aspectReasoning && (
                                    <Box padding={{ left: 'm' }}>
                                      <Box fontSize="body-s" fontWeight="bold" margin={{ bottom: 'xxs' }}>
                                        Reasoning:
                                      </Box>
                                      <Box fontSize="body-s" color="text-body-secondary">
                                        {aspectReasoning}
                                      </Box>
                                    </Box>
                                  )}
                                  {aspectQuestions && aspectQuestions.length > 0 && (
                                    <Box padding={{ left: 'm' }}>
                                      <Box fontSize="body-s" fontWeight="bold" margin={{ bottom: 'xxs' }}>
                                        Key Questions:
                                      </Box>
                                      <SpaceBetween size="xxs">
                                        {aspectQuestions.map((question, qIdx) => (
                                          <Box key={qIdx} fontSize="body-s" color="text-body-secondary">
                                            • {question}
                                          </Box>
                                        ))}
                                      </SpaceBetween>
                                    </Box>
                                  )}
                                </SpaceBetween>
                              </Box>
                            );
                          })
                        ) : (
                          // Fallback: Show simple aspect names
                          selectedNode.data.aspects.map((aspect, idx) => {
                            const aspectName = typeof aspect === 'string' ? aspect : (aspect?.name || 'Unknown');
                            return (
                              <Box key={idx} fontSize="body-s">
                                {idx + 1}. {aspectName}
                              </Box>
                            );
                          })
                        )}
                      </SpaceBetween>
                    </Box>
                  </Box>
                );
              })()}

              {/* Reference Materials (for references_prepared) */}
              {selectedNode.data?.reference_materials && Array.isArray(selectedNode.data.reference_materials) && (
                <Box>
                  <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                    Reference Materials
                  </Box>
                  <Box
                    padding="m"
                    backgroundColor="background-container-content"
                    borderRadius="default"
                  >
                    <SpaceBetween size="m">
                      {selectedNode.data.reference_materials.map((ref, idx) => (
                        <Box key={idx}>
                          <SpaceBetween size="xs">
                            <Box fontSize="body-m" fontWeight="bold" color="text-heading-default">
                              {idx + 1}. [{ref.type.toUpperCase()}] {ref.title}
                            </Box>
                            <Box fontSize="body-s" color="text-body-secondary">
                              Source: {ref.source}
                            </Box>
                            {ref.note && (
                              <Box fontSize="body-s" color="text-status-info">
                                Note: {ref.note}
                              </Box>
                            )}
                            {ref.key_points && ref.key_points.length > 0 && (
                              <Box padding={{ left: 'm' }}>
                                <Box fontSize="body-s" fontWeight="bold" margin={{ bottom: 'xxs' }}>
                                  Key Points:
                                </Box>
                                <SpaceBetween size="xxs">
                                  {ref.key_points.slice(0, 3).map((point, pointIdx) => (
                                    <Box key={pointIdx} fontSize="body-s" color="text-body-secondary">
                                      • {point}
                                    </Box>
                                  ))}
                                  {ref.key_points.length > 3 && (
                                    <Box fontSize="body-s" color="text-label">
                                      ... and {ref.key_points.length - 3} more
                                    </Box>
                                  )}
                                </SpaceBetween>
                              </Box>
                            )}
                          </SpaceBetween>
                        </Box>
                      ))}
                    </SpaceBetween>
                  </Box>
                </Box>
              )}

              {/* Dimension Summary Info (for dimension_summary virtual nodes) */}
              {eventType === 'dimension_summary' && selectedNode.data?.aspects && Array.isArray(selectedNode.data.aspects) && (
                <Box>
                  <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                    Aspects in this Dimension
                  </Box>
                  <Box
                    padding="m"
                    backgroundColor="background-container-content"
                    borderRadius="default"
                  >
                    <SpaceBetween size="s">
                      {selectedNode.data.aspects.map((aspect, idx) => {
                        // Extract aspect name - handle both string and object formats
                        const aspectName = typeof aspect === 'string' ? aspect : (aspect?.name || 'Unknown');

                        return (
                          <Box key={idx} fontSize="body-s">
                            {idx + 1}. {aspectName}
                          </Box>
                        );
                      })}
                    </SpaceBetween>
                  </Box>
                  <Box padding={{ top: 's' }}>
                    <Alert type="info">
                      This is a reduce node that aggregates {selectedNode.data.aspect_count || 0} aspect research results for the "{selectedNode.data.dimension || 'Unknown'}" dimension.
                    </Alert>
                  </Box>
                </Box>
              )}

              {/* Content Download & Preview */}
              {hasContent && (
                  <Box>
                    <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                      {hasDimensionContent ? 'Dimension Document' : 'Research Content'}
                    </Box>
                    <SpaceBetween size="s">
                      <Button
                        iconName="download"
                        onClick={() => {
                          const name = selectedNode.data?.filename ||
                                      selectedNode.aspect ||
                                      selectedNode.dimension ||
                                      selectedNode.type;
                          const filename = `${name}-${Date.now()}.md`;
                          downloadContent(content, filename);
                        }}
                      >
                        Download {hasDimensionContent ? 'Document' : 'Content'} (Markdown)
                      </Button>

                      <Button
                        iconName={showFullContent ? "angle-up" : "angle-down"}
                        variant="inline-link"
                        onClick={() => setShowFullContent(!showFullContent)}
                      >
                        {showFullContent ? "Hide Content" : "Show Content Preview"}
                      </Button>

                      {showFullContent && (
                        <Box
                          padding="m"
                          backgroundColor="background-container-content"
                          borderRadius="default"
                        >
                          <pre style={{
                            fontSize: '12px',
                            margin: 0,
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            maxHeight: '400px',
                            overflow: 'auto',
                            lineHeight: '1.5'
                          }}>
                            {content}
                          </pre>
                        </Box>
                      )}
                    </SpaceBetween>
                  </Box>
                )}

              {/* Research Start Details (formatted) */}
              {eventType === 'research_start' && (
                <Box>
                  <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                    Research Configuration
                  </Box>
                  <Box
                    padding="m"
                    backgroundColor="background-container-content"
                    borderRadius="default"
                  >
                    <SpaceBetween size="s">
                      {selectedNode.data.topic && (
                        <Box>
                          <Box fontSize="body-s" fontWeight="bold">Topic:</Box>
                          <Box fontSize="body-s" color="text-body-secondary" padding={{ top: 'xxs' }}>
                            {selectedNode.data.topic}
                          </Box>
                        </Box>
                      )}
                      {selectedNode.data.research_context && (
                        <Box>
                          <Box fontSize="body-s" fontWeight="bold">Research Context:</Box>
                          <Box fontSize="body-s" color="text-body-secondary" padding={{ top: 'xxs' }}>
                            {selectedNode.data.research_context}
                          </Box>
                        </Box>
                      )}
                      {selectedNode.data.model && (
                        <Box>
                          <Box fontSize="body-s" fontWeight="bold">Model:</Box>
                          <Box fontSize="body-s" color="text-body-secondary" padding={{ top: 'xxs' }}>
                            {selectedNode.data.model}
                          </Box>
                        </Box>
                      )}
                      {selectedNode.data.research_type && (
                        <Box>
                          <Box fontSize="body-s" fontWeight="bold">Research Type:</Box>
                          <Box fontSize="body-s" color="text-body-secondary" padding={{ top: 'xxs' }}>
                            {selectedNode.data.research_type}
                          </Box>
                        </Box>
                      )}
                      {selectedNode.data.research_depth && (
                        <Box>
                          <Box fontSize="body-s" fontWeight="bold">Research Depth:</Box>
                          <Box fontSize="body-s" color="text-body-secondary" padding={{ top: 'xxs' }}>
                            {selectedNode.data.research_depth}
                          </Box>
                        </Box>
                      )}
                    </SpaceBetween>
                  </Box>
                </Box>
              )}

              {/* Raw Event Data (only for specific event types that need it) */}
              {!selectedNode.data?.research_content?.content &&
               !hasDimensionsData &&
               !hasSingleDimensionData &&
               eventType !== 'research_start' &&
               eventType !== 'research_complete' && (
                <Box>
                  <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                    Event Data
                  </Box>
                  <Box
                    padding="m"
                    backgroundColor="background-container-content"
                    borderRadius="default"
                  >
                    <pre style={{
                      fontSize: '12px',
                      margin: 0,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      maxHeight: '400px',
                      overflow: 'auto',
                      lineHeight: '1.5'
                    }}>
                      {JSON.stringify(selectedNode.data, null, 2)}
                    </pre>
                  </Box>
                </Box>
              )}

              {/* Sources & References (at the bottom, collapsible) */}
              {sources.length > 0 && (
                <Box>
                  <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                    Sources & References
                  </Box>
                  <SpaceBetween size="s">
                    <Box>
                      <Button
                        iconName={showSources ? "angle-up" : "angle-down"}
                        variant="inline-link"
                        onClick={() => setShowSources(!showSources)}
                      >
                        {showSources ? "Hide Sources" : `Show ${sources.length} Sources`}
                      </Button>
                    </Box>

                    {showSources && (
                      <Box
                        padding="m"
                        backgroundColor="background-container-content"
                        borderRadius="default"
                      >
                        <SpaceBetween size="s">
                          {sources.map((source, idx) => (
                            <Box key={idx} padding={{ vertical: 'xs' }}>
                              <SpaceBetween size="xxs">
                                <Box fontSize="body-s" color="text-label">
                                  [{idx + 1}] {source.title}
                                </Box>
                                <a
                                  href={source.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{
                                    fontSize: '12px',
                                    color: '#0972d3',
                                    textDecoration: 'none',
                                    wordBreak: 'break-all'
                                  }}
                                >
                                  {source.url}
                                </a>
                              </SpaceBetween>
                            </Box>
                          ))}
                        </SpaceBetween>
                      </Box>
                    )}
                  </SpaceBetween>
                </Box>
              )}
            </SpaceBetween>
          </Container>
        );
      })()}
    </Grid>
  );
}
