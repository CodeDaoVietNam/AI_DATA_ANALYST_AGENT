# Checkpoint Summary - Những gì đã hoàn thành ở phase nền móng

Tài liệu này tổng kết trạng thái hiện tại của project sau khi hoàn thành phase nền móng cho Amazon Sales Analyzer.

Mục tiêu của file này:

- Ghi lại những gì đã làm.
- Ghi lại kiến trúc hiện tại sau thay đổi.
- Ghi lại các file đã thêm/chỉnh.
- Ghi lại kết quả kiểm thử.
- Làm checkpoint trước khi chuyển sang phase tiếp theo.

## 1. Bối cảnh trước phase này

Ban đầu project là một starter app:

```text
CSV upload
  -> FastAPI backend
  -> Pandas profiler
  -> rule-based chat
  -> Streamlit UI
  -> Markdown report
```

Project đã có:

- `app/main.py`
- `app/services/profiler.py`
- `app/services/storage.py`
- `app/services/agent.py`
- `app/tools/pandas_tool.py`
- `frontend/streamlit_app.py`
- `data/sample/ecommerce_sales.csv`
- `data/raw/Amazon Sale Report.csv`

Nhưng trước phase này, logic cho Amazon Sales dataset mới chỉ nằm trong notebook exploration, chưa được chuyển thành code dùng lại được.

## 2. Mục tiêu phase vừa làm

Mục tiêu không phải thêm LLM ngay.

Mục tiêu là:

```text
Notebook insight
  -> data cleaner
  -> feature engineering
  -> ecommerce analysis tools
  -> backend endpoints
  -> Streamlit ecommerce insights
  -> tests
```

Lý do:

```text
LLM/tool calling chỉ đáng tin khi các deterministic tools đã tính đúng.
```

## 3. Notebook đã được nâng cấp

Notebook chính:

```text
notebooks/01_amazon_sales_eda.ipynb
```

Notebook đã được nâng cấp từ một khung EDA cơ bản thành notebook phân tích có chiều sâu hơn.

Các phần đã có:

- Load raw Amazon Sales dataset.
- Kiểm tra shape, columns, dtypes.
- Missing values analysis.
- Duplicate/order ID analysis.
- Column cleaning thử nghiệm.
- Date parsing.
- Text normalization.
- Numeric/categorical analysis.
- Feature engineering thử nghiệm.
- Revenue by month/day.
- Revenue by category.
- Category revenue vs cancel rate.
- Revenue by state/city.
- Status distribution.
- Fulfilment/courier analysis.
- B2B analysis.
- Promotion analysis.
- SKU/size analysis.
- Outlier check.
- Correlation cơ bản.
- Data quality warnings.
- Recommended charts.
- Recommended reusable tools.
- Kết luận EDA.

Notebook hiện có nhiều chart hơn và có nhận xét Markdown sau các phần quan trọng.

## 4. Những insight chính rút ra từ notebook

### 4.1 Dataset ở cấp line-item

`Order ID` bị lặp nhiều lần, nhưng không nên coi đó là lỗi ngay.

Ý nghĩa:

```text
Một order có thể gồm nhiều dòng sản phẩm/SKU.
```

Do đó:

- Không drop duplicate theo `order_id`.
- Khi tính số đơn, dùng `order_id.nunique()`.
- Khi tính revenue/qty, có thể sum theo line-item.

### 4.2 Dataset cần cleaning

Các vấn đề phát hiện:

- Tên cột có khoảng trắng: `Sales Channel `.
- Tên cột có dấu hyphen: `ship-service-level`.
- Cột thừa: `index`.
- Cột không rõ nghĩa: `Unnamed: 22`.
- `Date` là object.
- City/state có thể không đồng nhất viết hoa/thường.

### 4.3 Missing values có ý nghĩa nghiệp vụ

Các điểm đáng chú ý:

- `fulfilled_by` missing nhiều.
- `promotion_ids` missing nhiều.
- `Amount` và `currency` missing 7,795 dòng.
- Shipping fields missing rất ít.

Quan trọng:

```text
Không fill amount bằng 0 một cách im lặng.
Phải báo missing amount trong data quality.
```

### 4.4 Cancellation là phân tích bắt buộc

Cancel rate khoảng 14.21% theo line-item.

Vì vậy cần có tool riêng:

- cancellation summary.
- cancel rate by category.
- cancel rate by fulfilment.

### 4.5 Category/location/fulfilment là các trục phân tích chính

Các analysis quan trọng:

- revenue by category.
- top states by revenue.
- revenue by month.
- cancel rate by fulfilment.

## 5. File mới đã thêm

### 5.1 Data cleaner

```text
app/services/data_cleaner.py
```

Vai trò:

- Chuẩn hóa tên cột.
- Clean Amazon Sales dataset.
- Drop cột thừa.
- Parse date.
- Strip text.
- Uppercase location.
- Normalize category.

Hàm chính:

```python
clean_column_name(column)
clean_column_names(df)
clean_amazon_sales_data(df)
```

Thiết kế quan trọng:

