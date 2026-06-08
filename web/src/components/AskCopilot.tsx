import { useMemo, type FormEvent } from "react";
import {
  AlertTriangle,
  BarChart3,
  Bot,
  CheckCircle2,
  Clock3,
  Download,
  FilePlus2,
  HelpCircle,
  Info,
  Loader2,
  MessageSquarePlus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Table2,
  Timer,
  Wand2,
} from "lucide-react";

import { useI18n } from "../i18n";
import type { AgentResponse, AgentStatus, AnswerCard, DashboardResponse, RecordRow } from "../types";

export type ChatEntry = {
  id: string;
  question: string;
  response: AgentResponse;
  status: "pending" | "done" | "error";
};

type QuickAction = NonNullable<AgentResponse["quick_actions"]>[number];

type AskCopilotProps = {
  onAsk: (formData: FormData) => void;
  onAskQuestion: (question: string) => void;
  onQuickAction: (action: QuickAction, response: AgentResponse) => void;
  chatHistory: ChatEntry[];
  disabled: boolean;
  clearHistory: () => void;
  agentStatus: AgentStatus | null;
  questionDraft: string;
  setQuestionDraft: (value: string) => void;
  dashboard: DashboardResponse | null;
};

const TIMELINE_STEPS = [
  { key: "understanding", icon: Search },
  { key: "selecting", icon: Wand2 },
  { key: "running", icon: Table2 },
  { key: "answering", icon: Sparkles },
];

export function AskCopilot({
  onAsk,
  onAskQuestion,
  onQuickAction,
  chatHistory,
  disabled,
  clearHistory,
  agentStatus,
  questionDraft,
  setQuestionDraft,
  dashboard,
}: AskCopilotProps) {
  const { t } = useI18n();
  const domain = dashboard?.domain || "generic";
  const suggestions = useMemo(() => t.ask.suggestions[domain as keyof typeof t.ask.suggestions] ?? t.ask.suggestions.generic, [domain, t]);
  const timelineLabels = useMemo(
    () => TIMELINE_STEPS.map((step) => ({
      ...step,
      label: t.ask.timeline[step.key as keyof typeof t.ask.timeline],
    })),
    [t],
  );
  const isOllamaReady = Boolean(agentStatus?.available && agentStatus.model_loaded);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    onAsk(new FormData(form));
    setQuestionDraft("");
  }

  return (
    <div className="copilot-shell">
      <section className="copilot-command-center">
        <div className="copilot-command-copy">
          <div className="copilot-orb">
            <Bot size={18} />
          </div>
          <div>
            <div className="copilot-eyebrow">{t.ask.eyebrow}</div>
            <h2>{t.ask.title}</h2>
            <p>{t.ask.subtitle}</p>
          </div>
        </div>
        <div className="copilot-status-stack">
          <span className={isOllamaReady ? "copilot-status is-online" : "copilot-status is-fallback"}>
            <span className="live-dot" />
            {isOllamaReady ? `${agentStatus?.model} · router ${agentStatus?.router_model || "default"}` : t.ask.deterministicFallback}
          </span>
          <span className="copilot-status is-domain">{domain}</span>
          {chatHistory.length > 0 && (
            <button className="btn-ghost" onClick={clearHistory}>
              {t.ask.clearChat}
            </button>
          )}
        </div>
      </section>

      <section className="copilot-suggestions" aria-label={t.ask.suggestionsTitle}>
        <div>
          <span>{t.ask.suggestionsTitle}</span>
          <p>{t.ask.suggestionsSubtitle}</p>
        </div>
        <div className="copilot-suggestion-list">
          {suggestions.map((question) => (
            <button key={question} disabled={disabled} onClick={() => onAskQuestion(question)}>
              {question}
            </button>
          ))}
        </div>
      </section>

      <section className="copilot-thread">
        {chatHistory.length === 0 ? (
          <EmptyCopilotState disabled={disabled} suggestions={suggestions} onAskQuestion={onAskQuestion} />
        ) : (
          chatHistory.map((entry) => (
            <ChatMessage
              key={entry.id}
              entry={entry}
              timelineLabels={timelineLabels}
              onQuickAction={onQuickAction}
              onRetry={() => onAskQuestion(entry.question)}
              onAskQuestion={onAskQuestion}
            />
          ))
        )}
      </section>

      <section className="copilot-input-card">
        <form onSubmit={handleSubmit} className="copilot-input-form">
          <div className="copilot-input-icon">
            <Bot size={15} />
          </div>
          <input
            name="question"
            disabled={disabled}
            value={questionDraft}
            onChange={(event) => setQuestionDraft(event.target.value)}
            placeholder={disabled ? t.ask.disabledPlaceholder : t.ask.inputPlaceholder}
          />
          <button disabled={disabled || !questionDraft.trim()} className="btn-primary">
            <Send size={13} />
            {t.ask.send}
          </button>
        </form>
      </section>
    </div>
  );
}

