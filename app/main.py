import json
import time
import uuid

import structlog
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import APIKeyHeader

from app.config import settings
from app.database import init_database
from app.services.storage import dataset_store
from app.services.agent import DataAnalystAgent
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.dashboard_builder import build_dashboard
from app.services.cache_manager import dashboard_cache, invalidate_dataset_cache, semantic_profile_cache, stable_cache_key
from app.services.data_loader import load_tabular_file
from app.services.dataset_pipeline import prepare_amazon_sales_dataframe
from app.services.chart_generator import generate_chart_spec
from app.services.report_generator import generate_markdown_report
from app.services.data_dictionary import parse_data_dictionary_file, validate_data_dictionary
from app.services.metric_builder import (
    evaluate_metric_summary,
    find_metric,
    normalize_metric_definition,
    validate_metric_definition,
)
from app.services.semantic_cache import semantic_cache_service
from app.services.semantic_mapper import build_semantic_profile
from app.schemas.models import (
    AgentChatRequest,
    AgentChatResponse,
    ChartRequest,
    ChatRequest,
    ChatResponse,
    DataDictionary,
    DataDictionaryResponse,
    MetricDefinition,
    MetricEvaluationResponse,
    MetricListResponse,
    MetricResponse,
    SemanticOverrideRequest,
    UploadResponse,
)
from app.tools.ecommerce_tools import (
    b2b_summary,
    cancellation_summary,
    category_cancellation_summary,
    courier_summary,
    fulfilment_summary,
    get_data_quality_summary,
    get_sales_overview,
    promotion_summary,
    revenue_by_category,
    revenue_by_month,
    revenue_by_size,
    state_cancellation_summary,
    top_cities_by_revenue,
    top_skus_by_revenue,
    top_states_by_revenue,
)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

# Initialize Database
init_database()

# API Key Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if settings.api_key and api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key

app = FastAPI(
    title=settings.app_name,
    description="Upload CSV, profile data, generate insights, and chat with datasets.",
    version=settings.app_version,
    dependencies=[Depends(verify_api_key)]
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = structlog.contextvars.get_contextvars().get("request_id", "unknown")
    logger.error("unhandled_exception", error=str(exc), type=str(type(exc)), request_id=request_id)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc), "request_id": request_id}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex or None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-API-Key"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    log = logger.bind(path=request.url.path, method=request.method)
    log.info("request_started")
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    log.info("request_finished", status_code=response.status_code, elapsed_ms=elapsed_ms)
    response.headers["X-Request-ID"] = request_id
    return response


agent = DataAnalystAgent()
agent_orchestrator = AgentOrchestrator()


@app.get("/")
@app.get("/health")
async def health_check():
    ollama_status = agent_orchestrator.provider.status()
    return {
        "status": "ok",
        "version": settings.app_version,
        "ollama": ollama_status,
        "datasets_count": len(dataset_store.datasets),
    }



