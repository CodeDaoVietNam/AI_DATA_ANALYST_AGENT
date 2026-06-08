# Universal CSV Intelligence Plan - Chuẩn bị phân tích tốt nhiều loại CSV hơn

## 1. Mục tiêu của phase này

Hiện project đã phân tích tốt các domain đã được thiết kế sẵn như ecommerce, retail, marketing và HR. Tuy nhiên, để tiến tới mục tiêu **"mọi CSV đều được phân tích tốt hơn"**, project cần thêm một lớp hiểu dữ liệu phổ quát hơn.

Phase này tập trung vào 5 năng lực chính:

1. Data dictionary upload/edit.
2. Custom metric builder.
3. Generic insight engine v2.
4. Universal planner intent schema.
5. Evaluation suite với nhiều dataset thuộc nhiều domain.

Mục tiêu không phải là production hóa ngay, mà là làm cho project hiểu nhiều loại CSV hơn trước khi bước sang các phase production như auth, workspace, monitoring, deployment.

## 2. Vấn đề hiện tại

Project hiện tại có:

- Semantic mapper tự đoán domain và role cột.
- Dashboard domain-aware.
- Generic tools cho CSV bất kỳ.
- AI Copilot gọi deterministic tools.
- Multi-step agent cho một số câu hỏi phức tạp.

Nhưng vẫn còn các giới hạn:

- Nếu tên cột lạ, semantic mapper có thể đoán sai.
- Nếu dataset thuộc domain mới như logistics, finance, education, survey, product analytics, dashboard chỉ fallback generic.
- User chưa thể upload data dictionary để giải thích ý nghĩa cột.
- Chưa có metric layer để định nghĩa metric mới như `margin`, `conversion_rate`, `on_time_rate`.
- Generic insight còn chưa đủ sâu để tự tìm trend, anomaly, driver, top/bottom contributor.
- Agent chưa parse câu hỏi thành intent schema rõ ràng.
- Chưa có eval suite lớn để đo project phân tích đúng bao nhiêu phần trăm trên nhiều CSV.

## 3. Nguyên tắc thiết kế

Phase này nên giữ các nguyên tắc sau:

- Deterministic tools vẫn là source of truth.
- LLM chỉ hỗ trợ parse intent hoặc giải thích, không tự bịa số liệu.
- Mọi metric tính toán phải trace được về column/role/tool result.
- User override luôn có ưu tiên cao hơn auto-detection.
- Nếu confidence thấp, hệ thống phải nói rõ thay vì đoán bừa.
- Eval phải đi cùng feature, không để đến cuối.
- Không dùng LangGraph ngay trong phase này; chỉ chuẩn bị interface để migrate sau.

## 4. Tài liệu/nền tảng nên tham khảo

Các nguồn nên học theo khi thiết kế:

- W3C CSV on the Web Metadata: https://www.w3.org/TR/tabular-metadata/
- Frictionless Table Schema: https://specs.frictionlessdata.io/table-schema/
- Frictionless Data Package: https://framework.frictionlessdata.io/docs/guides/describing-data.html
- Pandera DataFrame validation: https://pandera.readthedocs.io/
- Great Expectations validation: https://docs.greatexpectations.io/docs/guides/validation/validate_data_overview/
- DuckDB CSV/Parquet analytics: https://duckdb.org/docs/stable/clients/python/data_ingestion
- LangGraph docs, dùng sau khi planner/tool layer ổn: https://docs.langchain.com/oss/python/langgraph

## 5. Phase U1 - Data Dictionary Upload/Edit

### 5.1 Mục tiêu

Cho phép user mô tả ý nghĩa từng cột để hệ thống không phụ thuộc hoàn toàn vào heuristic auto-detection.

Ví dụ user upload một CSV có cột:

```text
amt, dt, prod_grp, cust_seg
```

Auto mapper có thể đoán sai. Data dictionary giúp khai báo:

```text
amt = revenue
dt = date
prod_grp = category
cust_seg = segment
```

