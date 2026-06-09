import { useState, useRef } from "react";
import { listDatasets, uploadCsv, type WorkspaceDataset } from "../api";
import type { SummaryResponse, UploadResponse, AgentStatus } from "../types";
import { useI18n } from "../i18n";

export type UploadPhase =
  | "idle"
  | "uploading" // 0-30%
  | "reading"   // 30-60%
  | "profiling" // 60-90%
  | "building"  // 90-99%
  | "completed" // 100%
  | "failed";

export function useDatasetWorkspace() {
  const { t } = useI18n();
  const [upload, setUpload] = useState<UploadResponse | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [availableDatasets, setAvailableDatasets] = useState<WorkspaceDataset[]>([]);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");

  // Better upload feedback states
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadPhase, setUploadPhase] = useState<UploadPhase>("idle");
  const [selectedFileMeta, setSelectedFileMeta] = useState<{
    name: string;
    size: number;
    type: string;
  } | null>(null);

  const progressIntervalRef = useRef<number | null>(null);

  const datasetId = upload?.dataset_id;
  const columns = summary?.columns ?? [];

  // Helper to start progress simulation in a range
  const startProgressSimulation = (start: number, end: number, speedMs = 150) => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }
    setUploadProgress(start);
    progressIntervalRef.current = window.setInterval(() => {
      setUploadProgress((prev) => {
        if (prev < end) {
          return prev + 1;
        }
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
        }
        return prev;
      });
    }, speedMs);
  };

  const cancelUpload = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    setUploadProgress(0);
    setUploadPhase("idle");
    setSelectedFileMeta(null);
    setLoading("");
    setError("");
  };

  async function handleUpload(
    file: File,
    onUploaded: (uploaded: UploadResponse, updatePhase: (phase: UploadPhase, progress: number) => void) => Promise<void>
  ) {
    try {
      setError("");
      setLoading(t.app.messages.uploadingData);
      setSelectedFileMeta({
        name: file.name,
        size: file.size,
        type: file.type,
      });

      // Phase 1: Uploading file
      setUploadPhase("uploading");
      startProgressSimulation(0, 30, 80);

      const uploaded = await uploadCsv(file);
      setUpload(uploaded);

      // Phase 2: Reading dataset columns and rows
      setUploadPhase("reading");
      startProgressSimulation(30, 60, 50);

      // Call refresh/process logic in App.tsx
      await onUploaded(uploaded, (phase, progress) => {
        setUploadPhase(phase);
        startProgressSimulation(uploadProgress, progress, 30);
      });

      // Phase 5: Completed
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
      setUploadProgress(100);
      setUploadPhase("completed");
      setLoading("");

      const { datasets } = await listDatasets();
      setAvailableDatasets(datasets);
    } catch (err) {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
      setUploadProgress(0);
      setUploadPhase("failed");
      setLoading("");

      // Actionable error mapping
      const errMsg = err instanceof Error ? err.message : String(err);
      if (errMsg.includes("Failed to fetch") || errMsg.includes("NetworkError")) {
        setError(
          t.app.language === "vi" || true // Force Vietnamese for local user when selected
            ? "Không thể kết nối tới Backend API. Hãy chắc chắn rằng bạn đã khởi động server python bằng lệnh: make backend hoặc chạy uvicorn."
            : "Cannot connect to Backend API. Please ensure the python server is running using command: make backend or uvicorn."
        );
      } else if (file.size > 50 * 1024 * 1024) {
        setError(
          t.app.language === "vi" || true
            ? "File của bạn quá lớn (> 50MB). Vui lòng chọn một tệp CSV nhỏ hơn để phân tích trong phiên làm việc demo này."
            : "Your file is too large (> 50MB). Please select a smaller CSV file for analysis in this demo workspace."
        );
      } else {
        setError(
          t.app.language === "vi" || true
            ? `Phân tích tệp thất bại: ${errMsg}. Vui lòng kiểm tra định dạng file CSV có phân tách bằng dấu phẩy hợp lệ.`
            : `Failed to parse file: ${errMsg}. Please check if the CSV file format is valid and comma-separated.`
        );
      }
    }
  }

  async function handleSelectDataset(
    ds: WorkspaceDataset,
    onSelected: (mockUpload: UploadResponse, updatePhase: (phase: UploadPhase, progress: number) => void) => Promise<void>
  ) {
    try {
      setError("");
      setLoading(`${t.app.messages.switchingWorkspace} ${ds.filename}...`);
      setSelectedFileMeta({
        name: ds.filename,
        size: 0,
        type: "text/csv",
      });

      setUploadPhase("reading");
      startProgressSimulation(0, 50, 40);

      const mockUpload: UploadResponse = {
        dataset_id: ds.dataset_id,
        filename: ds.filename,
        rows: 0,
        columns: 0,
        message: "Switched",
      };
      setUpload(mockUpload);

      await onSelected(mockUpload, (phase, progress) => {
        setUploadPhase(phase);
        startProgressSimulation(uploadProgress, progress, 20);
      });

      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
      setUploadProgress(100);
      setUploadPhase("completed");
      setLoading("");
    } catch (err) {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
      setUploadProgress(0);
      setUploadPhase("failed");
      setLoading("");
      setError(err instanceof Error ? err.message : t.app.messages.switchDatasetFailed);
    }
  }

  return {
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
    handleUpload,
    handleSelectDataset,
  };
}
