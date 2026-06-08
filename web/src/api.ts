import type { AgentResponse, AgentStatus, DashboardResponse, DataDictionary, DataDictionaryResponse, EcommerceOverview, ItemsResponse, MetricDefinition, MetricEvaluationResponse, MetricListResponse, MetricResponse, SemanticProfile, SummaryResponse, SummaryWrapper, UploadResponse } from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  `${window.location.protocol}//${window.location.hostname}:8000`;

const API_KEY = import.meta.env.VITE_API_KEY || "";

function apiBaseCandidates(): string[] {
  const protocol = window.location.protocol;
  const candidates = [
    API_BASE_URL,
    `${protocol}//${window.location.hostname}:8000`,
    `${protocol}//127.0.0.1:8000`,
    `${protocol}//localhost:8000`,
  ];
  return Array.from(new Set(candidates.map((item) => item.replace(/\/$/, ""))));
}

function backendReachabilityMessage(error?: unknown): string {
  const targets = apiBaseCandidates().join(", ");
  const suffix = error instanceof Error ? ` Last browser error: ${error.message}` : "";
  return `Cannot reach backend at ${targets}. Make sure FastAPI is running with: uvicorn app.main:app --reload.${suffix}`;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (API_KEY) {
    headers.set("X-API-Key", API_KEY);
  }
  let lastNetworkError: unknown;
  for (const baseUrl of apiBaseCandidates()) {
    let response: Response;
    try {
      response = await fetch(`${baseUrl}${path}`, {
        ...init,
        headers,
      });
    } catch (error) {
      lastNetworkError = error;
      continue;
    }
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Request failed with status ${response.status}`);
    }
    return response.json() as Promise<T>;
  }
  throw new Error(backendReachabilityMessage(lastNetworkError));
}

export async function uploadCsv(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson<UploadResponse>("/upload", {
    method: "POST",
    body: formData,
  });
}

export function getSummary(datasetId: string): Promise<SummaryResponse> {
  return requestJson<SummaryResponse>(`/summary/${datasetId}`);
}

export function getEcommerceOverview(datasetId: string): Promise<EcommerceOverview> {
  return requestJson<EcommerceOverview>(`/ecommerce/overview/${datasetId}`);
}

export function getRevenueByCategory(datasetId: string): Promise<ItemsResponse> {
  return requestJson<ItemsResponse>(`/ecommerce/revenue-by-category/${datasetId}`);
}

export function getRevenueByMonth(datasetId: string): Promise<ItemsResponse> {
  return requestJson<ItemsResponse>(`/ecommerce/revenue-by-month/${datasetId}`);
}

export function getTopStates(datasetId: string): Promise<ItemsResponse> {
  return requestJson<ItemsResponse>(`/ecommerce/top-states/${datasetId}`);
}

export function getTopSkus(datasetId: string, n = 20): Promise<ItemsResponse> {
  return requestJson<ItemsResponse>(`/ecommerce/top-skus/${datasetId}?n=${n}`);
}

export function getRevenueBySize(datasetId: string): Promise<ItemsResponse> {
  return requestJson<ItemsResponse>(`/ecommerce/revenue-by-size/${datasetId}`);
}

export function getCategoryCancellation(datasetId: string): Promise<ItemsResponse> {
  return requestJson<ItemsResponse>(`/ecommerce/category-cancellation/${datasetId}`);
}

export function getFulfilment(datasetId: string): Promise<ItemsResponse> {
  return requestJson<ItemsResponse>(`/ecommerce/fulfilment/${datasetId}`);
}

export function getCourier(datasetId: string): Promise<ItemsResponse> {
  return requestJson<ItemsResponse>(`/ecommerce/courier/${datasetId}`);
}

export function getPromotion(datasetId: string): Promise<SummaryWrapper> {
  return requestJson<SummaryWrapper>(`/ecommerce/promotion/${datasetId}`);
}

export function getB2B(datasetId: string): Promise<SummaryWrapper> {
  return requestJson<SummaryWrapper>(`/ecommerce/b2b/${datasetId}`);
}

export function getTopCities(datasetId: string, n = 20): Promise<ItemsResponse> {
  return requestJson<ItemsResponse>(`/ecommerce/top-cities/${datasetId}?n=${n}`);
}

export function getStateCancellation(datasetId: string, minOrders = 1000, n = 20): Promise<ItemsResponse> {
  return requestJson<ItemsResponse>(`/ecommerce/state-cancellation/${datasetId}?min_orders=${minOrders}&n=${n}`);
}

export function getReport(datasetId: string): Promise<{ report_markdown: string }> {
  return requestJson<{ report_markdown: string }>(`/report/${datasetId}`);
}

export function generateChart(payload: {
  dataset_id: string;
  chart_type: string;
  x: string;
  y?: string;
}): Promise<{ chart: { data: unknown[]; layout: Record<string, unknown> } }> {
  return requestJson("/chart", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function askAgent(datasetId: string, question: string): Promise<AgentResponse> {
  return requestJson<AgentResponse>("/agent/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId, question, mode: "balanced" }),
  });
}

export async function askAgentStream(
  datasetId: string,
  question: string,
  onEvent: (event: string, data: Record<string, unknown>) => void,
): Promise<AgentResponse> {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (API_KEY) {
    headers.set("X-API-Key", API_KEY);
  }
  let response: Response | null = null;
  let lastNetworkError: unknown;
  for (const baseUrl of apiBaseCandidates()) {
    try {
      response = await fetch(`${baseUrl}/agent/chat/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify({ dataset_id: datasetId, question, mode: "balanced" }),
      });
      break;
    } catch (error) {
      lastNetworkError = error;
    }
  }
  if (!response) {
    throw new Error(backendReachabilityMessage(lastNetworkError));
  }
  if (!response.ok || !response.body) {
    const text = await response.text();
    throw new Error(text || `Stream request failed with status ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResponse: AgentResponse | null = null;

  function parseBlock(block: string) {
    const eventLine = block.split("\n").find((line) => line.startsWith("event:"));
    const dataLine = block.split("\n").find((line) => line.startsWith("data:"));
    if (!eventLine || !dataLine) return;
    const event = eventLine.replace("event:", "").trim();
    const rawData = dataLine.replace("data:", "").trim();
    const data = JSON.parse(rawData) as Record<string, unknown>;
    onEvent(event, data);
    if (event === "final") {
      finalResponse = data as AgentResponse;
    }
    if (event === "error") {
      throw new Error(String(data.answer || data.error || "Agent stream failed"));
    }
  }

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    for (const block of blocks) {
      if (block.trim()) parseBlock(block);
    }
  }
  if (buffer.trim()) parseBlock(buffer);
  if (!finalResponse) throw new Error("Agent stream ended without a final response.");
  return finalResponse;
}

export function getAgentStatus(): Promise<AgentStatus> {
  return requestJson<AgentStatus>("/agent/status");
}

export function getSemanticProfile(datasetId: string): Promise<SemanticProfile> {
  return requestJson<SemanticProfile>(`/semantic-profile/${datasetId}`);
}

export function getDashboard(datasetId: string): Promise<DashboardResponse> {
  return requestJson<DashboardResponse>(`/dashboard/${datasetId}`);
}

export function getDataDictionary(datasetId: string): Promise<DataDictionaryResponse> {
  return requestJson<DataDictionaryResponse>(`/datasets/${datasetId}/data-dictionary`);
}

export async function uploadDataDictionary(datasetId: string, file: File): Promise<DataDictionaryResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson<DataDictionaryResponse>(`/datasets/${datasetId}/data-dictionary`, {
    method: "POST",
    body: formData,
  });
}

export function saveDataDictionary(datasetId: string, dictionary: DataDictionary): Promise<DataDictionaryResponse> {
  return requestJson<DataDictionaryResponse>(`/datasets/${datasetId}/data-dictionary`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dictionary),
  });
}

export function deleteDataDictionary(datasetId: string): Promise<{ dataset_id: string; deleted: boolean }> {
  return requestJson<{ dataset_id: string; deleted: boolean }>(`/datasets/${datasetId}/data-dictionary`, {
    method: "DELETE",
  });
}

export function getMetrics(datasetId: string): Promise<MetricListResponse> {
  return requestJson<MetricListResponse>(`/datasets/${datasetId}/metrics`);
}

export function createMetric(datasetId: string, metric: MetricDefinition): Promise<MetricResponse> {
  return requestJson<MetricResponse>(`/datasets/${datasetId}/metrics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(metric),
  });
}

