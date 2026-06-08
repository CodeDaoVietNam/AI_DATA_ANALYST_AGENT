# Phase U1 - Data Dictionary Upload/Edit Implementation Plan

## 1. Mục tiêu phase

Phase U1 tập trung thêm **Data Dictionary Layer** để project hiểu ý nghĩa cột tốt hơn, thay vì phụ thuộc hoàn toàn vào heuristic auto-detection của semantic mapper.

Ví dụ dataset có các cột khó hiểu:

```text
amt, dt, prod_grp, cust_seg
```

Auto semantic mapper có thể không chắc:

- `amt` là amount, revenue hay cost?
- `dt` là order date, created date hay delivery date?
- `prod_grp` là category hay segment?
- `cust_seg` là customer segment hay customer id?

Data dictionary cho phép user khai báo rõ:

```text
amt       -> revenue
dt        -> date
prod_grp  -> category
cust_seg  -> segment
```

Kết quả mong muốn:

- Semantic profile chính xác hơn.
- Dashboard generic/domain-aware tốt hơn.
- AI Copilot chọn tool đúng hơn.
- User có quyền giải thích dataset thay vì để hệ thống đoán bừa.

## 2. Có cần tải thêm dataset từ các link tham khảo không?

**Không bắt buộc trong Phase U1.**

Các link như W3C CSV on the Web, Frictionless Table Schema, Pandera, Great Expectations chủ yếu dùng để tham khảo cách thiết kế metadata/schema cho dữ liệu tabular.

Phase U1 có thể test bằng:

- Dataset hiện có trong project:
  - `data/raw/Amazon Sale Report.csv`
  - `data/raw/sample_-_superstore.xls`
  - `data/raw/Marketing+Data/marketing_data.csv`
  - `data/raw/HR-Employee-Attrition.csv`
- Dataset synthetic nhỏ tự tạo trong unit tests.
- Một vài data dictionary CSV/JSON mẫu tự viết.

Khi sang phase **U5 - Evaluation Suite**, lúc đó mới cần gom thêm 20-50 dataset từ Kaggle, Maven Analytics, UCI, Data.gov hoặc các nguồn public khác.

Nói ngắn gọn:

> U1 cần data dictionary mẫu, chưa cần dataset mới từ web. U5 mới cần mở rộng dataset thật sự.

## 3. Phạm vi implement

Phase U1 gồm 4 nhóm việc:

1. Backend data dictionary service.
2. Database/storage support.
3. Semantic mapper integration.
4. Frontend Data Dictionary panel.

Không làm trong phase này:

- Custom metric builder.
- Universal planner intent schema.
- Eval suite 20-50 CSV.
- LangGraph.
- Production auth/workspace.

## 4. Data dictionary format

### 4.1 CSV format

Format CSV được hỗ trợ:

```csv
column_name,business_name,description,semantic_role,data_type,unit,aggregation,sensitive,allowed_values
Sales,Revenue,Total sales amount,revenue,number,USD,sum,false,
Order Date,Order Date,Date order was placed,date,date,,,
Segment,Customer Segment,Customer group,segment,string,,,
Profit,Profit,Net profit,profit,number,USD,sum,false,
Discount,Discount,Discount rate,discount,number,percent,mean,false,
```

Ý nghĩa từng field:

| Field | Bắt buộc | Ý nghĩa |
|---|---:|---|
| `column_name` | Có | Tên cột thật trong dataset |
| `business_name` | Không | Tên nghiệp vụ dễ hiểu |
| `description` | Không | Mô tả cột |
| `semantic_role` | Không | Role như `revenue`, `date`, `category`, `target` |
| `data_type` | Không | `string`, `number`, `date`, `boolean`, `categorical` |
| `unit` | Không | USD, VND, percent, count |
| `aggregation` | Không | sum, mean, count, min, max |
| `sensitive` | Không | Cột có nhạy cảm hay không |
| `allowed_values` | Không | Danh sách value hợp lệ, cách nhau bằng `|` |

Ví dụ `allowed_values`:

```csv
Attrition,Attrition,Employee left company,target,boolean,,mean,false,Yes|No
```

### 4.2 JSON format

Format JSON được hỗ trợ:

```json
{
  "domain": "retail",
  "fields": [
    {
      "column_name": "Sales",
      "business_name": "Revenue",
      "description": "Total sales amount",
      "semantic_role": "revenue",
      "data_type": "number",
      "unit": "USD",
      "aggregation": "sum",
      "sensitive": false,
      "allowed_values": []
    }
  ]
}
```

### 4.3 Domain values đề xuất

Các domain hợp lệ ban đầu:

- `ecommerce`
- `retail`
- `marketing`
- `hr`
- `finance`
- `logistics`
- `education`
- `survey`
- `product`
- `generic`

Nếu user để trống `domain`, hệ thống vẫn auto-detect domain như hiện tại.

### 4.4 Semantic roles đề xuất

Các role nên hỗ trợ ở U1:

- `revenue`
- `cost`
- `profit`
- `margin`
- `discount`
- `date`
- `category`
- `segment`
- `quantity`
- `city`
- `state`
- `country`
- `customer`
- `campaign`
- `channel`
- `employee`
- `department`
- `job_role`
- `salary`
- `target`
- `conversion`
- `overtime`
- `tenure`
- `recency`
- `monetary`
- `frequency`

## 5. Backend design

### 5.1 Files cần tạo

Tạo service mới:

```text
app/services/data_dictionary.py
```

Nhiệm vụ:

- Parse dictionary CSV.
- Parse dictionary JSON.
- Validate dictionary against DataFrame columns.
- Normalize boolean/list fields.
- Convert dictionary thành semantic overrides.
- Serialize/deserialize dictionary từ database.

### 5.2 Files cần sửa

```text
app/schemas/models.py
app/database.py
app/services/storage.py
app/services/semantic_mapper.py
app/services/dashboard_builder.py
app/services/agent_orchestrator.py
app/main.py
```

### 5.3 Pydantic models

Thêm vào `app/schemas/models.py`:

```python
class DataDictionaryField(BaseModel):
    column_name: str
    business_name: str | None = None
    description: str | None = None
    semantic_role: str | None = None
    data_type: str | None = None
    unit: str | None = None
    aggregation: str | None = None
    sensitive: bool = False
    allowed_values: list[str] = Field(default_factory=list)


class DataDictionary(BaseModel):
    domain: str | None = None
    fields: list[DataDictionaryField] = Field(default_factory=list)


class DataDictionaryResponse(BaseModel):
    dataset_id: str
    dictionary: DataDictionary | None = None
    source: str = "none"
    warnings: list[str] = Field(default_factory=list)
```

### 5.4 Database changes

Hiện project đã có SQLite/SQLAlchemy metadata. Có 2 lựa chọn.

#### Option A - Lưu dictionary JSON trong bảng dataset metadata

Thêm cột vào `DatasetMetadata`:

```python
data_dictionary_json = Column(Text, default="{}")
```

Ưu điểm:

- Dễ làm.
- Phù hợp MVP.
- Ít bảng mới.

Nhược điểm:

- Khó query field-level.
- Không version history chi tiết.

#### Option B - Tạo bảng riêng

Tạo bảng:

```text
dataset_data_dictionaries
```

Fields:

- `id`
- `dataset_id`
- `dictionary_json`
- `created_at`
- `updated_at`

Ưu điểm:

- Sạch hơn.
- Dễ mở rộng version sau này.

Nhược điểm:

- Nhiều code hơn.

Khuyến nghị U1:

> Dùng Option A trước để làm nhanh và đủ tốt. Sang production phase có thể migrate thành bảng riêng/versioned table.

### 5.5 Storage methods

Thêm vào `DatasetStore`:

```python
def get_data_dictionary(self, dataset_id: str) -> dict | None:
    ...

def set_data_dictionary(self, dataset_id: str, dictionary: dict) -> dict:
    ...

def clear_data_dictionary(self, dataset_id: str) -> None:
    ...
```

