# Tong quan du an: AI Data Analyst Agent Starter

## 1. Du an nay la gi?

`AI Data Analyst Agent Starter` la mot starter project de xay dung mot san pham AI Data Analyst Agent theo huong production-style.

Y tuong cot loi:

```text
Nguoi dung upload file CSV
  -> he thong doc va kiem tra du lieu
  -> Pandas tinh toan thong ke that
  -> backend tra ve summary, missing values, duplicate rows, goi y phan tich
  -> frontend hien thi ket qua
  -> nguoi dung co the chat cac cau hoi don gian voi dataset
  -> he thong tao bao cao EDA dang Markdown
```

Du an duoc thiet ke nhu mot nen mong de hoc va mo rong thanh agent phan tich du lieu co LLM, tool calling, LangChain hoac LangGraph. Phien ban hien tai uu tien lop phan tich deterministic bang Python/Pandas truoc, sau do moi dua LLM vao de giai thich va dieu phoi tool.

## 2. Bai toan du an giai quyet

Nhieu nguoi hoc machine learning biet train model, nhung chua quen cach bien nang luc AI/data thanh mot san pham hoan chinh co API, UI, luu tru, validation, bao cao va kha nang mo rong. Du an nay giai quyet khoang cach do bang mot ung dung cu the:

- Nhan du lieu dang CSV tu nguoi dung.
- Tu dong profiling dataset.
- Phat hien kieu cot: numeric, datetime, categorical, text.
- Dem missing values va ty le missing theo cot.
- Dem dong trung lap.
- Tao thong ke EDA co ban cho cot numeric.
- Tao thong ke cho cot categorical neu duoc nhan dien la categorical.
- Goi y nhung huong phan tich nen lam tiep.
- Cho phep hoi dap don gian bang ngon ngu tu nhien.
- Sinh report Markdown de tai ve hoac doc truc tiep.

Van de quan trong nhat ma project nhan manh la:

```text
LLM khong nen tu boi ra so lieu.
Moi con so phai duoc tinh bang cong cu that nhu Python/Pandas.
LLM chi nen lap ke hoach, chon tool, giai thich va trinh bay ket qua sau khi tool da tinh xong.
```

Day la nguyen tac rat quan trong khi xay dung AI agent cho data analysis, vi nguoi dung co the dua ra quyet dinh kinh doanh dua tren cac con so nay.

## 3. Boi canh hoc tap va gia tri portfolio

Du an nay phu hop voi nguoi muon chung minh nang luc AI Engineering, khong chi data science don le.

Nhung ky nang duoc the hien:

- Python engineering voi module ro rang.
- Data analysis bang Pandas va NumPy.
- Xay dung REST API bang FastAPI.
- Xay UI demo bang Streamlit.
- Dinh nghia schema response/request bang Pydantic.
- Thiet ke agent theo huong tool-based.
- Guardrails de tranh hallucination va han che hanh vi nguy hiem.
- Docker/Docker Compose de chay backend va frontend.
- Unit test co ban cho data profiler.
- Tu duy product: upload, xem summary, chat, export report.

Neu dua vao CV, project co the duoc mo ta nhu:

> Built an AI Data Analyst Agent that allows users to upload CSV files, automatically performs EDA, generates charts, extracts insights, and supports natural-language Q&A over tabular data using Pandas-based tools and an extensible agent architecture.

## 4. Kien truc tong quan

Kien truc hien tai:

```text
User
  |
  v
Streamlit Frontend
  |
  v
FastAPI Backend
  |
  v
Dataset Storage
  |
  v
DataAnalystAgent
  |
  +-- Profiler Service
  |     +-- infer_column_types
  |     +-- profile_dataframe
  |     +-- recommend_analysis
  |
  +-- Pandas Tool
  |     +-- answer_simple_question
  |
  +-- Report Generator
  |     +-- generate_markdown_report
  |
  +-- Chart Generator
        +-- generate_chart_spec
```