### 5.2 Data dictionary format

Nên hỗ trợ CSV và JSON.

CSV format đề xuất:

```csv
column_name,business_name,description,semantic_role,data_type,unit,aggregation,sensitive,allowed_values
Sales,Revenue,Total sales amount,revenue,number,USD,sum,false,
Order Date,Order Date,Date order was placed,date,date,,,
Segment,Customer Segment,Customer group,segment,string,,,
Profit,Profit,Net profit,profit,number,USD,sum,false,
Discount,Discount,Discount rate,discount,number,percent,mean,false,
```

JSON format đề xuất:

```json
{
  "domain": "retail",
  "fields": [
    {
      "column_name": "Sales",
      "business_name": "Revenue",
      "description": "Total sales amount",
      "semantic_role": "revenue",
      "data_type": "number",
      "unit": "USD",
      "aggregation": "sum",
      "sensitive": false,
      "allowed_values": []
    }
  ]
}
```

### 5.3 Backend changes

File/service đề xuất:

- `app/services/data_dictionary.py`
- `app/schemas/models.py`
- `app/main.py`

Model đề xuất:

```python
class DataDictionaryField(BaseModel):
    column_name: str
    business_name: str | None = None
    description: str | None = None
    semantic_role: str | None = None
    data_type: str | None = None
    unit: str | None = None
    aggregation: str | None = None
    sensitive: bool = False
    allowed_values: list[str] = []


class DataDictionary(BaseModel):
    domain: str | None = None
    fields: list[DataDictionaryField]
```

API đề xuất:

- `POST /datasets/{dataset_id}/data-dictionary`
- `GET /datasets/{dataset_id}/data-dictionary`
- `PUT /datasets/{dataset_id}/data-dictionary`
- `DELETE /datasets/{dataset_id}/data-dictionary`

Behavior:

- Validate `column_name` phải tồn tại trong dataset.
- Nếu dictionary có `semantic_role`, role này ưu tiên cao hơn auto-detection.
- Nếu dictionary có `domain`, domain này ưu tiên cao hơn domain heuristic.
- Khi update dictionary, tăng `semantic_version`.
- Invalidate semantic/dashboard/tool cache.

### 5.4 Frontend changes

Thêm vào Smart Dashboard hoặc tab riêng:

- Data Dictionary panel.
- Upload dictionary CSV/JSON.
- Table edit inline:
  - column name
  - business name
  - description
  - semantic role
  - data type
  - unit
  - aggregation
  - sensitive
- Save/reset dictionary.
- Hiển thị mapping source:
  - auto
  - dictionary
  - user override

### 5.5 Tests

Unit tests:

- Parse dictionary CSV.
- Parse dictionary JSON.
- Reject dictionary có column không tồn tại.
- Dictionary role override semantic mapper.
- Update dictionary invalidates dashboard cache.

Integration tests:

- Upload dataset.
- Upload dictionary.
- `GET /semantic-profile/{dataset_id}` trả role theo dictionary.
- `GET /dashboard/{dataset_id}` dùng domain/role từ dictionary.

### 5.6 Definition of Done

- User upload được data dictionary.
- Semantic mapper dùng dictionary làm source ưu tiên.
- Dashboard refresh theo dictionary.
- Data dictionary hiển thị và chỉnh được trên frontend.

## 6. Phase U2 - Custom Metric Builder

### 6.1 Mục tiêu

Cho phép user định nghĩa metric mới từ các column/role đã có.

Ví dụ:

- `margin = profit / revenue`
- `conversion_rate = conversions / visits`
- `avg_order_value = revenue / orders`
- `on_time_rate = on_time_deliveries / total_deliveries`
- `retention_rate = retained_users / total_users`

### 6.2 Metric definition schema

Schema đề xuất:

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

### 6.3 Expression safety

Không dùng `eval` trực tiếp.

Nên tạo expression parser an toàn bằng Python AST allowlist:

Cho phép:

