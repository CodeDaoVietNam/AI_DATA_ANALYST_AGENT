import { useI18n } from "../i18n";
import type { DashboardResponse } from "../types";
import { Database, AlertTriangle, CheckCircle, ChevronDown, ChevronUp } from "lucide-react";

export function SemanticMappingSummary({
  dashboard,
  onToggleAdvanced,
  isAdvancedOpen,
}: {
  dashboard: DashboardResponse;
  onToggleAdvanced: () => void;
  isAdvancedOpen: boolean;
}) {
  const { language } = useI18n();
  const isVi = language === "vi";

  // Friendly role names mapper
  const roleLabelsVi: Record<string, string> = {
    revenue: "Doanh thu / giá trị",
    cost: "Chi phí",
    profit: "Lợi nhuận",
    margin: "Biên lợi nhuận",
    discount: "Chiết khấu / giảm giá",
    date: "Ngày",
    category: "Nhóm / phân loại",
    segment: "Phân khúc",
    quantity: "Số lượng",
    city: "Thành phố",
    state: "Tỉnh / Bang",
    country: "Quốc gia",
    customer: "Khách hàng",
    target: "Kết quả cần dự đoán/theo dõi",
    conversion: "Tỷ lệ chuyển đổi",
  };

  const roleLabelsEn: Record<string, string> = {
    revenue: "Revenue / Value",
    cost: "Cost",
    profit: "Profit",
    margin: "Margin",
    discount: "Discount",
    date: "Date",
    category: "Category / Classification",
    segment: "Segment",
    quantity: "Quantity",
    city: "City",
    state: "State / Province",
    country: "Country",
    customer: "Customer",
    target: "Target / Predict outcome",
    conversion: "Conversion rate",
  };

  const roleLabels = isVi ? roleLabelsVi : roleLabelsEn;

  // Format domain names
  const domainNamesVi: Record<string, string> = {
    ecommerce: "Thương mại điện tử (E-commerce)",
    retail: "Bán lẻ (Retail)",
    marketing: "Tiếp thị (Marketing)",
    hr: "Nhân sự (HR)",
    finance: "Tài chính (Finance)",
    logistics: "Logistics & Vận chuyển",
    education: "Giáo dục (Education)",
    survey: "Khảo sát (Survey)",
    product: "Sản phẩm (Product)",
    generic: "Dữ liệu chung (Generic)",
  };

  const domainNamesEn: Record<string, string> = {
    ecommerce: "E-commerce",
    retail: "Retail",
    marketing: "Marketing",
    hr: "Human Resources (HR)",
    finance: "Finance",
    logistics: "Logistics",
    education: "Education",
    survey: "Survey",
    product: "Product Analytics",
    generic: "General Data",
  };

  const domainNames = isVi ? domainNamesVi : domainNamesEn;

  const detectedDomain = dashboard.domain || "generic";
  const domainLabel = domainNames[detectedDomain] || detectedDomain;
  const confidence = Math.round((dashboard.semantic_profile.domain_confidence ?? 0.5) * 100);

  // Extract mapped roles
  const mappedRoles = Object.entries(dashboard.semantic_profile.roles)
    .filter(([_, match]) => match && match.column)
    .map(([role, match]) => ({
      role,
      column: match.column,
      label: roleLabels[role] || role,
    }));

  // Check if critical roles are missing based on domain
  const criticalRolesByDomain: Record<string, string[]> = {
    ecommerce: ["date", "revenue", "category"],
    retail: ["date", "revenue", "category"],
    marketing: ["date", "campaign"],
    hr: ["employee", "target"],
    finance: ["date", "revenue"],
  };

  const criticals = criticalRolesByDomain[detectedDomain] || ["date"];
  const missingCriticals = criticals.filter(
    (role) => !dashboard.semantic_profile.roles[role]?.column
  );

  const isHighConfidence = confidence >= 75 && missingCriticals.length === 0;

  // Recommendation message
  let recommendationTitle = "";
  let recommendationDesc = "";
  let isWarning = false;

  if (isVi) {
    if (isHighConfidence) {
      recommendationTitle = "Độ tin cậy cao - Sẵn sàng phân tích";
      recommendationDesc = "Hệ thống tự động nhận diện chính xác các cột quan trọng. Bạn có thể đặt câu hỏi cho AI hoặc xem dashboard ngay.";
    } else if (missingCriticals.length > 0) {
      recommendationTitle = "Cần tối ưu hóa mapping cột";
      recommendationDesc = `Dashboard thiếu cấu hình một số cột cốt lõi: ${missingCriticals
        .map((r) => roleLabels[r] || r)
        .join(", ")}. Hãy mở Cấu hình nâng cao phía dưới để gắn cột thủ công.`;
      isWarning = true;
    } else {
      recommendationTitle = "Độ tin cậy trung bình";
      recommendationDesc = "Các cột chính đã được nhận diện, nhưng bạn nên kiểm tra lại xem tên cột đã chính xác chưa nếu kết quả tính toán bị lệch.";
    }
  } else {
    if (isHighConfidence) {
      recommendationTitle = "High Confidence - Ready for Analysis";
      recommendationDesc = "We have auto-mapped columns accurately. You can query AI Copilot or review dashboards directly.";
    } else if (missingCriticals.length > 0) {
      recommendationTitle = "Column Mapping Optimization Recommended";
      recommendationDesc = `Dashboard is missing mappings for crucial columns: ${missingCriticals
        .map((r) => roleLabels[r] || r)
        .join(", ")}. Use Advanced settings below to manually bind them.`;
      isWarning = true;
    } else {
      recommendationTitle = "Medium Confidence Mapping";
      recommendationDesc = "Primary columns are mapped, but we suggest a quick review in Advanced panel if dashboard metrics look off.";
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
              {isVi ? "Ý NGHĨA DỮ LIỆU TỰ ĐỘNG" : "AUTOMATED SEMANTIC PROFILE"}
            </span>
          </div>
          <h3 className="text-lg font-black tracking-tight text-slate-900 capitalize">
            {isVi ? "Ý nghĩa & Cấu trúc đã nhận diện" : "Inferred Structure & Meanings"}
          </h3>
          <p className="text-[12px] text-slate-500 leading-relaxed max-w-xl">
            {isVi
              ? "Hệ thống tự động hiểu ý nghĩa các cột (ngày, doanh thu, phân loại) để vẽ biểu đồ và chạy AI Copilot mà bạn không cần lập trình."
              : "The system automatically comprehends column concepts (date, revenue, categories) to build charts and feed AI Copilot without manual coding."}
          </p>
        </div>

        <div className="rounded-xl bg-slate-50 border border-slate-100 p-3 text-right">
          <div className="text-[10px] font-bold text-slate-400 uppercase">
            {isVi ? "Lĩnh vực (Domain)" : "Domain Area"}
          </div>
          <div className="text-sm font-black text-slate-800">{domainLabel}</div>
          <div className="text-[11px] text-slate-400">
            {isVi ? "Độ tin cậy" : "Confidence"}: <span className="font-semibold text-slate-700">{confidence}%</span>
          </div>
        </div>
      </div>

      {/* Mapped columns overview */}
      <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {mappedRoles.map(({ role, column, label }) => (
          <div
            key={role}
            className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50/50 px-3.5 py-2.5 hover:bg-slate-50 transition-colors"
          >
            <div className="min-w-0">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">{label}</div>
              <div className="truncate text-xs font-mono font-semibold text-slate-700 mt-0.5">{column}</div>
            </div>
            <Database className="h-3.5 w-3.5 text-slate-400 shrink-0" />
          </div>
        ))}
        {mappedRoles.length === 0 && (
          <div className="col-span-full py-4 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-xl">
            {isVi ? "Chưa nhận dạng được cột semantic nào." : "No semantic columns mapped yet."}
          </div>
        )}
      </div>

      {/* Recommendation Card */}
      <div
        className={`mt-4 rounded-xl border p-4 flex gap-3.5 items-start ${
          isWarning
            ? "border-amber-100 bg-amber-50/50 text-amber-900"
            : "border-emerald-100 bg-emerald-50/30 text-emerald-950"
        }`}
      >
        {isWarning ? (
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
        ) : (
          <CheckCircle className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
        )}
        <div className="space-y-1">
          <h4 className="text-xs font-bold tracking-tight">
            {recommendationTitle}
          </h4>
          <p className="text-[11px] leading-relaxed opacity-90">
            {recommendationDesc}
          </p>
        </div>
      </div>

      {/* Toggle Advanced Button */}
      <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
        <span className="text-[11px] text-slate-400 italic">
          {isVi
            ? "Bạn chỉ cần chỉnh nâng cao nếu dashboard nhận diện sai cột hoặc muốn tự định nghĩa metric."
            : "Adjust advanced parameters only if columns are misidentified or to define custom metrics."}
        </span>
        <button
          onClick={onToggleAdvanced}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-sm"
        >
          {isAdvancedOpen ? (
            <>
              {isVi ? "Ẩn cấu hình nâng cao" : "Hide Advanced Settings"}
              <ChevronUp className="h-3.5 w-3.5 text-slate-500" />
            </>
          ) : (
            <>
              {isVi ? "Tùy chỉnh mapping & metric" : "Customize Mapping & Metrics"}
              <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
