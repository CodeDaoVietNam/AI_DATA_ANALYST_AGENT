# Plan - Copilot Answer Quality Guardrails cho weak/empty tool result

## 1. Bối cảnh

Hiện AI Copilot đôi khi trả lời kiểu:

```text
Kết luận chính
Kết quả nổi bật là chỉ số = Không có dữ liệu.
Công cụ `python code interpreter` đã chạy xong và thu được kết quả mà không có dữ liệu nổi bật.
```

Đây là output không tốt vì nó tạo cảm giác hệ thống đã phân tích được điều gì đó, trong khi thực tế tool result không có metric, bảng, top item hoặc evidence đủ rõ.

Vấn đề này thường xảy ra với:

- `python_code_interpreter`
- tool trả `None`
- tool trả stdout text trống hoặc text khó parse
- tool trả dict không có numeric metric rõ
- LLM trả answer card nhưng backend giữ evidence rỗng/yếu
- result summary có `primary_metric=None`, `primary_metric_value=None`

## 2. Vì sao nghiêm trọng

Người dùng không chỉ cần “có câu trả lời”; họ cần biết:

- Tool đã chạy được hay chưa.
- Có đủ dữ liệu để kết luận không.
- Nếu chưa đủ, thiếu gì.
- Nên hỏi lại như thế nào.
- Có nên tin kết quả hay không.

Câu “chỉ số = Không có dữ liệu” làm giảm trust vì:

- Không có insight.
- Không có actionable next step.
- Không nói rõ lỗi nằm ở dữ liệu, tool hay câu hỏi.
- Có vẻ như hệ thống đang cố tạo kết luận từ output rỗng.

## 3. Mục tiêu sprint

Sprint này không nhằm làm Copilot “thông minh toàn diện”, mà nhằm làm nó **trung thực và hữu ích hơn khi kết quả yếu**.

Mục tiêu:

1. Không còn câu “Kết quả nổi bật là chỉ số = Không có dữ liệu.”
2. Tool result yếu phải được phân loại rõ.
3. Python code interpreter phải trả output có schema dễ render hơn.
4. Answer Composer phải có nhánh `insufficient_result`.
5. Frontend phải render empty/weak result như một trạng thái có ích, không như insight thật.
6. LLM không được polish weak result thành kết luận chắc chắn.

## 4. Nguyên tắc sản phẩm

### 4.1 Không kết luận nếu không có evidence

Nếu không có metric/top item/rows rõ:

Không nên nói:

```text
Kết quả nổi bật là ...
```

Nên nói:

```text
Mình đã chạy công cụ phân tích, nhưng kết quả trả về chưa có chỉ số hoặc bảng đủ rõ để rút ra kết luận chắc chắn.
```

### 4.2 Weak result vẫn phải hữu ích

Weak result không phải là lỗi chết. Nó nên trả:

- Tool đã chạy.
- Output có gì.
- Vì sao chưa kết luận được.
- Cần bổ sung metric/dimension nào.
- Gợi ý câu hỏi tiếp theo.

### 4.3 Python code interpreter là fallback, không phải default

Nếu câu hỏi có thể trả bằng semantic/generic/domain tools thì không nên route sang `python_code_interpreter`.

Chỉ dùng code interpreter khi:

- Không tool deterministic nào đáp ứng.
- Câu hỏi yêu cầu calculation tùy biến thật sự.
- Planner có đủ column/role để generate code an toàn.

### 4.4 LLM không được bịa insight từ output yếu

Nếu result quality là `insufficient`, prompt LLM phải yêu cầu:

- Không tạo kết luận business chắc chắn.
- Không thêm số liệu mới.
- Nói rõ thiếu evidence.
- Gợi ý cách hỏi lại.

## 5. Thiết kế result quality layer

Thêm service mới:

```text
app/services/result_quality.py
```

### 5.1 Schema đề xuất

```python
from dataclasses import dataclass
from typing import Any, Literal

ResultQualityStatus = Literal[
    "strong",
    "partial",
    "empty",
    "insufficient",
    "tool_error",
]

@dataclass(frozen=True)
class ResultQuality:
    status: ResultQualityStatus
    reason: str
    has_rows: bool
    row_count: int | None
    has_metric: bool
    metric_name: str | None
    metric_value: Any | None
    has_label: bool
    label: str | None
    render_mode: str
    warnings: list[str]
```

