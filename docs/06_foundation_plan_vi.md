# Kế hoạch nền móng ban đầu cho AI Data Analyst Agent

## 1. Mục tiêu của giai đoạn này

Giai đoạn này chưa cần làm toàn bộ AI agent, chưa cần LangGraph ngay, cũng chưa cần fine-tune. Mục tiêu là xây nền thật chắc để sau này LLM có thứ đáng tin cậy để gọi.

Nói ngắn gọn:

```text
Hiểu dữ liệu thật
  -> làm sạch dữ liệu
  -> tạo feature hữu ích
  -> làm EDA notebook
  -> rút ra các logic phân tích lặp lại
  -> biến logic đó thành tool trong codebase
```

Đây là giai đoạn biến project từ starter đơn giản thành một nền tảng data analysis nghiêm túc.

## 2. Phạm vi chỉ làm trước mắt

Chỉ tập trung vào bộ dữ liệu:

```text
data/raw/Amazon Sale Report.csv
```

Không cần làm ngay:

- Fine-tuning.
- RAG.
- LangGraph workflow đầy đủ.
- Multi-file analysis.
- Authentication.
- Production deployment.
- Dashboard quá phức tạp.

Cần làm trước:

- Notebook EDA cho Amazon Sales data.
- Data cleaning pipeline cơ bản.
- Feature engineering cơ bản.
- Một số analysis tools dùng được lại trong backend.
- Test đơn giản cho cleaning và feature engineering.
- Cập nhật tài liệu để biết cách chạy.

## 3. Cách hiểu đúng về notebook trong project này

Notebook không phải sản phẩm cuối. Notebook là nơi khám phá dữ liệu và thử nghiệm phân tích.

Vai trò của notebook:

- Đọc dữ liệu thô.
- Hiểu ý nghĩa từng cột.
- Kiểm tra missing values.
- Kiểm tra duplicates.
- Kiểm tra kiểu dữ liệu.
- Thử parse ngày tháng.
- Thử tạo các feature mới.
- Thử groupby, chart, insight.
- Ghi lại các câu hỏi phân tích hay.

Sau khi logic đã rõ, không để logic quan trọng nằm mãi trong notebook. Phải đưa nó vào code:

```text
notebook thử nghiệm
  -> app/services/data_cleaner.py
  -> app/services/feature_engineering.py
  -> app/tools/ecommerce_tools.py
```

Đây là điểm khác biệt giữa một notebook data science và một AI Engineering product.

## 4. Bức tranh tổng thể sau giai đoạn nền móng

Sau giai đoạn này, project nên có cấu trúc thêm như sau:

```text
notebooks/
  01_amazon_sales_eda.ipynb

app/services/
  data_cleaner.py
  feature_engineering.py
  schema_detector.py

app/tools/
  generic_analysis_tools.py
  ecommerce_tools.py

tests/
  test_data_cleaner.py
  test_feature_engineering.py
  test_ecommerce_tools.py
```

Không nhất thiết phải hoàn thành tất cả trong một lần, nhưng đây là hướng đi hợp lý.

## 5. Phase 1 - Khám phá dữ liệu Amazon Sales

### Mục tiêu

Hiểu dataset thật sự có gì, cột nào dùng được, cột nào bẩn, cột nào cần xử lý.

### File cần tạo

```text
notebooks/01_amazon_sales_eda.ipynb
```

### Việc cần làm trong notebook

1. Load dataset:

```python
import pandas as pd

path = "../data/raw/Amazon Sale Report.csv"
df = pd.read_csv(path, low_memory=False)
```

2. Kiểm tra kích thước:

```python
df.shape
df.head()
df.tail()
```

3. Kiểm tra cột:

```python
df.columns
df.dtypes
df.info()
```

4. Kiểm tra missing values:

```python
missing = df.isna().sum().sort_values(ascending=False)
missing_percent = (df.isna().mean() * 100).round(2).sort_values(ascending=False)
```

5. Kiểm tra duplicates:

```python
df.duplicated().sum()
df["Order ID"].duplicated().sum()
```

6. Kiểm tra các cột quan trọng:

