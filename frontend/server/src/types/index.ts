/**
 * Research Status - Lightweight metadata stored in DynamoDB
 * Detailed workflow state is managed by LangGraph AgentCore checkpointer
 */
export interface ResearchStatus {
  session_id: string;
  user_id?: string;
  topic: string;
  research_type: string;
  research_depth: string;
  research_context?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelling' | 'cancelled';
  current_stage?: string;
  error?: string;
  // Final output files (S3 paths)
  report_file?: string;
  dimension_documents?: Record<string, string>;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  // Version management
  versions?: Record<string, any>;
  current_version?: string;
  // Comments
  comments?: any[];
  // Review metadata
  review_status?: 'not_started' | 'draft' | 'in_review' | 'approved';
  review_version?: string; // Version being reviewed
  review_base_version?: string; // Base version for comparison
  review_started_at?: string;
  review_completed_at?: string;
  pending_comments_count?: number;
  resolved_comments_count?: number;
}

export interface CreateResearchRequest {
  topic: string;
  research_type: string;
  research_depth: string;
  llm_model?: string;
  research_context?: string;
}

export interface CreateResearchResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface AgentCoreInvokeRequest {
  topic: string;
  researchConfig: {
    research_type: string;
    research_depth: string;
    research_context?: string;
    [key: string]: any;
  };
  userId?: string;
}

export interface AgentCoreInvokeResponse {
  session_id: string;
  status: string;
  trace_id?: string;
  result?: any;
}

export interface ChatSession {
  session_id: string;
  research_id?: string;
  research_name?: string;  // Name/title of the research
  model_id: string;
  title?: string;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export interface UserPreferences {
  user_id: string;
  default_chat_model?: string;
  default_research_model?: string;
  default_research_type?: string;
  default_research_depth?: string;
  chat_sessions?: ChatSession[];
  created_at: string;
  updated_at: string;
}
