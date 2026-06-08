from typing import Dict, Any
import pandas as pd

from app.services.profiler import profile_dataframe
from app.tools.pandas_tool import answer_simple_question


class DataAnalystAgent:
    '''
    Rule-based starter agent.

    Why rule-based first?
    - It helps you understand the data workflow.
    - It avoids LLM hallucination.
    - Later, you can replace the intent router with LangChain/LangGraph tool-calling.
    '''

    def profile(self, df: pd.DataFrame) -> Dict[str, Any]:
        return profile_dataframe(df)

    def chat(self, df: pd.DataFrame, question: str) -> Dict[str, Any]:
        return answer_simple_question(df, question)
