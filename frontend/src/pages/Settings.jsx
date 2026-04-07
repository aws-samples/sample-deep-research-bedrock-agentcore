import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  Select,
  Alert,
  Button
} from '@cloudscape-design/components';
import { api } from '../services/api';
import { getModelOptions } from '../config/modelRegistry';

export default function Settings({ addNotification }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Preferences state
  const [defaultChatModel, setDefaultChatModel] = useState({ label: 'Claude Haiku 4.5', value: 'claude_haiku45' });
  const [defaultResearchModel, setDefaultResearchModel] = useState({ label: 'Claude Sonnet 4.5', value: 'claude_sonnet45' });
  const [defaultResearchType, setDefaultResearchType] = useState({ label: 'General', value: 'general' });
  const [defaultResearchDepth, setDefaultResearchDepth] = useState({ label: 'Standard', value: 'standard' });

  // Model options (get from centralized registry - supports both Chat and Research)
  const modelOptions = getModelOptions('chat');

  const researchTypeOptions = [
    { label: 'General', value: 'general' },
    { label: 'Academic', value: 'academic' },
    { label: 'Technical', value: 'technical' },
    { label: 'Business', value: 'business' },
  ];

  const researchDepthOptions = [
    { label: 'Quick', value: 'quick' },
    { label: 'Standard', value: 'standard' },
    { label: 'Deep', value: 'deep' },
  ];

  // Load preferences on mount
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        setLoading(true);
        const prefs = await api.getUserPreferences();

        if (prefs.default_chat_model) {
          const modelOption = modelOptions.find(opt => opt.value === prefs.default_chat_model);
          if (modelOption) setDefaultChatModel(modelOption);
        }

        if (prefs.default_research_model) {
          const modelOption = modelOptions.find(opt => opt.value === prefs.default_research_model);
          if (modelOption) setDefaultResearchModel(modelOption);
        }

        if (prefs.default_research_type) {
          const typeOption = researchTypeOptions.find(opt => opt.value === prefs.default_research_type);
          if (typeOption) setDefaultResearchType(typeOption);
        }

        if (prefs.default_research_depth) {
          const depthOption = researchDepthOptions.find(opt => opt.value === prefs.default_research_depth);
          if (depthOption) setDefaultResearchDepth(depthOption);
        }
      } catch (error) {
        console.error('Failed to load preferences:', error);
        if (addNotification) {
          addNotification({
            type: 'error',
            content: `Failed to load preferences: ${error.message}`
          });
        }
      } finally {
        setLoading(false);
      }
    };

    loadPreferences();
  }, [addNotification]); // eslint-disable-line react-hooks/exhaustive-deps

  // Save preferences
  const handleSave = async () => {
    try {
      setSaving(true);
      await api.saveUserPreferences({
        default_chat_model: defaultChatModel.value,
        default_research_model: defaultResearchModel.value,
        default_research_type: defaultResearchType.value,
        default_research_depth: defaultResearchDepth.value,
      });

      if (addNotification) {
        addNotification({
          type: 'success',
          content: 'Preferences saved successfully'
        });
      }
    } catch (error) {
      console.error('Failed to save preferences:', error);
      if (addNotification) {
        addNotification({
          type: 'error',
          content: `Failed to save preferences: ${error.message}`
        });
      }
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    {
      id: 'general',
      label: 'Preferences',
      content: (
        <Container
          header={
            <Header
              variant="h2"
              actions={
                <Button
                  variant="primary"
                  onClick={handleSave}
                  loading={saving}
                  disabled={loading}
                >
                  Save Preferences
                </Button>
              }
            >
              Default Preferences
            </Header>
          }
        >
          <SpaceBetween size="l">
            <Alert type="info">
              These preferences will be used as default values when starting new chat sessions and research tasks.
            </Alert>

            <FormField
              label="Default Chat Model"
              description="The AI model to use for chat conversations"
            >
              <Select
                selectedOption={defaultChatModel}
                onChange={({ detail }) => setDefaultChatModel(detail.selectedOption)}
                options={modelOptions}
                disabled={loading}
              />
            </FormField>

            <FormField
              label="Default Research Model"
              description="The AI model to use for research tasks"
            >
              <Select
                selectedOption={defaultResearchModel}
                onChange={({ detail }) => setDefaultResearchModel(detail.selectedOption)}
                options={modelOptions}
                disabled={loading}
              />
            </FormField>

            <FormField
              label="Default Research Type"
              description="Default research type for new research sessions"
            >
              <Select
                selectedOption={defaultResearchType}
                onChange={({ detail }) => setDefaultResearchType(detail.selectedOption)}
                options={researchTypeOptions}
                disabled={loading}
              />
            </FormField>

            <FormField
              label="Default Research Depth"
              description="Default depth setting for new research sessions"
            >
              <Select
                selectedOption={defaultResearchDepth}
                onChange={({ detail }) => setDefaultResearchDepth(detail.selectedOption)}
                options={researchDepthOptions}
                disabled={loading}
              />
            </FormField>
          </SpaceBetween>
        </Container>
      )
    }
  ];

  return (
    <SpaceBetween size="l">
      <Header
        variant="h1"
        description="Configure default preferences for chat and research sessions"
      >
        Settings
      </Header>

      {tabs[0].content}
    </SpaceBetween>
  );
}
