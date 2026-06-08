# Sau notebook Amazon Sales EDA: rút ra gì và làm gì tiếp theo?

Tài liệu này tóm tắt những điều quan trọng rút ra từ notebook:

```text
notebooks/01_amazon_sales_eda.ipynb
```

Mục tiêu không phải bao quát toàn bộ project, mà là trả lời câu hỏi thực tế:

```text
Sau khi làm xong notebook EDA, bước tiếp theo nên làm gì để biến insight thành nền móng code thật?
```

## 1. Notebook đã chứng minh điều gì?

Notebook cho thấy `Amazon Sale Report.csv` là một dataset đủ tốt để làm nền cho ecommerce-specific AI Data Analyst Agent.

Dataset có:

- Hơn 128k dòng.
- Hơn 120k order unique.
- Dữ liệu thời gian.
- Trạng thái đơn hàng.
- Category, SKU, ASIN, size.
- Quantity và amount.
- City/state/country.
- Fulfilment mode.
- Courier status.
- B2B flag.
- Promotion information.

Điều này có nghĩa là dataset không chỉ dùng được cho EDA cơ bản, mà còn đủ ngữ cảnh để xây các tool phân tích ecommerce thật sự:

- revenue analysis.
- cancellation analysis.
- category/product analysis.
- location analysis.
- fulfilment/courier analysis.
- promotion analysis.
- B2B vs non-B2B analysis.

## 2. Những phát hiện chính từ notebook

### 2.1 Dataset đang ở cấp line-item, không phải cấp order

`Order ID` bị lặp nhiều lần. Đây không nhất thiết là lỗi.

Ý nghĩa:

```text
Một order có thể có nhiều dòng sản phẩm/SKU.
```

Do đó, khi phân tích cần phân biệt rõ:

- row count: số dòng trong file.
- unique order count: số đơn hàng thật.
- SKU/product line count: số dòng sản phẩm.

Không nên drop duplicate theo `Order ID`.

Chiến lược code:

- Các tool overview phải trả cả `rows` và `unique_orders`.
- Khi tính `orders`, nên dùng `order_id.nunique()`.
- Khi tính `qty` hoặc `revenue`, có thể sum theo line-item.
- Nếu cần phân tích cấp order, phải aggregate trước theo `order_id`.

### 2.2 Một số cột cần cleaning trước khi phân tích

Các vấn đề phát hiện:

- `Sales Channel ` có khoảng trắng ở tên cột.
- `ship-service-level` dùng dấu `-`.
- `Unnamed: 22` không có ý nghĩa rõ.
- `index` là cột thừa từ file gốc.
- `Date` đang là object, cần parse datetime.
- City/state có thể khác nhau do viết hoa/thường.

Chiến lược code:

- Tạo `clean_column_names`.
- Drop `index` và `unnamed_22`.
- Parse `date` bằng format rõ ràng.
- Chuẩn hóa location text.
- Chuẩn hóa category text.

### 2.3 Missing values có ý nghĩa nghiệp vụ, không chỉ là lỗi

Notebook cho thấy:

- `fulfilled_by` missing rất nhiều.
- `promotion_ids` missing nhiều.
- `Amount` và `currency` missing 7,795 dòng.
- Shipping fields missing rất ít, khoảng 33 dòng.

Cách hiểu:

- `promotion_ids` missing có thể nghĩa là đơn không có promotion.
- `fulfilled_by` missing có thể liên quan tới fulfillment type.
- `Amount` missing là vấn đề quan trọng vì ảnh hưởng revenue.
- Nhiều `amount` missing tập trung ở cancelled orders.

Chiến lược code:

- Không fill bừa `amount`.
- Tạo data quality warning cho `amount` missing.
- Tạo `has_promotion = promotion_ids.notna()`.
- Khi báo revenue, nên nói rõ revenue được tính trên các dòng có amount.
- Giữ shipping missing để report, không cần drop toàn bộ rows ngay.

### 2.4 Revenue analysis cần đi kèm cảnh báo

Tổng revenue trong notebook được tính từ `amount`.

Nhưng vì có missing `amount`, nên revenue không nên được trình bày như "doanh thu tuyệt đối hoàn chỉnh" nếu không có cảnh báo.

Cách diễn giải đúng:

```text
Revenue được tính từ cột amount trong các dòng có dữ liệu amount.
Một số dòng, chủ yếu cancelled orders, không có amount nên không đóng góp vào tổng revenue.
```

Chiến lược code:

