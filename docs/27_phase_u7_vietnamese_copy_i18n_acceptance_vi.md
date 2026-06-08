# Nghiệm thu Phase U7 - Vietnamese Product Copy + i18n Foundation

## 1. Mục tiêu

Phase U7 xử lý vấn đề UI đang lẫn nhiều tiếng Anh trong khi người dùng chính hiện tại là tiếng Việt.

Mục tiêu không chỉ là dịch từng chữ, mà là:

- Đồng nhất ngôn ngữ UI chính sang Tiếng Việt.
- Giữ thuật ngữ data/business quan trọng như `revenue`, `profit`, `SKU`, `margin`, `semantic role` khi cần thiết.
- Tạo nền i18n nhẹ để sau này không phải sửa copy rải rác trong component.
- Không thay đổi backend logic hoặc analytics behavior.

## 2. Thay đổi đã implement

### 2.1 Shared Vietnamese copy foundation

Đã thêm:

```text
web/src/i18n/vi.ts
```

File này hiện chứa copy chính cho:

- App shell.
- Sidebar navigation.
- Section metadata.
- Ask AI Copilot.
- Placeholder, status label, empty state.

Lợi ích:

- Copy chính không còn nằm rải rác hoàn toàn trong `App.tsx`.
- Có thể mở rộng thành `en.ts` sau này nếu muốn English/Vietnamese toggle.
- Giảm rủi ro UI mỗi page dùng một tone khác nhau.

### 2.2 Shared `Section` type

Đã chuyển `Section` sang:

```text
web/src/types.ts
```

Lý do:

- `vi.ts` cần biết các section hợp lệ.
- `App.tsx` và i18n copy dùng chung cùng một type.
- Tránh lệch key giữa nav, section metadata và route state.

### 2.3 Việt hóa App Shell

Đã Việt hóa các vùng chính trong:

```text
web/src/App.tsx
```

Bao gồm:

- Sidebar nav:
  - Nạp dữ liệu.
  - Tổng quan.
  - Chất lượng dữ liệu.
  - Dashboard thông minh.
  - Phân tích Ecommerce.
  - Biểu đồ.
  - Hỏi AI Copilot.
  - Báo cáo.

- Header section:
  - Eyebrow.
  - Title.
  - Subtitle.
  - Active file.
  - Backend API.
  - AI status.
  - Error title.

### 2.4 Việt hóa Upload / Overview / Quality

Đã Việt hóa:

- Upload zone.
- Supported domains.
- Workspace session history.
- Parsed file confirmation.
- Overview KPI labels.
- Header dictionary panel.
- Analysis recommendations panel.
- Missing value audit.
- Data health warnings.

Ngoài ra, domain cards đã bỏ emoji và chuyển sang icon Lucide để giao diện chuyên nghiệp hơn.

### 2.5 Việt hóa Smart Dashboard controls

Đã Việt hóa phần lớn copy người dùng nhìn thấy trong:

- Metric Builder.
- Data Dictionary.
- Semantic Mapping Studio.
- Semantic Profile Debug.

Các thuật ngữ role/metric như `revenue`, `profit`, `category`, `margin` vẫn giữ vì đó là vocabulary của semantic layer và expression engine.

### 2.6 Việt hóa Ecommerce / Charts / Report

Đã Việt hóa:

- Ecommerce section titles/subtitles.
- Chart builder labels.
- Chart render result panel.
- Executive report actions.
- Download/copy buttons.

### 2.7 Việt hóa Ask AI Copilot

Đã cập nhật:

```text
web/src/components/AskCopilot.tsx
```

Các phần đã Việt hóa:

- Timeline:
  - Hiểu câu hỏi.
  - Chọn phân tích.
  - Chạy tool.
  - Chuẩn bị câu trả lời.

- Header.
- Suggested questions label.
- Empty state.
- Input placeholder.
- Send button.
- Trust badge.
- Result preview.
- Source/calculation labels.
- Tool details.
- Error bubble actions.

## 3. Những gì cố ý chưa dịch hoàn toàn

Một số thuật ngữ vẫn giữ tiếng Anh vì chúng là vocabulary của data/AI engineering:

- `revenue`
- `profit`
- `margin`
- `SKU`
- `semantic role`
- `metric`
- `dataset`
- `tool`
- `fallback`
- `cache`
- `router`
- `LLM`
- `Ollama`

Lý do:

- Dịch ép có thể làm user khó liên hệ với tên cột và tool result.
- Những thuật ngữ này cũng xuất hiện trong data dictionary, semantic mapper, metric expression.
- Giữ nhất quán giữa UI và backend contract.

## 4. Test đã chạy

### 4.1 Frontend build

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
- Đây là backlog performance/lazy-load, không phải lỗi U7.

### 4.2 Backend tests

Command:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest -q
```

Kết quả:

```text
124 passed
```

Warning còn lại:

- `requests` dependency warning trong env Python.
- Không liên quan đến U7.

## 5. Manual acceptance checklist

Chạy:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd web
npm run dev
```

Checklist:

- Sidebar hiển thị tiếng Việt.
- Header mỗi page hiển thị tiếng Việt.
- Upload page không còn copy tiếng Anh chính.
- Overview/Quality page đọc tự nhiên hơn.
- Smart Dashboard controls dễ hiểu hơn.
- Ask AI Copilot timeline và answer UX hiển thị tiếng Việt.
- Report buttons hiển thị tiếng Việt.
- Thuật ngữ data như revenue/profit/SKU vẫn giữ khi cần.

## 6. Giới hạn còn lại

U7 là i18n foundation nhẹ, chưa phải hệ i18n hoàn chỉnh.

Chưa làm:

- English/Vietnamese toggle.
- `en.ts`.
- Context provider cho language.
- Persist language preference.
- Dịch toàn bộ dynamic backend text.
- Dịch toàn bộ Plotly chart title từ backend.
- Dịch toàn bộ warnings từ backend.

## 7. Bước tiếp theo đề xuất

Nếu muốn làm tiếp phần language thật chuẩn:

### U7.1 - Copy extraction hoàn chỉnh

- Tách toàn bộ copy còn lại khỏi `App.tsx`.
- Tách copy cho:
  - metric builder.
  - data dictionary.
  - ecommerce dashboard.
  - charts.
  - report.

### U7.2 - Language toggle

- Thêm `web/src/i18n/en.ts`.
- Thêm `I18nProvider`.
- Cho user chọn `VI/EN`.
- Lưu lựa chọn vào localStorage.

### U7.3 - Backend message localization

- Response backend nhận `locale`.
- Agent answer composer biết `vi` hoặc `en`.
- Tool warnings có mapping dịch.

### U7.4 - Product copy QA

- Duyệt toàn bộ UI bằng checklist:
  - câu ngắn.
  - không quá kỹ thuật.
  - không lẫn tone marketing.
  - không lạm dụng English.
  - không dịch thuật ngữ data gây khó hiểu.

## 8. Kết luận

Phase U7 đã giúp UI chính thống nhất hơn với người dùng Việt.

Quan trọng nhất:

- App không còn cảm giác “nửa dashboard tiếng Anh, nửa chat tiếng Việt”.
- Ask AI Copilot và dashboard controls thân thiện hơn.
- Project đã có nền để mở rộng i18n thay vì tiếp tục sửa copy rải rác.