Phien ban hien tai chua tich hop LLM that. `DataAnalystAgent` dang la wrapper rule-based, dung de tap trung vao workflow dung:

```text
Cau hoi cua user
  -> rule-based intent matching
  -> Pandas tinh ket qua
  -> tra ve cau tra loi va data
```

Sau nay co the thay rule-based router bang LLM tool calling hoac LangGraph workflow.

## 5. Cac thanh phan chinh trong codebase

### 5.1 Backend FastAPI

File chinh: `app/main.py`

Backend cung cap cac endpoint:

- `GET /`: health check.
- `POST /upload`: upload CSV, doc bang Pandas, luu vao storage, tra ve `dataset_id`.
- `GET /summary/{dataset_id}`: profiling dataset.
- `POST /chat`: hoi dap don gian voi dataset da upload.
- `GET /report/{dataset_id}`: tao Markdown report.

Backend hien tai chap nhan moi origin qua CORS, phu hop demo/dev, nhung can sieu chat hon neu dua len production.

### 5.2 Storage

File chinh: `app/services/storage.py`

`DatasetStore` luu file upload vao:

```text
data/uploads/{dataset_id}.csv
```

Moi dataset co mot UUID rieng. Metadata filename/path duoc giu trong memory dictionary. Neu app restart, file CSV van con tren disk, nhung filename goc co the mat vi metadata memory khong con. Khi do `get_filename()` co the tra ve `unknown.csv`.

### 5.3 Profiler

File chinh: `app/services/profiler.py`

Day la trai tim deterministic cua project. Cac viec no lam:

- `infer_column_types(df)`: suy luan kieu cot.
- `profile_dataframe(df)`: tao summary tong hop.
- `recommend_analysis(df, column_types)`: goi y huong phan tich tiep theo.

Output cua profiler gom:

- shape: so dong, so cot.
- columns: danh sach cot.
- column_types: kieu cot duoc suy luan.
- missing_values: so missing theo cot.
- missing_percent: ty le missing theo cot.
- duplicate_rows: so dong bi trung.
- numeric_summary: count, mean, std, min, quartile, max.
- categorical_summary: unique values va top values neu cot la categorical.
- recommendations: goi y phan tich.

Luu y thuc te: logic categorical hien tai dung dieu kien:

```python
series.nunique(dropna=True) / max(len(series), 1) < 0.3
```

Vi la `< 0.3`, sample data co `Category` va `City` moi cot co 3 gia tri unique tren 10 dong, ty le bang `0.3`, nen chung duoc phan loai la `text` chu khong phai `categorical`. Neu muon hai cot nay thanh categorical, co the doi nguong thanh `<= 0.3` hoac mot rule linh hoat hon.

### 5.4 Rule-based Agent

File chinh: `app/services/agent.py`

`DataAnalystAgent` hien tai co hai method:

- `profile(df)`: goi profiler.
- `chat(df, question)`: goi pandas tool de tra loi cau hoi don gian.

Day chua phai agent LLM dung nghia. No la starter agent co chu y: don gian, ro rang, de test, va tranh viec LLM hallucinate so lieu.

### 5.5 Pandas Tool

File chinh: `app/tools/pandas_tool.py`

`answer_simple_question(df, question)` match keyword de tra loi:

- Cau hoi co `missing`, `null`, `thieu`: tra ve missing values theo cot.
- Cau hoi co `duplicate`, `trung`: tra ve so dong trung lap.
- Cau hoi co `shape`, `bao nhieu dong`, `so dong`: tra ve so dong/so cot.
- Cau hoi co `column`, `cot`: tra ve danh sach cot.
- Cac cau hoi khac: fallback, thong bao can nang cap LLM tool-calling.

Vi day la rule-based engine, no khong hieu sau ngu nghia, khong groupby linh hoat, khong tinh correlation theo cau hoi tu nhien, va khong sinh chart tu chat.

### 5.6 Chart Generator

File chinh: `app/services/chart_generator.py`

