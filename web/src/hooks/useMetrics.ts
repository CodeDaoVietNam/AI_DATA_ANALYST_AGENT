import { useState } from "react";
import type { MetricDefinition } from "../types";

export function useMetrics() {
  const [customMetrics, setCustomMetrics] = useState<MetricDefinition[]>([]);

  return {
    customMetrics,
    setCustomMetrics,
  };
}
