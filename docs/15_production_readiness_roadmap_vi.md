# Production Readiness Roadmap - Từ Technical MVP đến sản phẩm thật

## 1. Đánh giá hiện trạng

Project hiện tại đã vượt mức demo đơn giản. Nó đang ở mức **advanced prototype / technical MVP**:

- Có FastAPI backend.
- Có React dashboard.
- Hỗ trợ upload CSV/XLS/XLSX.
- Có semantic mapper để nhận diện domain và role cột.
- Có dashboard backend-driven contract v2.
- Có AI Copilot dùng deterministic Pandas tools + Ollama.
- Có multi-step agent, SSE streaming, cache, semantic override.
- Có SQLite metadata bước đầu.
- Có structured logging bằng `structlog`.
- Có test backend tương đối tốt.

Tuy nhiên project **chưa production-ready** vì còn thiếu các năng lực quan trọng:

- Chưa có user account/workspace thật.
- API key hiện chỉ là bảo vệ rất nhẹ, chưa phải auth system hoàn chỉnh.
- File/dataset storage còn đơn giản.
- SQLite metadata mới là bước đầu, chưa có migration/versioning nghiêm túc.
- Chưa có audit trail đầy đủ cho dataset, tool call, LLM call.
- Chưa có LLM evaluation suite.
- Chưa có monitoring/metrics dashboard.
- Code interpreter vẫn cần sandbox mạnh hơn nếu cho user thật dùng.
- Chưa có data governance cho PII/sensitive data.
- Chưa có CI/CD và deployment production chuẩn.

Kết luận:

> Project hiện tại rất tốt cho portfolio, demo kỹ thuật, học AI engineering và làm nền móng sản phẩm. Để trở thành sản phẩm production, cần thêm các phase về security, persistence, observability, evaluation và deployment.

## 2. Tiêu chí để gọi là production-ready

Một AI Data Analyst Agent production-ready nên đạt các tiêu chí sau:

| Nhóm | Tiêu chí |
|---|---|
| Product | User có workspace, dataset manager, saved dashboard, saved report, chat history |
| Data | Dataset có owner, version, metadata, schema, semantic mapping, retention policy |
| Security | Auth, authorization, upload validation, PII detection, sandbox isolation |
| AI Reliability | Tool routing eval, answer eval, hallucination guardrails, fallback strategy |
| Observability | Structured logs, metrics, traces, request id, agent run logs, error tracking |
| Performance | Cache rõ ràng, async/background jobs, large-file strategy, pagination |
| Deployment | Docker production, migrations, CI/CD, health checks, backup/restore |
| Governance | Audit log, data deletion, sensitive data handling, access history |

## 3. Phase 0 - Stabilize Current MVP

### Mục tiêu

Ổn định hiện trạng trước khi thêm feature lớn. Phase này giúp project không bị “phình” mà mất kiểm soát.

### Việc cần làm

- Rà soát lại README, requirements, docs để phản ánh đúng trạng thái project.
- Tách rõ trạng thái:
  - đã có
  - đang prototype
  - chưa production
- Chạy lại full test backend.
- Chạy frontend build.
- Ghi lại manual acceptance cho 4 dataset:
  - Amazon Sales
  - Superstore
  - Marketing Campaign
  - HR Attrition

### Definition of Done

- README trung thực, không quảng cáo quá mức.
- Requirements cài được backend đầy đủ.
- `pytest -q` pass.
- `cd web && npm run build` pass.
- Có file roadmap production readiness.

## 4. Phase 1 - Product Workspace Foundation

### Mục tiêu

Biến project từ “upload file vào app local” thành workspace có cấu trúc.

### Việc cần làm

- Thêm model `Workspace`.
- Thêm model `User` tối thiểu hoặc `APIClient`.
- Dataset thuộc về workspace.
- Chat history thuộc về dataset/workspace.
- Dashboard/report có thể được lưu.
- Semantic overrides versioned theo dataset.

