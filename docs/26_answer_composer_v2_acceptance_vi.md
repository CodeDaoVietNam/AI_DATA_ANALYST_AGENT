# Nghiệm thu Phase U6 - Answer Composer v2

## 1. Mục tiêu đã xử lý

Phase U6 tập trung khắc phục vấn đề: **đầu ra câu trả lời của AI Copilot chưa đẹp, chưa thân thiện và còn giống log kỹ thuật**.

Trước U6:

- Backend trả `answer` là text tự do.
- Frontend phải tự đoán đâu là kết luận, evidence, why it matters.
- Deterministic fallback trả lời còn khô.
- LLM explanation nếu lỗi thì output không đủ “product-grade”.

Sau U6:

- Backend có structured `answer_card`.
- Fast mode không cần LLM vẫn trả được câu trả lời đẹp.
- Balanced/deep mode có thể để LLM polish wording bằng JSON structured.
- Frontend render theo card thay vì cố đoán text.
- Error tool cũng có card rõ ràng.
- Add to report dùng answer card đẹp hơn.

## 2. Backend đã implement

### 2.1 Service mới

Đã thêm:

```text
app/services/answer_composer.py
```

Các function chính:

- `compose_answer_card`
- `answer_card_to_text`
- `merge_llm_answer_card`
- `compose_tool_error_card`

Vai trò:

- Tạo câu trả lời có cấu trúc từ deterministic tool result.
- Convert card sang legacy `answer` để không phá API cũ.
- Cho phép LLM polish wording nhưng giữ nguyên evidence deterministic.
- Tạo card lỗi khi tool fail.

### 2.2 Schema mới

Đã mở rộng:

```text
app/schemas/models.py
```

Thêm:

- `AnswerTakeaway`
- `AnswerEvidence`
- `AnswerCard`
- `AgentChatResponse.answer_card`

`QuickAction` cũng đã hỗ trợ thêm:

- `add_to_report`
- `explain_calculation`

### 2.3 Agent Orchestrator

Đã cập nhật:

```text
app/services/agent_orchestrator.py
```

Thay đổi chính:

- `_explain_result` tạo deterministic `answer_card` trước.
- `mode=fast` trả card ngay, không cần Ollama.
- `balanced/deep` yêu cầu LLM trả JSON structured.
- Nếu LLM lỗi, timeout, trả JSON sai hoặc rỗng thì fallback về deterministic card.
- Response có thêm:

```json
{
  "answer": "...",
  "answer_card": {
    "headline": "...",
    "summary": "...",
    "key_takeaways": [],
    "evidence": [],
    "why_it_matters": "...",
    "recommended_next_questions": [],
    "confidence": "high",
    "answer_source": "deterministic_composer",
    "data_warnings": [],
    "calculation_notes": []
  }
}
```

## 3. Frontend đã implement

### 3.1 TypeScript types

Đã cập nhật:

```text
web/src/types.ts
```

Thêm type:

- `AnswerCard`
- `AgentResponse.answer_card`

### 3.2 Ask Copilot renderer

Đã cập nhật:

```text
web/src/components/AskCopilot.tsx
```

Nếu response có `answer_card`, frontend render:

- Kết luận chính.
- Summary.
- Evidence metric cards.
- Key takeaways theo tone.
- Vì sao quan trọng.
- Nên hỏi tiếp.
- Nguồn tính toán và cảnh báo.

Nếu backend cũ chưa có `answer_card`, frontend vẫn fallback về renderer cũ.

### 3.3 Add to report

Đã cập nhật:

```text
web/src/App.tsx
```

Nếu có `answer_card`, report snippet dùng:

- Headline.
- Tool.
- Source.
- Summary.
- Evidence.
- Why it matters.
- Warnings.

## 4. UI/UX thay đổi cảm nhận được

Trước:

- Câu trả lời nhìn giống một đoạn text/log.
- Người dùng phải tự đọc tool details để hiểu số liệu.
- Output chưa có nhịp kể chuyện rõ.

Sau:

- Câu trả lời mở đầu bằng kết luận chính.
- Evidence hiển thị thành card, dễ scan.
- Có phần “Vì sao quan trọng”.
- Có câu hỏi tiếp theo để user tiếp tục phân tích.
- Có trust layer và calculation notes.
- Fallback không còn quá khô.