@app.post("/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {exc}")

    # Task 2: File size validation
    if len(content) > settings.max_upload_bytes:
        max_mb = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {max_mb} MB.",
        )

    try:
        df = load_tabular_file(content, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot read tabular file: {str(exc)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty.")

    dataset_id = dataset_store.save_dataframe(df, file.filename)
    invalidate_dataset_cache(dataset_id)
    logger.info("dataset_uploaded", dataset_id=dataset_id, filename=file.filename, rows=df.shape[0], columns=df.shape[1])

    return UploadResponse(
        dataset_id=dataset_id,
        filename=file.filename,
        rows=df.shape[0],
        columns=df.shape[1],
        message="File uploaded successfully."
    )


@app.get("/datasets")
def list_datasets():
    return {
        "datasets": [
            {"dataset_id": did, "filename": meta["filename"]}
            for did, meta in dataset_store.datasets.items()
        ]
    }


@app.get("/summary/{dataset_id}")

def get_summary(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        summary = agent.profile(df)
        return {
            "dataset_id": dataset_id,
            **summary
        }
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/chat", response_model=ChatResponse)
def chat_with_dataset(request: ChatRequest):
    try:
        df = dataset_store.load_dataframe(request.dataset_id)
        result = agent.chat(df, request.question)
        return ChatResponse(
            answer=result["answer"],
            data=result.get("data"),
            chart=None
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/report/{dataset_id}")
def get_report(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        summary = agent.profile(df)
        filename = dataset_store.get_filename(dataset_id)
        report = generate_markdown_report(filename, summary)
        return {"dataset_id": dataset_id, "report_markdown": report}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/semantic-profile/{dataset_id}")
def get_semantic_profile(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        signature = dataset_store.get_dataset_signature(dataset_id)
        overrides = dataset_store.get_semantic_overrides(dataset_id)
        data_dictionary = dataset_store.get_data_dictionary(dataset_id)
        profile_context = {**overrides, "data_dictionary": data_dictionary}
        key = stable_cache_key("semantic", dataset_id, signature, profile_context)
        profile, _ = semantic_profile_cache.get_or_set(key, lambda: build_semantic_profile(df, overrides=profile_context))
        return {
            "dataset_id": dataset_id,
            **profile.to_dict(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/dashboard/{dataset_id}")
def get_dashboard(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        signature = dataset_store.get_dataset_signature(dataset_id)
        overrides = dataset_store.get_semantic_overrides(dataset_id)
        data_dictionary = dataset_store.get_data_dictionary(dataset_id)
        profile_context = {**overrides, "data_dictionary": data_dictionary}
        key = stable_cache_key("dashboard", dataset_id, signature, profile_context)
        dashboard, cache_hit = dashboard_cache.get_or_set(
            key,
            lambda: build_dashboard(dataset_id, df, build_semantic_profile(df, overrides=profile_context)),
        )
        return {**dashboard, "cache": {"dashboard": "hit" if cache_hit else "miss"}}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/semantic-profile/{dataset_id}/overrides")
def put_semantic_overrides(dataset_id: str, request: SemanticOverrideRequest):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        invalid_columns = [column for column in request.roles.values() if column and column not in df.columns]
        if invalid_columns:
            raise HTTPException(status_code=400, detail=f"Columns do not exist: {invalid_columns}")
        dataset_store.set_semantic_overrides(dataset_id, domain=request.domain, roles=request.roles)
        invalidate_dataset_cache(dataset_id)
        semantic_cache_service.clear_dataset_cache(dataset_id)
        overrides = dataset_store.get_semantic_overrides(dataset_id)
        data_dictionary = dataset_store.get_data_dictionary(dataset_id)
        profile = build_semantic_profile(df, overrides={**overrides, "data_dictionary": data_dictionary})
        return {"dataset_id": dataset_id, **profile.to_dict()}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/semantic-profile/{dataset_id}/overrides")
def delete_semantic_overrides(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        dataset_store.clear_semantic_overrides(dataset_id)
        invalidate_dataset_cache(dataset_id)
        semantic_cache_service.clear_dataset_cache(dataset_id)
        data_dictionary = dataset_store.get_data_dictionary(dataset_id)
        profile = build_semantic_profile(df, overrides={"data_dictionary": data_dictionary})
        return {"dataset_id": dataset_id, **profile.to_dict()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/datasets/{dataset_id}/data-dictionary", response_model=DataDictionaryResponse)
async def upload_data_dictionary(dataset_id: str, file: UploadFile = File(...)):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        content = await file.read()
        dictionary = parse_data_dictionary_file(content, file.filename)
        warnings = validate_data_dictionary(dictionary, list(df.columns))
        saved = dataset_store.set_data_dictionary(dataset_id, dictionary)
        invalidate_dataset_cache(dataset_id)
        semantic_cache_service.clear_dataset_cache(dataset_id)
        return DataDictionaryResponse(dataset_id=dataset_id, dictionary=DataDictionary(**saved), source="uploaded_file", warnings=warnings)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/datasets/{dataset_id}/data-dictionary", response_model=DataDictionaryResponse)
def get_data_dictionary(dataset_id: str):
    try:
        dataset_store.load_dataframe(dataset_id)
        dictionary = dataset_store.get_data_dictionary(dataset_id)
        if not dictionary:
            return DataDictionaryResponse(
                dataset_id=dataset_id,
                dictionary=None,
                source="none",
                warnings=["No data dictionary has been saved for this dataset."],
            )
        return DataDictionaryResponse(dataset_id=dataset_id, dictionary=DataDictionary(**dictionary), source="saved", warnings=[])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/datasets/{dataset_id}/data-dictionary", response_model=DataDictionaryResponse)
def put_data_dictionary(dataset_id: str, request: DataDictionary):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        dictionary = request.model_dump()
        warnings = validate_data_dictionary(dictionary, list(df.columns))
        saved = dataset_store.set_data_dictionary(dataset_id, dictionary)
        invalidate_dataset_cache(dataset_id)
        semantic_cache_service.clear_dataset_cache(dataset_id)
        return DataDictionaryResponse(dataset_id=dataset_id, dictionary=DataDictionary(**saved), source="saved", warnings=warnings)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/datasets/{dataset_id}/data-dictionary")
def delete_data_dictionary(dataset_id: str):
    try:
        dataset_store.load_dataframe(dataset_id)
        dataset_store.clear_data_dictionary(dataset_id)
        invalidate_dataset_cache(dataset_id)
        semantic_cache_service.clear_dataset_cache(dataset_id)
        return {"dataset_id": dataset_id, "deleted": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/datasets/{dataset_id}/metrics", response_model=MetricListResponse)
def get_custom_metrics(dataset_id: str):
    try:
        dataset_store.load_dataframe(dataset_id)
        metrics = [MetricDefinition(**metric) for metric in dataset_store.get_custom_metrics(dataset_id)]
        return MetricListResponse(dataset_id=dataset_id, metrics=metrics)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/datasets/{dataset_id}/metrics", response_model=MetricResponse)
def create_custom_metric(dataset_id: str, request: MetricDefinition):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        profile = _build_current_semantic_profile(dataset_id, df)
        metric = normalize_metric_definition(request.model_dump())
        warnings = validate_metric_definition(metric, df, profile)
        saved = dataset_store.set_custom_metric(dataset_id, metric)
        invalidate_dataset_cache(dataset_id)
        semantic_cache_service.clear_dataset_cache(dataset_id)
        return MetricResponse(dataset_id=dataset_id, metric=MetricDefinition(**saved), warnings=warnings)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/datasets/{dataset_id}/metrics/{metric_name}", response_model=MetricResponse)
def update_custom_metric(dataset_id: str, metric_name: str, request: MetricDefinition):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        profile = _build_current_semantic_profile(dataset_id, df)
        metric = normalize_metric_definition({**request.model_dump(), "name": metric_name})
        warnings = validate_metric_definition(metric, df, profile)
        saved = dataset_store.set_custom_metric(dataset_id, metric)
        invalidate_dataset_cache(dataset_id)
        semantic_cache_service.clear_dataset_cache(dataset_id)
        return MetricResponse(dataset_id=dataset_id, metric=MetricDefinition(**saved), warnings=warnings)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/datasets/{dataset_id}/metrics/{metric_name}")
def delete_custom_metric(dataset_id: str, metric_name: str):
    try:
        dataset_store.load_dataframe(dataset_id)
        dataset_store.delete_custom_metric(dataset_id, metric_name)
        invalidate_dataset_cache(dataset_id)
        semantic_cache_service.clear_dataset_cache(dataset_id)
        return {"dataset_id": dataset_id, "metric_name": metric_name, "deleted": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/datasets/{dataset_id}/metrics/{metric_name}/evaluate", response_model=MetricEvaluationResponse)
def evaluate_custom_metric(dataset_id: str, metric_name: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        profile = _build_current_semantic_profile(dataset_id, df)
        metric = find_metric(dataset_store.get_custom_metrics(dataset_id), metric_name)
        summary = evaluate_metric_summary(df, profile, metric)
        return MetricEvaluationResponse(dataset_id=dataset_id, metric_name=metric["name"], summary=summary, rows=None, warnings=[])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _build_current_semantic_profile(dataset_id: str, df):
    overrides = dataset_store.get_semantic_overrides(dataset_id)
    data_dictionary = dataset_store.get_data_dictionary(dataset_id)
    return build_semantic_profile(df, overrides={**overrides, "data_dictionary": data_dictionary})


@app.post("/chart")
def generate_chart(request: ChartRequest):
    try:
        df = dataset_store.load_dataframe(request.dataset_id)
        chart = generate_chart_spec(df, request.chart_type, request.x, request.y)
        return {
            "dataset_id": request.dataset_id,
            "chart": chart,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/agent/chat", response_model=AgentChatResponse)
def agent_chat(request: AgentChatRequest):
    try:
        result = agent_orchestrator.chat(request.dataset_id, request.question, mode=request.mode)
        return AgentChatResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/agent/chat/stream")
def agent_chat_stream(request: AgentChatRequest):
    def event_stream():
        try:
            for event in agent_orchestrator.stream_chat(request.dataset_id, request.question, mode=request.mode):
                yield f"event: {event['event']}\n"
                yield f"data: {json.dumps(event['data'], ensure_ascii=False, default=str)}\n\n"
        except Exception as exc:
            payload = {"answer": f"Mình chưa chạy được câu hỏi này: {str(exc)}", "warnings": [str(exc)]}
            yield "event: error\n"
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/agent/status")
def agent_status():
    return agent_orchestrator.status()


@app.get("/ecommerce/overview/{dataset_id}")
def get_ecommerce_overview(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {
            "dataset_id": dataset_id,
            "overview": get_sales_overview(prepared),
            "data_quality": get_data_quality_summary(prepared),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/revenue-by-month/{dataset_id}")
def get_ecommerce_revenue_by_month(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {
            "dataset_id": dataset_id,
            "items": revenue_by_month(prepared),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/revenue-by-category/{dataset_id}")
def get_ecommerce_revenue_by_category(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {
            "dataset_id": dataset_id,
            "items": revenue_by_category(prepared),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/top-states/{dataset_id}")
def get_ecommerce_top_states(dataset_id: str, n: int = 10):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {
            "dataset_id": dataset_id,
            "items": top_states_by_revenue(prepared, n=n),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/cancellation/{dataset_id}")
def get_ecommerce_cancellation(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {
            "dataset_id": dataset_id,
            "summary": cancellation_summary(prepared),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/top-skus/{dataset_id}")
def get_ecommerce_top_skus(dataset_id: str, n: int = 20):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {"dataset_id": dataset_id, "items": top_skus_by_revenue(prepared, n=n)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/revenue-by-size/{dataset_id}")
def get_ecommerce_revenue_by_size(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {"dataset_id": dataset_id, "items": revenue_by_size(prepared)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/category-cancellation/{dataset_id}")
def get_ecommerce_category_cancellation(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {"dataset_id": dataset_id, "items": category_cancellation_summary(prepared)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/fulfilment/{dataset_id}")
def get_ecommerce_fulfilment(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {"dataset_id": dataset_id, "items": fulfilment_summary(prepared)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/courier/{dataset_id}")
def get_ecommerce_courier(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {"dataset_id": dataset_id, "items": courier_summary(prepared)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/promotion/{dataset_id}")
def get_ecommerce_promotion(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {"dataset_id": dataset_id, "summary": promotion_summary(prepared)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/b2b/{dataset_id}")
def get_ecommerce_b2b(dataset_id: str):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {"dataset_id": dataset_id, "summary": b2b_summary(prepared)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/top-cities/{dataset_id}")
def get_ecommerce_top_cities(dataset_id: str, n: int = 20):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {"dataset_id": dataset_id, "items": top_cities_by_revenue(prepared, n=n)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/ecommerce/state-cancellation/{dataset_id}")
def get_ecommerce_state_cancellation(dataset_id: str, min_orders: int = 1000, n: int = 20):
    try:
        df = dataset_store.load_dataframe(dataset_id)
        prepared = prepare_amazon_sales_dataframe(df)
        return {
            "dataset_id": dataset_id,
            "items": state_cancellation_summary(prepared, min_orders=min_orders, n=n),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
