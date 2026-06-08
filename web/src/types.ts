export type UploadResponse = {
  dataset_id: string;
  filename: string;
  rows: number;
  columns: number;
  message: string;
};

export type RecordRow = Record<string, unknown>;

export type Section = "upload" | "overview" | "quality" | "dashboard" | "ecommerce" | "charts" | "ask" | "report";

export type ItemsResponse = {
  dataset_id: string;
  items: RecordRow[];
};

export type SummaryWrapper = {
  dataset_id: string;
  summary: {
    items?: RecordRow[];
    warning?: string | null;
    [key: string]: unknown;
  };
};

export type SummaryResponse = {
  dataset_id: string;
  shape: { rows: number; columns: number };
  columns: string[];
  column_types: Record<string, string>;
  missing_values: Record<string, number>;
  missing_percent: Record<string, number>;
  duplicate_rows: number;
  recommendations: string[];
};

export type EcommerceOverview = {
  dataset_id: string;
  overview: {
    rows: number;
    columns: number;
    unique_orders: number;
    date_min: string | null;
    date_max: string | null;
    total_revenue: number;
    total_qty: number;
    cancel_rate: number;
    missing_amount_rows: number;
    missing_amount_percent: number;
    notes: string[];
  };
  data_quality: {
    duplicate_rows: number;
    duplicate_order_id_rows: number;
    missing_values: Record<string, number>;
    missing_percent: Record<string, number>;
    warnings: string[];
  };
};

export type AnswerCard = {
  headline: string;
  summary: string;
  key_takeaways: Array<{
    label: string;
    text: string;
    tone: "positive" | "neutral" | "warning" | "risk";
  }>;
  evidence: Array<{
    label: string;
    value: string;
    description?: string | null;
  }>;
  why_it_matters: string;
  recommended_next_questions: string[];
  confidence: "low" | "medium" | "high";
  answer_source: "llm_structured" | "deterministic_composer" | "tool_error";
  data_warnings: string[];
  calculation_notes: string[];
};

export type AgentResponse = {
  answer: string;
  answer_card?: AnswerCard | null;
  tool_call?: {
    tool_name: string;
    arguments: Record<string, unknown>;
    result?: unknown;
    error?: string | null;
    purpose?: string | null;
    execution_ms?: number | null;
  } | null;
  tool_calls?: Array<{
    tool_name: string;
    arguments: Record<string, unknown>;
    result?: unknown;
    error?: string | null;
    purpose?: string | null;
    execution_ms?: number | null;
  }>;
  agent_plan?: Record<string, unknown> | null;
  data?: unknown;
  chart?: { data: unknown[]; layout: Record<string, unknown> } | null;
  warnings: string[];
  execution_timeline?: Array<{
    step: string;
    status: string;
    detail?: string | null;
    elapsed_ms?: number | null;
    metadata: Record<string, unknown>;
  }>;
  result_summary?: {
    row_count?: number | null;
    top_item?: unknown;
    primary_metric?: string | null;
    primary_metric_value?: unknown;
    has_chart: boolean;
    result_type: string;
  } | null;
  explanation_source?: "llm" | "deterministic_fallback" | "tool_error";
  quick_actions?: Array<{
    action: "view_chart" | "export_result" | "ask_followup" | "add_to_report" | "explain_calculation";
    label: string;
    payload: Record<string, unknown>;
  }>;
  latency?: Record<string, unknown>;
  cache?: Record<string, unknown>;
};

export type AgentStatus = {
  available: boolean;
  ollama_available?: boolean;
  base_url: string | null;
  model: string | null;
  router_model?: string | null;
  model_loaded: boolean | null;
  router_model_loaded?: boolean | null;
  models: string[];
  error: string | null;
};

export type SemanticCandidate = {
  role: string;
  column: string;
  confidence: number;
  confidence_label: string;
  reason: string;
  score_breakdown?: Record<string, number>;
};

export type SemanticProfile = {
  dataset_id?: string;
  domain: string;
  domain_confidence?: number;
  domain_reasons?: string[];
  roles: Record<string, { role: string; column: string; confidence: number; reason: string; confidence_label?: string; source?: string }>;
  candidates?: Record<string, SemanticCandidate[]>;
  unmatched_columns: string[];
  warnings: string[];
  overrides?: { domain?: string | null; roles?: Record<string, string> };
};

export type DataDictionaryField = {
  column_name: string;
  business_name?: string | null;
  description?: string | null;
  semantic_role?: string | null;
  data_type?: string | null;
  unit?: string | null;
  aggregation?: string | null;
  sensitive: boolean;
  allowed_values: string[];
};

export type DataDictionary = {
  domain?: string | null;
  fields: DataDictionaryField[];
};

export type DataDictionaryResponse = {
  dataset_id: string;
  dictionary: DataDictionary | null;
  source: string;
  warnings: string[];
};

export type MetricDefinition = {
  name: string;
  label?: string | null;
  description?: string | null;
  expression: string;
  format: "number" | "percent" | "currency" | "integer";
  aggregation: "sum" | "mean" | "median" | "min" | "max" | "count";
  required_roles: string[];
  higher_is_better: boolean;
};

export type MetricListResponse = {
  dataset_id: string;
  metrics: MetricDefinition[];
};

export type MetricResponse = {
  dataset_id: string;
  metric: MetricDefinition;
  warnings: string[];
};

export type MetricEvaluationResponse = {
  dataset_id: string;
  metric_name: string;
  summary: Record<string, unknown>;
  rows?: RecordRow[] | null;
  warnings: string[];
};

export type DashboardResponse = {
  contract_version?: number;
  dataset_id: string;
  domain: string;
  semantic_profile: SemanticProfile;
  kpi_cards: Array<{ label: string; value: string; description: string; tone: string }>;
  insight_cards: Array<{
    title: string;
    value?: string;
    narrative?: string;
    finding?: string;
    evidence?: string;
    why_it_matters?: string;
    recommended_next_question?: string;
    tone: string;
    severity?: string;
    confidence?: number;
    related_chart_id?: string | null;
    related_table_id?: string | null;
  }>;
  charts: Array<{ id?: string; title: string; description: string; chart: { data: unknown[]; layout: Record<string, unknown> } }>;
  tables: Array<{ id?: string; title: string; description: string; rows: RecordRow[] }>;
  warnings: string[];
  cache?: Record<string, unknown>;
};
