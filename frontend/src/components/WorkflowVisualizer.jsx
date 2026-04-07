import React from 'react';
import {
  Box,
  SpaceBetween,
  StatusIndicator,
  Grid
} from '@cloudscape-design/components';
import { WORKFLOW_STAGES, getStageIndex } from '../utils/workflowStages';

export default function WorkflowVisualizer({ currentStage }) {
  const currentIndex = getStageIndex(currentStage);

  // Filter out optional and hidden stages
  const visibleStages = WORKFLOW_STAGES.filter(stage => !stage.optional && !stage.hidden);

  return (
    <Grid gridDefinition={visibleStages.map(() => ({ colspan: { default: 12, xs: 3 } }))}>
      {visibleStages.map((stage) => {
        const isCompleted = currentIndex > stage.order;
        const isActive = currentIndex === stage.order;

        return (
          <Box key={stage.id} padding="s">
            <SpaceBetween size="xs">
              <StatusIndicator
                type={
                  isCompleted ? 'success' :
                  isActive ? 'in-progress' :
                  'pending'
                }
              >
                <strong>{stage.name}</strong>
              </StatusIndicator>
              <Box variant="small" color="text-body-secondary">
                {stage.description}
              </Box>
            </SpaceBetween>
          </Box>
        );
      })}
    </Grid>
  );
}
