import { lazy, Suspense, useMemo, useState, useEffect, type ReactNode } from "react";

import {
  AlertTriangle,
  BarChart3,
  Bot,
  ChevronRight,
  Database,
  FileText,
  Gauge,
  LineChart,
  Loader2,
  Upload,
  Sparkles,
  TrendingUp,
  Activity,
  Terminal,
  ArrowUpRight,
  Copy,
  CheckCircle2,
  Download,
  Info,
  Layers3,
  ShieldCheck,
  Megaphone,
  Store,
  Users,
} from "lucide-react";
import {
  askAgent,
  askAgentStream,
  createMetric,
  deleteDataDictionary,
  deleteMetric,
  evaluateMetric,
  generateChart,
  getDataDictionary,
  getB2B,
  getCategoryCancellation,
  getCourier,
  getEcommerceOverview,
  getFulfilment,
  getPromotion,
  getReport,
  getRevenueBySize,
  getRevenueByCategory,
  getRevenueByMonth,
  getSummary,
  getStateCancellation,
  getTopCities,
  getTopSkus,
  getTopStates,
  getAgentStatus,
  getDashboard,
  getMetrics,
  resetSemanticOverrides,
  saveDataDictionary,
  saveSemanticOverrides,
  uploadCsv,
  uploadDataDictionary,
  updateMetric,
  listDatasets,
  type WorkspaceDataset,
} from "./api";
import { AskCopilot, type ChatEntry } from "./components/AskCopilot";
import { useI18n, type Language } from "./i18n";
import type { AgentResponse, AgentStatus, DashboardResponse, DataDictionary, DataDictionaryResponse, EcommerceOverview, MetricDefinition, MetricEvaluationResponse, RecordRow, Section, SemanticProfile, SummaryResponse, SummaryWrapper, UploadResponse } from "./types";

const Plot = lazy(() => import("react-plotly.js"));

type DashboardFigure = {
  title: string;
  note: string;
  data: unknown[];
  layout: Record<string, unknown>;
};

type DashboardInsight = {
  label: string;
  value: string;
  note: string;
  tone?: "risk";
};

