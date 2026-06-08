# Phase A - AI Copilot Stability Acceptance

## 1. Mục tiêu đã hoàn thành

Phase A tập trung làm Ask AI Copilot ổn định hơn trước khi mở rộng sang semantic layer và auto dashboard đa domain.

Các mục đã implement:

- Chat pending state ở frontend.
- Error bubble trong chat nếu backend/API lỗi.
- Execution timeline trong response backend.
- Result summary trong response backend.
- Explanation source: `llm`, `deterministic_fallback`, `tool_error`.
- Quick actions sau mỗi câu trả lời.
- Tool result đầy đủ vẫn trả về, nhưng context gửi LLM được rút gọn.
- LLM explanation có timeout ngắn hơn.
- Nếu LLM lỗi/chậm, backend fallback sang deterministic answer.
- Retry/fallback tool cơ bản khi tool selection hoặc tool execution lỗi.
- Semantic mapper v1 để chuẩn bị Phase B.

## 2. API response mới của `POST /agent/chat`

Các field cũ vẫn giữ:

- `answer`
- `tool_call`
- `data`
- `chart`
- `warnings`

Các field mới:

```json
{
  "execution_timeline": [
    {
      "step": "received_question",
      "status": "ok",
      "detail": "Question received by agent.",
      "elapsed_ms": 0.01,
      "metadata": {}
    }
  ],
  "result_summary": {
    "row_count": 10,
    "top_item": {},
    "primary_metric": "revenue",
    "primary_metric_value": 12345,
    "has_chart": false,
    "result_type": "list"
  },
  "explanation_source": "llm",
  "quick_actions": [
    {
      "action": "export_result",
      "label": "Export result",
      "payload": {
        "format": "json"
      }
    }
  ]
}
```

## 3. Luồng Copilot mới

Luồng chính:

```text
User question
  -> rule-based router hoặc LLM router
  -> selected tool
  -> execute deterministic Pandas tool
  -> build full tool result
  -> build compact explanation context
  -> ask LLM for flexible explanation
  -> if LLM fails, use deterministic fallback answer
  -> return answer + timeline + result summary + quick actions
```

Fallback:

```text
Invalid tool selection
  -> fallback to safe overview tool

Tool execution error
  -> retry one fallback tool

LLM explanation error/timeout
  -> deterministic fallback answer
```

## 4. Frontend Ask AI thay đổi

Ask AI hiện có:

- Bubble pending ngay sau khi bấm Send.
- Trạng thái message:
  - `RUNNING TOOL`
  - `COGNITIVE AGENT`
  - `AGENT ERROR`
- Metadata nhỏ sau câu trả lời:
  - Tool
  - Explanation source
  - Row count
  - Primary metric
- Warning hiển thị ngay trong chat.
- Tool execution details dạng collapsible.
- Execution timeline dạng collapsible.
- Quick actions:
  - View chart
  - Export result
  - Ask follow-up

## 5. Semantic layer v1

Đã thêm nền móng:

```text
app/services/semantic_mapper.py
```

Các semantic roles ban đầu:

- `revenue`
- `date`
- `category`
- `quantity`
- `city`
- `state`
- `country`
- `customer`
- `campaign`
- `employee`
- `target`

Output chính:

- `DatasetSemanticProfile`
- `SemanticColumnMatch`
- `domain`
- `roles`
- `confidence`
- `warnings`

Phase A chưa bắt generic tools phụ thuộc semantic profile. Việc đó dành cho Phase B.

## 6. Test đã chạy

Backend:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest -q
```

Kết quả:

```text
49 passed, 1 warning
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

- Vite báo bundle lớn do Plotly. Đây là warning đã biết, chưa xử lý trong Phase A.
- Python có `RequestsDependencyWarning` từ môi trường hiện tại, chưa ảnh hưởng test.

## 7. Manual acceptance checklist

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

- Upload `Amazon Sale Report.csv`.
- Vào Ask AI Copilot.
- Hỏi: `SKU nào có doanh thu cao nhất?`
- Kỳ vọng:
  - Pending bubble xuất hiện ngay.
  - Response có answer.
  - Tool là `top_skus_by_revenue`.
  - Có result summary.
  - Có quick action export.
- Hỏi: `Category nào có cancel rate cao nhất?`
- Kỳ vọng:
  - Tool là `category_cancellation_summary`.
  - Có warning nếu liên quan missing amount.
- Hỏi: `Vẽ biểu đồ doanh thu theo category`
- Kỳ vọng:
  - Response có chart.
  - Quick action có View chart.
- Tắt Ollama hoặc đổi model sai.
- Kỳ vọng:
  - Backend vẫn trả deterministic answer nếu tool chạy được.
  - Warning nói rõ LLM explanation fallback.

## 8. Dataset hiện tại và dữ liệu cần bổ sung

Dataset nguồn hiện tại còn ít:

- `data/raw/Amazon Sale Report.csv`
- `data/sample/ecommerce_sales.csv`

Các file trong `data/uploads` là bản upload/runtime, không nên xem là bộ dữ liệu chuẩn để phát triển lâu dài.

Nên bổ sung cho Phase B/C:

1. Superstore retail dataset
   - Mục tiêu: test retail schema khác Amazon.
   - Cột kỳ vọng: `Sales`, `Quantity`, `Profit`, `Segment`, `State`, `Category`.

2. Marketing campaign dataset
   - Mục tiêu: test campaign/customer/response domain.
   - Cột kỳ vọng: campaign, customer, channel, response/conversion.

3. HR attrition dataset
   - Mục tiêu: test employee/attrition/department/job role domain.
   - Cột kỳ vọng: employee, attrition, department, job role, salary/income.

## 9. Giới hạn còn lại

Phase A chưa làm:

- Chưa chuyển generic tools sang dùng semantic profile.
- Chưa có endpoint `GET /dashboard/{dataset_id}`.
- Chưa có domain dashboard cho finance/marketing/HR.
- Chưa có persistent chat history.
- Chưa có streaming response.
- Chưa có database metadata.
- Chưa có Redis/rate limit.
- Chưa có LangGraph.

## 10. Bước tiếp theo

Thứ tự đề xuất:

1. Phase B: tích hợp semantic profile vào generic tools.
2. Thêm endpoint `GET /semantic-profile/{dataset_id}` để debug mapping.
3. Phase C: tạo backend-driven dashboard contract.
4. Di chuyển dần logic auto chart/dashboard khỏi frontend về backend.
5. Sau đó mới cân nhắc LangGraph nếu cần multi-step analysis.
