import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Header,
  SpaceBetween,
  Button,
  Box,
  ColumnLayout,
  StatusIndicator,
  Table,
  Link
} from '@cloudscape-design/components';
import { api } from '../services/api';
import { formatDate, formatElapsedTime, getStatusBadgeType } from '../utils/formatters';

export default function ResearchDashboard({ addNotification }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [recentSessions, setRecentSessions] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    processing: 0,
    completed: 0,
    failed: 0
  });

  const loadDashboard = async () => {
    try {
      setLoading(true);
      const data = await api.getResearchHistory(10);
      setRecentSessions(data.sessions || []);

      // Calculate stats
      const statsData = {
        total: data.sessions?.length || 0,
        processing: data.sessions?.filter(s => s.status === 'processing').length || 0,
        completed: data.sessions?.filter(s => s.status === 'completed').length || 0,
        failed: data.sessions?.filter(s => s.status === 'failed').length || 0
      };
      setStats(statsData);
    } catch (error) {
      addNotification({
        type: 'error',
        content: `Failed to load dashboard: ${error.message}`
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const columnDefinitions = [
    {
      id: 'topic',
      header: 'Topic',
      cell: item => (
        <Link
          onFollow={(e) => {
            e.preventDefault();
            navigate(`/research/${item.session_id}`);
          }}
          href={`#/research/${item.session_id}`}
        >
          {item.topic}
        </Link>
      ),
      width: 300
    },
    {
      id: 'status',
      header: 'Status',
      cell: item => (
        <StatusIndicator type={getStatusBadgeType(item.status)}>
          {item.status}
        </StatusIndicator>
      ),
      width: 150
    },
    {
      id: 'research_type',
      header: 'Type',
      cell: item => item.research_type || '-',
      width: 150
    },
    {
      id: 'created_at',
      header: 'Created',
      cell: item => formatDate(item.created_at),
      width: 200
    },
    {
      id: 'elapsed',
      header: 'Duration',
      cell: item => {
        if (item.status === 'completed' && item.completed_at) {
          const duration = new Date(item.completed_at) - new Date(item.created_at);
          return formatElapsedTime(duration / 1000);
        }
        return '-';
      },
      width: 120
    }
  ];

  return (
    <SpaceBetween size="l">
      <Container
        header={
          <Header
            variant="h1"
            description="AI-powered deep research workflow"
            actions={
              <Button
                variant="primary"
                iconName="add-plus"
                onClick={() => navigate('/research/create')}
              >
                New Research
              </Button>
            }
          >
            Research Dashboard
          </Header>
        }
      >
        <ColumnLayout columns={4} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">Total Research</Box>
            <Box fontSize="display-l" fontWeight="bold">{stats.total}</Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Processing</Box>
            <Box fontSize="display-l">
              <StatusIndicator type="in-progress">
                {stats.processing}
              </StatusIndicator>
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Completed</Box>
            <Box fontSize="display-l">
              <StatusIndicator type="success">
                {stats.completed}
              </StatusIndicator>
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Failed</Box>
            <Box fontSize="display-l">
              <StatusIndicator type="error">
                {stats.failed}
              </StatusIndicator>
            </Box>
          </div>
        </ColumnLayout>
      </Container>

      <Table
        columnDefinitions={columnDefinitions}
        items={recentSessions}
        loading={loading}
        loadingText="Loading recent research..."
        empty={
          <Box textAlign="center" color="inherit">
            <b>No research sessions</b>
            <Box padding={{ bottom: 's' }} variant="p" color="inherit">
              Create your first research to get started.
            </Box>
            <Button onClick={() => navigate('/research/create')}>
              New Research
            </Button>
          </Box>
        }
        header={
          <Header
            actions={
              <Button onClick={() => navigate('/research/history')}>
                View all
              </Button>
            }
          >
            Recent Research
          </Header>
        }
      />
    </SpaceBetween>
  );
}
