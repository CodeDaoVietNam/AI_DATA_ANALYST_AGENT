# Phase B/C - Semantic Layer và Backend-Driven Dashboard Acceptance

## 1. Mục tiêu đã hoàn thành

Phase B/C mở rộng project từ Amazon/ecommerce analytics sang nền tảng phân tích nhiều loại dataset hơn.

Đã implement:

- Upload/read `.csv`, `.xls`, `.xlsx`.
- Semantic mapper chính thức hơn với role/domain detection.
- Semantic generic tools cho dataset ngoài Amazon.
- Backend endpoint `GET /semantic-profile/{dataset_id}`.
- Backend endpoint `GET /dashboard/{dataset_id}`.
- Dashboard contract thống nhất: KPI cards, insights, charts, tables, warnings.
- Frontend page mới: `Smart Dashboard`.
- AI Copilot có semantic profile và semantic tools trong routing/context.

## 2. File và API mới

Backend service mới:

- `app/services/data_loader.py`
- `app/services/dashboard_builder.py`

Service được mở rộng:

- `app/services/semantic_mapper.py`
- `app/tools/generic_analysis_tools.py`
- `app/services/agent_orchestrator.py`

API mới:

```text
GET /semantic-profile/{dataset_id}
GET /dashboard/{dataset_id}
```

Upload hiện hỗ trợ:

```text
.csv
.xls
.xlsx
```

Backend lưu dataframe đã parse thành CSV nội bộ trong `data/uploads`, nên storage vẫn đơn giản.

## 3. Semantic roles đã hỗ trợ

Các role chính:

- `revenue`
- `cost`
- `profit`
- `date`
- `category`
- `quantity`
- `city`
- `state`
- `country`
- `customer`
- `campaign`
- `employee`
- `department`
- `salary`
- `target`
- `conversion`

Mỗi role có:

- `role`
- `column`
- `confidence`
- `reason`

## 4. Domain detection

Domain hiện hỗ trợ:

- `ecommerce`
- `retail`
- `marketing`
- `hr`
- `finance`
- `generic`

Rule chính:

- Amazon Sales có `Order ID`, `SKU`, `ASIN`, `Fulfilment`, `Courier Status`, `Amount` -> `ecommerce`.
- Superstore-like có `Sales`, `Profit`, `Quantity`, `Segment/Category`, `State` -> `retail`.
- Marketing có `Response`, `Dt_Customer`, `NumWebPurchases`, campaign/customer fields -> `marketing`.
- HR có `Attrition`, `EmployeeNumber`, `Department`, `MonthlyIncome` -> `hr`.
- Nếu không đủ tín hiệu -> `generic`.

## 5. Dashboard contract

`GET /dashboard/{dataset_id}` trả:

```json
{
  "dataset_id": "...",
  "domain": "retail",
  "semantic_profile": {},
  "kpi_cards": [],
  "insight_cards": [],
  "charts": [],
  "tables": [],
  "warnings": []
}
```

Frontend chỉ render contract này trong page `Smart Dashboard`.

## 6. Domain dashboard behavior

### Ecommerce

- Revenue.
- Orders.
- Cancel rate.
- Quantity.
- Revenue by month.
- Revenue by category.
- Top states.

### Retail / Superstore

- Rows.
- Revenue.
- Profit.
- Quantity.
- Trend over time.
- Breakdown by category/state/customer segment khi detect được.

### Marketing

- Customers.
- Response rate.
- Income total nếu detect được.
- Response/conversion by campaign.
- Breakdown by country/campaign khi detect được.

### HR

- Employees.
- Attrition rate.
- Income total.
- Attrition by department.
- Breakdown by department/category khi detect được.

### Generic

- Rows.
- Columns.
- Duplicate rows.
- Missing values.
- Top categorical value counts.

## 7. AI Copilot integration

Agent context hiện có thêm:

- semantic profile
- domain
- roles
- semantic tools

Semantic tools:

- `semantic_overview`
- `semantic_kpis`
- `semantic_time_series`
- `semantic_breakdown`
- `semantic_target_summary`

Ví dụ route mới:

- “doanh thu theo category” -> `semantic_breakdown`
- “attrition theo department” -> `semantic_target_summary`
- “conversion theo campaign” -> `semantic_target_summary`
- “doanh thu theo tháng” -> `semantic_time_series`

## 8. Dataset nghiệm thu thực tế

Đã smoke test các file trong `data/raw`:

```text
Amazon Sale Report.csv       -> ecommerce
sample_-_superstore.xls      -> retail
marketing_data.csv           -> marketing
HR-Employee-Attrition.csv    -> hr
```

Kết quả smoke test:

```text
Amazon Sale Report.csv ecommerce 4 KPI 2 charts 2 tables
sample_-_superstore.xls retail 4 KPI 4 charts 4 tables
marketing_data.csv marketing 3 KPI 2 charts 3 tables
HR-Employee-Attrition.csv hr 3 KPI 2 charts 3 tables
```

## 9. Test đã chạy

Backend:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest -q
```

Kết quả:

```text
60 passed, 1 warning
```

Frontend:

```bash
cd web
npm run build
```

Kết quả:

```text
build passed
```

Warning còn lại:

- `RequestsDependencyWarning` từ môi trường Python hiện tại.
- Vite vẫn cảnh báo bundle lớn do Plotly.

## 10. Manual acceptance checklist

Chạy backend:

```bash
uvicorn app.main:app --reload
```

Chạy frontend:

```bash
cd web
npm run dev
```

Kiểm thử:

1. Upload `data/raw/Amazon Sale Report.csv`
   - `Smart Dashboard` domain là `ecommerce`.
   - KPI, chart, table render.

2. Upload `data/raw/sample_-_superstore.xls`
   - Upload Excel thành công.
   - `Smart Dashboard` domain là `retail`.
   - Có KPI revenue/profit/quantity.

3. Upload `data/raw/Marketing+Data/marketing_data.csv`
   - Domain là `marketing`.
   - Có response rate và campaign/response sections.

4. Upload `data/raw/HR-Employee-Attrition.csv`
   - Domain là `hr`.
   - Có attrition rate và department table.

5. Ask AI:
   - “doanh thu theo category”
   - “attrition theo department”
   - “conversion theo campaign”
   - Kỳ vọng agent gọi semantic tools tương ứng.

## 11. Giới hạn còn lại

Phase này chưa làm:

- Chưa cache dashboard result.
- Chưa có database metadata.
- Chưa có dashboard editor.
- Chưa có natural-language dashboard generation.
- Chưa có LangGraph multi-step reasoning.
- Domain detection vẫn heuristic, chưa dùng embedding/LLM classifier.
- Semantic mapper chưa xử lý mọi biến thể tên cột ngoài đời thật.

## 12. Bước tiếp theo

Đề xuất thứ tự:

1. Thêm `/dashboard/{dataset_id}?domain_override=...` để user override domain nếu detect sai.
2. Tách frontend dashboard page thành component riêng để `App.tsx` nhẹ hơn.
3. Thêm semantic role debugger trong UI upload.
4. Dùng semantic profile sâu hơn cho chart builder.
5. Sau đó mới xây LangGraph/multi-step analyst.