- column/role names
- numeric constants
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

Không cho phép:

- import
- attribute access
- function arbitrary
- file/network/system calls

### 6.4 Backend changes

Service đề xuất:

- `app/services/metric_builder.py`
- `app/services/expression_engine.py`

Functions:

```python
def validate_metric_definition(definition, profile) -> list[str]:
    ...

def evaluate_metric(df, profile, definition) -> pd.Series | float:
    ...

def list_metrics(dataset_id) -> list[MetricDefinition]:
    ...
```

API đề xuất:

- `GET /datasets/{dataset_id}/metrics`
- `POST /datasets/{dataset_id}/metrics`
- `PUT /datasets/{dataset_id}/metrics/{metric_name}`
- `DELETE /datasets/{dataset_id}/metrics/{metric_name}`
- `POST /datasets/{dataset_id}/metrics/{metric_name}/evaluate`

### 6.5 Integration với dashboard/tools

Metric builder phải tích hợp với:

- semantic profile
- dashboard builder
- generic insight engine
- agent planner

Nếu user tạo `margin`, dashboard retail/finance nên có KPI margin.

Nếu user hỏi:

```text
margin theo category như thế nào?
```

Planner phải map:

- intent: breakdown
- metric: custom metric `margin`
- dimension: category

### 6.6 Tests

Test cases:

- `profit / revenue` tính đúng.
- Chia cho 0 trả `None` hoặc `NaN` có kiểm soát.
- Expression dùng role name hoạt động.
- Expression dùng column name hoạt động.
- Unsafe expression bị reject.
- Metric xuất hiện trong dashboard.
- Agent dùng được custom metric trong breakdown.

### 6.7 Definition of Done

- User tạo/sửa/xóa metric được.
- Metric được dùng trong dashboard.
- Agent có thể dùng custom metric khi trả lời.
- Expression engine an toàn.

## 7. Phase U3 - Generic Insight Engine v2

### 7.1 Mục tiêu

Làm dashboard generic thông minh hơn cho mọi dataset, kể cả khi chưa detect được domain.

### 7.2 Insight types cần hỗ trợ

Insight engine v2 nên có các detector:

1. Data quality insight
   - missing columns
   - duplicate rows
   - high null percentage
   - suspicious constant columns

2. Distribution insight
   - numeric min/max/mean/median
   - skewness nếu cần
   - outlier count

3. Top/bottom contributor
   - top categories by metric
   - bottom categories by metric

4. Trend insight
   - metric over time
   - growth/decline
   - moving average optional

5. Anomaly insight
   - periods unusually high/low
   - z-score/IQR simple baseline

6. Segment difference
   - compare metric across groups
   - flag large gaps

7. Correlation insight
   - strongest positive/negative correlation
   - warning: correlation is not causation

8. Pareto insight
   - 80/20 contributor analysis

9. Target/conversion insight
   - positive rate by group
   - high-risk/high-opportunity segment

### 7.3 Unified insight schema

Mọi insight nên trả cùng format:

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

### 7.4 Backend changes

Service đề xuất:

- `app/services/generic_insight_engine.py`

Functions:

```python
def generate_generic_insights(df, profile, metrics, max_insights=10) -> list[InsightCard]:
    ...

def detect_data_quality_insights(df) -> list[InsightCard]:
    ...

def detect_trend_insights(df, profile, metrics) -> list[InsightCard]:
    ...

def detect_segment_insights(df, profile, metrics) -> list[InsightCard]:
    ...
```

### 7.5 Dashboard integration

`dashboard_builder.py` nên dùng generic insight engine cho:

- generic dashboard
- finance dashboard
- unknown/new domain dashboard
- domain dashboards khi thiếu domain-specific insight

### 7.6 Tests

Test cases:

- Missing value insight xuất hiện khi null > threshold.
- Top contributor insight đúng.
- Trend insight đúng khi có date + metric.
- Outlier insight đúng với numeric outlier.
- Correlation insight đúng với numeric columns.
- Không crash khi dataset toàn text.
- Không crash khi dataset nhỏ.

