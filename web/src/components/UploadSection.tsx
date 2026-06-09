import { useI18n } from "../i18n";
import type { UploadResponse, DashboardResponse } from "../types";
import type { WorkspaceDataset } from "../api";
import type { UploadPhase } from "../hooks/useDatasetWorkspace";
import {
  Upload,
  Database,
  ArrowUpRight,
  Store,
  Users,
  Megaphone,
  CheckCircle,
  AlertOctagon,
  Loader2,
  FileText,
  X,
  RefreshCw,
  Gauge,
  HelpCircle,
} from "lucide-react";

// Format file size in readable unit
function formatBytes(bytes: number, decimals = 2) {
  if (!bytes || bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

export function UploadSection({
  onUpload,
  upload,
  availableDatasets,
  onSelectDataset,
  uploadProgress,
  uploadPhase,
  selectedFileMeta,
  cancelUpload,
  error,
  dashboard,
}: {
  onUpload: (file: File) => void;
  upload: UploadResponse | null;
  availableDatasets: WorkspaceDataset[];
  onSelectDataset: (ds: WorkspaceDataset) => void;
  uploadProgress: number;
  uploadPhase: UploadPhase;
  selectedFileMeta: { name: string; size: number; type: string } | null;
  cancelUpload: () => void;
  error: string;
  dashboard: DashboardResponse | null;
}) {
  const { language } = useI18n();
  const isVi = language === "vi";

  const sampleDomains = [
    {
      icon: Store,
      label: isVi ? "Bán lẻ / E-commerce" : "Retail / E-commerce",
      desc: isVi ? "Đơn hàng, SKU, ngày bán, doanh thu theo nhóm hàng" : "Orders, SKUs, sales date, category breakdown",
      color: "rgba(37,99,235,0.04)",
      border: "rgba(37,99,235,0.12)",
    },
    {
      icon: Users,
      label: isVi ? "Nhân sự / Attrition" : "HR / Attrition",
      desc: isVi ? "Lương, thâm niên, làm thêm giờ, tỷ lệ nghỉ việc" : "Salary, tenure, overtime, attrition factors",
      color: "rgba(16,185,129,0.04)",
      border: "rgba(16,185,129,0.12)",
    },
    {
      icon: Megaphone,
      label: isVi ? "Marketing & Campaign" : "Marketing Campaign",
      desc: isVi ? "Response rate, kênh mua sắm, giá trị chuyển đổi" : "Response rate, channels, conversion values",
      color: "rgba(245,158,11,0.04)",
      border: "rgba(245,158,11,0.12)",
    },
  ];

  // Map phase to localized text description
  const phaseLabelsVi = {
    idle: "Đang chờ tệp...",
    uploading: "Đang tải file lên máy chủ (0 - 30%)...",
    reading: "Máy chủ đang đọc cấu trúc tệp (30 - 60%)...",
    profiling: "Đang trích xuất profile & thống kê mô tả (60 - 90%)...",
    building: "Đang tạo thông tin dashboard thông minh (90 - 99%)...",
    completed: "Hoàn tất xử lý dữ liệu!",
    failed: "Đã có lỗi xảy ra.",
  };

  const phaseLabelsEn = {
    idle: "Awaiting file...",
    uploading: "Uploading file to server (0 - 30%)...",
    reading: "Reading file structure (30 - 60%)...",
    profiling: "Extracting semantic profiles (60 - 90%)...",
    building: "Synthesizing smart dashboard metadata (90 - 99%)...",
    completed: "Data ready for analysis!",
    failed: "Intake process failed.",
  };

  const phaseLabels = isVi ? phaseLabelsVi : phaseLabelsEn;
  const currentPhaseText = phaseLabels[uploadPhase];

  const isPending = uploadPhase !== "idle" && uploadPhase !== "completed" && uploadPhase !== "failed";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Drop zone / Upload State Cards */}
      {uploadPhase === "idle" ? (
        <div className="doppelrand">
          <div className="doppelrand-inner">
            <label className="drop-zone flex flex-col items-center py-10" style={{ cursor: "pointer" }}>
              <div
                className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl transition-transform hover:scale-105"
                style={{
                  background: "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)",
                  border: "1px solid rgba(37,99,235,0.2)",
                  boxShadow: "0 4px 16px rgba(37,99,235,0.08)",
                }}
              >
                <Upload style={{ width: 22, height: 22, color: "#2563eb" }} />
              </div>
              <h3 className="text-base font-bold text-slate-900 tracking-tight">
                {isVi ? "Kéo thả file dữ liệu vào đây" : "Drag and drop data file here"}
              </h3>
              <p className="mt-2 text-xs text-slate-500 max-w-sm text-center leading-relaxed px-4">
                {isVi
                  ? "Hỗ trợ tệp định dạng CSV (.csv). Hệ thống sẽ tự động quét ý nghĩa các cột và lập báo cáo phân tích."
                  : "Supports CSV format (.csv). The engine will automatically scan headers and construct smart dashboards."}
              </p>
              <div className="mt-6 btn-primary" style={{ pointerEvents: "none" }}>
                <Upload style={{ width: 13, height: 13 }} />
                <span>{isVi ? "Chọn file từ máy tính" : "Choose file from computer"}</span>
                <span
                  className="ml-1 flex h-5 w-5 items-center justify-center rounded-full"
                  style={{ background: "rgba(255,255,255,0.15)" }}
                >
                  <ArrowUpRight style={{ width: 10, height: 10 }} />
                </span>
              </div>
              <input
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) onUpload(file);
                  event.target.value = "";
                }}
              />
            </label>
          </div>
        </div>
      ) : isPending ? (
        /* Stepper progress card */
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4 animate-pulse">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 text-accent animate-spin" />
              <div>
                <h4 className="text-sm font-bold text-slate-900">{isVi ? "Đang nạp và xử lý tệp" : "Processing File..."}</h4>
                <p className="text-[11px] text-slate-400 mt-0.5 font-mono">{selectedFileMeta?.name}</p>
              </div>
            </div>
            <button
              onClick={cancelUpload}
              className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-400 hover:text-slate-700 hover:bg-slate-50 transition-colors shadow-sm"
              title={isVi ? "Hủy bỏ" : "Cancel"}
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* File Meta */}
          {selectedFileMeta && (
            <div className="flex gap-4 p-3 rounded-xl bg-slate-50 text-[11px] text-slate-500 border border-slate-100">
              <div>
                <span className="font-semibold text-slate-600">{isVi ? "Kích thước" : "Size"}:</span>{" "}
                {selectedFileMeta.size > 0 ? formatBytes(selectedFileMeta.size) : "n/a"}
              </div>
              <div>
                <span className="font-semibold text-slate-600">Định dạng:</span> CSV
              </div>
            </div>
          )}

          {/* Progress bar */}
          <div className="space-y-1.5">
            <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full bg-accent transition-all duration-300 rounded-full"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] font-semibold text-slate-400">
              <span>{currentPhaseText}</span>
              <span className="font-mono">{uploadProgress}%</span>
            </div>
          </div>
        </div>
      ) : uploadPhase === "failed" ? (
        /* Actionable Error Card */
        <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-6 shadow-sm space-y-4">
          <div className="flex items-start gap-3.5">
            <div className="h-10 w-10 rounded-xl bg-rose-100 flex items-center justify-center shrink-0 border border-rose-200">
              <AlertOctagon className="h-5 w-5 text-rose-600" />
            </div>
            <div className="space-y-1.5 min-w-0 flex-1">
              <h4 className="text-sm font-black text-rose-900 tracking-tight">
                {isVi ? "Lỗi phân tích dữ liệu tệp" : "Data Intake Failed"}
              </h4>
              <p className="text-xs text-rose-800 leading-relaxed font-semibold">{error}</p>
            </div>
          </div>

          {/* Help box */}
          <div className="rounded-xl border border-rose-200/40 bg-white/70 p-4 text-[11px] text-rose-950 space-y-2 leading-relaxed">
            <div className="font-bold flex items-center gap-1">
              <HelpCircle className="h-3.5 w-3.5 text-rose-600" />
              {isVi ? "Gợi ý khắc phục hành động:" : "Actionable Guidelines:"}
            </div>
            <ul className="list-disc pl-4 space-y-1">
              <li>
                {isVi
                  ? "Hãy chắc chắn Backend API đang chạy ở cổng 8000 (uvicorn app.main:app)."
                  : "Make sure Backend API is running on port 8000 (uvicorn app.main:app)."}
              </li>
              <li>
                {isVi
                  ? "Kiểm tra file có bị khóa hoặc lỗi định dạng CSV phân tách bằng dấu phẩy không."
                  : "Check if the file is locked or has syntax errors (must be comma-separated CSV)."}
              </li>
              <li>
                {isVi
                  ? "Tệp tải lên không được vượt quá giới hạn 50MB."
                  : "Uploaded file must not exceed the demo size limit of 50MB."}
              </li>
            </ul>
          </div>

          <div className="flex gap-2">
            <button
              onClick={cancelUpload}
              className="rounded-lg bg-rose-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-rose-700 flex items-center gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              {isVi ? "Thử lại tải tệp" : "Retry Upload"}
            </button>
            <button
              onClick={cancelUpload}
              className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50"
            >
              {isVi ? "Hủy bỏ" : "Cancel"}
            </button>
          </div>
        </div>
      ) : (
        /* Completed view summary card */
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/20 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-emerald-100 flex items-center justify-center border border-emerald-200">
                <CheckCircle className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <h4 className="text-sm font-black text-emerald-900 tracking-tight">
                  {isVi ? "Đã nạp dữ liệu thành công!" : "Data Loaded Successfully!"}
                </h4>
                <p className="text-[11px] text-emerald-700 mt-0.5">{upload?.filename}</p>
              </div>
            </div>
            <button
              onClick={cancelUpload}
              className="text-xs font-bold text-emerald-700 hover:text-emerald-900 flex items-center gap-1"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              {isVi ? "Tải tệp khác" : "Upload Another"}
            </button>
          </div>

          {/* Preview Info grid */}
          {upload && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-white rounded-xl border border-emerald-100 p-4 shadow-sm text-center">
              <div>
                <div className="text-[10px] font-bold text-slate-400 uppercase">{isVi ? "Số dòng" : "Rows"}</div>
                <div className="text-base font-black text-slate-800 mt-0.5">{upload.rows.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-slate-400 uppercase">{isVi ? "Số cột" : "Columns"}</div>
                <div className="text-base font-black text-slate-800 mt-0.5">{upload.columns.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-slate-400 uppercase">Domain</div>
                <div className="text-base font-black text-slate-800 mt-0.5 capitalize">
                  {dashboard?.domain || "generic"}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-slate-400 uppercase">{isVi ? "Cảnh báo" : "Warnings"}</div>
                <div className="text-base font-black text-slate-800 mt-0.5">
                  {dashboard?.warnings?.length || 0}
                </div>
              </div>
            </div>
          )}

          <div className="rounded-xl border border-emerald-100 bg-white p-3.5 text-xs text-emerald-900/80 leading-relaxed">
            ✨ {isVi ? "Hồ sơ phân tích đã sẵn sàng!" : "Workspace profile is compiled!"}{" "}
            <strong>
              {isVi
                ? "Vui lòng chọn tab 'Hồ sơ dữ liệu' hoặc 'Dashboard' phía trên để bắt đầu phân tích sâu."
                : "Select the 'Data Profile' or 'Dashboard' tabs above to begin deep exploration."}
            </strong>
          </div>
        </div>
      )}

      {/* Supported Data Domains info */}
      <div className="panel-shell">
        <p className="section-label mb-3">{isVi ? "Vùng dữ liệu được tối ưu tự động" : "Optimized Domain Categories"}</p>
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
          {sampleDomains.map((d) => {
            const Icon = d.icon;
            return (
              <div
                key={d.label}
                className="rounded-xl p-4 transition-all hover:shadow-sm"
                style={{ background: d.color, border: `1px solid ${d.border}` }}
              >
                <Icon style={{ width: 18, height: 18, marginBottom: 8, color: "var(--accent)" }} />
                <p className="text-[12px] font-bold text-slate-800">{d.label}</p>
                <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">{d.desc}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Dataset history */}
      {availableDatasets.length > 0 && (
        <div className="panel-shell">
          <p className="section-label mb-3">{isVi ? "Lịch sử dataset trong workspace" : "Workspace Dataset History"}</p>
          <div className="space-y-1.5 max-h-[200px] overflow-y-auto pr-1">
            {availableDatasets.map((ds) => {
              const isActive = upload?.dataset_id === ds.dataset_id;
              return (
                <button
                  key={ds.dataset_id}
                  onClick={() => onSelectDataset(ds)}
                  className="w-full flex items-center justify-between rounded-xl px-3.5 py-3 text-left transition-all"
                  style={{
                    background: isActive ? "rgba(37,99,235,0.04)" : "var(--surface)",
                    border: `1px solid ${isActive ? "rgba(37,99,235,0.18)" : "var(--border)"}`,
                  }}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Database
                      style={{ width: 13, height: 13, color: isActive ? "#2563eb" : "#94a3b8", flexShrink: 0 }}
                    />
                    <span className="text-[12px] font-bold text-slate-700 truncate">{ds.filename}</span>
                  </div>
                  <span
                    className="text-[10px] font-bold uppercase tracking-wider shrink-0"
                    style={{ color: isActive ? "#2563eb" : "var(--text-muted)" }}
                  >
                    {isActive ? (isVi ? "Đang mở" : "Active") : (isVi ? "Mở lại" : "Restore")}
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
