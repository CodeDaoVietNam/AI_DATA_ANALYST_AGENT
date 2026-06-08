# Phase U5 - Nghiệm thu Evaluation Suite

## 1. Những gì đã implement

Đã thêm Evaluation Suite cho project:

- `evals/manifest.json` với 20 dataset mục tiêu.
- `evals/questions/*.jsonl` với 100 câu hỏi eval.
- `evals/run_eval.py` để chạy eval qua service layer.
- `evals/download_datasets.py` để snapshot/download/validate dataset.
- Data dictionary mẫu cho các schema đã biết.
- `Makefile` với các lệnh chạy backend/frontend/test/build/eval.
- Report có thêm bảng per-domain để nhìn domain nào đang yếu.
- Snapshot eval strip khoảng trắng ở tên cột để data dictionary không bị lệch vì header bẩn.
- `evals/prepare_snapshots.py` để chuẩn hóa raw dataset/package thành CSV snapshot đúng manifest.
- `evals/generate_numeric_checks.py` để sinh expected numeric checks từ snapshot hiện tại.
- Data dictionary CSV hỗ trợ cột `domain` để các domain như logistics, survey, education, product được map rõ hơn.

## 2. Luồng eval

```text
load dataset
  -> save vào DatasetStore
  -> apply data dictionary nếu có
  -> build semantic profile
  -> parse universal intent
  -> run AgentOrchestrator fast mode
  -> compare checks
  -> generate markdown/json report
```

Eval không cần FastAPI server chạy.

## 3. Dataset nghiệm thu

Dataset local đã có thể snapshot ngay:

- Amazon Sale Report.
- Marketing Campaign Results.
- HR Employee Attrition.
- Superstore nếu môi trường đã cài `xlrd`.

Dataset external trong manifest:

- UCI Online Retail II.
- UCI Bank Marketing.
- UCI Student Performance.
- Maven Financial Consumer Complaints.
- Maven US Candy Distributor.
- Maven MTA Daily Ridership.
- Maven NYC Traffic Accidents.
- Maven Automotive Fuel Economy.
- Và các dataset Maven/manual khác trong manifest.

## 4. Commands nghiệm thu

```bash
PYTHONPATH=. python evals/download_datasets.py
PYTHONPATH=. python evals/prepare_snapshots.py
PYTHONPATH=. python evals/generate_numeric_checks.py
PYTHONPATH=. python evals/download_datasets.py --validate
PYTHONPATH=. python evals/run_eval.py --mode fast
PYTHONPATH=. python evals/run_eval.py --mode fast --strict
```

Lệnh tiện ích:

```bash
make eval-download
make eval-prepare
make eval-numeric-checks
make eval-validate
make eval
```

## 5. Output nghiệm thu

Runner sinh:

```text
evals/reports/latest.md
evals/reports/latest.json
```

Report có:

- Tổng số case.
- Số pass/fail/error.
- Domain detection accuracy.
- Role mapping accuracy.
- Intent accuracy.
- Tool accuracy.
- Numeric accuracy.
- Answer constraint pass rate.
- Fallback rate.
- Average latency.
- p95 latency.
- Cache hit rate.
- Error rate.
- Bảng per-domain.
- Danh sách case pass không được, gồm failed/error/skipped.

## 6. Kết quả nghiệm thu hiện tại

Đã chạy mới nhất:

```bash
PYTHONPATH=. /home/ductien/miniconda3/envs/reis/bin/python evals/prepare_snapshots.py
PYTHONPATH=. /home/ductien/miniconda3/envs/reis/bin/python evals/generate_numeric_checks.py
PYTHONPATH=. /home/ductien/miniconda3/envs/reis/bin/python evals/download_datasets.py --validate
PYTHONPATH=. /home/ductien/miniconda3/envs/reis/bin/python evals/run_eval.py --mode fast --strict
```

Trạng thái dataset:

- Present: 20/20 dataset.
- Raw package đã được chuẩn hóa thành single-file CSV snapshot cho manifest.
- Numeric checks hiện có: 83/100 eval cases.
- Strict eval không còn skipped case.

Kết quả strict eval hiện tại:

```text
Total cases: 100
Passed: 100
Failed: 0
Errors: 0
Skipped: 0
Domain accuracy: 100%
Role mapping accuracy: 100%
Intent accuracy: 100%
Tool accuracy: 100%
Numeric accuracy: 100%
Error rate: 0%
Overall pass: yes
```

Đây là mốc nghiệm thu đầy đủ U5 MVP: đủ 20 dataset và 100 câu hỏi eval chạy qua strict mode.

## 7. Giới hạn còn lại

- Một số dataset external vẫn cần tải thủ công vì Maven/Kaggle không luôn có direct URL ổn định.
- Numeric checks hiện đã phủ 83 case, nhưng vẫn cần bổ sung thêm các kiểm tra nhiều dòng/multiple metrics cho các case correlation, missing values và chart/anomaly.
- Một số domain như logistics, survey, product vẫn dựa nhiều vào data dictionary.
- Eval hiện đo routing/semantic/tool correctness tốt, nhưng chưa đo chất lượng insight narrative ở mức chuyên sâu.

## 8. Cảm nhận thay đổi

Trước U5, việc đánh giá project còn dựa nhiều vào cảm giác khi upload vài file mẫu.

Sau U5, project bắt đầu có một thước đo kỹ thuật rõ ràng:

- Biết dataset nào fail.
- Biết fail ở semantic mapping, intent, tool hay numeric.
- Biết domain nào yếu.
- Biết latency và fallback rate.

Đây là nền quan trọng trước khi nâng AI Copilot, mở rộng semantic mapper hoặc cân nhắc LangGraph.
