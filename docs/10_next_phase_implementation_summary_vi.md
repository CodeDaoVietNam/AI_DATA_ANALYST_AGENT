# Phase mới: Generic Tools, Chart API, React Dashboard và Ollama

Tài liệu này ghi lại cách chạy và kiểm thử phase nâng cấp sau checkpoint nền móng.

## 1. Các năng lực mới

Phase này thêm:

- Profiler inference ít warning hơn.
- Generic analysis tools cho mọi CSV.
- `POST /chart` để tạo Plotly chart JSON.
- Ollama local agent qua `POST /agent/chat`.
- React dashboard mới trong `web/`.
- Docker Compose service mới cho React.

Streamlit vẫn được giữ làm fallback tại port `8501`.

## 2. Chạy Ollama local

Trước khi dùng Ask AI:

```bash
ollama pull qwen2.5:7b
ollama serve
```

Backend mặc định đọc:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

Nếu chạy backend trong Docker Compose, compose đã trỏ tới:

```text
http://host.docker.internal:11434
```

## 3. Chạy backend

```bash
uvicorn app.main:app --reload
```

Backend:

```text
http://localhost:8000
```

## 4. Chạy React dashboard

```bash
cd web
npm install
npm run dev
```

React:

```text
http://localhost:5173
```

## 5. Chạy bằng Docker Compose

```bash
docker compose up --build
```

Services:

- Backend: `http://localhost:8000`
- React dashboard: `http://localhost:5173`
- Streamlit fallback: `http://localhost:8501`

## 6. API mới

### Chart API

```http
POST /chart
```

Body:

```json
{
  "dataset_id": "...",
  "chart_type": "bar",
  "x": "Category",
  "y": "Revenue"
}
```

### Agent API

```http
POST /agent/chat
```

Body:

```json
{
  "dataset_id": "...",
  "question": "Category nào có revenue cao nhất?"
}
```

Agent flow:

```text
question
  -> Ollama chọn tool bằng JSON
  -> backend validate tool
  -> Pandas tool tính toán
  -> Ollama giải thích kết quả bằng tiếng Việt
```

## 7. Test

```bash
PYTHONPATH=. pytest -q
```

React build:

```bash
cd web
npm run build
```

## 8. Lưu ý

- LLM không nhận full CSV.
- Backend chỉ cho phép approved tools.
- Nếu Ollama trả JSON lỗi, agent sẽ trả fallback an toàn.
- Không có database/Redis trong phase này.