Nói ngắn gọn:

> Copilot giờ bắt đầu giống một data analyst assistant hơn, không chỉ là frontend bọc quanh tool JSON.

## 5. Về việc đồng nhất Tiếng Việt

Nên đồng nhất sang Tiếng Việt nếu target user chính là người Việt.

Hiện U6 đã ưu tiên Việt hóa trong vùng Ask AI:

- Label chính trong Answer Card.
- Quick actions.
- Error/cảnh báo.
- Calculation notes.

Tuy nhiên project vẫn còn nhiều page/section tiếng Anh:

- Upload Center.
- Data Overview.
- Smart Dashboard.
- Ecommerce Suite.
- Analytics Hub.
- Executive Report.
- Một số button/table label.

Khuyến nghị không nên sửa rải rác từng dòng nữa. Nên làm một sprint riêng:

```text
Phase U7 - Vietnamese Product Copy + i18n Foundation
```

Mục tiêu U7:

- Chuẩn hóa toàn bộ UI copy sang Tiếng Việt.
- Tách copy constants ra file riêng.
- Có thể chuẩn bị i18n nếu sau này cần English/Vietnamese toggle.
- Đồng nhất tone: chuyên nghiệp, dễ hiểu, không quá kỹ thuật.

## 6. Test đã chạy

### 6.1 Composer + agent tests

Command:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest tests/test_answer_composer.py tests/test_agent_orchestrator.py -q
```

Kết quả:

```text
13 passed
```

### 6.2 Full backend tests

Command:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest -q
```

Kết quả:

```text
124 passed
```

Warning còn lại:

- `requests` dependency warning từ môi trường Python.
- Không liên quan tới U6.

### 6.3 Frontend build

Command:

```bash
cd web && npm run build
```

Kết quả:

```text
built successfully
```

Warning còn lại:

- Plotly bundle lớn hơn 500KB.
- Đây là backlog performance/lazy-load, không phải lỗi U6.

## 7. Manual acceptance checklist

Chạy backend:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Chạy frontend:

```bash
cd web
npm run dev
```

Checklist:

- Upload Amazon Sales CSV.
- Vào Ask AI Copilot.
- Hỏi: `SKU nào có doanh thu cao nhất?`
- Kỳ vọng:
  - Có headline rõ.
  - Có evidence card.
  - Có why it matters.
  - Có next questions.
  - Có calculation notes.

- Hỏi: `Category nào cancel rate cao nhất?`
- Kỳ vọng:
  - Answer nêu risk.
  - Có cảnh báo nếu sample/missing.
  - Có next question về nguyên nhân/risk.

- Tắt Ollama hoặc dùng mode fast.
- Kỳ vọng:
  - Vẫn có answer card đẹp.
  - Không bị trống câu trả lời.

## 8. Giới hạn còn lại

U6 chưa giải quyết toàn bộ UX:

- Chưa Việt hóa toàn bộ UI ngoài Ask AI.
- Chưa có i18n architecture.
- Chưa có user preference cho giọng trả lời:
  - ngắn gọn.
  - executive.
  - beginner-friendly.
  - technical.
- Chưa có feedback button:
  - hữu ích.
  - sai số.
  - khó hiểu.
- Chưa lazy-load Plotly.
- Chưa có report composer chuyên nghiệp hoàn toàn.

## 9. Bước tiếp theo đề xuất

Nếu tiếp tục ngay, thứ tự hợp lý:

1. **Phase U7 - Vietnamese Product Copy + i18n Foundation**
   - Đồng nhất toàn UI sang Tiếng Việt.
   - Tách copy ra constants.
   - Chuẩn hóa tone.

2. **Phase U8 - Chat Feedback + Saved Conversations**
   - Lưu chat history.
   - Feedback helpful/not helpful.
   - Log câu hỏi lỗi.

3. **Phase U9 - Plotly Lazy Load + Frontend Performance**
   - Code split dashboard/charts.
   - Giảm initial JS bundle.

4. **Phase U10 - Report Composer v2**
   - Dùng answer cards/insight cards để tạo report đẹp hơn.