```text
Date
Status
Fulfilment
Sales Channel
Category
Size
Qty
Amount
ship-city
ship-state
B2B
promotion-ids
fulfilled-by
```

7. Ghi lại nhận xét:

- Cột nào có missing nhiều?
- Cột nào là ID?
- Cột nào là categorical?
- Cột nào là numeric?
- Cột nào cần parse datetime?
- Cột nào nên bỏ?
- Cột nào có thể tạo feature mới?

### Kết quả mong muốn

Cuối notebook phải có một section:

```text
EDA Notes
```

Trong đó ghi rõ:

- Dataset này nói về điều gì.
- Các cột quan trọng.
- Các vấn đề data quality.
- Các feature nên tạo.
- Các câu hỏi business có thể hỏi.

## 6. Phase 2 - Làm sạch dữ liệu

### Mục tiêu

Tạo một pipeline làm sạch dữ liệu có thể dùng lại trong backend, không chỉ trong notebook.

### File nên tạo

```text
app/services/data_cleaner.py
```

### Những việc cleaning cần làm

1. Chuẩn hóa tên cột.

Ví dụ:

```text
Order ID              -> order_id
Sales Channel         -> sales_channel
ship-service-level    -> ship_service_level
ship-city             -> ship_city
ship-state            -> ship_state
ship-postal-code      -> ship_postal_code
promotion-ids         -> promotion_ids
Unnamed: 22           -> unnamed_22
```

2. Bỏ khoảng trắng dư trong tên cột.

Dataset hiện có cột:

```text
Sales Channel 
```

Cột này có khoảng trắng ở cuối, nên phải strip.

3. Parse cột ngày:

```text
Date -> date
```

Sau cleaning, `date` nên là datetime.

4. Bỏ cột không hữu ích.

Cân nhắc bỏ:

```text
index
unnamed_22
```

5. Chuẩn hóa text.

Ví dụ:

```text
ship_city
ship_state
category
status
fulfilment
```

Có thể strip khoảng trắng và chuẩn hóa viết hoa/thường.

6. Xử lý missing values.

Không nhất thiết fill toàn bộ. Quan trọng là tạo rule rõ:

- `amount` missing thì giữ missing để báo data quality.
- `currency` missing thì có thể fill bằng `"UNKNOWN"` hoặc giữ missing.
- `promotion_ids` missing nghĩa là không có promotion.
- `fulfilled_by` missing có thể nghĩa là Amazon fulfillment hoặc unknown, cần kiểm tra kỹ.
- shipping fields missing thì giữ missing và báo.

### Hàm đề xuất

```python
def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    ...

def clean_amazon_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    ...
```

### Output mong muốn

Sau cleaning, DataFrame nên có cột dễ dùng hơn:

```text
order_id
date
status
fulfilment
sales_channel
ship_service_level
style
sku
category
size
asin
courier_status
qty
currency
amount
ship_city
ship_state
ship_postal_code
ship_country
promotion_ids
b2b
fulfilled_by
```

## 7. Phase 3 - Feature engineering cơ bản

### Mục tiêu

Tạo các cột mới giúp phân tích business tốt hơn.

### File nên tạo

```text
app/services/feature_engineering.py
```

### Feature nên tạo trước

1. Feature thời gian:

```text
order_year
order_month
order_month_name
order_week
order_day
order_day_name
```

2. Feature trạng thái đơn hàng:

```text
is_cancelled
is_shipped
is_delivered
```

Gợi ý logic:

```text
is_cancelled = status chứa "cancelled"
is_shipped = status chứa "shipped"
is_delivered = status chứa "delivered"
```

3. Feature promotion:

```text
has_promotion
```

Gợi ý:

```text
has_promotion = promotion_ids không null
```

4. Feature doanh thu:

```text
revenue
```

Giai đoạn đầu có thể đặt:

```text
revenue = amount
```

5. Feature order value:

```text
amount_per_item
```

Gợi ý:

```text
amount_per_item = amount / qty
```

Cần tránh chia cho 0.

### Hàm đề xuất