- `clean_column_names` là generic, dùng được cho mọi CSV.
- `clean_amazon_sales_data` là domain-specific cho Amazon Sales.

### 5.2 Feature engineering

```text
app/services/feature_engineering.py
```

Vai trò:

- Tạo các feature ecommerce từ dữ liệu đã clean.

Hàm chính:

```python
add_amazon_sales_features(df)
```

Features đã tạo:

```text
order_year
order_month
order_day
order_day_name
status_clean
is_cancelled
is_shipped
is_delivered
has_promotion
revenue
amount_per_item
```

Thiết kế quan trọng:

- Không mutate input DataFrame.
- Tolerant với missing optional columns.
- Không chia cho 0 khi tính `amount_per_item`.

### 5.3 Dataset pipeline

```text
app/services/dataset_pipeline.py
```

Vai trò:

```text
raw dataframe
  -> clean_amazon_sales_data
  -> add_amazon_sales_features
  -> prepared dataframe
```

Hàm chính:

```python
prepare_amazon_sales_dataframe(df)
```

Lý do tạo pipeline:

- Backend endpoint không phải chứa quá nhiều logic.
- Dễ thay đổi cleaning/features sau này.
- Giữ boundary rõ giữa API và data processing.

### 5.4 Ecommerce tools

```text
app/tools/ecommerce_tools.py
```

Vai trò:

- Chứa các deterministic tools cho Amazon/ecommerce analysis.
- Trả output JSON-serializable.
- Có validation cột bắt buộc.

Helpers:

```python
require_columns(df, columns)
records(df)
```

Tools đã implement:

```python
get_sales_overview(df)
get_data_quality_summary(df)
revenue_by_month(df)
revenue_by_category(df)
top_states_by_revenue(df, n=10)
cancellation_summary(df)
```

## 6. File test mới đã thêm

### 6.1 Data cleaner tests

```text
tests/test_data_cleaner.py
```

Test coverage:

- `clean_column_name`.
- `clean_column_names` không mutate input.
- Clean Amazon columns.
- Drop `index` và `unnamed_22`.
- Parse date.
- Uppercase city/state.
- Title case category.
- Missing optional columns không crash.

### 6.2 Feature engineering tests

```text
tests/test_feature_engineering.py
```

Test coverage:

- `is_cancelled`.
- `is_shipped`.
- `is_delivered`.
- `has_promotion`.
- `amount_per_item`.
- Time features.
- Missing optional columns.

### 6.3 Ecommerce tools tests

```text
tests/test_ecommerce_tools.py
```

Test coverage:

- `get_sales_overview`.
- `get_data_quality_summary`.
- `revenue_by_month`.
- `revenue_by_category`.
- `top_states_by_revenue`.
- `top_states_by_revenue` validate `n`.
- `cancellation_summary`.

## 7. Backend đã được nâng cấp

File chỉnh:

```text
app/main.py
```

Đã thêm ecommerce endpoints:

```text
GET /ecommerce/overview/{dataset_id}
GET /ecommerce/revenue-by-month/{dataset_id}
GET /ecommerce/revenue-by-category/{dataset_id}
GET /ecommerce/top-states/{dataset_id}
GET /ecommerce/cancellation/{dataset_id}
```

Luồng endpoint:

```text
load dataframe từ dataset_store
  -> prepare_amazon_sales_dataframe
  -> gọi ecommerce tool
  -> trả JSON
```

Endpoint quan trọng nhất:

```text
GET /ecommerce/overview/{dataset_id}
```

Response gồm:

```json
{
  "dataset_id": "...",
  "overview": {},
  "data_quality": {}
}
```

## 8. Streamlit đã được nâng cấp

File chỉnh:

```text
frontend/streamlit_app.py
```

Đã thêm section:

```text
Ecommerce Insights
```

Hiển thị:

- Total revenue.
- Unique orders.
- Cancel rate.
- Missing amount rows.
- Date range.
- Data quality warnings.
- Revenue by category table.
- Revenue by category bar chart.
- Revenue by month line chart.

Nếu dataset không phù hợp Amazon Sales style, UI sẽ báo nhẹ:

```text
Ecommerce-specific insights are available for Amazon Sales style datasets.
```

## 9. Kết quả kiểm thử

Bạn đã chạy:

```bash
PYTHONPATH=. pytest -q
```

Kết quả:

```text
15 passed, 1 warning in 1.06s
```

Điều này xác nhận:

- Test cũ vẫn pass.
- Data cleaner pass.
- Feature engineering pass.
- Ecommerce tools pass.

Warning còn lại:

```text
app/services/profiler.py: UserWarning: Could not infer format
```

Warning này đến từ profiler cũ khi thử parse datetime bằng:

```python
pd.to_datetime(series, errors="coerce")
```

Đây không phải lỗi phase này, nhưng nên cải thiện sau.

## 10. Số liệu xác minh trên Amazon Sale Report

Khi chạy pipeline trên:

```text
data/raw/Amazon Sale Report.csv
```

Các số chính:

