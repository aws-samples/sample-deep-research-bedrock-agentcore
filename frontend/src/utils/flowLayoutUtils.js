/**
 * Utility functions for React Flow layout calculation
 * Map-Reduce style: dimensions → aspects (parallel) → dimension summaries → complete
 */

export function createFlowElements(events, providedDimensions) {
  const nodes = [];
  const edges = [];

  console.log('createFlowElements called with:', {
    eventCount: events?.length,
    dimensionsCount: providedDimensions?.length,
    dimensions: providedDimensions
  });

  if (!events || events.length === 0) {
    console.warn('No events provided to createFlowElements');
    return { nodes, edges };
  }

  // ALWAYS extract dimensions from events (ignore DynamoDB dimensions)
  const aspectEventsForDimensions = events.filter(e => e.type === 'aspect_research_complete');
  let dimensions = [];
  if (aspectEventsForDimensions.length > 0) {
    dimensions = [...new Set(aspectEventsForDimensions.map(e => e.dimension).filter(d => d))];
    console.log('Extracted dimensions from events:', dimensions);
  }

  let xOffset = 50;
  const horizontalSpacing = 450;
  const verticalSpacing = 200;
  const centerY = 400;

  // Helper to add a single node
  const addSingleNode = (id, data, x, y = centerY) => {
    nodes.push({
      id,
      type: 'workflowNode',
      position: { x, y },
      data,
      draggable: false
    });
  };

  let lastNodeId = null;

  // Stage 1: Research Start
  const startEvent = events.find(e => e.type === 'research_start');
  if (startEvent) {
    addSingleNode('start', {
      label: 'Research Start',
      type: 'research_start',
      status: 'completed',
      subtitle: startEvent.data.topic?.substring(0, 40) || '',
      event: startEvent
    }, xOffset);
    lastNodeId = 'start';
    xOffset += horizontalSpacing;
  }

  // Stage 2: References Prepared (optional)
  const refEvent = events.find(e => e.type === 'references_prepared');
  if (refEvent) {
    addSingleNode('ref_prep', {
      label: 'References Prepared',
      type: 'references_prepared',
      status: 'completed',
      subtitle: `${refEvent.data.reference_count || 0} references`,
      event: refEvent
    }, xOffset);
    if (lastNodeId) {
      edges.push({ id: `e-${lastNodeId}-ref`, source: lastNodeId, target: 'ref_prep' });
    }
    lastNodeId = 'ref_prep';
    xOffset += horizontalSpacing;
  }

  // Stage 3: Dimensions Identified
  const dimEvent = events.find(e => e.type === 'dimensions_identified');
  if (dimEvent) {
    addSingleNode('dimensions', {
      label: 'Dimensions Identified',
      type: 'dimensions_identified',
      status: 'completed',
      subtitle: `${dimensions.length} dimensions, ${aspectEventsForDimensions.length} aspects`,
      event: dimEvent
    }, xOffset);
    if (lastNodeId) {
      edges.push({ id: `e-${lastNodeId}-dim`, source: lastNodeId, target: 'dimensions' });
    }
    lastNodeId = 'dimensions';
    xOffset += horizontalSpacing;
  }

  // Stage 4: MAP - Dimension Entry Nodes (parallel)
  const researchEvents = events.filter(e => e.type === 'aspect_research_complete');

  if (researchEvents.length > 0 && dimensions.length > 0) {
    // Group research events by dimension
    const researchByDimension = {};
    dimensions.forEach(dim => {
      researchByDimension[dim] = researchEvents.filter(e => e.dimension === dim);
    });

    const totalHeight = (dimensions.length - 1) * verticalSpacing;
    const startY = centerY - totalHeight / 2;

    const dimensionStartX = xOffset;
    const dimensionNodeIds = [];

    // Create dimension entry nodes (MAP stage start)
    dimensions.forEach((dimension, dimIdx) => {
      const y = startY + dimIdx * verticalSpacing;
      const dimNodeId = `dim_start_${dimIdx}`;

      // Create a synthetic event with dimension-specific data
      const dimAspects = researchByDimension[dimension] || [];

      // We need to get aspect details from dimensions_identified event
      // Extract aspect names for basic display
      const aspectNames = dimAspects.map(e => e.aspect || e.data?.aspect || 'Unknown Aspect');

      addSingleNode(dimNodeId, {
        label: 'Dimension',
        subtitle: dimension.length > 35 ? dimension.substring(0, 32) + '...' : dimension,
        type: 'dimension_start',
        status: 'completed',
        metadata: `${dimAspects.length} aspects`,
        event: {
          type: 'dimension_start',
          dimension: dimension,
          data: {
            dimension: dimension,
            aspects: aspectNames,  // Aspect names for simple display
            aspect_count: dimAspects.length,
            event_type: 'dimension_start',
            // Add reference to dimensions_identified event for detailed aspect info
            dimensions_identified_event: dimEvent
          }
        }
      }, dimensionStartX, y);

      dimensionNodeIds.push(dimNodeId);

      // Connect from dimensions_identified to each dimension start
      if (lastNodeId) {
        edges.push({ id: `e-${lastNodeId}-${dimNodeId}`, source: lastNodeId, target: dimNodeId });
      }
    });

    xOffset += horizontalSpacing;

    // Stage 5: Aspect Research Nodes (MAP - parallel processing)
    // Display aspects vertically separated (like dimensions)
    const aspectStartX = xOffset;
    const aspectVerticalSpacing = 150;  // Tighter spacing for aspects
    const dimensionEndNodeIds = [];

    // Calculate total aspects to determine vertical layout
    let totalAspects = 0;
    dimensions.forEach(dim => {
      totalAspects += researchByDimension[dim].length;
    });

    const aspectsStartY = centerY - ((totalAspects - 1) * aspectVerticalSpacing) / 2;

    let currentAspectY = aspectsStartY;

    dimensions.forEach((dimension, dimIdx) => {
      const dimResearchEvents = researchByDimension[dimension] || [];
      const dimStartNodeId = `dim_start_${dimIdx}`;

      dimResearchEvents.forEach((event, aspectIdx) => {
        const nodeId = `research_${dimIdx}_${aspectIdx}`;

        // Place each aspect vertically
        addSingleNode(nodeId, {
          label: event.aspect || `Aspect ${aspectIdx + 1}`,
          subtitle: event.dimension || '',
          type: 'aspect_research_complete',
          status: 'completed',
          event
        }, aspectStartX, currentAspectY);

        // Connect from dimension start to EVERY aspect (parallel processing)
        edges.push({ id: `e-${dimStartNodeId}-${nodeId}`, source: dimStartNodeId, target: nodeId });

        // Save all aspect nodes for this dimension (for connecting to summary)
        dimensionEndNodeIds.push({ nodeId, dimIdx, y: currentAspectY });

        currentAspectY += aspectVerticalSpacing;
      });
    });

    // Move summary nodes to the right to show clear Reduce phase
    xOffset = aspectStartX + horizontalSpacing * 1.3;

    // Stage 6: REDUCE - Dimension Summary Nodes
    // Place summaries at the Y coordinate of each dimension's last aspect
    const dimDocEvents = events.filter(e => e.type === 'dimension_document_complete');
    const hasDimDocs = dimDocEvents.length > 0;
    const dimensionSummaryNodeIds = [];

    // Group dimension end nodes by dimension index for easy lookup
    const endNodesByDimension = {};
    dimensionEndNodeIds.forEach(node => {
      if (!endNodesByDimension[node.dimIdx]) {
        endNodesByDimension[node.dimIdx] = [];
      }
      endNodesByDimension[node.dimIdx].push(node);
    });

    // Calculate middle Y position for each dimension's aspects
    const dimensionMiddleY = {};
    dimensions.forEach((dimension, dimIdx) => {
      const dimAspects = endNodesByDimension[dimIdx] || [];
      if (dimAspects.length > 0) {
        // Find first and last aspect Y positions for this dimension
        let firstY = Infinity;
        let lastY = -Infinity;

        const dimResearchEvents = researchByDimension[dimension] || [];
        let tempY = aspectsStartY;
        for (let i = 0; i < dimIdx; i++) {
          const prevDimEvents = researchByDimension[dimensions[i]] || [];
          tempY += prevDimEvents.length * aspectVerticalSpacing;
        }

        firstY = tempY;
        lastY = tempY + (dimResearchEvents.length - 1) * aspectVerticalSpacing;

        dimensionMiddleY[dimIdx] = (firstY + lastY) / 2;
      } else {
        dimensionMiddleY[dimIdx] = centerY;
      }
    });

    if (hasDimDocs) {
      // Use actual dimension_document_complete events
      dimensions.forEach((dimension, dimIdx) => {
        const dimDocEvent = dimDocEvents.find(e => e.dimension === dimension);
        if (dimDocEvent) {
          const dimSummaryId = `dim_summary_${dimIdx}`;
          const y = dimensionMiddleY[dimIdx];

          addSingleNode(dimSummaryId, {
            label: 'Dimension Summary',
            subtitle: dimension.length > 35 ? dimension.substring(0, 32) + '...' : dimension,
            type: 'dimension_document_complete',
            status: 'completed',
            metadata: `${dimDocEvent.data.word_count || 0} words`,
            event: dimDocEvent
          }, xOffset, y);

          dimensionSummaryNodeIds.push(dimSummaryId);

          // Connect from ALL aspects of this dimension to summary (reduce phase)
          const dimensionAspects = dimensionEndNodeIds.filter(n => n.dimIdx === dimIdx);
          dimensionAspects.forEach(aspectNode => {
            edges.push({ id: `e-${aspectNode.nodeId}-${dimSummaryId}`, source: aspectNode.nodeId, target: dimSummaryId });
          });
        }
      });

      xOffset += horizontalSpacing;
    } else {
      // Create virtual dimension summary nodes even without events
      dimensions.forEach((dimension, dimIdx) => {
        const dimSummaryId = `dim_summary_${dimIdx}`;
        const y = dimensionMiddleY[dimIdx];

        // Collect aspect information for this dimension
        const dimAspects = researchByDimension[dimension] || [];
        const aspectList = dimAspects.map(e => ({
          name: e.aspect || e.data?.aspect || 'Unknown',
          dimension: dimension
        }));

        addSingleNode(dimSummaryId, {
          label: 'Dimension Summary',
          subtitle: dimension.length > 35 ? dimension.substring(0, 32) + '...' : dimension,
          type: 'dimension_summary',
          status: 'completed',
          metadata: `${dimAspects.length} aspects`,
          event: {
            type: 'dimension_summary',
            dimension: dimension,
            data: {
              dimension: dimension,
              aspect_count: dimAspects.length,
              aspects: aspectList,
              event_type: 'dimension_summary'
            }
          }
        }, xOffset, y);

        dimensionSummaryNodeIds.push(dimSummaryId);

        // Connect from ALL aspects of this dimension to summary (reduce phase)
        const dimensionAspects = dimensionEndNodeIds.filter(n => n.dimIdx === dimIdx);
        dimensionAspects.forEach(aspectNode => {
          edges.push({ id: `e-${aspectNode.nodeId}-${dimSummaryId}`, source: aspectNode.nodeId, target: dimSummaryId });
        });
      });

      xOffset += horizontalSpacing;
    }

    // Stage 7: Research Complete (REDUCE final)
    const completeEvent = events.find(e => e.type === 'research_complete');
    if (completeEvent) {
      addSingleNode('complete', {
        label: 'Research Complete',
        type: 'research_complete',
        status: 'completed',
        subtitle: `${researchEvents.length} aspects completed`,
        event: completeEvent
      }, xOffset, centerY);

      // Connect all dimension summaries to complete
      dimensionSummaryNodeIds.forEach(dimSummaryId => {
        edges.push({ id: `e-${dimSummaryId}-complete`, source: dimSummaryId, target: 'complete' });
      });
    }
  }

  console.log('Created flow elements:', { nodeCount: nodes.length, edgeCount: edges.length });

  return { nodes, edges };
}
