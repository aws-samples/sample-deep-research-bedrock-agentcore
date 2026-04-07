import React from 'react';
import {
  SpaceBetween,
  ExpandableSection,
  Table,
  Box,
  ProgressBar,
  StatusIndicator
} from '@cloudscape-design/components';

export default function ResearchProgressTracker({ aspectsByDimension, researchByAspect = {} }) {
  if (!aspectsByDimension) {
    return (
      <Box textAlign="center" color="text-body-secondary">
        No research data available yet
      </Box>
    );
  }

  return (
    <SpaceBetween size="l">
      {Object.entries(aspectsByDimension).map(([dimension, aspects]) => {
        const dimensionCompleted = aspects.filter(aspect => {
          const aspectKey = `${dimension}::${aspect.name}`;
          return researchByAspect[aspectKey];
        }).length;

        const dimensionProgress = aspects.length > 0
          ? Math.round((dimensionCompleted / aspects.length) * 100)
          : 0;

        const columnDefinitions = [
          {
            id: 'aspect',
            header: 'Aspect',
            cell: item => item.name,
            width: 300
          },
          {
            id: 'status',
            header: 'Status',
            cell: item => {
              const aspectKey = `${dimension}::${item.name}`;
              const research = researchByAspect[aspectKey];
              const isFailed = research?.failed === true;
              const isCompleted = !isFailed && (item.completed || (research && research.completed !== false));

              if (isFailed) {
                return (
                  <StatusIndicator type="error">
                    Failed
                  </StatusIndicator>
                );
              }

              return (
                <StatusIndicator
                  type={isCompleted ? 'success' : 'in-progress'}
                >
                  {isCompleted ? 'Completed' : 'In Progress'}
                </StatusIndicator>
              );
            },
            width: 150
          },
          {
            id: 'error',
            header: 'Error',
            cell: item => {
              const aspectKey = `${dimension}::${item.name}`;
              const research = researchByAspect[aspectKey];
              if (research?.error) {
                return (
                  <Box color="text-status-error" fontSize="body-s">
                    {research.error}
                  </Box>
                );
              }
              return '-';
            },
            width: 250
          },
          {
            id: 'wordCount',
            header: 'Word Count',
            cell: item => {
              const aspectKey = `${dimension}::${item.name}`;
              const research = researchByAspect[aspectKey];
              return research?.word_count || '-';
            },
            width: 120
          },
          {
            id: 'sources',
            header: 'Sources',
            cell: item => {
              const aspectKey = `${dimension}::${item.name}`;
              const research = researchByAspect[aspectKey];
              return research?.sources_count || '-';
            },
            width: 100
          }
        ];

        return (
          <ExpandableSection
            key={dimension}
            headerText={dimension}
            headerDescription={`${dimensionCompleted}/${aspects.length} aspects completed`}
            variant="container"
          >
            <SpaceBetween size="m">
              <ProgressBar
                value={dimensionProgress}
                variant="standalone"
              />
              <Table
                columnDefinitions={columnDefinitions}
                items={aspects}
                variant="embedded"
              />
            </SpaceBetween>
          </ExpandableSection>
        );
      })}
    </SpaceBetween>
  );
}