### 7.7 Definition of Done

- Generic dashboard có insight thật sự hữu ích.
- Insight có evidence và next question.
- Không phụ thuộc domain-specific tools.

## 8. Phase U4 - Universal Planner Intent Schema

### 8.1 Mục tiêu

Agent không chỉ chọn tool bằng keyword, mà parse câu hỏi thành một intent có cấu trúc.

Ví dụ:

```text
Doanh thu theo category trong năm 2023 như thế nào?
```

Parse thành:

```json
{
  "intent": "breakdown",
  "metric": {
    "role": "revenue",
    "column": "Sales"
  },
  "dimension": {
    "role": "category",
    "column": "Category"
  },
  "filters": [
    {
      "role": "date",
      "operator": "between",
      "value": ["2023-01-01", "2023-12-31"]
    }
  ],
  "time_grain": null,
  "needs_chart": false,
  "confidence": 0.84
}
```

### 8.2 Intent types

Intent enum đề xuất:

- `overview`
- `data_quality`
- `missing_values`
- `duplicates`
- `breakdown`
- `trend`
- `compare_segments`
- `top_bottom`
- `correlation`
- `outlier`
- `anomaly`
- `forecast`
- `period_over_period`
- `explain_change`
- `target_summary`
- `chart`
- `custom_calculation`

### 8.3 Planner flow

Flow đề xuất:

```text
question
  -> normalize question
  -> load semantic profile + data dictionary + custom metrics
  -> rule parser attempt
  -> if confidence low, ask LLM to parse intent JSON
  -> validate intent against dataset
  -> convert intent to tool plan
  -> execute deterministic tools
  -> compact result
  -> LLM explanation or deterministic fallback
```

### 8.4 Intent validation

Backend phải validate:

- metric tồn tại không
- metric numeric không
- dimension tồn tại không
- date role parse được không
- filter column hợp lệ không
- custom metric expression hợp lệ không
- intent có tool tương ứng không

Nếu confidence thấp:

- Trả fallback hỏi user chỉnh semantic mapping.
- Hoặc gợi ý 2-3 mapping có thể chọn.

### 8.5 Tool plan schema

```json
{
  "plan_id": "...",
  "strategy": "intent_to_tools",
  "intent": {},
  "steps": [
    {
      "tool_name": "semantic_breakdown",
      "arguments": {
        "metric": "revenue",
        "dimension": "category"
      },
      "purpose": "Break down revenue by category"
    }
  ]
}
```

### 8.6 Backend changes

Service đề xuất:

- `app/services/intent_parser.py`
- `app/services/intent_validator.py`
- `app/services/universal_planner.py`

Agent orchestrator nên gọi planner mới thay vì nhồi logic vào một file lớn.

### 8.7 Tests

Test cases:

- “doanh thu theo category” -> breakdown.
- “sales trend by month” -> trend.
- “top 5 products by revenue” -> top_bottom.
- “cột nào thiếu nhiều nhất” -> missing_values.
- “attrition theo department” -> target_summary.
- “margin theo segment” dùng custom metric.
- Câu hỏi mơ hồ trả low-confidence fallback.

### 8.8 Definition of Done

- Agent có intent object rõ ràng trong response.
- Tool plan được sinh từ intent.
- Dễ debug vì biết câu hỏi được hiểu như thế nào.

## 9. Phase U5 - Evaluation Suite với 20-50 CSV

### 9.1 Mục tiêu

Đo được project có thật sự phân tích tốt nhiều loại CSV hay không.

Nếu không có eval, mọi nâng cấp AI chỉ là cảm giác.

### 9.2 Dataset domains cần gom

Tối thiểu 20 dataset, lý tưởng 50 dataset.

Domain đề xuất:

1. Ecommerce
2. Retail
3. Finance
4. Marketing
5. HR
6. Logistics
7. Education
8. Survey
9. Product analytics
10. Generic public tabular data