### Schema đề xuất

Các bảng nên có:

- `users`
- `workspaces`
- `workspace_members`
- `datasets`
- `dataset_versions`
- `semantic_profiles`
- `semantic_overrides`
- `dashboard_snapshots`
- `chat_sessions`
- `chat_messages`
- `agent_runs`
- `tool_calls`

### API đề xuất

- `GET /workspaces`
- `POST /workspaces`
- `GET /workspaces/{workspace_id}/datasets`
- `POST /workspaces/{workspace_id}/datasets/upload`
- `GET /datasets/{dataset_id}/versions`
- `GET /datasets/{dataset_id}/chat-sessions`
- `POST /datasets/{dataset_id}/chat-sessions`

### Definition of Done

- User có thể upload nhiều dataset vào một workspace.
- Dataset list không còn là global list lẫn lộn.
- Chat có thể lưu và mở lại.
- Dashboard có thể lưu snapshot.

## 5. Phase 2 - Database, Migration và Storage chuẩn

### Mục tiêu

Làm data layer đủ chắc để không mất metadata, không phụ thuộc JSON file, không khó migrate.

### Việc cần làm

- Chuẩn hóa SQLAlchemy models.
- Thêm Alembic migrations.
- Dùng PostgreSQL cho production, SQLite chỉ dùng local/dev.
- Lưu file upload vào storage riêng:
  - local object storage trong dev
  - S3/MinIO trong production
- Tách metadata và raw file.
- Thêm checksum cho file.
- Thêm dataset versioning.

### Storage contract đề xuất

Mỗi dataset version cần có:

- `dataset_id`
- `version_id`
- `original_filename`
- `storage_uri`
- `file_size`
- `content_hash`
- `row_count`
- `column_count`
- `created_at`
- `created_by`

### Definition of Done

- Có migration reproducible.
- Restart server không mất metadata.
- Có thể backup/restore database.
- Có thể thay local storage bằng S3/MinIO mà ít sửa code.

## 6. Phase 3 - Security và Data Governance

### Mục tiêu

Đưa project tới mức có thể xử lý dữ liệu user thật một cách có trách nhiệm.

### Việc cần làm

- Thay API key đơn giản bằng auth rõ ràng:
  - JWT/OAuth2 cho app thật
  - API key scoped cho integration
- Authorization theo workspace/dataset.
- Giới hạn upload:
  - size
  - extension
  - MIME type
  - số dòng/cột tối đa
- PII/sensitive data detection:
  - email
  - phone
  - address
  - ID number
  - salary/income
- PII masking option.
- Audit log:
  - ai đã upload
  - ai đã hỏi gì
  - tool nào đã chạy
  - ai đã export dữ liệu
- Data retention:
  - xóa dataset
  - xóa workspace
  - xóa chat history

### Code interpreter hardening

Hiện code interpreter đã có subprocess + restricted keywords, nhưng production nên:

- Chạy trong Docker sandbox riêng.
- Có CPU/memory limit.
- Không mount source code app.
- Không có network.
- Có timeout cứng.
- Có output size limit.
- Có allowlist API rõ ràng.
- Có option tắt code interpreter theo workspace.

### Definition of Done

- User chỉ thấy dataset của workspace mình.
- Export có audit log.
- Upload file sai format bị reject rõ ràng.
- Code interpreter không có quyền truy cập filesystem/network nhạy cảm.

## 7. Phase 4 - AI Reliability và Evaluation Suite

### Mục tiêu

Không chỉ “AI trả lời được”, mà phải đo được AI trả lời đúng đến mức nào.

### Việc cần làm

- Tạo golden dataset questions cho từng domain:
  - ecommerce
  - retail
  - marketing
  - HR
  - generic
- Mỗi test case có:
  - question
  - expected tool
  - expected arguments
  - expected numeric result
  - answer constraints
