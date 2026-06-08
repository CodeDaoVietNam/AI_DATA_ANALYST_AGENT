# Phase U4 - Nghiệm Thu Universal Planner Intent Schema

## 1. Tóm tắt kết quả

Phase U4 đã được implement để thêm một lớp **Universal Planner Intent Schema** cho AI Copilot.

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

Điểm thay đổi lớn nhất:

- Agent không còn phải nhảy thẳng từ câu hỏi sang tool.
- Agent có một bước trung gian có cấu trúc: `task`, `metric`, `dimension`, `time_grain`, `limit`, `comparison`.
- Các câu như `margin theo category`, `doanh thu theo tháng`, `doanh thu theo category` có thể route deterministic mà không cần Ollama.

## 2. Files đã thêm/sửa

### 2.1 Service mới

Đã thêm:

```text
app/services/intent_planner.py
```

Service này gồm:

- `IntentFilter`
- `IntentComparison`
- `UniversalAnalysisIntent`
- `parse_universal_intent`
- `compile_intent_to_plan`

### 2.2 Agent integration

Đã cập nhật:

```text
app/services/agent_orchestrator.py
```

`AgentOrchestrator._build_plan` hiện chạy theo thứ tự:

```text
1. parse_universal_intent
2. compile_intent_to_plan
3. fallback old rule-based plan
4. fallback LLM router
5. fallback overview
```

Nếu intent compile được thành plan, agent bỏ qua LLM router và chạy tool deterministic ngay.

## 3. Intent schema hiện tại

Intent có shape:

```json
{
  "task": "breakdown",
  "metric": "margin",
  "metric_source": "custom_metric",
  "dimension": "category",
  "time_grain": null,
  "filters": [],
  "comparison": null,
  "chart_type": null,
  "limit": null,
  "confidence": 0.95,
  "reasons": [
    "Detected custom metric `margin`.",
    "Detected dimension `category`.",
    "Detected task `breakdown`."
  ]
}
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

## 4. Plan compiler v1

Compiler hiện map intent sang tool:

| Intent | Tool |
|---|---|
| custom metric + no dimension | `evaluate_custom_metric` |
| custom metric + dimension | `custom_metric_breakdown` |
| semantic metric by dimension | `semantic_breakdown` |
| semantic metric trend | `semantic_time_series` |
| target/conversion summary | `semantic_target_summary` |
| missing/duplicate | `get_missing_values` / `get_duplicate_rows` |
| correlation | `correlation_analysis` |
| chart | `generate_chart_spec` |
| outlier | `detect_outliers` |
| anomaly | `anomaly_detection` |
| forecast | `forecast_next_period` |
| pareto | `pareto_analysis` |
| overview | `get_dataset_overview` / `get_sales_overview` |

## 5. Response thay đổi

`agent_plan` hiện có thêm `intent` khi planner parse được.

Ví dụ:

```json
{
  "strategy": "intent:breakdown",
  "intent": {
    "task": "breakdown",
    "metric": "margin",
    "metric_source": "custom_metric",
    "dimension": "category"
  },
  "steps": [
    {
      "tool_name": "custom_metric_breakdown",
      "arguments": {
        "metric_name": "margin",
        "by_role": "category"
      }
    }
  ]
}
```

Timeline cũng có thêm step:

```text
parsed_intent
```

Điều này giúp debug Copilot dễ hơn: biết user hỏi gì, planner hiểu ra sao, rồi mới biết tool nào được gọi.

## 6. Ví dụ routing sau U4

### 6.1 Custom metric breakdown

Question:

```text
margin theo category như thế nào?
```

Intent:

```json
{
  "task": "breakdown",
  "metric": "margin",
  "metric_source": "custom_metric",
  "dimension": "category"
}
```

Tool:

```text
custom_metric_breakdown
```

### 6.2 Semantic breakdown

Question:

```text
doanh thu theo category
```

Intent:

```json
{
  "task": "breakdown",
  "metric": "revenue",
  "metric_source": "semantic_role",
  "dimension": "category"
}
```

Tool:

```text
semantic_breakdown
```

### 6.3 Trend

Question:

```text
doanh thu theo tháng
```

Intent:

```json
{
  "task": "trend",
  "metric": "revenue",
  "time_grain": "month"
}
```

Tool:

```text
semantic_time_series
```

### 6.4 Data quality

Question:

```text
cột nào thiếu dữ liệu?
```

Intent:

```json
{
  "task": "data_quality"
}
```

Tool:

```text
get_missing_values
```

## 7. Tests đã thêm

### 7.1 Intent planner tests

File:

```text
tests/test_intent_planner.py
```

Coverage:

- parse custom metric breakdown intent.
- compile custom metric breakdown plan.
- parse semantic revenue/category breakdown.
- parse trend intent.
- parse data quality intent.
- parse correlation intent.
- carry `top 5` limit into plan.

### 7.2 Agent intent tests

File:

```text
tests/test_agent_intent_planner.py
```

Coverage:

- Agent route custom metric breakdown without LLM.
- Agent route semantic revenue/category breakdown without LLM.
- Agent route semantic monthly trend without LLM.
- `agent_plan.intent` xuất hiện trong response.
- timeline có `parsed_intent`.

## 8. Verification

### 8.1 Targeted tests

Lệnh:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest tests/test_intent_planner.py tests/test_agent_intent_planner.py -q
```

