# Phase U6 - Answer Composer v2: Làm đầu ra AI Copilot đẹp, dễ hiểu và đáng tin hơn

## 1. Nhận xét thẳng về hiện trạng

Hiện tại AI Copilot đã có nền backend khá mạnh:

- Có semantic mapper.
- Có tool registry.
- Có deterministic Pandas tools.
- Có multi-step orchestrator.
- Có dashboard/insight engine.
- Có frontend chat shell, timeline, trust badge, table/mini chart preview.

Nhưng phần **đầu ra câu trả lời** vẫn chưa đủ đẹp và chưa đủ thân thiện với người dùng cuối.

Lý do chính không phải chỉ do CSS. Vấn đề nằm ở contract giữa backend và frontend:

- Backend đang trả `answer` là một chuỗi text tự do.
- Deterministic fallback trả lời còn giống log kỹ thuật.
- LLM explanation có prompt nhưng chưa bị ép trả về schema sản phẩm.
- Frontend đang cố suy luận từ `answer`, `tool_call`, `result_summary` để chia thành các phần như kết luận/evidence/why/next question.
- Khi backend output không có cấu trúc, frontend chỉ có thể “bọc lại” chứ không thể làm câu trả lời thật sự mượt.

Kết luận senior review:

> Backend analytics của project đang tốt hơn Answer UX. Muốn output đẹp thật sự, cần thiết kế lại “answer composer layer”, không chỉ chỉnh UI.

## 2. Mục tiêu của Phase U6

Mục tiêu là biến câu trả lời của AI Copilot từ dạng:

```text
Tool revenue_by_category đã chạy thành công. Kết quả nổi bật: Set đứng đầu...
```

thành dạng product-grade:

```text
Category Set đang là nhóm tạo doanh thu lớn nhất.

Bằng chứng:
- Revenue của Set đạt 392,041.
- Set đứng đầu trong breakdown theo category.
- Tuy nhiên cần kiểm tra thêm cancel rate nếu category này chiếm tỷ trọng lớn.

Vì sao quan trọng:
Set là nhóm ảnh hưởng mạnh nhất đến doanh thu tổng. Nếu margin hoặc cancel rate của nhóm này không tốt, tác động đến business sẽ rất lớn.

Nên hỏi tiếp:
Set có margin tốt không và cancel rate đến từ state nào?
```

Phase này cần đạt 5 mục tiêu:

1. Câu trả lời có cấu trúc rõ ràng.
2. Số liệu bằng chứng đọc được ngay.
3. Người dùng hiểu “vì sao insight này quan trọng”.
4. Có next question thật sự hữu ích.
5. UI render theo schema, không đoán text tự do.

## 3. Nguyên tắc thiết kế Answer UX

### 3.1 Tool result là nguồn sự thật

LLM không được tự tính số liệu. LLM chỉ diễn giải từ:

- `tool_result`
- `result_summary`
- `semantic_profile`
- `metric_definition`
- `warnings`
- `source columns`

Nếu LLM lỗi hoặc timeout, deterministic composer vẫn phải trả được câu trả lời đẹp.

### 3.2 Không show JSON làm trải nghiệm chính

JSON/tool details vẫn cần cho trust/debug, nhưng phải nằm trong collapsible section.

Màn hình chính cần hiển thị:

- Headline.
- Key takeaways.
- Evidence metrics.
- Result preview.
- Why it matters.
- Suggested next questions.
- Warnings.
- Source/calculation.

### 3.3 Trả lời theo cấp độ người dùng

Cùng một tool result nhưng cần diễn giải theo business language.

Ví dụ với `revenue_by_category`:

- Không nên chỉ nói “Category A revenue = X”.
- Nên nói “Category A là revenue driver chính”.
- Nếu có share/cancel rate/missing amount thì nêu caveat.

### 3.4 Fallback cũng phải đẹp

Không được để fallback trả lời kiểu:

```text
Tool `abc` đã chạy thành công.
```

Fallback nên dùng template có cấu trúc:

- Kết luận.
- Bằng chứng.
- Cảnh báo.
- Câu hỏi tiếp.

## 4. Response contract mới

### 4.1 Thêm `answer_card` vào `AgentChatResponse`

Giữ `answer` cũ để backward compatible, nhưng thêm field mới:

```json
{
  "answer": "Legacy text answer",
  "answer_card": {
    "headline": "Category Set đang tạo doanh thu cao nhất.",
    "summary": "Set là nhóm dẫn đầu về revenue trong breakdown theo category.",
    "key_takeaways": [
      {
        "label": "Revenue leader",
        "text": "Set đứng đầu về revenue.",
        "tone": "positive"
      },
      {
        "label": "Data caveat",
        "text": "Một số dòng amount bị thiếu nên cần đọc total revenue cùng warning.",
        "tone": "warning"
      }
    ],
    "evidence": [
      {
        "label": "Top category",
        "value": "Set",
        "description": "Category có revenue cao nhất."
      },
      {
        "label": "Revenue",
        "value": "392,041",
        "description": "Tổng revenue từ tool result."
      },
      {
        "label": "Rows analyzed",
        "value": "9",
        "description": "Số dòng trong result preview."
      }
    ],
    "why_it_matters": "Nhóm category dẫn đầu ảnh hưởng trực tiếp tới doanh thu tổng. Đây là nơi nên kiểm tra margin, cancellation và inventory trước.",
    "recommended_next_questions": [
      "Category Set có margin tốt không?",
      "Cancel rate của Set theo state như thế nào?",
      "Revenue của Set thay đổi theo tháng ra sao?"
    ],
    "confidence": "high",
    "answer_source": "deterministic_composer",
    "data_warnings": [
      "Amount có missing values nên tổng revenue cần đọc cùng data quality warning."
    ],
    "calculation_notes": [
      "Revenue được tính từ cột amount/revenue sau cleaning và feature engineering.",
      "Breakdown được group theo category."
    ]
  }
}
```

### 4.2 Schema đề xuất trong `app/schemas/models.py`

```python
class AnswerTakeaway(BaseModel):
    label: str
    text: str
    tone: Literal["positive", "neutral", "warning", "risk"] = "neutral"


class AnswerEvidence(BaseModel):
    label: str
    value: str
    description: str | None = None


class AnswerCard(BaseModel):
    headline: str
    summary: str
    key_takeaways: list[AnswerTakeaway] = Field(default_factory=list)
    evidence: list[AnswerEvidence] = Field(default_factory=list)
    why_it_matters: str
    recommended_next_questions: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    answer_source: Literal["llm_structured", "deterministic_composer", "tool_error"] = "deterministic_composer"
    data_warnings: list[str] = Field(default_factory=list)
    calculation_notes: list[str] = Field(default_factory=list)
```

Sau đó mở rộng:

```python
class AgentChatResponse(BaseModel):
    answer: str
    answer_card: AnswerCard | None = None
    ...
```

### 4.3 TypeScript type đề xuất

```ts
export type AnswerCard = {
  headline: string;
  summary: string;
  key_takeaways: Array<{
    label: string;
    text: string;
    tone: "positive" | "neutral" | "warning" | "risk";
  }>;
  evidence: Array<{
    label: string;
    value: string;
    description?: string | null;
  }>;
  why_it_matters: string;
  recommended_next_questions: string[];
  confidence: "low" | "medium" | "high";
  answer_source: "llm_structured" | "deterministic_composer" | "tool_error";
  data_warnings: string[];
  calculation_notes: string[];
};
```

## 5. Backend implementation plan

### 5.1 Tạo service mới

File đề xuất:

```text
app/services/answer_composer.py
```

Functions:

```python
def compose_answer_card(
    *,
    question: str,
    tool_name: str,
    arguments: dict[str, Any],
    result: Any,
    result_summary: dict[str, Any],
    semantic_profile: DatasetSemanticProfile | None = None,
    warnings: list[str] | None = None,
    explanation_source: str = "deterministic_fallback",
) -> dict[str, Any]:
    ...
```

```python
def answer_card_to_text(card: dict[str, Any]) -> str:
    ...
```

Mục tiêu:

- Tạo `answer_card` deterministic trước.
- Convert `answer_card` thành `answer` legacy text.
- Nếu LLM có trả structured JSON tốt hơn thì merge/replace một số phần nhưng không được thay số liệu.

### 5.2 Composer theo tool family

Nên chia rule theo nhóm tool:

#### Overview tools

Tools:

- `get_dataset_overview`
- `get_sales_overview`
- `semantic_overview`
- `semantic_kpis`

Output nên nhấn:

- Dataset có bao nhiêu rows/columns.
- Metric chính là gì.
- Có warning chất lượng dữ liệu không.
- Nên hỏi tiếp breakdown/trend/data quality.

