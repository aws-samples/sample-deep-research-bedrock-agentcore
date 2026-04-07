import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  Textarea,
  Select,
  Wizard,
  Box,
  ExpandableSection,
  Grid,
  Input,
  Button,
  ColumnLayout,
  Icon,
  Cards,
  Alert
} from '@cloudscape-design/components';
import { api } from '../services/api';
import { RESEARCH_TYPES, WEB_RESEARCH_SUBTYPES, RESEARCH_DEPTHS, LLM_MODELS } from '../utils/workflowStages';

export default function CreateResearch({ addNotification }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [, setLoadingPreferences] = useState(true);

  // Form state
  const [topic, setTopic] = useState('');
  const [selectedResearchType, setSelectedResearchType] = useState([RESEARCH_TYPES[0]]); // Cards uses array
  const [selectedWebSubType, setSelectedWebSubType] = useState([WEB_RESEARCH_SUBTYPES[0]]); // Cards uses array
  const [researchDepth, setResearchDepth] = useState({ value: 'balanced', label: 'Balanced' });
  const [llmModel, setLlmModel] = useState({ value: 'claude_haiku45', label: 'Claude Haiku 4.5' });
  const [researchContext, setResearchContext] = useState('');
  const [referenceMaterials, setReferenceMaterials] = useState([]);

  // Load user preferences on mount
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        setLoadingPreferences(true);
        const prefs = await api.getUserPreferences();

        // Set research model
        if (prefs.default_research_model) {
          const modelOption = LLM_MODELS.find(m => m.value === prefs.default_research_model);
          if (modelOption) {
            setLlmModel(modelOption);
          }
        }

        // Set research depth
        if (prefs.default_research_depth) {
          const depthOption = RESEARCH_DEPTHS.find(d => d.value === prefs.default_research_depth);
          if (depthOption) {
            setResearchDepth(depthOption);
          }
        }

        // Set research type
        if (prefs.default_research_type) {
          const typeOption = RESEARCH_TYPES.find(t => t.value === prefs.default_research_type);
          if (typeOption) {
            setSelectedResearchType([typeOption]);
          }
        }
      } catch (error) {
        console.error('Failed to load user preferences:', error);
        // Continue with default values if loading fails
      } finally {
        setLoadingPreferences(false);
      }
    };

    loadPreferences();
  }, []);

  const handleSubmit = async () => {
    try {
      setLoading(true);

      // Filter out empty reference materials
      const validReferences = referenceMaterials.filter(ref =>
        ref.type && ((ref.type === 'url' && ref.url) || (ref.type === 'pdf' && ref.pdf_file)) && ref.note
      ).map((ref, index) => ({
        type: ref.type,
        ...(ref.url && { url: ref.url }),
        ...(ref.pdf_file && { pdf_index: index }), // Mark PDF index for backend matching
        note: ref.note,
        title: ref.title || ref.pdf_file?.name
      }));

      // Create FormData for multipart/form-data
      const formData = new FormData();
      formData.append('topic', topic);
      // Use webSubType if web is selected, otherwise use researchType
      const researchTypeValue = selectedResearchType[0]?.value || 'web';
      const finalResearchType = researchTypeValue === 'web'
        ? (selectedWebSubType[0]?.value || 'basic_web')
        : researchTypeValue;
      formData.append('research_type', finalResearchType);
      formData.append('research_depth', researchDepth.value);
      formData.append('llm_model', llmModel.value);

      if (researchContext) {
        formData.append('research_context', researchContext);
      }

      if (validReferences.length > 0) {
        formData.append('reference_materials_json', JSON.stringify(validReferences));

        // Append PDF files with matching indices
        referenceMaterials.forEach((ref, index) => {
          if (ref.type === 'pdf' && ref.pdf_file) {
            formData.append(`pdf_${index}`, ref.pdf_file);
          }
        });
      }

      const response = await api.createResearch(formData);

      addNotification({
        type: 'success',
        content: 'Research started successfully!'
      });

      navigate(`/research/${response.session_id}`);
    } catch (error) {
      addNotification({
        type: 'error',
        content: `Failed to start research: ${error.message}`
      });
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    {
      title: 'Research Setup',
      description: 'Define topic and configuration',
      content: (
        <SpaceBetween size="l">
          <Container header={<Header variant="h2">Research Topic</Header>}>
            <FormField
              label="Topic"
              description="Describe the topic you want to research"
              constraintText="Be specific and clear about your research focus"
            >
              <Textarea
                value={topic}
                onChange={({ detail }) => setTopic(detail.value)}
                placeholder="e.g., Cloud cost optimization strategies for enterprise workloads"
                rows={4}
              />
            </FormField>
          </Container>

          <Container header={<Header variant="h2">Research Configuration</Header>}>
            <SpaceBetween size="l">
              {/* Research Type Cards */}
              <FormField
                label="Research Type"
                description="Select the type of research to conduct"
              >
                <Cards
                  cardDefinition={{
                    header: item => (
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                        <div style={{
                          backgroundColor: '#f2f3f3',
                          borderRadius: '3px',
                          padding: '4px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '24px',
                          height: '24px',
                          flexShrink: 0
                        }}>
                          <Icon name={item.icon} size="small" variant="normal" />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{
                            fontSize: '14px',
                            fontWeight: '700',
                            lineHeight: '20px',
                            color: '#000716',
                            marginBottom: '2px'
                          }}>
                            {item.label}
                          </div>
                          <div style={{
                            fontSize: '12px',
                            fontWeight: '400',
                            lineHeight: '18px',
                            color: '#5f6b7a'
                          }}>
                            {item.description}
                          </div>
                        </div>
                      </div>
                    ),
                    sections: []
                  }}
                  cardsPerRow={[
                    { cards: 1 },
                    { minWidth: 500, cards: 2 },
                    { minWidth: 900, cards: 3 }
                  ]}
                  items={RESEARCH_TYPES}
                  selectedItems={selectedResearchType}
                  onSelectionChange={({ detail }) =>
                    setSelectedResearchType(detail.selectedItems)
                  }
                  isItemDisabled={item => item.disabled === true}
                  selectionType="single"
                  trackBy="value"
                />
              </FormField>

              {/* Web Sub-types (show only when web is selected) */}
              {selectedResearchType[0]?.value === 'web' && (
                <FormField
                  label="Web Research Level"
                  description="Choose between basic or advanced web research"
                >
                  <Cards
                    cardDefinition={{
                      header: item => (
                        <div>
                          <div style={{
                            fontSize: '14px',
                            fontWeight: '700',
                            lineHeight: '20px',
                            color: '#000716',
                            marginBottom: '2px'
                          }}>
                            {item.label}
                          </div>
                          <div style={{
                            fontSize: '12px',
                            fontWeight: '400',
                            lineHeight: '18px',
                            color: '#5f6b7a'
                          }}>
                            {item.description}
                          </div>
                        </div>
                      ),
                      sections: []
                    }}
                    cardsPerRow={[
                      { cards: 1 },
                      { minWidth: 500, cards: 2 }
                    ]}
                    items={WEB_RESEARCH_SUBTYPES}
                    selectedItems={selectedWebSubType}
                    onSelectionChange={({ detail }) =>
                      setSelectedWebSubType(detail.selectedItems)
                    }
                    selectionType="single"
                    trackBy="value"
                  />
                </FormField>
              )}

              <FormField
                label="Research Depth"
                description="Choose how deep the research should go"
              >
                <Select
                  selectedOption={researchDepth}
                  onChange={({ detail }) => setResearchDepth(detail.selectedOption)}
                  options={RESEARCH_DEPTHS.map(depth => ({
                    value: depth.value,
                    label: depth.label,
                    description: depth.description
                  }))}
                />
              </FormField>

              <FormField
                label="LLM Model"
                description="Select the language model for research analysis"
              >
                <Select
                  selectedOption={llmModel}
                  onChange={({ detail }) => setLlmModel(detail.selectedOption)}
                  options={LLM_MODELS.map(model => ({
                    value: model.value,
                    label: model.label,
                    description: model.description
                  }))}
                />
              </FormField>
            </SpaceBetween>
          </Container>
        </SpaceBetween>
      ),
      isOptional: false
    },
    {
      title: 'Additional Options',
      description: 'Context and reference materials (optional)',
      content: (
        <SpaceBetween size="l">
          <Container header={<Header variant="h2">Research Context (Optional)</Header>}>
            <FormField
              label="Context"
              description="Provide background information, constraints, or specific focus areas"
            >
              <Textarea
                value={researchContext}
                onChange={({ detail }) => setResearchContext(detail.value)}
                placeholder="e.g., I'm evaluating cloud cost optimization strategies for our enterprise. Focus on FinOps best practices, multi-cloud considerations, and ROI analysis."
                rows={6}
              />
            </FormField>
          </Container>

          <Container header={<Header variant="h2">Reference Materials (Optional)</Header>}>
            <SpaceBetween size="l">
              {referenceMaterials.length === 0 ? (
                <Box textAlign="center" color="text-body-secondary" padding="l">
                  No reference materials added. Click "Add reference" to get started.
                </Box>
              ) : (
                <SpaceBetween size="m">
                  {referenceMaterials.map((ref, index) => (
                    <Container
                      key={index}
                      header={
                        <Header
                          variant="h3"
                          actions={
                            <Button
                              iconName="close"
                              variant="icon"
                              onClick={() => {
                                const tmp = [...referenceMaterials];
                                tmp.splice(index, 1);
                                setReferenceMaterials(tmp);
                              }}
                            />
                          }
                        >
                          Reference {index + 1}
                        </Header>
                      }
                    >
                      <SpaceBetween size="m">
                        <FormField label="Type">
                          <Select
                            selectedOption={{
                              value: ref.type || 'url',
                              label: ref.type === 'pdf' ? 'PDF Document' : 'URL'
                            }}
                            onChange={({ detail }) => {
                              const tmp = [...referenceMaterials];
                              tmp[index].type = detail.selectedOption.value;
                              // Clear previous inputs
                              tmp[index].url = '';
                              tmp[index].pdf_file = null;
                              tmp[index].title = '';
                              setReferenceMaterials(tmp);
                            }}
                            options={[
                              { value: 'url', label: 'URL', description: 'Web article, documentation, or online resource' },
                              { value: 'pdf', label: 'PDF Document', description: 'Upload a PDF file (max 4.5MB)' }
                            ]}
                          />
                        </FormField>

                        {ref.type === 'pdf' ? (
                          <FormField
                            label="PDF Document"
                            description="Upload a PDF file for comprehensive analysis"
                            constraintText="Maximum file size: 4.5MB"
                          >
                            <SpaceBetween size="s">
                              <input
                                type="file"
                                accept=".pdf,application/pdf"
                                id={`pdf-upload-${index}`}
                                onChange={(e) => {
                                  const file = e.target.files?.[0];
                                  if (!file) return;

                                  // Check file size (4.5MB limit)
                                  if (file.size > 4.5 * 1024 * 1024) {
                                    alert('PDF file must be under 4.5MB. Please choose a smaller file.');
                                    e.target.value = '';
                                    return;
                                  }

                                  const tmp = [...referenceMaterials];
                                  tmp[index].pdf_file = file;
                                  tmp[index].title = file.name;
                                  setReferenceMaterials(tmp);
                                }}
                                style={{ display: 'none' }}
                              />

                              {!ref.pdf_file ? (
                                <Button
                                  iconName="upload"
                                  onClick={() => document.getElementById(`pdf-upload-${index}`).click()}
                                >
                                  Choose file
                                </Button>
                              ) : (
                                <Container>
                                  <SpaceBetween size="xs">
                                    <ColumnLayout columns={2}>
                                      <Box>
                                        <Box variant="awsui-key-label">File name</Box>
                                        <Box>{ref.pdf_file.name}</Box>
                                      </Box>
                                      <Box>
                                        <Box variant="awsui-key-label">File size</Box>
                                        <Box>{(ref.pdf_file.size / 1024 / 1024).toFixed(2)} MB</Box>
                                      </Box>
                                    </ColumnLayout>
                                    <Button
                                      iconName="close"
                                      variant="link"
                                      onClick={() => {
                                        const tmp = [...referenceMaterials];
                                        tmp[index].pdf_file = null;
                                        tmp[index].title = '';
                                        setReferenceMaterials(tmp);
                                        document.getElementById(`pdf-upload-${index}`).value = '';
                                      }}
                                    >
                                      Remove file
                                    </Button>
                                  </SpaceBetween>
                                </Container>
                              )}
                            </SpaceBetween>
                          </FormField>
                        ) : (
                          <FormField
                            label="URL"
                            description="Link to web article, documentation, or online resource"
                          >
                            <Input
                              value={ref.url || ''}
                              onChange={({ detail }) => {
                                const tmp = [...referenceMaterials];
                                tmp[index].url = detail.value;
                                setReferenceMaterials(tmp);
                              }}
                              placeholder="e.g., https://example.com/article"
                            />
                          </FormField>
                        )}

                        <FormField label="Note">
                          <Input
                            value={ref.note || ''}
                            onChange={({ detail }) => {
                              const tmp = [...referenceMaterials];
                              tmp[index].note = detail.value;
                              setReferenceMaterials(tmp);
                            }}
                            placeholder="Brief description of this reference"
                          />
                        </FormField>
                      </SpaceBetween>
                    </Container>
                  ))}
                </SpaceBetween>
              )}

              <Button
                iconName="add-plus"
                onClick={() => setReferenceMaterials([...referenceMaterials, { type: 'url', url: '', id: '', note: '', pdf_file: null }])}
              >
                Add reference
              </Button>

              <Alert type="info">
                Reference materials are thoroughly analyzed by AI to extract comprehensive insights.
                Processing time increases with the number of references provided (approximately 20-40 seconds per reference).
                We recommend adding 1-3 key sources for optimal balance between depth and speed.
              </Alert>
            </SpaceBetween>
          </Container>
        </SpaceBetween>
      ),
      isOptional: true
    },
    {
      title: 'Review & Submit',
      description: 'Review your configuration',
      content: (
        <Container header={<Header variant="h2">Review Configuration</Header>}>
          <SpaceBetween size="l">
            <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
              <Box>
                <Box variant="awsui-key-label">Topic</Box>
                <Box>{topic || '-'}</Box>
              </Box>
              <Box>
                <Box variant="awsui-key-label">Research Type</Box>
                <Box>
                  {selectedResearchType[0]?.value === 'web'
                    ? `Web Research - ${selectedWebSubType[0]?.label || 'Basic Web'}`
                    : selectedResearchType[0]?.label || 'Web Research'}
                </Box>
              </Box>
              <Box>
                <Box variant="awsui-key-label">Research Depth</Box>
                <Box>{researchDepth.label}</Box>
              </Box>
              <Box>
                <Box variant="awsui-key-label">LLM Model</Box>
                <Box>{llmModel.label}</Box>
              </Box>
              <Box>
                <Box variant="awsui-key-label">Context Provided</Box>
                <Box>{researchContext ? 'Yes' : 'No'}</Box>
              </Box>
              <Box>
                <Box variant="awsui-key-label">Reference Materials</Box>
                <Box>{referenceMaterials.length > 0 ? `${referenceMaterials.length} reference(s)` : 'None'}</Box>
              </Box>
            </Grid>

            {researchContext && (
              <ExpandableSection headerText="Research Context">
                <Box variant="p">{researchContext}</Box>
              </ExpandableSection>
            )}

            {referenceMaterials.length > 0 && (
              <ExpandableSection headerText={`Reference Materials (${referenceMaterials.length})`}>
                <SpaceBetween size="xs">
                  {referenceMaterials.map((ref, idx) => (
                    <Box key={idx}>
                      <Box variant="strong">
                        {idx + 1}. {ref.type === 'pdf' ? 'PDF Document' : 'URL'}:
                      </Box>
                      <Box fontSize="body-s">
                        {ref.type === 'pdf' ? (ref.pdf_file?.name || ref.title || 'PDF Document') : ref.url}
                      </Box>
                      {ref.note && (
                        <Box fontSize="body-s" color="text-body-secondary">
                          {ref.note}
                        </Box>
                      )}
                    </Box>
                  ))}
                </SpaceBetween>
              </ExpandableSection>
            )}

            <Box variant="p" color="text-status-info">
              <strong>Estimated Duration:</strong> {
                researchDepth.value === 'quick' ? '5-10 minutes' :
                researchDepth.value === 'balanced' ? '10-20 minutes' :
                '20-40 minutes'
              }
            </Box>
          </SpaceBetween>
        </Container>
      ),
      isOptional: false
    }
  ];

  return (
    <Wizard
      i18nStrings={{
        stepNumberLabel: stepNumber => `Step ${stepNumber}`,
        collapsedStepsLabel: (stepNumber, stepsCount) =>
          `Step ${stepNumber} of ${stepsCount}`,
        skipToButtonLabel: (step, stepNumber) => `Skip to ${step.title}`,
        navigationAriaLabel: 'Steps',
        cancelButton: 'Cancel',
        previousButton: 'Previous',
        nextButton: 'Next',
        submitButton: 'Start Research',
        optional: 'optional'
      }}
      onNavigate={({ detail }) => setActiveStepIndex(detail.requestedStepIndex)}
      onCancel={() => navigate('/dashboard')}
      onSubmit={handleSubmit}
      activeStepIndex={activeStepIndex}
      steps={steps}
      isLoadingNextStep={loading}
    />
  );
}