- Đo:
  - tool routing accuracy
  - numeric correctness
  - hallucination rate
  - fallback rate
  - average latency
  - cache hit rate

### Eval files đề xuất

- `evals/questions/ecommerce.jsonl`
- `evals/questions/retail.jsonl`
- `evals/questions/marketing.jsonl`
- `evals/questions/hr.jsonl`
- `evals/run_eval.py`
- `evals/reports/latest.md`

### Guardrails cần thêm

- Final answer phải cite tool result.
- Không cho LLM tự tạo số liệu.
- Nếu tool result thiếu dữ liệu, answer phải nói rõ.
- Nếu confidence thấp, answer phải gợi ý chỉnh semantic mapping.
- Nếu câu hỏi vượt khả năng, trả lời honest fallback.

### Definition of Done

- Có command chạy eval.
- Có report eval tự động.
- Tool routing accuracy đạt ngưỡng đặt trước.
- Numeric correctness được kiểm tra bằng test deterministic.

## 8. Phase 5 - Observability và Agent Run Logging

### Mục tiêu

Khi lỗi xảy ra, biết lỗi ở đâu: upload, semantic mapping, tool execution, Ollama, cache hay frontend.

### Việc cần làm

- Chuẩn hóa structured logs.
- Log agent run vào database.
- Log từng tool call:
  - tool name
  - args
  - execution time
  - cache hit/miss
  - error
- Log LLM call:
  - provider
  - model
  - timeout
  - duration
  - success/error
- Metrics endpoint:
  - request count
  - error count
  - p50/p95 latency
  - cache hit rate
  - LLM fallback rate
- Tích hợp Sentry hoặc OpenTelemetry về sau.

### API/endpoint đề xuất

- `GET /admin/metrics`
- `GET /admin/agent-runs`
- `GET /admin/agent-runs/{run_id}`

### Definition of Done

- Mỗi câu hỏi có `agent_run_id`.
- Có thể xem lại toàn bộ plan/tool/explanation của một agent run.
- Có latency breakdown đáng tin.

## 9. Phase 6 - Dashboard và Product UX v3

### Mục tiêu

Dashboard không chỉ “có chart”, mà phải giúp người dùng hiểu và hành động.

### Việc cần làm

- Saved dashboards.
- Report builder.
- Export PDF/HTML/Markdown.
- Drill-down từ insight sang table/chart.
- Chart recommendation engine.
- Metric dictionary.
- User-defined metrics:
  - `revenue = sales - discount`
  - `margin = profit / sales`
  - `conversion_rate = response / total_customers`
- Dataset compare:
  - compare 2 versions
  - compare 2 segments
  - compare current vs previous period
- Better loading/error states.
- Empty-state theo domain.

### Frontend improvement

- Tách `App.tsx` lớn thành modules:
  - `pages/UploadPage.tsx`
  - `pages/DashboardPage.tsx`
  - `pages/AskPage.tsx`
  - `components/DataTable.tsx`
  - `components/InsightCard.tsx`
  - `components/SemanticMappingPanel.tsx`
  - `api/client.ts`
- Code split Plotly để giảm bundle.
- Add table pagination/virtualization.
- Add dataset selector UX tốt hơn.

### Definition of Done

- User có thể tạo dashboard, lưu dashboard, export report.
- Dashboard lớn vẫn responsive.
- Frontend build nhẹ hơn hoặc Plotly được lazy-load.

## 10. Phase 7 - Performance và Scalability

### Mục tiêu

Chuẩn bị cho file lớn, nhiều user, nhiều dataset.

### Việc cần làm

- Background jobs cho:
  - profiling
  - semantic profile
  - dashboard precompute
  - report generation
- Redis/Celery hoặc RQ nếu cần.
- Pagination cho API table.
- Sampling strategy cho chart.
- Dataframe cache có memory limit.
- Large file strategy:
  - DuckDB
  - Polars
  - Parquet cache