Kết quả:

```text
9 passed, 1 warning
```

### 8.2 Full backend tests

Lệnh:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest -q
```

Kết quả:

```text
114 passed, 1 warning
```

Warning còn lại là dependency warning từ môi trường `requests/urllib3/chardet`, không phải lỗi U4.

### 8.3 Frontend build

Lệnh:

```bash
cd web
npm run build
```

Kết quả:

```text
✓ built
```

Vite vẫn cảnh báo bundle lớn do Plotly, không phải lỗi build.

## 9. Cách test thủ công

### 9.1 Với dataset retail/Superstore

Tạo metric:

```text
margin = profit / revenue
```

Ask AI:

```text
margin theo category như thế nào?
```

Kỳ vọng:

- `agent_plan.strategy = intent:breakdown`
- `agent_plan.intent.metric = margin`
- tool `custom_metric_breakdown`

### 9.2 Semantic breakdown

Ask AI:

```text
doanh thu theo category
```

Kỳ vọng:

- tool `semantic_breakdown`
- intent metric `revenue`
- dimension `category`

### 9.3 Trend

Ask AI:

```text
doanh thu theo tháng
```

Kỳ vọng:

- tool `semantic_time_series`
- intent task `trend`
- time grain `month`

## 10. Cảm nhận sự thay đổi

U4 làm Copilot bớt giống một router keyword chắp vá và bắt đầu giống một planner thật hơn.

Trước đây:

```text
"margin theo category" -> tìm keyword -> chọn tool
```

Bây giờ:

```text
"margin theo category"
  -> task = breakdown
  -> metric = margin
  -> metric_source = custom_metric
  -> dimension = category
  -> compile plan
  -> run custom_metric_breakdown
```

Đây là nền rất quan trọng cho các câu hỏi phức tạp hơn:

- "So sánh margin giữa Consumer và Corporate."
- "Doanh thu tháng này giảm do category nào?"
- "Top state có revenue cao nhưng margin thấp là gì?"
- "Forecast revenue 3 tháng tới."

Các câu trên về sau chỉ cần mở rộng intent parser/compiler, không phải viết thêm rule rải rác trong agent.

## 11. Giới hạn còn lại

U4 v1 vẫn còn giới hạn:

- Filter parsing còn rất đơn giản.
- Chưa parse date range tự nhiên như "quý trước", "30 ngày gần nhất".
- Chưa có LLM intent parser fallback riêng.
- Chưa có UI hiển thị intent đẹp trong Ask AI.
- Chưa có evaluation suite 20-50 CSV để đo planner accuracy.
- `ecommerce_risk` vẫn fallback nhiều sang rule cũ khi compiler chưa map đủ.

## 12. Bước tiếp theo đề xuất

Sau U4, nên làm:

1. **Ask AI Intent Debug UI**
   - Hiển thị task/metric/dimension/time_grain trong chat bubble.

2. **Evaluation Suite**
   - Tạo 20-50 CSV + bộ câu hỏi expected intent/tool.

3. **Filter/Date Range Parser**
   - Parse `state = California`, `year = 2024`, `last 30 days`.

4. **LLM Intent Parser Fallback**
   - Khi deterministic confidence thấp, hỏi model trả về `UniversalAnalysisIntent`, rồi backend validate.

## 13. Definition of Done

U4 hoàn thành khi:

- Có `intent_planner.py`.
- Agent dùng intent trước rule/LLM.
- `agent_plan.intent` có trong response.
- Timeline có `parsed_intent`.
- Custom metric/semantic trend/breakdown route được bằng intent.
- Tests pass.
- Có acceptance doc.

Tình trạng hiện tại:

```text
Done.
```