```python
def add_amazon_sales_features(df: pd.DataFrame) -> pd.DataFrame:
    ...
```

### Output mong muốn

Sau feature engineering, dataset có thể trả lời các câu hỏi:

- Doanh thu theo tháng là bao nhiêu?
- Tỷ lệ đơn bị huỷ là bao nhiêu?
- Category nào bán tốt nhất?
- Thành phố nào có doanh thu cao nhất?
- B2B khác non-B2B như thế nào?
- Đơn có promotion có doanh thu khác đơn không có promotion không?

## 8. Phase 4 - EDA business questions

### Mục tiêu

Từ dataset đã clean và có feature, tạo các phân tích business thực tế.

### Trong notebook cần có các section

1. Overview:

```text
Số dòng
Số cột
Khoảng thời gian dữ liệu
Tổng revenue
Tổng quantity
Số order unique
```

2. Data quality:

```text
Missing values
Duplicate rows
Amount missing
Shipping fields missing
Status distribution
```

3. Sales trend:

```text
Revenue by date
Revenue by month
Quantity by month
```

4. Category analysis:

```text
Revenue by category
Quantity by category
Cancel rate by category
```

5. Location analysis:

```text
Revenue by state
Revenue by city
Orders by state
```

6. Fulfillment analysis:

```text
Revenue by fulfilment
Cancel rate by fulfilment
Courier status distribution
```

7. B2B analysis:

```text
Revenue: B2B vs non-B2B
Orders: B2B vs non-B2B
Average order value: B2B vs non-B2B
```

8. Promotion analysis:

```text
Revenue with promotion vs without promotion
Quantity with promotion vs without promotion
Cancel rate with promotion vs without promotion
```

### Kết quả mong muốn

Notebook nên kết thúc bằng:

```text
Key Insights
Recommended Agent Tools
Recommended Charts
Data Quality Warnings
```

Đây sẽ là nguyên liệu để viết code tools.

## 9. Phase 5 - Biến phân tích thành tools

### Mục tiêu

Không để phân tích chỉ nằm trong notebook. Ta cần biến chúng thành hàm có thể được backend hoặc LLM gọi.

### File nên tạo

```text
app/tools/ecommerce_tools.py
```

### Tools nên làm trước

1. Dataset overview:

```python
def get_sales_overview(df: pd.DataFrame) -> dict:
    ...
```

Trả về:

```text
rows
columns
date_min
date_max
total_revenue
total_qty
unique_orders
cancel_rate
```

2. Revenue by time:

```python
def revenue_by_month(df: pd.DataFrame) -> dict:
    ...
```

3. Revenue by category:

```python
def revenue_by_category(df: pd.DataFrame) -> dict:
    ...
```

4. Top locations:

```python
def top_states_by_revenue(df: pd.DataFrame, n: int = 10) -> dict:
    ...
```

5. Cancellation analysis:

```python
def cancellation_summary(df: pd.DataFrame) -> dict:
    ...
```

6. Promotion analysis:

```python
def promotion_summary(df: pd.DataFrame) -> dict:
    ...
```

### Nguyên tắc viết tools

- Tool không được phụ thuộc vào notebook.
- Tool phải nhận DataFrame và trả về dict/list JSON-serializable.
- Tool phải validate cột cần thiết.
- Nếu thiếu cột, trả lỗi rõ ràng.
- Không để LLM tự tính số.

## 10. Phase 6 - Kết nối nhẹ vào backend

### Mục tiêu

Expose một vài endpoint mới hoặc tích hợp vào `/summary` để frontend/app dùng được.

### Endpoint có thể thêm sau khi tools ổn

```text
GET /ecommerce/overview/{dataset_id}
GET /ecommerce/revenue-by-month/{dataset_id}
GET /ecommerce/revenue-by-category/{dataset_id}
GET /ecommerce/cancellation/{dataset_id}
GET /ecommerce/promotion/{dataset_id}
```

Không cần làm hết ngay. Có thể bắt đầu với:

```text
GET /ecommerce/overview/{dataset_id}
```

Sau đó mở rộng.

## 11. Phase 7 - Test nền móng

