# Implementation Guide - Nền móng Amazon Sales Analyzer

Tài liệu này hướng dẫn cách bắt đầu implement sau notebook `01_amazon_sales_eda.ipynb`.

Vai trò của giai đoạn này:

```text
Notebook insight
  -> production-like data cleaner
  -> feature engineering
  -> reusable ecommerce tools
  -> tests
  -> API endpoint nhẹ
  -> Streamlit insight nhẹ
```

Đây chưa phải giai đoạn thêm LLM/LangGraph. Làm chắc nền deterministic trước. Khi tool tính đúng, LLM mới có thể gọi tool một cách đáng tin.

## 1. Mục tiêu kỹ thuật của phase này

Sau phase này, project cần có:

- Data cleaning pipeline cho Amazon sales dataset.
- Feature engineering pipeline dùng lại được.
- Ecommerce analysis tools trả về JSON-serializable data.
- Unit tests cho cleaner/features/tools.
- Ít nhất một backend endpoint cho ecommerce overview.
- Streamlit hiển thị được một số ecommerce insights.

Không làm trong phase này:

- Fine-tuning.
- LangGraph.
- Redis.
- Database metadata.
- Multi-file analysis.
- Forecasting nâng cao.
- PDF report.

## 2. Nguyên tắc implement

### 2.1 Không để production logic trong notebook

Notebook chỉ dùng để khám phá. Logic dùng thật phải nằm trong:

```text
app/services/
app/tools/
tests/
```

### 2.2 Tool phải deterministic

Mọi số liệu phải tính bằng Pandas.

Không viết kiểu:

```text
LLM tự đọc câu hỏi rồi tự trả số.
```

Phải đi theo:

```text
Tool tính số -> backend trả data -> sau này LLM giải thích.
```

### 2.3 Function nhỏ, dễ test

Tránh viết một function khổng lồ như:

```python
analyze_amazon_sales_everything(df)
```

Nên tách:

```python
clean_amazon_sales_data(df)
add_amazon_sales_features(df)
get_sales_overview(df)
revenue_by_category(df)
cancellation_summary(df)
```

### 2.4 Không mutate input DataFrame bất ngờ

Trong cleaner/features/tools, nên copy DataFrame trước khi sửa:

```python
result = df.copy()
```

Điều này giúp tránh bug khó tìm khi cùng một DataFrame được dùng nhiều nơi.

### 2.5 Output phải JSON-serializable

FastAPI cần trả JSON. Vì vậy tools không nên trả trực tiếp DataFrame.

Không nên:

```python
return df.groupby(...).sum()
```

Nên:

```python
return records_df.to_dict(orient="records")
```

Hoặc:

```python
return {
    "total_revenue": float(...),
    "rows": int(...),
    "items": [...]
}
```

## 3. Thứ tự implement đề xuất

Làm đúng thứ tự này:

```text
1. app/services/data_cleaner.py
2. tests/test_data_cleaner.py
3. app/services/feature_engineering.py
4. tests/test_feature_engineering.py
5. app/tools/ecommerce_tools.py
6. tests/test_ecommerce_tools.py
7. app/main.py endpoint mới
8. frontend/streamlit_app.py hiển thị nhẹ
9. README/docs cập nhật cách chạy
```

Lý do:

- Cleaner là nền.
- Feature phụ thuộc cleaner.
- Tools phụ thuộc cleaner/features.
- API phụ thuộc tools.
- UI phụ thuộc API.

## 4. Step 1 - Implement data cleaner

### File cần tạo

```text
app/services/data_cleaner.py
```

### Interface đề xuất

```python
from __future__ import annotations

import pandas as pd


def clean_column_name(column: str) -> str:
    ...


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    ...


def clean_amazon_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    ...
```

### `clean_column_name`

Nhiệm vụ:

- Strip khoảng trắng.
- Lowercase.
- Đổi space thành underscore.
- Đổi hyphen thành underscore.
- Bỏ colon.
- Gộp double underscore nếu có.

Ví dụ:

```text
"Order ID"              -> "order_id"
"Sales Channel "        -> "sales_channel"
"ship-service-level"    -> "ship_service_level"
"Unnamed: 22"           -> "unnamed_22"
```

### `clean_column_names`

Nhiệm vụ:

- Nhận DataFrame bất kỳ.
- Trả DataFrame copy với tên cột đã chuẩn hóa.

Không mutate input.

### `clean_amazon_sales_data`

Nhiệm vụ:

1. Gọi `clean_column_names`.
2. Drop các cột không cần:

```text
index
unnamed_22
```

3. Parse `date`:

```python
pd.to_datetime(df["date"], format="%m-%d-%y", errors="coerce")
```

4. Strip text columns:

```text
status
fulfilment
sales_channel
ship_service_level
category
size
courier_status
currency
ship_country
ship_city
ship_state
fulfilled_by
```

