# Phase U7.1/U7.2 - Hoàn thiện i18n + giảm bundle Plotly

## 1. Bối cảnh

Sau U7, UI chính đã được Việt hóa khá nhiều, nhưng vẫn còn hạn chế:

- Copy tiếng Việt đang nằm một phần trong `vi.ts`, một phần vẫn nằm trực tiếp trong component.
- Chưa có `en.ts`.
- Chưa có language toggle.
- Chưa lưu lựa chọn ngôn ngữ của user.
- Plotly đang được import trực tiếp trong `App.tsx`, làm initial JS bundle rất lớn.

Mục tiêu U7.1/U7.2 là chuyển từ “Việt hóa UI” sang một nền i18n có thể mở rộng.

## 2. Mục tiêu

### U7.1 - Copy extraction

- Tách copy cấp app/shell/navigation/Ask Copilot sang dictionary.
- Chuẩn hóa key copy để `vi` và `en` cùng shape.
- Giữ thuật ngữ data/AI engineering khi cần:
  - `dataset`
  - `metric`
  - `revenue`
  - `profit`
  - `margin`
  - `SKU`
  - `semantic role`
  - `tool`
  - `LLM`

### U7.2 - Language toggle

- Thêm `en.ts`.
- Thêm `I18nProvider`.
- Thêm `useI18n`.
- Thêm toggle `VI/EN` trên top bar.
- Lưu lựa chọn vào `localStorage`.
- Default language là `vi`.

### Performance - Plotly lazy load

- Không import `react-plotly.js` trực tiếp ở initial bundle.
- Dùng `React.lazy`.
- Bọc chart render bằng `Suspense`.
- Thêm loading skeleton cho chart.
- Kỳ vọng:
  - main JS bundle giảm rõ.
  - Plotly tách thành chunk riêng.

## 3. Files cần thay đổi

### i18n

```text
web/src/i18n/vi.ts
web/src/i18n/en.ts
web/src/i18n/index.tsx
web/src/types.ts
```

### Frontend integration

```text
web/src/main.tsx
web/src/App.tsx
web/src/components/AskCopilot.tsx
```

### Docs

```text
docs/28_phase_u7_1_u7_2_i18n_plotly_performance_plan_vi.md
docs/29_phase_u7_1_u7_2_i18n_plotly_performance_acceptance_vi.md
```

## 4. Technical design

### 4.1 Translation shape

`vi.ts` là source of truth:

```ts
export const vi = {
  app: {},
  nav: {},
  sections: {},
  ask: {},
};

export type Translation = typeof vi;
```

`en.ts` phải implement đúng:

```ts
export const en: Translation = { ... };
```

Lợi ích:

- TypeScript bắt lỗi thiếu key.
- Không cần runtime validator.
- Copy mới thêm vào `vi` sẽ bắt `en` cập nhật theo.

### 4.2 I18n provider

Provider:

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

### 4.3 Language toggle

UI:

```text
VI | EN
```

Vị trí:

- Top bar, cạnh Ollama status.

Behavior:

- Click đổi language ngay.
- Lưu localStorage.
- Reload vẫn giữ language.

### 4.4 Plotly lazy-load

Trước:

```ts
import Plot from "react-plotly.js";
```

Sau:

```ts
const Plot = lazy(() => import("react-plotly.js"));
```

Render:

```tsx
<Suspense fallback={<ChartLoading />}>
  <Plot ... />
</Suspense>
```

## 5. Definition of Done

Hoàn thành khi:

- Có `en.ts`.
- Có `I18nProvider`.
- App dùng `useI18n`.
- Ask Copilot dùng dictionary theo language hiện tại.
- Toggle VI/EN hoạt động.
- Language lưu vào localStorage.
- Build frontend pass.
- Plotly không còn nằm trong initial main chunk.
- Full backend tests vẫn pass.

## 6. Test commands

Frontend:

```bash
cd web
npm run build
```

Backend:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest -q
```

Manual:

- Mở frontend.
- Đổi VI sang EN.
- Reload browser.
- Language vẫn là EN.
- Vào Dashboard/Charts, chart vẫn render.
- Kiểm tra build output có Plotly chunk riêng.