### Mục tiêu

Đảm bảo cleaning, feature engineering và tools không hỏng khi dữ liệu thay đổi nhẹ.

### File test nên tạo

```text
tests/test_data_cleaner.py
tests/test_feature_engineering.py
tests/test_ecommerce_tools.py
```

### Test tối thiểu

1. Test clean column names:

- Input có `"Order ID"`.
- Output có `"order_id"`.
- Input có `"Sales Channel "`.
- Output có `"sales_channel"`.

2. Test date parsing:

- `date` phải parse được thành datetime.

3. Test feature flags:

- Status `"Cancelled"` -> `is_cancelled = True`.
- `promotion_ids` not null -> `has_promotion = True`.

4. Test revenue overview:

- `total_revenue` tính đúng.
- `total_qty` tính đúng.
- `cancel_rate` tính đúng.

## 12. Thứ tự làm cụ thể trong tuần đầu

### Ngày 1 - Hiểu dữ liệu

- Tạo notebook `01_amazon_sales_eda.ipynb`.
- Load CSV.
- Xem shape, columns, dtypes.
- Kiểm tra missing values.
- Viết phần ghi chú đầu tiên về dataset.

### Ngày 2 - Cleaning thử trong notebook

- Chuẩn hóa column names.
- Parse date.
- Drop `index` và `Unnamed: 22` nếu xác nhận không hữu ích.
- Kiểm tra lại dtypes.
- Ghi lại cleaning rules.

### Ngày 3 - Feature engineering thử trong notebook

- Tạo `order_month`.
- Tạo `is_cancelled`.
- Tạo `is_shipped`.
- Tạo `has_promotion`.
- Tạo `revenue`.
- Tạo `amount_per_item`.

### Ngày 4 - EDA business

- Revenue by month.
- Revenue by category.
- Revenue by state/city.
- Cancel rate.
- B2B vs non-B2B.
- Promotion vs no promotion.

### Ngày 5 - Đưa logic vào code

- Tạo `app/services/data_cleaner.py`.
- Tạo `app/services/feature_engineering.py`.
- Tạo `app/tools/ecommerce_tools.py`.
- Copy logic đã ổn từ notebook vào function.

### Ngày 6 - Viết test

- Test column cleaning.
- Test feature engineering.
- Test ecommerce tools.

### Ngày 7 - Kết nối nhẹ vào app

- Tích hợp cleaning/feature engineering vào flow upload hoặc summary.
- Thêm một endpoint overview nếu cần.
- Cập nhật README hoặc docs.

## 13. Definition of Done cho giai đoạn nền móng

Giai đoạn này được xem là xong khi:

- Có notebook EDA cho Amazon Sales dataset.
- Có danh sách rõ các vấn đề data quality.
- Có cleaning pipeline trong code.
- Có feature engineering pipeline trong code.
- Có ít nhất 3 ecommerce analysis tools.
- Có test tối thiểu cho cleaning/features/tools.
- Backend có thể dùng được dữ liệu đã clean.
- Tài liệu ghi rõ cách chạy và ý nghĩa dữ liệu.

## 14. Sau giai đoạn này mới làm gì?

Sau khi nền này chắc, mới nên chuyển sang AI:

```text
Tool calling
  -> LLM chọn tool
  -> Pandas tool tính toán
  -> LLM giải thích kết quả
```

Sau đó mới nâng lên:

```text
LangChain
LangGraph
Ollama local mode
Chart generation từ câu hỏi
Executive report bằng LLM
```

Lý do: nếu tools và dữ liệu chưa chắc, thêm LLM sớm sẽ làm project trông có vẻ thông minh nhưng thực chất dễ sai số liệu.

## 15. Kết luận

Việc đầu tiên không phải là fine-tune, cũng không phải LangGraph ngay. Việc đầu tiên là biến dataset thật thành một nền phân tích đáng tin:

```text
Clean data
Feature engineering
EDA notebook
Reusable analysis tools
Tests
```

Khi nền này tốt, LLM mới có thể trở thành một agent hữu ích thay vì chỉ là chatbot trả lời chung chung.