- Tool `get_sales_overview` nên trả:
  - `total_revenue`
  - `missing_amount_rows`
  - `missing_amount_percent`
  - `revenue_note`

### 2.5 Cancellation là chủ đề phân tích bắt buộc

`Cancelled` là trạng thái lớn thứ ba và chiếm khoảng 14% line-item.

Điều này quan trọng vì:

- ảnh hưởng revenue.
- ảnh hưởng operations.
- liên quan tới fulfilment/courier.
- liên quan tới promotion/missing amount.

Chiến lược code:

- Tạo feature `is_cancelled`.
- Tạo tool `cancellation_summary`.
- Tạo tool `category_cancellation_summary`.
- Tạo tool `state_cancellation_summary`.
- Tạo chart cancel rate theo category/fulfilment/location.

### 2.6 Category là trục phân tích quan trọng nhất

Category có ít nhóm và có ý nghĩa business rõ.

Các category chính:

- Set.
- Kurta.
- Western Dress.
- Top.

Chiến lược code:

- Tạo tool `revenue_by_category`.
- Tạo tool `category_performance_summary`.
- Output nên có:
  - revenue.
  - revenue share.
  - qty.
  - unique orders.
  - cancel rate.
  - avg amount.

### 2.7 Location analysis cần chuẩn hóa trước

Notebook phát hiện city/state có thể bị tách nhóm nếu không chuẩn hóa viết hoa/thường.

Ví dụ:

```text
HYDERABAD
Hyderabad
```

Chiến lược code:

- Chuẩn hóa `ship_city`, `ship_state`, `ship_country` về uppercase.
- Strip khoảng trắng.
- Tool location phải chạy sau cleaning.

Các tool nên có:

- `top_states_by_revenue`.
- `top_cities_by_revenue`.
- `state_cancellation_summary`.

### 2.8 Fulfilment có tín hiệu phân tích tốt

Notebook cho thấy Merchant fulfilment có cancel rate cao hơn Amazon fulfilment trong dữ liệu hiện tại.

Không nên vội kết luận nguyên nhân, nhưng đây là insight tốt để đưa vào report.

Chiến lược code:

- Tạo tool `fulfilment_summary`.
- Output gồm:
  - revenue.
  - orders.
  - qty.
  - cancel rate.
  - avg amount.

### 2.9 Promotion analysis cần diễn giải cẩn trọng

`has_promotion = False` có cancel rate cao bất thường.

Nhưng không nên kết luận:

```text
Promotion làm giảm cancellation.
```

Vì có thể có confounding:

- cancelled orders thường missing promotion ids.
- promotion ids có thể chỉ được ghi nhận cho một số loại đơn.
- missing promotion không chắc nghĩa là không có promotion thật.

Chiến lược code:

- Vẫn tạo tool `promotion_summary`.
- Nhưng output nên kèm `warning`.
- LLM sau này phải diễn giải theo hướng association, không causal.

### 2.10 B2B là segment nhỏ

B2B có số dòng rất nhỏ so với non-B2B.

Chiến lược code:

- Vẫn giữ `b2b_summary`.
- Không dùng B2B làm insight chính.
- Khi báo kết quả, thêm caveat về sample size.

## 3. Những chart nên giữ làm chart MVP

Notebook đã có nhiều chart hơn, nhưng khi đưa vào app không nên đưa tất cả ngay.

Nên chọn chart MVP:

### Chart 1 - Revenue by day/month

Mục tiêu:

- Cho user thấy trend doanh thu.
- Rất hợp với câu hỏi "doanh thu thay đổi như thế nào?".

Tool liên quan:

```text
revenue_by_day
revenue_by_month
```

### Chart 2 - Revenue by category

Mục tiêu:

- Cho thấy nhóm sản phẩm đóng góp doanh thu chính.

Tool liên quan:

```text
revenue_by_category
category_performance_summary
```

### Chart 3 - Category revenue vs cancel rate

Mục tiêu:

- Không chỉ nhìn doanh thu, mà nhìn cả rủi ro hủy đơn.

Tool liên quan:

```text
category_cancellation_summary
```

### Chart 4 - Top states/cities by revenue

Mục tiêu:

- Cho thấy khu vực bán tốt.

Tool liên quan:

```text
top_states_by_revenue
top_cities_by_revenue
```

### Chart 5 - Order status distribution

Mục tiêu:

- Cho thấy shipped/cancelled/pending/returned.

Tool liên quan:

```text
status_summary
cancellation_summary
```

### Chart 6 - Fulfilment cancel rate

Mục tiêu:

- Cho thấy khác biệt vận hành giữa Amazon và Merchant.

Tool liên quan:

```text
fulfilment_summary
```

## 4. Chiến lược làm tiếp theo sau notebook

Sau notebook, không nên viết LLM ngay. Bước đúng là chuyển logic đã ổn thành code production-like.

Thứ tự nên làm:

```text
1. Data cleaner
2. Feature engineering
3. Ecommerce tools
4. Tests
5. API tích hợp nhẹ
6. Streamlit hiển thị nhẹ
7. Sau đó mới LLM/tool calling
```

## 5. Step 1 - Tạo data cleaner

### File cần tạo

```text
app/services/data_cleaner.py
```

### Hàm nên có

```python
def clean_column_name(col: str) -> str:
    ...

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    ...

def clean_amazon_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    ...
```

### Logic cần chuyển từ notebook

- Strip/lowercase tên cột.
- Replace space/hyphen bằng underscore.
- Remove colon trong `unnamed:_22`.
- Drop `index`.
- Drop `unnamed_22`.
- Parse `date` với format `%m-%d-%y`.
- Strip text columns.
- Uppercase city/state/country.
- Title case category.

### Output kỳ vọng

Input raw:

```text
Order ID
Sales Channel 
ship-service-level
Unnamed: 22
```

Output clean:

```text
order_id
sales_channel
ship_service_level
```

Và bỏ:

```text
index
unnamed_22
```

## 6. Step 2 - Tạo feature engineering

### File cần tạo

```text
app/services/feature_engineering.py
```

### Hàm nên có

```python
def add_amazon_sales_features(df: pd.DataFrame) -> pd.DataFrame:
    ...
```

### Feature cần tạo

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

### Lưu ý quan trọng

`revenue = amount` là alias phục vụ phân tích. Không có nghĩa là amount luôn là revenue hoàn chỉnh tuyệt đối.

Nên giữ warning:

```text
Revenue is calculated from available amount values.
Rows with missing amount are excluded from revenue sums.
```

## 7. Step 3 - Tạo ecommerce tools

### File cần tạo

```text
app/tools/ecommerce_tools.py
```

### Tool nên làm trước

Không cần làm hết ngay. Nên làm 6 tool đầu tiên:

```text
get_sales_overview
get_data_quality_summary
revenue_by_month
revenue_by_category
top_states_by_revenue
cancellation_summary
```

### Tool 1 - `get_sales_overview`

Output nên có:

```json
{
  "rows": 128975,
  "unique_orders": 120378,
  "date_min": "2022-03-31",
  "date_max": "2022-06-29",
  "total_revenue": 78592678.3,
  "total_qty": 116649,
  "cancel_rate": 0.1421,
  "missing_amount_rows": 7795,
  "notes": ["Revenue is calculated from available amount values."]
}
```

### Tool 2 - `get_data_quality_summary`

Output nên có:

```text
missing by column
duplicate rows
duplicate order id count
missing amount rows
missing shipping rows
```

### Tool 3 - `revenue_by_month`

Output:

```text
order_month
revenue
orders
qty
cancel_rate
```

### Tool 4 - `revenue_by_category`

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

Output:

```text
ship_state
revenue
orders
qty
cancel_rate
```

### Tool 6 - `cancellation_summary`

Output:

```text
overall_cancel_rate
cancelled_rows
cancelled_orders
cancel_rate_by_status
cancel_rate_by_category
cancel_rate_by_fulfilment
```

## 8. Step 4 - Viết tests

### File cần tạo

```text
tests/test_data_cleaner.py
tests/test_feature_engineering.py
tests/test_ecommerce_tools.py
```

### Test data cleaner

Cần test:

- `"Order ID"` thành `"order_id"`.
- `"Sales Channel "` thành `"sales_channel"`.
- `"ship-service-level"` thành `"ship_service_level"`.
- `"Unnamed: 22"` thành `"unnamed_22"` rồi bị drop.
- `date` parse được.
- city/state được uppercase.

### Test feature engineering

Cần test:

- `is_cancelled` đúng với status `Cancelled`.
- `is_shipped` đúng với status chứa `Shipped`.
- `is_delivered` đúng với status chứa `Delivered`.
- `has_promotion` đúng với promotion not null.
- `amount_per_item` không bị chia cho 0.

### Test ecommerce tools

Cần test:

- `get_sales_overview` tính đúng total revenue.
- `revenue_by_category` groupby đúng.
- `top_states_by_revenue` sort đúng.
- `cancellation_summary` tính cancel rate đúng.
- Tool trả JSON-serializable output.

