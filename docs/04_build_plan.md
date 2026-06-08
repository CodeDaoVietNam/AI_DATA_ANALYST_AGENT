# 04 - Build Plan

## Phase 1 - Deterministic EDA Engine

Goal: Build the data analysis layer without LLM.

Tasks:

- Read CSV
- Validate file
- Infer column types
- Generate missing-value report
- Generate numeric summary
- Generate categorical summary
- Generate markdown report

Deliverable:

```bash
python scripts/analyze.py data/sample/ecommerce_sales.csv
```

## Phase 2 - Backend API

Goal: Expose analysis as API.

Tasks:

- POST /upload
- GET /summary/{dataset_id}
- POST /chat
- GET /report/{dataset_id}

Deliverable:

```bash
uvicorn app.main:app --reload
```

## Phase 3 - Frontend

Goal: Make the project demo-friendly.

Tasks:

- Upload CSV
- Show dataset overview
- Show missing values
- Chat with dataset
- Export report

Deliverable:

```bash
streamlit run frontend/streamlit_app.py
```

## Phase 4 - Add LLM Insight Generator

Goal: Let the LLM explain tool results.

Tasks:

- Add OpenAI API key
- Send Pandas-computed statistics to model
- Get structured JSON output
- Display summary, insights, warnings

Important:

The LLM should explain results, not compute them.

## Phase 5 - Add LangChain / LangGraph Agent

Goal: Replace rule-based router with real tool-calling agent.

Tools to implement:

- profile_data_tool
- missing_values_tool
- groupby_aggregate_tool
- chart_tool
- correlation_tool
- outlier_tool

## Phase 6 - Production Polish

Tasks:

- Docker Compose
- Better README
- Screenshots
- Unit tests
- Error handling
- Logging
- CV description
