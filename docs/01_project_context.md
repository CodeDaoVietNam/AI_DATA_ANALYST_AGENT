# 01 - Project Context

## Problem

Many students know how to train ML models, but fewer can build a real AI product.

This project helps you practice AI Engineering by building a useful product:

> Upload CSV → automatically analyze data → generate charts → write insights → chat with the dataset.

## Why this is valuable for internship

This project demonstrates:

- Python engineering
- Data analysis
- API development
- LLM integration
- Agent design
- Tool calling
- Guardrails
- Product thinking
- Deployment

## Core principle

The LLM should not invent numbers.

Correct workflow:

```text
User question
  ↓
Agent decides what to compute
  ↓
Python/Pandas computes real result
  ↓
LLM explains the result
```

## MVP Features

- CSV upload
- Data profiling
- Missing values report
- Duplicate row detection
- Column type inference
- Recommended analysis
- Simple chat with dataset
- Markdown report export

## Advanced Features

- LLM-powered insight generator
- LangChain/LangGraph agent
- Plotly chart generator
- RAG over uploaded reports
- Multi-file comparison
- Scheduled report generation