Module nay da co ham tao chart spec bang Plotly:

- bar chart.
- line chart.
- scatter chart.
- histogram.
- box plot.

Ham co validate column truoc khi ve chart. Tuy nhien, endpoint FastAPI va Streamlit UI hien tai chua ket noi truc tiep chart generator vao flow chat/report. No la nen tang san co de nang cap.

### 5.7 Report Generator

File chinh: `app/services/report_generator.py`

`generate_markdown_report(filename, summary)` tao EDA report Markdown gom:

- Dataset overview.
- Columns va inferred types.
- Missing values.
- Recommended analysis.
- Notes ve viec report duoc tao tu Pandas deterministic analysis.

### 5.8 Frontend Streamlit

File chinh: `frontend/streamlit_app.py`

Frontend hien tai cho phep:

- Upload CSV.
- Goi backend `/upload`.
- Lay dataset summary tu `/summary/{dataset_id}`.
- Hien thi metric rows, columns, duplicate rows.
- Hien thi column types.
- Hien thi bang missing values.
- Hien thi recommended analysis.
- Chat voi dataset qua `/chat`.
- Generate va download Markdown report qua `/report/{dataset_id}`.

Day la UI demo nhanh, phu hop cho portfolio hoac test local.

### 5.9 CLI Script

File chinh: `scripts/analyze.py`

Script nay cho phep phan tich CSV khong can chay server:

```bash
PYTHONPATH=. python scripts/analyze.py data/sample/ecommerce_sales.csv --out reports
```

Output:

- `reports/summary.json`
- `reports/eda_report.md`

Luu y: neu chay `python scripts/analyze.py ...` truc tiep trong moi truong hien tai, co the gap loi `ModuleNotFoundError: No module named 'app'`. Cach chay on dinh la them `PYTHONPATH=.` nhu lenh tren, hoac cai project theo editable package neu sau nay bo sung packaging.

## 6. Du lieu mau va ket qua thuc te

File mau: `data/sample/ecommerce_sales.csv`

Dataset mau co 10 dong va 7 cot:

- `Date`
- `Category`
- `City`
- `Revenue`
- `COGS`
- `Orders`
- `Rating`

Ket qua profiler thuc te tren sample:

- Rows: 10.
- Columns: 7.
- Duplicate rows: 0.
- Missing values: 0 o tat ca cot.
- `Date`: datetime.
- `Revenue`: numeric.
- `COGS`: numeric.
- `Orders`: numeric.
- `Rating`: numeric.
- `Category`: text theo rule hien tai.
- `City`: text theo rule hien tai.

Numeric summary noi bat:

- `Revenue`: mean 1,880,000; min 900,000; max 3,200,000.
- `COGS`: mean 1,220,000; min 500,000; max 2,500,000.
- `Orders`: mean 11.1; min 6; max 17.
- `Rating`: mean 4.49; min 4.0; max 4.9.

Recommended analysis tren sample:

- Analyze trend over time using `Date` and `Revenue`.
- Check correlation between numeric columns.

Khi chay CLI trong moi truong hien tai, profiler co canh bao Pandas ve datetime inference:

```text
Could not infer format, so each element will be parsed individually
```

Day khong lam script that bai, nhung la dau hieu nen cai tien logic parse datetime bang cach chi parse cac cot co kha nang ngay thang, hoac truyen format neu biet truoc.

## 7. Cach chay project

### 7.1 Cai dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 7.2 Chay backend

```bash
uvicorn app.main:app --reload
```

Backend mac dinh:

```text
http://localhost:8000
```

### 7.3 Chay frontend

```bash
streamlit run frontend/streamlit_app.py
```

Frontend mac dinh:

```text
http://localhost:8501
```

### 7.4 Chay bang Docker Compose

```bash
docker compose up --build
```

Docker Compose se chay:

- Backend tai port `8000`.
- Frontend tai port `8501`.
- Frontend goi backend qua `BACKEND_URL=http://backend:8000`.