Khi set/clear dictionary:

- Tăng `semantic_version`.
- Save database.
- Invalidate cache ở API layer.

### 5.6 Data dictionary service interface

`app/services/data_dictionary.py`:

```python
def parse_data_dictionary_csv(content: bytes) -> dict:
    ...


def parse_data_dictionary_json(content: bytes) -> dict:
    ...


def normalize_data_dictionary(raw: dict) -> dict:
    ...


def validate_data_dictionary(dictionary: dict, columns: list[str]) -> list[str]:
    ...


def dictionary_to_semantic_overrides(dictionary: dict) -> dict:
    ...
```

### 5.7 Validation rules

Validation bắt buộc:

- `column_name` phải tồn tại trong dataset.
- `semantic_role` nếu có thì nên nằm trong role allowlist.
- `data_type` nếu có thì nằm trong:
  - `string`
  - `number`
  - `date`
  - `boolean`
  - `categorical`
- `aggregation` nếu có thì nằm trong:
  - `sum`
  - `mean`
  - `count`
  - `min`
  - `max`
  - `median`
- `sensitive` parse được thành boolean.
- `allowed_values` CSV string được tách bằng `|`.

Validation không nên quá cứng ở U1:

- Nếu `semantic_role` lạ, có thể warning thay vì reject.
- Nếu `data_type` không khớp dtype thật, warning thay vì reject.

### 5.8 Semantic mapper integration

Hiện semantic mapper nhận `overrides`.

U1 nên thêm flow:

```text
auto candidates
  + data dictionary
  + user semantic overrides
  -> final semantic profile
```

Priority:

1. User semantic override.
2. Data dictionary.
3. Auto detection.

Nếu dictionary khai báo:

```json
{
  "domain": "retail",
  "fields": [
    {"column_name": "Sales", "semantic_role": "revenue"}
  ]
}
```

Semantic profile phải trả:

```json
{
  "domain": "retail",
  "roles": {
    "revenue": {
      "column": "Sales",
      "confidence": 1.0,
      "confidence_label": "dictionary",
      "reason": "Data dictionary mapping"
    }
  }
}
```

Nếu user override lại:

```json
{
  "roles": {
    "revenue": "Profit"
  }
}
```

Final role phải là:

```text
revenue -> Profit
```

Reason:

```text
User semantic override
```

### 5.9 Cache invalidation

Khi upload/update/delete dictionary:

- Invalidate semantic profile cache.
- Invalidate dashboard cache.
- Invalidate tool result cache.
- Tăng semantic version.

Điều này quan trọng vì cùng một dataset nhưng mapping đổi thì kết quả dashboard/tool cũng đổi.

## 6. API design

### 6.1 Upload data dictionary

Endpoint:

```text
POST /datasets/{dataset_id}/data-dictionary
```

Request:

- `multipart/form-data`
- field: `file`
- file extension: `.csv` hoặc `.json`

Response:

```json
{
  "dataset_id": "...",
  "dictionary": {
    "domain": "retail",
    "fields": []
  },
  "source": "uploaded_file",
  "warnings": []
}
```

Behavior:

- Load dataset.
- Parse file.
- Validate columns.
- Save dictionary.
- Increase semantic version.
- Invalidate cache.
- Return normalized dictionary.

### 6.2 Get data dictionary

Endpoint:

```text
GET /datasets/{dataset_id}/data-dictionary
```

Response nếu có dictionary:

```json
{
  "dataset_id": "...",
  "dictionary": {
    "domain": "retail",
    "fields": []
  },
  "source": "saved",
  "warnings": []
}
```

Response nếu chưa có:

```json
{
  "dataset_id": "...",
  "dictionary": null,
  "source": "none",
  "warnings": ["No data dictionary has been saved for this dataset."]
}
```

### 6.3 Update data dictionary

Endpoint:

```text
PUT /datasets/{dataset_id}/data-dictionary
```

Request JSON:

```json
{
  "domain": "retail",
  "fields": [
    {
      "column_name": "Sales",
      "business_name": "Revenue",
      "semantic_role": "revenue",
      "data_type": "number",
      "aggregation": "sum"
    }
  ]
}
```

