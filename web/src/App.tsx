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
  Menu,
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
import { UploadSection } from "./components/UploadSection";
import { SemanticMappingSummary } from "./components/SemanticMappingSummary";
import { AdvancedDataControls } from "./components/AdvancedDataControls";
import { useI18n, type Language } from "./i18n";
import type { AgentResponse, AgentStatus, DashboardResponse, DataDictionary, DataDictionaryResponse, EcommerceOverview, MetricDefinition, MetricEvaluationResponse, RecordRow, Section, SemanticProfile, SummaryResponse, SummaryWrapper, UploadResponse } from "./types";

import { useDatasetWorkspace } from "./hooks/useDatasetWorkspace";
import { useDashboardData } from "./hooks/useDashboardData";
import { useEcommerceData } from "./hooks/useEcommerceData";
import { useCopilotChat } from "./hooks/useCopilotChat";
import { useMetrics } from "./hooks/useMetrics";
import { useDataDictionary } from "./hooks/useDataDictionary";
import { useSemanticMapping } from "./hooks/useSemanticMapping";

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
  const [dashboardSubTab, setDashboardSubTab] = useState<"kpis" | "charts" | "ecommerce">("kpis");
  const [profileSubTab, setProfileSubTab] = useState<"overview" | "quality">("overview");

  // Destructure hook properties
  const workspace = useDatasetWorkspace();
  const dashboard = useDashboardData();
  const ecommerceData = useEcommerceData();
  const copilot = useCopilotChat();
  const metrics = useMetrics();
  const dictionary = useDataDictionary();
  const semantic = useSemanticMapping();

  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 1024);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 1024);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Alias original variable names to avoid breaking existing JSX and handlers
  const {
    upload,
    setUpload,
    summary,
    setSummary,
    availableDatasets,
    setAvailableDatasets,
    agentStatus,
    setAgentStatus,
    loading,
    setLoading,
    error,
    setError,
    datasetId,
    columns,
    uploadProgress,
    uploadPhase,
    selectedFileMeta,
    cancelUpload,
    handleUpload: workspaceUpload,
    handleSelectDataset: workspaceSelectDataset,
  } = workspace;

  const {
    smartDashboard,
    setSmartDashboard,
  } = dashboard;

  const {
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
    fetchEcommerceData,
    resetEcommerceData,
  } = ecommerceData;

  const {
    chatHistory,
    setChatHistory,
    questionDraft,
    setQuestionDraft,
  } = copilot;

  const {
    customMetrics,
    setCustomMetrics,
  } = metrics;

  const {
    dataDictionary,
    setDataDictionary,
  } = dictionary;

  const [chart, setChart] = useState<{ data: unknown[]; layout: Record<string, unknown> } | null>(null);
  const [report, setReport] = useState("");
  const [copied, setCopied] = useState(false);

  const navItems: Array<{ id: Section; label: string; icon: typeof Upload; badge?: string }> = useMemo(() => [
    { id: "upload",    label: t.nav.upload,    icon: Upload },
    { id: "profile",   label: t.nav.profile ?? "Data Profile",   icon: Database },
    { id: "dashboard", label: t.nav.dashboard, icon: Activity },
    { id: "ask",       label: t.nav.ask,       icon: Bot },
    { id: "report",    label: t.nav.report,    icon: FileText },
  ], [t]);
  const sectionMeta = t.sections;

  // Fix 1.2: reset section when domain changes to avoid blank screen
  useEffect(() => {
    const validSections: Section[] = ["upload", "profile", "dashboard", "ask", "report"];
    if (!validSections.includes(section)) {
      setSection("dashboard");
    }
  }, [smartDashboard?.domain, section]);

  // Reset ecommerce sub-tab when domain is no longer ecommerce
  useEffect(() => {
    if (dashboardSubTab === "ecommerce" && smartDashboard?.domain !== "ecommerce") {
      setDashboardSubTab("kpis");
    }
  }, [smartDashboard?.domain, dashboardSubTab]);

  async function refreshDataset(
    nextUpload: UploadResponse,
    updatePhase?: (phase: "profiling" | "building" | "completed", progress: number) => void
  ) {
    if (!updatePhase) {
      setLoading(t.app.messages.parsingDataset);
    }
    setError("");
    setUpload(nextUpload);
    try {
      if (updatePhase) updatePhase("profiling", 60);
      // 1. Fetch summary and dashboard contract first to determine domain
      const summaryData = await getSummary(nextUpload.dataset_id);
      setSummary(summaryData);

      if (updatePhase) updatePhase("building", 75);
      const dashboardData = await getDashboard(nextUpload.dataset_id).catch(() => null);
      setSmartDashboard(dashboardData);
      const dictionaryData = await getDataDictionary(nextUpload.dataset_id).catch(() => null);
      setDataDictionary(dictionaryData);
      const metricsData = await getMetrics(nextUpload.dataset_id).catch(() => ({ metrics: [] }));
      setCustomMetrics(metricsData.metrics);

      // 2. Only fetch deep ecommerce endpoints if detected domain is "ecommerce"
      if (dashboardData && dashboardData.domain === "ecommerce") {
        if (updatePhase) updatePhase("building", 90);
        await fetchEcommerceData(nextUpload.dataset_id);
      } else {
        resetEcommerceData();
      }

      setSection("profile");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.app.messages.loadDetailsFailed);
      throw err;
    } finally {
      if (!updatePhase) {
        setLoading("");
      }
    }
  }

  async function handleUpload(file: File) {
    await workspaceUpload(file, async (uploaded, update) => {
      await refreshDataset(uploaded, update);
    });
  }

  async function handleSelectDataset(ds: WorkspaceDataset) {
    await workspaceSelectDataset(ds, async (mockUpload, update) => {
      await refreshDataset(mockUpload, update);
    });
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

    // Get current chat history before appending the new one
    let currentHistory: any[] = [];
    setChatHistory((prev) => {
      currentHistory = prev;
      return [
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
      ];
    });

    const historyPayload = currentHistory
      .slice(-5)
      .flatMap((entry) => {
        if (entry.status === "done") {
          return [
            { role: "user" as const, content: entry.question },
            {
              role: "assistant" as const,
              content: entry.response.answer || "",
              tool_name: entry.response.tool_call?.tool_name || null,
              tool_result_summary: entry.response.result_summary || null,
              answer_card: entry.response.answer_card || null,
            }
          ];
        } else if (entry.status === "error") {
          return [
            { role: "user" as const, content: entry.question },
            {
              role: "assistant" as const,
              content: entry.response.answer || "",
            }
          ];
        }
        return [];
      });

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
      }, historyPayload).catch(async () => askAgent(datasetId, question, historyPayload));
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
      setSection("dashboard");
      setDashboardSubTab("charts");
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

      {/* Backdrop overlay */}
      {!isDesktop && sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-sm transition-opacity duration-300"
        />
      )}

      {/* ── Sidebar ───────────────────────────────────────────────── */}
      <aside
        className={`glass-sidebar fixed inset-y-0 left-0 z-50 flex flex-col transition-transform duration-300 ease-in-out ${
          isDesktop ? "translate-x-0" : sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
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
            .map((item) => {
              const Icon = item.icon;
              const active = section === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setSection(item.id);
                    if (!isDesktop) setSidebarOpen(false);
                  }}
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
        className="relative z-10 min-h-screen transition-all duration-300"
        style={{
          marginLeft: isDesktop ? 'var(--sidebar-w)' : '0',
          padding: isDesktop ? '20px 28px 40px' : '16px 16px 32px',
        }}
      >
        {/* Page header */}
        <header className="glass-panel mb-6 rounded-[16px] px-6 py-5">
          <div className="flex items-start justify-between gap-6">
            <div className="flex items-start gap-3 min-w-0">
              {!isDesktop && (
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="p-2 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 transition-colors shadow-sm shrink-0 mt-1"
                  aria-label="Toggle sidebar"
                >
                  <Menu className="h-5 w-5" />
                </button>
              )}
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

        {error && section !== "upload" && (
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
              uploadProgress={uploadProgress}
              uploadPhase={uploadPhase}
              selectedFileMeta={selectedFileMeta}
              cancelUpload={cancelUpload}
              error={error}
              dashboard={smartDashboard}
            />
          )}

          {section === "profile" && (
            <ProfileSection
              summary={summary}
              ecommerce={ecommerce}
              activeTab={profileSubTab}
              onTabChange={setProfileSubTab}
            />
          )}

          {section === "dashboard" && (
            <UnifiedDashboard
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
              chart={chart}
              onChartSubmit={handleChart}
              activeSubTab={dashboardSubTab}
              onSubTabChange={setDashboardSubTab}
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
              onOpenMapping={() => setSection("profile")}
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


// ─── ISSUE 1.1 FIX: Shared sub-tab bar ───────────────────────────────────────

function SubTabBar({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div
      className="flex gap-1 rounded-[10px] p-1 mb-6"
      style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className="flex-1 rounded-[8px] px-4 py-2 text-[12px] font-semibold transition-all duration-200"
          style={
            active === tab.id
              ? {
                  background: 'var(--surface)',
                  color: 'var(--accent)',
                  boxShadow: '0 1px 4px rgba(15,23,42,0.08)',
                  border: '1px solid rgba(37,99,235,0.18)',
                }
              : { color: 'var(--text-secondary)', background: 'transparent', border: '1px solid transparent' }
          }
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// ─── ProfileSection = Overview + Quality merged ───────────────────────────────

function ProfileSection({
  summary,
  ecommerce,
  activeTab,
  onTabChange,
}: {
  summary: SummaryResponse | null;
  ecommerce: EcommerceOverview | null;
  activeTab: "overview" | "quality";
  onTabChange: (tab: "overview" | "quality") => void;
}) {
  if (!summary) return <EmptyState />;
  return (
    <div>
      <SubTabBar
        tabs={[
          { id: "overview", label: "Tổng quan dataset" },
          { id: "quality", label: "Kiểm tra chất lượng" },
        ]}
        active={activeTab}
        onChange={(id) => onTabChange(id as "overview" | "quality")}
      />
      {activeTab === "overview" && <OverviewSection summary={summary} ecommerce={ecommerce} />}
      {activeTab === "quality" && <QualitySection summary={summary} ecommerce={ecommerce} />}
    </div>
  );
}

// ─── UnifiedDashboard = SmartDashboard + Charts + Ecommerce ──────────────────

function UnifiedDashboard({
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
  chart,
  onChartSubmit,
  activeSubTab,
  onSubTabChange,
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
  chart: { data: unknown[]; layout: Record<string, unknown> } | null;
  onChartSubmit: (formData: FormData) => void;
  activeSubTab: "kpis" | "charts" | "ecommerce";
  onSubTabChange: (tab: "kpis" | "charts" | "ecommerce") => void;
}) {
  const isEcommerce = dashboard?.domain === "ecommerce";
  const tabs = [
    { id: "kpis", label: "KPI & Insights" },
    { id: "charts", label: "Biểu đồ phân tích" },
    ...(isEcommerce ? [{ id: "ecommerce", label: "E-commerce Chi tiết" }] : []),
  ];

  return (
    <div>
      <SubTabBar
        tabs={tabs}
        active={activeSubTab}
        onChange={(id) => onSubTabChange(id as "kpis" | "charts" | "ecommerce")}
      />

      {activeSubTab === "kpis" && (
        <SmartDashboardSection
          dashboard={dashboard}
          dataDictionary={dataDictionary}
          customMetrics={customMetrics}
          columns={columns}
          onAskQuestion={onAskQuestion}
          onSaveSemanticOverrides={onSaveSemanticOverrides}
          onResetSemanticOverrides={onResetSemanticOverrides}
          onUploadDataDictionary={onUploadDataDictionary}
          onSaveDataDictionary={onSaveDataDictionary}
          onDeleteDataDictionary={onDeleteDataDictionary}
          onSaveMetric={onSaveMetric}
          onDeleteMetric={onDeleteMetric}
          onEvaluateMetric={onEvaluateMetric}
        />
      )}

      {activeSubTab === "charts" && (
        <ChartsSection
          dashboard={dashboard}
          columns={columns}
          chart={chart}
          onSubmit={onChartSubmit}
          disabled={!dashboard}
        />
      )}

      {activeSubTab === "ecommerce" && isEcommerce && (
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
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);

  if (!dashboard) return <EmptyState message="Hãy upload dataset để tạo dashboard thông minh từ backend." />;

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
            <div key={warning} className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800 animate-fade-up">
              ⚠️ {warning}
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

      <SemanticMappingSummary
        dashboard={dashboard}
        onToggleAdvanced={() => setIsAdvancedOpen(!isAdvancedOpen)}
        isAdvancedOpen={isAdvancedOpen}
      />

      {isAdvancedOpen && (
        <AdvancedDataControls
          dashboard={dashboard}
          dataDictionary={dataDictionary}
          customMetrics={customMetrics}
          columns={columns}
          onSaveSemanticOverrides={onSaveSemanticOverrides}
          onResetSemanticOverrides={onResetSemanticOverrides}
          onUploadDataDictionary={onUploadDataDictionary}
          onSaveDataDictionary={onSaveDataDictionary}
          onDeleteDataDictionary={onDeleteDataDictionary}
          onSaveMetric={onSaveMetric}
          onDeleteMetric={onDeleteMetric}
          onEvaluateMetric={onEvaluateMetric}
        />
      )}
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
  dashboard,
  columns,
  chart,
  onSubmit,
  disabled,
}: {
  dashboard: DashboardResponse | null;
  columns: string[];
  chart: { data: unknown[]; layout: Record<string, unknown> } | null;
  onSubmit: (formData: FormData) => void;
  disabled: boolean;
}) {
  const [activeTab, setActiveTab] = useState<"dashboard" | "custom">("dashboard");

  return (
    <div className="space-y-6">
      {/* Sub-tab navigation */}
      <div className="flex border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={() => setActiveTab("dashboard")}
          className={`px-4 py-2 text-xs font-bold transition-all border-b-2 ${
            activeTab === "dashboard"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          Biểu đồ từ dashboard
        </button>
        <button
          onClick={() => setActiveTab("custom")}
          className={`px-4 py-2 text-xs font-bold transition-all border-b-2 ${
            activeTab === "custom"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          Tự tạo biểu đồ
        </button>
      </div>

      {activeTab === "dashboard" ? (
        <div className="space-y-6">
          {!dashboard || !dashboard.charts || dashboard.charts.length === 0 ? (
            <EmptyState message="Backend chưa tạo biểu đồ phù hợp cho dataset này." />
          ) : (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {dashboard.charts.map((item) => (
                <ChartPanel
                  key={`${item.id || item.title}-${item.description}`}
                  title={item.title}
                  note={item.description}
                  figure={{
                    title: item.title,
                    note: item.description,
                    data: item.chart.data,
                    layout: item.chart.layout,
                  }}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-6">
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
  const { language } = useI18n();
  const isVi = language === "vi";

  if (!row) {
    return (
      <Panel title={title}>
        <div className="text-[11px] text-slate-400 py-3">
          {isVi ? "Không nhận diện thuộc tính trong dataset này." : "Attributes not recognized in current dataset context."}
        </div>
      </Panel>
    );
  }
  return (
    <div className={`group rounded-lg border border-slate-200 ${bgClass} p-4 shadow-[0_10px_30px_rgba(15,23,42,0.045)] transition-all duration-300 hover:-translate-y-0.5 hover:border-slate-300`}>
      <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-2">
        <h4 className="text-[10px] font-bold text-slate-400 font-mono tracking-wider uppercase">{title}</h4>
        <ArrowUpRight className="text-slate-400 w-3.5 h-3.5 transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
      </div>

      <div className="text-xl font-bold text-slate-900 tracking-tight leading-none truncate select-all">{formatCell(row[primaryKey], isVi)}</div>

      <div className="mt-4 grid grid-cols-2 gap-2.5">
        {secondaryKeys.map((key) => (
          <div
            key={key}
            className="rounded-lg border border-slate-100 bg-white/90 p-2.5 transition-colors hover:border-slate-200"
          >
            <div className="text-[8px] font-mono font-bold uppercase text-slate-400 tracking-wider">{key}</div>
            <div className="mt-0.5 text-xs font-semibold text-slate-800">{formatCell(row[key], isVi)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DataTable({ rows, riskColumn }: { rows: RecordRow[]; riskColumn?: string }) {
  const { language } = useI18n();
  const isVi = language === "vi";
  const columns = useMemo(() => Object.keys(rows[0] ?? {}), [rows]);
  if (!rows.length) {
    return (
      <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/70 py-7 text-center text-xs font-semibold text-slate-400">
        {isVi ? "Không có dữ liệu dòng." : "No rows parsed."}
      </div>
    );
  }
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
                  {formatCell(row[column], isVi)}
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

export function formatBooleanLocalized(val: boolean, isVi: boolean): string {
  return val ? (isVi ? "Có" : "Yes") : (isVi ? "Không" : "No");
}

export function formatEmptyLocalized(val: unknown, isVi: boolean): string {
  return isVi ? "Không có" : "N/A";
}

export function humanizeMetricLabelLocalized(label: string, isVi: boolean): string {
  const mappingVi: Record<string, string> = {
    mean: "Trung bình",
    sum: "Tổng",
    median: "Trung vị",
    min: "Nhỏ nhất",
    max: "Lớn nhất",
    count: "Số lượng",
    number: "Số thực",
    percent: "Phần trăm",
    currency: "Tiền tệ",
    integer: "Số nguyên",
  };
  const mappingEn: Record<string, string> = {
    mean: "Average",
    sum: "Sum",
    median: "Median",
    min: "Minimum",
    max: "Maximum",
    count: "Count",
    number: "Float",
    percent: "Percentage",
    currency: "Currency",
    integer: "Integer",
  };
  return (isVi ? mappingVi[label.toLowerCase()] : mappingEn[label.toLowerCase()]) || label;
}

function formatCell(value: unknown, isVi = false) {
  if (value === null || value === undefined || value === "") return formatEmptyLocalized(value, isVi);
  if (typeof value === "boolean") return formatBooleanLocalized(value, isVi);
  if (typeof value === "number") {
    // If it's a decimal between 0 and 1, probably a percentage
    if (value > 0 && value < 1) return (value * 100).toFixed(2) + "%";
    return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  return String(value);
}