## 9. Step 5 - Tích hợp nhẹ vào backend

Sau khi cleaner/features/tools có test, mới tích hợp vào backend.

Không cần sửa quá nhiều API ngay. Có 2 lựa chọn.

### Lựa chọn A - Tích hợp vào `/summary`

Khi user upload Amazon Sales dataset:

```text
load dataframe
  -> clean
  -> add features
  -> generic profile
  -> ecommerce overview nếu đủ cột
```

Ưu điểm:

- Frontend ít phải đổi.
- Summary giàu thông tin hơn.

Nhược điểm:

- `/summary` có thể phình to.

### Lựa chọn B - Thêm endpoint riêng

Bắt đầu với:

```text
GET /ecommerce/overview/{dataset_id}
```

Sau đó thêm:

```text
GET /ecommerce/revenue-by-month/{dataset_id}
GET /ecommerce/revenue-by-category/{dataset_id}
GET /ecommerce/cancellation/{dataset_id}
```

Ưu điểm:

- Rõ boundary.
- Dễ test.
- Hợp với domain-specific tools.

Khuyến nghị:

```text
Chọn B trước.
```

Vì project đang học kiến trúc AI Engineering, tách endpoint riêng giúp nhìn rõ tool/domain boundary.

## 10. Step 6 - Tích hợp nhẹ vào Streamlit

Không cần làm dashboard lớn ngay.

Chỉ cần thêm một khu vực:

```text
Ecommerce Insights
```

Hiển thị:

- Total revenue.
- Unique orders.
- Cancel rate.
- Missing amount rows.
- Revenue by category table.
- Revenue by month chart.
- Top states chart.

Sau này LLM sẽ dùng chính các tools này để trả lời câu hỏi.

## 11. Những việc chưa nên làm ngay

Chưa nên làm ngay:

- Fine-tuning.
- LangGraph.
- Multi-agent.
- RAG.
- Forecasting phức tạp.
- Anomaly detection nâng cao.
- PDF report.
- Authentication.

Lý do:

```text
Hiện tại cần biến notebook thành deterministic reusable tools trước.
Nếu thêm AI quá sớm, agent sẽ thiếu nền tính toán đáng tin.
```

## 12. Mini roadmap 5 ngày sau notebook

### Ngày 1 - Data cleaner

- Tạo `app/services/data_cleaner.py`.
- Chuyển clean column/date/text logic từ notebook sang code.
- Viết test cho cleaner.

### Ngày 2 - Feature engineering

- Tạo `app/services/feature_engineering.py`.
- Thêm các feature ecommerce.
- Viết test cho features.

### Ngày 3 - Ecommerce tools phần 1

- Tạo `app/tools/ecommerce_tools.py`.
- Implement:
  - `get_sales_overview`.
  - `get_data_quality_summary`.
  - `revenue_by_month`.

### Ngày 4 - Ecommerce tools phần 2

- Implement:
  - `revenue_by_category`.
  - `top_states_by_revenue`.
  - `cancellation_summary`.
- Viết test cho tools.

### Ngày 5 - Backend integration nhẹ

- Thêm endpoint `GET /ecommerce/overview/{dataset_id}`.
- Nếu còn thời gian, thêm `GET /ecommerce/revenue-by-category/{dataset_id}`.
- Cập nhật Streamlit hiển thị ecommerce overview đơn giản.

## 13. Definition of Done cho bước sau notebook

Xem như hoàn thành giai đoạn sau notebook khi:

- Cleaning logic không còn nằm riêng trong notebook.
- Feature engineering không còn nằm riêng trong notebook.
- Có ít nhất 6 ecommerce tools chạy được.
- Có tests cho cleaner/features/tools.
- Backend có ít nhất 1 ecommerce endpoint.
- Streamlit hiển thị được ít nhất một phần ecommerce insight.
- Notebook trở thành tài liệu exploration, không phải nơi duy nhất chứa logic.

## 14. Kết luận

Notebook đã làm đúng vai trò của nó: khám phá dữ liệu, phát hiện vấn đề, thử feature, thử chart và xác định các phân tích đáng xây thành tool.

Bước tiếp theo không phải là thêm LLM ngay.

Bước tiếp theo là:

```text
Notebook insight
  -> data cleaner
  -> feature engineering
  -> ecommerce tools
  -> tests
  -> API endpoint
  -> Streamlit insight
```

Khi các tools này ổn, LLM/tool calling mới có nền vững để trở thành AI Data Analyst Agent thật.