export function updateMetric(datasetId: string, metricName: string, metric: MetricDefinition): Promise<MetricResponse> {
  return requestJson<MetricResponse>(`/datasets/${datasetId}/metrics/${metricName}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(metric),
  });
}

export function deleteMetric(datasetId: string, metricName: string): Promise<{ dataset_id: string; metric_name: string; deleted: boolean }> {
  return requestJson<{ dataset_id: string; metric_name: string; deleted: boolean }>(`/datasets/${datasetId}/metrics/${metricName}`, {
    method: "DELETE",
  });
}

export function evaluateMetric(datasetId: string, metricName: string): Promise<MetricEvaluationResponse> {
  return requestJson<MetricEvaluationResponse>(`/datasets/${datasetId}/metrics/${metricName}/evaluate`, {
    method: "POST",
  });
}

export function saveSemanticOverrides(
  datasetId: string,
  payload: { domain?: string | null; roles: Record<string, string | null> },
): Promise<SemanticProfile> {
  return requestJson<SemanticProfile>(`/semantic-profile/${datasetId}/overrides`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function resetSemanticOverrides(datasetId: string): Promise<SemanticProfile> {
  return requestJson<SemanticProfile>(`/semantic-profile/${datasetId}/overrides`, {
    method: "DELETE",
  });
}

export type WorkspaceDataset = { dataset_id: string; filename: string };

export function listDatasets(): Promise<{ datasets: WorkspaceDataset[] }> {
  return requestJson<{ datasets: WorkspaceDataset[] }>("/datasets");
}
