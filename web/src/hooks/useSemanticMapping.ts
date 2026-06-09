import { useState } from "react";

export function useSemanticMapping() {
  const [mappingStatus, setMappingStatus] = useState<string>("idle");

  return {
    mappingStatus,
    setMappingStatus,
  };
}