### 5.2 Rules đề xuất

`strong` khi:

- Có rows list không rỗng.
- Có top item.
- Có label rõ.
- Có numeric metric rõ.

`partial` khi:

- Có rows nhưng thiếu metric hoặc thiếu label.
- Có dict với một vài field hữu ích nhưng không đủ để gọi là top insight.

`empty` khi:

- Result là `None`.
- Result là list rỗng.
- Result là dict rỗng.
- stdout rỗng.

`insufficient` khi:

- Tool success nhưng result không có metric/table usable.
- Result chỉ là text chung chung.
- `primary_metric=None`.
- `primary_metric_value=None`.

`tool_error` khi:

- Tool result có `success=False`.
- Có `error`.
- Exception path.

### 5.3 Function đề xuất

```python
def assess_result_quality(
    *,
    tool_name: str,
    result: Any,
    result_summary: dict[str, Any] | None,
) -> ResultQuality:
    ...
```

## 6. Chuẩn hóa Python code interpreter output

File:

```text
app/services/code_interpreter.py
```

Hiện output:

```json
{
  "success": true,
  "error": null,
  "stdout": "...",
  "result": ...
}
```

Vấn đề:

- `result` có thể là stdout string.
- stdout có thể rỗng.
- DataFrame/Series convert chưa có metadata.
- Không có `result_type`.
- Không có `row_count`.
- Không có `columns`.
- Không có `metrics`.
- Answer Composer khó biết render kiểu gì.

### 6.1 Output schema v2 đề xuất

```json
{
  "success": true,
  "error": null,
  "stdout": "...",
  "result": [...],
  "result_type": "dataframe | series | scalar | dict | text | empty",
  "row_count": 10,
  "columns": ["category", "revenue"],
  "metrics": {
    "revenue": 45231.0
  },
  "warnings": []
}
```

### 6.2 Rules convert

Nếu result là DataFrame:

- Convert top `MAX_RESULT_ROWS` rows.
- `result_type="dataframe"`.
- `row_count=len(converted_rows)`.
- `columns=list(df.columns)`.

Nếu result là Series:

- Nếu index/value dạng groupby summary, convert thành rows:

```json
[
  {"label": "Set", "value": 45231}
]
```

- `result_type="series"`.

Nếu result là scalar:

- `result_type="scalar"`.
- `metrics={"value": scalar}`.

Nếu result là dict:

- `result_type="dict"`.
- Nếu dict có numeric values, đưa vào `metrics`.

Nếu chỉ có stdout:

- `result_type="text"`.
- Nếu stdout rỗng, `result_type="empty"`.

Nếu code chạy success nhưng không set `result` và không print:

```json
{
  "success": true,
  "result_type": "empty",
  "warnings": ["Code ran successfully but did not assign `result` or print output."]
}
```

## 7. Nâng cấp Answer Composer

File:

```text
app/services/answer_composer.py
```

### 7.1 Thêm input result_quality

```python
def compose_answer_card(
    *,
    question: str,
    tool_name: str,
    arguments: dict[str, Any] | None,
    result: Any,
    result_summary: dict[str, Any] | None,
    semantic_profile: Any | None = None,
    warnings: list[str] | None = None,
    result_quality: ResultQuality | None = None,
    answer_source: str = "deterministic_composer",
) -> dict[str, Any]:
    ...
```

### 7.2 Thêm nhánh insufficient

Nếu:

```python
result_quality.status in {"empty", "insufficient", "partial"}
```

và không có metric/label tốt, tạo card:

```json
{
  "headline": "Mình đã chạy phân tích, nhưng chưa đủ dữ liệu rõ để kết luận.",
  "summary": "Công cụ đã hoàn tất, nhưng kết quả không có bảng, metric hoặc nhóm nổi bật đủ rõ.",
  "key_takeaways": [
    {
      "label": "Chưa đủ evidence",
      "text": "Không có metric/top item rõ nên hệ thống không nên suy diễn insight.",
      "tone": "warning"
    },
    {
      "label": "Cách hỏi lại",
      "text": "Hãy nêu rõ metric và dimension, ví dụ: doanh thu theo category hoặc missing values theo cột.",
      "tone": "neutral"
    }
  ],
  "evidence": [
    {
      "label": "Công cụ đã chạy",
      "value": "python code interpreter"
    },
    {
      "label": "Trạng thái kết quả",
      "value": "Chưa đủ rõ để kết luận"
    }
  ],
  "why_it_matters": "Nếu không có evidence rõ, hệ thống cần nói thật thay vì tạo kết luận giả.",
  "recommended_next_questions": [
    "Metric chính bạn muốn phân tích là gì?",
    "Bạn muốn breakdown theo cột nào?",
    "Hãy tổng quan dataset này trước."
  ],
  "confidence": "low",
  "data_warnings": [
    "Tool result không có metric hoặc bảng đủ rõ."
  ]
}
```