#### Breakdown tools

Tools:

- `revenue_by_category`
- `revenue_by_month`
- `revenue_by_size`
- `top_states_by_revenue`
- `top_cities_by_revenue`
- `semantic_breakdown`
- `groupby_aggregate`

Output nên nhấn:

- Nhóm đứng đầu.
- Metric value.
- Nếu có share thì nêu share.
- Nếu có cancel/risk/margin thì nêu caveat.
- Câu hỏi tiếp nên đào sâu trend/risk/profit.

#### Risk tools

Tools:

- `category_cancellation_summary`
- `state_cancellation_summary`
- `cancellation_summary`
- `hr_attrition_by_role`
- `hr_high_risk_segments`
- `semantic_target_summary`

Output nên nhấn:

- Nhóm có risk cao nhất.
- Sample size/rows/orders để tránh hiểu sai.
- Vì sao risk cao quan trọng.
- Câu hỏi tiếp nên hỏi driver/root cause.

#### Quality tools

Tools:

- `get_missing_values`
- `get_duplicate_rows`
- data quality dashboard.

Output nên nhấn:

- Cột/issue nghiêm trọng nhất.
- Tác động tới metric.
- Nên sửa dữ liệu nào trước.

#### Chart tools

Tools:

- `generate_chart_spec`
- chart shortcut tools.

Output nên nhấn:

- Chart đã vẽ cái gì.
- Trục X/Y là gì.
- Người dùng nên nhìn pattern nào.

#### Multi-step tools

Tool:

- `multi_step`

Output nên tổng hợp:

- Tool 1 tìm gì.
- Tool 2 xác nhận gì.
- Insight chung là gì.
- Nếu các tool mâu thuẫn hoặc thiếu dữ liệu thì nêu rõ.

### 5.3 LLM structured explanation

Hiện `_explain_result` đang hỏi LLM trả text.

Nên đổi thành 2 bước:

1. Tạo deterministic `answer_card`.
2. Nếu mode là `balanced/deep`, gửi compact context + deterministic card cho LLM để cải thiện wording, nhưng yêu cầu trả JSON đúng schema.

Prompt nguyên tắc:

```text
Bạn là senior BI analyst.
Bạn nhận:
- user question
- deterministic answer card
- compact tool result
- warnings

Nhiệm vụ:
- Viết lại headline/summary/why_it_matters/recommended_next_questions cho tự nhiên hơn.
- Không thay số liệu evidence.
- Không thêm metric không có trong tool result.
- Trả ONLY valid JSON theo schema AnswerCard.
```

Nếu JSON parse fail:

- Dùng deterministic card.
- Warning: `LLM structured answer invalid, deterministic composer was used.`

### 5.4 Structured answer không được làm chậm agent

Latency rule:

- `fast`: chỉ dùng deterministic composer.
- `balanced`: dùng LLM structured answer với timeout ngắn.
- `deep`: dùng LLM structured answer + có thể diễn giải sâu hơn.

Nếu Ollama chậm:

- Trả deterministic card ngay.
- Không để chat treo.

## 6. Frontend implementation plan

### 6.1 Update `AgentResponse`

File:

```text
web/src/types.ts
```

Thêm:

```ts
answer_card?: AnswerCard | null;
```

### 6.2 Update `AskCopilot`

File:

```text
web/src/components/AskCopilot.tsx
```

Hiện frontend đang tự tạo:

- conclusion
- evidence
- why
- next

Sau U6:

- Nếu `response.answer_card` tồn tại: render theo `answer_card`.
- Nếu không tồn tại: fallback sang logic hiện tại.

### 6.3 UI layout đề xuất cho answer card

Mỗi AI response nên có thứ tự:

1. Status header:
   - Tool-grounded answer.
   - Latency.
   - Cache.
   - Source.

2. Headline:
   - 1 câu lớn nhất.
   - Không quá dài.

3. Summary:
   - 1 đoạn ngắn 1-2 câu.

4. Evidence metric strip:
   - 3-5 metric cards nhỏ.

5. Key takeaways:
   - Bullet cards có tone:
     - positive
     - neutral
     - warning
     - risk

6. Result preview:
   - table/mini chart/KPI cards.

7. Why it matters:
   - Một panel ngắn.

8. Recommended next questions:
   - Nút click để prefill/send follow-up.

9. Trust/calc details:
   - source columns.
   - calculation notes.
   - warnings.
   - collapsible raw tool result.

