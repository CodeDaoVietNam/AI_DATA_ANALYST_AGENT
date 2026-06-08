# 05 - Upgrade Path

## Upgrade 1: Better Natural Language Understanding

Current version uses rule-based question matching.

Upgrade:

- Use LLM to classify intent.
- Validate output using Pydantic.
- Route to the correct tool.

## Upgrade 2: Real Tool Calling

Use LangChain or OpenAI tool calling.

Example tools:

```text
get_dataset_overview
get_missing_values
groupby_aggregate
generate_chart
detect_outliers
```

## Upgrade 3: LangGraph

Use LangGraph when you need a more controlled multi-step workflow.

Example graph:

```text
START
  ↓
Classify Intent
  ↓
Select Tool
  ↓
Run Tool
  ↓
Validate Result
  ↓
Generate Final Answer
  ↓
END
```

## Upgrade 4: Safer Pandas Agent

Do not allow arbitrary Python execution.

Prefer predefined tools over Python REPL.

Unsafe:

```text
Agent writes and executes arbitrary Python code.
```

Safer:

```text
Agent selects from approved tools with validated arguments.
```

## Upgrade 5: Report Generation

Generate:

- Markdown report
- PDF report
- HTML dashboard

## Upgrade 6: Portfolio Polish

Add:

- Architecture diagram
- Demo video
- Screenshots
- API docs
- Test cases
- Docker instructions