### 7.5 Chay CLI phan tich file CSV

```bash
PYTHONPATH=. python scripts/analyze.py data/sample/ecommerce_sales.csv --out reports
```

## 8. API surface

### `GET /`

Dung de kiem tra API co dang chay khong.

Response mau:

```json
{
  "status": "ok",
  "message": "AI Data Analyst Agent API is running."
}
```

### `POST /upload`

Nhan file CSV multipart form-data. Neu file khong phai `.csv`, backend tra ve loi 400.

Response gom:

- `dataset_id`
- `filename`
- `rows`
- `columns`
- `message`

### `GET /summary/{dataset_id}`

Tra ve summary tu profiler.

### `POST /chat`

Request:

```json
{
  "dataset_id": "...",
  "question": "Dataset co bao nhieu dong?"
}
```

Response:

```json
{
  "answer": "...",
  "data": {},
  "chart": null
}
```

### `GET /report/{dataset_id}`

Tra ve Markdown report:

```json
{
  "dataset_id": "...",
  "report_markdown": "# EDA Report: ..."
}
```

## 9. Nhung gi project da lam duoc

Project hien tai da co MVP kha day du:

- Upload CSV qua API va UI.
- Luu dataset bang UUID.
- Profile dataset bang Pandas.
- Missing value report.
- Duplicate row detection.
- Type inference.
- Numeric summary.
- Basic recommendation engine.
- Rule-based chat cho cac cau hoi co ban.
- Markdown report generation.
- Streamlit demo UI.
- Dockerfile va docker-compose.
- Unit test co ban cho profiler.
- Tai lieu learning path va upgrade path.

## 10. Nhung gioi han hien tai

Can hieu ro cac gioi han nay de khong danh gia sai project:

- Chua co LLM integration that.
- Chua co LangChain/LangGraph.
- Chat chi la keyword matching, chua phai natural language understanding that.
- Chart generator co san nhung chua duoc expose qua API/UI.
- Storage metadata nam trong memory, restart server co the mat filename goc.
- Chua co gioi han upload size.
- Chua co authentication/authorization.
- CORS dang mo `*`.
- Chua co logging va error handling production-grade.
- Chua co validation phuc tap cho CSV schema.
- Chua co protection rieng cho du lieu nhay cam.
- Test coverage con rat mong.
- CLI can `PYTHONPATH=.` neu chua setup package.
- Type inference categorical hien tai co the qua chat voi dataset nho.

## 11. Nen nang cap theo huong AI Engineering nhu the nao?

Co. Neu muc tieu la bien project nay thanh mot AI Engineering portfolio project nghiem tuc, thi can nang cap tu "data analysis app co rule-based chat" thanh "AI Data Analyst Agent co LLM, tool calling va guardrails".

Dieu quan trong la khong phai them LLM de no tu tinh toan. Cach dung dung la:

```text
User hoi bang ngon ngu tu nhien
  -> LLM hieu y dinh va chon tool
  -> backend validate input
  -> Pandas/Plotly tinh toan hoac ve chart
  -> LLM giai thich ket qua bang ngon ngu de hieu
  -> frontend hien thi answer, data, chart, report
```

### 11.1 Muc tieu nang cap

Sau khi nang cap, project nen chung minh duoc cac nang luc AI Engineering sau:

- LLM integration that, vi ten project la AI Data Analyst Agent.
- Tool calling de agent khong hallucinate so lieu.
- Structured output bang JSON/Pydantic de backend co the validate.
- Guardrails cho column name, file size, chart type, aggregation type.
- Agent workflow ro rang: classify intent, select tool, run tool, validate result, explain.
- UI hien thi duoc ket qua phan tich, chart va insight.
- Report generation co LLM nhung chi dua tren statistics do Pandas tinh.
- Logging, error handling va test coverage tot hon.

### 11.2 Co can LangChain/LangGraph khong?