- Async job status:
  - pending
  - running
  - completed
  - failed

### Definition of Done

- Upload file lớn không block request quá lâu.
- Dashboard có thể load theo section.
- Chart API không trả payload quá lớn.
- Có memory limit rõ ràng.

## 11. Phase 8 - Deployment, CI/CD và Operations

### Mục tiêu

Triển khai được như một service thật.

### Việc cần làm

- Dockerfile production.
- Docker Compose production:
  - backend
  - frontend
  - postgres
  - redis optional
  - ollama optional/local
- Alembic migration chạy trong deploy.
- CI pipeline:
  - install backend
  - run pytest
  - install frontend
  - run npm build
  - optional lint/typecheck
- Health checks:
  - `/health`
  - database check
  - storage check
  - ollama check
- Backup/restore docs.
- `.env.production.example`.

### Definition of Done

- Clone repo mới có thể chạy bằng Docker Compose.
- CI fail nếu backend/frontend hỏng.
- Có health check cho deploy platform.
- Có hướng dẫn rollback cơ bản.

## 12. Thứ tự ưu tiên khuyến nghị

Nếu muốn làm hiệu quả, không nên làm tất cả cùng lúc.

Thứ tự tốt nhất:

1. Phase 0 - Stabilize Current MVP.
2. Phase 4 - AI Evaluation Suite.
3. Phase 5 - Agent Run Logging.
4. Phase 1 - Workspace Foundation.
5. Phase 2 - Database/Migration/Storage chuẩn.
6. Phase 3 - Security/Data Governance.
7. Phase 6 - Dashboard UX v3.
8. Phase 7 - Performance/Scalability.
9. Phase 8 - Deployment/CI/CD.

Lý do:

- AI project cần eval sớm, nếu không sẽ khó biết nâng cấp có thật sự tốt hơn không.
- Agent run logging giúp debug mọi phase sau.
- Workspace/database/auth nên đi cùng nhau nhưng có thể chia nhỏ.
- Dashboard UX nên làm sau khi metric/semantic layer đã ổn.

## 13. Production readiness score hiện tại

| Mảng | Điểm hiện tại | Nhận xét |
|---|---:|---|
| Data analytics tools | 8/10 | Rất tốt cho MVP, còn cần statistical validation |
| Semantic layer | 7/10 | Có override/candidates, cần custom metrics/versioning |
| AI Copilot | 7/10 | Có tool calling/multi-step/cache, cần eval suite |
| Frontend dashboard | 6.5/10 | Demo tốt, cần modular hóa và saved dashboards |
| Persistence | 5.5/10 | Đã có SQLite metadata, cần migration/workspace |
| Security | 4/10 | Có API key/upload limit, chưa có auth/governance |
| Observability | 5/10 | Có structured log, cần agent run DB/metrics |
| Deployment | 4.5/10 | Có Docker Compose dev, cần production pipeline |

Tổng thể:

> Project đang ở mức **technical MVP mạnh**, phù hợp portfolio/demo nội bộ. Để production, cần thêm khoảng 4-8 tuần engineering tập trung tùy độ sâu của auth, storage, eval và deployment.

## 14. Definition of Done cho production v1

Có thể gọi là production v1 khi đạt tối thiểu:

- Có workspace/user/auth.
- Dataset metadata nằm trong PostgreSQL hoặc SQLite có migration rõ.
- File storage có abstraction.
- Có agent run logging.
- Có eval suite cho AI Copilot.
- Có upload validation và sensitive data warning.
- Có dashboard/report persistence.
- Có CI chạy backend tests và frontend build.
- Có Docker Compose production hoặc deployment guide rõ.
- Có monitoring tối thiểu: logs, request id, latency, error rate.

Khi đạt các điều này, project có thể chuyển từ “prototype rất xịn” sang “beta product có thể cho người dùng thật thử nghiệm có kiểm soát”.