5. Uppercase location:

```text
ship_city
ship_state
ship_country
```

6. Normalize category:

```text
category -> title case
```

### Edge cases cần xử lý

- Nếu cột không tồn tại thì bỏ qua, không crash.
- Nếu date parse lỗi thì thành `NaT`.
- Nếu DataFrame empty thì vẫn trả DataFrame hợp lệ.

### Test trước khi qua step sau

Chạy:

```bash
PYTHONPATH=. pytest tests/test_data_cleaner.py -q
```

## 5. Step 2 - Test data cleaner

### File cần tạo

```text
tests/test_data_cleaner.py
```

### Test cases tối thiểu

#### Test 1 - Clean column name

```python
def test_clean_column_name():
    assert clean_column_name("Order ID") == "order_id"
    assert clean_column_name("Sales Channel ") == "sales_channel"
    assert clean_column_name("ship-service-level") == "ship_service_level"
    assert clean_column_name("Unnamed: 22") == "unnamed_22"
```

#### Test 2 - Clean Amazon columns

Input:

```python
pd.DataFrame({
    "index": [0],
    "Order ID": ["1"],
    "Date": ["04-30-22"],
    "Sales Channel ": ["Amazon.in"],
    "ship-city": ["Hyderabad"],
    "ship-state": ["Telangana"],
    "Category": ["kurta"],
    "Unnamed: 22": [None],
})
```

Expected:

- Có `order_id`.
- Có `sales_channel`.
- Có `ship_city`.
- Không còn `index`.
- Không còn `unnamed_22`.
- `date` là datetime.
- `ship_city == "HYDERABAD"`.
- `ship_state == "TELANGANA"`.
- `category == "Kurta"`.

## 6. Step 3 - Implement feature engineering

### File cần tạo

```text
app/services/feature_engineering.py
```

### Interface đề xuất

```python
from __future__ import annotations

import numpy as np
import pandas as pd


def add_amazon_sales_features(df: pd.DataFrame) -> pd.DataFrame:
    ...
```

### Features cần tạo

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

### Logic chi tiết

#### Time features

```python
df["order_year"] = df["date"].dt.year
df["order_month"] = df["date"].dt.to_period("M").astype(str)
df["order_day"] = df["date"].dt.day
df["order_day_name"] = df["date"].dt.day_name()
```

Nếu `date` không tồn tại hoặc không phải datetime:

- Có thể parse lại bằng `pd.to_datetime`.
- Hoặc raise lỗi rõ ràng.

Khuyến nghị phase này:

```text
Nếu thiếu date thì vẫn chạy được, nhưng bỏ qua time features.
```

#### Status flags

```python
status_clean = status.lower()
is_cancelled = contains "cancelled"
is_shipped = contains "shipped"
is_delivered = contains "delivered"
```

#### Promotion flag

```python
has_promotion = promotion_ids.notna()
```

Nếu thiếu `promotion_ids`:

```python
has_promotion = False
```

#### Revenue

```python
revenue = amount
```

Nếu thiếu `amount`:

```python
revenue = np.nan
```

#### Amount per item

```python
amount_per_item = amount / qty nếu qty > 0
amount_per_item = NaN nếu qty <= 0
```

Không được chia cho 0.

## 7. Step 4 - Test feature engineering

### File cần tạo

```text
tests/test_feature_engineering.py
```

### Test cases tối thiểu

#### Test 1 - Status flags

Input:

```python
pd.DataFrame({
    "date": pd.to_datetime(["2022-04-30", "2022-05-01"]),
    "status": ["Cancelled", "Shipped - Delivered to Buyer"],
    "promotion_ids": [None, "promo"],
    "amount": [100.0, 200.0],
    "qty": [0, 2],
})
```

Expected:

- Row 1 `is_cancelled = True`.
- Row 2 `is_shipped = True`.
- Row 2 `is_delivered = True`.
- Row 1 `has_promotion = False`.
- Row 2 `has_promotion = True`.
- Row 2 `amount_per_item = 100.0`.
- Row 1 `amount_per_item` is NaN.

#### Test 2 - Time features

Expected:

- `order_year = 2022`.
- `order_month = "2022-04"` hoặc `"2022-05"`.
- `order_day_name` tồn tại.

## 8. Step 5 - Implement ecommerce tools

### File cần tạo

```text
app/tools/ecommerce_tools.py
```

### Design quan trọng

Tools nên giả định input đã clean và đã có features.

Nhưng để an toàn, mỗi tool nên validate cột bắt buộc.

Tạo helper:

```python
def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
```

Tạo helper convert:

```python
def records(df: pd.DataFrame) -> list[dict]:
    return df.replace({np.nan: None}).to_dict(orient="records")
```

### Tool 1 - `get_sales_overview`

Interface:

```python
def get_sales_overview(df: pd.DataFrame) -> dict:
    ...
```

Required columns:

```text
order_id
date
revenue
qty
is_cancelled
amount
```

Output:

```python
{
    "rows": int,
    "columns": int,
    "unique_orders": int,
    "date_min": str | None,
    "date_max": str | None,
    "total_revenue": float,
    "total_qty": int,
    "cancel_rate": float,
    "missing_amount_rows": int,
    "missing_amount_percent": float,
    "notes": [...]
}
```

### Tool 2 - `get_data_quality_summary`

Interface:

```python
def get_data_quality_summary(df: pd.DataFrame) -> dict:
    ...
```

Output:

```python
{
    "duplicate_rows": int,
    "duplicate_order_id_rows": int,
    "missing_values": {...},
    "missing_percent": {...},
    "warnings": [...]
}
```

Warnings nên có:

- `amount` missing.
- shipping fields missing.
- duplicate rows.
- duplicate order IDs are likely multi-line orders.

### Tool 3 - `revenue_by_month`

Interface:

```python
def revenue_by_month(df: pd.DataFrame) -> list[dict]:
    ...
```

Output records:

```text
order_month
revenue
orders
qty
cancel_rate
```

### Tool 4 - `revenue_by_category`

Interface:

```python
def revenue_by_category(df: pd.DataFrame) -> list[dict]:
    ...
```

Output:

```text
category
revenue
revenue_share
qty
orders
cancel_rate
avg_amount
```

### Tool 5 - `top_states_by_revenue`

Interface:

```python
def top_states_by_revenue(df: pd.DataFrame, n: int = 10) -> list[dict]:
    ...
```

Validation:

- `n` phải từ 1 đến 100.

Output:

```text
ship_state
revenue
orders
qty
cancel_rate
```

### Tool 6 - `cancellation_summary`

Interface:

```python
def cancellation_summary(df: pd.DataFrame) -> dict:
    ...
```

Output:

```python
{
    "overall_cancel_rate": float,
    "cancelled_rows": int,
    "cancelled_orders": int,
    "by_category": [...],
    "by_fulfilment": [...],
}
```

## 9. Step 6 - Test ecommerce tools

### File cần tạo

```text
tests/test_ecommerce_tools.py
```

### Test strategy

Không dùng full Amazon CSV trong unit tests.

Tạo DataFrame nhỏ trong test:

```python
def sample_sales_df():
    return pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4"],
        "date": pd.to_datetime(["2022-04-01", "2022-04-02", "2022-05-01", "2022-05-02"]),
        "order_month": ["2022-04", "2022-04", "2022-05", "2022-05"],
        "category": ["Set", "Set", "Kurta", "Kurta"],
        "ship_state": ["A", "A", "B", "B"],
        "fulfilment": ["Amazon", "Merchant", "Amazon", "Merchant"],
        "qty": [1, 2, 1, 1],
        "amount": [100.0, 200.0, None, 400.0],
        "revenue": [100.0, 200.0, None, 400.0],
        "is_cancelled": [False, True, False, False],
    })
```

Test:

- Overview total revenue = 700.
- Missing amount rows = 1.
- Unique orders = 4.
- Revenue by category:
  - Set = 300.
  - Kurta = 400.
- Top state B revenue = 400.
- Cancel rate overall = 0.25.

## 10. Step 7 - Kết nối cleaner/features vào backend

Sau khi tests pass, tích hợp vào backend.

### Lựa chọn kỹ thuật đề xuất

Không nên clean/feature ngay trong `/upload` ở phase đầu.

Lý do:

- `/upload` nên chỉ lưu raw file.
- Nếu sau này cleaner thay đổi, không cần upload lại file.
- Summary/ecommerce endpoint có thể load raw rồi transform runtime.

Tạo helper trong `app/main.py` hoặc service riêng:

```python
def prepare_amazon_sales_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = clean_amazon_sales_data(df)
    featured = add_amazon_sales_features(cleaned)
    return featured
```

Về sau có thể chuyển helper này sang:

```text
app/services/dataset_pipeline.py
```

Nhưng phase đầu có thể giữ đơn giản.

## 11. Step 8 - Thêm endpoint ecommerce overview

### Endpoint đầu tiên

```text
GET /ecommerce/overview/{dataset_id}
```

Luồng:

```text
load dataframe
  -> clean_amazon_sales_data
  -> add_amazon_sales_features
  -> get_sales_overview
  -> get_data_quality_summary
  -> return JSON
```

Response đề xuất:

```json
{
  "dataset_id": "...",
  "overview": {},
  "data_quality": {}
}
```

### Endpoint thứ hai nếu còn thời gian

```text
GET /ecommerce/revenue-by-category/{dataset_id}
```

Response:

```json
{
  "dataset_id": "...",
  "items": []
}
```

### Endpoint thứ ba nếu còn thời gian

