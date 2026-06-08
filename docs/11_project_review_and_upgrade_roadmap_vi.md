# Đánh giá hiện trạng và roadmap nâng cấp

## 1. Nhận định ngắn gọn

Project hiện tại đã vượt qua mức notebook/demo cơ bản vì đã có:

- Backend FastAPI.
- Upload CSV.
- Profiling dữ liệu.
- Data cleaner và feature engineering cho Amazon Sales.
- Ecommerce deterministic tools.
- Chart API.
- React dashboard.
- Ollama agent orchestration.
- Test coverage cho các service quan trọng.

Tuy nhiên project vẫn chưa phải một AI data product thật sự hoàn thiện. Điểm yếu lớn nhất hiện tại là **AI Copilot chưa đủ ổn định và chưa đủ “biết việc”**. Dashboard đã có nhiều bảng và chart, nhưng trải nghiệm chưa đủ thông minh nếu người dùng không biết hỏi gì hoặc nếu LLM route sai tool.

## 2. Vấn đề lớn đã phát hiện

### 2.1 Ask AI phụ thuộc quá nhiều vào LLM router

Trước bản sửa hiện tại, mọi câu hỏi đều đi qua Ollama để chọn tool. Điều này tạo ra các lỗi:

- Ollama trả JSON không hợp lệ.
- Ollama chọn sai tool.
- Ollama chọn đúng tool nhưng truyền sai column.
- Thời gian phản hồi lâu khiến người dùng tưởng app không chạy.
- Câu hỏi phổ biến như “SKU nào doanh thu cao nhất?” vẫn phải chờ LLM suy luận, trong khi backend đã có tool chắc chắn.

Đã cải thiện:

- Thêm deterministic rule-based router cho các câu hỏi phổ biến.
- Các intent ecommerce quen thuộc giờ có thể route thẳng tới Pandas tool.
- LLM vẫn được dùng để giải thích kết quả, nhưng không còn là điểm nghẽn duy nhất.

### 2.2 Copilot UI chưa giải thích trạng thái hệ thống

Người dùng không biết:

- Ollama có đang chạy không.
- Model có tồn tại không.
- App đang dùng LLM hay deterministic fallback.
- Tool nào vừa được gọi.
- Lỗi đến từ backend, Ollama, hay dataset không tương thích.

Đã cải thiện:

- Thêm `/agent/status`.
- Frontend hiển thị trạng thái Ollama/model.
- Thêm prompt suggestions.
- Hiển thị warnings trong chat response.

### 2.3 Project vẫn thiên về Amazon Sales

Amazon Sales hiện là domain chính. Generic CSV support đã có nhưng còn mỏng:

- Generic tools chưa đủ nhiều.
- Chưa có semantic column mapping.
- Chưa có schema detector theo domain.
- Chưa có multi-dataset analysis.
- Chưa có auto-dashboard cho các dataset ngoài ecommerce.

Điều này không sai ở phase hiện tại, nhưng cần nói rõ: project đang mạnh nhất ở ecommerce analytics, chưa phải universal data analyst.

## 3. Nâng cấp nên làm tiếp theo

### Phase A - Làm AI Copilot ổn định trước

Ưu tiên cao nhất.

Nên làm:

- Thêm chat message pending state để user thấy câu hỏi đã được gửi.
- Lưu tool execution timeline:
  - selected tool
  - arguments
  - execution time
  - row count/result summary
- Thêm “retry with fallback tool”.
- Thêm quick action buttons sau mỗi câu trả lời:
  - View chart
  - Export result
  - Ask follow-up
- Giới hạn kích thước tool result gửi lại cho LLM.
- Tách tool result đầy đủ và explanation context rút gọn.

### Phase B - Tạo semantic layer cho dataset

Đây là bước làm project đa dạng hơn.

Nên có:

- `app/services/semantic_mapper.py`
- Detect các cột tương đương:
  - revenue: amount, sales, total, price
  - date: date, order_date, created_at
  - category: category, product_category, segment
  - location: state, city, country, region
  - quantity: qty, quantity, units
- Trả về `DatasetSemanticProfile`.
- Các generic tool dùng semantic profile thay vì hard-code column.

Khi đó project có thể hiểu nhiều file CSV hơn, không chỉ Amazon Sales.

### Phase C - Auto dashboard theo domain

Hiện dashboard ecommerce đã khá mạnh, nhưng generic dashboard còn yếu.

Nên làm:

- Nếu dataset là ecommerce: dùng ecommerce dashboard.
- Nếu dataset là finance: doanh thu, chi phí, margin, trend.
- Nếu dataset là marketing: campaign, channel, conversion.
- Nếu dataset là HR: headcount, attrition, salary.
- Nếu không detect được domain: dùng generic dashboard.

Backend nên có endpoint:

```text
GET /dashboard/{dataset_id}
```

Response gồm:

- KPI cards.
- Insight cards.
- Chart specs.
- Tables.
- Warnings.

Frontend chỉ render response, không tự build toàn bộ logic.

### Phase D - Tool coverage sâu hơn

Nên thêm tools:

- `compare_segments`
- `detect_outliers`
- `trend_analysis`
- `period_over_period_change`
- `top_bottom_contributors`
- `pareto_analysis`
- `cohort_summary`
- `anomaly_detection`
- `forecast_next_period` ở mức baseline
- `explain_metric_change`

Đây là nơi AI Copilot bắt đầu có nhiều use case thực tế hơn.

### Phase E - Lưu trữ và production foundations

Hiện storage vẫn chưa production-grade.

Nên thêm:

- SQLite/PostgreSQL cho metadata dataset.
- File storage rõ ràng hơn.
- Dataset versioning.
- Upload size limit.
- Basic auth.
- CORS config theo env.
- Logging structured.
- Request ID.
- Error response chuẩn.
- Rate limit nếu dùng external LLM.

Redis chưa bắt buộc ở phase này, nhưng sẽ hữu ích khi có:

- Rate limit.
- Cache tool result.
- Cache LLM explanation.
- Background jobs.

## 4. Đánh giá độ ưu tiên

Nên làm tiếp theo theo thứ tự:

1. Fix và nâng AI Copilot UX.
2. Semantic column mapping.
3. Backend-driven auto dashboard.
4. Generic analytics tool expansion.
5. Multi-domain dataset support.
6. Database metadata.
7. LangGraph/multi-agent.

LangGraph chưa nên làm ngay nếu tool layer và semantic layer chưa đủ chắc. LangGraph sẽ hữu ích khi cần multi-step reasoning, nhưng nếu tool còn mỏng thì graph chỉ làm hệ thống phức tạp hơn.

## 5. Kết luận

Project hiện tại là một nền tảng tốt, nhưng cảm giác “chưa ổn” của bạn là đúng. Lý do không phải vì project sai hướng, mà vì nó đang ở giữa giai đoạn chuyển từ dashboard demo sang AI analytics product.

Điểm cần nâng cấp mạnh nhất là:

- AI Copilot phải đáng tin.
- Dataset support phải đa dạng hơn.
- Dashboard phải sinh từ backend insight contract.
- Tool layer phải rộng và sâu hơn.
- Frontend phải hướng người dùng bằng insight, không chỉ show bảng.

Sau các nâng cấp này, project mới thật sự giống một AI Data Analyst Agent chuyên nghiệp.
