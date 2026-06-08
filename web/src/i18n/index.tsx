import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { en } from "./en";
import { vi, type Translation } from "./vi";

export type Language = "vi" | "en";

const STORAGE_KEY = "ai-data-analyst-language";

const dictionaries: Record<Language, Translation> = { vi, en };

type I18nContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: Translation;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    if (typeof window === "undefined") return "vi";
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "en" || stored === "vi" ? stored : "vi";
  });

  function setLanguage(nextLanguage: Language) {
    setLanguageState(nextLanguage);
    window.localStorage.setItem(STORAGE_KEY, nextLanguage);
  }

  const value = useMemo(
    () => ({ language, setLanguage, t: dictionaries[language] }),
    [language],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used inside I18nProvider");
  }
  return context;
}