function EmptyCopilotState({
  disabled,
  suggestions,
  onAskQuestion,
}: {
  disabled: boolean;
  suggestions: string[];
  onAskQuestion: (question: string) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="copilot-empty-state">
      <div className="copilot-empty-icon">
        <MessageSquarePlus size={22} />
      </div>
      <h3>{t.ask.emptyTitle}</h3>
      <p>{t.ask.emptyBody}</p>
      <div className="copilot-empty-actions">
        {suggestions.slice(0, 3).map((question) => (
          <button key={question} disabled={disabled} onClick={() => onAskQuestion(question)}>
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

function ChatMessage({
  entry,
  timelineLabels,
  onQuickAction,
  onRetry,
  onAskQuestion,
}: {
  entry: ChatEntry;
  timelineLabels: Array<{ key: string; label: string; icon: typeof Search }>;
  onQuickAction: (action: QuickAction, response: AgentResponse) => void;
  onRetry: () => void;
  onAskQuestion: (question: string) => void;
}) {
  const { t } = useI18n();
  const response = entry.response;
  const rows = extractRows(response);
  const kpis = extractKpis(response);
  const timeline = buildTimeline(entry, timelineLabels);
  const readable = buildReadableAnswer(entry);
  const hasResult = rows.length > 0 || kpis.length > 0 || Boolean(response.chart);
  const errorType = entry.status === "error" ? classifyError(response) : null;

  return (
    <article className="copilot-message">
      <div className="copilot-user-row">
        <div className="copilot-user-bubble">{entry.question}</div>
      </div>

      <div className={`copilot-ai-bubble ${entry.status === "error" ? "is-error" : ""}`}>
        <header className="copilot-bubble-header">
          <div className="copilot-agent-label">
            {entry.status === "pending" ? <Loader2 size={13} className="animate-spin" /> : <Bot size={13} />}
            <span>{entry.status === "pending" ? "Đang phân tích" : entry.status === "error" ? "Copilot cần xử lý" : "Câu trả lời dựa trên tool"}</span>
          </div>
          <TrustBadges response={response} status={entry.status} />
        </header>

        <ExecutionTimeline timeline={timeline} status={entry.status} timelineLabels={timelineLabels} />

        {entry.status === "error" && errorType ? (
          <ErrorBubble type={errorType} answer={response.answer} onRetry={onRetry} />
        ) : response.answer_card && entry.status !== "pending" ? (
          <AnswerCardRenderer card={response.answer_card} onAskQuestion={onAskQuestion} />
        ) : (
          <ReadableAnswer answer={readable} status={entry.status} />
        )}

        {response.warnings.length > 0 && (
          <div className="copilot-warning-stack">
            {response.warnings.map((warning) => (
              <div key={warning} className="copilot-warning">
                <AlertTriangle size={13} />
                <span>{warning}</span>
              </div>
            ))}
          </div>
        )}

        {hasResult && entry.status !== "error" && (
          <ResultRenderer rows={rows} kpis={kpis} response={response} />
        )}

        <SourceAndCalculation response={response} rows={rows} />

        <QuickActions
          response={response}
          rows={rows}
          onQuickAction={onQuickAction}
          onAskQuestion={onAskQuestion}
        />

        <details className="copilot-trace">
          <summary>
            <Info size={13} />
            {t.ask.toolDetails}
          </summary>
          <pre>{JSON.stringify(buildTracePayload(response), null, 2)}</pre>
        </details>
      </div>
    </article>
  );
}

function ExecutionTimeline({
  timeline,
  status,
  timelineLabels,
}: {
  timeline: Array<{ label: string; state: "done" | "active" | "waiting"; detail?: string }>;
  status: ChatEntry["status"];
  timelineLabels: Array<{ key: string; label: string; icon: typeof Search }>;
}) {
  return (
    <div className="copilot-timeline" aria-label="Copilot execution timeline">
      {timeline.map((step, index) => {
        const Icon = timelineLabels[index]?.icon ?? CheckCircle2;
        return (
          <div key={step.label} className={`copilot-step is-${step.state}`}>
            <span className="copilot-step-icon">
              {step.state === "active" && status === "pending" ? <Loader2 size={12} className="animate-spin" /> : <Icon size={12} />}
            </span>
            <span>{step.label}</span>
          </div>
        );
      })}
    </div>
  );
}

function ReadableAnswer({
  answer,
  status,
}: {
  answer: ReturnType<typeof buildReadableAnswer>;
  status: ChatEntry["status"];
}) {
  if (status === "pending") {
    return (
      <div className="copilot-thinking-card">
        <span className="copilot-thinking-dot" />
        <div>
          <strong>{answer.conclusion}</strong>
          <p>{answer.evidence}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="copilot-answer-grid">
      <section className="copilot-answer-main">
        <span>Kết luận chính</span>
        <p>{answer.conclusion}</p>
      </section>
      <section>
        <span>Số liệu bằng chứng</span>
        <p>{answer.evidence}</p>
      </section>
      <section>
        <span>Vì sao quan trọng</span>
        <p>{answer.why}</p>
      </section>
      <section>
        <span>Câu hỏi tiếp theo</span>
        <p>{answer.next}</p>
      </section>
    </div>
  );
}

function AnswerCardRenderer({
  card,
  onAskQuestion,
}: {
  card: AnswerCard;
  onAskQuestion: (question: string) => void;
}) {
  return (
    <div className="answer-card-v2">
      <section className="answer-card-hero">
        <div>
          <span>Kết luận chính</span>
          <h3>{card.headline}</h3>
          <p>{card.summary}</p>
        </div>
        <div className={`answer-confidence is-${card.confidence}`}>
          <ShieldCheck size={13} />
          {confidenceLabel(card.confidence)}
        </div>
      </section>

      {card.evidence.length > 0 && (
        <section className="answer-evidence-grid">
          {card.evidence.slice(0, 6).map((item) => (
            <div key={`${item.label}-${item.value}`} className="answer-evidence-card">
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              {item.description && <p>{item.description}</p>}
            </div>
          ))}
        </section>
      )}

      {card.key_takeaways.length > 0 && (
        <section className="answer-takeaways">
          {card.key_takeaways.slice(0, 4).map((item) => (
            <div key={`${item.label}-${item.text}`} className={`answer-takeaway is-${item.tone}`}>
              <span>{item.label}</span>
              <p>{item.text}</p>
            </div>
          ))}
        </section>
      )}

      <section className="answer-why-card">
        <span>Vì sao quan trọng</span>
        <p>{card.why_it_matters}</p>
      </section>

      {card.recommended_next_questions.length > 0 && (
        <section className="answer-next-questions">
          <span>Nên hỏi tiếp</span>
          <div>
            {card.recommended_next_questions.slice(0, 4).map((question) => (
              <button key={question} onClick={() => onAskQuestion(question)}>
                <MessageSquarePlus size={13} />
                {question}
              </button>
            ))}
          </div>
        </section>
      )}

      {(card.data_warnings.length > 0 || card.calculation_notes.length > 0) && (
        <details className="answer-calculation-notes">
          <summary>
            <Info size={13} />
            Nguồn tính toán và cảnh báo
          </summary>
          {card.data_warnings.length > 0 && (
            <div>
              <strong>Cảnh báo dữ liệu</strong>
              <ul>
                {card.data_warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
          {card.calculation_notes.length > 0 && (
            <div>
              <strong>Ghi chú tính toán</strong>
              <ul>
                {card.calculation_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          )}
        </details>
      )}
    </div>
  );
}

function ResultRenderer({
  rows,
  kpis,
  response,
}: {
  rows: RecordRow[];
  kpis: Array<{ label: string; value: string }>;
  response: AgentResponse;
}) {
  const { t } = useI18n();
  return (
    <div className="copilot-result-panel">
      <div className="copilot-result-header">
        <div>
          <span>{t.ask.resultPreview}</span>
          <strong>{response.result_summary?.result_type || inferResultType(rows, kpis)}</strong>
        </div>
        <span>{rows.length ? `${rows.length} dòng` : `${kpis.length} metric`}</span>
      </div>

      {kpis.length > 0 && (
        <div className="copilot-kpi-grid">
          {kpis.slice(0, 6).map((kpi) => (
            <div key={kpi.label} className="copilot-kpi-card">
              <span>{humanize(kpi.label)}</span>
              <strong>{kpi.value}</strong>
            </div>
          ))}
        </div>
      )}

      {rows.length > 0 && <MiniResultChart rows={rows} />}
      {rows.length > 0 && <ResultTable rows={rows.slice(0, 8)} />}
    </div>
  );
}

function MiniResultChart({ rows }: { rows: RecordRow[] }) {
  const labelKey = pickLabelKey(rows);
  const metricKey = pickMetricKey(rows);
  if (!labelKey || !metricKey) return null;
  const values = rows
    .slice(0, 8)
    .map((row) => ({ label: String(row[labelKey] ?? "N/A"), value: toNumber(row[metricKey]) ?? 0 }));
  const max = Math.max(...values.map((item) => Math.abs(item.value)), 1);

  return (
    <div className="copilot-mini-chart" aria-label={`Mini chart by ${labelKey}`}>
      {values.map((item) => (
        <div key={`${item.label}-${item.value}`} className="copilot-mini-bar-row">
          <span title={item.label}>{item.label}</span>
          <div>
            <i style={{ width: `${Math.max((Math.abs(item.value) / max) * 100, 2)}%` }} />
          </div>
          <strong>{formatValue(item.value)}</strong>
        </div>
      ))}
    </div>
  );
}

function ResultTable({ rows }: { rows: RecordRow[] }) {
  const columns = Object.keys(rows[0] ?? {}).slice(0, 8);
  if (columns.length === 0) return null;
  return (
    <div className="copilot-table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{humanize(column)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column) => (
                <td key={column}>{formatUnknown(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TrustBadges({ response, status }: { response: AgentResponse; status: ChatEntry["status"] }) {
  const { t } = useI18n();
  const source = response.explanation_source || (status === "pending" ? "running" : "tool_result");
  const totalMs = response.latency?.total_ms;
  const cache = inferCacheState(response.cache);
  return (
    <div className="copilot-trust-badges">
      <span>
        <ShieldCheck size={12} />
        {t.ask.basedOnTool}
      </span>
      <span>
        <Timer size={12} />
        {typeof totalMs === "number" ? `${Math.round(totalMs)}ms` : t.ask.latencyPending}
      </span>
      <span>{source}</span>
      {cache && <span>{cache}</span>}
    </div>
  );
}

function SourceAndCalculation({ response, rows }: { response: AgentResponse; rows: RecordRow[] }) {
  const { t } = useI18n();
  const toolName = response.tool_call?.tool_name || response.tool_calls?.[0]?.tool_name || "none";
  const args = response.tool_call?.arguments || response.tool_calls?.[0]?.arguments || {};
  const sourceColumns = Array.from(
    new Set(
      Object.values(args)
        .flatMap((value) => (Array.isArray(value) ? value : [value]))
        .filter((value): value is string => typeof value === "string")
    )
  ).slice(0, 6);
  const columns = rows.length ? Object.keys(rows[0]).slice(0, 6) : sourceColumns;

  return (
    <div className="copilot-source-card">
      <div>
        <span>{t.ask.source}</span>
        <strong>{toolName}</strong>
      </div>
      <div>
        <span>{t.ask.calculationColumns}</span>
        <strong>{columns.length ? columns.join(", ") : t.ask.toolArgumentsOnly}</strong>
      </div>
      {(response.warnings.some((warning) => /missing|nan|null|partial/i.test(warning)) || hasNaNish(rows)) && (
        <div className="copilot-source-warning">
          <AlertTriangle size={12} />
          Giá trị thiếu/NaN có thể ảnh hưởng tới tổng hoặc tỷ lệ.
        </div>
      )}
    </div>
  );
}

function QuickActions({
  response,
  rows,
  onQuickAction,
  onAskQuestion,
}: {
  response: AgentResponse;
  rows: RecordRow[];
  onQuickAction: (action: QuickAction, response: AgentResponse) => void;
  onAskQuestion: (question: string) => void;
}) {
  const followUp = response.answer_card?.recommended_next_questions?.[0] ?? buildReadableAnswer({ response, status: "done" }).next;
  const actions: QuickAction[] = normalizeQuickActions(response, rows, followUp);

  return (
    <div className="copilot-actions">
      {actions.map((action) => {
        const Icon = actionIcon(action.action);
        return (
          <button
            key={`${action.action}-${action.label}`}
            onClick={() => {
              if (action.action === "ask_followup" && response.answer_card?.recommended_next_questions?.[0]) {
                onAskQuestion(response.answer_card.recommended_next_questions[0]);
                return;
              }
              onQuickAction(action, response);
            }}
          >
            <Icon size={13} />
            {action.label}
          </button>
        );
      })}
    </div>
  );
}

function ErrorBubble({
  type,
  answer,
  onRetry,
}: {
  type: ReturnType<typeof classifyError>;
  answer: string;
  onRetry: () => void;
}) {
  const copy = {
    backend: {
      title: "Chưa kết nối được backend",
      body: "FastAPI có thể chưa chạy, sai port, hoặc bị CORS/network chặn. Hãy kiểm tra backend 8000 rồi retry.",
    },
    ollama: {
      title: "Ollama chưa sẵn sàng",
      body: "Copilot vẫn có deterministic fallback, nhưng phần giải thích LLM có thể không chạy cho tới khi Ollama/model hoạt động.",
    },
    mapping: {
      title: "Thiếu mapping dữ liệu",
      body: "Câu hỏi cần semantic role chưa chắc chắn. Hãy chỉnh Data Dictionary hoặc Semantic Mapping rồi hỏi lại.",
    },
    unclear: {
      title: "Câu hỏi chưa đủ rõ",
      body: "Hãy nêu metric và dimension cụ thể hơn, ví dụ: doanh thu theo category hoặc attrition theo department.",
    },
    generic: {
      title: "Agent chưa chạy thành công",
      body: answer || "Có lỗi khi chạy analysis tool. Bạn có thể retry hoặc hỏi theo cách cụ thể hơn.",
    },
  }[type];

  return (
    <div className="copilot-error-card">
      <AlertTriangle size={18} />
      <div>
        <strong>{copy.title}</strong>
        <p>{copy.body}</p>
        {answer && <small>{answer}</small>}
        <button onClick={onRetry}>
          <RefreshCw size={12} />
          Thử lại / dùng fallback
        </button>
      </div>
    </div>
  );
}

function buildTimeline(entry: ChatEntry, timelineLabels: Array<{ key: string; label: string; icon: typeof Search }>) {
  if (entry.status === "done") {
    return timelineLabels.map((step) => ({ label: step.label, state: "done" as const }));
  }
  if (entry.status === "error") {
    return timelineLabels.map((step, index) => ({ label: step.label, state: index < 2 ? ("done" as const) : ("waiting" as const) }));
  }
  const answer = entry.response.answer.toLowerCase();
  let activeIndex = 0;
  if (answer.includes("plan") || answer.includes("tool phù hợp") || answer.includes("select")) activeIndex = 1;
  if (answer.includes("running") || answer.includes("đang chạy") || answer.includes("tool")) activeIndex = 2;
  if (answer.includes("answer") || answer.includes("trả lời") || answer.includes("explanation")) activeIndex = 3;
  return timelineLabels.map((step, index) => ({
    label: step.label,
    state: index < activeIndex ? ("done" as const) : index === activeIndex ? ("active" as const) : ("waiting" as const),
  }));
}

function buildReadableAnswer(entry: Pick<ChatEntry, "response" | "status">) {
  const response = entry.response;
  const firstLine = String(response.answer || "").split("\n").find(Boolean)?.trim();
  const summary = response.result_summary;
  const toolName = response.tool_call?.tool_name || response.tool_calls?.[0]?.tool_name;
  const rows = extractRows(response);
  const top = summary?.top_item ? summarizeObject(summary.top_item) : rows[0] ? summarizeObject(rows[0]) : null;
  const metric = summary?.primary_metric || pickMetricKey(rows) || "metric";
  const primaryValue = summary?.primary_metric_value;

  if (entry.status === "pending") {
    return {
      conclusion: firstLine || "Copilot đang xử lý câu hỏi.",
      evidence: "Đang chọn analysis tool và chuẩn bị chạy trên dataset hiện tại.",
      why: "User cần biết hệ thống không bị đứng mà đang thực thi từng bước.",
      next: "Đợi tool hoàn tất rồi xem result preview.",
    };
  }

  return {
    conclusion: firstLine || "Copilot đã hoàn tất phân tích từ tool result.",
    evidence: top
      ? `Top result: ${top}${primaryValue !== undefined && primaryValue !== null ? `; ${metric} = ${formatUnknown(primaryValue)}` : ""}.`
      : toolName
        ? `Tool ${toolName} đã chạy và trả về ${summary?.row_count ?? rows.length ?? 0} dòng kết quả.`
        : "Kết quả được lấy từ phân tích deterministic phía backend.",
    why: inferWhyItMatters(toolName, response.answer),
    next: inferNextQuestion(toolName, rows),
  };
}

function extractRows(response: AgentResponse): RecordRow[] {
  const candidates = [
    response.tool_call?.result,
    response.data,
    response.tool_calls?.find((call) => Array.isArray(call.result))?.result,
  ];
  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      return candidate.filter(isRecord).slice(0, 50);
    }
    if (isRecord(candidate)) {
      const nested = Object.values(candidate).find(Array.isArray);
      if (Array.isArray(nested)) return nested.filter(isRecord).slice(0, 50);
      if (candidate.items && Array.isArray(candidate.items)) return candidate.items.filter(isRecord).slice(0, 50);
      if (candidate.rows && Array.isArray(candidate.rows)) return candidate.rows.filter(isRecord).slice(0, 50);
    }
  }
  return [];
}

function extractKpis(response: AgentResponse) {
  const source = response.tool_call?.result ?? response.data;
  if (!isRecord(source) || Array.isArray(source)) return [];
  return Object.entries(source)
    .filter(([, value]) => typeof value === "number" || typeof value === "string" || typeof value === "boolean")
    .slice(0, 8)
    .map(([label, value]) => ({ label, value: formatUnknown(value) }));
}

function normalizeQuickActions(response: AgentResponse, rows: RecordRow[], followUp: string): QuickAction[] {
  const existing = response.quick_actions ?? [];
  const byAction = new Map<string, QuickAction>();
  for (const action of existing) byAction.set(action.action, action);
  if (!byAction.has("view_chart") && (response.chart || rows.length > 1)) {
    byAction.set("view_chart", { action: "view_chart", label: "Xem biểu đồ", payload: {} });
  }
  byAction.set("export_result", { ...(byAction.get("export_result") ?? { action: "export_result", label: "Xuất kết quả", payload: {} }), label: "Xuất kết quả" });
  byAction.set("ask_followup", { ...(byAction.get("ask_followup") ?? { action: "ask_followup", label: "Hỏi tiếp", payload: { question: followUp } }), label: "Hỏi tiếp", payload: { question: followUp } });
  byAction.set("add_to_report", { action: "add_to_report", label: "Thêm vào report", payload: {} });
  byAction.set("explain_calculation", { action: "explain_calculation", label: "Giải thích cách tính", payload: {} });
  return Array.from(byAction.values());
}

function actionIcon(action: QuickAction["action"]) {
  if (action === "view_chart") return BarChart3;
  if (action === "export_result") return Download;
  if (action === "ask_followup") return MessageSquarePlus;
  if (action === "add_to_report") return FilePlus2;
  if (action === "explain_calculation") return HelpCircle;
  return Info;
}

function classifyError(response: AgentResponse): "backend" | "ollama" | "mapping" | "unclear" | "generic" {
  const text = `${response.answer} ${response.warnings.join(" ")} ${response.tool_call?.error ?? ""}`.toLowerCase();
  if (text.includes("failed to fetch") || text.includes("backend") || text.includes("network")) return "backend";
  if (text.includes("ollama") || text.includes("model") || text.includes("timeout")) return "ollama";
  if (text.includes("mapping") || text.includes("semantic") || text.includes("missing role")) return "mapping";
  if (text.includes("unclear") || text.includes("rephrase") || text.includes("cụ thể")) return "unclear";
  return "generic";
}

function buildTracePayload(response: AgentResponse) {
  return {
    plan: response.agent_plan,
    primary_tool: response.tool_call,
    tool_calls: response.tool_calls,
    timeline: response.execution_timeline,
    summary: response.result_summary,
    latency: response.latency,
    cache: response.cache,
    warnings: response.warnings,
  };
}

function inferWhyItMatters(toolName?: string, answer?: string) {
  const text = `${toolName ?? ""} ${answer ?? ""}`.toLowerCase();
  if (text.includes("cancel") || text.includes("risk") || text.includes("attrition")) {
    return "Các nhóm rủi ro cao là nơi nên ưu tiên kiểm tra nguyên nhân, chính sách vận hành hoặc dữ liệu thiếu.";
  }
  if (text.includes("margin") || text.includes("profit") || text.includes("loss")) {
    return "Doanh thu cao chưa đủ; margin/profit cho biết nhóm nào thật sự tạo giá trị kinh doanh.";
  }
  if (text.includes("missing") || text.includes("duplicate") || text.includes("quality")) {
    return "Chất lượng dữ liệu quyết định độ tin cậy của dashboard, metric và các câu trả lời tiếp theo.";
  }
  return "Insight này giúp bạn biết nên đào sâu vào nhóm nào trước thay vì đọc toàn bộ bảng dữ liệu thủ công.";
}

function inferNextQuestion(toolName?: string, rows: RecordRow[] = []) {
  const metric = pickMetricKey(rows) || "metric";
  const dimension = pickLabelKey(rows) || "category";
  const tool = (toolName || "").toLowerCase();
  if (tool.includes("category")) return "Category dẫn đầu có profit/margin tốt không?";
  if (tool.includes("state") || tool.includes("city")) return "Khu vực này có rủi ro hoặc missing data bất thường không?";
  if (tool.includes("missing")) return "Các cột missing nhiều có ảnh hưởng đến metric chính không?";
  return `${humanize(metric)} theo ${humanize(dimension)} thay đổi như thế nào nếu lọc top nhóm?`;
}

function pickLabelKey(rows: RecordRow[]) {
  const keys = Object.keys(rows[0] ?? {});
  return keys.find((key) => !isNumericColumn(rows, key)) ?? keys[0];
}

function pickMetricKey(rows: RecordRow[]) {
  const keys = Object.keys(rows[0] ?? {});
  const preferred = ["revenue", "sales", "profit", "margin", "amount", "qty", "orders", "cancel_rate", "rate", "count"];
  return keys.find((key) => preferred.some((token) => key.toLowerCase().includes(token)) && isNumericColumn(rows, key))
    ?? keys.find((key) => isNumericColumn(rows, key));
}

function isNumericColumn(rows: RecordRow[], key: string) {
  return rows.some((row) => toNumber(row[key]) !== null);
}

function toNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value.replace(/,/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function inferResultType(rows: RecordRow[], kpis: Array<{ label: string; value: string }>) {
  if (rows.length > 0) return "table/breakdown";
  if (kpis.length > 0) return "kpi";
  return "tool result";
}

function inferCacheState(cache?: Record<string, unknown>) {
  if (!cache) return null;
  const values = Object.values(cache);
  if (values.some((value) => String(value).toLowerCase().includes("hit") || value === true)) return "cache hit";
  if (values.length > 0) return "cache miss";
  return null;
}

function confidenceLabel(confidence: AnswerCard["confidence"]) {
  if (confidence === "high") return "Độ tin cậy cao";
  if (confidence === "medium") return "Độ tin cậy vừa";
  return "Cần kiểm tra thêm";
}

function summarizeObject(value: unknown) {
  if (!isRecord(value)) return formatUnknown(value);
  return Object.entries(value)
    .slice(0, 3)
    .map(([key, item]) => `${humanize(key)}: ${formatUnknown(item)}`)
    .join("; ");
}

function hasNaNish(rows: RecordRow[]) {
  return rows.some((row) =>
    Object.values(row).some((value) => value === null || value === undefined || (typeof value === "number" && Number.isNaN(value)))
  );
}

function isRecord(value: unknown): value is RecordRow {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function humanize(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatValue(value: number) {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  if (Math.abs(value) < 1 && value !== 0) return value.toFixed(3);
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatUnknown(value: unknown) {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "number") return formatValue(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
