# Nghiệm thu Phase U7.1/U7.2 - i18n toggle + Plotly lazy-load

## 1. Mục tiêu đã hoàn thành

Sprint này hoàn thiện hai phần:

1. **i18n foundation**
   - Thêm dictionary `vi`.
   - Thêm dictionary `en`.
   - Thêm provider/hook.
   - Thêm toggle `VI/EN`.
   - Lưu lựa chọn language vào localStorage.

2. **Frontend performance**
   - Không import Plotly trực tiếp vào initial app bundle.
   - Lazy-load `react-plotly.js`.
   - Tách Plotly thành chunk riêng.
   - Thêm loading fallback cho chart.

## 2. Files đã thêm

### i18n

```text
web/src/i18n/en.ts
web/src/i18n/index.tsx
```

### Docs

```text
docs/28_phase_u7_1_u7_2_i18n_plotly_performance_plan_vi.md
docs/29_phase_u7_1_u7_2_i18n_plotly_performance_acceptance_vi.md
```

## 3. Files đã cập nhật

```text
web/src/i18n/vi.ts
web/src/main.tsx
web/src/App.tsx
web/src/components/AskCopilot.tsx
web/src/types.ts
```

## 4. i18n architecture

### 4.1 Translation source of truth

`vi.ts` hiện là source of truth:

```ts
export const vi = { ... };
export type Translation = typeof vi;
```

`en.ts` implement cùng shape:

```ts
export const en: Translation = { ... };
```

Lợi ích:

- Nếu `vi` thêm key mới, TypeScript bắt `en` phải cập nhật.
- Không cần runtime schema validator.
- Giảm rủi ro thiếu copy khi mở rộng UI.

### 4.2 I18n provider

Đã thêm:

```tsx
<I18nProvider>
  <App />
</I18nProvider>
```

Hook:

```ts
const { t, language, setLanguage } = useI18n();
```

LocalStorage key:

```text
ai-data-analyst-language
```

Default:

```text
vi
```

### 4.3 Language toggle

Đã thêm toggle:

```text
VI | EN
```

Vị trí:

- Top bar, cạnh Ollama status.

Behavior:

- Click đổi language ngay.
- Reload browser vẫn giữ lựa chọn.
- `AskCopilot` đổi timeline/suggestion/header/input theo language hiện tại.

## 5. Plotly lazy-load

### 5.1 Trước

App import trực tiếp:

```ts
import Plot from "react-plotly.js";
```

Hệ quả:

- Plotly nằm trong initial bundle.
- Build warning lớn.
- User chưa vào chart vẫn phải tải chart library.

### 5.2 Sau

Đã đổi sang:

```ts
const Plot = lazy(() => import("react-plotly.js"));
```

Chart render được bọc:

```tsx
<Suspense fallback={<ChartLoading />}>
  <Plot ... />
</Suspense>
```

Fallback:

- Hiển thị loading skeleton.
- Copy loading theo language hiện tại.

## 6. Build result

Command:

```bash
cd web
npm run build
```

Kết quả:

```text
dist/assets/index-C4C43bhP.js           265.64 kB │ gzip: 79.52 kB
dist/assets/react-plotly-BhbnSUFM.js  4,870.53 kB │ gzip: 1,476.55 kB
```

Ý nghĩa:

- Initial app bundle đã giảm mạnh.
- Plotly được tách thành chunk riêng.
- Warning lớn vẫn còn vì Plotly chunk lớn, nhưng nó không còn chặn initial app load.

So với trước đó:

```text
index JS khoảng 5.13 MB
```

Sau lazy-load:

```text
index JS khoảng 266 KB
```

Đây là cải thiện rất lớn về perceived performance.

## 7. Backend tests

Command:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest -q
```

Kết quả:

```text
124 passed
```

Warning còn lại:

- `requests` dependency warning trong Python env.
- Không liên quan đến sprint này.

## 8. Manual acceptance checklist

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

- Mở app thấy default là Tiếng Việt.
- Click `EN`, nav/header/Ask Copilot đổi sang English.
- Reload browser, app vẫn giữ `EN`.
- Click `VI`, app đổi lại Tiếng Việt.
- Upload dataset vẫn hoạt động.
- Vào Dashboard/Charts, chart loading fallback xuất hiện nếu Plotly chưa tải xong.
- Chart render đúng sau khi lazy chunk tải xong.
- Ask Copilot suggestions đổi theo language.

## 9. Giới hạn còn lại

U7.1/U7.2 chưa làm hết 100% mọi copy:

- Một số copy sâu trong Metric Builder/Data Dictionary vẫn còn thuật ngữ English do liên quan trực tiếp tới schema/data roles.
- Backend dynamic warnings chưa nhận locale.
- Answer Composer hiện ưu tiên Tiếng Việt từ backend; nếu muốn English answer thật sự, cần truyền `locale` xuống `/agent/chat`.
- Plotly chunk vẫn lớn, nhưng đã tách khỏi initial app bundle.

## 10. Bước tiếp theo đề xuất

### U7.3 - Backend locale support

- Thêm `locale` vào request.
- Answer Composer trả `vi` hoặc `en`.
- Tool warning có mapping theo locale.

### U7.4 - Copy QA pass

- Duyệt toàn bộ UI theo checklist.
- Tách nốt copy còn lại nếu muốn i18n tuyệt đối.

### U9 - Further performance

- Lazy-load cả Dashboard/Charts route-level.
- Manual chunking cho vendor.
- Skeleton UI cho dashboard charts.
