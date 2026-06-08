# Phase U2/U3 - Nghiệm Thu Custom Metric Builder + Generic Insight Engine v2

## 1. Tóm tắt kết quả

Phase U2/U3 đã được implement theo hướng backend-first.

Kết quả chính:

- Có safe expression engine bằng Python AST allowlist.
- Có custom metric builder theo dataset.
- Có metric CRUD/evaluate API.
- Custom metric được lưu trong dataset metadata.
- Custom metric xuất hiện trong dashboard KPI/table/chart/insight.
- Agent có thể route câu hỏi custom metric như `margin theo category`.
- React Smart Dashboard có Metric Builder UI để tạo/sửa/xóa/evaluate metric.
- Có Generic Insight Engine v2 để sinh insight cho dataset generic/unknown.
- Full backend tests pass.
- Frontend build vẫn pass.

Điểm thay đổi lớn nhất:

```text
Trước U2/U3:
  Hệ thống hiểu cột và role.

Sau U2/U3:
  Hệ thống bắt đầu hiểu metric nghiệp vụ do user định nghĩa.
```

Ví dụ:

```text
margin = profit / revenue
conversion_rate = conversions / visits
avg_order_value = revenue / orders
```

## 2. Những gì đã implement trong U2

### 2.1 Safe Expression Engine

Đã tạo:

```text
app/services/expression_engine.py
```

Service này dùng Python AST để parse expression an toàn.

Cho phép:

- numeric constants
- role/column names
- `+`
- `-`
- `*`
- `/`
- parentheses
- safe functions:
  - `sum`
  - `mean`
  - `count`
  - `safe_div`

Chặn:

- `import`
- attribute access
- subscript
- lambda
- comprehension
- arbitrary function call
- dunder names
- file/network/system calls

Ví dụ expression hợp lệ:

```text
profit / revenue
Profit / Sales
safe_div(profit, revenue)
sum(profit) / sum(revenue)
```

Ví dụ expression bị reject:

```text
__import__("os").system("rm -rf /")
```

### 2.2 Metric Builder Service

Đã tạo:

```text
app/services/metric_builder.py
```

Functions chính:

```python
normalize_metric_definition(definition)
validate_metric_definition(definition, df, profile)
evaluate_metric(df, profile, definition)
evaluate_metric_summary(df, profile, definition)
metric_breakdown(df, profile, definition, by_role=None, by_column=None)
find_metric(metrics, metric_name)
```

Metric expression resolve biến theo thứ tự:

```text
semantic role -> exact column name -> sanitized column alias
```

Ví dụ:

```text
profit / revenue
```

Nếu semantic profile có:

```text
profit -> Profit
revenue -> Sales
```

thì expression sẽ dùng:

```text
Profit / Sales
```

### 2.3 Metric Schema

Đã thêm vào:

```text
app/schemas/models.py
```

Models:

- `MetricDefinition`
- `MetricListResponse`
- `MetricResponse`
- `MetricEvaluationResponse`

Schema:

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

### 2.4 Metric Storage

Đã cập nhật:

```text
app/database.py
app/services/storage.py
```

Thêm field metadata:

```text
custom_metrics_json
```

`DatasetStore` có thêm:

```python
get_custom_metrics(dataset_id)
set_custom_metric(dataset_id, metric)
delete_custom_metric(dataset_id, metric_name)
```

Khi metric thay đổi:

- `semantic_version` tăng.
- runtime cache bị invalidate.
- semantic cache bị clear.

### 2.5 Metric APIs

Đã thêm:

```text
GET    /datasets/{dataset_id}/metrics
POST   /datasets/{dataset_id}/metrics
PUT    /datasets/{dataset_id}/metrics/{metric_name}
DELETE /datasets/{dataset_id}/metrics/{metric_name}
POST   /datasets/{dataset_id}/metrics/{metric_name}/evaluate
```

Ví dụ tạo metric:

```bash
curl -X POST http://localhost:8000/datasets/{dataset_id}/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "margin",
    "label": "Margin",
    "expression": "profit / revenue",
    "format": "percent",
    "aggregation": "mean",
    "required_roles": ["profit", "revenue"],
    "higher_is_better": true
  }'
```