export default function App() {
  const { t, language, setLanguage } = useI18n();
  const [section, setSection] = useState<Section>("upload");
  const [upload, setUpload] = useState<UploadResponse | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [ecommerce, setEcommerce] = useState<EcommerceOverview | null>(null);
  const [smartDashboard, setSmartDashboard] = useState<DashboardResponse | null>(null);
  const [dataDictionary, setDataDictionary] = useState<DataDictionaryResponse | null>(null);
  const [customMetrics, setCustomMetrics] = useState<MetricDefinition[]>([]);
  const [categoryRows, setCategoryRows] = useState<RecordRow[]>([]);
  const [monthRows, setMonthRows] = useState<RecordRow[]>([]);
  const [stateRows, setStateRows] = useState<RecordRow[]>([]);
  const [skuRows, setSkuRows] = useState<RecordRow[]>([]);
  const [sizeRows, setSizeRows] = useState<RecordRow[]>([]);
  const [categoryRiskRows, setCategoryRiskRows] = useState<RecordRow[]>([]);
  const [fulfilmentRows, setFulfilmentRows] = useState<RecordRow[]>([]);
  const [courierRows, setCourierRows] = useState<RecordRow[]>([]);
  const [promotionSummary, setPromotionSummary] = useState<SummaryWrapper["summary"] | null>(null);
  const [b2bSummary, setB2bSummary] = useState<SummaryWrapper["summary"] | null>(null);
  const [cityRows, setCityRows] = useState<RecordRow[]>([]);
  const [stateRiskRows, setStateRiskRows] = useState<RecordRow[]>([]);
  const [chart, setChart] = useState<{ data: unknown[]; layout: Record<string, unknown> } | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatEntry[]>([]);
  const [report, setReport] = useState("");
  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [availableDatasets, setAvailableDatasets] = useState<WorkspaceDataset[]>([]);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [questionDraft, setQuestionDraft] = useState("");

  const datasetId = upload?.dataset_id;

  const columns = summary?.columns ?? [];
  const navItems: Array<{ id: Section; label: string; icon: typeof Upload }> = useMemo(() => [
    { id: "upload", label: t.nav.upload, icon: Upload },
    { id: "overview", label: t.nav.overview, icon: Database },
    { id: "quality", label: t.nav.quality, icon: AlertTriangle },
    { id: "dashboard", label: t.nav.dashboard, icon: Activity },
    { id: "ecommerce", label: t.nav.ecommerce, icon: BarChart3 },
    { id: "charts", label: t.nav.charts, icon: LineChart },
    { id: "ask", label: t.nav.ask, icon: Bot },
    { id: "report", label: t.nav.report, icon: FileText },
  ], [t]);
  const sectionMeta = t.sections;

  async function refreshDataset(nextUpload: UploadResponse) {
    setLoading(t.app.messages.parsingDataset);
    setError("");
    setUpload(nextUpload);
    try {
      // 1. Fetch summary and dashboard contract first to determine domain
      const summaryData = await getSummary(nextUpload.dataset_id);
      setSummary(summaryData);

      const dashboardData = await getDashboard(nextUpload.dataset_id).catch(() => null);
      setSmartDashboard(dashboardData);
      const dictionaryData = await getDataDictionary(nextUpload.dataset_id).catch(() => null);
      setDataDictionary(dictionaryData);
      const metricsData = await getMetrics(nextUpload.dataset_id).catch(() => ({ metrics: [] }));
      setCustomMetrics(metricsData.metrics);

      // 2. Only fetch deep ecommerce endpoints if detected domain is "ecommerce"
      if (dashboardData && dashboardData.domain === "ecommerce") {
        const [
          ecommerceData,
          categoryData,
          monthData,
          stateData,
          skuData,
          sizeData,
          categoryRiskData,
          fulfilmentData,
          courierData,
          promotionData,
          b2bData,
          cityData,
          stateRiskData,
        ] = await Promise.all([
          getEcommerceOverview(nextUpload.dataset_id).catch(() => null),
          getRevenueByCategory(nextUpload.dataset_id).catch(() => ({ items: [] })),
          getRevenueByMonth(nextUpload.dataset_id).catch(() => ({ items: [] })),
          getTopStates(nextUpload.dataset_id).catch(() => ({ items: [] })),
          getTopSkus(nextUpload.dataset_id).catch(() => ({ items: [] })),
          getRevenueBySize(nextUpload.dataset_id).catch(() => ({ items: [] })),
          getCategoryCancellation(nextUpload.dataset_id).catch(() => ({ items: [] })),
          getFulfilment(nextUpload.dataset_id).catch(() => ({ items: [] })),
          getCourier(nextUpload.dataset_id).catch(() => ({ items: [] })),
          getPromotion(nextUpload.dataset_id).catch(() => ({ summary: null })),
          getB2B(nextUpload.dataset_id).catch(() => ({ summary: null })),
          getTopCities(nextUpload.dataset_id).catch(() => ({ items: [] })),
          getStateCancellation(nextUpload.dataset_id).catch(() => ({ items: [] })),
        ]);

        setEcommerce(ecommerceData);
        setCategoryRows(categoryData.items);
        setMonthRows(monthData.items);
        setStateRows(stateData.items);
        setSkuRows(skuData.items);
        setSizeRows(sizeData.items);
        setCategoryRiskRows(categoryRiskData.items);
        setFulfilmentRows(fulfilmentData.items);
        setCourierRows(courierData.items);
        setPromotionSummary(promotionData.summary);
        setB2bSummary(b2bData.summary);
        setCityRows(cityData.items);
        setStateRiskRows(stateRiskData.items);
      } else {
        // Reset ecommerce states for non-ecommerce domains
        setEcommerce(null);
        setCategoryRows([]);
        setMonthRows([]);
        setStateRows([]);
        setSkuRows([]);
        setSizeRows([]);
        setCategoryRiskRows([]);
        setFulfilmentRows([]);
        setCourierRows([]);
        setPromotionSummary(null);
        setB2bSummary(null);
        setCityRows([]);
        setStateRiskRows([]);
      }

      setSection("overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.app.messages.loadDetailsFailed);
    } finally {
      setLoading("");
    }
  }

  async function handleUpload(file: File) {
    try {
      setLoading(t.app.messages.uploadingData);
      setError("");
      const uploaded = await uploadCsv(file);
      await refreshDataset(uploaded);
      const { datasets } = await listDatasets();
      setAvailableDatasets(datasets);
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.uploadFailed);
    }
  }

  async function handleSelectDataset(ds: WorkspaceDataset) {
    try {
      setLoading(`${t.app.messages.switchingWorkspace} ${ds.filename}...`);
      setError("");
      const mockUpload: UploadResponse = {
        dataset_id: ds.dataset_id,
        filename: ds.filename,
        rows: 0,
        columns: 0,
        message: "Switched"
      };
      setUpload(mockUpload);
      await refreshDataset(mockUpload);
      setLoading("");
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.switchDatasetFailed);
    }
  }

  useEffect(() => {
    async function initWorkspace() {
      try {
        const [datasetResponse, statusResponse] = await Promise.all([
          listDatasets(),
          getAgentStatus().catch(() => null),
        ]);
        const { datasets } = datasetResponse;
        setAgentStatus(statusResponse);
        setAvailableDatasets(datasets);
        if (datasets.length > 0) {
          const first = datasets[datasets.length - 1];
          setLoading(t.app.messages.restoringWorkspace);
          const mockUpload: UploadResponse = {
            dataset_id: first.dataset_id,
            filename: first.filename,
            rows: 0,
            columns: 0,
            message: "Restored"
          };
          setUpload(mockUpload);
          await refreshDataset(mockUpload);
          setLoading("");
        }
      } catch (err) {
        console.error("Workspace restore failed:", err);
      }
    }
    initWorkspace();

    // Poll Ollama status every 30 seconds
    const statusInterval = setInterval(async () => {
      try {
        const status = await getAgentStatus();
        setAgentStatus(status);
      } catch {
        // silently ignore polling errors
      }
    }, 30_000);
    return () => clearInterval(statusInterval);
  }, []);


  async function handleChart(formData: FormData) {
    if (!datasetId) return;
    try {
      setLoading(t.app.messages.chartSpec);
      setError("");
      const payload = {
        dataset_id: datasetId,
        chart_type: String(formData.get("chart_type")),
        x: String(formData.get("x")),
        y: String(formData.get("y") || "") || undefined,
      };
      const result = await generateChart(payload);
      setChart(result.chart);
      setLoading("");
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.chartFailed);
    }
  }

  async function handleAsk(formData: FormData) {
    await submitQuestion(String(formData.get("question") || ""));
  }

  async function submitQuestion(question: string) {
    if (!datasetId) return;
    if (!question.trim()) return;
    const chatId = crypto.randomUUID();
    setChatHistory((prev) => [
      ...prev,
      {
        id: chatId,
        question,
        status: "pending",
        response: {
          answer: "Đang chọn tool phù hợp và chạy phân tích deterministic...",
          tool_call: null,
          data: null,
          chart: null,
          warnings: [],
        },
      },
    ]);
    try {
      setLoading(t.app.messages.agentStreaming);
      setError("");
      const result = await askAgentStream(datasetId, question, (event, payload) => {
        if (event === "progress") {
          const message = String(payload.message || payload.step || "Agent is working...");
          setChatHistory((prev) =>
            prev.map((item) =>
              item.id === chatId
                ? { ...item, response: { ...item.response, answer: message } }
                : item
            )
          );
        }
        if (event === "plan") {
          const steps = Array.isArray(payload.steps) ? payload.steps.length : 1;
          setChatHistory((prev) =>
            prev.map((item) =>
              item.id === chatId
                ? { ...item, response: { ...item.response, answer: `Đã chọn plan ${steps} bước, đang chạy tool...`, agent_plan: payload } }
                : item
            )
          );
        }
        if (event === "tool_started") {
          setChatHistory((prev) =>
            prev.map((item) =>
              item.id === chatId
                ? { ...item, response: { ...item.response, answer: `Đang chạy ${String(payload.tool_name)}...` } }
                : item
            )
          );
        }
        if (event === "explanation_started") {
          setChatHistory((prev) =>
            prev.map((item) =>
              item.id === chatId
                ? { ...item, response: { ...item.response, answer: "Đang viết câu trả lời từ kết quả tool..." } }
                : item
            )
          );
        }
      }).catch(async () => askAgent(datasetId, question));
      setChatHistory((prev) =>
        prev.map((item) =>
          item.id === chatId ? { ...item, status: "done", response: result } : item
        )
      );
      setLoading("");
    } catch (err) {
      setLoading("");
      const message = err instanceof Error ? err.message : "Agent failed";
      setChatHistory((prev) =>
        prev.map((item) =>
          item.id === chatId
            ? {
                ...item,
                status: "error",
                response: {
                  answer: `Mình chưa chạy được câu hỏi này: ${message}`,
                  tool_call: {
                    tool_name: "none",
                    arguments: {},
                    result: null,
                    error: message,
                  },
                  data: null,
                  chart: null,
                  warnings: [message],
                },
              }
            : item
        )
      );
    }
  }

  function handleQuickAction(action: NonNullable<AgentResponse["quick_actions"]>[number], response: AgentResponse) {
    if (action.action === "ask_followup") {
      setQuestionDraft(String(action.payload.question || ""));
      return;
    }
    if (action.action === "export_result") {
      downloadAgentResult(response.tool_call?.result ?? response.data ?? response.tool_calls ?? response, "agent_tool_result.json");
      return;
    }
    if (action.action === "view_chart" && response.chart) {
      setChart(response.chart);
      setSection("charts");
      return;
    }
    if (action.action === "add_to_report") {
      const snippet = buildAgentReportSnippet(response);
      setReport((prev) => (prev.trim() ? `${prev}\n\n${snippet}` : snippet));
      setSection("report");
      return;
    }
    if (action.action === "explain_calculation") {
      const toolName = response.tool_call?.tool_name || response.tool_calls?.[0]?.tool_name || "tool vừa chạy";
      const args = response.tool_call?.arguments || response.tool_calls?.[0]?.arguments || {};
      setQuestionDraft(`Giải thích cách tính của ${toolName} với các tham số ${JSON.stringify(args)} bằng ngôn ngữ dễ hiểu.`);
    }
  }

  async function handleSaveSemanticOverrides(payload: { domain?: string | null; roles: Record<string, string | null> }) {
    if (!datasetId) return;
    try {
      setLoading(t.app.messages.savingSemantic);
      setError("");
      await saveSemanticOverrides(datasetId, payload);
      const dashboardData = await getDashboard(datasetId);
      setSmartDashboard(dashboardData);
      setLoading("");
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.saveSemanticFailed);
    }
  }

  async function handleResetSemanticOverrides() {
    if (!datasetId) return;
    try {
      setLoading(t.app.messages.resettingSemantic);
      setError("");
      await resetSemanticOverrides(datasetId);
      const dashboardData = await getDashboard(datasetId);
      setSmartDashboard(dashboardData);
      setLoading("");
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.resetSemanticFailed);
    }
  }

  async function refreshDictionaryDrivenViews() {
    if (!datasetId) return;
    const [dictionaryData, dashboardData, metricsData] = await Promise.all([
      getDataDictionary(datasetId).catch(() => null),
      getDashboard(datasetId).catch(() => null),
      getMetrics(datasetId).catch(() => ({ metrics: [] })),
    ]);
    setDataDictionary(dictionaryData);
    setSmartDashboard(dashboardData);
    setCustomMetrics(metricsData.metrics);
  }

  async function refreshMetricDrivenViews() {
    if (!datasetId) return;
    const [metricsData, dashboardData] = await Promise.all([
      getMetrics(datasetId).catch(() => ({ metrics: [] })),
      getDashboard(datasetId).catch(() => null),
    ]);
    setCustomMetrics(metricsData.metrics);
    setSmartDashboard(dashboardData);
  }

  async function handleUploadDataDictionary(file: File) {
    if (!datasetId) return;
    try {
      setLoading(t.app.messages.uploadingDictionary);
      setError("");
      const response = await uploadDataDictionary(datasetId, file);
      setDataDictionary(response);
      await refreshDictionaryDrivenViews();
      setLoading("");
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.uploadDictionaryFailed);
    }
  }

  async function handleSaveDataDictionary(dictionary: DataDictionary) {
    if (!datasetId) return;
    try {
      setLoading(t.app.messages.savingDictionary);
      setError("");
      const response = await saveDataDictionary(datasetId, dictionary);
      setDataDictionary(response);
      await refreshDictionaryDrivenViews();
      setLoading("");
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.saveDictionaryFailed);
    }
  }

  async function handleDeleteDataDictionary() {
    if (!datasetId) return;
    try {
      setLoading(t.app.messages.deletingDictionary);
      setError("");
      await deleteDataDictionary(datasetId);
      await refreshDictionaryDrivenViews();
      setLoading("");
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.deleteDictionaryFailed);
    }
  }

  async function handleSaveMetric(metric: MetricDefinition, previousName?: string | null) {
    if (!datasetId) return;
    try {
      setLoading(t.app.messages.savingMetric);
      setError("");
      if (previousName && previousName !== metric.name) {
        await deleteMetric(datasetId, previousName).catch(() => null);
        await createMetric(datasetId, metric);
      } else if (previousName) {
        await updateMetric(datasetId, previousName, metric);
      } else {
        await createMetric(datasetId, metric);
      }
      await refreshMetricDrivenViews();
      setLoading("");
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.saveMetricFailed);
    }
  }

  async function handleDeleteMetric(metricName: string) {
    if (!datasetId) return;
    try {
      setLoading(t.app.messages.deletingMetric);
      setError("");
      await deleteMetric(datasetId, metricName);
      await refreshMetricDrivenViews();
      setLoading("");
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.deleteMetricFailed);
    }
  }

  async function handleEvaluateMetric(metricName: string): Promise<MetricEvaluationResponse | null> {
    if (!datasetId) return null;
    try {
      setLoading(t.app.messages.evaluatingMetric);
      setError("");
      const result = await evaluateMetric(datasetId, metricName);
      setLoading("");
      return result;
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.evaluateMetricFailed);
      return null;
    }
  }

  async function handleReport() {
    if (!datasetId) return;
    try {
      setLoading(t.app.messages.generatingReport);
      setError("");
      const result = await getReport(datasetId);
      setReport(result.report_markdown);
      setLoading("");
    } catch (err) {
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.reportFailed);
    }
  }

  const copyToClipboard = () => {
    if (!report) return;
    navigator.clipboard.writeText(report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadReport = () => {
    if (!report) return;
    const element = document.createElement("a");
    const file = new Blob([report], { type: "text/markdown" });
    element.href = URL.createObjectURL(file);
    element.download = `${upload?.filename.replace(".csv", "")}_intelligence_report.md`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const currentSection = sectionMeta[section];
  const domainLabel = smartDashboard?.domain ? smartDashboard.domain : "not profiled";
  const datasetLabel = upload?.filename || "No active dataset";

  return (
    <div className="min-h-screen overflow-x-hidden text-slate-800 font-sans antialiased" style={{background: '#f0f4f8'}}>
      <div className="workspace-grid pointer-events-none fixed inset-0 z-0" />
      {/* ── Sidebar ───────────────────────────────────────────────── */}
      <aside
        className="glass-sidebar fixed inset-y-0 left-0 z-30 flex flex-col"
        style={{ width: 'var(--sidebar-w)', padding: '18px 14px' }}
      >
        {/* Logo mark */}
        <div className="doppelrand mb-6">
          <div className="doppelrand-inner flex items-center gap-3 px-3 py-3">
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px]"
              style={{
                background: 'linear-gradient(135deg, #1e40af 0%, #2563eb 100%)',
                boxShadow: '0 4px 12px rgba(37,99,235,0.35), inset 0 1px 0 rgba(255,255,255,0.15)'
              }}
            >
              <Sparkles className="text-white" style={{ width: 15, height: 15 }} />
            </div>
            <div>
              <div className="text-[13px] font-bold tracking-tight text-slate-900">{t.app.brand}</div>
              <div className="section-label mt-0.5">{t.app.product}</div>
            </div>
          </div>
        </div>

        {/* Dataset pill */}
        {upload && (
          <div
            className="mb-5 flex items-center gap-2 rounded-[10px] px-3 py-2"
            style={{ background: 'rgba(37,99,235,0.06)', border: '1px solid rgba(37,99,235,0.14)' }}
          >
            <div className="live-dot live-dot-green shrink-0" />
            <div className="min-w-0">
              <p className="section-label">{t.app.activeFile}</p>
              <p className="mt-0.5 truncate text-[12px] font-semibold text-slate-800">{upload.filename}</p>
            </div>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 space-y-0.5 overflow-y-auto">
          {navItems
            .filter((item) => {
              if (item.id === "ecommerce") return smartDashboard?.domain === "ecommerce";
              return true;
            })
            .map((item) => {
              const Icon = item.icon;
              const active = section === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setSection(item.id)}
                  className={`nav-item ${active ? 'active' : ''}`}
                >
                  <span className="nav-icon">
                    <Icon style={{ width: 13, height: 13 }} />
                  </span>
                  <span className="flex-1 text-left text-[13px]">{item.label}</span>
                  {active && (
                    <span
                      className="h-1.5 w-1.5 shrink-0 rounded-full"
                      style={{ background: 'rgba(255,255,255,0.6)' }}
                    />
                  )}
                </button>
              );
            })}
        </nav>

        {/* System status */}
        <div className="mt-auto border-t pt-4" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2.5 px-2 py-2">
            <ShieldCheck style={{ width: 13, height: 13, color: '#10b981', flexShrink: 0 }} />
            <div className="min-w-0">
              <p className="section-label">{t.app.backendApi}</p>
              <p className="mt-0.5 text-[11px] font-semibold text-slate-600">
                {agentStatus?.ollama_available ? 'AI + Deterministic' : 'Deterministic Mode'}
              </p>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main Workspace ─────────────────────────────────────────── */}
      <main
        className="relative z-10 min-h-screen"
        style={{ marginLeft: 'var(--sidebar-w)', padding: '20px 28px 40px' }}
      >
        {/* Page header */}
        <header className="glass-panel mb-6 rounded-[16px] px-6 py-5">
          <div className="flex items-start justify-between gap-6">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="badge badge-slate">{currentSection.eyebrow}</span>
                {agentStatus?.ollama_available
                  ? <span className="badge badge-green"><span className="live-dot live-dot-green" style={{width:5,height:5,animation:'none'}} />{t.app.aiReady}</span>
                  : <span className="badge badge-amber">{t.app.deterministic}</span>
                }
                {upload && <span className="badge badge-blue"><Database style={{width:9,height:9}} />{upload.filename}</span>}
                {upload && (
                  <span className="badge badge-slate">
                    <Gauge style={{width:9,height:9}} />
                    {upload.rows.toLocaleString()} {t.app.rows}
                  </span>
                )}
                {smartDashboard?.domain && (
                  <span className="badge badge-blue" style={{textTransform:'capitalize'}}>
                    <Layers3 style={{width:9,height:9}} />
                    {smartDashboard.domain}
                  </span>
                )}
              </div>
              <h1 className="text-2xl font-black tracking-tight text-slate-950">{currentSection.title}</h1>
              <p className="mt-1 text-[12px] leading-relaxed text-slate-500 max-w-2xl">{currentSection.subtitle}</p>
            </div>
            <div className="shrink-0">
              {loading ? (
                <div
                  className="flex items-center gap-2 rounded-[10px] px-4 py-2 text-[11px] font-semibold animate-pulse"
                  style={{ background: 'rgba(37,99,235,0.08)', color: '#2563eb', border: '1px solid rgba(37,99,235,0.2)' }}
                >
                  <Loader2 className="animate-spin" style={{ width: 13, height: 13 }} />
                  {loading}
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <LanguageToggle language={language} setLanguage={setLanguage} />
                  <OllamaStatusBadge status={agentStatus} />
                </div>
              )}
            </div>
          </div>
        </header>

        {error && (
          <div
            className="mb-5 flex items-start gap-3 rounded-[12px] px-4 py-3.5 animate-fade-up"
            style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)' }}
          >
            <AlertTriangle style={{ width: 15, height: 15, color: '#dc2626', flexShrink: 0, marginTop: 1 }} />
            <div>
              <strong className="text-[12px] font-bold text-rose-900 block mb-0.5">{t.app.errorTitle}</strong>
              <span className="text-[11px] text-rose-700">{error}</span>
            </div>
          </div>
        )}

        {/* Tab Sections render */}
        <div>
          {section === "upload" && (
            <UploadSection
              onUpload={handleUpload}
              upload={upload}
              availableDatasets={availableDatasets}
              onSelectDataset={handleSelectDataset}
            />
          )}

          {section === "overview" && <OverviewSection summary={summary} ecommerce={ecommerce} />}
          {section === "quality" && <QualitySection summary={summary} ecommerce={ecommerce} />}
          {section === "dashboard" && (
            <SmartDashboardSection
              dashboard={smartDashboard}
              dataDictionary={dataDictionary}
              customMetrics={customMetrics}
              columns={columns}
              onAskQuestion={submitQuestion}
              onSaveSemanticOverrides={handleSaveSemanticOverrides}
              onResetSemanticOverrides={handleResetSemanticOverrides}
              onUploadDataDictionary={handleUploadDataDictionary}
              onSaveDataDictionary={handleSaveDataDictionary}
              onDeleteDataDictionary={handleDeleteDataDictionary}
              onSaveMetric={handleSaveMetric}
              onDeleteMetric={handleDeleteMetric}
              onEvaluateMetric={handleEvaluateMetric}
            />
          )}
          {section === "ecommerce" && (
            <EcommerceSection
              ecommerce={ecommerce}
              categoryRows={categoryRows}
              monthRows={monthRows}
              stateRows={stateRows}
              skuRows={skuRows}
              sizeRows={sizeRows}
              categoryRiskRows={categoryRiskRows}
              fulfilmentRows={fulfilmentRows}
              courierRows={courierRows}
              promotionSummary={promotionSummary}
              b2bSummary={b2bSummary}
              cityRows={cityRows}
              stateRiskRows={stateRiskRows}
            />
          )}
          {section === "charts" && (
            <ChartsSection
              columns={columns}
              chart={chart}
              onSubmit={handleChart}
              disabled={!datasetId}
              ecommerce={ecommerce}
              categoryRows={categoryRows}
              monthRows={monthRows}
              stateRows={stateRows}
              skuRows={skuRows}
              sizeRows={sizeRows}
              categoryRiskRows={categoryRiskRows}
              fulfilmentRows={fulfilmentRows}
              promotionSummary={promotionSummary}
              cityRows={cityRows}
              stateRiskRows={stateRiskRows}
            />
          )}
          {section === "ask" && (
            <AskCopilot
              onAsk={handleAsk}
              onAskQuestion={submitQuestion}
              onQuickAction={handleQuickAction}
              chatHistory={chatHistory}
              disabled={!datasetId}
              clearHistory={() => setChatHistory([])}
              agentStatus={agentStatus}
              questionDraft={questionDraft}
              setQuestionDraft={setQuestionDraft}
              dashboard={smartDashboard}
            />
          )}

          {section === "report" && (
            <ReportSection
              report={report}
              onGenerate={handleReport}
              disabled={!datasetId}
              copy={copyToClipboard}
              download={downloadReport}
              copied={copied}
            />
          )}
        </div>
      </main>
    </div>
  );
}