Behavior:

- Validate against dataset.
- Save normalized dictionary.
- Increase semantic version.
- Invalidate cache.

### 6.4 Delete data dictionary

Endpoint:

```text
DELETE /datasets/{dataset_id}/data-dictionary
```

Response:

```json
{
  "dataset_id": "...",
  "deleted": true
}
```

Behavior:

- Clear dictionary.
- Increase semantic version.
- Invalidate cache.
- Semantic mapper quay lại auto/user override flow.

## 7. Frontend design

### 7.1 Vị trí UI

Khuyến nghị đặt trong Smart Dashboard:

```text
Smart Dashboard
  - KPI cards
  - Insight cards
  - Charts
  - Tables
  - Semantic Mapping Studio
  - Data Dictionary Panel
```

Không cần tạo page mới ở U1, vì dictionary liên quan trực tiếp semantic profile/dashboard.

### 7.2 Data Dictionary Panel

Panel nên có:

- Upload CSV/JSON dictionary.
- Current dictionary table.
- Edit inline các field:
  - column name
  - business name
  - description
  - semantic role
  - data type
  - unit
  - aggregation
  - sensitive
  - allowed values
- Save button.
- Reset/delete button.
- Warning display.

### 7.3 Mapping source display

Trong Semantic Mapping Studio, thêm cột:

```text
source
```

Values:

- `auto`
- `dictionary`
- `override`

Ví dụ:

| role | column | confidence | source | reason |
|---|---|---:|---|---|
| revenue | Sales | 1.0 | dictionary | Data dictionary mapping |
| date | Order Date | 1.0 | override | User semantic override |
| category | Segment | 0.82 | auto | exact name match |

### 7.4 API client updates

`web/src/api.ts` thêm:

```ts
export function getDataDictionary(datasetId: string): Promise<DataDictionaryResponse>
export function uploadDataDictionary(datasetId: string, file: File): Promise<DataDictionaryResponse>
export function saveDataDictionary(datasetId: string, dictionary: DataDictionary): Promise<DataDictionaryResponse>
export function deleteDataDictionary(datasetId: string): Promise<{ dataset_id: string; deleted: boolean }>
```

`web/src/types.ts` thêm:

```ts
export type DataDictionaryField = {
  column_name: string;
  business_name?: string | null;
  description?: string | null;
  semantic_role?: string | null;
  data_type?: string | null;
  unit?: string | null;
  aggregation?: string | null;
  sensitive: boolean;
  allowed_values: string[];
};

export type DataDictionary = {
  domain?: string | null;
  fields: DataDictionaryField[];
};
```

## 8. Test plan

### 8.1 Unit tests cho parser

File:

```text
tests/test_data_dictionary.py
```

Test cases:

- Parse CSV dictionary hợp lệ.
- Parse JSON dictionary hợp lệ.
- Parse `allowed_values` bằng `|`.
- Parse `sensitive` từ `true/false/yes/no/1/0`.
- Missing optional fields vẫn hợp lệ.
- Unknown semantic role tạo warning.
- Unknown aggregation tạo warning hoặc reject tùy policy.

### 8.2 Unit tests cho validation

Test cases:

- Dictionary có `column_name` không tồn tại -> reject.
- Dictionary có duplicate `column_name` -> warning hoặc reject.
- Dictionary domain hợp lệ.
- Dictionary domain lạ -> warning.
- Data type mismatch -> warning.

### 8.3 Semantic mapper tests

Test cases:

- Dictionary role override auto mapping.
- User override có ưu tiên cao hơn dictionary.
- Dictionary domain override domain heuristic.
- Role reason là `Data dictionary mapping`.
- Confidence label là `dictionary`.

### 8.4 API integration tests

File:

```text
tests/test_data_dictionary_api.py
```

Flow:

1. Upload dataset.
2. Upload dictionary CSV.
3. `GET /datasets/{dataset_id}/data-dictionary`.
4. `GET /semantic-profile/{dataset_id}`.
5. Assert role theo dictionary.
6. `GET /dashboard/{dataset_id}`.
7. Assert dashboard domain theo dictionary.
8. Delete dictionary.
9. Assert semantic profile quay lại auto mapping.

### 8.5 Frontend checks

Run:

```bash
cd web
npm run build
```

Manual:

- Upload Superstore.
- Upload dictionary CSV khai báo `Sales -> revenue`.
- Smart Dashboard refresh.
- Semantic Mapping Studio hiển thị source `dictionary`.
- Edit role trong UI.
- Save.
- Delete dictionary.

## 9. Suggested implementation order

### Step 1 - Backend schema

- Thêm Pydantic models.
- Thêm database field `data_dictionary_json`.
- Thêm storage methods.

### Step 2 - Parser service

- Tạo `app/services/data_dictionary.py`.
- Implement CSV parser.
- Implement JSON parser.
- Implement normalize/validate.

### Step 3 - API endpoints

- `POST /datasets/{dataset_id}/data-dictionary`
- `GET /datasets/{dataset_id}/data-dictionary`
- `PUT /datasets/{dataset_id}/data-dictionary`
- `DELETE /datasets/{dataset_id}/data-dictionary`

### Step 4 - Semantic mapper integration

- Load dictionary trong `/semantic-profile`.
- Merge dictionary với overrides.
- Add source/reason/confidence label.

### Step 5 - Dashboard/agent integration

- Dashboard dùng semantic profile đã merge dictionary.
- Agent context dùng semantic profile đã merge dictionary.
- Cache key có semantic version mới.

### Step 6 - Tests

- Parser tests.
- Validation tests.
- Semantic mapper tests.
- API tests.

### Step 7 - Frontend

- API client.
- Types.
- Data Dictionary Panel.
- Mapping source display.
- Refresh dashboard after save/delete.

### Step 8 - Docs

- Cập nhật README ngắn.
- Tạo acceptance doc nếu cần:

```text
docs/18_phase_u1_data_dictionary_acceptance_vi.md
```

## 10. Acceptance checklist

Phase U1 hoàn thành khi:

- Upload dictionary CSV được.
- Upload dictionary JSON được.
- GET dictionary trả đúng dữ liệu đã lưu.
- PUT dictionary update được.
- DELETE dictionary reset được.
- Dictionary có column sai bị reject.
- Semantic profile dùng dictionary role.
- User override vẫn ưu tiên cao hơn dictionary.
- Dashboard refresh theo dictionary.
- Frontend hiển thị/edit dictionary.
- Tests pass.
- Frontend build pass.

## 11. Rủi ro và cách xử lý

### Rủi ro 1 - Dictionary sai làm dashboard sai

Cách xử lý:

- Hiển thị mapping source.
- Hiển thị warning data type mismatch.
- Cho reset dictionary.
- Cho user override lại role.

### Rủi ro 2 - User không biết semantic_role nên chọn gì

Cách xử lý:

- Dropdown semantic role.
- Gợi ý role từ auto candidates.
- Tooltip giải thích role.

### Rủi ro 3 - Dictionary format không nhất quán

Cách xử lý:

- Normalize field names.
- Cho phép alias:
  - `column`
  - `column_name`
  - `field`
  - `field_name`
- Return warning rõ ràng.

### Rủi ro 4 - Cache stale sau khi update dictionary

Cách xử lý:

- Tăng `semantic_version`.
- Invalidate semantic/dashboard/tool cache.
- Test cache invalidation.

## 12. Kết luận

Phase U1 là bước nền rất quan trọng để project tiến tới phân tích tốt nhiều loại CSV hơn.

Không cần tải thêm dataset mới từ web ở phase này. Chỉ cần:

- Dataset hiện có.
- Dictionary mẫu.
- Synthetic test data.

Sau khi U1 hoàn thành, các phase tiếp theo như Custom Metric Builder, Generic Insight Engine v2 và Universal Planner sẽ có nền semantic chắc hơn để xây dựng.