Khong bat buoc, nhung nen co neu ban muon project nhin dung chat AI Engineering.

Dung OpenAI tool calling truc tiep la du cho MVP:

```text
FastAPI -> OpenAI Responses/Chat API -> tool schemas -> Pandas tools -> final answer
```

Dung LangChain khi ban muon:

- define tools nhanh.
- quan ly prompt/templates.
- tach chain thanh cac buoc ro rang.
- de nguoi review thay ban biet ecosystem AI agent.

Dung LangGraph khi ban muon:

- workflow co trang thai ro rang.
- kiem soat tung buoc cua agent.
- co node validate truoc/sau khi chay tool.
- de debug agent tot hon.
- demo mot AI agent khong phai black box.

Recommendation cho project nay:

```text
Phase AI 1: OpenAI/LangChain tool calling
Phase AI 2: LangGraph workflow
Phase AI 3: production guardrails + tests + observability
```

### 11.3 AI architecture nen huong toi

Kien truc sau nang cap:

```text
Streamlit UI
  -> FastAPI
  -> DatasetStore
  -> Agent Orchestrator
      -> Intent Classifier Node
      -> Tool Selection Node
      -> Tool Validation Node
      -> Pandas Tool Executor
      -> Chart Tool Executor
      -> Result Validation Node
      -> LLM Explanation Node
  -> Response: answer + data + chart + warnings + reasoning_summary
```

Trong do:

- `Intent Classifier Node`: hieu cau hoi thuoc loai nao.
- `Tool Selection Node`: chon tool phu hop.
- `Tool Validation Node`: dam bao cot/aggregation/chart hop le.
- `Pandas Tool Executor`: tinh toan so lieu that.
- `Chart Tool Executor`: tao Plotly chart spec.
- `Result Validation Node`: dam bao ket qua khong rong, khong loi schema.
- `LLM Explanation Node`: giai thich ket qua, khong tu tao so moi.

### 11.4 Bo tool nen co

Nang cap tu `answer_simple_question` thanh cac tool nho, ro nghia:

- `get_dataset_overview(dataset_id)`
- `get_column_profile(dataset_id, column)`
- `get_missing_values(dataset_id)`
- `get_duplicate_rows(dataset_id)`
- `groupby_aggregate(dataset_id, group_by, metric, aggregation)`
- `filter_rows(dataset_id, filters)`
- `sort_top_n(dataset_id, metric, n, group_by)`
- `correlation_analysis(dataset_id, columns)`
- `detect_outliers(dataset_id, column, method)`
- `generate_chart(dataset_id, chart_type, x, y, aggregation)`
- `generate_eda_report(dataset_id)`

Moi tool nen co schema Pydantic rieng de validate input. Vi du:

```json
{
  "tool_name": "groupby_aggregate",
  "arguments": {
    "group_by": "Region",
    "metric": "Sales",
    "aggregation": "sum"
  }
}
```

### 11.5 Prompt nen su dung sau khi co LLM

System prompt nen giu nguyen tac:

```text
You are an AI Data Analyst Agent.
Never invent numbers.
For every numerical answer, call an approved tool.
Only explain results after tool output is available.
If a requested column does not exist, say it clearly.
If the dataset is insufficient, explain what is missing.
Return concise Vietnamese explanations for end users.
```

Output sau cung nen co format:

```json
{
  "answer": "...",
  "data": {},
  "chart": {},
  "warnings": [],
  "next_steps": []
}
```

### 11.6 Cac cau hoi demo nen tra loi duoc

Khi nang cap xong, agent nen xu ly duoc cac cau hoi nhu:

- "Doanh thu theo thang thay doi nhu the nao?"
- "Category nao co loi nhuan cao nhat?"
- "Region nao dang bi profit am?"
- "Discount co anh huong den profit khong?"
- "Top 10 san pham theo revenue la gi?"
- "Cot nao missing nhieu nhat?"
- "Ve chart sales theo thang."
- "Hay tao mot executive summary cho dataset nay."
- "Co dau hieu outlier trong Sales khong?"
- "Nen phan tich gi tiep theo?"