### 6.4 Copywriting rules cho frontend

Không nên dùng nhãn quá kỹ thuật làm primary UX:

- Tránh: `COGNITIVE AGENT`, `RUNNING TOOL`, `Tool execution details` ở vị trí quá nổi.
- Nên dùng:
  - `Đang phân tích`
  - `Đã tính từ dữ liệu`
  - `Nguồn tính toán`
  - `Cảnh báo dữ liệu`

Trust text nên rõ nhưng không quá nặng:

```text
Based on deterministic tool result
```

hoặc tiếng Việt:

```text
Dựa trên kết quả tool, không tự bịa số liệu
```

## 7. Prompt design mới

### 7.1 System prompt cho answer composer

```text
Bạn là Senior Business Intelligence Analyst.
Bạn viết câu trả lời bằng tiếng Việt chuyên nghiệp, rõ ràng, thân thiện.

Luật bắt buộc:
- Không bịa số liệu.
- Không thêm metric ngoài tool_result/evidence.
- Không nói quá chắc nếu dữ liệu thiếu, sample nhỏ hoặc có NaN.
- Headline phải là kết luận chính, không phải mô tả tool.
- Evidence phải ngắn, cụ thể, đọc được ngay.
- Why it matters phải giải thích tác động business.
- Recommended questions phải giúp user đào sâu bước tiếp theo.
- Trả ONLY valid JSON theo schema.
```

### 7.2 User prompt payload

```json
{
  "question": "...",
  "domain": "retail",
  "tool_name": "semantic_breakdown",
  "arguments": {},
  "deterministic_answer_card": {},
  "compact_tool_result": [],
  "warnings": [],
  "semantic_roles": {},
  "custom_metrics": []
}
```

### 7.3 Guardrails

- Evidence values từ deterministic card được khóa.
- LLM chỉ được sửa wording.
- Nếu LLM trả evidence khác số liệu gốc, reject.
- Nếu LLM không trả JSON, reject.
- Nếu LLM trả quá dài, truncate theo field.

## 8. Evaluation cho Answer UX

Không nên chỉ test code pass. Cần test chất lượng câu trả lời.

### 8.1 Unit tests

File đề xuất:

```text
tests/test_answer_composer.py
```

Test cases:

- `revenue_by_category` tạo headline có top category.
- `get_sales_overview` tạo evidence revenue/orders/cancel rate.
- `get_missing_values` tạo warning đúng.
- `category_cancellation_summary` nêu sample/risk.
- `multi_step` tổng hợp nhiều tool.
- Empty result không crash.
- Missing/NaN result có data warning.
- `answer_card_to_text` tạo text legacy đọc được.

### 8.2 Agent tests

Mở rộng:

```text
tests/test_agent_orchestrator.py
```

Test:

- `/agent/chat` trả `answer_card`.
- `mode=fast` không gọi LLM nhưng vẫn có card đẹp.
- LLM invalid JSON fallback deterministic.
- LLM cố sửa số liệu evidence thì bị reject.
- Warnings được đưa vào `answer_card.data_warnings`.

### 8.3 Frontend build tests

Command:

```bash
cd web && npm run build
```

Manual check:

- Ask: `SKU nào có doanh thu cao nhất?`
- Ask: `Category nào sales cao nhưng profit thấp?`
- Ask: `Campaign nào response tốt nhất?`
- Ask: `Nhóm nào attrition risk cao?`
- Tắt Ollama, câu trả lời vẫn đẹp nhờ deterministic composer.

### 8.4 Eval answer quality checklist

Trong U5 eval suite, thêm check nhẹ:

- answer_card exists.
- headline not empty.
- evidence length >= 1 nếu tool có result.
- recommended_next_questions length >= 1.
- answer does not include raw JSON.
- answer does not say “maybe”, “I guess”.
- numeric evidence matches tool result.

## 9. Definition of Done

Phase U6 hoàn thành khi:

