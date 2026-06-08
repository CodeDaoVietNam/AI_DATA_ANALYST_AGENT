# Phase U2/U3 - Custom Metric Builder + Generic Insight Engine v2 Implementation Plan

## 1. Mục tiêu tổng thể

Phase U2/U3 nâng project từ chỗ "hiểu cột" sang chỗ "hiểu metric nghiệp vụ" và tự sinh insight generic tốt hơn cho nhiều loại CSV.

Hai câu hỏi trung tâm:

1. Nếu user nói `margin`, `conversion_rate`, `avg_order_value`, hệ thống có biết metric này được tính như thế nào không?
2. Nếu dataset không thuộc ecommerce/retail/marketing/HR rõ ràng, dashboard generic có tự tìm được insight hữu ích không?

Kết quả mong muốn:

- User định nghĩa custom metric bằng expression an toàn.
- Metric được lưu theo dataset.
- Metric dùng được trong dashboard.
- Agent dùng được metric trong breakdown.
- Generic insight engine sinh insight có evidence, why it matters, recommended next question.

## 2. Phase U2 - Custom Metric Builder

### 2.1 Scope

U2 tập trung backend-first:

- Metric schema.
- Safe expression engine.
- Metric CRUD API.
- Metric evaluate API.
- Dashboard integration.
- Agent/tool integration.
- Backend tests.

Frontend editor đầy đủ có thể làm ở sprint UI riêng, nhưng API đã đủ để user tạo/sửa/xóa metric.

### 2.2 Metric definition schema

Schema chuẩn:

```json
{
  "name": "margin",
  "label": "Margin",
  "description": "Profit divided by revenue",
  "expression": "profit / revenue",
  "format": "percent",
  "aggregation": "mean",
  "required_roles": ["profit", "revenue"],
  "higher_is_better": true
}
```

Field:

| Field | Ý nghĩa |
|---|---|
| `name` | ID metric, snake_case, unique trong dataset |
| `label` | Tên hiển thị |
| `description` | Mô tả nghiệp vụ |
| `expression` | Công thức dùng role/column |
| `format` | `number`, `percent`, `currency`, `integer` |
| `aggregation` | `sum`, `mean`, `median`, `min`, `max`, `count` |
| `required_roles` | Role bắt buộc như `profit`, `revenue` |
| `higher_is_better` | Metric cao hơn có tốt hơn không |

### 2.3 Expression safety

Không dùng `eval` trực tiếp.

Tạo:

```text
app/services/expression_engine.py
```

AST allowlist:

- `Expression`
- `BinOp`
- `UnaryOp`
- `Name`
- `Constant`
- `Call`
- `Load`

Operators:

- `+`
- `-`
- `*`
- `/`
- parentheses do Python AST xử lý tự nhiên

Safe functions:

- `sum(x)`
- `mean(x)`
- `count(x)`
- `safe_div(a, b)`

Reject:

- `import`
- attribute access
- subscript
- lambda
- comprehensions
- arbitrary function call
- file/network/system calls
- dunder names

### 2.4 Role/column resolution

Expression token có thể là:

- Semantic role: `profit`, `revenue`, `quantity`.
- Column name hợp lệ dạng identifier: `Profit`, `Sales`, `Visits`.
- Sanitized column alias: `order_amount` nếu cột gốc là `Order Amount`.

Resolution order:

```text
semantic role -> exact column -> sanitized column alias
```

Ví dụ:

```text
profit / revenue
  -> role profit maps to Profit
  -> role revenue maps to Sales

Profit / Sales
  -> exact column names
```

### 2.5 Backend services

Tạo:

```text
app/services/expression_engine.py
app/services/metric_builder.py
```

Functions:

```python
validate_expression(expression, variables)
evaluate_expression(expression, variables)

normalize_metric_definition(definition)
validate_metric_definition(definition, df, profile)
evaluate_metric(df, profile, definition)
evaluate_metric_summary(df, profile, definition)
metric_breakdown(df, profile, definition, by_role=None, by_column=None)
```

### 2.6 Storage

Thêm vào `DatasetMetadata`:

```text
custom_metrics_json
```

`DatasetStore` thêm:

```python
get_custom_metrics(dataset_id)
set_custom_metric(dataset_id, metric)
delete_custom_metric(dataset_id, metric_name)
```

Khi metric thay đổi:

- tăng `semantic_version`
- invalidate runtime cache
- clear semantic cache

### 2.7 API

Thêm endpoints:

```text
GET    /datasets/{dataset_id}/metrics
POST   /datasets/{dataset_id}/metrics
PUT    /datasets/{dataset_id}/metrics/{metric_name}
DELETE /datasets/{dataset_id}/metrics/{metric_name}
POST   /datasets/{dataset_id}/metrics/{metric_name}/evaluate
```

Behavior:

- Reject metric name không hợp lệ.
- Reject expression unsafe.
- Reject required role không có trong semantic profile.
- Evaluate trả JSON-safe result.

### 2.8 Dashboard integration

`dashboard_builder.py` sẽ:

- đọc custom metrics theo `dataset_id`
- evaluate từng metric
- thêm KPI card
- thêm table `Custom Metrics`
- nếu có `category/segment/state`, tạo breakdown cho metric đầu tiên phù hợp
- append insight từ metric nếu metric có kết quả tốt

Ví dụ user tạo `margin`, dashboard retail/finance sẽ có KPI `Margin`.

### 2.9 Agent integration

Agent thêm tool:

```text
evaluate_custom_metric
custom_metric_breakdown
```

Routing rule:

- Nếu câu hỏi chứa tên metric custom và không có dimension -> `evaluate_custom_metric`.
- Nếu câu hỏi chứa tên metric custom + `category/segment/state/department/country` -> `custom_metric_breakdown`.

Ví dụ:

```text
margin theo category như thế nào?
  -> custom_metric_breakdown(metric_name="margin", by_role="category")
```

## 3. Phase U3 - Generic Insight Engine v2

### 3.1 Scope

Tạo:

```text
app/services/generic_insight_engine.py
```

Insight engine v2 không phụ thuộc domain-specific tools. Nó dùng:

- dataframe
- semantic profile
- custom metrics
- simple statistical detectors

### 3.2 Unified insight schema

Insight format:

```json
{
  "id": "insight_001",
  "type": "top_contributor",
  "title": "Top revenue category",
  "finding": "Technology contributes the most revenue.",
  "evidence": "Technology revenue = 123,456, share = 42%",
  "why_it_matters": "This group drives most business value.",
  "recommended_next_question": "Profit margin của Technology có tốt không?",
  "severity": "info",
  "tone": "positive",
  "confidence": 0.82,
  "metric": "revenue",
  "dimension": "category",
  "related_chart_id": "chart_revenue_by_category",
  "related_table_id": "table_revenue_by_category"
}
```

### 3.3 Detectors v2

Implement các detector đầu tiên:

- Data quality:
  - missing columns
  - duplicate rows
  - high null percentage
  - constant columns
- Top contributor:
  - top group by metric
  - share of total
- Trend:
  - first vs last period growth/decline
- Outlier:
  - IQR-based outlier count
- Segment difference:
  - top group vs bottom group gap
- Correlation:
  - strongest positive/negative numeric correlation
  - warning correlation is not causation
- Pareto:
  - contributor concentration
- Target/conversion:
  - positive rate by group

### 3.4 Dashboard integration

`dashboard_builder.py` dùng generic insight engine cho:

- generic dashboard
- finance dashboard
- domain dashboards khi số insight còn ít

Dashboard vẫn giữ các domain insight cũ, nhưng bổ sung v2 insights có schema đầy đủ hơn.

### 3.5 Tests

Backend tests cần có:

- `profit / revenue` tính đúng.
- Chia cho 0 trả NaN/None có kiểm soát.
- Expression dùng role name hoạt động.
- Expression dùng column name hoạt động.
- Unsafe expression bị reject.
- Metric xuất hiện trong dashboard.
- Agent dùng custom metric breakdown.
- Missing value insight xuất hiện khi null cao.
- Top contributor insight đúng.
- Trend insight đúng khi có date + metric.
- Outlier insight đúng.
- Correlation insight đúng.
- Không crash dataset toàn text.
- Không crash dataset nhỏ.

## 4. Definition of Done

Phase U2/U3 hoàn thành khi:

- Có `expression_engine.py`.
- Có `metric_builder.py`.
- Có `generic_insight_engine.py`.
- Có metric CRUD/evaluate APIs.
- Metric lưu theo dataset.
- Metric được dashboard render.
- Agent gọi được custom metric tools.
- Generic dashboard có insight v2.
- Test backend pass.
- Có file nghiệm thu phase.

## 5. Giới hạn chủ ý

Chưa làm trong sprint này:

- Full frontend metric editor đẹp.
- Metric version history.
- Metric sharing giữa dataset/workspace.
- SQL-backed metric governance.
- Complex expression như rolling window, if/else, joins.
- LangGraph orchestration.

Các phần này nên để sau khi metric engine nền đã ổn.
