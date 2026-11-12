export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  model: string;
  system_prompt: string;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  cost: number;
  citations: Citation[];
  error: string | null;
  created_at: string;
}

export interface Citation {
  index?: number;
  document_id?: number;
  filename?: string;
  chunk_id?: number;
  url?: string;
  title?: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ModelInfo {
  id: number;
  provider: string;
  model_id: string;
  name: string;
  context_window: number;
  input_price: number;
  output_price: number;
  capabilities: Record<string, boolean>;
  enabled: boolean;
}

export interface ModelCatalog {
  configured: boolean;
  default_model: string;
  models: ModelInfo[];
}

export interface SearchResult {
  title: string;
  url: string;
  content: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  answer: string | null;
  results: SearchResult[];
  provider: string;
  latency_ms: number;
}

export interface ResearchRun {
  id: number;
  question: string;
  plan: string[];
  report: string;
  sources: { title: string; url: string; snippet?: string; retrieved_at?: string }[];
  status: string;
  created_at: string;
}

export interface MediaItem {
  id: number;
  kind: string;
  title: string;
  mime_type: string;
  size: number;
  source: string;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface Agent {
  id: number;
  slug: string;
  name: string;
  domain: string;
  description: string;
  model: string;
  tools: string[];
  restrictions: string[];
  enabled: boolean;
}

export interface AgentExecution {
  id: number;
  agent_id: number;
  input: string;
  output: string;
  model: string;
  status: string;
  error: string | null;
  tokens_in: number;
  tokens_out: number;
  cost: number;
  latency_ms: number;
  log: { step: string; status: string; error?: string; reason?: string }[];
  created_at: string;
}

export interface Workflow {
  id: number;
  name: string;
  description: string;
  graph: WorkflowGraph;
  version: number;
  active: boolean;
  created_at: string;
}

export interface WorkflowNode {
  id: string;
  type: string;
  config: Record<string, unknown>;
}

export interface WorkflowGraph {
  nodes: WorkflowNode[];
  edges: { from: string; to: string }[];
}

export interface WorkflowExecution {
  id: number;
  workflow_id: number;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  logs: { node_id: string; type: string; status: string; error?: string; ms?: number; output?: unknown }[];
  error: string | null;
  approval_token: string | null;
  created_at: string;
}

export interface KnowledgeBase {
  id: number;
  name: string;
  description: string;
  document_count?: number;
  created_at: string;
}

export interface DocumentItem {
  id: number;
  knowledge_base_id: number;
  filename: string;
  mime_type: string;
  size: number;
  status: string;
  error: string | null;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface RagHit {
  document_id: number;
  filename: string;
  chunk_id: number;
  content: string;
  score: number;
}

export interface Chatbot {
  id: number;
  name: string;
  instructions: string;
  model: string;
  knowledge_base_id: number | null;
  grounded: boolean;
  public_token: string;
  published: boolean;
  theme: Record<string, unknown>;
}

export interface MCPConnection {
  id: number;
  name: string;
  url: string;
  allowed_tools: string[];
  require_approval: boolean;
  allow_private: boolean;
  enabled: boolean;
  status: string;
  tools: { name: string; description: string; inputSchema: Record<string, unknown> }[];
  last_error: string | null;
  last_checked: string | null;
}

export interface EvalDataset {
  id: number;
  name: string;
  items: { question: string; expected: string; contexts?: string[] }[];
  created_at: string;
}

export interface EvalRun {
  id: number;
  dataset_id: number;
  model: string;
  status: string;
  metrics: Record<string, number | null>;
  results: Record<string, unknown>[];
  error: string | null;
  created_at: string;
}

export interface Usage {
  requests: number;
  tokens_in: number;
  tokens_out: number;
  cost: number;
}

export interface Integration {
  provider: string;
  configured: boolean;
  env: string;
}