### 9.3 Nguồn dataset gợi ý

Nguồn nên dùng:

- Kaggle datasets
- Maven Analytics Data Playground
- UCI Machine Learning Repository
- Data.gov
- World Bank / OECD public datasets
- Frictionless Data examples
- Synthetic datasets tự tạo để test edge cases

### 9.4 Cấu trúc thư mục eval

```text
evals/
  datasets/
    ecommerce/
    retail/
    finance/
    marketing/
    hr/
    logistics/
    education/
    survey/
    product/
    generic/
  dictionaries/
    ecommerce/
    retail/
    finance/
  questions/
    ecommerce.jsonl
    retail.jsonl
    finance.jsonl
    marketing.jsonl
    hr.jsonl
  expected/
    ecommerce_expected.json
  reports/
    latest.md
  run_eval.py
```

### 9.5 Eval case schema

```json
{
  "id": "retail_001",
  "dataset": "retail/superstore.csv",
  "data_dictionary": "retail/superstore_dictionary.csv",
  "question": "Doanh thu theo category là gì?",
  "expected_domain": "retail",
  "expected_intent": "breakdown",
  "expected_metric_role": "revenue",
  "expected_dimension_role": "category",
  "expected_tool": "semantic_breakdown",
  "numeric_checks": [
    {
      "label": "Technology",
      "metric": "revenue",
      "expected": 123456.0,
      "tolerance": 0.01
    }
  ],
  "answer_must_include": ["Technology"],
  "answer_must_not_include": ["I guess", "maybe"]
}
```

### 9.6 Metrics cần đo

Eval report cần có:

- Domain detection accuracy.
- Semantic role mapping accuracy.
- Intent parsing accuracy.
- Tool selection accuracy.
- Numeric correctness.
- Answer constraint pass rate.
- Fallback rate.
- Average latency.
- p95 latency.
- Cache hit rate.
- Error rate.

### 9.7 Eval runner flow

```text
for each eval case:
  load dataset
  upload/test through backend service layer
  apply data dictionary if provided
  build semantic profile
  parse intent
  run planner/agent
  compare domain/intent/tool/result
  record latency/errors
generate markdown report
```

### 9.8 Definition of Done

- Có ít nhất 20 CSV eval.
- Có ít nhất 100 câu hỏi eval.
- Có command chạy eval.
- Có markdown report.
- Có threshold pass/fail.

Ví dụ threshold ban đầu:

- Domain detection >= 80%.
- Role mapping >= 75%.
- Tool selection >= 80%.
- Numeric correctness >= 90% với deterministic checks.
- No hallucinated numeric answer trong eval set.

## 10. Có nên dùng LangGraph trong phase này không?

Khuyến nghị: **chưa dùng ngay trong phase U1-U5**.

Lý do:

- Bottleneck hiện tại là hiểu CSV, metric và eval.
- LangGraph giải quyết orchestration, không tự làm semantic mapping tốt hơn.
- Nếu semantic layer chưa tốt, graph chỉ làm workflow phức tạp hơn.
- Project hiện đã có orchestrator multi-step đủ dùng cho phase này.

Nên chuẩn bị interface để migrate sau:

- Intent schema rõ ràng.
- Tool plan schema rõ ràng.
- Agent run state rõ ràng.
- Tool registry độc lập.
- Result validator độc lập.

Sau U1-U5, có thể làm Phase U6:

```text
LangGraph migration
  receive question
  load dataset context
  check semantic confidence
  ask user mapping if low confidence
  parse intent
  validate intent
  plan tools
  execute tools
  validate result
  synthesize answer
  save agent run
```

Khi đó LangGraph sẽ hữu ích vì workflow đã đủ rõ.

## 11. Thứ tự implement khuyến nghị

Không nên làm tất cả cùng lúc. Thứ tự tốt nhất:

### Sprint 1 - Data dictionary foundation

