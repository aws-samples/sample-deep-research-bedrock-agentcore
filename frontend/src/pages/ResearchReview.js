import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Header,
  Table,
  Box,
  SpaceBetween,
  Button,
  Badge,
  Link,
  Flashbar
} from '@cloudscape-design/components';
import { api } from '../services/api';

export default function ResearchReview() {
  const navigate = useNavigate();
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [flashMessages, setFlashMessages] = useState([]);

  useEffect(() => {
    loadReviews();
  }, []);

  const loadReviews = async () => {
    try {
      setLoading(true);
      const data = await api.getReviews();
      setReviews(data.reviews || []);
    } catch (error) {
      console.error('Failed to load reviews:', error);
      setFlashMessages([{
        type: 'error',
        content: `Failed to load reviews: ${error.message}`,
        dismissible: true,
        dismissLabel: 'Dismiss message',
        onDismiss: () => setFlashMessages([]),
        id: 'error-message'
      }]);
    } finally {
      setLoading(false);
    }
  };

  const columnDefinitions = [
    {
      id: 'created',
      header: 'Created',
      cell: item => new Date(item.created_at).toLocaleString(),
      sortingField: 'created_at'
    },
    {
      id: 'topic',
      header: 'Research Topic',
      cell: item => (
        <Link
          onFollow={(e) => {
            e.preventDefault();
            navigate(`/research/${item.session_id}/review`);
          }}
        >
          {item.topic}
        </Link>
      )
    },
    {
      id: 'version',
      header: 'Version',
      cell: item => (
        <Badge color="blue">
          {item.review_version || 'draft'}
        </Badge>
      )
    },
    {
      id: 'comments',
      header: 'Comments',
      cell: item => {
        const totalComments = (item.pending_comments_count || 0) + (item.resolved_comments_count || 0);
        return (
          <Badge color={totalComments > 0 ? 'blue' : 'grey'}>
            {totalComments}
          </Badge>
        );
      }
    },
    {
      id: 'research_type',
      header: 'Research Type',
      cell: item => item.research_type || '-'
    }
  ];

  return (
    <SpaceBetween size="l">
      <Flashbar items={flashMessages} />
      <Container
        header={
          <Header
            variant="h1"
            description="Review and evaluate research quality"
            actions={
              <Button onClick={loadReviews} iconName="refresh">
                Refresh
              </Button>
            }
          >
            Research Reviews
          </Header>
        }
      >
        <Table
          columnDefinitions={columnDefinitions}
          items={reviews}
          loading={loading}
          loadingText="Loading reviews..."
          sortingDisabled={false}
          empty={
            <Box textAlign="center" color="inherit">
              <Box variant="p" color="inherit">
                No research reviews available
              </Box>
              <Box variant="small" color="text-body-secondary">
                Complete a research session to start reviewing
              </Box>
            </Box>
          }
        />
      </Container>
    </SpaceBetween>
  );
}
