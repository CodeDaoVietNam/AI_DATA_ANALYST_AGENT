from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from typing import Literal


class ChatRequest(BaseModel):
    dataset_id: str
    question: str


class ChatResponse(BaseModel):
    answer: str
    data: Optional[Any] = None
    chart: Optional[Dict[str, Any]] = None


class ChartRequest(BaseModel):
    dataset_id: str
    chart_type: Literal["bar", "line", "scatter", "histogram", "box"]
    x: str
    y: Optional[str] = None


class GenericGroupbyRequest(BaseModel):
    dataset_id: str
    group_by: str
    metric: str
    aggregation: Literal["sum", "mean", "median", "min", "max", "count"]
    limit: int = Field(default=50, ge=1, le=500)


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    purpose: Optional[str] = None
    execution_ms: Optional[float] = None


class ExecutionTimelineRecord(BaseModel):
    step: str
    status: str
    detail: Optional[str] = None
    elapsed_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResultSummary(BaseModel):
    row_count: Optional[int] = None
    top_item: Optional[Any] = None
    primary_metric: Optional[str] = None
    primary_metric_value: Optional[Any] = None
    has_chart: bool = False
    result_type: str


class ResultQualityModel(BaseModel):
    status: Literal["strong", "partial", "empty", "insufficient", "tool_error"]
    reason: str
    has_rows: bool
    row_count: Optional[int] = None
    has_metric: bool
    metric_name: Optional[str] = None
    metric_value: Optional[Any] = None
    has_label: bool
    label: Optional[str] = None
    render_mode: str
    warnings: List[str] = Field(default_factory=list)


class QuickAction(BaseModel):
    action: Literal["view_chart", "export_result", "ask_followup", "add_to_report", "explain_calculation"]
    label: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class AnswerTakeaway(BaseModel):
    label: str
    text: str
    tone: Literal["positive", "neutral", "warning", "risk"] = "neutral"


class AnswerEvidence(BaseModel):
    label: str
    value: str
    description: Optional[str] = None


class AnswerCard(BaseModel):
    headline: str
    summary: str
    key_takeaways: List[AnswerTakeaway] = Field(default_factory=list)
    evidence: List[AnswerEvidence] = Field(default_factory=list)
    why_it_matters: str
    recommended_next_questions: List[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    answer_source: Literal["llm_structured", "deterministic_composer", "tool_error"] = "deterministic_composer"
    data_warnings: List[str] = Field(default_factory=list)
    calculation_notes: List[str] = Field(default_factory=list)


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    tool_name: Optional[str] = None
    tool_result_summary: Optional[Dict[str, Any]] = None
    answer_card: Optional[Dict[str, Any]] = None


class AgentChatRequest(BaseModel):
    dataset_id: str
    question: str
    mode: Literal["fast", "balanced", "deep"] = "balanced"
    conversation_history: List[ConversationMessage] = Field(default_factory=list)


class AgentChatResponse(BaseModel):
    answer: str
    answer_card: Optional[AnswerCard] = None
    tool_call: Optional[ToolCallRecord] = None
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    agent_plan: Optional[Dict[str, Any]] = None
    data: Optional[Any] = None
    chart: Optional[Dict[str, Any]] = None
    warnings: List[str] = Field(default_factory=list)
    execution_timeline: List[ExecutionTimelineRecord] = Field(default_factory=list)
    result_summary: Optional[ResultSummary] = None
    result_quality: Optional[ResultQualityModel] = None
    explanation_source: Literal["llm", "deterministic_fallback", "tool_error"] = "deterministic_fallback"
    quick_actions: List[QuickAction] = Field(default_factory=list)
    latency: Dict[str, Any] = Field(default_factory=dict)
    cache: Dict[str, Any] = Field(default_factory=dict)
    conversation_context_used: Optional[bool] = None
    resolved_references: List[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    dataset_id: str
    filename: str
    rows: int
    columns: int
    message: str


class SemanticOverrideRequest(BaseModel):
    domain: Optional[str] = None
    roles: Dict[str, Optional[str]] = Field(default_factory=dict)


class DataDictionaryField(BaseModel):
    column_name: str
    business_name: Optional[str] = None
    description: Optional[str] = None
    semantic_role: Optional[str] = None
    data_type: Optional[str] = None
    unit: Optional[str] = None
    aggregation: Optional[str] = None
    sensitive: bool = False
    allowed_values: List[str] = Field(default_factory=list)


class DataDictionary(BaseModel):
    domain: Optional[str] = None
    fields: List[DataDictionaryField] = Field(default_factory=list)


class DataDictionaryResponse(BaseModel):
    dataset_id: str
    dictionary: Optional[DataDictionary] = None
    source: str = "none"
    warnings: List[str] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    expression: str
    format: Literal["number", "percent", "currency", "integer"] = "number"
    aggregation: Literal["sum", "mean", "median", "min", "max", "count"] = "mean"
    required_roles: List[str] = Field(default_factory=list)
    higher_is_better: bool = True


class MetricListResponse(BaseModel):
    dataset_id: str
    metrics: List[MetricDefinition] = Field(default_factory=list)


class MetricResponse(BaseModel):
    dataset_id: str
    metric: MetricDefinition
    warnings: List[str] = Field(default_factory=list)


class MetricEvaluationResponse(BaseModel):
    dataset_id: str
    metric_name: str
    summary: Dict[str, Any]
    rows: Optional[List[Dict[str, Any]]] = None
    warnings: List[str] = Field(default_factory=list)


class DatasetSummary(BaseModel):
    dataset_id: str
    shape: Dict[str, int]
    columns: List[str]
    column_types: Dict[str, str]
    missing_values: Dict[str, int]
    duplicate_rows: int
    numeric_summary: Dict[str, Any]
    categorical_summary: Dict[str, Any]
    recommendations: List[str]