### 7.3 Chặn câu xấu

Không bao giờ render:

```text
chỉ số = Không có dữ liệu
metric = N/A
metric = None
value = Không có dữ liệu
```

Nếu metric value missing:

- Không gọi metric đó là nổi bật.
- Chuyển sang insufficient/partial wording.

### 7.4 Humanize python_code_interpreter

Trong `_humanize_tool_name`:

```python
"python_code_interpreter": "Python analysis sandbox"
```

Tiếng Việt UI có thể render:

```text
Python analysis sandbox
```

hoặc:

```text
công cụ Python sandbox
```

## 8. Nâng cấp Agent Orchestrator

File:

```text
app/services/agent_orchestrator.py
```

### 8.1 Tích hợp result quality

Sau khi chạy tool:

```python
result_summary = _result_summary(...)
result_quality = assess_result_quality(
    tool_name=primary_tool,
    result=primary_result,
    result_summary=result_summary,
)
```

Response thêm:

```json
{
  "result_quality": {
    "status": "insufficient",
    "reason": "...",
    "render_mode": "insufficient_result"
  }
}
```

### 8.2 LLM explanation guardrail

Nếu `result_quality.status` là `empty` hoặc `insufficient`:

- Không gọi LLM để polish như insight thật.
- Hoặc nếu vẫn gọi LLM, prompt phải nói:

```text
Tool result is insufficient. Do not present a business conclusion.
Explain what is missing and ask for clarification.
```

Khuyến nghị phase đầu:

- Với insufficient result, bỏ qua LLM.
- Dùng deterministic insufficient card.

### 8.3 Giảm route sang python_code_interpreter

Trong planner prompt/rule:

Hiện có rule:

```text
If no specialized tool fits, use python_code_interpreter
```

Nên đổi thành:

```text
If no specialized tool fits, prefer semantic_overview, get_dataset_overview,
get_missing_values, groupby_aggregate, semantic_breakdown, semantic_time_series.
Use python_code_interpreter only when the user explicitly requests a custom
calculation that available tools cannot express.
```

### 8.4 Warning rõ hơn

Nếu tool là python interpreter và result insufficient:

```text
Python analysis đã chạy nhưng không tạo ra output có cấu trúc. Hãy set biến `result` thành DataFrame/list/dict hoặc hỏi theo metric cụ thể hơn.
```

## 9. Nâng cấp frontend renderer

File:

```text
web/src/components/AskCopilot.tsx
web/src/types.ts
```

### 9.1 Type mới

```ts
export type ResultQuality = {
  status: "strong" | "partial" | "empty" | "insufficient" | "tool_error";
  reason: string;
  render_mode: string;
  warnings: string[];
};
```

`AgentResponse` thêm:

```ts
result_quality?: ResultQuality | null;
```

### 9.2 Renderer mới

Nếu:

```ts
response.result_quality?.status === "insufficient"
```

render card riêng:

- Title: “Chưa đủ dữ liệu để kết luận”
- Body: lý do
- Evidence:
  - tool đã chạy
  - row_count
  - metric missing
- Suggested actions:
  - “Hỏi tổng quan dataset”
  - “Chọn metric cụ thể”
  - “Mở semantic mapping”
  - “Xem chi tiết kỹ thuật”

### 9.3 Không show fake KPI

Nếu result quality weak:

- Không render KPI card với “Không có dữ liệu”.
- Không render mini chart rỗng.
- Không render “Kết quả nổi bật”.

## 10. Tests cần thêm

### 10.1 Backend tests

File:

```text
tests/test_result_quality.py
tests/test_answer_composer.py
tests/test_agent_orchestrator.py
tests/test_code_interpreter.py
```