Ví dụ evaluate:

```bash
curl -X POST http://localhost:8000/datasets/{dataset_id}/metrics/margin/evaluate
```

Response trả:

```json
{
  "dataset_id": "...",
  "metric_name": "margin",
  "summary": {
    "name": "margin",
    "label": "Margin",
    "expression": "profit / revenue",
    "format": "percent",
    "aggregation": "mean",
    "value": 0.175,
    "valid_count": 2,
    "missing_count": 0,
    "result_type": "series"
  }
}
```

## 3. Dashboard Integration

Đã cập nhật:

```text
app/services/dashboard_builder.py
```

Dashboard hiện:

- đọc custom metrics theo `dataset_id`
- evaluate metric
- thêm KPI card
- thêm table `Custom Metrics`
- tạo breakdown theo role đầu tiên phù hợp như `category`, `segment`, `state`, `country`, `department`
- thêm insight cho top custom metric group

Ví dụ với metric:

```text
margin = profit / revenue
```

Dashboard retail/finance/generic có thể hiển thị:

- KPI `Margin`
- Table `Custom Metrics`
- Table `margin by Category`
- Chart `margin by Category`
- Insight top group theo margin

## 3.1 Frontend Metric Builder UI

Đã cập nhật:

```text
web/src/App.tsx
web/src/api.ts
web/src/types.ts
```

Smart Dashboard hiện có panel **Metric Builder**.

UI hỗ trợ:

- Xem danh sách custom metrics đã lưu.
- Chọn metric để edit.
- Tạo metric mới.
- Sửa:
  - `name`
  - `label`
  - `description`
  - `expression`
  - `format`
  - `aggregation`
  - `required_roles`
  - `higher_is_better`
- Save metric.
- Delete metric.
- Evaluate metric và xem preview summary.
- Insert expression helper tokens từ semantic roles và column aliases.

Frontend API client đã thêm:

```text
getMetrics
createMetric
updateMetric
deleteMetric
evaluateMetric
```

Sau khi save/delete metric:

```text
metric API
  -> backend invalidate cache
  -> frontend refetch metrics
  -> frontend refetch dashboard
  -> KPI/table/insight refresh
```

## 4. Agent Integration

Đã cập nhật:

```text
app/services/agent_orchestrator.py
```

Thêm tools:

```text
evaluate_custom_metric
custom_metric_breakdown
```

Routing rule:

```text
Nếu câu hỏi chứa custom metric name/label:
  - không có dimension -> evaluate_custom_metric
  - có category/segment/state/department/... -> custom_metric_breakdown
```

Ví dụ:

```text
margin theo category như thế nào?
```

Planner map thành:

```json
{
  "tool_name": "custom_metric_breakdown",
  "arguments": {
    "metric_name": "margin",
    "by_role": "category"
  }
}
```

Điều này làm Copilot không cần bịa công thức metric. Công thức đến từ custom metric definition đã validate.

## 5. Những gì đã implement trong U3

### 5.1 Generic Insight Engine v2

Đã tạo:

```text
app/services/generic_insight_engine.py
```

Functions chính:

```python
generate_generic_insights(df, profile, metrics=None, max_insights=10)
detect_data_quality_insights(df)
detect_top_contributor_insights(df, profile, metrics)
detect_trend_insights(df, profile, metrics)
detect_outlier_insights(df)
detect_segment_insights(df, profile, metrics)
detect_correlation_insights(df)
detect_pareto_insights(df, profile, metrics)
detect_target_insights(df, profile)
```

### 5.2 Insight schema v2

Insight mới có format thống nhất:

```json
{
  "id": "top_contributor_12345",
  "type": "top_contributor",
  "title": "Top revenue Contributor",
  "finding": "`Technology` contributes the most revenue.",
  "evidence": "revenue = 123,456, share = 42.00%.",
  "why_it_matters": "Top contributors show where business value is concentrated.",
  "recommended_next_question": "revenue của `Technology` có bền vững theo thời gian không?",
  "severity": "info",
  "tone": "positive",
  "confidence": 0.84,
  "metric": "revenue",
  "dimension": "category",
  "related_chart_id": "chart_revenue_by_category",
  "related_table_id": "table_revenue_by_category"
}
```

Vẫn giữ các field cũ như:

- `value`
- `narrative`

để frontend hiện tại không bị gãy.

### 5.3 Insight detectors đã có

Data quality:

- missing values cao
- duplicate rows
- constant columns

Distribution/outlier:

- IQR outlier count

Top/bottom contributor:

- top group by metric
- share of total

Trend:

- first period vs latest period

Segment difference:

- top group vs bottom group gap

Correlation:

- strongest numeric correlation
- có cảnh báo correlation is not causation

Pareto:

- concentration around 80% contribution

Target/conversion:

- positive target rate by group

### 5.4 Dashboard integration

`dashboard_builder.py` hiện append generic insight v2 vào dashboard:

- generic dashboard: tối đa nhiều insight hơn
- finance dashboard: bổ sung insight generic
- domain dashboards: bổ sung nếu số insight còn ít

Điều này giúp dataset chưa detect domain rõ vẫn có insight đáng đọc hơn thay vì chỉ có bảng thống kê khô.

## 6. Tests đã thêm

### 6.1 Metric builder tests

File:

```text
tests/test_metric_builder.py
```

Coverage:

- `profit / revenue` tính đúng bằng semantic role.
- Chia cho 0 trả NaN có kiểm soát.
- Expression dùng column name hoạt động.
- Unsafe expression bị reject.
- Metric breakdown by role hoạt động.

### 6.2 Generic insight engine tests

File:

```text
tests/test_generic_insight_engine.py
```

Coverage:

- Missing value insight.
- Top contributor insight.
- Trend insight.
- Outlier insight.
- Correlation insight.
- Không crash dataset toàn text.
- Không crash dataset nhỏ.

### 6.3 Metric API/dashboard/agent tests

File:

```text
tests/test_metric_api_dashboard_agent.py
```

Coverage:

- Metric CRUD/evaluate API.
- Metric xuất hiện trong dashboard.
- Agent route custom metric breakdown.

## 7. Verification

### 7.1 Targeted tests

Lệnh:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest tests/test_metric_builder.py tests/test_generic_insight_engine.py tests/test_metric_api_dashboard_agent.py -q
```

Kết quả:

```text
14 passed, 1 warning
```

### 7.2 Full backend tests

Lệnh:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest -q
```

Kết quả:

```text
105 passed, 1 warning
```

Warning còn lại là dependency warning từ môi trường `requests/urllib3/chardet`, không phải lỗi logic U2/U3.

### 7.3 Frontend build

Lệnh:

```bash
cd web
npm run build
```

Kết quả:

```text
✓ built
```

Vite vẫn cảnh báo bundle lớn do Plotly. Đây là warning hiện có, không phải lỗi build.

## 8. Cách test thủ công

### 8.1 Tạo metric margin qua UI

Vào:

```text
Smart Dashboard -> Metric Builder
```

Nhập:

```text
Name: margin
Label: Margin
Expression: profit / revenue
Format: percent
Aggregation: mean
Required roles: profit, revenue
Higher is better: checked
```

Bấm:

```text
Save Metric
```

Kỳ vọng:

- Metric xuất hiện trong Saved Metrics.
- Dashboard refresh.
- KPI `Margin` xuất hiện.
- Table `Custom Metrics` xuất hiện.
- Có thể bấm Evaluate để xem preview.

### 8.2 Tạo metric margin qua API

Upload Superstore hoặc dataset retail có `Sales`, `Profit`, `Category`.

Gọi API:

```bash
curl -X POST http://localhost:8000/datasets/{dataset_id}/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "margin",
    "label": "Margin",
    "description": "Profit divided by revenue",
    "expression": "profit / revenue",
    "format": "percent",
    "aggregation": "mean",
    "required_roles": ["profit", "revenue"],
    "higher_is_better": true
  }'
```