// ─── Ollama Status Badge ───────────────────────────────────────────────────

function OllamaStatusBadge({ status }: { status: AgentStatus | null }) {
  if (!status) {
    return (
      <div className="flex items-center gap-2 rounded-[10px] border px-3 py-1.5 text-[11px]" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
        <div className="live-dot live-dot-slate" />
        <span className="font-mono font-semibold">Đang kiểm tra AI...</span>
      </div>
    );
  }

  const isReady = status.ollama_available && (status.model_loaded || status.router_model_loaded);
  const isPartial = status.ollama_available && !isReady;

  if (isReady) {
    return (
      <div
        className="group relative flex items-center gap-2 rounded-[10px] border px-3 py-1.5 text-[11px] cursor-default"
        style={{ background: '#f0fdf4', borderColor: '#bbf7d0', color: '#16a34a' }}
        title={`Model: ${status.model} | Router: ${status.router_model}`}
      >
        <div className="live-dot live-dot-green" />
        <span className="font-mono font-bold">AI sẵn sàng</span>
        <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block z-50 rounded-[10px] px-3 py-2 shadow-xl whitespace-nowrap text-[10px]" style={{ background: '#0f172a', color: '#f1f5f9' }}>
          <div className="font-bold mb-1">Ollama đang chạy</div>
          <div>Model: <span style={{ color: '#4ade80' }}>{status.model}</span></div>
          <div>Router: <span style={{ color: '#4ade80' }}>{status.router_model}</span></div>
        </div>
      </div>
    );
  }

  if (isPartial) {
    return (
      <div className="flex items-center gap-2 rounded-[10px] border px-3 py-1.5 text-[11px]" style={{ background: '#fffbeb', borderColor: '#fde68a', color: '#d97706' }}>
        <div className="live-dot live-dot-amber" />
        <span className="font-mono font-bold">Đang tải model</span>
      </div>
    );
  }

  return (
    <div
      className="group relative flex items-center gap-2 rounded-[10px] border px-3 py-1.5 text-[11px] cursor-default"
      style={{ background: '#fffbeb', borderColor: '#fde68a', color: '#d97706' }}
      title="Run: ollama serve && ollama pull qwen2.5:7b"
    >
      <div className="live-dot live-dot-amber" />
      <span className="font-mono font-bold">Chế độ deterministic</span>
      <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block z-50 rounded-[10px] px-3 py-2 shadow-xl whitespace-nowrap text-[10px]" style={{ background: '#0f172a', color: '#f1f5f9' }}>
        <div className="font-bold mb-1">Chưa có diễn giải từ AI</div>
        <div style={{ color: '#94a3b8' }}>Số liệu vẫn được tính chính xác bằng Pandas.</div>
        <div className="mt-1" style={{ color: '#fbbf24' }}>Chạy: ollama serve</div>
      </div>
    </div>
  );
}

