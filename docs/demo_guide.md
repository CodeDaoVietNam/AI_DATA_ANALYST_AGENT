# Demo Guide - AI Data Analyst Agent

Mục tiêu của demo này là giúp reviewer thấy rõ project không chỉ là chatbot, mà là một hệ thống analytics agent có semantic layer, deterministic tools, dashboard và eval.

Thời lượng đề xuất: 5 phút.

## 1. Chuẩn bị

Terminal 1:

```bash
make backend
```

Terminal 2:

```bash
make frontend
```

Mở frontend:

```text
http://127.0.0.1:5173
```

Ollama là optional. Nếu muốn demo AI explanation tốt hơn:

```bash
ollama serve
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
```

Nếu Ollama không chạy, Copilot vẫn trả deterministic fallback.

## 2. Dataset demo khuyến nghị

Ưu tiên dùng một trong hai file:

```text
data/raw/Amazon Sale Report.csv
data/raw/sample_-_superstore.xls
```

Nếu không có raw dataset, dùng sample nhỏ:

```text
data/sample/ecommerce_sales.csv
```

## 3. Flow 5 phút

### Bước 1 - Upload dataset

Vào trang Upload, chọn file CSV/XLS/XLSX.

Nói với reviewer:

> Hệ thống không chỉ đọc file, mà còn lưu metadata, profile schema, detect domain và chuẩn bị dashboard contract từ backend.

### Bước 2 - Smart Dashboard

Mở Smart Dashboard.

Kiểm tra:

- domain detected
- KPI cards
- insight cards
- charts
- tables
- warnings
- semantic profile panel

Nói với reviewer:

> Dashboard được build từ backend response contract, frontend chỉ render. Điều này giúp logic analytics không bị nằm rải rác trong UI.

### Bước 3 - Semantic Mapping

Mở Semantic Mapping hoặc Data Dictionary panel.

Demo:

- revenue -> Sales/Amount
- date -> Order Date/Date
- category -> Category/Segment
- quantity -> Qty/Quantity

Nói với reviewer:

> Nếu auto-detection sai, user có thể override mapping. Đây là nền để hỗ trợ nhiều CSV khác nhau.

### Bước 4 - Custom Metric

Nếu dùng Superstore hoặc finance/retail data, tạo metric:

```text
name: margin
label: Margin
expression: profit / revenue
format: percent
aggregation: mean
```

Nói với reviewer:

> Metric Builder dùng expression engine có allowlist, không dùng eval trực tiếp.

### Bước 5 - Ask AI Copilot

Hỏi một câu theo dataset:

Ecommerce:

```text
SKU nào có doanh thu cao nhất?
Category nào có cancellation risk cao nhất?
```

Retail:

```text
Category nào sales cao nhưng profit thấp?
Margin theo segment như thế nào?
```

Marketing:

```text
Campaign nào response tốt nhất?
```

HR:

```text
Nhóm nhân viên nào attrition risk cao?
```

Generic:

```text
Cột nào thiếu dữ liệu nhiều nhất?
```

Chỉ vào các phần:

- answer card
- evidence
- why it matters
- recommended next question
- tool timeline
- selected tool
- latency/cache/fallback badge

Nói với reviewer:

> LLM không tự bịa số. Backend chọn tool, Pandas tính toán, Answer Composer trình bày kết quả theo format thân thiện.

### Bước 6 - Eval Suite

Chạy:

```bash
make eval
```

Mở:

```text
evals/reports/latest.md
```

Nói với reviewer:

> Eval đo domain detection, semantic mapping, intent parsing, tool selection, numeric correctness và latency. Đây là thứ phân biệt project AI engineering với demo cảm tính.

## 4. Checklist trước khi demo

- Backend chạy ở `127.0.0.1:8000`.
- Frontend chạy ở `127.0.0.1:5173`.
- Upload file thành công.
- Smart Dashboard có chart/table.
- Ask AI trả answer card hoặc deterministic fallback.
- `make test` pass.
- `make build-web` pass.
- `make eval` tạo report.

## 5. Demo script ngắn

> Đây là AI Data Analyst Agent. User có thể upload CSV/XLS/XLSX bất kỳ. Backend tự profile dataset, detect domain, map semantic roles và build dashboard contract. Với dataset có schema khác nhau, user có thể dùng data dictionary hoặc override mapping. Khi hỏi AI Copilot, hệ thống không để LLM tự tính toán; nó chọn deterministic tool, Pandas tính số liệu, rồi answer composer trình bày kết quả bằng kết luận, bằng chứng, ý nghĩa và câu hỏi tiếp theo. Project cũng có eval suite để đo chất lượng trên nhiều domain.

## 6. Screenshot cần chụp sau

Khi app đang chạy, nên chụp và lưu:

```text
docs/assets/dashboard.png
docs/assets/copilot.png
docs/assets/semantic-mapping.png
docs/assets/metric-builder.png
```

Các file SVG hiện tại trong `docs/assets` chỉ là preview placeholder nhẹ cho GitHub.
