import { useState } from "react";
import { type ChatEntry } from "../components/AskCopilot";

export function useCopilotChat() {
  const [chatHistory, setChatHistory] = useState<ChatEntry[]>([]);
  const [questionDraft, setQuestionDraft] = useState("");

  return {
    chatHistory,
    setChatHistory,
    questionDraft,
    setQuestionDraft,
  };
}
