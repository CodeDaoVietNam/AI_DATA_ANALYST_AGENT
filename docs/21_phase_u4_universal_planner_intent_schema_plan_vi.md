# Phase U4 - Universal Planner Intent Schema Implementation Plan

## 1. Mục tiêu

Phase U4 thêm một lớp **Universal Planner Intent Schema** để AI Copilot hiểu câu hỏi theo cấu trúc trước khi chọn tool.

Trước U4:

```text
question -> keyword rules / LLM router -> tool
```

Sau U4:

```text
question
  -> UniversalAnalysisIntent
  -> deterministic plan compiler
  -> tool execution
  -> fallback rule/LLM nếu intent chưa đủ chắc
```

Ví dụ:

```json
{
  "task": "breakdown",
  "metric": "margin",
  "metric_source": "custom_metric",
  "dimension": "category",
  "time_grain": null,
  "filters": [],
  "comparison": null
}
```

## 2. Vì sao cần U4

Hiện Copilot đã có nhiều tool, semantic profile, data dictionary và custom metrics. Nhưng routing vẫn còn nhiều keyword rule riêng lẻ.

Vấn đề:

- Câu hỏi tương tự có thể route khác nhau.
- Metric/dimension/task chưa được chuẩn hóa.
- LLM router phải chọn tool trực tiếp, dễ sai hơn chọn intent.
- Khó mở rộng sang filters, comparison, anomaly, forecast, top/bottom.

U4 làm agent ổn định hơn bằng cách chuẩn hóa:

- người dùng muốn làm **task** gì
- dùng **metric** nào
- chia theo **dimension** nào
- có **time grain** không
- có **filter/comparison** không
- confidence bao nhiêu

## 3. Intent schema

Tạo service:

```text
app/services/intent_planner.py
```

Dataclasses:

```python
class IntentFilter:
    field: str
    operator: str
    value: Any

class IntentComparison:
    type: str
    baseline: str | None
    target: str | None

class UniversalAnalysisIntent:
    task: str
    metric: str | None
    metric_source: str | None
    dimension: str | None
    time_grain: str | None
    filters: list[IntentFilter]
    comparison: IntentComparison | None
    chart_type: str | None
    limit: int | None
    confidence: float
    reasons: list[str]
```

Task values v1:

- `overview`
- `data_quality`
- `correlation`
- `chart`
- `trend`
- `breakdown`
- `target_summary`
- `compare`
- `top_bottom`
- `outlier`
- `anomaly`
- `forecast`
- `pareto`
- `metric_change`
- `ecommerce_risk`
- `unknown`

Metric source:

- `custom_metric`
- `semantic_role`
- `column`
- `ecommerce`
- `none`

## 4. Parser strategy

U4 v1 dùng deterministic parser trước:

```text
normalize question
  -> detect task
  -> detect custom metric
  -> detect semantic metric role
  -> detect dimension role
  -> detect time grain
  -> detect chart intent
  -> detect limit
  -> assign confidence
```

Không phụ thuộc LLM ở parser v1. LLM router vẫn fallback khi intent confidence thấp.

## 5. Plan compiler

Function:

```python
compile_intent_to_plan(intent, df, profile, custom_metrics, ecommerce_available) -> dict | None
```

Mapping v1:

| Intent | Tool |
|---|---|
| custom metric + no dimension | `evaluate_custom_metric` |
| custom metric + dimension | `custom_metric_breakdown` |
| breakdown semantic metric by dimension | `semantic_breakdown` |
| trend semantic metric | `semantic_time_series` |
| target summary | `semantic_target_summary` |
| data quality | `get_missing_values` hoặc `get_duplicate_rows` |
| correlation | `correlation_analysis` |
| chart | `generate_chart_spec` |
| ecommerce risk | ecommerce multi-step tools |
| outlier | `detect_outliers` |
| anomaly | `anomaly_detection` |
| forecast | `forecast_next_period` |
| pareto | `pareto_analysis` |

## 6. Agent integration

`AgentOrchestrator._build_plan` đổi thứ tự:

```text
1. parse intent
2. compile intent to plan nếu confidence đủ
3. fallback old rule-based plan
4. fallback LLM router
5. fallback overview
```

Response thêm:

```json
{
  "agent_plan": {
    "intent": {},
    "strategy": "intent:breakdown"
  }
}
```

Timeline thêm:

```text
parsed_intent
```

## 7. Tests

Test parser:

- `margin theo category` -> task `breakdown`, metric `margin`, source `custom_metric`, dimension `category`.
- `doanh thu theo tháng` -> task `trend`, metric `revenue`, dimension/date grain month.
- `cột nào thiếu dữ liệu` -> task `data_quality`.
- `tương quan giữa các cột numeric` -> task `correlation`.
- `vẽ biểu đồ revenue theo category` -> task `chart`.
- `top 5 category theo revenue` -> task `top_bottom` hoặc `breakdown`, limit 5.

Test agent:

- custom metric breakdown routes without LLM.
- semantic revenue/category routes to `semantic_breakdown`.
- trend routes to `semantic_time_series`.
- data quality routes to missing/duplicate tool.
- parsed intent appears in `agent_plan`.

## 8. Definition of Done

U4 hoàn thành khi:

- Có `intent_planner.py`.
- Agent dùng intent trước rule/LLM.
- Response plan có `intent`.
- Tests pass.
- Có acceptance doc.
- Architecture cập nhật.

## 9. Giới hạn v1

- Filter parsing còn đơn giản.
- Chưa có full natural-language date range parser.
- Chưa có LLM intent parser fallback riêng.
- Chưa có UI hiển thị intent đẹp.
- Chưa có evaluation suite 20-50 CSV trong sprint này.