## 12. Dataset nen dung cho project nay

File `data/sample/ecommerce_sales.csv` hien tai rat tot de test nhanh, nhung qua nho de demo AI Data Analyst Agent. Nen giu no lam sample nho, dong thoi them mot hoac hai dataset lon hon trong `data/sample` hoac huong dan download trong docs.

Tieu chi chon dataset:

- Co toi thieu vai nghin dong de analysis co y nghia.
- Co datetime column de phan tich trend.
- Co numeric columns nhu sales, revenue, profit, quantity, discount.
- Co categorical columns nhu category, product, region, country, segment.
- Co kha nang tao chart va groupby.
- Co license ro rang.
- Khong chua PII nhay cam nhu email, phone, dia chi nha that.

### Dataset 1 - UCI Online Retail

Link: https://archive.ics.uci.edu/dataset/352/online%2Bretail

Nen chon lam dataset chinh neu ban muon du lieu gan voi thuc te nhat.

Thong tin chinh:

- Nguon: UCI Machine Learning Repository.
- Ten: Online Retail.
- File: `Online Retail.xlsx`, khoang 22.6 MB.
- Quy mo: hon 540k giao dich.
- Domain: online retail cua mot UK-based non-store retailer.
- Cot quan trong: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`.
- License: Creative Commons Attribution 4.0 International.
- Co DOI/citation ro rang.

Ly do phu hop:

- Co transaction data that hon dataset synthetic.
- Co datetime de trend analysis.
- Co product/customer/country de segmentation.
- Co `Quantity` va `UnitPrice` de tinh revenue.
- Co cancellation invoice, missing customer, country, product description: rat tot de demo data quality.

Cac cau hoi demo:

- "Doanh thu theo thang la bao nhieu?"
- "Quoc gia nao co doanh thu cao nhat?"
- "San pham nao ban chay nhat?"
- "Ty le transaction bi cancel la bao nhieu?"
- "Khach hang nao co gia tri mua hang cao nhat?"
- "Co missing values o CustomerID khong?"

Feature engineering nen them:

```text
Revenue = Quantity * UnitPrice
InvoiceMonth = month(InvoiceDate)
IsCancellation = InvoiceNo startswith "C"
```

### Dataset 2 - UCI Online Retail II

Link: https://archive.ics.uci.edu/ml/datasets/Online%20Retail%20II

Nen chon neu muon demo voi dataset lon hon va co tinh time-series manh hon.

Thong tin chinh:

- Nguon: UCI Machine Learning Repository.
- Ten: Online Retail II.
- File: `online_retail_II.xlsx`, khoang 43.5 MB.
- Quy mo: hon 1.06M transactions.
- Khoang thoi gian: 01/12/2009 den 09/12/2011.
- Domain: UK-based online retail.
- Co missing values.
- License: Creative Commons Attribution 4.0 International.

Ly do phu hop:

- Dataset du lon de test performance, upload limit, background processing.
- Co 2 nam transaction de phan tich seasonality.
- Tot de demo customer segmentation/RFM sau nay.

Luu y:

- File lon hon, co the can xu ly upload size va async processing.
- Dinh dang XLSX, trong khi app hien chi support CSV. Nen convert sang CSV truoc, hoac nang cap app support Excel.

### Dataset 3 - Kaggle E-commerce Orders and Sales Performance Dataset

Link: https://www.kaggle.com/datasets/zahranusratt/e-commerce-orders-and-sales-performance-dataset

Nen chon lam dataset demo de bat dau nhanh vi nhe va dung domain.

Thong tin chinh:

- Nguon: Kaggle.
- Khoang 3,500 records.
- Cac cot: `Order Date`, `Product Name`, `Category`, `Region`, `Quantity`, `Sales`, `Profit`.
- Khoang thoi gian: 2022 den 2024.
- License: CC0 Public Domain theo metadata Kaggle.

Ly do phu hop:

- Nho gon, de commit vao repo neu license cho phep.
- Cot ro rang, dung voi cac tool can xay: trend, groupby, top N, profit analysis.
- Rat hop de demo voi Streamlit ma khong bi nang.

Cac cau hoi demo:

- "Sales theo thang nam 2024 nhu the nao?"
- "Category nao profit cao nhat?"
- "Region nao co quantity lon nhat?"
- "San pham nao nen uu tien ban tiep?"

### Dataset 4 - Kaggle Superstore Sales Dataset

Link: https://www.kaggle.com/datasets/aashwinkumar/superstore-sales-dataset

Nen chon neu muon demo business analytics day du hon.

Thong tin chinh:

- Nguon: Kaggle.
- Format: CSV.
- Size khoang 2.17 MB.
- Cac cot quan trong: `order_id`, `order_date`, `ship_date`, `ship_mode`, `customer_name`, `segment`, `state`, `country`, `market`, `region`, `product_id`, `category`, `sub_category`, `product_name`, `sales`, `quantity`, `discount`, `profit`, `shipping_cost`, `order_priority`, `year`.
- License: Apache 2.0 theo metadata Kaggle.

Ly do phu hop:

- Co sales, profit, discount, shipping cost.
- Co region/market/category/sub-category.
- Rat tot de demo dashboard, chart recommendation va business insight.
- Co the hoi nhieu cau hoi phan tich thuc te hon dataset 7 cot.

Cac cau hoi demo:

- "Discount co lam profit giam khong?"
- "Sub-category nao dang lo nhieu nhat?"
- "Market nao co shipping cost cao?"
- "Segment nao mang lai doanh thu tot nhat?"
- "Ve scatter chart giua discount va profit."

### Dataset 5 - Kaggle E-Commerce Sales Dataset

Link: https://www.kaggle.com/datasets/thedevastator/unlock-profits-with-e-commerce-sales-data/data

Nen chon neu muon dataset phuc tap hon ve ecommerce operations.

Thong tin chinh:

- Nguon: Kaggle.
- Gom nhieu file CSV.
- Co sales channel, SKU, stock, category, size, color, MRP theo platform, amount, quantity, gross amount va cac thong tin lien quan loi nhuan.

Ly do phu hop:

- Tot cho multi-file analysis sau nay.
- Co the mo rong agent thanh "compare files" hoac "join datasets".
- Gan voi bai toan ecommerce operation hon la dataset mau don gian.

Luu y:

- Phuc tap hon, khong nen dung lam dataset dau tien.
- Nen dung sau khi app co multi-file support.

### Khuyen nghi chon dataset cho repo nay

Nen dung 3 cap dataset:

```text
Level 1 - Small demo:
  data/sample/ecommerce_sales.csv hien tai

