import { useMemo, type FormEvent } from "react";
import { marked } from "marked";
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
import type { AgentResponse, AgentStatus, AnswerCard, DashboardResponse, RecordRow, SemanticProfile } from "../types";

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
  onOpenMapping?: () => void;
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
  onOpenMapping,
}: AskCopilotProps) {
  const { t } = useI18n();
  const { questions: suggestions, reason: suggestionReason } = useMemo(
    () => buildSuggestedQuestions(dashboard, dashboard?.semantic_profile || null, t),
    [dashboard, t]
  );
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
          <span className="copilot-status is-domain">{dashboard?.domain || "generic"}</span>
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
          {suggestionReason && (
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 italic">
              {suggestionReason}
            </p>
          )}
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
          <EmptyCopilotState
            disabled={disabled}
            suggestions={suggestions}
            onAskQuestion={onAskQuestion}
            suggestionReason={suggestionReason}
          />
        ) : (
          chatHistory.map((entry) => (
            <ChatMessage
              key={entry.id}
              entry={entry}
              timelineLabels={timelineLabels}
              onQuickAction={onQuickAction}
              onRetry={() => onAskQuestion(entry.question)}
              onAskQuestion={onAskQuestion}
              onOpenMapping={onOpenMapping}
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
  suggestionReason,
}: {
  disabled: boolean;
  suggestions: string[];
  onAskQuestion: (question: string) => void;
  suggestionReason?: string;
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
      {suggestionReason && (
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-4 italic text-center">
          {suggestionReason}
        </p>
      )}
    </div>
  );
}

function ChatMessage({
  entry,
  timelineLabels,
  onQuickAction,
  onRetry,
  onAskQuestion,
  onOpenMapping,
}: {
  entry: ChatEntry;
  timelineLabels: Array<{ key: string; label: string; icon: typeof Search }>;
  onQuickAction: (action: QuickAction, response: AgentResponse) => void;
  onRetry: () => void;
  onAskQuestion: (question: string) => void;
  onOpenMapping?: () => void;
}) {
  const { t } = useI18n();
  const response = entry.response;
  const rows = extractRows(response);
  const kpis = extractKpis(response);
  const timeline = buildTimeline(entry, timelineLabels);
  const readable = buildReadableAnswer(entry);
  const isWeakResult = entry.status !== "pending" && isWeakResultQuality(response);
  const hasResult = !isWeakResult && (rows.length > 0 || kpis.length > 0 || Boolean(response.chart));
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
            <span>{entry.status === "pending" ? t.ask.analyzing : entry.status === "error" ? t.ask.needsAttention : t.ask.groundedAnswer}</span>
          </div>
          <TrustBadges response={response} status={entry.status} />
        </header>

        <ExecutionTimeline timeline={timeline} status={entry.status} timelineLabels={timelineLabels} />

        {entry.status === "error" && errorType ? (
          <ErrorBubble
            type={errorType}
            answer={response.answer}
            onRetry={onRetry}
            onOpenMapping={onOpenMapping}
          />
        ) : isWeakResult ? (
          <InsufficientResultCard
            response={response}
            rows={rows}
            onRetry={onRetry}
            onAskQuestion={onAskQuestion}
            onOpenMapping={onOpenMapping}
          />
        ) : response.answer_card && entry.status !== "pending" ? (
          <AnswerCardRenderer card={response.answer_card} onAskQuestion={onAskQuestion} />
        ) : entry.status !== "pending" && isMarkdown(response.answer) ? (
          <div className="copilot-markdown-container p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
            <MarkdownAnswerRenderer markdown={response.answer} />
          </div>
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

        <details className="copilot-trace mt-4 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden text-xs">
          <summary className="flex items-center gap-1.5 p-2 bg-slate-50 dark:bg-slate-900/50 cursor-pointer list-none select-none hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors">
            <Info size={12} className="text-slate-500" />
            <span className="font-medium text-slate-700 dark:text-slate-300">Chi tiết kỹ thuật</span>
            <span className="text-[10px] text-slate-400 dark:text-slate-500">(Dành cho kiểm tra/debug)</span>
          </summary>
          <div className="p-3 bg-white dark:bg-slate-950 border-t border-slate-100 dark:border-slate-800 space-y-2.5 text-slate-600 dark:text-slate-300">
            {response.tool_call && (
              <div className="flex flex-col gap-0.5">
                <span className="font-semibold text-slate-700 dark:text-slate-200">Công cụ phân tích:</span>
                <code className="text-blue-600 dark:text-blue-400 bg-blue-50/50 dark:bg-blue-950/20 px-1.5 py-0.5 rounded font-mono w-max">{response.tool_call.tool_name}</code>
              </div>
            )}
            {response.tool_call?.arguments && Object.keys(response.tool_call.arguments).length > 0 && (
              <div className="flex flex-col gap-0.5">
                <span className="font-semibold text-slate-700 dark:text-slate-200">Đối số đầu vào (Arguments):</span>
                <pre className="bg-slate-50 dark:bg-slate-900 p-1.5 rounded font-mono overflow-auto max-h-40">{JSON.stringify(response.tool_call.arguments, null, 2)}</pre>
              </div>
            )}
            {response.latency && (
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-slate-700 dark:text-slate-200">Thời gian thực thi:</span>
                <span>
                  {Number(response.latency.total_ms || response.latency.execution_ms || 0).toFixed(0)}ms
                </span>
              </div>
            )}
            {response.cache && (
              <div className="flex flex-col gap-1">
                <span className="font-semibold text-slate-700 dark:text-slate-200 font-medium">Trạng thái Cache:</span>
                <div className="pl-3 text-[11px] font-mono text-slate-600 dark:text-slate-300">
                  <div>Semantic Cache: {response.cache.semantic_cache?.status || "n/a"} {response.cache.semantic_cache?.reason ? `(${response.cache.semantic_cache.reason})` : ""}</div>
                  <div>Tool Cache: {response.cache.tool_result_cache?.status || "n/a"}</div>
                </div>
              </div>
            )}
            {response.result_summary && (
              <div className="flex flex-col gap-0.5">
                <span className="font-semibold text-slate-700 dark:text-slate-200">Tóm tắt kết quả (Result Summary):</span>
                <pre className="bg-slate-50 dark:bg-slate-900 p-1.5 rounded font-mono overflow-auto max-h-40">{JSON.stringify(response.result_summary, null, 2)}</pre>
              </div>
            )}
            {response.result_quality && (
              <div className="flex flex-col gap-0.5">
                <span className="font-semibold text-slate-700 dark:text-slate-200">Chất lượng kết quả (Result Quality):</span>
                <pre className="bg-slate-50 dark:bg-slate-900 p-1.5 rounded font-mono overflow-auto max-h-40">{JSON.stringify(response.result_quality, null, 2)}</pre>
              </div>
            )}
            {response.warnings && response.warnings.length > 0 && (
              <div className="flex flex-col gap-0.5">
                <span className="font-semibold text-red-700 dark:text-red-400">Cảnh báo (Warnings):</span>
                <ul className="list-disc pl-4 space-y-0.5 text-red-600 dark:text-red-400">
                  {response.warnings.map((w, idx) => <li key={idx}>{w}</li>)}
                </ul>
              </div>
            )}
          </div>
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
  const { t } = useI18n();
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
        <span>{t.ask.mainConclusion}</span>
        <p>{answer.conclusion}</p>
      </section>
      <section>
        <span>{t.ask.evidence}</span>
        <p>{answer.evidence}</p>
      </section>
      <section>
        <span>{t.ask.whyItMatters}</span>
        <p>{answer.why}</p>
      </section>
      <section>
        <span>{t.ask.nextQuestion}</span>
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
  const { t } = useI18n();
  return (
    <div className="answer-card-v2">
      <section className="answer-card-hero">
        <div>
          <span>{t.ask.mainConclusion}</span>
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
        <span>{t.ask.whyItMatters}</span>
        <p>{card.why_it_matters}</p>
      </section>

      {card.recommended_next_questions.length > 0 && (
        <section className="answer-next-questions">
          <span>{t.ask.recommendedNext}</span>
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
            {t.ask.calculationSource}
          </summary>
          {card.data_warnings.length > 0 && (
            <div>
              <strong>{t.ask.dataWarnings}</strong>
              <ul>
                {card.data_warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
          {card.calculation_notes.length > 0 && (
            <div>
              <strong>{t.ask.calculationNotes}</strong>
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

function InsufficientResultCard({
  response,
  onRetry,
  onAskQuestion,
  onOpenMapping,
}: {
  response: AgentResponse;
  rows: RecordRow[];
  onRetry: () => void;
  onAskQuestion: (question: string) => void;
  onOpenMapping?: () => void;
}) {
  const quality = response.result_quality;
  const card = response.answer_card;
  const suggested = card?.recommended_next_questions?.length
    ? card.recommended_next_questions
    : ["Hãy tổng quan dataset này trước.", "Metric chính bạn muốn phân tích là gì?", "Bạn muốn breakdown theo cột nào?"];

  return (
    <div className="answer-card-v2 border-amber-200 dark:border-amber-900/60 bg-amber-50/40 dark:bg-amber-950/10">
      <section className="answer-card-hero">
        <div>
          <span>Trạng thái phân tích</span>
          <h3>{card?.headline || "Chưa đủ dữ liệu để kết luận"}</h3>
          <p>{card?.summary || "Công cụ đã chạy nhưng output chưa có metric, bảng hoặc nhóm nổi bật đủ rõ để tạo insight đáng tin."}</p>
        </div>
        <div className="answer-confidence is-low">
          <AlertTriangle size={13} />
          Cần kiểm tra thêm
        </div>
      </section>

      <section className="answer-evidence-grid">
        <div className="answer-evidence-card">
          <span>Công cụ đã chạy</span>
          <strong>{humanizeToolName(response.tool_call?.tool_name || response.tool_calls?.[0]?.tool_name || "none")}</strong>
          <p>Copilot không suy diễn số liệu khi tool result chưa đủ rõ.</p>
        </div>
        <div className="answer-evidence-card">
          <span>Lý do</span>
          <strong>{quality?.status === "empty" ? "Output rỗng" : quality?.status === "tool_error" ? "Tool lỗi" : "Evidence yếu"}</strong>
          <p>{quality?.reason || "Không tìm thấy metric/top item usable trong kết quả."}</p>
        </div>
        <div className="answer-evidence-card">
          <span>Số dòng usable</span>
          <strong>{quality?.row_count ?? response.result_summary?.row_count ?? 0}</strong>
          <p>Không render KPI/chart giả nếu kết quả không đủ cấu trúc.</p>
        </div>
      </section>

      <section className="answer-takeaways">
        <div className="answer-takeaway is-warning">
          <span>Không bịa insight</span>
          <p>Không có metric hoặc bảng rõ thì câu trả lời phải nói thật là chưa đủ cơ sở.</p>
        </div>
        <div className="answer-takeaway is-neutral">
          <span>Cách sửa nhanh</span>
          <p>Hỏi lại với metric và dimension cụ thể, hoặc chỉnh semantic mapping/data dictionary nếu cột bị hiểu sai.</p>
        </div>
      </section>

      {quality?.warnings?.length ? (
        <div className="copilot-warning-stack">
          {quality.warnings.map((warning) => (
            <div key={warning} className="copilot-warning">
              <AlertTriangle size={13} />
              <span>{warning}</span>
            </div>
          ))}
        </div>
      ) : null}

      <section className="answer-next-questions">
        <span>Nên hỏi tiếp</span>
        <div>
          {suggested.slice(0, 4).map((question) => (
            <button key={question} onClick={() => onAskQuestion(question)}>
              <MessageSquarePlus size={13} />
              {question}
            </button>
          ))}
        </div>
      </section>

      <div className="copilot-actions">
        <button onClick={onRetry}>
          <RefreshCw size={13} />
          Thử lại
        </button>
        {onOpenMapping && (
          <button onClick={onOpenMapping}>
            <Wand2 size={13} />
            Mở semantic mapping
          </button>
        )}
      </div>
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
          <strong>{translateResultType(response.result_summary?.result_type || inferResultType(rows, kpis), t)}</strong>
        </div>
        <span>{rows.length ? `${rows.length} ${t.ask.rowsLabel}` : `${kpis.length} ${t.ask.metricsLabel}`}</span>
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
    .map((row) => ({ label: String(row[labelKey] ?? "Không có dữ liệu"), value: toNumber(row[metricKey]) ?? 0 }));
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

  const semCache = response.cache?.semantic_cache;
  const toolCache = response.cache?.tool_result_cache;

  return (
    <div className="copilot-trust-badges flex flex-wrap items-center gap-1.5">
      <span>
        <ShieldCheck size={12} />
        {t.ask.basedOnTool}
      </span>
      <span>
        <Timer size={12} />
        {typeof totalMs === "number" ? `${Math.round(totalMs)}ms` : t.ask.latencyPending}
      </span>
      <span>{translateSource(source, t)}</span>

      {/* Semantic Cache Badge */}
      {semCache && (
        <span
          className={`group relative cursor-help inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold ${
            semCache.status === "hit"
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900/50"
              : semCache.status === "miss"
              ? "bg-slate-100 text-slate-600 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700/50"
              : semCache.status === "skipped"
              ? "bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/20 dark:text-amber-400 dark:border-amber-900/50"
              : "bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/20 dark:text-rose-400 dark:border-rose-900/50"
          }`}
        >
          Semantic Cache: {semCache.status.toUpperCase()}
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-50 rounded bg-slate-900 text-white text-[10px] p-2 shadow-lg w-48 whitespace-normal font-sans leading-normal">
            <div className="font-bold mb-0.5">Semantic Cache</div>
            <div>Trạng thái: <span className="font-bold">{semCache.status}</span></div>
            {semCache.similarity !== null && semCache.similarity !== undefined && (
              <div>Độ tương đồng: <span className="font-bold">{(semCache.similarity * 100).toFixed(0)}%</span></div>
            )}
            {semCache.reason && <div className="mt-1 text-slate-300 italic">{semCache.reason}</div>}
          </div>
        </span>
      )}

      {/* Tool Result Cache Badge */}
      {toolCache && (
        <span
          className={`group relative cursor-help inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold ${
            toolCache.status === "hit"
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900/50"
              : toolCache.status === "miss"
              ? "bg-slate-100 text-slate-600 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700/50"
              : toolCache.status === "skipped"
              ? "bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/20 dark:text-amber-400 dark:border-amber-900/50"
              : "bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/20 dark:text-rose-400 dark:border-rose-900/50"
          }`}
        >
          Tool Cache: {toolCache.status.toUpperCase()}
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-50 rounded bg-slate-900 text-white text-[10px] p-2 shadow-lg w-48 whitespace-normal font-sans leading-normal">
            <div className="font-bold mb-0.5">Tool Result Cache</div>
            <div>Trạng thái: <span className="font-bold">{toolCache.status}</span></div>
            <div className="mt-1 text-slate-300 italic">
              {toolCache.status === "hit"
                ? "Kết quả truy vấn công cụ được tái sử dụng từ cache để tối ưu tốc độ."
                : "Không tìm thấy kết quả công cụ tương ứng trong cache, đã tính toán mới."}
            </div>
          </div>
        </span>
      )}
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
        <strong>{humanizeToolName(toolName)}</strong>
      </div>
      <div>
        <span>{t.ask.calculationColumns}</span>
        <strong>{columns.length ? columns.join(", ") : t.ask.toolArgumentsOnly}</strong>
      </div>
      {(response.warnings.some((warning) => /missing|nan|null|partial/i.test(warning)) || hasNaNish(rows)) && (
        <div className="copilot-source-warning">
          <AlertTriangle size={12} />
          {t.ask.missingValueWarning}
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
  const { t } = useI18n();
  const followUp = response.answer_card?.recommended_next_questions?.[0] ?? buildReadableAnswer({ response, status: "done" }).next;
  const actions: QuickAction[] = normalizeQuickActions(response, rows, followUp, t);

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
            {t.ask.quickActions[action.action as keyof typeof t.ask.quickActions] ?? action.label}
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
  onOpenMapping,
}: {
  type: ReturnType<typeof classifyError>;
  answer: string;
  onRetry: () => void;
  onOpenMapping?: () => void;
}) {
  const { t } = useI18n();

  const copyMap: Record<
    ReturnType<typeof classifyError>,
    { title: string; body: string; diagnostic: string; actionText?: string; actionType?: "mapping" | "retry" | "fallback" }
  > = {
    backend: {
      title: "Không thể kết nối đến máy chủ",
      body: "Hệ thống không thể kết nối đến backend FastAPI. Vui lòng kiểm tra xem backend đã chạy ở cổng 8000 chưa.",
      diagnostic: "Lỗi: BACKEND_UNREACHABLE",
    },
    ollama: {
      title: "Dịch vụ LLM (Ollama) ngoại tuyến hoặc lỗi tải mô hình",
      body: "Mô hình ngôn ngữ Ollama chưa sẵn sàng. Bạn có thể sử dụng chế độ phân tích deterministic (không cần LLM giải thích).",
      diagnostic: "Lỗi: OLLAMA_OFFLINE",
      actionText: "Sử dụng fallback deterministic",
      actionType: "fallback",
    },
    timeout: {
      title: "Yêu cầu xử lý quá thời gian",
      body: "Thời gian xử lý câu hỏi vượt quá giới hạn. Hãy thử lại hoặc đặt câu hỏi đơn giản hơn.",
      diagnostic: "Lỗi: REQUEST_TIMEOUT",
    },
    mapping: {
      title: "Thiếu mapping vai trò ngữ nghĩa (Semantic mapping)",
      body: "Không tìm thấy các vai trò cột cần thiết (như date, target, revenue...) để trả lời câu hỏi này. Vui lòng cấu hình lại mapping.",
      diagnostic: "Lỗi: MISSING_SEMANTIC_MAPPING",
      actionText: "Mở Semantic Mapping Studio",
      actionType: "mapping",
    },
    invalid_args: {
      title: "Đối số công cụ phân tích không hợp lệ",
      body: "Agent truyền sai tên cột hoặc đối số khi chạy công cụ. Hãy kiểm tra Data Dictionary và kiểu dữ liệu của các cột.",
      diagnostic: "Lỗi: INVALID_TOOL_ARGUMENTS",
      actionText: "Kiểm tra Data Dictionary",
      actionType: "mapping",
    },
    incompatible: {
      title: "Dữ liệu không tương thích với phân tích yêu cầu",
      body: "Cột dữ liệu được chọn không khớp với yêu cầu của thuật toán (ví dụ: phân tích xu hướng thời gian nhưng cột date chứa null hoặc sai định dạng).",
      diagnostic: "Lỗi: DATASET_INCOMPATIBLE",
      actionText: "Kiểm tra kiểu dữ liệu",
      actionType: "mapping",
    },
    unclear: {
      title: "Câu hỏi chưa rõ ràng hoặc mơ hồ",
      body: "Agent không xác định được metric hoặc nhóm bạn muốn phân tích. Hãy sử dụng các mẫu câu hỏi gợi ý bên dưới.",
      diagnostic: "Lỗi: UNCLEAR_QUESTION",
    },
    generic: {
      title: "Gặp sự cố khi chạy phân tích dữ liệu",
      body: answer || "Đã xảy ra lỗi không xác định trong quá trình thực thi công cụ phân tích dữ liệu.",
      diagnostic: "Lỗi: GENERIC_EXECUTION_FAILURE",
    },
  };

  const copy = copyMap[type] || copyMap.generic;

  return (
    <div className="copilot-error-card p-4 rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50/50 dark:bg-red-950/10 flex gap-3 text-sm">
      <AlertTriangle className="text-red-500 shrink-0" size={20} />
      <div className="space-y-2.5 flex-1">
        <div>
          <div className="text-xs font-mono font-semibold text-red-600 dark:text-red-400 mb-0.5">
            {copy.diagnostic}
          </div>
          <strong className="text-slate-900 dark:text-slate-100 font-bold">{copy.title}</strong>
          <p className="text-slate-600 dark:text-slate-300 text-xs mt-1 leading-relaxed">{copy.body}</p>
        </div>

        {answer && type !== "generic" && (
          <div className="bg-white dark:bg-slate-950 p-2 rounded border border-red-100 dark:border-red-900/30 text-xs font-mono text-slate-500 max-h-24 overflow-auto">
            {answer}
          </div>
        )}

        <div className="flex flex-wrap gap-2 pt-1">
          <button
            onClick={onRetry}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
          >
            <RefreshCw size={12} />
            Thử lại câu hỏi
          </button>

          {copy.actionType === "mapping" && onOpenMapping && (
            <button
              onClick={onOpenMapping}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-950 text-white dark:bg-slate-700 dark:hover:bg-slate-600 rounded-lg text-xs font-semibold transition-all"
            >
              {copy.actionText}
            </button>
          )}

          {copy.actionType === "fallback" && (
            <button
              onClick={onRetry}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold transition-all"
            >
              {copy.actionText}
            </button>
          )}
        </div>
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
      evidence: "Đang chọn công cụ phân tích và chuẩn bị chạy trên dataset hiện tại.",
      why: "Bạn cần thấy hệ thống đang thực thi từng bước, không phải bị đứng.",
      next: "Đợi công cụ hoàn tất rồi xem phần xem nhanh kết quả.",
    };
  }

  return {
    conclusion: firstLine || "Copilot đã hoàn tất phân tích từ kết quả công cụ.",
    evidence: top
      ? `Kết quả nổi bật: ${top}${primaryValue !== undefined && primaryValue !== null ? `; ${humanize(metric)} = ${formatUnknown(primaryValue)}` : ""}.`
      : toolName
        ? `Công cụ ${humanizeToolName(toolName)} đã chạy và trả về ${summary?.row_count ?? rows.length ?? 0} dòng kết quả.`
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
      if (Array.isArray(candidate.result)) return candidate.result.filter(isRecord).slice(0, 50);
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
  if (isRecord(source.metrics) && Object.keys(source.metrics).length > 0) {
    return Object.entries(source.metrics)
      .filter(([, value]) => typeof value === "number" || typeof value === "string" || typeof value === "boolean")
      .slice(0, 8)
      .map(([label, value]) => ({ label, value: formatUnknown(value) }));
  }
  return Object.entries(source)
    .filter(([, value]) => typeof value === "number" || typeof value === "string" || typeof value === "boolean")
    .slice(0, 8)
    .map(([label, value]) => ({ label, value: formatUnknown(value) }));
}

function isWeakResultQuality(response: AgentResponse) {
  const quality = response.result_quality;
  if (!quality) return false;
  if (quality.status === "empty" || quality.status === "insufficient" || quality.status === "tool_error") return true;
  return quality.status === "partial" && (!quality.has_metric || !quality.has_label);
}

function normalizeQuickActions(
  response: AgentResponse,
  rows: RecordRow[],
  followUp: string,
  t: ReturnType<typeof useI18n>["t"],
): QuickAction[] {
  const existing = response.quick_actions ?? [];
  const byAction = new Map<string, QuickAction>();
  for (const action of existing) byAction.set(action.action, action);
  if (!byAction.has("view_chart") && (response.chart || rows.length > 1)) {
    byAction.set("view_chart", { action: "view_chart", label: t.ask.quickActions.view_chart, payload: {} });
  }
  byAction.set("export_result", { ...(byAction.get("export_result") ?? { action: "export_result", label: t.ask.quickActions.export_result, payload: {} }), label: t.ask.quickActions.export_result });
  byAction.set("ask_followup", { ...(byAction.get("ask_followup") ?? { action: "ask_followup", label: t.ask.quickActions.ask_followup, payload: { question: followUp } }), label: t.ask.quickActions.ask_followup, payload: { question: followUp } });
  byAction.set("add_to_report", { action: "add_to_report", label: t.ask.quickActions.add_to_report, payload: {} });
  byAction.set("explain_calculation", { action: "explain_calculation", label: t.ask.quickActions.explain_calculation, payload: {} });
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

function classifyError(response: AgentResponse): "backend" | "ollama" | "timeout" | "mapping" | "invalid_args" | "incompatible" | "unclear" | "generic" {
  const text = `${response.answer || ""} ${(response.warnings || []).join(" ")} ${response.tool_call?.error ?? ""}`.toLowerCase();
  if (text.includes("failed to fetch") || text.includes("backend") || text.includes("network") || text.includes("cannot reach backend")) {
    return "backend";
  }
  if (text.includes("timeout") || text.includes("gateway") || text.includes("quá thời gian")) {
    return "timeout";
  }
  if (text.includes("ollama") || text.includes("ollama unavailable") || text.includes("connection refused") || text.includes("model not loaded")) {
    return "ollama";
  }
  if (text.includes("mapping") || text.includes("semantic") || text.includes("missing role")) {
    return "mapping";
  }
  if (text.includes("column") || text.includes("arguments") || text.includes("invalid column") || text.includes("đối số không hợp lệ")) {
    return "invalid_args";
  }
  if (text.includes("incompatible") || text.includes("không tương thích") || text.includes("not supported")) {
    return "incompatible";
  }
  if (text.includes("unclear") || text.includes("rephrase") || text.includes("cụ thể") || text.includes("không rõ")) {
    return "unclear";
  }
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
  if (rows.length > 0) return "table";
  if (kpis.length > 0) return "kpi";
  return "tool_result";
}

function inferCacheState(cache: Record<string, unknown> | undefined, t: ReturnType<typeof useI18n>["t"]) {
  if (!cache) return null;
  const values = Object.values(cache);
  if (values.some((value) => String(value).toLowerCase().includes("hit") || value === true)) return t.ask.cacheHit;
  if (values.length > 0) return t.ask.cacheMiss;
  return null;
}

function translateSource(source: string, t: ReturnType<typeof useI18n>["t"]) {
  return t.ask.sourceLabels[source as keyof typeof t.ask.sourceLabels] ?? source.replace(/_/g, " ");
}

function translateResultType(type: string, t: ReturnType<typeof useI18n>["t"]) {
  return t.ask.resultTypes[type as keyof typeof t.ask.resultTypes] ?? type.replace(/_/g, " ");
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
  const normalized = value.replace(/[\s-]+/g, "_").toLowerCase();
  const labels: Record<string, string> = {
    metric: "chỉ số",
    rows: "số dòng",
    columns: "số cột",
    revenue: "doanh thu",
    sales: "doanh số",
    profit: "lợi nhuận",
    margin: "biên lợi nhuận",
    amount: "giá trị",
    qty: "số lượng",
    quantity: "số lượng",
    orders: "số đơn hàng",
    cancel_rate: "tỷ lệ hủy",
    attrition_rate: "tỷ lệ nghỉ việc",
    positive_rate: "tỷ lệ phản hồi",
    response_rate: "tỷ lệ phản hồi",
    missing_percent: "tỷ lệ thiếu dữ liệu",
    duplicate_rows: "số dòng trùng lặp",
    category: "nhóm sản phẩm",
    segment: "phân khúc",
    state: "bang/khu vực",
    city: "thành phố",
    country: "quốc gia",
    department: "phòng ban",
    job_role: "vai trò công việc",
    campaign: "chiến dịch",
    channel: "kênh",
    sku: "SKU",
  };
  return labels[normalized] ?? normalized.replace(/_/g, " ");
}

function humanizeToolName(value: string) {
  const labels: Record<string, string> = {
    none: "chưa có công cụ",
    multi_step: "phân tích nhiều bước",
    get_dataset_overview: "tổng quan dataset",
    get_missing_values: "kiểm tra dữ liệu thiếu",
    get_duplicate_rows: "kiểm tra dòng trùng lặp",
    groupby_aggregate: "tổng hợp theo nhóm",
    correlation_analysis: "phân tích tương quan",
    semantic_overview: "tổng quan semantic",
    semantic_kpis: "KPI semantic",
    semantic_time_series: "xu hướng theo thời gian",
    semantic_breakdown: "breakdown theo nhóm",
    semantic_target_summary: "tóm tắt target/conversion",
    get_sales_overview: "tổng quan bán hàng",
    revenue_by_month: "doanh thu theo tháng",
    revenue_by_category: "doanh thu theo category",
    top_states_by_revenue: "top khu vực theo doanh thu",
    top_skus_by_revenue: "top SKU theo doanh thu",
    category_cancellation_summary: "rủi ro hủy theo category",
    generate_chart_spec: "tạo biểu đồ",
  };
  return labels[value] ?? value.replace(/_/g, " ");
}

function formatValue(value: number) {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  if (Math.abs(value) < 1 && value !== 0) return value.toFixed(3);
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatUnknown(value: unknown) {
  if (value === null || value === undefined) return "Không có dữ liệu";
  if (typeof value === "number") return formatValue(value);
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function renderInline(tokens: any[]): React.ReactNode[] {
  if (!tokens) return [];
  return tokens.map((token: any, i: number) => {
    switch (token.type) {
      case "strong":
        return <strong key={i}>{token.text}</strong>;
      case "em":
        return <em key={i}>{token.text}</em>;
      case "codespan":
        return <code key={i} className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded text-xs">{token.text}</code>;
      case "link":
        return (
          <a key={i} href={token.href} target="_blank" rel="noreferrer" className="text-blue-500 hover:underline">
            {token.text}
          </a>
        );
      case "text":
      default:
        return token.text;
    }
  });
}

export function MarkdownAnswerRenderer({ markdown }: { markdown: string }) {
  if (!markdown) return null;
  const tokens = marked.lexer(markdown);

  return (
    <div className="markdown-answer space-y-3 text-slate-700 dark:text-slate-200">
      {tokens.map((token: any, index: number) => {
        switch (token.type) {
          case "heading": {
            const Tag = `h${Math.min(token.depth + 1, 6)}` as keyof JSX.IntrinsicElements;
            return (
              <Tag key={index} className="font-bold text-slate-800 dark:text-slate-100 mt-4 mb-2">
                {renderInline(token.tokens)}
              </Tag>
            );
          }
          case "paragraph":
            return (
              <p key={index} className="text-slate-600 dark:text-slate-300 leading-relaxed my-2">
                {renderInline(token.tokens)}
              </p>
            );
          case "list": {
            const Tag = token.ordered ? "ol" : "ul";
            return (
              <Tag key={index} className={`list-outside pl-5 my-2 space-y-1 ${token.ordered ? "list-decimal" : "list-disc"}`}>
                {token.items.map((item: any, i: number) => (
                  <li key={i} className="text-slate-600 dark:text-slate-300">
                    {renderInline(item.tokens)}
                  </li>
                ))}
              </Tag>
            );
          }
          case "space":
            return <div key={index} className="h-2" />;
          default:
            return (
              <div key={index} className="my-2">
                {token.text}
              </div>
            );
        }
      })}
    </div>
  );
}

function isMarkdown(text: string): boolean {
  return /[\*\#\_\[\]]/.test(text) || /\n\s*[-*+]\s+/.test(text) || /\n\s*\d+\.\s+/.test(text);
}

function buildSuggestedQuestions(
  dashboard: DashboardResponse | null,
  semanticProfile: SemanticProfile | null,
  t: any
): { questions: string[]; reason: string } {
  const domain = dashboard?.domain || "generic";
  const roles = semanticProfile?.roles || {};
  const activeRoles = Object.entries(roles)
    .filter(([, col]) => Boolean(col))
    .map(([role]) => role);

  const roleText = activeRoles.length > 0 ? ` và roles: ${activeRoles.join(", ")}` : "";
  const reason = `Gợi ý dựa trên domain: ${domain.toUpperCase()}${roleText}`;

  // Heuristics for filters based on active semantic roles:
  const hasRole = (role: string) => Boolean(roles[role]);

  let questions: string[] = [];

  switch (domain) {
    case "ecommerce":
      questions = [
        "SKU nào có doanh thu cao nhất?",
        "Category nào có tỷ lệ hủy cao?",
        "State nào doanh thu cao nhưng rủi ro hủy cũng cao?",
      ];
      break;
    case "retail":
      questions = [
        hasRole("revenue") && hasRole("profit") ? "Category nào sales cao nhưng profit thấp?" : "",
        "Segment nào có margin tốt nhất?",
        hasRole("profit") ? "Discount ảnh hưởng profit thế nào?" : "",
      ].filter(Boolean);
      break;
    case "marketing":
      questions = [
        "Campaign nào response tốt nhất?",
        "Response rate theo income band ra sao?",
        "Kênh mua hàng nào hiệu quả nhất?",
      ];
      break;
    case "hr":
      questions = [
        "Nhóm nào attrition risk cao?",
        hasRole("department") ? "Attrition theo overtime và department thế nào?" : "",
        hasRole("salary") ? "Income band nào có attrition rate cao?" : "",
      ].filter(Boolean);
      break;
    case "logistics":
      questions = [
        "Khu vực nào có số lượng sự kiện cao nhất?",
        hasRole("date") ? "Xu hướng theo tháng thay đổi thế nào?" : "",
        "Vehicle/transit mode nào nổi bật nhất?",
      ];
      break;
    case "finance":
      questions = [
        hasRole("date") ? "Profit/margin theo thời gian thế nào?" : "",
        hasRole("revenue") ? "Nhóm nào revenue cao nhưng margin thấp?" : "",
      ].filter(Boolean);
      break;
    default:
      questions = [];
  }

  // Fallback to generic/standard questions
  const genericQuestions = [
    "Cột nào thiếu dữ liệu nhiều nhất?",
    "Dataset này có duplicate rows không?",
    "Các cột numeric tương quan mạnh nhất là gì?",
  ];

  if (questions.length === 0) {
    questions = genericQuestions;
  } else {
    // Fill up to at least 3 questions if needed
    while (questions.length < 3) {
      const nextGen = genericQuestions.find(q => !questions.includes(q));
      if (!nextGen) break;
      questions.push(nextGen);
    }
  }

  return { questions: questions.slice(0, 5), reason };
}
