import React from 'react';
import { Handle, Position } from 'reactflow';
import {
  Box,
  StatusIndicator,
  SpaceBetween
} from '@cloudscape-design/components';

// Custom node component for workflow visualization
export function WorkflowNode({ data, isConnectable }) {
  const getNodeStyle = () => {
    const baseStyle = {
      padding: '18px 22px',
      borderRadius: '12px',
      border: '2px solid',
      background: '#ffffff',
      minWidth: '300px',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      fontSize: '15px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
    };

    // Different styles based on node type
    switch (data.type) {
      // Workflow milestones (green)
      case 'research_start':
      case 'references_prepared':
      case 'dimensions_identified':
      case 'research_complete':
        return {
          ...baseStyle,
          borderColor: '#059669',
          background: 'linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%)',
          boxShadow: '0 4px 12px rgba(5, 150, 105, 0.15), 0 2px 4px rgba(0, 0, 0, 0.05)'
        };
      // Dimension nodes (blue)
      case 'dimension_start':
        return {
          ...baseStyle,
          borderColor: '#2563eb',
          background: 'linear-gradient(135deg, #ffffff 0%, #eff6ff 100%)',
          boxShadow: '0 4px 12px rgba(37, 99, 235, 0.15), 0 2px 4px rgba(0, 0, 0, 0.05)'
        };
      // Aspect research nodes (purple)
      case 'aspect_research_complete':
        return {
          ...baseStyle,
          borderColor: '#9333ea',
          background: 'linear-gradient(135deg, #ffffff 0%, #faf5ff 100%)',
          minWidth: '350px',
          boxShadow: '0 4px 12px rgba(147, 51, 234, 0.15), 0 2px 4px rgba(0, 0, 0, 0.05)'
        };
      // Dimension summary nodes (orange)
      case 'dimension_document_complete':
      case 'dimension_summary':
        return {
          ...baseStyle,
          borderColor: '#ea580c',
          background: 'linear-gradient(135deg, #ffffff 0%, #fff7ed 100%)',
          boxShadow: '0 4px 12px rgba(234, 88, 12, 0.15), 0 2px 4px rgba(0, 0, 0, 0.05)'
        };
      default:
        return baseStyle;
    }
  };

  const getStatusType = () => {
    if (data.status === 'completed') return 'success';
    if (data.status === 'error') return 'error';
    if (data.status === 'in_progress') return 'in-progress';
    return 'pending';
  };

  return (
    <div style={getNodeStyle()}>
      <Handle
        type="target"
        position={Position.Left}
        isConnectable={isConnectable}
        style={{
          background: '#6b7280',
          width: '10px',
          height: '10px',
          border: '2px solid #fff',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}
      />

      <SpaceBetween size="s">
        <Box>
          <StatusIndicator type={getStatusType()}>
            <Box fontSize="heading-s" fontWeight="bold" color="text-heading-default">
              {data.label}
            </Box>
          </StatusIndicator>
        </Box>

        {data.subtitle && (
          <Box
            fontSize="body-m"
            color="text-body-secondary"
            padding={{ top: 'xxs' }}
            style={{
              lineHeight: '1.5',
              whiteSpace: 'normal',
              wordBreak: 'break-word'
            }}
          >
            {data.subtitle}
          </Box>
        )}

        {data.metadata && (
          <Box
            fontSize="body-s"
            color="text-status-info"
            fontWeight="bold"
            padding={{ top: 'xxs' }}
          >
            {data.metadata}
          </Box>
        )}
      </SpaceBetween>

      <Handle
        type="source"
        position={Position.Right}
        isConnectable={isConnectable}
        style={{
          background: '#6b7280',
          width: '10px',
          height: '10px',
          border: '2px solid #fff',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}
      />
    </div>
  );
}

// Custom edge styles
export const customEdgeStyle = {
  stroke: '#5f6b7a',
  strokeWidth: 2,
};

export const customEdgeAnimatedStyle = {
  stroke: '#0972d3',
  strokeWidth: 2,
};
