from typing import Dict, Any
import pandas as pd


def answer_simple_question(df: pd.DataFrame, question: str) -> Dict[str, Any]:
    q = question.lower()

    if "missing" in q or "null" in q or "thiếu" in q:
        result = df.isna().sum().sort_values(ascending=False).to_dict()
        return {
            "type": "missing_values",
            "answer": "Đây là số lượng missing values theo từng cột.",
            "data": result
        }

    if "duplicate" in q or "trùng" in q:
        result = int(df.duplicated().sum())
        return {
            "type": "duplicate_rows",
            "answer": f"Dataset có {result} dòng bị trùng.",
            "data": result
        }

    if "shape" in q or "bao nhiêu dòng" in q or "số dòng" in q:
        return {
            "type": "shape",
            "answer": f"Dataset có {df.shape[0]} dòng và {df.shape[1]} cột.",
            "data": {"rows": df.shape[0], "columns": df.shape[1]}
        }

    if "column" in q or "cột" in q:
        return {
            "type": "columns",
            "answer": "Các cột trong dataset là: " + ", ".join(df.columns),
            "data": list(df.columns)
        }

    return {
        "type": "fallback",
        "answer": (
            "Mình chưa hiểu câu hỏi này bằng rule-based engine. "
            "Ở bước nâng cấp, bạn sẽ dùng LLM tool-calling để phân tích câu hỏi linh hoạt hơn."
        ),
        "data": None
    }