Level 2 - Main portfolio demo:
  Kaggle E-commerce Orders and Sales Performance Dataset
  hoac Kaggle Superstore Sales Dataset

Level 3 - Realistic advanced demo:
  UCI Online Retail
  hoac UCI Online Retail II
```

Lua chon thuc te nhat:

```text
Dataset chinh nen dung: Kaggle Superstore Sales Dataset
Dataset nang cao nen ho tro: UCI Online Retail
```

Ly do:

- Superstore co san CSV, nhe, nhieu cot business, de demo chart/report/LLM insights.
- UCI Online Retail that hon va lon hon, phu hop khi nang cap performance, cleaning va customer analytics.

## 13. Nguyen tac thiet ke quan trong

Du an nay nen duoc phat trien theo cac nguyen tac:

### 13.1 Tinh toan bang tool, giai thich bang LLM

Dung:

```text
Pandas tinh ket qua -> LLM giai thich ket qua
```

Sai:

```text
LLM tu doc cau hoi va tu doan con so
```

### 13.2 Predefined tools tot hon Python REPL tu do

Khong nen cho agent chay code Python bat ky do user hoac model tao ra. Nen tao cac tool an toan:

- `get_dataset_overview`
- `get_missing_values`
- `groupby_aggregate`
- `generate_chart`
- `detect_outliers`
- `correlation_analysis`

Moi tool can validate:

- dataset_id co ton tai khong.
- column name co ton tai khong.
- aggregation co nam trong danh sach cho phep khong.
- chart type co duoc support khong.

### 13.3 Structured output

Khi them LLM, nen yeu cau output JSON co schema ro rang, vi backend can parse de hien thi:

```json
{
  "summary": "...",
  "insights": ["..."],
  "warnings": ["..."],
  "next_steps": ["..."]
}
```

## 14. Lo trinh nang cap de thanh AI Data Analyst Agent that

### Phase 1: Lam chac deterministic EDA engine

- Cai tien type inference.
- Them categorical summary linh hoat hon.
- Them correlation matrix.
- Them outlier detection.
- Them data quality score.
- Them tests cho edge cases: empty CSV, missing heavy, duplicate, mixed types.

### Phase 2: Ket noi chart generator

- Them endpoint `/chart`.
- Cho frontend hien thi Plotly chart.
- De agent goi chart tool khi cau hoi yeu cau visualization.
- Recommend chart dua tren schema.

### Phase 3: Nang cap chat router

- Thay keyword matching bang intent classifier.
- Co the ban dau van khong can LLM: dung regex/rule tot hon.
- Sau do them LLM structured output de classify intent.

### Phase 4: LLM insight generator

- Gui summary do Pandas tinh sang LLM.
- Yeu cau LLM chi giai thich dua tren JSON co san.
- Validate response bang Pydantic.
- Hien thi summary, insights, warnings, next steps tren UI.

### Phase 5: Tool-calling agent

- Dinh nghia tool schemas.
- Cho LLM chon tool phu hop.
- Backend validate tool args.
- Tool tinh ket qua that.
- LLM tong hop cau tra loi cuoi.

### Phase 6: LangGraph workflow

Khi workflow phuc tap hon, co the dung graph:

```text
START
  -> classify intent
  -> validate columns
  -> select tool
  -> run tool
  -> validate result
  -> generate explanation
  -> END