```text
rows: 128,975
unique_orders: 120,378
date_min: 2022-03-31
date_max: 2022-06-29
total_revenue: 78,592,678.3
total_qty: 116,649
cancel_rate: 14.21%
missing_amount_rows: 7,795
missing_amount_percent: 6.04%
top category: Set
top state: MAHARASHTRA
cancelled_rows: 18,332
cancelled_orders: 17,185
```

Những số này khớp với insight từ notebook.

## 11. Kiến trúc hiện tại sau phase này

Luồng hiện tại:

```text
User upload CSV
  -> FastAPI /upload
  -> DatasetStore lưu raw CSV
  -> Streamlit gọi ecommerce endpoints
  -> Backend load raw CSV
  -> clean_amazon_sales_data
  -> add_amazon_sales_features
  -> ecommerce_tools
  -> JSON response
  -> Streamlit render metrics/tables/charts
```

Sơ đồ:

```text
Raw CSV
  -> DatasetStore
  -> Dataset Pipeline
      -> Data Cleaner
      -> Feature Engineering
  -> Ecommerce Tools
      -> Overview
      -> Data Quality
      -> Revenue by Month
      -> Revenue by Category
      -> Top States
      -> Cancellation
  -> FastAPI
  -> Streamlit
```

## 12. Điều đã làm đúng về mặt AI Engineering

Phase này quan trọng vì đã đặt đúng nền:

```text
Tính toán bằng tool trước.
LLM để sau.
```

Các điểm tốt:

- Không thêm LLM quá sớm.
- Không để notebook là source of truth duy nhất.
- Logic phân tích đã chuyển vào services/tools.
- Tools có test.
- Backend expose output dạng JSON.
- UI bắt đầu hiển thị insight thật.

Đây là hướng đúng để sau này thêm tool calling:

```text
LLM chọn tool
  -> tool tính bằng Pandas
  -> LLM giải thích kết quả
```

## 13. Những giới hạn hiện tại sau phase này

Vẫn còn một số giới hạn:

- Ecommerce cleaner hiện chỉ phù hợp Amazon Sales style dataset.
- Chưa có domain detector.
- Chưa có generic groupby tool nâng cao.
- Chưa có chart endpoint riêng.
- Chưa có LLM/tool calling.
- Chưa có database metadata.
- Chưa có Redis/rate limiting.
- Chưa xử lý async/background jobs cho file lớn.
- Warning trong profiler cũ chưa được xử lý.

Đây là các giới hạn bình thường ở checkpoint này.

## 14. Trạng thái hiện tại của project

Hiện tại project đã vượt qua mức starter ban đầu.

Nó đang ở trạng thái:

```text
AI Data Analyst Agent Starter
  + Amazon Sales deterministic analysis foundation
```

Có thể demo:

1. Upload `Amazon Sale Report.csv`.
2. Xem generic dataset summary.
3. Xem ecommerce insights.
4. Xem revenue by category/month.
5. Xem data quality warnings.
6. Chat rule-based cơ bản.
7. Export report cũ.

## 15. Bước tiếp theo nên làm gì?

Chưa nên nhảy ngay vào LangGraph.

Bước tiếp theo hợp lý là củng cố deterministic layer thêm một chút.

Ưu tiên đề xuất:

```text
1. Fix profiler datetime warning.
2. Thêm generic analysis tools.
3. Thêm chart endpoint dùng chart_generator.py.
4. Thêm ecommerce-specific chart outputs hoặc chart recommendations.
5. Sau đó mới thêm LLM tool calling.
```

Nếu muốn đi thật chắc, làm theo thứ tự:

### Next Step 1 - Fix profiler warning

File:

```text
app/services/profiler.py
```

Mục tiêu:

- Giảm warning khi infer datetime.
- Cải thiện type inference.
- Không làm hỏng test cũ.

### Next Step 2 - Generic analysis tools

File đề xuất:

```text
app/tools/generic_analysis_tools.py
```

Tools:

```text
get_dataset_overview
get_missing_values
get_duplicate_rows
groupby_aggregate
correlation_analysis
```

### Next Step 3 - Chart endpoint

Hiện đã có:

```text
app/services/chart_generator.py
```

Nhưng chưa expose đầy đủ qua API/UI.

Nên thêm:

```text
POST /chart
```

Hoặc:

```text
GET /ecommerce/charts/revenue-by-category/{dataset_id}
GET /ecommerce/charts/revenue-by-month/{dataset_id}
```

### Next Step 4 - LLM tool calling

Chỉ làm sau khi generic/ecommerce tools đủ ổn.

Mục tiêu:

```text
User question
  -> LLM chọn tool
  -> Pandas tool tính
  -> LLM giải thích
```

## 16. Kết luận checkpoint

Phase vừa rồi đã hoàn thành tốt phần nền:

- Data cleaner.
- Feature engineering.
- Ecommerce tools.
- Tests.
- Backend endpoints.
- Streamlit ecommerce insights.

Quan trọng nhất:

```text
Notebook insight đã được chuyển thành code có thể test và dùng lại.
```

Đây là checkpoint tốt trước khi chuyển sang các năng lực cao hơn như generic tools, chart endpoint, LLM tool calling và LangGraph.
