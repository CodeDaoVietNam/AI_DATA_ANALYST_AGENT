# Phase D - Nghiệm thu Fast Copilot, Multi-Step Agent và Deep Domain Insight

## 1. Mục tiêu đã implement

Phase D nâng project từ semantic dashboard v1 lên nền phân tích có chiều sâu hơn:

- AI Copilot có cache, latency metadata, tool timeline và SSE streaming.
- Agent có thể chạy multi-step plan tối đa 3 tools cho câu hỏi phức tạp.
- Dashboard backend-driven dùng contract v2, có insight biết nói.
- Semantic mapper có candidates, confidence label, domain confidence và user override.
- Retail, Marketing, HR có domain analytics sâu hơn.
- Frontend có Semantic Mapping Studio để chỉnh mapping role -> column.

## 2. Latency layer

Đã thêm `app/services/cache_manager.py`:

- `semantic_profile_cache`: TTL 30 phút.
- `dashboard_cache`: TTL 10 phút.
- `tool_result_cache`: TTL 10 phút.

Cache key có:

- `dataset_id`
- file signature
- `semantic_version`
- semantic overrides
- tool name
- tool arguments

Khi user chỉnh semantic mapping, backend tăng `semantic_version` và invalidate cache liên quan.

## 3. Ollama routing

`OllamaProvider` hiện hỗ trợ:

- `OLLAMA_MODEL`, mặc định `qwen2.5:7b`.
- `OLLAMA_ROUTER_MODEL`, mặc định `qwen2.5:3b`.
- `OLLAMA_ROUTER_TIMEOUT`, mặc định `4`.
- `OLLAMA_EXPLAIN_TIMEOUT`, mặc định `8`.

Khuyến nghị local:

```bash
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
```

Router dùng model nhỏ hơn để giảm latency. Explanation dùng model chính khi cần. Nếu LLM lỗi hoặc timeout, backend vẫn trả deterministic fallback.

## 4. API mới và API được nâng cấp

### Agent

`POST /agent/chat` vẫn hoạt động như cũ, nhưng response có thêm:

- `tool_calls`
- `agent_plan`
- `latency`
- `cache`

`POST /agent/chat/stream` trả `text/event-stream` với các event:

- `progress`
- `plan`
- `tool_started`
- `tool_finished`
- `explanation_started`
- `final`
- `error`

### Semantic override

`GET /semantic-profile/{dataset_id}` giờ trả thêm:

- `domain_confidence`
- `domain_reasons`
- `candidates`
- `overrides`

`PUT /semantic-profile/{dataset_id}/overrides`

Body:

```json
{
  "domain": "retail",
  "roles": {
    "revenue": "Sales",
    "profit": "Profit",
    "date": "Order Date"
  }
}
```

`DELETE /semantic-profile/{dataset_id}/overrides`

Reset mapping về auto-detect.

### Dashboard

`GET /dashboard/{dataset_id}` trả contract v2:

- `contract_version: 2`
- `kpi_cards`
- `insight_cards`
- `charts`
- `tables`
- `semantic_profile`
- `warnings`
- `cache`

Insight card có:

- `finding`
- `evidence`
- `why_it_matters`
- `recommended_next_question`
- `tone`
- `severity`
- `confidence`
- `related_chart_id`
- `related_table_id`

## 5. Multi-step agent flow

Agent hiện chạy single-step hoặc multi-step tùy câu hỏi.

Ví dụ ecommerce:

> State nào revenue cao nhưng cancellation risk cũng cao?

Plan:

1. `top_states_by_revenue`
2. `state_cancellation_summary`

Ví dụ retail:

> Segment nào margin thấp dù sales cao?

Plan:

1. `retail_margin_summary`
2. `retail_top_opportunities`
3. `retail_loss_analysis`

Ví dụ marketing:

> Campaign nào response tốt nhất?

Plan:

1. `marketing_campaign_acceptance`
2. `marketing_response_by_segment`
3. `marketing_rfm_summary`

Ví dụ HR:

> Nhóm nhân viên nào attrition risk cao?

Plan:

1. `hr_attrition_by_role`
2. `hr_income_band_attrition`
3. `hr_high_risk_segments`

## 6. Domain analytics mới

### Retail

- Margin summary.
- Loss-making groups.
- Discount effect.
- Segment-state-category interaction.
- High revenue / low margin opportunities.

### Marketing

- Response by segment/country/campaign.
- Campaign acceptance.
- RFM-like summary.
- Income band response.
- Purchase channel summary.

### HR

- Attrition by department.
- Attrition by job role.
- Attrition by overtime.
- Income band attrition.
- Tenure risk.
- Combined high-risk segments.

### Generic

- Numeric distributions.
- Top categorical values.
- Missing/duplicate insight.
- Correlation highlights.

## 7. Frontend đã nâng cấp

Ask AI Copilot:

- Dùng stream endpoint trước.
- Nếu stream lỗi, fallback sang `/agent/chat`.
- Pending bubble cập nhật theo event.
- Hiển thị multi-step tool list.
- Hiển thị latency.

Smart Dashboard:

- Render insight card v2.
- Có nút `Ask this` từ recommended next question.
- Có Semantic Mapping Studio.
- User có thể đổi domain và mapping role -> column.
- Save/reset mapping gọi backend override API và rebuild dashboard.

## 8. Test đã chạy

Backend:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest -q
```

Kết quả:

```text
64 passed, 1 warning
```

Warning còn lại đến từ package `requests` trong môi trường hiện tại, không phải lỗi logic project.

Frontend:

```bash
cd web
npm run build
```

Kết quả:

```text
✓ built
```

Vite vẫn cảnh báo bundle lớn do Plotly. Đây là cảnh báo đã biết, chưa chặn phase này.

## 9. Manual acceptance checklist

Chạy backend:

```bash
uvicorn app.main:app --reload
```

Chạy frontend:

```bash
cd web
npm run dev
```

Nếu dùng Ollama:

```bash
ollama serve
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
```

Checklist:

- Upload `Amazon Sale Report.csv`, mở Smart Dashboard, thấy domain ecommerce và insight cards.
- Upload `sample_-_superstore.xls`, thấy domain retail và margin/opportunity tables.
- Upload `Marketing+Data/marketing_data.csv`, thấy marketing campaign/channel/RFM sections.
- Upload `HR-Employee-Attrition.csv`, thấy HR attrition/risk sections.
- Ask AI câu: `State nào revenue cao nhưng cancellation risk cũng cao?`
- Ask AI câu: `Segment nào margin thấp dù sales cao?`
- Ask AI câu: `Campaign nào response tốt nhất?`
- Ask AI câu: `Nhóm nhân viên nào attrition risk cao?`
- Tắt Ollama hoặc dùng model chưa pull, Copilot vẫn trả deterministic fallback.
- Vào Semantic Mapping Studio, đổi mapping revenue/date/category, save, dashboard refresh.
- Reset semantic mapping, dashboard quay về auto-detect.

## 10. Giới hạn còn lại

- Cache là in-memory, restart server sẽ mất.
- Semantic override lưu trong metadata JSON, chưa có database thật.
- Multi-step agent vẫn là orchestrator tự viết, chưa phải LangGraph.
- Insight engine v2 là heuristic deterministic, chưa có statistical significance.
- Streaming dùng SSE qua fetch, chưa có cancel request/abort đầy đủ.
- Frontend chưa code-split Plotly nên bundle còn lớn.
- Chưa có persistent chat history.
- Chưa có auth/user workspace.

## 11. Hướng sau Phase D

Sau checkpoint này mới nên cân nhắc:

- LangGraph cho multi-agent workflow dài hơn.
- SQLite/PostgreSQL cho metadata, overrides, chat history.
- Redis cho distributed cache/rate limit.
- Background jobs cho dashboard precompute.
- Chart recommendation engine chuyên sâu hơn.
- User-defined metrics và saved dashboards.
