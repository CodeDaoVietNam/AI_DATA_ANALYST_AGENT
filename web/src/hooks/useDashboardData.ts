import { useState } from "react";
import type { DashboardResponse } from "../types";

export function useDashboardData() {
  const [smartDashboard, setSmartDashboard] = useState<DashboardResponse | null>(null);

  return {
    smartDashboard,
    setSmartDashboard,
  };
}