```

### Phase 7: Production polish

- Auth.
- Upload size limit.
- Persistent metadata database.
- Background jobs cho file lon.
- Logging.
- Monitoring.
- Rate limiting.
- Better test coverage.
- Deployment docs.
- Screenshots va demo video.

## 15. Cach hieu dung ve ten "Agent" trong project nay

Ten project la `AI Data Analyst Agent Starter`, nhung ban nen hieu chu "Starter" rat quan trong.

Hien tai:

```text
Agent = wrapper rule-based + Pandas tools
```

Muc tieu sau khi nang cap:

```text
Agent = LLM + tools + memory/context + planning loop + guardrails
```

Cach lam nay tot cho nguoi hoc vi no tach hai lop:

- Lop tinh toan dang tin cay: Pandas, API, schema, report.
- Lop tri tue ngon ngu: LLM chon tool va giai thich ket qua.

Neu them LLM qua som, nguoi hoc de bi lech sang prompt engineering ma chua co nen tang data workflow vung.

## 16. Ket luan ngan gon

Du an nay la mot nen tang tot de hoc cach xay mot AI data product thuc te. No khong chi la notebook phan tich du lieu, ma gom ca backend, frontend, storage, API contract, report generation, Docker va huong mo rong sang LLM agent.

Gia tri lon nhat cua project nam o triet ly:

```text
So lieu phai den tu computation that.
LLM chi nen giup hieu, giai thich, dieu phoi va trinh bay.
```

Neu tiep tuc phat trien dung huong, project nay co the tro thanh mot portfolio project manh cho AI Engineer/Data Engineer junior: vua co tinh ung dung, vua cho thay hieu biet ve rui ro hallucination, guardrails va thiet ke agent dua tren tool.