Sau đó mở Dashboard:

```text
GET /dashboard/{dataset_id}
```

Kỳ vọng:

- Có KPI `Margin`.
- Có table `Custom Metrics`.
- Có breakdown `margin by Category` nếu dataset có category role.
- Có insight liên quan custom metric.

### 8.3 Hỏi AI Copilot

Trong Ask AI:

```text
margin theo category như thế nào?
```

Kỳ vọng:

- Agent chọn tool `custom_metric_breakdown`.
- Kết quả không phải số LLM tự bịa.
- Dữ liệu đến từ expression đã lưu.

### 8.4 Test unsafe expression

Gọi API tạo metric:

```json
{
  "name": "bad",
  "expression": "__import__('os').system('echo nope')"
}
```

Kỳ vọng:

```text
400 Bad Request
```

## 9. Cảm nhận sự thay đổi

Phase U1 giúp hệ thống hiểu:

```text
Cột này có nghĩa là gì?
```

Phase U2 giúp hệ thống hiểu thêm:

```text
Metric nghiệp vụ này được tính như thế nào?
```

Phase U3 giúp hệ thống biết hỏi:

```text
Trong dataset này có điều gì đáng chú ý?
```

Trước đây dashboard generic chủ yếu là thống kê. Sau U3, dashboard bắt đầu có “giọng phân tích” hơn:

- cột nào thiếu nhiều
- nhóm nào đóng góp nhiều
- xu hướng tăng hay giảm
- outlier nằm ở đâu
- tương quan mạnh nhất là gì
- nhóm target/conversion nào cao

Đây là bước rất quan trọng để project tiến gần hơn tới một AI analytics product thật sự. Nó không chỉ render chart, mà bắt đầu tạo được insight có evidence và câu hỏi follow-up.

## 10. Giới hạn còn lại

U2/U3 hiện vẫn còn giới hạn:

- Chưa có frontend metric editor đầy đủ.
- Frontend metric editor đã có bản đầu, nhưng chưa có autocomplete/parser preview nâng cao.
- Metric CRUD không còn chỉ dùng API, nhưng UI vẫn nên được nâng thêm UX validation.
- Chưa có metric version history.
- Chưa có metric sharing giữa dataset/workspace.
- Chưa validate unit/format sâu từ Data Dictionary.
- Expression chưa hỗ trợ conditional logic, rolling window, window functions.
- Insight engine v2 vẫn heuristic, chưa có evaluation benchmark nhiều dataset.
- Agent mới route custom metric bằng rule-based matching đơn giản.
- Chưa có Universal Planner Intent Schema.

## 11. Bước tiếp theo đề xuất

Sau U2/U3, thứ tự hợp lý là:

1. **Metric Builder UI**
   - Thêm panel tạo/sửa/xóa metric trong Smart Dashboard.
   - Gợi ý role/column có thể dùng trong expression.
   - Preview metric result trước khi save.

2. **U4 - Universal Planner Intent Schema**
   - Parse câu hỏi thành intent:
     - metric
     - dimension
     - time grain
     - filters
     - comparison
   - Agent dùng intent để chọn tool thay vì keyword/router rời rạc.

3. **Insight Evaluation Suite**
   - Test insight quality trên 20-50 CSV.
   - Đo dashboard coverage, semantic mapping accuracy, answer correctness.

4. **Frontend Insight UX**
   - Cho insight card có nút Ask this.
   - Link insight tới chart/table liên quan.
   - Filter insight theo type/severity.

## 12. Definition of Done

Phase U2/U3 đạt DoD:

- Có safe expression engine.
- Có metric builder service.
- Có metric CRUD/evaluate APIs.
- Có metric storage theo dataset.
- Dashboard dùng custom metric.
- Agent dùng custom metric breakdown.
- Có generic insight engine v2.
- Dashboard append insight v2.
- Tests pass.
- Có file nghiệm thu.

Tình trạng hiện tại:

```text
Done for backend-first U2/U3 foundation.
```
