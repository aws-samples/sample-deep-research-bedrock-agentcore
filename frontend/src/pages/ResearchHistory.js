import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Header,
  Pagination,
  TextFilter,
  StatusIndicator,
  Box,
  SpaceBetween,
  Button,
  Link
} from '@cloudscape-design/components';
import { api } from '../services/api';
import { formatDate, formatElapsedTime, getStatusBadgeType, formatModelName } from '../utils/formatters';

export default function ResearchHistory({ addNotification }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [filteredSessions, setFilteredSessions] = useState([]);
  const [filterText, setFilterText] = useState('');
  const [currentPageIndex, setCurrentPageIndex] = useState(1);
  const [selectedItems, setSelectedItems] = useState([]);
  const [deleting, setDeleting] = useState(false);
  const pageSize = 20;

  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getResearchHistory(100);
      setSessions(data.sessions || []);
      setFilteredSessions(data.sessions || []);
      setSelectedItems([]);
    } catch (error) {
      addNotification({
        type: 'error',
        content: `Failed to load history: ${error.message}`
      });
    } finally {
      setLoading(false);
    }
  }, [addNotification]);

  const handleDelete = async () => {
    if (selectedItems.length === 0) return;

    try {
      setDeleting(true);

      // Delete all selected items
      await Promise.all(
        selectedItems.map(item => api.deleteResearch(item.session_id))
      );

      addNotification({
        type: 'success',
        content: `Deleted ${selectedItems.length} research session(s)`
      });

      // Reload history
      await loadHistory();
    } catch (error) {
      addNotification({
        type: 'error',
        content: `Failed to delete: ${error.message}`
      });
    } finally {
      setDeleting(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    // Filter sessions
    if (filterText) {
      const filtered = sessions.filter(session =>
        session.topic.toLowerCase().includes(filterText.toLowerCase()) ||
        session.session_id.toLowerCase().includes(filterText.toLowerCase())
      );
      setFilteredSessions(filtered);
    } else {
      setFilteredSessions(sessions);
    }
    setCurrentPageIndex(1);
  }, [filterText, sessions]);

  const paginatedSessions = filteredSessions.slice(
    (currentPageIndex - 1) * pageSize,
    currentPageIndex * pageSize
  );

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
      sortingField: 'topic',
      width: 350
    },
    {
      id: 'status',
      header: 'Status',
      cell: item => (
        <StatusIndicator type={getStatusBadgeType(item.status)}>
          {item.status}
        </StatusIndicator>
      ),
      sortingField: 'status',
      width: 150
    },
    {
      id: 'research_type',
      header: 'Type',
      cell: item => item.research_type || '-',
      sortingField: 'research_type',
      width: 150
    },
    {
      id: 'model',
      header: 'Model',
      cell: item => formatModelName(item.model),
      sortingField: 'model',
      width: 150
    },
    {
      id: 'research_depth',
      header: 'Depth',
      cell: item => item.research_depth || '-',
      sortingField: 'research_depth',
      width: 120
    },
    {
      id: 'created_at',
      header: 'Created',
      cell: item => formatDate(item.created_at),
      sortingField: 'created_at',
      width: 200
    },
    {
      id: 'duration',
      header: 'Duration',
      cell: item => {
        // Only show duration for completed research
        if (item.status === 'completed' && item.elapsed_time !== undefined && item.elapsed_time !== null) {
          return formatElapsedTime(item.elapsed_time);
        }
        // Show '-' for all other statuses (processing, pending, failed)
        return '-';
      },
      width: 120
    }
  ];

  return (
    <Table
      columnDefinitions={columnDefinitions}
      items={paginatedSessions}
      loading={loading}
      loadingText="Loading research history..."
      sortingDisabled={false}
      selectionType="multi"
      selectedItems={selectedItems}
      onSelectionChange={({ detail }) => setSelectedItems(detail.selectedItems)}
      filter={
        <TextFilter
          filteringPlaceholder="Search by topic or session ID"
          filteringText={filterText}
          onChange={({ detail }) => setFilterText(detail.filteringText)}
        />
      }
      header={
        <Header
          counter={`(${filteredSessions.length})`}
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                iconName="remove"
                disabled={selectedItems.length === 0 || deleting}
                loading={deleting}
                onClick={handleDelete}
              >
                Delete {selectedItems.length > 0 ? `(${selectedItems.length})` : ''}
              </Button>
              <Button iconName="refresh" onClick={loadHistory} disabled={deleting}>
                Refresh
              </Button>
              <Button
                variant="primary"
                iconName="add-plus"
                onClick={() => navigate('/research/create')}
              >
                Create Research
              </Button>
            </SpaceBetween>
          }
        >
          Research History
        </Header>
      }
      pagination={
        <Pagination
          currentPageIndex={currentPageIndex}
          pagesCount={Math.ceil(filteredSessions.length / pageSize)}
          onChange={({ detail }) => setCurrentPageIndex(detail.currentPageIndex)}
        />
      }
      empty={
        <Box textAlign="center" color="inherit">
          <b>No research sessions</b>
          <Box padding={{ bottom: 's' }} variant="p" color="inherit">
            {filterText ? 'No matches found' : 'Create your first research to get started'}
          </Box>
          {!filterText && (
            <Button onClick={() => navigate('/research/create')}>
              Create Research
            </Button>
          )}
        </Box>
      }
      trackBy="session_id"
    />
  );
}
