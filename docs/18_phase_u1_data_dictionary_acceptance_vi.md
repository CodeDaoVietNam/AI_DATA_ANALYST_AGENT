# Phase U1 - Nghiệm Thu Data Dictionary Upload/Edit

## 1. Tóm tắt kết quả

Phase U1 đã được implement để thêm một lớp **Data Dictionary** vào hệ thống. Trước phase này, semantic mapper chủ yếu tự đoán ý nghĩa cột dựa trên tên cột, kiểu dữ liệu, pattern giá trị và domain prior. Sau phase này, user có thể trực tiếp mô tả ý nghĩa dữ liệu, ví dụ:

```text
amt       -> revenue
dt        -> date
prod_grp  -> category
cust_seg  -> segment
```

Điểm thay đổi quan trọng nhất:

- Hệ thống không còn chỉ "đoán" semantic role bằng heuristic.
- User có thể upload hoặc chỉnh Data Dictionary.
- Semantic profile ưu tiên Data Dictionary hơn auto-detection.
- User override vẫn là lớp ưu tiên cao nhất.
- Dashboard và AI Copilot có nền semantic đáng tin hơn với các CSV lạ.

## 2. Những gì đã implement

### 2.1 Backend Data Dictionary Service

Đã thêm service:

```text
app/services/data_dictionary.py
```

Service này xử lý:

- Parse Data Dictionary từ CSV.
- Parse Data Dictionary từ JSON.
- Normalize field rỗng, boolean, allowed values.
- Validate `column_name` phải tồn tại trong dataset.
- Reject duplicate dictionary fields.
- Convert dictionary thành semantic hints để semantic mapper sử dụng.

Format CSV hỗ trợ:

```csv
column_name,business_name,description,semantic_role,data_type,unit,aggregation,sensitive,allowed_values
Sales,Revenue,Total sales amount,revenue,number,USD,sum,false,
Order Date,Order Date,Date order was placed,date,date,,,
Segment,Customer Segment,Customer group,segment,string,,,
```

Format JSON hỗ trợ:

```json
{
  "domain": "retail",
  "fields": [
    {
      "column_name": "Sales",
      "business_name": "Revenue",
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

### 2.2 Schema/API Models

Đã thêm các Pydantic models trong:

```text
app/schemas/models.py
```

Models chính:

- `DataDictionaryField`
- `DataDictionary`
- `DataDictionaryResponse`

Các field được hỗ trợ:

- `column_name`
- `business_name`
- `description`
- `semantic_role`
- `data_type`
- `unit`
- `aggregation`
- `sensitive`
- `allowed_values`

### 2.3 Storage và database support

Đã thêm storage metadata cho Data Dictionary trong:

```text
app/database.py
app/services/storage.py
```

Thay đổi chính:

- `DatasetMetadata` có thêm `data_dictionary_json`.
- Có migration nhẹ bằng `ALTER TABLE` nếu database local đã tồn tại trước đó.
- `DatasetStore` có thêm:
  - `get_data_dictionary(dataset_id)`
  - `set_data_dictionary(dataset_id, dictionary)`
  - `clear_data_dictionary(dataset_id)`
- Khi dictionary thay đổi, `semantic_version` tăng lên để các cache semantic/dashboard/tool biết dữ liệu mapping đã đổi.

### 2.4 API endpoints mới

Đã thêm các endpoint:

```text
POST   /datasets/{dataset_id}/data-dictionary
GET    /datasets/{dataset_id}/data-dictionary
PUT    /datasets/{dataset_id}/data-dictionary
DELETE /datasets/{dataset_id}/data-dictionary
```

Ý nghĩa:

| Endpoint | Mục đích |
|---|---|
| `POST` | Upload dictionary file CSV/JSON |
| `GET` | Lấy dictionary hiện tại |
| `PUT` | Lưu/chỉnh dictionary bằng JSON |
| `DELETE` | Xóa dictionary |

Behavior:

- File chỉ chấp nhận `.csv` và `.json`.
- `column_name` không tồn tại trong dataset sẽ trả `400`.
- Khi save/delete dictionary:
  - tăng `semantic_version`
  - invalidate dataset cache
  - clear semantic cache

### 2.5 Semantic Mapper integration

Đã cập nhật:

```text
app/services/semantic_mapper.py
```

Semantic priority hiện tại:

```text
auto detection < data dictionary < user override
```

Ví dụ:

- Auto mapper đoán `Sales -> revenue` confidence 0.7.
- Data Dictionary khai báo `Sales -> profit`.
- Semantic profile sẽ dùng `Sales -> profit` với source `dictionary`.
- Nếu user override tiếp `Sales -> revenue`, source sẽ là `override` và override thắng dictionary.

Semantic profile hiện có thêm `source` cho role/candidate:

- `auto`
- `dictionary`
- `override`

Domain priority:

```text
auto-detected domain < dictionary domain < user domain override
```

Điều này giúp dataset có schema lạ nhưng user biết rõ domain vẫn render dashboard đúng hướng hơn.

### 2.6 Cache invalidation

Đã bổ sung:

```text
app/services/semantic_cache.py
```

Thêm hàm:

```text
clear_dataset_cache(dataset_id)
```

Khi Data Dictionary thay đổi:

- Semantic cache bị clear.
- Dataset cache bị invalidate.
- Dashboard request kế tiếp sẽ rebuild theo mapping mới.

### 2.7 Frontend Data Dictionary Panel

Đã nâng frontend React trong:

```text
web/src/App.tsx
web/src/api.ts
web/src/types.ts
```

Trong Smart Dashboard hiện có thêm panel **Data Dictionary**:

- Upload dictionary CSV/JSON.
- Hiển thị dictionary source.
- Chỉnh domain.
- Chỉnh từng field theo bảng:
  - business name
  - semantic role
  - data type
  - unit
  - aggregation
  - sensitive
  - allowed values
  - description
- Save dictionary.
- Delete/reset dictionary.
- Semantic Profile Debug hiển thị source mapping: `auto`, `dictionary`, `override`.

Frontend API client đã thêm:

- `getDataDictionary(datasetId)`
- `uploadDataDictionary(datasetId, file)`
- `saveDataDictionary(datasetId, dictionary)`
- `deleteDataDictionary(datasetId)`

## 3. Luồng hoạt động sau Phase U1

### 3.1 Luồng upload dataset bình thường

```text
User upload CSV/XLS/XLSX
  -> Backend parse dataframe
  -> Store raw parsed dataset
  -> Auto semantic mapper chạy như cũ
  -> Dashboard/AI Copilot dùng semantic profile auto
