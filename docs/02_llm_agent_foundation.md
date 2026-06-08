# 02 - LLM and Agent Foundation

## Concepts to learn first

### 1. LLM

An LLM is good at language understanding and generation.

It is not reliable as a calculator or database engine.

Use it for:

- Planning
- Explaining
- Summarizing
- Choosing tools
- Communicating insights

Do not use it for:

- Raw calculation without tools
- Guessing values from CSV
- Executing unsafe code

### 2. Prompt

A prompt is the instruction sent to the model.

A good prompt contains:

- Role
- Task
- Context
- Rules
- Output format
- Examples

### 3. System Prompt

Example:

```text
You are an AI Data Analyst Agent.
Never invent numbers.
For any numerical answer, call a tool.
Only explain results after tool output is available.
```

### 4. Structured Output

Instead of free text, require JSON output:

```json
{
  "summary": "...",
  "insights": ["..."],
  "warnings": ["..."]
}
```

### 5. Tool Calling

A tool is a Python function the model can call.

Examples:

- get_missing_values
- groupby_sum
- generate_chart
- detect_outliers

### 6. Agent

An agent is:

```text
LLM + Tools + Memory + Planning Loop + Guardrails
```

### 7. Guardrails

Guardrails protect the system from unsafe or low-quality behavior.

For this project:

- Do not run arbitrary user code
- Validate column names
- Limit upload size
- Do not expose API keys
- Do not let LLM invent numbers
