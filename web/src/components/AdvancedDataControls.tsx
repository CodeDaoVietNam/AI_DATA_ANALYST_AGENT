import { useState } from "react";
import { useI18n } from "../i18n";
import type {
  DashboardResponse,
  DataDictionary,
  DataDictionaryResponse,
  MetricDefinition,
  MetricEvaluationResponse,
  RecordRow,
} from "../types";
import {
  Database,
  Layers,
  TrendingUp,
  Settings,
  HelpCircle,
  Cpu,
  FileSpreadsheet,
  Plus,
  Trash2,
  Play,
  RotateCcw,
} from "lucide-react";

// Local helper to humanize metric token expressions
function toMetricExpressionToken(col: string) {
  return col.replace(/[^a-zA-Z0-9_]/g, "_");
}

export function AdvancedDataControls({
  dashboard,
  dataDictionary,
  customMetrics,
  columns,
  onSaveSemanticOverrides,
  onResetSemanticOverrides,
  onUploadDataDictionary,
  onSaveDataDictionary,
  onDeleteDataDictionary,
  onSaveMetric,
  onDeleteMetric,
  onEvaluateMetric,
}: {
  dashboard: DashboardResponse;
  dataDictionary: DataDictionaryResponse | null;
  customMetrics: MetricDefinition[];
  columns: string[];
  onSaveSemanticOverrides: (payload: { domain?: string | null; roles: Record<string, string | null> }) => void;
  onResetSemanticOverrides: () => void;
  onUploadDataDictionary: (file: File) => void;
  onSaveDataDictionary: (dictionary: DataDictionary) => void;
  onDeleteDataDictionary: () => void;
  onSaveMetric: (metric: MetricDefinition, previousName?: string | null) => Promise<void>;
  onDeleteMetric: (metricName: string) => Promise<void>;
  onEvaluateMetric: (metricName: string) => Promise<MetricEvaluationResponse | null>;
}) {
  const { language, t } = useI18n();
  const isVi = language === "vi";

  type TabType = "mapping" | "dictionary" | "metrics" | "debug";
  const [activeTab, setActiveTab] = useState<TabType>("mapping");

  // Semantic Mapping state copies
  const [domainDraft, setDomainDraft] = useState(
    dashboard.semantic_profile.overrides?.domain || dashboard.domain
  );
  const [roleDraft, setRoleDraft] = useState<Record<string, string>>(
    Object.fromEntries(
      Object.entries(dashboard.semantic_profile.roles).map(([role, match]) => [role, match.column || ""])
    )
  );

  // Data Dictionary state copies
  const [dictionaryDraft, setDictionaryDraft] = useState<DataDictionary>(() => {
    const currentDictionary = dataDictionary?.dictionary;
    const fieldsByColumn = new Map((currentDictionary?.fields || []).map((field) => [field.column_name, field]));
    const dictionaryColumns =
      columns.length > 0
        ? columns
        : Array.from(
            new Set([
              ...Object.values(dashboard.semantic_profile.roles).map((match) => match.column || ""),
              ...dashboard.semantic_profile.unmatched_columns,
            ])
          ).filter(Boolean);

    return {
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
    };
  });

  // Metric Builder state copies
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
  const [metricError, setMetricError] = useState("");

  const candidateRoles = Object.keys(dashboard.semantic_profile.candidates || dashboard.semantic_profile.roles).sort();
  const allColumns = Array.from(
    new Set([
      ...Object.values(dashboard.semantic_profile.roles).map((match) => match.column || ""),
      ...Object.values(dashboard.semantic_profile.candidates || {})
        .flat()
        .map((candidate) => candidate.column),
      ...dashboard.semantic_profile.unmatched_columns,
    ])
  ).filter((column): column is string => Boolean(column));

  const domainOptions = ["ecommerce", "retail", "marketing", "hr", "finance", "logistics", "education", "survey", "product", "generic"];
  const roleOptions = [
    "",
    "revenue",
    "cost",
    "profit",
    "margin",
    "discount",
    "date",
    "category",
    "segment",
    "quantity",
    "city",
    "state",
    "country",
    "customer",
    "campaign",
    "channel",
    "employee",
    "department",
    "job_role",
    "salary",
    "target",
    "conversion",
    "overtime",
    "tenure",
    "recency",
    "monetary",
    "frequency",
  ];
  const dataTypeOptions = ["", "string", "number", "date", "boolean", "categorical"];
  const aggregationOptions = ["", "sum", "mean", "count", "min", "max", "median"];
  const metricFormatOptions: MetricDefinition["format"][] = ["number", "percent", "currency", "integer"];
  const metricAggregationOptions: MetricDefinition["aggregation"][] = ["mean", "sum", "median", "min", "max", "count"];
  const expressionTokens = Array.from(
    new Set([...Object.keys(dashboard.semantic_profile.roles), ...allColumns.map(toMetricExpressionToken)])
  )
    .filter(Boolean)
    .slice(0, 28);

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
    setMetricError("");
  }

  function resetMetricDraft() {
    setEditingMetricName(null);
    setMetricDraft(emptyMetricDraft);
    setMetricPreview(null);
    setMetricError("");
  }

  async function handleSaveMetricDraft() {
    try {
      setMetricError("");
      await onSaveMetric(
        {
          ...metricDraft,
          name: metricDraft.name.trim(),
          label: metricDraft.label?.trim() || metricDraft.name.trim(),
          description: metricDraft.description?.trim() || null,
          expression: metricDraft.expression.trim(),
          required_roles: metricDraft.required_roles.filter(Boolean),
        },
        editingMetricName
      );
      resetMetricDraft();
    } catch (err) {
      setMetricError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleEvaluateMetricDraft() {
    const metricName = editingMetricName || metricDraft.name.trim();
    if (!metricName) return;
    try {
      setMetricError("");
      const result = await onEvaluateMetric(metricName);
      if (result) {
        setMetricPreview(result);
      }
    } catch (err) {
      setMetricError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleDeleteSelectedMetric() {
    if (!editingMetricName) return;
    try {
      setMetricError("");
      await onDeleteMetric(editingMetricName);
      resetMetricDraft();
    } catch (err) {
      setMetricError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <h4 className="text-sm font-black tracking-tight text-slate-800 uppercase flex items-center gap-1.5">
            <Settings className="h-4 w-4 text-accent" />
            {isVi ? "Cấu hình dữ liệu nâng cao" : "Advanced Data Settings"}
          </h4>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {isVi
              ? "Tùy chỉnh vai trò cột, mô tả từ điển và định nghĩa công thức cho dashboard."
              : "Customize column roles, dictionary details, and formulas for the smart dashboard."}
          </p>
        </div>

        {/* Tab Selection */}
        <div className="flex gap-1 bg-slate-50 rounded-lg p-0.5 border border-slate-200/60 self-start sm:self-auto">
          {(
            [
              { id: "mapping", label: isVi ? "Semantic Mapping" : "Semantic Mapping", icon: Layers },
              { id: "dictionary", label: isVi ? "Data Dictionary" : "Data Dictionary", icon: FileSpreadsheet },
              { id: "metrics", label: isVi ? "Metric Builder" : "Metric Builder", icon: TrendingUp },
              { id: "debug", label: isVi ? "Thông tin Raw" : "Raw Details", icon: Cpu },
            ] as const
          ).map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-bold transition-all ${
                  active
                    ? "bg-white text-slate-900 shadow-sm border border-slate-200/50"
                    : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                }`}
              >
                <Icon className="h-3 w-3" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab 1: Semantic Mapping Studio */}
      {activeTab === "mapping" && (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-[200px_1fr_auto_auto] items-end">
            <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
              {isVi ? "Vùng dữ liệu (Domain)" : "Domain Category"}
              <select
                value={domainDraft}
                onChange={(event) => setDomainDraft(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
              >
                {domainOptions.map((domain) => (
                  <option key={domain} value={domain}>
                    {domain}
                  </option>
                ))}
              </select>
            </label>
            <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-[11px] text-slate-500 italic">
              {(dashboard.semantic_profile.domain_reasons || []).join(" · ") ||
                (isVi ? "Domain được phán đoán từ dữ liệu phân tích." : "Domain was inferred from profiles.")}
            </div>
            <button
              onClick={() => onSaveSemanticOverrides({ domain: domainDraft, roles: roleDraft })}
              className="rounded-lg bg-accent px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-accent/90"
            >
              {isVi ? "Lưu mapping" : "Save Mapping"}
            </button>
            <button
              onClick={() => {
                onResetSemanticOverrides();
                setDomainDraft(dashboard.domain);
                setRoleDraft(
                  Object.fromEntries(
                    Object.entries(dashboard.semantic_profile.roles).map(([role, match]) => [role, match.column || ""])
                  )
                );
              }}
              className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 flex items-center gap-1"
            >
              <RotateCcw className="h-3 w-3" />
              {isVi ? "Đặt lại" : "Reset"}
            </button>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {candidateRoles.map((role) => (
              <div key={role} className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{role}</span>
                  <span className="text-[10px] font-semibold text-slate-400 bg-slate-100 rounded px-1.5 py-0.5">
                    {dashboard.semantic_profile.roles[role]?.confidence_label || "candidate"}
                  </span>
                </div>
                <select
                  value={roleDraft[role] || ""}
                  onChange={(event) => setRoleDraft((prev) => ({ ...prev, [role]: event.target.value }))}
                  className="w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs text-slate-700"
                >
                  <option value="">{isVi ? "Chưa map" : "Unmapped"}</option>
                  {allColumns.map((column) => (
                    <option key={`${role}-${column}`} value={column}>
                      {column}
                    </option>
                  ))}
                </select>
                <div className="text-[10px] leading-relaxed text-slate-400 italic">
                  {(dashboard.semantic_profile.candidates?.[role] || [])
                    .slice(0, 2)
                    .map((candidate) => `${candidate.column} (${Math.round(candidate.confidence * 100)}%)`)
                    .join(" · ") || (isVi ? "Không tìm thấy gợi ý cột." : "No candidates found.")}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Data Dictionary */}
      {activeTab === "dictionary" && (
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-end gap-3 justify-between">
            <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-[11px] text-slate-500">
              {isVi ? "Nguồn dữ liệu" : "Source"}: <span className="font-semibold text-slate-700">{dataDictionary?.source || "none"}</span>
              {(dataDictionary?.warnings || []).length > 0 && (
                <div className="mt-1 text-amber-700 font-semibold">
                  ⚠️ {dataDictionary!.warnings.join(" · ")}
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <label className="flex cursor-pointer items-center justify-center rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-600 shadow-sm hover:bg-slate-50">
                {isVi ? "Tải lên file CSV/JSON" : "Upload CSV/JSON"}
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
                className="rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-600 shadow-sm hover:bg-slate-50 hover:text-rose-600 hover:border-rose-200"
              >
                {isVi ? "Xóa dictionary" : "Delete Dictionary"}
              </button>
            </div>
          </div>

          <div className="flex flex-col md:flex-row md:items-end gap-3 justify-between">
            <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block max-w-xs w-full">
              {isVi ? "Domain khai báo" : "Declared Domain"}
              <select
                value={dictionaryDraft.domain || ""}
                onChange={(event) => setDictionaryDraft((prev) => ({ ...prev, domain: event.target.value || null }))}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs text-slate-700"
              >
                <option value="">{isVi ? "Tự động phát hiện" : "Auto detect"}</option>
                {domainOptions.map((domain) => (
                  <option key={domain} value={domain}>
                    {domain}
                  </option>
                ))}
              </select>
            </label>
            <button
              onClick={() =>
                onSaveDataDictionary({
                  domain: dictionaryDraft.domain || null,
                  fields: dictionaryDraft.fields.filter(
                    (field) =>
                      field.business_name ||
                      field.description ||
                      field.semantic_role ||
                      field.data_type ||
                      field.unit ||
                      field.aggregation ||
                      field.sensitive ||
                      field.allowed_values.length > 0
                  ),
                })
              }
              className="rounded-lg bg-accent px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-accent/90"
            >
              {isVi ? "Lưu dictionary" : "Save Dictionary"}
            </button>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-[1000px] w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-3 py-2.5">{isVi ? "Tên Cột" : "Column Name"}</th>
                  <th className="px-3 py-2.5">{isVi ? "Tên Tiếng Việt/Business" : "Business Name"}</th>
                  <th className="px-3 py-2.5">Role</th>
                  <th className="px-3 py-2.5">{isVi ? "Kiểu" : "Data Type"}</th>
                  <th className="px-3 py-2.5">Unit</th>
                  <th className="px-3 py-2.5">{isVi ? "Tổng hợp" : "Aggregation"}</th>
                  <th className="px-3 py-2.5">{isVi ? "Nhạy cảm" : "Sensitive"}</th>
                  <th className="px-3 py-2.5">{isVi ? "Giá trị" : "Allowed Values"}</th>
                  <th className="px-3 py-2.5">{isVi ? "Mô tả chi tiết" : "Description"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {dictionaryDraft.fields.map((field, index) => (
                  <tr key={field.column_name}>
                    <td className="px-3 py-2 font-mono text-[11px] font-bold text-slate-700">{field.column_name}</td>
                    <td className="px-3 py-2">
                      <input
                        value={field.business_name || ""}
                        onChange={(event) => updateDictionaryField(index, "business_name", event.target.value)}
                        className="w-full rounded-md border border-slate-200 px-2.5 py-1 text-xs"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={field.semantic_role || ""}
                        onChange={(event) => updateDictionaryField(index, "semantic_role", event.target.value)}
                        className="w-full rounded-md border border-slate-200 px-2.5 py-1 text-xs"
                      >
                        {roleOptions.map((role) => (
                          <option key={`${field.column_name}-${role || "none"}`} value={role}>
                            {role || (isVi ? "Trống" : "None")}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={field.data_type || ""}
                        onChange={(event) => updateDictionaryField(index, "data_type", event.target.value)}
                        className="w-full rounded-md border border-slate-200 px-2.5 py-1 text-xs"
                      >
                        {dataTypeOptions.map((dataType) => (
                          <option key={`${field.column_name}-${dataType || "auto"}`} value={dataType}>
                            {dataType || (isVi ? "Tự động" : "Auto")}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <input
                        value={field.unit || ""}
                        onChange={(event) => updateDictionaryField(index, "unit", event.target.value)}
                        className="w-full rounded-md border border-slate-200 px-2.5 py-1 text-xs"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={field.aggregation || ""}
                        onChange={(event) => updateDictionaryField(index, "aggregation", event.target.value)}
                        className="w-full rounded-md border border-slate-200 px-2.5 py-1 text-xs"
                      >
                        {aggregationOptions.map((aggregation) => (
                          <option key={`${field.column_name}-${aggregation || "none"}`} value={aggregation}>
                            {aggregation || (isVi ? "Trống" : "None")}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2 text-center">
                      <input
                        type="checkbox"
                        checked={field.sensitive}
                        onChange={(event) => updateDictionaryField(index, "sensitive", event.target.checked)}
                        className="h-3.5 w-3.5 text-accent rounded"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        value={(field.allowed_values || []).join("|")}
                        onChange={(event) =>
                          updateDictionaryField(
                            index,
                            "allowed_values",
                            event.target.value
                              .split("|")
                              .map((item) => item.trim())
                              .filter(Boolean)
                          )
                        }
                        placeholder="A|B|C"
                        className="w-full rounded-md border border-slate-200 px-2.5 py-1 text-xs"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        value={field.description || ""}
                        onChange={(event) => updateDictionaryField(index, "description", event.target.value)}
                        className="w-full rounded-md border border-slate-200 px-2.5 py-1 text-xs"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Metric Builder */}
      {activeTab === "metrics" && (
        <div className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-[280px_1fr]">
            {/* List Metrics */}
            <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 space-y-3">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                {isVi ? "Các metrics đã định nghĩa" : "Defined Metrics"}
              </div>
              <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
                {customMetrics.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-slate-200 bg-white p-3 text-[11px] leading-relaxed text-slate-400">
                    {isVi
                      ? "Chưa có metric tự chế nào. Hãy thử: margin = profit / revenue."
                      : "No custom metrics yet. Try setting margin = profit / revenue."}
                  </div>
                ) : (
                  customMetrics.map((metric) => (
                    <button
                      key={metric.name}
                      onClick={() => selectMetric(metric)}
                      className={`w-full rounded-lg border px-3 py-2 text-left shadow-sm transition-colors text-xs ${
                        editingMetricName === metric.name
                          ? "border-accent bg-accent/5 text-slate-900"
                          : "border-slate-150 bg-white hover:border-slate-300 text-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold">{metric.label || metric.name}</span>
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[8px] font-bold uppercase text-slate-500">
                          {metric.format}
                        </span>
                      </div>
                      <div className="mt-1 font-mono text-[9px] text-slate-400">{metric.expression}</div>
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* Metric Form */}
            <div className="space-y-3.5">
              {metricError && (
                <div className="rounded-lg border border-rose-100 bg-rose-50 px-3.5 py-2.5 text-xs text-rose-800 font-semibold">
                  {metricError}
                </div>
              )}

              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  {isVi ? "Tên Metric (Không dấu)" : "Metric Name (Slug)"}
                  <input
                    value={metricDraft.name}
                    onChange={(event) => setMetricDraft((prev) => ({ ...prev, name: event.target.value }))}
                    placeholder="margin"
                    disabled={editingMetricName !== null}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs font-mono text-slate-700 bg-white disabled:bg-slate-50"
                  />
                </label>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  {isVi ? "Nhãn hiển thị" : "Display Label"}
                  <input
                    value={metricDraft.label || ""}
                    onChange={(event) => setMetricDraft((prev) => ({ ...prev, label: event.target.value }))}
                    placeholder="Margin (%)"
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700 bg-white"
                  />
                </label>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  {isVi ? "Định dạng" : "Format"}
                  <select
                    value={metricDraft.format}
                    onChange={(event) =>
                      setMetricDraft((prev) => ({ ...prev, format: event.target.value as MetricDefinition["format"] }))
                    }
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700 bg-white"
                  >
                    {metricFormatOptions.map((format) => (
                      <option key={format} value={format}>
                        {format}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  {isVi ? "Cách tổng hợp" : "Aggregation"}
                  <select
                    value={metricDraft.aggregation}
                    onChange={(event) =>
                      setMetricDraft((prev) => ({
                        ...prev,
                        aggregation: event.target.value as MetricDefinition["aggregation"],
                      }))
                    }
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700 bg-white"
                  >
                    {metricAggregationOptions.map((agg) => (
                      <option key={agg} value={agg}>
                        {agg}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                {isVi ? "Công thức tính toán" : "Formula Expression"}
                <input
                  value={metricDraft.expression}
                  onChange={(event) => setMetricDraft((prev) => ({ ...prev, expression: event.target.value }))}
                  placeholder="profit / revenue"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-xs text-slate-700 bg-white"
                />
              </label>

              <div className="grid gap-3 lg:grid-cols-[1fr_200px]">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  {isVi ? "Mô tả ý nghĩa" : "Description / Purpose"}
                  <input
                    value={metricDraft.description || ""}
                    onChange={(event) => setMetricDraft((prev) => ({ ...prev, description: event.target.value }))}
                    placeholder={isVi ? "Tỷ suất lợi nhuận sau chi phí" : "Profit margin percentage"}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700 bg-white"
                  />
                </label>
                <label className="flex items-end gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-xs font-semibold text-slate-700 cursor-pointer self-end h-[36px]">
                  <input
                    type="checkbox"
                    checked={metricDraft.higher_is_better}
                    onChange={(event) =>
                      setMetricDraft((prev) => ({ ...prev, higher_is_better: event.target.checked }))
                    }
                    className="h-4 w-4 rounded text-accent"
                  />
                  <span>{isVi ? "Chỉ số cao là tốt" : "Higher is better"}</span>
                </label>
              </div>

              {/* Roles Selector */}
              <div>
                <div className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  {isVi ? "Semantic Roles bắt buộc" : "Required Semantic Roles"}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {roleOptions.filter(Boolean).map((role) => {
                    const active = metricDraft.required_roles.includes(role);
                    return (
                      <button
                        key={`metric-role-${role}`}
                        type="button"
                        onClick={() =>
                          setMetricDraft((prev) => ({
                            ...prev,
                            required_roles: prev.required_roles.includes(role)
                              ? prev.required_roles.filter((item) => item !== role)
                              : [...prev.required_roles, role],
                          }))
                        }
                        className={`rounded-md border px-2.5 py-1 text-[10px] font-bold transition-all ${
                          active
                            ? "border-accent bg-accent/5 text-accent"
                            : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
                        }`}
                      >
                        {role}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Suggestions token */}
              <div className="rounded-xl border border-slate-200 bg-white p-3 space-y-2">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  {isVi ? "Gợi ý click chèn nhanh token" : "Formula construction helper tokens"}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {expressionTokens.map((token) => (
                    <button
                      key={`token-${token}`}
                      type="button"
                      onClick={() =>
                        setMetricDraft((prev) => ({
                          ...prev,
                          expression: `${prev.expression}${prev.expression ? " " : ""}${token}`,
                        }))
                      }
                      className="rounded border border-slate-200 bg-slate-50/50 px-2 py-0.5 font-mono text-[10px] text-slate-600 hover:bg-slate-100 hover:border-slate-300"
                    >
                      {token}
                    </button>
                  ))}
                </div>
              </div>

              {/* Control Buttons */}
              <div className="flex flex-wrap gap-2 pt-2 items-center justify-between">
                <div className="flex gap-2">
                  <button
                    onClick={handleSaveMetricDraft}
                    disabled={!metricDraft.name.trim() || !metricDraft.expression.trim()}
                    className="rounded-lg bg-accent px-4 py-2 text-xs font-bold text-white hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    {isVi ? "Lưu metric" : "Save Metric"}
                  </button>
                  <button
                    onClick={handleEvaluateMetricDraft}
                    disabled={
                      !editingMetricName &&
                      !customMetrics.some((metric) => metric.name === metricDraft.name.trim())
                    }
                    className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                  >
                    <Play className="h-3 w-3" />
                    {isVi ? "Chạy test" : "Evaluate"}
                  </button>
                  <button
                    onClick={resetMetricDraft}
                    className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50"
                  >
                    {isVi ? "Tạo mới" : "Clear / New"}
                  </button>
                </div>

                {editingMetricName && (
                  <button
                    onClick={handleDeleteSelectedMetric}
                    className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-bold text-rose-700 hover:bg-rose-100 flex items-center gap-1"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    {isVi ? `Xóa ${editingMetricName}` : `Delete ${editingMetricName}`}
                  </button>
                )}
              </div>

              {/* Preview results */}
              {metricPreview && (
                <div className="rounded-xl border border-emerald-100 bg-emerald-50/20 p-3.5 mt-2 space-y-1.5">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">
                    {isVi ? "Kết quả đánh giá thử nghiệm" : "Evaluation Preview"}
                  </div>
                  <div className="overflow-x-auto rounded-lg border border-emerald-100/50 bg-white text-xs">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-emerald-50/40 text-emerald-950 font-bold border-b border-emerald-100">
                          {Object.keys(metricPreview.summary).map((key) => (
                            <th key={key} className="px-3 py-2 font-mono text-[10px]">
                              {key}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          {Object.values(metricPreview.summary).map((val, i) => (
                            <td key={i} className="px-3 py-2 font-mono">
                              {typeof val === "number" ? val.toLocaleString(undefined, { maximumFractionDigits: 4 }) : String(val)}
                            </td>
                          ))}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Raw Details Debug */}
      {activeTab === "debug" && (
        <div className="space-y-3">
          <div className="text-[11px] text-slate-500 leading-normal">
            {isVi
              ? "Dành cho kỹ thuật: Chi tiết độ tin cậy và nguồn ánh xạ gốc của các cột do AI nhận diện."
              : "For engineers: detailed confidence scores and origin sources for the mapped columns."}
          </div>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 font-bold uppercase text-[9px] border-b border-slate-200">
                  <th className="px-3 py-2">Role</th>
                  <th className="px-3 py-2">{isVi ? "Cột Ánh Xạ" : "Mapped Column"}</th>
                  <th className="px-3 py-2">{isVi ? "Độ tin cậy" : "Confidence"}</th>
                  <th className="px-3 py-2">{isVi ? "Mức độ" : "Confidence Level"}</th>
                  <th className="px-3 py-2">{isVi ? "Nguồn" : "Source"}</th>
                  <th className="px-3 py-2">{isVi ? "Nguyên do" : "Reason"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white font-mono text-[11px]">
                {Object.entries(dashboard.semantic_profile.roles).map(([role, match]) => (
                  <tr key={role}>
                    <td className="px-3 py-2 text-slate-900 font-bold">{role}</td>
                    <td className="px-3 py-2 text-slate-600">{match.column || "n/a"}</td>
                    <td className="px-3 py-2 text-slate-600">{(match.confidence * 100).toFixed(0)}%</td>
                    <td className="px-3 py-2 text-slate-600">{match.confidence_label}</td>
                    <td className="px-3 py-2 text-slate-600">{match.source || "auto"}</td>
                    <td className="px-3 py-2 text-[10px] text-slate-400 font-sans">{match.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