- Tạo schema data dictionary.
- Upload/get/update/delete dictionary.
- Semantic mapper dùng dictionary.
- Frontend panel upload/edit dictionary.
- Tests.

### Sprint 2 - Metric builder

- Metric definition schema.
- Safe expression parser.
- Metric CRUD.
- Metric evaluate endpoint.
- Dashboard dùng custom metrics.
- Tests.

### Sprint 3 - Generic insight engine v2

- Insight detectors.
- Unified insight schema.
- Dashboard generic nâng cấp.
- Tests với dataset domain lạ.

### Sprint 4 - Universal planner intent schema

- Intent parser.
- Intent validator.
- Tool plan generator.
- Agent response có intent.
- Tests câu hỏi phổ biến.

### Sprint 5 - Eval suite

- Gom 20 CSV.
- Tạo 100 câu hỏi eval.
- Tạo eval runner.
- Tạo report.
- Dùng report để sửa mapper/planner.

## 12. Các file dự kiến cần tạo/sửa

### Backend files mới

- `app/services/data_dictionary.py`
- `app/services/metric_builder.py`
- `app/services/expression_engine.py`
- `app/services/generic_insight_engine.py`
- `app/services/intent_parser.py`
- `app/services/intent_validator.py`
- `app/services/universal_planner.py`

### Backend files cần sửa

- `app/main.py`
- `app/schemas/models.py`
- `app/services/semantic_mapper.py`
- `app/services/dashboard_builder.py`
- `app/services/agent_orchestrator.py`
- `app/services/storage.py`
- `app/database.py`

### Frontend files cần sửa/tách

- `web/src/App.tsx`
- `web/src/api.ts`
- `web/src/types.ts`

Nên tách dần:

- `web/src/components/DataDictionaryPanel.tsx`
- `web/src/components/MetricBuilderPanel.tsx`
- `web/src/components/InsightCard.tsx`
- `web/src/components/SemanticMappingPanel.tsx`
- `web/src/pages/DashboardPage.tsx`
- `web/src/pages/AskPage.tsx`

### Eval files mới

- `evals/run_eval.py`
- `evals/questions/*.jsonl`
- `evals/datasets/**`
- `evals/reports/latest.md`

## 13. Rủi ro dễ gặp

### Rủi ro 1 - Metric expression không an toàn

Không dùng `eval` trực tiếp. Phải parse AST allowlist.

### Rủi ro 2 - Data dictionary override sai

Nếu user mapping sai, dashboard sẽ sai. Vì vậy cần:

- hiển thị source mapping
- hiển thị confidence
- cho reset
- cảnh báo nếu data type không khớp role

### Rủi ro 3 - Insight engine tạo quá nhiều insight

Cần ranking:

- severity
- confidence
- business value
- data quality impact

Dashboard chỉ nên hiển thị top 5-10 insight.

### Rủi ro 4 - LLM parse intent sai

Phải validate intent bằng backend. Không tin LLM tuyệt đối.

### Rủi ro 5 - Eval quá ít

Nếu chỉ test 3-4 dataset thì không gọi là universal. Cần tối thiểu 20 CSV.

## 14. Definition of Done toàn phase

Phase này hoàn thành khi:

- User upload/edit được data dictionary.
- Semantic mapper ưu tiên dictionary/user override.
- User tạo được custom metric an toàn.
- Dashboard generic có insight v2 thật sự hữu ích.
- Agent có intent schema rõ ràng.
- Agent sinh tool plan từ intent.
- Có ít nhất 20 CSV eval.
- Có ít nhất 100 câu hỏi eval.
- Eval report đo domain/role/intent/tool/numeric correctness.
- Backend tests pass.
- Frontend build pass.

Khi đạt xong phase này, project sẽ tiến gần hơn tới mục tiêu:

> Không chỉ phân tích tốt Amazon/Superstore/Marketing/HR, mà có nền tảng để phân tích tốt nhiều loại CSV khác nhau một cách có kiểm soát, đo lường được và có thể mở rộng.