Cases:

1. Empty result:

```python
assess_result_quality(result=None) -> status="empty"
```

2. Dict no metric:

```python
{"message": "done"} -> status="insufficient" hoặc "partial"
```

3. List rows with metric:

```python
[{"category": "Set", "revenue": 100}] -> status="strong"
```

4. Code interpreter no result:

```python
execute_pandas_code(df, "x = 1")
```

Expected:

- success true
- result_type empty
- warning nói chưa set result/print

5. Code interpreter DataFrame result:

```python
result = df.groupby("category")["revenue"].sum().reset_index()
```

Expected:

- result_type dataframe
- rows present
- columns present

6. Answer composer insufficient:

Expected:

- headline chứa “chưa đủ dữ liệu”
- không chứa “chỉ số = Không có dữ liệu”
- confidence low

7. Agent with python insufficient:

Expected:

- result_quality.status insufficient/empty
- explanation_source deterministic_fallback
- answer_card warning rõ

### 10.2 Frontend checks

Nếu chưa có frontend test framework:

- `cd web && npm run build`
- Manual check:
  - response.result_quality insufficient render đúng card.
  - Không render fake KPI.
  - Không hiện “Không có dữ liệu” như metric nổi bật.

## 11. Manual acceptance checklist

### Case 1 - Code interpreter không có result

Question:

```text
Chạy thử một phân tích Python đơn giản.
```

Nếu tool chạy nhưng không có output:

Expected:

- Không có “chỉ số = Không có dữ liệu”.
- Có card “Chưa đủ dữ liệu để kết luận”.
- Có hướng dẫn: cần metric/dimension hoặc set `result`.

### Case 2 - Generic tool có result mạnh

Question:

```text
Cột nào missing nhiều nhất?
```

Expected:

- Vẫn có answer card mạnh.
- Có evidence.
- Có metric.

### Case 3 - Ecommerce result mạnh

Question:

```text
Category nào doanh thu cao nhất?
```

Expected:

- Card bình thường, không bị classify insufficient.

### Case 4 - LLM unavailable

Expected:

- Deterministic insufficient card vẫn rõ ràng.
- Không im lặng.

## 12. Definition of Done

Hoàn thành khi:

- Có `result_quality.py`.
- Code interpreter output có `result_type`, `row_count`, `columns`, `metrics`, `warnings`.
- Agent response có `result_quality`.
- Answer Composer có nhánh insufficient/empty.
- Không còn output “chỉ số = Không có dữ liệu”.
- UI có state “Chưa đủ dữ liệu để kết luận”.
- Tests pass.
- Frontend build pass.

## 13. Thứ tự implement đề xuất

1. Tạo `app/services/result_quality.py`.
2. Thêm tests cho `assess_result_quality`.
3. Chuẩn hóa `code_interpreter.py` output.
4. Update `_result_summary` trong `agent_orchestrator.py` để hiểu interpreter schema.
5. Truyền `result_quality` vào `compose_answer_card`.
6. Thêm insufficient branch trong `answer_composer.py`.
7. Thêm `result_quality` vào schema/types.
8. Update frontend renderer.
9. Chạy tests/build.
10. Manual test bằng câu hỏi gây weak result.

## 14. Prompt mẫu cho AI coding agent implement

```text
Please implement the Copilot Answer Quality Guardrails from docs/30_copilot_weak_result_answer_quality_plan_vi.md.

Focus on:
- result_quality service
- code_interpreter structured output
- answer_composer insufficient/empty result branch
- agent_orchestrator result_quality response
- frontend insufficient result renderer
- tests and build verification

Do not add LangGraph.
Do not rewrite the whole frontend.
Do not let answer cards say "metric = N/A" or "chỉ số = Không có dữ liệu".
Run:
- PYTHONPATH=. pytest -q
- cd web && npm run build
```

## 15. Ghi chú dài hạn

Về lâu dài, `python_code_interpreter` nên có một contract bắt buộc:

```python
result = {
    "summary": "...",
    "metrics": {...},
    "rows": [...],
    "warnings": [...]
}
```

Nếu LLM generate code, prompt nên bắt buộc set `result` theo schema này. Khi output đã chuẩn, Answer Composer sẽ dễ tạo câu trả lời đẹp và đáng tin hơn nhiều.