```text
GET /ecommerce/revenue-by-month/{dataset_id}
```

## 12. Step 9 - Cập nhật Streamlit nhẹ

Không cần làm UI lớn.

Sau khi user upload dataset, thêm section:

```text
Ecommerce Insights
```

Hiển thị:

- Total revenue.
- Unique orders.
- Cancel rate.
- Missing amount rows.
- Date range.
- Table revenue by category.

Nếu có thời gian, thêm chart:

- Revenue by category.
- Revenue by month.

Streamlit có thể dùng:

```python
st.bar_chart(...)
st.line_chart(...)
```

Hoặc dùng Plotly sau.

## 13. Commands nên chạy trong quá trình implement

### Run tests

```bash
PYTHONPATH=. pytest -q
```

Nếu `pytest` chưa có:

```bash
pip install -r requirements.txt
```

### Run backend

```bash
uvicorn app.main:app --reload
```

### Run frontend

```bash
streamlit run frontend/streamlit_app.py
```

### Test CLI cũ

```bash
PYTHONPATH=. python scripts/analyze.py data/sample/ecommerce_sales.csv --out reports
```

Đảm bảo code mới không làm hỏng flow cũ.

## 14. Quality checklist trước khi coi là xong

### Code quality

- Không có logic production nằm riêng trong notebook.
- Cleaner/features/tools có function nhỏ.
- Tools có validation cột bắt buộc.
- Output JSON-serializable.
- Không mutate input DataFrame bất ngờ.
- Không hard-code quá nhiều vào endpoint.

### Data correctness

- Date parse đúng.
- City/state được normalize.
- Category được normalize.
- Revenue sum khớp notebook.
- Cancel rate khớp notebook.
- Missing amount được báo rõ.
- Duplicate order ID không bị xử lý sai.

### Tests

- `test_data_cleaner.py` pass.
- `test_feature_engineering.py` pass.
- `test_ecommerce_tools.py` pass.
- Test cũ `test_profiler.py` vẫn pass.

### Product

- Backend có endpoint ecommerce overview.
- Frontend hiển thị insight cơ bản.
- User vẫn upload CSV được.
- Summary cũ vẫn hoạt động.

## 15. Các lỗi dễ mắc

### Lỗi 1 - Drop duplicate theo `order_id`

Không làm:

```python
df.drop_duplicates(subset=["order_id"])
```

Vì dataset là line-item level.

### Lỗi 2 - Fill missing amount bằng 0 không có cảnh báo

Không nên fill bừa:

```python
df["amount"] = df["amount"].fillna(0)
```

Nếu cần tính sum, Pandas đã skip NaN. Nhưng phải báo missing amount trong data quality.

### Lỗi 3 - Groupby city khi chưa normalize

Nếu chưa uppercase city/state, kết quả top city sẽ bị tách:

```text
HYDERABAD
Hyderabad
```

### Lỗi 4 - Tool trả DataFrame

Không trả DataFrame trực tiếp từ API tool.

Hãy convert sang records/dict.

### Lỗi 5 - Thêm LLM quá sớm

Nếu tools chưa ổn, LLM chỉ làm project trông phức tạp hơn, không làm nó đúng hơn.

## 16. Gợi ý thứ tự commit

Nếu dùng git sau này, commit nên chia nhỏ:

```text
commit 1: add data cleaner service and tests
commit 2: add feature engineering service and tests
commit 3: add ecommerce analysis tools and tests
commit 4: expose ecommerce overview API
commit 5: add Streamlit ecommerce insights
commit 6: update docs
```

Mỗi commit nên chạy test trước.

## 17. Sau phase này mới làm gì?

Khi phase này xong, bước tiếp theo mới là AI layer:

```text
LLM tool calling
  -> tool registry
  -> prompt cho tool selection
  -> structured output
  -> guardrails
```

Lúc đó LLM có thể trả lời:

```text
"Category nào có revenue cao nhất nhưng cancel rate cũng cao?"
```

Bằng cách gọi:

```text
revenue_by_category
category_cancellation_summary
```

Sau đó mới cân nhắc:

- LangChain.
- LangGraph.
- Redis rate limit.
- SQLite/PostgreSQL metadata.
- LLM usage tracking.

## 18. Definition of Done

Phase này hoàn thành khi:

- Có `data_cleaner.py`.
- Có `feature_engineering.py`.
- Có `ecommerce_tools.py`.
- Có tests cho cả 3 phần.
- `pytest -q` pass.
- Có endpoint `GET /ecommerce/overview/{dataset_id}`.
- Streamlit hiển thị ecommerce insights cơ bản.
- Notebook vẫn chỉ là exploration, không còn là nơi duy nhất chứa logic.

Khi đạt được các điều trên, project đã có nền rất tốt để bước sang AI tool calling một cách chuyên nghiệp.