- Backend có `app/services/answer_composer.py`.
- `AgentChatResponse` có `answer_card`.
- `mode=fast` vẫn trả answer đẹp không cần LLM.
- `balanced/deep` có thể dùng LLM để polish wording bằng structured JSON.
- Frontend render `answer_card` nếu có.
- Error/fallback cũng có card rõ ràng.
- Quick actions dùng recommended next questions từ card.
- Tests pass:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest -q
cd web && npm run build
```

- Manual UX thấy câu trả lời:
  - có kết luận ngay đầu.
  - có evidence dễ đọc.
  - có why it matters.
  - có next questions.
  - có trust/calc details.

## 10. Thứ tự implement đề xuất

### Step 1 - Backend schema

- Thêm `AnswerTakeaway`.
- Thêm `AnswerEvidence`.
- Thêm `AnswerCard`.
- Thêm `answer_card` vào `AgentChatResponse`.

### Step 2 - Deterministic composer

- Tạo `app/services/answer_composer.py`.
- Implement composer cho:
  - overview.
  - list/breakdown.
  - risk/rate.
  - data quality.
  - multi-step.
  - chart.
  - error.

### Step 3 - Wire vào orchestrator

- Trong `_explain_result`, tạo deterministic card trước.
- `answer = answer_card_to_text(card)`.
- Nếu mode không phải `fast`, thử LLM structured polishing.
- Merge warnings.

### Step 4 - Frontend type + renderer

- Update `web/src/types.ts`.
- Trong `AskCopilot`, render `answer_card`.
- Fallback sang renderer hiện tại nếu backend cũ chưa có card.

### Step 5 - Quick actions từ card

- Recommended questions của card trở thành quick action.
- `Explain calculation` dùng `calculation_notes`.
- `Add to report` đưa headline/evidence/why vào markdown.

### Step 6 - Tests

- Unit tests answer composer.
- Agent tests.
- Frontend build.

### Step 7 - UX acceptance doc

Tạo:

```text
docs/26_answer_composer_v2_acceptance_vi.md
```

Nội dung:

- Vấn đề trước U6.
- Contract mới.
- Ví dụ response trước/sau.
- Test commands.
- Manual checklist.
- Giới hạn còn lại.

## 11. Ví dụ output mong muốn

### 11.1 Ecommerce

Question:

```text
SKU nào có doanh thu cao nhất?
```

Output:

```text
SKU JNE3797-KR-L đang là sản phẩm tạo doanh thu cao nhất.

Bằng chứng:
- Revenue: 772,000
- Quantity: 661
- Orders: 527

Vì sao quan trọng:
SKU dẫn đầu là điểm bắt đầu tốt để kiểm tra tồn kho, fulfilment, cancellation và biên lợi nhuận. Nếu SKU này gặp lỗi vận hành, tác động đến doanh thu tổng sẽ lớn.

Nên hỏi tiếp:
SKU này có cancel rate cao ở state nào không?
```

### 11.2 Retail

Question:

```text
Category nào sales cao nhưng profit thấp?
```

Output:

```text
Furniture là nhóm cần kiểm tra vì sales cao nhưng profit/margin thấp hơn kỳ vọng.

Bằng chứng:
- Sales cao trong top category.
- Profit thấp hơn Technology/Office Supplies.
- Discount có thể là một nguyên nhân cần kiểm tra thêm.

Vì sao quan trọng:
Nhóm sales cao nhưng margin thấp có thể làm dashboard trông tích cực nhưng thực tế không tạo nhiều lợi nhuận.

Nên hỏi tiếp:
Furniture bị lỗ ở state hoặc segment nào?
```

### 11.3 HR

Question:

```text
Nhóm nào attrition risk cao?
```

Output:

```text
Nhóm nhân viên làm overtime có attrition risk cao hơn đáng kể.

Bằng chứng:
- Attrition rate của nhóm overtime cao hơn nhóm không overtime.
- Một số department/job role có sample nhỏ nên cần đọc cùng cảnh báo.

Vì sao quan trọng:
Attrition cao ở nhóm overtime có thể phản ánh áp lực công việc, burnout hoặc vấn đề quản lý workload.

Nên hỏi tiếp:
Overtime ảnh hưởng mạnh nhất ở department nào?
```

## 12. Giới hạn còn lại sau U6

Ngay cả khi U6 xong, project vẫn cần các nâng cấp sau để output đạt mức production BI assistant:

- User preference cho giọng trả lời:
  - concise.
  - executive.
  - technical.
  - beginner-friendly.
- Citation chi tiết tới dòng/cột/source file.
- Report composer chuyên nghiệp hơn.
- Saved chat history.
- Human feedback:
  - helpful / not helpful.
  - wrong number.
  - unclear answer.
- Eval scoring bằng human rubric hoặc LLM judge offline.

Nhưng U6 là bước nền quan trọng nhất để khắc phục cảm giác “AI trả lời chưa đẹp”.

