# Phase U5 - Kế hoạch implement Evaluation Suite

## 1. Mục tiêu

Phase U5 xây dựng bộ đánh giá để đo project có phân tích tốt nhiều loại CSV/XLS/XLSX hay không.

Trọng tâm của phase này:

- Đo domain detection.
- Đo semantic role mapping.
- Đo intent parsing.
- Đo tool selection.
- Đo numeric correctness khi có expected value.
- Đo latency, fallback, cache hit và error rate.

Không làm trong phase này:

- Không refactor frontend lớn.
- Không lazy-load Plotly.
- Không migrate LangGraph.
- Không bắt buộc Ollama chạy trong eval.

## 2. Thiết kế đã chọn

Eval runner chạy trực tiếp qua service layer:

```text
dataset file
  -> DatasetStore.save_dataframe
  -> optional data dictionary
  -> build_semantic_profile
  -> parse_universal_intent
  -> AgentOrchestrator.chat(mode=fast)
  -> compare expected checks
  -> markdown/json report
```

Lý do không đi qua HTTP:

- Không bị ảnh hưởng bởi CORS.
- Không cần backend server đang chạy.
- Dễ chạy trong CI.
- Tập trung test logic phân tích thật.

## 3. Cấu trúc eval

```text
evals/
  manifest.json
  datasets/
  dictionaries/
  questions/
  expected/
  reports/
  run_eval.py
  download_datasets.py
  prepare_snapshots.py
  generate_numeric_checks.py
```

`manifest.json` là nguồn sự thật cho 20 dataset ban đầu.

`questions/*.jsonl` chứa 100 câu hỏi eval.

`reports/latest.md` và `reports/latest.json` được sinh khi chạy eval.

`generate_numeric_checks.py` sinh expected numeric checks từ snapshot hiện tại để eval đo được số liệu aggregate thật, không chỉ route/tool đúng.

## 4. Dataset strategy

Chiến lược là external-first:

- Dataset local có sẵn được snapshot vào `evals/datasets`.
- Dataset UCI có direct zip URL được auto-download nếu có thể.
- Dataset Maven/Kaggle/manual sẽ in hướng dẫn tải và đường dẫn cần đặt file.
- Dataset raw/package sau khi tải được chuẩn hóa bằng `prepare_snapshots.py`.

`prepare_snapshots.py` xử lý các case thực tế:

- Northwind Traders nhiều bảng -> `retail/northwind_orders.csv`.
- Maven Fuzzy Factory nhiều bảng -> `ecommerce/maven_toy_store_orders.csv`.
- MTA wide table -> long table `logistics/mta_daily_ridership.csv`.
- Excel/semicolon/encoding khác nhau -> CSV UTF-8 chuẩn.

Raw dataset lớn không commit vào git.

## 5. Commands

Tải/snapshot dataset:

```bash
PYTHONPATH=. python evals/download_datasets.py
```

Validate dataset đã đủ chưa:

```bash
PYTHONPATH=. python evals/prepare_snapshots.py
PYTHONPATH=. python evals/download_datasets.py --validate
```

Chạy eval không strict:

```bash
PYTHONPATH=. python evals/run_eval.py --mode fast
```

Chạy eval strict:

```bash
PYTHONPATH=. python evals/run_eval.py --mode fast --strict
```

Hoặc dùng Makefile:

```bash
make eval-download
make eval-prepare
make eval-numeric-checks
make eval-validate
make eval
```

## 6. Threshold ban đầu

```text
Domain detection >= 80%
Role mapping >= 75%
Intent parsing >= 80%
Tool selection >= 80%
Numeric correctness >= 90%
Error rate <= 5%
```

Các threshold này là baseline để phát hiện regression. Khi dataset suite đầy đủ hơn, threshold có thể nâng dần.

## 7. Ghi chú về dataset chưa đủ

Manifest có đúng 20 mục. Một số nguồn Maven cần tải thủ công từ browser. Sau khi tải, đặt file đúng `local_path` trong manifest.

Hai dataset nằm trong backlog để mở rộng sau mốc 20:

- UCI Student Academics Performance.
- Telecom Customer Churn.
