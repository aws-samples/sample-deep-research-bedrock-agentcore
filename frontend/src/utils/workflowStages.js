/**
 * Workflow stages mapping from sample-deep-research-bedrock-agentcore workflow.py
 */

// Import from centralized model registry (auto-generated from shared/model_registry.json)
import { getModelOptions } from '../config/modelRegistry';

export const WORKFLOW_STAGES = [
  {
    id: 'initialize_session',
    name: 'Initialize Session',
    description: 'Generate session ID and prepare research environment',
    icon: 'settings',
    order: 0
  },
  {
    id: 'topic_analysis',
    name: 'Topic Analysis',
    description: 'Analyze topic and discover research dimensions',
    icon: 'search',
    order: 1
  },
  {
    id: 'reference_preparation',
    name: 'Reference Preparation',
    description: 'Process reference materials (if provided)',
    icon: 'file',
    order: 2,
    optional: true
  },
  {
    id: 'aspect_analysis',
    name: 'Aspect Analysis',
    description: 'Analyze aspects for each dimension in parallel',
    icon: 'group',
    order: 3
  },
  {
    id: 'prepare_research',
    name: 'Preparing Research',
    description: 'Aggregating aspect analysis results',
    icon: 'sync',
    order: 4,
    hidden: true  // Internal barrier - don't show in UI
  },
  {
    id: 'research_planning',
    name: 'Research Planning',
    description: 'Plan and refine research structure',
    icon: 'calendar',
    order: 5
  },
  {
    id: 'research',
    name: 'Deep Research',
    description: 'Conduct deep research for each aspect in parallel',
    icon: 'file-search',
    order: 6
  },
  {
    id: 'prepare_dimension_reduction',
    name: 'Preparing Document Generation',
    description: 'Aggregating research results',
    icon: 'sync',
    order: 7,
    hidden: true  // Internal barrier - don't show in UI
  },
  {
    id: 'dimension_reduction',
    name: 'Document Generation',
    description: 'Generate documents for each dimension in parallel',
    icon: 'file-text',
    order: 8
  },
  {
    id: 'chart_generation',
    name: 'Chart Generation',
    description: 'Generate visualizations for research report',
    icon: 'bar-chart',
    order: 9
  },
  {
    id: 'report_writing',
    name: 'Report Writing',
    description: 'Merge documents and create final report with charts',
    icon: 'edit',
    order: 10
  },
  {
    id: 'finalize',
    name: 'Finalize',
    description: 'Complete research workflow and save results',
    icon: 'check',
    order: 11
  },
  {
    id: 'workflow_complete',
    name: 'Completed',
    description: 'Research workflow completed successfully',
    icon: 'check-circle',
    order: 12,
    hidden: true  // Don't show in UI - just for final state tracking
  }
];

export const RESEARCH_TYPES = [
  {
    value: 'web',
    label: 'Web Research',
    description: 'Search and analyze web content from public sources',
    icon: 'external',
    hasSubTypes: true,
    subTypes: ['basic_web', 'advanced_web']
  },
  {
    value: 'academic',
    label: 'Academic Research',
    description: 'Access ArXiv papers, academic publications, and research papers',
    icon: 'insert-row'
  },
  {
    value: 'financial',
    label: 'Financial Research',
    description: 'Analyze financial data, market trends, and economic indicators',
    icon: 'status-positive'
  },
  {
    value: 'comprehensive',
    label: 'Comprehensive',
    description: 'Use all available research tools and sources for complete analysis',
    icon: 'folder-open'
  },
  {
    value: 'custom',
    label: 'Custom',
    description: 'Configure custom research sources and tools (Coming soon)',
    icon: 'settings',
    disabled: true
  }
];

export const WEB_RESEARCH_SUBTYPES = [
  {
    value: 'basic_web',
    label: 'Basic Web',
    description: 'Standard web search with essential analysis tools'
  },
  {
    value: 'advanced_web',
    label: 'Advanced Web',
    description: 'Deep web search with comprehensive analysis and advanced tools'
  }
];

export const RESEARCH_DEPTHS = [
  {
    value: 'quick',
    label: 'Quick',
    description: 'Faster research with focused scope'
  },
  {
    value: 'balanced',
    label: 'Balanced',
    description: 'Good balance between speed and comprehensiveness'
  },
  {
    value: 'deep',
    label: 'Deep',
    description: 'Thorough and comprehensive research'
  }
];

export const LLM_MODELS = getModelOptions('research');

/**
 * Get stage by ID
 */
export function getStageById(stageId) {
  return WORKFLOW_STAGES.find(stage => stage.id === stageId);
}

/**
 * Get stage index (order)
 */
export function getStageIndex(stageId) {
  const stage = getStageById(stageId);
  return stage ? stage.order : -1;
}

/**
 * Check if stage is completed
 */
export function isStageCompleted(currentStageId, checkStageId) {
  const currentIndex = getStageIndex(currentStageId);
  const checkIndex = getStageIndex(checkStageId);
  return currentIndex > checkIndex;
}

/**
 * Get progress percentage with weighted stages
 *
 * Stage weights (50% deep research, 50% document/chart generation):
 * - initialize_session: 5%
 * - topic_analysis: 10%
 * - aspect_analysis: 15%
 * - research_planning: 10%
 * - research (Deep Research): 10% (total 50% at this point)
 * - dimension_reduction: 20%
 * - chart_generation: 15%
 * - report_writing: 10%
 * - finalize: 5%
 */
export function getProgressPercentage(currentStageId) {
  if (!currentStageId) return 0;

  // Cumulative progress up to and including current stage
  const cumulativeProgress = {
    'initialize_session': 5,
    'topic_analysis': 15,
    'aspect_analysis': 30,
    'prepare_research': 30,
    'research_planning': 40,
    'research': 50,           // Deep research complete = 50%
    'prepare_dimension_reduction': 50,
    'dimension_reduction': 70,
    'chart_generation': 85,
    'report_writing': 95,
    'finalize': 100
  };

  return cumulativeProgress[currentStageId] || 0;
}

/**
 * Format elapsed time
 * @param {number|string} elapsedTime - Elapsed time in seconds (from DynamoDB) or timestamp
 */
export function formatElapsedTime(elapsedTime) {
  if (!elapsedTime) return '0s';

  // If elapsedTime is already in seconds (number from DynamoDB)
  let elapsed;
  if (typeof elapsedTime === 'number' && elapsedTime < 1000000) {
    // It's already elapsed seconds (not a timestamp)
    elapsed = elapsedTime;
  } else {
    // It's a timestamp, calculate elapsed time
    elapsed = Date.now() / 1000 - elapsedTime;
  }

  const hours = Math.floor(elapsed / 3600);
  const minutes = Math.floor((elapsed % 3600) / 60);
  const seconds = Math.floor(elapsed % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}