function LanguageToggle({ language, setLanguage }: { language: Language; setLanguage: (language: Language) => void }) {
  return (
    <div
      className="flex items-center gap-1 rounded-[10px] border bg-white p-1 text-[10px] font-bold shadow-sm"
      style={{ borderColor: 'var(--border)' }}
      aria-label="Language switcher"
    >
      {(["vi", "en"] as Language[]).map((option) => (
        <button
          key={option}
          onClick={() => setLanguage(option)}
          className={`rounded-[7px] px-2.5 py-1 transition-all ${language === option ? "bg-slate-950 text-white" : "text-slate-500 hover:bg-slate-100"}`}
        >
          {option.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

// ---------------------- SUBSECTIONS ----------------------

function UploadSection({
  onUpload,
  upload,
  availableDatasets,
  onSelectDataset,
}: {
  onUpload: (file: File) => void;
  upload: UploadResponse | null;
  availableDatasets: WorkspaceDataset[];
  onSelectDataset: (ds: WorkspaceDataset) => void;
}) {
  const sampleDomains = [
    { icon: Store, label: 'Bán lẻ / Ecommerce', desc: 'Sales, đơn hàng, SKU, revenue theo category', color: 'rgba(37,99,235,0.08)', border: 'rgba(37,99,235,0.18)' },
    { icon: Users, label: 'Nhân sự / Attrition', desc: 'Nhân viên, lương, attrition rate, phòng ban', color: 'rgba(16,185,129,0.07)', border: 'rgba(16,185,129,0.2)' },
    { icon: Megaphone, label: 'Marketing', desc: 'Campaign, phân khúc khách hàng, conversion', color: 'rgba(245,158,11,0.07)', border: 'rgba(245,158,11,0.22)' },
  ];

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      {/* Drop zone - Double-Bezel */}
      <div className="doppelrand">
        <div className="doppelrand-inner">
          <label className="drop-zone flex flex-col items-center" style={{ cursor: 'pointer' }}>
            <div
              className="mb-4 flex h-14 w-14 items-center justify-center rounded-[14px]"
              style={{
                background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
                border: '1px solid rgba(37,99,235,0.2)',
                boxShadow: '0 4px 16px rgba(37,99,235,0.1)'
              }}
            >
              <Upload style={{ width: 22, height: 22, color: '#2563eb' }} />
            </div>
            <h3 className="text-[15px] font-bold text-slate-900 tracking-tight">Thả file dữ liệu vào đây</h3>
            <p className="mt-2 text-[12px] text-slate-500 max-w-xs text-center leading-relaxed">
              Hỗ trợ .csv, .xls và .xlsx. Engine sẽ phân tích semantic và dựng dashboard tự động.
            </p>
            <div
              className="mt-5 btn-primary"
              style={{ pointerEvents: 'none' }}
            >
              <Upload style={{ width: 13, height: 13 }} />
              Chọn file dữ liệu
              <span
                className="ml-1 flex h-5 w-5 items-center justify-center rounded-full"
                style={{ background: 'rgba(255,255,255,0.15)' }}
              >
                <ArrowUpRight style={{ width: 10, height: 10 }} />
              </span>
            </div>
            <input
              type="file"
              accept=".csv,.xls,.xlsx"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onUpload(file);
              }}
            />
          </label>
        </div>
      </div>

      {/* Active file confirmation */}
      {upload && (
        <div
          className="flex items-center justify-between rounded-[14px] px-4 py-3.5 animate-fade-up"
          style={{
            background: 'rgba(16,185,129,0.06)',
            border: '1px solid rgba(16,185,129,0.2)',
            boxShadow: '0 2px 8px rgba(16,185,129,0.08)'
          }}
        >
          <div className="flex items-center gap-3">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-[8px]"
              style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.2)' }}
            >
              <CheckCircle2 style={{ width: 15, height: 15, color: '#10b981' }} />
            </div>
            <div>
              <p className="section-label" style={{ color: '#059669' }}>File đã được đọc thành công</p>
              <p className="text-[13px] font-semibold text-slate-800 mt-0.5">{upload.filename}</p>
            </div>
          </div>
          <div className="flex gap-5 text-right font-mono">
            <div>
              <p className="section-label">Dòng</p>
              <p className="text-[13px] font-bold text-slate-700 mt-0.5">{upload.rows.toLocaleString()}</p>
            </div>
            <div>
              <p className="section-label">Cột</p>
              <p className="text-[13px] font-bold text-slate-700 mt-0.5">{upload.columns.toLocaleString()}</p>
            </div>
          </div>
        </div>
      )}

      {/* Sample domain cards */}
      <div className="panel-shell">
        <p className="section-label mb-3">Domain dữ liệu được hỗ trợ</p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {sampleDomains.map((d) => {
            const Icon = d.icon;
            return (
              <div
                key={d.label}
                className="rounded-[12px] p-3.5"
                style={{ background: d.color, border: `1px solid ${d.border}` }}
              >
                <Icon style={{ width: 18, height: 18, marginBottom: 8, color: 'var(--accent)' }} />
                <p className="text-[12px] font-bold text-slate-800">{d.label}</p>
                <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{d.desc}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Dataset history */}
      {availableDatasets.length > 0 && (
        <div className="panel-shell">
          <p className="section-label mb-3">Lịch sử dataset trong workspace</p>
          <div className="space-y-1.5">
            {availableDatasets.map((ds) => {
              const isActive = upload?.dataset_id === ds.dataset_id;
              return (
                <button
                  key={ds.dataset_id}
                  onClick={() => onSelectDataset(ds)}
                  className="w-full flex items-center justify-between rounded-[10px] px-3.5 py-2.5 text-left transition-all"
                  style={{
                    background: isActive ? 'rgba(37,99,235,0.06)' : 'var(--surface-2)',
                    border: `1px solid ${isActive ? 'rgba(37,99,235,0.22)' : 'var(--border)'}`,
                  }}
                >
                  <div className="flex items-center gap-2.5">
                    <Database
                      style={{ width: 13, height: 13, color: isActive ? '#2563eb' : '#94a3b8', flexShrink: 0 }}
                    />
                    <span className="text-[12px] font-semibold text-slate-800">{ds.filename}</span>
                  </div>
                  <span className="section-label" style={{ color: isActive ? '#2563eb' : 'var(--text-muted)' }}>
                    {isActive ? 'Đang dùng' : 'Khôi phục'}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}


function OverviewSection({ summary, ecommerce }: { summary: SummaryResponse | null; ecommerce: EcommerceOverview | null }) {
  if (!summary) return <EmptyState />;
  return (
    <div className="space-y-6">
      <MetricGrid
        items={[
          ["Số dòng", summary.shape.rows.toLocaleString(), "Bản ghi trong dataset", Database],
          ["Số cột", summary.shape.columns.toLocaleString(), "Header/biến dữ liệu", Activity],
          ["Dòng trùng lặp", summary.duplicate_rows.toLocaleString(), "Dòng lặp giống nhau", AlertTriangle],
          [
            "Tổng doanh thu",
            ecommerce ? formatNumber(ecommerce.overview.total_revenue) : "N/A",
            "Tổng giá trị cộng dồn",
            TrendingUp,
          ],
        ]}
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <Panel
            title="Từ điển header"
            subtitle="Danh sách cột, biến cấu trúc và kiểu dữ liệu được hệ thống suy luận."
          >
            <DataTable rows={Object.entries(summary.column_types).map(([column, type]) => ({ Cột: column, "Kiểu suy luận": type }))} />
          </Panel>
        </div>

        <div className="xl:col-span-1">
          <Panel
            title="Gợi ý hướng phân tích"
            subtitle="Các hướng phân tích tự động dựa trên cấu trúc dataset hiện tại."
          >
            <div className="space-y-2.5 mt-2">
              {summary.recommendations.map((item, idx) => (
                <div
                  key={item}
                  className="rounded-lg bg-slate-50 border border-slate-100 p-3 hover:bg-slate-100/50 transition-colors flex gap-2.5"
                >
                  <span className="w-5 h-5 rounded bg-indigo-100 text-indigo-700 flex items-center justify-center flex-shrink-0 text-[10px] font-mono font-bold">
                    {idx + 1}
                  </span>
                  <p className="text-xs text-slate-600 leading-relaxed font-medium">{item}</p>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function QualitySection({ summary, ecommerce }: { summary: SummaryResponse | null; ecommerce: EcommerceOverview | null }) {
  if (!summary) return <EmptyState />;
  const missingRows = Object.keys(summary.missing_values).map((column) => ({
    Cột: column,
    "Số giá trị thiếu": summary.missing_values[column].toLocaleString(),
    "Tỷ lệ thiếu": asPercent(summary.missing_percent[column] / 100),
  }));
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel
          title="Kiểm tra độ đầy đủ của biến"
          subtitle="Tỷ lệ missing values theo từng cột trong dataset."
        >
          <DataTable rows={missingRows} />
        </Panel>

        <Panel
          title="Cảnh báo sức khỏe dữ liệu"
          subtitle="Các warning về dữ liệu, business anomaly hoặc cấu trúc có thể ảnh hưởng phân tích."
        >
          {(ecommerce?.data_quality.warnings.length ?? 0) > 0 ? (
            <div className="space-y-2 max-h-[450px] overflow-y-auto pr-1">
              {ecommerce!.data_quality.warnings.map((warning, index) => (
                <div
                  key={index}
                  className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 flex gap-2 text-xs leading-relaxed text-amber-800"
                >
                  <AlertTriangle className="text-amber-600 flex-shrink-0 mt-0.5" size={14} />
                  <div>
                    <span className="text-[9px] font-mono text-amber-700 font-bold block uppercase tracking-wider">
                      Cảnh báo #{index + 1}
                    </span>
                    <p className="mt-0.5">{warning}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3">
                <CheckCircle2 size={20} />
              </div>
              <p className="text-xs font-semibold text-slate-800">Dữ liệu chưa có cảnh báo lớn</p>
              <p className="text-[11px] text-slate-400 mt-1 max-w-xs leading-relaxed">
                Hệ thống chưa phát hiện warning cấu trúc hoặc nghịch lý metric rõ ràng.
              </p>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}

function SmartDashboardSection({
  dashboard,
  dataDictionary,
  customMetrics,
  columns,
  onAskQuestion,
  onSaveSemanticOverrides,
  onResetSemanticOverrides,
  onUploadDataDictionary,
  onSaveDataDictionary,
  onDeleteDataDictionary,
  onSaveMetric,
  onDeleteMetric,
  onEvaluateMetric,
}: {
  dashboard: DashboardResponse | null;
  dataDictionary: DataDictionaryResponse | null;
  customMetrics: MetricDefinition[];
  columns: string[];
  onAskQuestion: (question: string) => void;
  onSaveSemanticOverrides: (payload: { domain?: string | null; roles: Record<string, string | null> }) => void;
  onResetSemanticOverrides: () => void;
  onUploadDataDictionary: (file: File) => void;
  onSaveDataDictionary: (dictionary: DataDictionary) => void;
  onDeleteDataDictionary: () => void;
  onSaveMetric: (metric: MetricDefinition, previousName?: string | null) => Promise<void>;
  onDeleteMetric: (metricName: string) => Promise<void>;
  onEvaluateMetric: (metricName: string) => Promise<MetricEvaluationResponse | null>;
}) {
  const [domainDraft, setDomainDraft] = useState("");
  const [roleDraft, setRoleDraft] = useState<Record<string, string>>({});
  const [dictionaryDraft, setDictionaryDraft] = useState<DataDictionary>({ domain: null, fields: [] });
  const emptyMetricDraft: MetricDefinition = {
    name: "",
    label: "",
    description: "",
    expression: "",
    format: "number",
    aggregation: "mean",
    required_roles: [],
    higher_is_better: true,
  };
  const [metricDraft, setMetricDraft] = useState<MetricDefinition>(emptyMetricDraft);
  const [editingMetricName, setEditingMetricName] = useState<string | null>(null);
  const [metricPreview, setMetricPreview] = useState<MetricEvaluationResponse | null>(null);

  useEffect(() => {
    if (!dashboard) return;
    setDomainDraft(dashboard.semantic_profile.overrides?.domain || dashboard.domain);
    setRoleDraft(Object.fromEntries(Object.entries(dashboard.semantic_profile.roles).map(([role, match]) => [role, match.column])));
    const currentDictionary = dataDictionary?.dictionary;
    const fieldsByColumn = new Map((currentDictionary?.fields || []).map((field) => [field.column_name, field]));
    const dictionaryColumns = columns.length > 0 ? columns : Array.from(new Set([
      ...Object.values(dashboard.semantic_profile.roles).map((match) => match.column),
      ...dashboard.semantic_profile.unmatched_columns,
    ]));
    setDictionaryDraft({
      domain: currentDictionary?.domain || dashboard.domain,
      fields: dictionaryColumns.map((column) => ({
        column_name: column,
        business_name: fieldsByColumn.get(column)?.business_name || "",
        description: fieldsByColumn.get(column)?.description || "",
        semantic_role: fieldsByColumn.get(column)?.semantic_role || "",
        data_type: fieldsByColumn.get(column)?.data_type || "",
        unit: fieldsByColumn.get(column)?.unit || "",
        aggregation: fieldsByColumn.get(column)?.aggregation || "",
        sensitive: fieldsByColumn.get(column)?.sensitive || false,
        allowed_values: fieldsByColumn.get(column)?.allowed_values || [],
      })),
    });
  }, [dashboard, dataDictionary, columns]);

  if (!dashboard) return <EmptyState message="Hãy upload dataset để tạo dashboard thông minh từ backend." />;
  const candidateRoles = Object.keys(dashboard.semantic_profile.candidates || dashboard.semantic_profile.roles).sort();
  const allColumns = Array.from(new Set([
    ...Object.values(dashboard.semantic_profile.roles).map((match) => match.column),
    ...Object.values(dashboard.semantic_profile.candidates || {}).flat().map((candidate) => candidate.column),
    ...dashboard.semantic_profile.unmatched_columns,
  ])).filter((column): column is string => Boolean(column));
  const domainOptions = ["ecommerce", "retail", "marketing", "hr", "finance", "logistics", "education", "survey", "product", "generic"];
  const roleOptions = ["", "revenue", "cost", "profit", "margin", "discount", "date", "category", "segment", "quantity", "city", "state", "country", "customer", "campaign", "channel", "employee", "department", "job_role", "salary", "target", "conversion", "overtime", "tenure", "recency", "monetary", "frequency"];
  const dataTypeOptions = ["", "string", "number", "date", "boolean", "categorical"];
  const aggregationOptions = ["", "sum", "mean", "count", "min", "max", "median"];
  const metricFormatOptions: MetricDefinition["format"][] = ["number", "percent", "currency", "integer"];
  const metricAggregationOptions: MetricDefinition["aggregation"][] = ["mean", "sum", "median", "min", "max", "count"];
  const expressionTokens = Array.from(new Set([
    ...Object.keys(dashboard.semantic_profile.roles),
    ...allColumns.map(toMetricExpressionToken),
  ])).filter(Boolean).slice(0, 28);

  function updateDictionaryField(index: number, key: keyof DataDictionary["fields"][number], value: unknown) {
    setDictionaryDraft((prev) => ({
      ...prev,
      fields: prev.fields.map((field, fieldIndex) =>
        fieldIndex === index ? { ...field, [key]: value } : field
      ),
    }));
  }

  function selectMetric(metric: MetricDefinition) {
    setEditingMetricName(metric.name);
    setMetricDraft({
      ...metric,
      label: metric.label || "",
      description: metric.description || "",
      required_roles: metric.required_roles || [],
    });
    setMetricPreview(null);
  }

  function resetMetricDraft() {
    setEditingMetricName(null);
    setMetricDraft(emptyMetricDraft);
    setMetricPreview(null);
  }

  async function saveMetricDraft() {
    await onSaveMetric(
      {
        ...metricDraft,
        name: metricDraft.name.trim(),
        label: metricDraft.label?.trim() || metricDraft.name.trim(),
        description: metricDraft.description?.trim() || null,
        expression: metricDraft.expression.trim(),
        required_roles: metricDraft.required_roles.filter(Boolean),
      },
      editingMetricName,
    );
    resetMetricDraft();
  }

  async function evaluateMetricDraft() {
    const metricName = editingMetricName || metricDraft.name.trim();
    if (!metricName) return;
    const result = await onEvaluateMetric(metricName);
    if (result) setMetricPreview(result);
  }

  async function deleteSelectedMetric() {
    if (!editingMetricName) return;
    await onDeleteMetric(editingMetricName);
    resetMetricDraft();
  }

  return (
    <div className="space-y-6">
      <div className="overflow-hidden rounded-lg border border-slate-200/80 bg-slate-950 p-5 text-white shadow-[0_20px_60px_rgba(15,23,42,0.18)]">
        <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-center">
        <div>
          <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-emerald-300">Domain được phát hiện</div>
          <h2 className="mt-1 text-2xl font-black capitalize tracking-tight text-white">{dashboard.domain}</h2>
          <p className="mt-1 text-[11px] text-slate-300">
            Contract v{dashboard.contract_version ?? 1} · Độ tin cậy {Math.round((dashboard.semantic_profile.domain_confidence ?? 0.5) * 100)}% · Cache {String(dashboard.cache?.dashboard ?? "n/a")}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-right">
          <MiniMeta label="Vai trò" value={String(Object.keys(dashboard.semantic_profile.roles).length)} />
          <MiniMeta label="Biểu đồ" value={String(dashboard.charts.length)} />
          <MiniMeta label="Dataset" value={dashboard.dataset_id.slice(0, 8)} />
        </div>
        </div>
      </div>

      {dashboard.warnings.length > 0 && (
        <div className="space-y-2">
          {dashboard.warnings.map((warning) => (
            <div key={warning} className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
              {warning}
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {dashboard.kpi_cards.map((card) => (
          <div key={card.label} className="kpi-card">
            <div className="section-label mb-2">{card.label}</div>
            <div className="text-[22px] font-black tracking-tight text-slate-950">{card.value}</div>
            <p className="mt-1.5 line-clamp-2 text-[10px] leading-relaxed text-slate-500">{card.description}</p>
          </div>
        ))}
      </div>

      {dashboard.insight_cards.length > 0 && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          {dashboard.insight_cards.map((card) => (
            <div
              key={`${card.title}-${card.value || card.finding}`}
              className={`insight-card ${card.tone === 'risk' ? 'tone-risk' : 'tone-neutral'}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="section-label" style={{ color: card.tone === 'risk' ? '#dc2626' : 'var(--accent)' }}>
                  {card.title}
                </div>
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ background: card.tone === 'risk' ? '#ef4444' : 'var(--accent)' }}
                />
              </div>
              <div className="mt-2 text-[13px] font-extrabold leading-snug text-slate-950">{card.finding || card.value}</div>
              {card.evidence && (
                <p
                  className="mt-2 rounded-[8px] px-2.5 py-1.5 text-[11px] font-semibold text-slate-600"
                  style={{ background: 'rgba(255,255,255,0.7)', border: '1px solid rgba(255,255,255,0.8)' }}
                >
                  {card.evidence}
                </p>
              )}
              <p className="mt-2 text-[12px] leading-relaxed text-slate-600">{card.why_it_matters || card.narrative}</p>
              {card.recommended_next_question && (
                <button
                  onClick={() => onAskQuestion(card.recommended_next_question!)}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-[8px] px-3 py-1.5 text-[10px] font-bold text-slate-700 transition-all"
                  style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
                >
                  <Bot style={{ width: 11, height: 11, color: 'var(--accent)' }} />
                  Hỏi câu này
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 2xl:grid-cols-2">
        {dashboard.charts.map((item) => (
          <ChartPanel
            key={`${item.id || item.title}-${item.description}`}
            title={item.title}
            note={item.description}
            figure={{ title: item.title, note: item.description, data: item.chart.data, layout: item.chart.layout }}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 2xl:grid-cols-2">
        {dashboard.tables.map((table) => (
          <Panel key={table.id || table.title} title={table.title} subtitle={table.description}>
            <DataTable rows={table.rows} />
          </Panel>
        ))}
      </div>

      <Panel title="Metric Builder" subtitle="Định nghĩa metric business dùng lại được từ semantic roles hoặc cột numeric.">
        <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
          <div className="space-y-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Metric đã lưu</div>
              <div className="mt-3 space-y-2">
                {customMetrics.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-slate-300 bg-white p-3 text-[11px] leading-relaxed text-slate-500">
                    Chưa có custom metric. Hãy thử `margin = profit / revenue` cho dataset retail/finance.
                  </div>
                ) : (
                  customMetrics.map((metric) => (
                    <button
                      key={metric.name}
                      onClick={() => selectMetric(metric)}
                      className={`w-full rounded-lg border px-3 py-2 text-left shadow-sm transition ${editingMetricName === metric.name ? "border-indigo-300 bg-indigo-50" : "border-slate-200 bg-white hover:border-slate-300"}`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold text-slate-800">{metric.label || metric.name}</span>
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[9px] font-bold uppercase text-slate-500">{metric.format}</span>
                      </div>
                      <div className="mt-1 font-mono text-[10px] text-slate-500">{metric.expression}</div>
                    </button>
                  ))
                )}
              </div>
            </div>

            <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-3 text-[11px] leading-relaxed text-indigo-800">
              Expression được chạy bằng safe AST engine. Cho phép: roles, cột numeric, hằng số, +, -, *, / và hàm an toàn `sum`, `mean`, `count`, `safe_div`.
            </div>
          </div>

          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Tên metric
                <input
                  value={metricDraft.name}
                  onChange={(event) => setMetricDraft((prev) => ({ ...prev, name: event.target.value }))}
                  placeholder="margin"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs font-mono text-slate-700"
                />
              </label>
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Nhãn hiển thị
                <input
                  value={metricDraft.label || ""}
                  onChange={(event) => setMetricDraft((prev) => ({ ...prev, label: event.target.value }))}
                  placeholder="Margin"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700"
                />
              </label>
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Định dạng
                <select
                  value={metricDraft.format}
                  onChange={(event) => setMetricDraft((prev) => ({ ...prev, format: event.target.value as MetricDefinition["format"] }))}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700"
                >
                  {metricFormatOptions.map((format) => <option key={format} value={format}>{format}</option>)}
                </select>
              </label>
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Cách tổng hợp
                <select
                  value={metricDraft.aggregation}
                  onChange={(event) => setMetricDraft((prev) => ({ ...prev, aggregation: event.target.value as MetricDefinition["aggregation"] }))}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700"
                >
                  {metricAggregationOptions.map((aggregation) => <option key={aggregation} value={aggregation}>{aggregation}</option>)}
                </select>
              </label>
            </div>

            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Công thức
              <input
                value={metricDraft.expression}
                onChange={(event) => setMetricDraft((prev) => ({ ...prev, expression: event.target.value }))}
                placeholder="profit / revenue"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-xs text-slate-700"
              />
            </label>

            <div className="grid gap-3 lg:grid-cols-[1fr_220px]">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Mô tả
                <input
                  value={metricDraft.description || ""}
                  onChange={(event) => setMetricDraft((prev) => ({ ...prev, description: event.target.value }))}
                  placeholder="Profit divided by revenue"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700"
                />
              </label>
              <label className="flex items-end gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={metricDraft.higher_is_better}
                  onChange={(event) => setMetricDraft((prev) => ({ ...prev, higher_is_better: event.target.checked }))}
                />
                Giá trị cao là tốt hơn
              </label>
            </div>

            <div>
              <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">Role bắt buộc</div>
              <div className="flex flex-wrap gap-2">
                {roleOptions.filter(Boolean).map((role) => (
                  <button
                    key={`metric-role-${role}`}
                    type="button"
                    onClick={() => setMetricDraft((prev) => ({
                      ...prev,
                      required_roles: prev.required_roles.includes(role)
                        ? prev.required_roles.filter((item) => item !== role)
                        : [...prev.required_roles, role],
                    }))}
                    className={`rounded-lg border px-2 py-1 text-[10px] font-semibold ${metricDraft.required_roles.includes(role) ? "border-indigo-300 bg-indigo-50 text-indigo-700" : "border-slate-200 bg-white text-slate-500 hover:border-slate-300"}`}
                  >
                    {role}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-[1fr_auto_auto_auto]">
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] leading-relaxed text-slate-600">
                Role khả dụng: {Object.keys(dashboard.semantic_profile.roles).slice(0, 10).join(", ") || "không có"}.
                <br />
                Cột numeric cũng có thể dùng trực tiếp nếu tên cột là identifier hợp lệ.
              </div>
              <button
                onClick={saveMetricDraft}
                disabled={!metricDraft.name.trim() || !metricDraft.expression.trim()}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-[10px] font-bold text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                Lưu metric
              </button>
              <button
                onClick={evaluateMetricDraft}
                disabled={!editingMetricName && !customMetrics.some((metric) => metric.name === metricDraft.name.trim())}
                className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-[10px] font-bold text-slate-600 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300"
              >
                Đánh giá
              </button>
              <button
                onClick={resetMetricDraft}
                className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-[10px] font-bold text-slate-600 shadow-sm hover:bg-slate-50"
              >
                Tạo mới
              </button>
            </div>

            {editingMetricName && (
              <button
                onClick={deleteSelectedMetric}
                className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-[10px] font-bold text-rose-700 hover:bg-rose-100"
              >
                Xóa `{editingMetricName}`
              </button>
            )}

            {metricPreview && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-3">
                <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-700">Xem trước kết quả</div>
                <DataTable rows={[metricPreview.summary]} />
              </div>
            )}

            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">Gợi ý token cho công thức</div>
              <div className="flex flex-wrap gap-2">
                {expressionTokens.map((token) => (
                  <button
                    key={`token-${token}`}
                    type="button"
                    onClick={() => setMetricDraft((prev) => ({ ...prev, expression: `${prev.expression}${prev.expression ? " " : ""}${token}` }))}
                    className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 font-mono text-[10px] text-slate-600 hover:border-indigo-200 hover:text-indigo-700"
                  >
                    {token}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="Data Dictionary" subtitle="Mô tả ý nghĩa cột bằng business name, semantic role, data type, unit và sensitivity flag.">
        <div className="mb-4 grid gap-3 lg:grid-cols-[1fr_auto_auto]">
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] leading-relaxed text-slate-600">
            Nguồn: <span className="font-semibold text-slate-800">{dataDictionary?.source || "none"}</span>
            {(dataDictionary?.warnings || []).length > 0 && (
              <div className="mt-1 text-amber-700">{dataDictionary!.warnings.join(" · ")}</div>
            )}
          </div>
          <label className="flex cursor-pointer items-center justify-center rounded-lg border border-slate-200 bg-white px-3 py-2 text-[10px] font-bold text-slate-600 shadow-sm hover:bg-slate-50">
            Upload CSV/JSON
            <input
              type="file"
              accept=".csv,.json"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onUploadDataDictionary(file);
                event.currentTarget.value = "";
              }}
            />
          </label>
          <button
            onClick={onDeleteDataDictionary}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-[10px] font-bold text-slate-600 shadow-sm hover:bg-slate-50"
          >
            Xóa dictionary
          </button>
        </div>

        <div className="mb-4 grid gap-3 md:grid-cols-[180px_1fr_auto]">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Domain trong dictionary
            <select
              value={dictionaryDraft.domain || ""}
              onChange={(event) => setDictionaryDraft((prev) => ({ ...prev, domain: event.target.value || null }))}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs text-slate-700"
            >
              <option value="">Tự động</option>
              {domainOptions.map((domain) => (
                <option key={domain} value={domain}>{domain}</option>
              ))}
            </select>
          </label>
          <div className="rounded-lg border border-indigo-100 bg-indigo-50/50 px-3 py-2 text-[11px] leading-relaxed text-indigo-800">
            Mapping từ dictionary được ưu tiên hơn auto-detection. Semantic override thủ công vẫn có ưu tiên cao nhất.
          </div>
          <button
            onClick={() => onSaveDataDictionary({
              domain: dictionaryDraft.domain || null,
              fields: dictionaryDraft.fields.filter((field) =>
                field.business_name || field.description || field.semantic_role || field.data_type || field.unit || field.aggregation || field.sensitive || field.allowed_values.length > 0
              ),
            })}
            className="rounded-lg bg-indigo-600 px-3 py-2 text-[10px] font-bold text-white shadow-sm hover:bg-indigo-700"
          >
            Lưu dictionary
          </button>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-[1180px] w-full divide-y divide-slate-200 text-left text-[11px]">
            <thead className="bg-slate-50 text-[9px] font-bold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-3 py-2">Cột</th>
                <th className="px-3 py-2">Tên business</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Kiểu</th>
                <th className="px-3 py-2">Unit</th>
                <th className="px-3 py-2">Tổng hợp</th>
                <th className="px-3 py-2">Nhạy cảm</th>
                <th className="px-3 py-2">Giá trị hợp lệ</th>
                <th className="px-3 py-2">Mô tả</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {dictionaryDraft.fields.map((field, index) => (
                <tr key={field.column_name}>
                  <td className="px-3 py-2 font-mono text-[10px] font-semibold text-slate-700">{field.column_name}</td>
                  <td className="px-3 py-2">
                    <input
                      value={field.business_name || ""}
                      onChange={(event) => updateDictionaryField(index, "business_name", event.target.value)}
                      className="w-full rounded-md border border-slate-200 px-2 py-1 text-[11px]"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={field.semantic_role || ""}
                      onChange={(event) => updateDictionaryField(index, "semantic_role", event.target.value)}
                      className="w-full rounded-md border border-slate-200 px-2 py-1 text-[11px]"
                    >
                      {roleOptions.map((role) => (
                        <option key={`${field.column_name}-${role || "none"}`} value={role}>{role || "Không chọn"}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={field.data_type || ""}
                      onChange={(event) => updateDictionaryField(index, "data_type", event.target.value)}
                      className="w-full rounded-md border border-slate-200 px-2 py-1 text-[11px]"
                    >
                      {dataTypeOptions.map((dataType) => (
                        <option key={`${field.column_name}-${dataType || "auto"}`} value={dataType}>{dataType || "Tự động"}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <input
                      value={field.unit || ""}
                      onChange={(event) => updateDictionaryField(index, "unit", event.target.value)}
                      className="w-full rounded-md border border-slate-200 px-2 py-1 text-[11px]"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={field.aggregation || ""}
                      onChange={(event) => updateDictionaryField(index, "aggregation", event.target.value)}
                      className="w-full rounded-md border border-slate-200 px-2 py-1 text-[11px]"
                    >
                      {aggregationOptions.map((aggregation) => (
                        <option key={`${field.column_name}-${aggregation || "none"}`} value={aggregation}>{aggregation || "Không chọn"}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <input
                      type="checkbox"
                      checked={field.sensitive}
                      onChange={(event) => updateDictionaryField(index, "sensitive", event.target.checked)}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      value={(field.allowed_values || []).join("|")}
                      onChange={(event) => updateDictionaryField(index, "allowed_values", event.target.value.split("|").map((item) => item.trim()).filter(Boolean))}
                      placeholder="A|B|C"
                      className="w-full rounded-md border border-slate-200 px-2 py-1 text-[11px]"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      value={field.description || ""}
                      onChange={(event) => updateDictionaryField(index, "description", event.target.value)}
                      className="w-full rounded-md border border-slate-200 px-2 py-1 text-[11px]"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Semantic Mapping Studio" subtitle="Kiểm tra và chỉnh lại business roles khi auto mapper đoán chưa đúng.">
        <div className="mb-4 grid gap-3 md:grid-cols-[180px_1fr_auto_auto]">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Domain
            <select
              value={domainDraft}
              onChange={(event) => setDomainDraft(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs text-slate-700"
            >
              {["ecommerce", "retail", "marketing", "hr", "finance", "generic"].map((domain) => (
                <option key={domain} value={domain}>{domain}</option>
              ))}
            </select>
          </label>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] text-slate-600">
            {(dashboard.semantic_profile.domain_reasons || []).join(" · ") || "Domain was inferred from semantic roles."}
          </div>
          <button
            onClick={() => onSaveSemanticOverrides({ domain: domainDraft, roles: roleDraft })}
            className="rounded-lg bg-indigo-600 px-3 py-2 text-[10px] font-bold text-white shadow-sm hover:bg-indigo-700"
          >
            Lưu mapping
          </button>
          <button
            onClick={onResetSemanticOverrides}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-[10px] font-bold text-slate-600 shadow-sm hover:bg-slate-50"
          >
            Đặt lại
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {candidateRoles.map((role) => (
            <div key={role} className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{role}</div>
                <div className="text-[10px] text-slate-400">
                  {dashboard.semantic_profile.roles[role]?.confidence_label || "candidate"}
                </div>
              </div>
              <select
                value={roleDraft[role] || ""}
                onChange={(event) => setRoleDraft((prev) => ({ ...prev, [role]: event.target.value }))}
                className="w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs text-slate-700"
              >
                <option value="">Chưa map</option>
                {allColumns.map((column) => (
                  <option key={`${role}-${column}`} value={column}>{column}</option>
                ))}
              </select>
              <div className="mt-2 text-[10px] leading-relaxed text-slate-500">
                {(dashboard.semantic_profile.candidates?.[role] || []).slice(0, 2).map((candidate) => `${candidate.column} (${Math.round(candidate.confidence * 100)}%)`).join(" · ") || "Chưa có candidate mạnh."}
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Debug semantic profile" subtitle="Các role và confidence score đang được backend dashboard sử dụng.">
        <DataTable
          rows={Object.entries(dashboard.semantic_profile.roles).map(([role, match]) => ({
            role,
            column: match.column,
            confidence: match.confidence,
            confidence_label: match.confidence_label,
            source: match.source || match.confidence_label || "auto",
            reason: match.reason,
          }))}
        />
      </Panel>
    </div>
  );
}

function EcommerceSection({
  ecommerce,
  categoryRows,
  monthRows,
  stateRows,
  skuRows,
  sizeRows,
  categoryRiskRows,
  fulfilmentRows,
  courierRows,
  promotionSummary,
  b2bSummary,
  cityRows,
  stateRiskRows,
}: {
  ecommerce: EcommerceOverview | null;
  categoryRows: RecordRow[];
  monthRows: RecordRow[];
  stateRows: RecordRow[];
  skuRows: RecordRow[];
  sizeRows: RecordRow[];
  categoryRiskRows: RecordRow[];
  fulfilmentRows: RecordRow[];
  courierRows: RecordRow[];
  promotionSummary: SummaryWrapper["summary"] | null;
  b2bSummary: SummaryWrapper["summary"] | null;
  cityRows: RecordRow[];
  stateRiskRows: RecordRow[];
}) {
  if (!ecommerce) return <EmptyState message="Pipeline ecommerce chuyên sâu chỉ bật khi dataset tương thích Amazon/Ecommerce." />;
  const topSku = skuRows[0];
  const topSize = sizeRows[0];
  const promotionRows = summaryItems(promotionSummary);
  const b2bRows = summaryItems(b2bSummary);

  return (
    <div className="space-y-6">
      <MetricGrid
        items={[
          ["Tổng doanh thu", formatNumber(ecommerce.overview.total_revenue), "Tổng sales", TrendingUp],
          ["Đơn hàng unique", ecommerce.overview.unique_orders.toLocaleString(), "Số đơn giao dịch", Database],
          ["Cancel/refund rate", `${(ecommerce.overview.cancel_rate * 100).toFixed(2)}%`, "Tỷ lệ hủy/hoàn", AlertTriangle],
          ["Dòng thiếu amount", ecommerce.overview.missing_amount_rows.toLocaleString(), "Dòng thiếu giá trị", Info],
          ["Số lượng bán", ecommerce.overview.total_qty.toLocaleString(), "Tổng units", Activity],
          ["Khoảng thời gian", formatDateRange(ecommerce.overview.date_min, ecommerce.overview.date_max), "Thời gian vận hành", Sparkles],
        ]}
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <HighlightCard
          title="SKU tạo doanh thu cao nhất"
          row={topSku}
          primaryKey="sku"
          secondaryKeys={["category", "revenue", "qty", "cancel_rate"]}
          bgClass="bg-[#fcfcff] border-indigo-100"
        />
        <HighlightCard
          title="Size có demand cao nhất"
          row={topSize}
          primaryKey="size"
          secondaryKeys={["revenue", "qty", "orders", "cancel_rate"]}
          bgClass="bg-[#fcfcff] border-indigo-100"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Mức tập trung theo SKU" subtitle="Các SKU tạo giá trị giao dịch chính.">
          <DataTable rows={skuRows} />
        </Panel>
        <Panel title="Danh mục size" subtitle="Breakdown doanh thu theo kích cỡ sản phẩm.">
          <DataTable rows={sizeRows} />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Metric theo category" subtitle="Giá trị sales theo nhóm category trong catalog.">
          <DataTable rows={categoryRows} />
        </Panel>
        <Panel title="Rủi ro leakage theo category" subtitle="Cancellation metric được đánh dấu theo từng category.">
          <DataTable rows={categoryRiskRows} riskColumn="cancel_rate" />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Tốc độ doanh thu" subtitle="Financial metric được aggregate theo tháng để xem xu hướng.">
          <DataTable rows={monthRows} />
        </Panel>
        <Panel title="Khu vực mạnh theo state" subtitle="Các state dẫn đầu về sales.">
          <DataTable rows={stateRows} />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Khu vực mạnh theo city" subtitle="Các city dẫn đầu về sales.">
          <DataTable rows={cityRows} />
        </Panel>
        <Panel title="Theo dõi leakage theo khu vực" subtitle="Tỷ lệ cancellation risk theo state.">
          <DataTable rows={stateRiskRows} riskColumn="cancel_rate" />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Funnel vận hành logistics" subtitle="Tỷ lệ cancellation theo fulfillment/dispatch channel.">
          <DataTable rows={fulfilmentRows} riskColumn="cancel_rate" />
        </Panel>
        <Panel title="Hiệu suất courier" subtitle="Financial metric theo trạng thái courier/dispatch.">
          <DataTable rows={courierRows} />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel
          title="Phân tích hiệu quả promotion"
          subtitle={promotionSummary?.warning ? `Cảnh báo: ${promotionSummary.warning}` : "Yield metric theo promotion/campaign tags."}
        >
          <DataTable rows={promotionRows} riskColumn="cancel_rate" />
        </Panel>
        <Panel
          title="Phân khúc thương mại: B2B"
          subtitle={b2bSummary?.warning ? `Cảnh báo: ${b2bSummary.warning}` : "So sánh giao dịch B2B với hoạt động retail consumer."}
        >
          <DataTable rows={b2bRows} riskColumn="cancel_rate" />
        </Panel>
      </div>
    </div>
  );
}

function ChartsSection({
  columns,
  chart,
  onSubmit,
  disabled,
  ecommerce,
  categoryRows,
  monthRows,
  stateRows,
  skuRows,
  sizeRows,
  categoryRiskRows,
  fulfilmentRows,
  promotionSummary,
  cityRows,
  stateRiskRows,
}: {
  columns: string[];
  chart: { data: unknown[]; layout: Record<string, unknown> } | null;
  onSubmit: (formData: FormData) => void;
  disabled: boolean;
  ecommerce: EcommerceOverview | null;
  categoryRows: RecordRow[];
  monthRows: RecordRow[];
  stateRows: RecordRow[];
  skuRows: RecordRow[];
  sizeRows: RecordRow[];
  categoryRiskRows: RecordRow[];
  fulfilmentRows: RecordRow[];
  promotionSummary: SummaryWrapper["summary"] | null;
  cityRows: RecordRow[];
  stateRiskRows: RecordRow[];
}) {
  const promotionRows = summaryItems(promotionSummary);
  const autoFigures = buildDashboardFigures({
    categoryRows,
    monthRows,
    stateRows,
    skuRows,
    sizeRows,
    categoryRiskRows,
    fulfilmentRows,
    promotionRows,
    cityRows,
    stateRiskRows,
  });
  const insights = buildDashboardInsights({
    ecommerce,
    categoryRows,
    skuRows,
    stateRows,
    categoryRiskRows,
    fulfilmentRows,
    promotionRows,
    stateRiskRows,
  });

  return (
    <div className="space-y-6">
      {!ecommerce ? (
        <EmptyState message="Hãy cung cấp dataset Amazon Sales hợp lệ để dựng biểu đồ phân tích tự động." />
      ) : (
        <>
          <Panel
            title="Tín hiệu business quan trọng"
            subtitle="Các KPI vận hành chính được tính trực tiếp từ dataset."
          >
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4 mt-2">
              {insights.map((insight, idx) => (
                <div
                  key={insight.label}
                  className={`rounded-xl border p-4 transition-colors ${
                    insight.tone === "risk"
                      ? "border-rose-200 bg-rose-50/50 text-rose-900"
                      : "border-slate-200 bg-slate-50/30 text-slate-800"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono uppercase text-slate-400 font-bold">{insight.label}</span>
                    <span className={`w-1.5 h-1.5 rounded-full ${insight.tone === "risk" ? "bg-rose-500 animate-pulse" : "bg-indigo-500"}`} />
                  </div>
                  <div className="mt-1.5 text-lg font-bold text-slate-900 tracking-tight">{insight.value}</div>
                  <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{insight.note}</p>
                </div>
              ))}
            </div>
          </Panel>

          <Panel
            title="Biểu đồ phân tích tự động"
            subtitle="Các biểu đồ Plotly tự động mô hình hóa business metrics."
          >
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 mt-2">
              {autoFigures.map((figure) => (
                <ChartPanel key={figure.title} title={figure.title} note={figure.note} figure={figure} />
              ))}
            </div>
          </Panel>
        </>
      )}

      <Panel
        title="Trình khám phá chart tùy chỉnh"
        subtitle="Tự chọn biến để kiểm tra mối quan hệ giữa dimension và metric."
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit(new FormData(event.currentTarget));
          }}
          className="grid grid-cols-1 gap-4 md:grid-cols-4 mt-2"
        >
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-mono text-slate-400 font-bold uppercase">Loại biểu đồ</label>
            <Select name="chart_type" options={["bar", "line", "scatter", "histogram", "box"]} disabled={disabled} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-mono text-slate-400 font-bold uppercase">Biến X (dimension)</label>
            <Select name="x" options={columns} disabled={disabled} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-mono text-slate-400 font-bold uppercase">Biến Y (metric)</label>
            <Select name="y" options={["", ...columns]} disabled={disabled} />
          </div>
          <div className="flex items-end">
            <button
              disabled={disabled}
              className="w-full h-[38px] rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs transition-colors shadow-sm disabled:opacity-40 disabled:pointer-events-none flex items-center justify-center gap-1.5"
            >
              <Sparkles size={12} />
              Vẽ biểu đồ
            </button>
          </div>
        </form>
      </Panel>

      {chart && (
        <Panel title="Kết quả biểu đồ" subtitle="Plotly spec được tạo động từ lựa chọn hiện tại.">
          <div className="rounded-xl border border-slate-200 bg-white p-4 mt-3 shadow-sm">
            <Suspense fallback={<ChartLoading height={400} />}>
              <Plot
                data={chart.data as never[]}
                layout={{
                  ...chart.layout,
                  autosize: true,
                  paper_bgcolor: "rgba(0,0,0,0)",
                  plot_bgcolor: "rgba(0,0,0,0)",
                  font: { family: "Outfit, sans-serif", color: "#1e293b" },
                  xaxis: { ...(chart.layout.xaxis as object), gridcolor: "#f1f5f9" },
                  yaxis: { ...(chart.layout.yaxis as object), gridcolor: "#f1f5f9" },
                }}
                className="w-full h-[400px]"
                useResizeHandler
              />
            </Suspense>
          </div>
        </Panel>
      )}
    </div>
  );
}


function ReportSection({
  report,
  onGenerate,
  disabled,
  copy,
  download,
  copied,
}: {
  report: string;
  onGenerate: () => void;
  disabled: boolean;
  copy: () => void;
  download: () => void;
  copied: boolean;
}) {
  return (
    <div className="max-w-3xl mx-auto">
      <Panel
        title="Studio báo cáo điều hành"
        subtitle="Tổng hợp metrics, data quality log và khuyến nghị phân tích thành báo cáo markdown."
      >
        <div className="flex gap-2.5 mt-3">
          <button
            disabled={disabled}
            onClick={onGenerate}
            className="rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs px-5 py-2.5 transition-colors disabled:opacity-40 disabled:pointer-events-none flex items-center gap-1.5 shadow-sm"
          >
            <FileText size={14} />
            Tạo báo cáo điều hành
          </button>

          {report && (
            <>
              <button
                onClick={copy}
                className="rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-xs px-4 py-2.5 transition-colors flex items-center gap-1.5"
              >
                {copied ? <CheckCircle2 className="text-emerald-600" size={14} /> : <Copy size={14} />}
                {copied ? "Đã copy" : "Copy vào clipboard"}
              </button>
              <button
                onClick={download}
                className="rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-xs px-4 py-2.5 transition-colors flex items-center gap-1.5"
              >
                <Download size={14} />
                Tải báo cáo (.md)
              </button>
            </>
          )}
        </div>

        {report && (
          <div className="mt-5 rounded-xl border border-slate-200 bg-white p-6 max-h-[500px] overflow-y-auto font-mono text-[11px] leading-relaxed text-slate-700 shadow-sm whitespace-pre-wrap select-all">
            {report}
          </div>
        )}
      </Panel>
    </div>
  );
}

// ---------------------- SHARED PLATFORM SHELLS ----------------------

function ChartLoading({ height }: { height: number }) {
  const { t } = useI18n();
  return (
    <div
      className="flex w-full items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/70 text-[11px] font-semibold text-slate-400"
      style={{ height }}
    >
      <Loader2 className="mr-2 animate-spin" style={{ width: 14, height: 14 }} />
      {t.app.loadingChart}
    </div>
  );
}

function ChartPanel({ title, note, figure }: { title: string; note: string; figure: DashboardFigure }) {
  return (
    <div className="chart-shell" style={{ height: 420 }}>
      <div
        className="flex items-start justify-between gap-3 px-4 py-3.5"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <div className="min-w-0">
          <h3 className="truncate text-[13px] font-bold tracking-tight text-slate-900">{title}</h3>
          <p className="mt-0.5 line-clamp-1 text-[10px] leading-snug text-slate-500">{note}</p>
        </div>
        <span
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[7px]"
          style={{ background: 'var(--accent-light)', border: '1px solid var(--accent-dim)' }}
        >
          <LineChart style={{ width: 13, height: 13, color: 'var(--accent)' }} />
        </span>
      </div>
      <div className="flex-1 w-full relative" style={{ height: 360 }}>
        <Suspense fallback={<ChartLoading height={360} />}>
          <Plot
            data={figure.data as never[]}
            layout={{
              ...figure.layout,
              autosize: true,
              paper_bgcolor: "rgba(0,0,0,0)",
              plot_bgcolor: "rgba(0,0,0,0)",
              font: { family: "Outfit, sans-serif", size: 9, color: "#475569" },
              xaxis: { ...(figure.layout.xaxis as object), gridcolor: "#f1f5f9" },
              yaxis: { ...(figure.layout.yaxis as object), gridcolor: "#f1f5f9" },
            }}
            className="w-full h-full"
            useResizeHandler
            config={{ displayModeBar: false, responsive: true }}
          />
        </Suspense>
      </div>
    </div>
  );
}

function Panel({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="panel-shell">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-[14px] font-bold tracking-tight text-slate-950">{title}</h2>
          {subtitle && <p className="mt-0.5 max-w-3xl text-[11px] leading-relaxed text-slate-500">{subtitle}</p>}
        </div>
        <span
          className="mt-0.5 h-2 w-2 shrink-0 rounded-full transition-all"
          style={{ background: 'rgba(37,99,235,0.3)' }}
        />
      </div>
      {children}
    </section>
  );
}

function MiniMeta({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="rounded-[8px] px-2.5 py-2"
      style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
    >
      <div className="section-label">{label}</div>
      <div className="mt-1 truncate text-[12px] font-bold text-slate-800">{value}</div>
    </div>
  );
}

function buildAgentReportSnippet(response: AgentResponse) {
  const toolName = response.tool_call?.tool_name || response.tool_calls?.[0]?.tool_name || "unknown_tool";
  const summary = response.result_summary;
  const card = response.answer_card;
  if (card) {
    const evidence = card.evidence.length
      ? card.evidence.map((item) => `- **${item.label}:** ${item.value}${item.description ? ` - ${item.description}` : ""}`).join("\n")
      : "- Không có evidence card.";
    const warnings = card.data_warnings.length
      ? card.data_warnings.map((warning) => `- ${warning}`).join("\n")
      : "- Không có warning từ answer card.";
    return [
      "## AI Copilot Insight",
      "",
      `**Headline:** ${card.headline}`,
      `**Tool:** ${toolName}`,
      `**Source:** ${card.answer_source}`,
      "",
      "### Summary",
      card.summary,
      "",
      "### Evidence",
      evidence,
      "",
      "### Why It Matters",
      card.why_it_matters,
      "",
      "### Warnings",
      warnings,
    ].join("\n");
  }
  const warnings = response.warnings.length
    ? response.warnings.map((warning) => `- ${warning}`).join("\n")
    : "- Không có warning từ tool.";
  return [
    "## AI Copilot Insight",
    "",
    `**Tool:** ${toolName}`,
    `**Source:** ${response.explanation_source || "tool_result"}`,
    `**Rows:** ${summary?.row_count ?? "N/A"}`,
    "",
    "### Answer",
    response.answer || "Không có nội dung trả lời.",
    "",
    "### Warnings",
    warnings,
  ].join("\n");
}

function downloadAgentResult(data: unknown, filename: string) {
  const element = document.createElement("a");
  const file = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  element.href = URL.createObjectURL(file);
  element.download = filename;
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
  URL.revokeObjectURL(element.href);
}

function MetricGrid({ items }: { items: Array<[string, string, string, typeof Upload]> }) {
  return (
    <div className="grid grid-flow-dense grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {items.map(([label, value, desc, Icon]) => (
        <div key={label} className="kpi-card">
          <div className="flex items-center justify-between mb-3">
            <span className="section-label">{label}</span>
            <span
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[7px]"
              style={{ background: 'var(--accent-light)', border: '1px solid var(--accent-dim)' }}
            >
              <Icon style={{ width: 13, height: 13, color: 'var(--accent)' }} />
            </span>
          </div>
          <div className="text-[18px] font-black leading-tight tracking-tight text-slate-950">{value}</div>
          <p className="mt-1.5 truncate text-[10px] leading-relaxed text-slate-400">{desc}</p>
        </div>
      ))}
    </div>
  );
}

function HighlightCard({
  title,
  row,
  primaryKey,
  secondaryKeys,
  bgClass,
}: {
  title: string;
  row?: RecordRow;
  primaryKey: string;
  secondaryKeys: string[];
  bgClass: string;
}) {
  if (!row) {
    return (
      <Panel title={title}>
        <div className="text-[11px] text-slate-400 py-3">Attributes not recognized in current dataset context.</div>
      </Panel>
    );
  }
  return (
    <div className={`group rounded-lg border border-slate-200 ${bgClass} p-4 shadow-[0_10px_30px_rgba(15,23,42,0.045)] transition-all duration-300 hover:-translate-y-0.5 hover:border-slate-300`}>
      <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-2">
        <h4 className="text-[10px] font-bold text-slate-400 font-mono tracking-wider uppercase">{title}</h4>
        <ArrowUpRight className="text-slate-400 w-3.5 h-3.5 transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
      </div>

      <div className="text-xl font-bold text-slate-900 tracking-tight leading-none truncate select-all">{formatCell(row[primaryKey])}</div>

      <div className="mt-4 grid grid-cols-2 gap-2.5">
        {secondaryKeys.map((key) => (
          <div
            key={key}
            className="rounded-lg border border-slate-100 bg-white/90 p-2.5 transition-colors hover:border-slate-200"
          >
            <div className="text-[8px] font-mono font-bold uppercase text-slate-400 tracking-wider">{key}</div>
            <div className="mt-0.5 text-xs font-semibold text-slate-800">{formatCell(row[key])}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DataTable({ rows, riskColumn }: { rows: RecordRow[]; riskColumn?: string }) {
  const columns = useMemo(() => Object.keys(rows[0] ?? {}), [rows]);
  if (!rows.length) return <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/70 py-7 text-center text-xs font-semibold text-slate-400">No rows parsed.</div>;
  return (
    <div className="max-h-[420px] overflow-auto rounded-lg border border-slate-200/80 bg-white/95 shadow-inner">
      <table className="w-full border-collapse text-xs select-text">
        <thead className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50/95 backdrop-blur">
          <tr>
            {columns.map((column) => (
              <th
                key={column}
                className="whitespace-nowrap px-4 py-2.5 text-left font-mono text-[9px] font-bold uppercase tracking-wider text-slate-400"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row, index) => (
            <tr
              key={index}
              className={`hover:bg-slate-50/50 transition-colors ${riskClass(row, riskColumn, index)}`}
            >
              {columns.map((column) => (
                <td key={column} className={`whitespace-nowrap px-4 py-2.5 align-middle font-medium ${column === columns[0] ? "text-slate-900" : "text-slate-700"}`}>
                  {formatCell(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Select({ name, options, disabled }: { name: string; options: string[]; disabled: boolean }) {
  return (
    <select
      name={name}
      disabled={disabled}
      className="w-full rounded-lg border border-slate-200 bg-white text-slate-700 text-xs px-3 py-2 outline-none focus:border-indigo-500 transition-colors shadow-sm disabled:opacity-40"
    >
      {options.map((option) => (
        <option key={option || "none"} value={option}>
          {option || "None"}
        </option>
      ))}
    </select>
  );
}

// ---------------------- STATUS SHELLS ----------------------

function EmptyState({ message = "Awaiting CSV datasource. Load a dataset file to generate insights." }: { message?: string }) {
  return (
    <div
      className="mx-auto mt-8 flex max-w-md flex-col items-center justify-center rounded-[16px] p-12 text-center"
      style={{ background: 'rgba(37,99,235,0.03)', border: '2px dashed rgba(37,99,235,0.15)' }}
    >
      <div
        className="mb-4 flex h-12 w-12 items-center justify-center rounded-[12px]"
        style={{ background: '#eff6ff', border: '1px solid rgba(37,99,235,0.2)' }}
      >
        <Info style={{ width: 18, height: 18, color: '#2563eb' }} />
      </div>
      <p className="text-[13px] font-bold text-slate-800">No context loaded</p>
      <p className="text-[11px] text-slate-500 mt-1.5 max-w-xs leading-relaxed">{message}</p>
    </div>
  );
}

// ---------------------- REDUCTION MATHS ----------------------

function formatNumber(value: number) {
  return "$" + value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function formatDateRange(dateMin: string | null, dateMax: string | null) {
  if (!dateMin || !dateMax) return "N/A";
  return `${dateMin} to ${dateMax}`;
}

function summaryItems(summary: SummaryWrapper["summary"] | null): RecordRow[] {
  return Array.isArray(summary?.items) ? summary.items : [];
}

function buildDashboardInsights({
  ecommerce,
  categoryRows,
  skuRows,
  stateRows,
  categoryRiskRows,
  fulfilmentRows,
  promotionRows,
  stateRiskRows,
}: {
  ecommerce: EcommerceOverview | null;
  categoryRows: RecordRow[];
  skuRows: RecordRow[];
  stateRows: RecordRow[];
  categoryRiskRows: RecordRow[];
  fulfilmentRows: RecordRow[];
  promotionRows: RecordRow[];
  stateRiskRows: RecordRow[];
}): DashboardInsight[] {
  const topCategory = categoryRows[0];
  const topSku = skuRows[0];
  const topState = stateRows[0];
  const riskyCategory = categoryRiskRows[0];
  const riskyState = stateRiskRows[0];
  const riskyFulfilment = highestBy(fulfilmentRows, "cancel_rate");
  const promoted = promotionRows.find((row) => row.has_promotion === true);
  const unpromoted = promotionRows.find((row) => row.has_promotion === false);

  return [
    {
      label: "Revenue Base",
      value: ecommerce ? formatNumber(ecommerce.overview.total_revenue) : "N/A",
      note: ecommerce
        ? `${ecommerce.overview.unique_orders.toLocaleString()} active transactional orders aggregated from ${formatDateRange(
            ecommerce.overview.date_min,
            ecommerce.overview.date_max
          )}.`
        : "No ecommerce overview available.",
    },
    {
      label: "Dominant SKU Identifier",
      value: topSku ? String(topSku.sku) : "N/A",
      note: topSku
        ? `${formatCell(topSku.category)} leads product performance with ${formatCell(topSku.revenue)} sales on ${formatCell(
            topSku.qty
          )} units.`
        : "SKU concentration ranking not compiled.",
    },
    {
      label: "Market Leader Segment",
      value: topCategory ? String(topCategory.category) : "N/A",
      note: topCategory
        ? `Monopolizing ${formatCell(topCategory.revenue_share)}% gross share, accounting for ${formatCell(
            topCategory.orders
          )} orders with a cancel score of ${asPercent(topCategory.cancel_rate)}.`
        : "Category tracking is disabled.",
    },
    {
      label: "Geographic Hub",
      value: topState ? String(topState.ship_state) : "N/A",
      note: topState
        ? `Delivering ${formatCell(topState.revenue)} revenue from ${formatCell(topState.orders)} deliveries.`
        : "Regional geo mapping not compiled.",
    },
    {
      label: "Cancellation Focus",
      value: riskyCategory ? String(riskyCategory.category) : "N/A",
      note: riskyCategory
        ? `Vulnerable product category displaying cancellation score of ${asPercent(
            riskyCategory.cancel_rate
          )} over ${formatCell(riskyCategory.orders)} orders.`
        : "No category risk anomalies detected.",
      tone: "risk",
    },
    {
      label: "Fulfillment Risk Flag",
      value: riskyFulfilment ? String(riskyFulfilment.fulfilment) : "N/A",
      note: riskyFulfilment
        ? `Highest cancel-score routing pipeline flagged at ${asPercent(
            riskyFulfilment.cancel_rate
          )}. Check transactional volume balance before modifying.`
        : "Operational delivery safe.",
      tone: "risk",
    },
    {
      label: "Promotion Performance",
      value: promoted ? formatCell(promoted.revenue) : "N/A",
      note:
        promoted && unpromoted
          ? `Campaign orders avg ${formatCell(promoted.avg_amount)} compared to baseline non-promotional avg ${formatCell(
              unpromoted.avg_amount
            )}. (Non-causal association)`
          : "Promo comparisons require distinct baseline records.",
    },
    {
      label: "High Risk Region",
      value: riskyState ? String(riskyState.ship_state) : "N/A",
      note: riskyState
        ? `State passing threshold order metrics flagging a cancellation rate of ${asPercent(riskyState.cancel_rate)}.`
        : "No regional anomalies found.",
      tone: "risk",
    },
  ];
}

function buildDashboardFigures({
  categoryRows,
  monthRows,
  stateRows,
  skuRows,
  sizeRows,
  categoryRiskRows,
  fulfilmentRows,
  promotionRows,
  cityRows,
  stateRiskRows,
}: {
  categoryRows: RecordRow[];
  monthRows: RecordRow[];
  stateRows: RecordRow[];
  skuRows: RecordRow[];
  sizeRows: RecordRow[];
  categoryRiskRows: RecordRow[];
  fulfilmentRows: RecordRow[];
  promotionRows: RecordRow[];
  cityRows: RecordRow[];
  stateRiskRows: RecordRow[];
}): DashboardFigure[] {
  return [
    lineFigure(monthRows, "order_month", "revenue", "Aggregate Revenue Flow", "Descriptive month-on-month revenue velocity trends.", "#4f46e5"),
    barFigure(categoryRows, "category", "revenue", "Category Contribution Matrix", "Aggregated gross sales by retail category.", 10, "#6366f1"),
    barFigure(skuRows, "sku", "revenue", "Product Revenue Focus (SKU)", "Top 10 individual product gross concentrations.", 10, "#0ea5e9"),
    barFigure(sizeRows, "size", "revenue", "Revenue Sizing Portfolio", "Size mix gross sales distributions.", 12, "#ec4899"),
    barFigure(stateRows, "ship_state", "revenue", "Top Geographic Hubs (States)", "State-level demand density mapping.", 12, "#10b981"),
    barFigure(cityRows, "ship_city", "revenue", "Top City Demand Nodes", "Highest value consumer centers by city.", 12, "#f59e0b"),
    barFigure(categoryRiskRows, "category", "cancel_rate", "Category Leakage Vulnerability", "Cancellation and refund percentage by category.", 10, "#f43f5e", true),
    barFigure(stateRiskRows, "ship_state", "cancel_rate", "Regional Leakage (States)", "States exceeding cancellation safety baselines.", 10, "#ff1493", true),
    barFigure(fulfilmentRows, "fulfilment", "cancel_rate", "Logistical Pipeline Vulnerability", "Cancellation rates across logistic channels.", 10, "#e11d48", true),
    barFigure(promotionRows, "has_promotion", "avg_amount", "Promotion Ticket Yield", "Average customer purchase values by promotional flag.", 2, "#8b5cf6"),
  ].filter((figure) => figure.data.length > 0);
}

function barFigure(
  rows: RecordRow[],
  xKey: string,
  yKey: string,
  title: string,
  note: string,
  limit: number,
  color: string,
  percentAxis = false,
): DashboardFigure {
  const filtered = rows
    .filter((row) => typeof row[yKey] === "number")
    .slice(0, limit);
  const x = filtered.map((row) => String(row[xKey] ?? "Unknown"));
  const y = filtered.map((row) => numberValue(row[yKey]));
  return {
    title,
    note,
    data: filtered.length
      ? [
          {
            type: "bar",
            x,
            y,
            marker: { color, line: { color: "rgba(255,255,255,0.05)", width: 1 } },
            hovertemplate: percentAxis ? "%{x}<br>%{y:.2%}<extra></extra>" : "%{x}<br>$%{y:,.0f}<extra></extra>",
          },
        ]
      : [],
    layout: dashboardLayout(percentAxis ? "Leakage Rate" : "Gross Financials", percentAxis),
  };
}

// ---------------------- LINE CHART projects ----------------------

function lineFigure(rows: RecordRow[], xKey: string, yKey: string, title: string, note: string, color: string): DashboardFigure {
  const filtered = rows.filter((row) => typeof row[yKey] === "number");
  return {
    title,
    note,
    data: filtered.length
      ? [
          {
            type: "scatter",
            mode: "lines+markers",
            x: filtered.map((row) => String(row[xKey] ?? "")),
            y: filtered.map((row) => numberValue(row[yKey])),
            line: { color, width: 2, shape: "spline" },
            marker: { size: 6, color: "#ffffff", line: { color, width: 2 } },
            hovertemplate: "%{x}<br>$%{y:,.0f}<extra></extra>",
          },
        ]
      : [],
    layout: dashboardLayout("Gross Financials"),
  };
}

function dashboardLayout(yTitle: string, percentAxis = false): Record<string, unknown> {
  return {
    margin: { l: 50, r: 10, t: 15, b: 50 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Outfit, sans-serif", size: 9, color: "#475569" },
    xaxis: {
      automargin: true,
      tickangle: -30,
      gridcolor: "#f1f5f9",
      zerolinecolor: "#e2e8f0",
      tickfont: { size: 8 },
    },
    yaxis: {
      title: { text: yTitle, font: { size: 9 } },
      tickformat: percentAxis ? ".0%" : "$s",
      gridcolor: "#f1f5f9",
      zerolinecolor: "#e2e8f0",
      tickfont: { size: 8 },
    },
    showlegend: false,
  };
}

function highestBy(rows: RecordRow[], key: string) {
  return rows.reduce<RecordRow | undefined>((best, row) => {
    if (typeof row[key] !== "number") return best;
    if (!best || numberValue(row[key]) > numberValue(best[key])) return row;
    return best;
  }, undefined);
}

function numberValue(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function asPercent(value: unknown) {
  return typeof value === "number" ? `${(value * 100).toFixed(2)}%` : "N/A";
}

function riskClass(row: RecordRow, riskColumn: string | undefined, index: number) {
  if (!riskColumn) return index % 2 === 0 ? "bg-white" : "bg-slate-50/40";
  const value = row[riskColumn];
  if (typeof value !== "number") return index % 2 === 0 ? "bg-white" : "bg-slate-50/40";
  if (value >= 0.25) return "bg-rose-50/60 text-rose-800 hover:bg-rose-50";
  if (value >= 0.1) return "bg-amber-50/60 text-amber-800 hover:bg-amber-50";
  return index % 2 === 0 ? "bg-white" : "bg-slate-50/40";
}

function toMetricExpressionToken(value: string) {
  const token = value
    .trim()
    .replace(/[^0-9a-zA-Z_]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");
  if (!token) return "";
  return /^[0-9]/.test(token) ? `col_${token}` : token;
}

function formatCell(value: unknown) {
  if (typeof value === "number") {
    // If it's a decimal between 0 and 1, probably a percentage
    if (value > 0 && value < 1) return (value * 100).toFixed(2) + "%";
    return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "TRUE" : "FALSE";
  return String(value);
}
