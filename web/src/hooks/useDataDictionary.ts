import { useState } from "react";
import type { DataDictionaryResponse } from "../types";

export function useDataDictionary() {
  const [dataDictionary, setDataDictionary] = useState<DataDictionaryResponse | null>(null);

  return {
    dataDictionary,
    setDataDictionary,
  };
}