```

### 3.2 Luồng thêm Data Dictionary

```text
User upload hoặc chỉnh Data Dictionary
  -> Backend parse dictionary
  -> Validate column_name against dataset columns
  -> Save dictionary vào dataset metadata
  -> semantic_version tăng
  -> clear semantic/dashboard cache
  -> Dashboard refresh
  -> Semantic mapper dùng dictionary role/domain trước auto detection
```

### 3.3 Luồng user override sau dictionary

```text
Auto mapper đoán role
  -> Data Dictionary sửa role
  -> User override có thể sửa tiếp
  -> Semantic profile lấy user override làm kết quả cuối
```

## 4. Test đã thêm

### 4.1 Unit tests

Đã thêm:

```text
tests/test_data_dictionary.py
```

Coverage:

- Parse dictionary CSV.
- Parse dictionary JSON.
- Reject dictionary có cột không tồn tại.
- Convert dictionary sang semantic overrides.
- Dictionary override auto semantic mapper.
- User override thắng dictionary.

### 4.2 API tests

Đã thêm:

```text
tests/test_data_dictionary_api.py
```

Coverage:

- Upload dictionary CSV.
- GET dictionary.
- DELETE dictionary.
- PUT dictionary JSON.
- Semantic profile dùng role từ dictionary.
- Dashboard dùng domain từ dictionary.
- Reject unknown column qua API.

## 5. Verification

### 5.1 Backend tests

Lệnh đã chạy:

```bash
/home/ductien/miniconda3/envs/reis/bin/python -m pytest -q
```

Kết quả:

```text
91 passed, 1 warning
```

Warning còn lại đến từ dependency `requests/urllib3/chardet` trong môi trường hiện tại, không phải failure của Phase U1.

### 5.2 Frontend build

Lệnh đã chạy:

```bash
cd web
npm run build
```

Kết quả:

```text
✓ built
```

Vite có cảnh báo bundle lớn do Plotly bundle, đây là warning đã dự đoán được và không làm build fail.

## 6. Cách test thủ công

### 6.1 Chạy backend

```bash
uvicorn app.main:app --reload
```

### 6.2 Chạy React frontend

```bash
cd web
npm run dev
```

### 6.3 Test với Superstore

Upload:

```text
data/raw/sample_-_superstore.xls
```

Tạo dictionary CSV mẫu:

```csv
column_name,business_name,description,semantic_role,data_type,unit,aggregation,sensitive,allowed_values
Sales,Revenue,Total sales amount,revenue,number,USD,sum,false,
Order Date,Order Date,Date order was placed,date,date,,,
Category,Product Category,Product category,category,string,,count,false,
Segment,Customer Segment,Customer segment,segment,string,,count,false,
Profit,Profit,Net profit,profit,number,USD,sum,false,
Discount,Discount,Discount rate,discount,number,percent,mean,false,
State,State,Shipping state,state,string,,count,false,
```

Kỳ vọng:

- Semantic profile domain là `retail` nếu dictionary có domain qua JSON hoặc user chọn trong UI.
- `Sales` được map thành `revenue`.
- `Profit` được map thành `profit`.
- Dashboard refresh theo mapping mới.

### 6.4 Test với dataset có tên cột khó hiểu

Ví dụ dataset có cột:

```text
amt, dt, prod_grp, cust_seg
```

Dictionary:

```csv
column_name,business_name,description,semantic_role,data_type,unit,aggregation,sensitive,allowed_values
amt,Revenue,Total order amount,revenue,number,USD,sum,false,
dt,Order Date,Order date,date,date,,,
prod_grp,Product Group,Product category,category,string,,count,false,
cust_seg,Customer Segment,Customer segment,segment,string,,count,false,
```

Kỳ vọng:

- Auto mapper có thể không chắc, nhưng dictionary ép mapping đúng.
- Dashboard và Copilot hiểu `amt` là revenue thay vì chỉ là một numeric column bất kỳ.

## 7. Cảm nhận sự thay đổi

Phase U1 làm project chuyển từ kiểu:

```text
Hệ thống tự đoán ý nghĩa cột.
```

sang kiểu:

```text
Hệ thống có thể được user dạy ý nghĩa dữ liệu.
```

Đây là một bước rất quan trọng nếu muốn tiến tới "mọi CSV đều phân tích tốt". Với CSV thực tế, tên cột thường không sạch, không chuẩn, bị viết tắt, hoặc mang ngôn ngữ nội bộ của doanh nghiệp. Không có Data Dictionary thì hệ thống sẽ luôn có trần chất lượng vì semantic mapper chỉ có thể đoán.

Sau phase này:

- Dashboard đáng tin hơn với dataset lạ.
- AI Copilot có ngữ cảnh nghiệp vụ rõ hơn.
- User kiểm soát được semantic mapping thay vì phụ thuộc vào heuristic.
- Các phase sau như Metric Builder, Universal Planner và Evaluation Suite có nền metadata tốt hơn.

Nói ngắn gọn: U1 không làm dashboard "đẹp hơn" ngay lập tức, nhưng làm hệ thống "hiểu dữ liệu đúng hơn". Đây là nền rất sâu cho các tính năng AI/BI về sau.

## 8. Giới hạn còn lại

Phase U1 vẫn còn một số giới hạn:

- Chưa có version history cho Data Dictionary.
- Chưa có import/export dictionary template từ UI.
- Chưa có validation nâng cao theo `data_type`, `allowed_values`, `unit`.
- Chưa có metric builder dùng dictionary aggregation/unit.
- Chưa có workspace/user ownership cho dictionary.
- Dictionary hiện lưu trong metadata runtime/database local, chưa phải production-grade governance.
- Chưa có audit log ai chỉnh mapping lúc nào.
- Chưa có eval suite nhiều dataset để đo accuracy semantic mapper trước/sau dictionary.

## 9. Gợi ý bước tiếp theo

Sau U1, thứ tự hợp lý là:

1. **U2 - Custom Metric Builder**
   - Cho user định nghĩa metric như `margin = profit / revenue`.
   - Tận dụng role/unit/aggregation từ Data Dictionary.

2. **U3 - Generic Insight Engine v2**
   - Tự tìm trend, anomaly, segment difference, outlier.
   - Dùng semantic role thay vì hard-code từng domain.

3. **U4 - Universal Planner Intent Schema**
   - Chuẩn hóa câu hỏi user thành intent:
     - metric
     - dimension
     - time grain
     - filter
     - comparison
   - Agent chọn tool dựa trên intent thay vì prompt tự do.

4. **U5 - Evaluation Suite 20-50 CSV**
   - Test nhiều domain để biết hệ thống fail ở đâu.
   - Đo semantic mapping accuracy, dashboard coverage, answer correctness.

## 10. Definition of Done

Phase U1 được xem là hoàn thành khi:

- Backend parse được Data Dictionary CSV/JSON.
- API upload/get/update/delete dictionary hoạt động.
- Dictionary validate theo dataset columns.
- Semantic mapper ưu tiên dictionary hơn auto detection.
- User override vẫn thắng dictionary.
- Cache semantic/dashboard được invalidate khi dictionary đổi.
- Frontend có panel upload/edit/save/delete dictionary.
- Semantic debug hiển thị mapping source.
- Backend tests pass.
- Frontend build pass.

Tình trạng hiện tại:

```text
Done.
```
