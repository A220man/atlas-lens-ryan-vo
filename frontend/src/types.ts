export type RoleType = 'viewer' | 'operator' | 'admin';

export interface User {
  id: string;
  email: string;
  role: RoleType;
  is_demo: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: RoleType;
  expires_in: number;
  user_id: string;
  email: string;
}

export interface ChatValidationReport {
  is_valid: boolean;
  total_messages: number;
  cycles_detected: boolean;
  orphan_messages: string[];
  missing_children_links: number;
  out_of_sync_count: number;
  repaired: boolean;
  details: string[];
}

export interface ChatRecord {
  id: string;
  title: string;
  user_id: string;
  total_messages: number;
  is_repaired: boolean;
  created_at: string;
  updated_at: string;
  validation_summary: ChatValidationReport;
}

export interface ChatNode {
  id: string;
  parentId?: string | null;
  childrenIds: string[];
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp?: number;
  model?: string;
  thinking_content?: string;
}

export interface ChatDetailResponse {
  id: string;
  title: string;
  user_id: string;
  is_repaired: boolean;
  created_at: string;
  updated_at: string;
  validation_report: ChatValidationReport;
  chat_data: {
    history?: {
      messages?: Record<string, ChatNode>;
      currentId?: string;
    };
    messages?: ChatNode[];
  };
  linearized_trajectory: ChatNode[];
}

export interface PromptMessageItem {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  reasoning?: string;
}

export interface SanitizedMessage {
  role: string;
  content: string;
  stripped_reasoning?: string | null;
}

export interface PromptHygieneResponse {
  model_id: string;
  reinject_reasoning: boolean;
  original_estimated_tokens: number;
  sanitized_estimated_tokens: number;
  token_savings_pct: number;
  contains_think_tags: boolean;
  imitation_risk_score: number;
  sanitized_messages: SanitizedMessage[];
}

export interface McpServerResponse {
  id: string;
  name: string;
  url: string;
  description: string;
  global_header_keys: string[];
  created_at: string;
}

export interface UserMcpHeaderResponse {
  id: string;
  server_id: string;
  user_id: string;
  header_key: string;
  header_value_masked: string;
  created_at: string;
}

export interface McpToolExecuteResponse {
  server_id: string;
  tool_name: string;
  status: 'success' | 'mocked_fallback' | 'error';
  result: any;
  injected_header_keys: string[];
  execution_time_ms: number;
}

export interface EvaluationMetricSummary {
  run_id: string;
  timestamp: string;
  dataset_name: string;
  sample_count: number;
  mean_token_savings_pct: number;
  imitation_suppression_pct: number;
  dag_healing_success_pct: number;
  mean_repair_latency_ms: number;
  observations: string[];
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, any>;
}
