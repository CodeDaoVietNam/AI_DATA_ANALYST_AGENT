from __future__ import annotations

import json
import queue
import re
import threading
import time
import uuid
from typing import Any, Callable, Iterable

from app.config import settings

from app.services.cache_manager import semantic_profile_cache, stable_cache_key, tool_result_cache
from app.services.chart_generator import generate_chart_spec
from app.services.code_interpreter import execute_pandas_code
from app.services.dataset_pipeline import prepare_amazon_sales_dataframe
from app.services.answer_composer import answer_card_to_text, compose_answer_card, compose_tool_error_card, merge_llm_answer_card
from app.services.llm.ollama_provider import OllamaProvider
from app.services.metric_builder import evaluate_metric_summary, find_metric, metric_breakdown
from app.services.profiler import infer_column_types
from app.services.intent_planner import compile_intent_to_plan, parse_universal_intent
from app.services.semantic_mapper import DatasetSemanticProfile, build_semantic_profile
from app.services.storage import DatasetStore, dataset_store
from app.services.semantic_cache import semantic_cache_service
from app.tools.domain_analysis_tools import (
    hr_attrition_by_role,
    hr_high_risk_segments,
    hr_income_band_attrition,
    hr_tenure_risk,
    marketing_campaign_acceptance,
    marketing_income_band_response,
    marketing_purchase_channel_summary,
    marketing_response_by_segment,
    marketing_rfm_summary,
    retail_discount_effect,
    retail_interaction,
    retail_loss_analysis,
    retail_margin_summary,
    retail_top_opportunities,
)
from app.tools.ecommerce_tools import (
    b2b_summary,
    cancellation_summary,
    category_cancellation_summary,
    courier_summary,
    fulfilment_summary,
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
from app.tools.generic_analysis_tools import (
    correlation_analysis,
    get_dataset_overview,
    get_duplicate_rows,
    get_missing_values,
    groupby_aggregate,
    semantic_breakdown,
    semantic_overview,
    semantic_target_summary,
    semantic_time_series,
    compare_segments,
    detect_outliers,
    trend_analysis,
    period_over_period_change,
    top_bottom_contributors,
    pareto_analysis,
    cohort_summary,
    anomaly_detection,
    forecast_next_period,
    explain_metric_change,
)


GENERIC_TOOL_SPECS = {
    "get_dataset_overview": {"description": "Return dataset overview.", "arguments": {}},
    "get_missing_values": {"description": "Return missing values by column.", "arguments": {}},
    "get_duplicate_rows": {"description": "Return duplicate row count.", "arguments": {}},
    "groupby_aggregate": {"description": "Aggregate a numeric metric by a group column.", "arguments": {"group_by": "column", "metric": "column", "aggregation": "sum|mean|median|min|max|count"}},
    "correlation_analysis": {"description": "Return numeric correlations.", "arguments": {"columns": "optional list"}},
    "generate_chart_spec": {"description": "Generate Plotly chart spec.", "arguments": {"chart_type": "bar|line|scatter|histogram|box", "x": "column", "y": "optional column"}},
    "python_code_interpreter": {"description": "Fallback Python/Pandas sandbox for complex calculations.", "arguments": {"code": "python code"}},
    "semantic_overview": {"description": "Return semantic/domain overview.", "arguments": {}},
    "semantic_time_series": {"description": "Return semantic metric trend by month.", "arguments": {}},
    "semantic_breakdown": {"description": "Break down semantic metric by semantic role.", "arguments": {"by_role": "role", "metric_role": "role"}},
    "semantic_target_summary": {"description": "Summarize target/conversion/attrition by role.", "arguments": {"by_role": "role"}},
    "compare_segments": {"description": "Compare metric between two segments (groups).", "arguments": {"segment_column": "column", "segment_a": "string", "segment_b": "string", "metric_column": "column", "aggregation": "optional sum|mean|median|min|max|count"}},
    "detect_outliers": {"description": "Detect outliers using IQR or Z-score.", "arguments": {"metric_column": "column", "method": "optional iqr|zscore"}},
    "trend_analysis": {"description": "Analyze growth trends and month-over-month rate.", "arguments": {"date_column": "column", "metric_column": "column", "freq": "optional M|Q|Y", "aggregation": "optional sum|mean"}},
    "period_over_period_change": {"description": "Compare metric value between two datetime periods.", "arguments": {"date_column": "column", "metric_column": "column", "period_a_start": "YYYY-MM-DD", "period_a_end": "YYYY-MM-DD", "period_b_start": "YYYY-MM-DD", "period_b_end": "YYYY-MM-DD", "aggregation": "optional sum|mean"}},
    "top_bottom_contributors": {"description": "Find top and bottom categories contributing to a metric.", "arguments": {"group_column": "column", "metric_column": "column", "n": "optional integer"}},
    "pareto_analysis": {"description": "Run Pareto 80/20 analysis on a category.", "arguments": {"category_column": "column", "metric_column": "column"}},
    "cohort_summary": {"description": "Perform cohort analysis (e.g. user acquisition and activity monthly retention).", "arguments": {"cohort_date_column": "column", "activity_date_column": "column", "user_id_column": "column"}},
    "anomaly_detection": {"description": "Detect anomalies in metric over time.", "arguments": {"date_column": "column", "metric_column": "column", "freq": "optional M|Q|Y"}},
    "forecast_next_period": {"description": "Baseline forecast (Exponential Smoothing + naive trend) for next periods.", "arguments": {"date_column": "column", "metric_column": "column", "periods": "optional integer"}},
    "explain_metric_change": {"description": "Explain change of a metric between two periods via contribution analysis.", "arguments": {"date_column": "column", "metric_column": "column", "dimension_column": "column", "period_a_start": "YYYY-MM-DD", "period_a_end": "YYYY-MM-DD", "period_b_start": "YYYY-MM-DD", "period_b_end": "YYYY-MM-DD"}},
    "evaluate_custom_metric": {"description": "Evaluate a user-defined custom metric by metric name.", "arguments": {"metric_name": "custom metric name"}},
    "custom_metric_breakdown": {"description": "Break down a user-defined custom metric by semantic role or column.", "arguments": {"metric_name": "custom metric name", "by_role": "optional role", "by_column": "optional column", "limit": "optional integer"}},
    "retail_margin_summary": {"description": "Retail revenue/profit/margin summary.", "arguments": {}},
    "retail_loss_analysis": {"description": "Retail loss-making groups.", "arguments": {"by_role": "category|segment|state"}},
    "retail_discount_effect": {"description": "Retail discount-band effect.", "arguments": {}},
    "retail_interaction": {"description": "Retail segment/state/category interaction.", "arguments": {}},
    "retail_top_opportunities": {"description": "High revenue but low margin retail opportunities.", "arguments": {"by_role": "category|segment|state"}},
    "marketing_response_by_segment": {"description": "Marketing response by segment/country/campaign.", "arguments": {"by_role": "country|campaign|segment"}},
    "marketing_campaign_acceptance": {"description": "Campaign acceptance rates.", "arguments": {}},
    "marketing_rfm_summary": {"description": "RFM-like marketing summary.", "arguments": {}},
    "marketing_income_band_response": {"description": "Response by income band.", "arguments": {}},
    "marketing_purchase_channel_summary": {"description": "Purchases by web/catalog/store/deals.", "arguments": {}},
    "hr_attrition_by_role": {"description": "HR attrition by department/job_role/overtime.", "arguments": {"by_role": "department|job_role|overtime"}},
    "hr_income_band_attrition": {"description": "HR attrition by income band.", "arguments": {}},
    "hr_tenure_risk": {"description": "HR attrition by tenure band.", "arguments": {}},
    "hr_high_risk_segments": {"description": "Combined HR high-risk segments.", "arguments": {}},
}

ECOMMERCE_TOOL_SPECS = {
    "get_sales_overview": {"description": "Return ecommerce revenue/orders/cancel overview.", "arguments": {}},
    "revenue_by_month": {"description": "Return monthly ecommerce revenue.", "arguments": {}},
    "revenue_by_category": {"description": "Return ecommerce revenue by category.", "arguments": {}},
    "top_states_by_revenue": {"description": "Return top states by revenue.", "arguments": {"n": "1-100"}},
    "cancellation_summary": {"description": "Return cancellation summary.", "arguments": {}},
    "top_skus_by_revenue": {"description": "Return top SKUs by revenue.", "arguments": {"n": "1-100"}},
    "revenue_by_size": {"description": "Return revenue by size.", "arguments": {}},
    "category_cancellation_summary": {"description": "Return cancellation risk by category.", "arguments": {}},
    "fulfilment_summary": {"description": "Return fulfilment performance.", "arguments": {}},
    "courier_summary": {"description": "Return courier status summary.", "arguments": {}},
    "promotion_summary": {"description": "Return promotion vs non-promotion summary.", "arguments": {}},
    "b2b_summary": {"description": "Return B2B vs non-B2B summary.", "arguments": {}},
    "top_cities_by_revenue": {"description": "Return top cities by revenue.", "arguments": {"n": "1-100"}},
    "state_cancellation_summary": {"description": "Return cancellation risk by state.", "arguments": {"min_orders": "integer", "n": "1-100"}},
}


class AgentOrchestrator:
    def __init__(self, provider: Any | None = None, store: DatasetStore | None = None):
        self.provider = provider or OllamaProvider()
        self.store = store or dataset_store

    def chat(
        self,
        dataset_id: str,
        question: str,
        mode: str = "balanced",
        event_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        timeline: list[dict[str, Any]] = []
        cache_info: dict[str, Any] = {"semantic_profile": "miss", "tool_results": []}
        latency: dict[str, Any] = {}

        def emit(event: str, payload: dict[str, Any]) -> None:
            if event_callback:
                event_callback(event, payload)

        _timeline(timeline, started_at, "received_question", "ok", "Question received by agent.")
        emit("progress", {"step": "received_question", "message": "Question received."})

        # --- 🚀 TÍCH HỢP SEMANTIC CACHE (PHẢN HỒI DƯỚI 50MS) ---
        cached_response = semantic_cache_service.query_cache(dataset_id, question)
        if cached_response:
            latency["total_ms"] = _elapsed_ms(started_at)
            cached_response["latency"] = {**cached_response.get("latency", {}), "total_ms": latency["total_ms"]}
            cached_response["execution_timeline"] = timeline
            _timeline(timeline, started_at, "completed", "ok", f"Served from semantic cache: {cached_response.get('explanation_source')}")
            emit("progress", {"step": "completed", "message": f"Response served instantly from Semantic Cache ({cached_response.get('explanation_source')})."})
            emit("final", cached_response)
            return cached_response
        # -----------------------------------------------------

        load_started = time.perf_counter()
        raw_df = self.store.load_dataframe(dataset_id)
        signature = self.store.get_dataset_signature(dataset_id)
        latency["load_dataset_ms"] = _elapsed_ms(load_started)
        emit("progress", {"step": "loading_dataset", "message": "Dataset loaded."})

        profile_started = time.perf_counter()
        semantic_profile, profile_cache_hit = self._semantic_profile(dataset_id, raw_df, signature)
        custom_metrics = self.store.get_custom_metrics(dataset_id)
        cache_info["semantic_profile"] = "hit" if profile_cache_hit else "miss"
        latency["semantic_profile_ms"] = _elapsed_ms(profile_started)
        emit("progress", {"step": "building_semantic_profile", "message": f"Semantic profile ready ({cache_info['semantic_profile']})."})

        column_types = infer_column_types(raw_df)
        ecommerce_available = _looks_like_amazon_sales(raw_df)
        tool_specs = dict(GENERIC_TOOL_SPECS)
        if custom_metrics:
            tool_specs["evaluate_custom_metric"] = GENERIC_TOOL_SPECS["evaluate_custom_metric"]
            tool_specs["custom_metric_breakdown"] = GENERIC_TOOL_SPECS["custom_metric_breakdown"]
        if ecommerce_available:
            tool_specs.update(ECOMMERCE_TOOL_SPECS)

        plan_started = time.perf_counter()
        plan, plan_warnings = self._build_plan(question, raw_df, column_types, ecommerce_available, semantic_profile, custom_metrics, tool_specs, mode)
        latency["planning_ms"] = _elapsed_ms(plan_started)
        if plan_warnings:
            _timeline(timeline, started_at, "fallback_tool", "ok", "Falling back to a safe deterministic plan.", {"warnings": plan_warnings})
        if plan.get("intent"):
            _timeline(timeline, started_at, "parsed_intent", "ok", f"Parsed universal intent `{plan['intent'].get('task')}`.", plan["intent"])
        _timeline(timeline, started_at, "selected_plan", "ok", f"Selected {len(plan['steps'])} tool step(s).", plan)
        emit("plan", plan)

        tool_calls = []
        results = []
        for index, step in enumerate(plan["steps"], start=1):
            tool_name = step["tool_name"]
            arguments = step.get("arguments", {}) or {}
            purpose = step.get("purpose")
            emit("tool_started", {"index": index, "total": len(plan["steps"]), "tool_name": tool_name, "arguments": arguments, "purpose": purpose})
            _timeline(timeline, started_at, "tool_started", "ok", f"Running `{tool_name}`.", {"tool_name": tool_name, "arguments": arguments})
            tool_started = time.perf_counter()
            try:
                result, tool_cache_hit = self._execute_tool_cached(
                    dataset_id,
                    signature,
                    tool_name,
                    arguments,
                    raw_df,
                    ecommerce_available,
                    semantic_profile,
                    custom_metrics,
                )
                execution_ms = _elapsed_ms(tool_started)
                cache_info["tool_results"].append({"tool_name": tool_name, "cache": "hit" if tool_cache_hit else "miss"})
                call = {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": result,
                    "error": None,
                    "purpose": purpose,
                    "execution_ms": execution_ms,
                }
                tool_calls.append(call)
                results.append({"tool_name": tool_name, "arguments": arguments, "purpose": purpose, "result": result})
                _timeline(timeline, started_at, "tool_finished", "ok", f"Công cụ `{tool_name}` đã chạy xong.", {"tool_name": tool_name, "execution_ms": execution_ms, "cache": cache_info["tool_results"][-1]["cache"]})
                emit("tool_finished", {"index": index, "tool_name": tool_name, "execution_ms": execution_ms, "summary": _result_summary(result, tool_name), "cache": cache_info["tool_results"][-1]["cache"]})
            except Exception as exc:
                _timeline(timeline, started_at, "tool_failed", "error", str(exc), {"tool_name": tool_name, "arguments": arguments})
                error_response = _tool_error_response(tool_name, arguments, exc, timeline, started_at)
                error_response["tool_calls"] = tool_calls
                error_response["agent_plan"] = plan
                error_response["latency"] = {**latency, "total_ms": _elapsed_ms(started_at)}
                error_response["cache"] = cache_info
                emit("error", error_response)
                return error_response

        primary_call = tool_calls[0] if tool_calls else None
        primary_result = results[0]["result"] if len(results) == 1 else {"tool_results": results}
        primary_tool = primary_call["tool_name"] if primary_call else "none"
        primary_args = primary_call["arguments"] if primary_call else {}
        chart_val = primary_result if primary_tool == "generate_chart_spec" else None
        if len(results) > 1:
            chart_val = next((item["result"] for item in results if item["tool_name"] == "generate_chart_spec"), None)

        result_summary = _result_summary(primary_result, primary_tool if len(results) == 1 else "multi_step")
        emit("explanation_started", {"message": "Preparing explanation."})
        explain_started = time.perf_counter()
        explanation = self._explain_result(
            question,
            primary_tool if len(results) == 1 else "multi_step",
            primary_args,
            primary_result,
            result_summary,
            mode,
            semantic_profile,
            plan_warnings,
        )
        latency["explanation_ms"] = _elapsed_ms(explain_started)

        answer = explanation["answer"]
        answer_card = explanation.get("answer_card")
        quick_actions = _quick_actions(primary_tool if len(results) == 1 else "multi_step", primary_result, result_summary)
        _timeline(timeline, started_at, "prepared_explanation", "ok", f"Prepared answer with {explanation['source']}.", {"explanation_source": explanation["source"]})
        warnings = [*plan_warnings, *explanation.get("warnings", [])]
        if _result_mentions_missing_amount(primary_result):
            warnings.append("Doanh thu được tính từ các giá trị amount hiện có; một số dòng đang thiếu amount.")
            if answer_card:
                answer_card.setdefault("data_warnings", [])
                if "Doanh thu được tính từ các giá trị amount hiện có; một số dòng đang thiếu amount." not in answer_card["data_warnings"]:
                    answer_card["data_warnings"].append("Doanh thu được tính từ các giá trị amount hiện có; một số dòng đang thiếu amount.")
        if hasattr(self.provider, "router_model") and cache_info.get("router_fallback"):
            warnings.append(str(cache_info["router_fallback"]))

        latency["total_ms"] = _elapsed_ms(started_at)
        _timeline(timeline, started_at, "completed", "ok", "Agent response completed.")
        response = {
            "answer": answer,
            "answer_card": answer_card,
            "tool_call": primary_call,
            "tool_calls": tool_calls,
            "agent_plan": plan,
            "data": primary_result,
            "chart": chart_val,
            "warnings": warnings,
            "execution_timeline": timeline,
            "result_summary": result_summary,
            "explanation_source": explanation["source"],
            "quick_actions": quick_actions,
            "latency": latency,
            "cache": cache_info,
        }
        # --- 🚀 LƯU VÀO SEMANTIC CACHE CHO LẦN SAU ---
        semantic_cache_service.add_to_cache(dataset_id, question, response)
        # ---------------------------------------------

        emit("final", response)
        return response

    def stream_chat(self, dataset_id: str, question: str, mode: str = "balanced") -> Iterable[dict[str, Any]]:
        events: queue.Queue[dict[str, Any]] = queue.Queue()

        def emit(event: str, payload: dict[str, Any]) -> None:
            events.put({"event": event, "data": payload})

        def runner() -> None:
            try:
                self.chat(dataset_id, question, mode=mode, event_callback=emit)
            except Exception as exc:
                emit("error", {"answer": f"Mình chưa chạy được câu hỏi này: {exc}", "warnings": [str(exc)]})
            finally:
                events.put({"event": "__done__", "data": {}})

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        while True:
            event = events.get()
            if event["event"] == "__done__":
                break
            yield event

    def _semantic_profile(self, dataset_id: str, raw_df, signature: dict[str, Any]) -> tuple[DatasetSemanticProfile, bool]:
        overrides = self.store.get_semantic_overrides(dataset_id)
        data_dictionary = self.store.get_data_dictionary(dataset_id)
        profile_context = {**overrides, "data_dictionary": data_dictionary}
        key = stable_cache_key("semantic", dataset_id, signature, profile_context)
        return semantic_profile_cache.get_or_set(key, lambda: build_semantic_profile(raw_df, overrides=profile_context))

    def _build_plan(
        self,
        question: str,
        df,
        column_types: dict[str, str],
        ecommerce_available: bool,
        semantic_profile: DatasetSemanticProfile,
        custom_metrics: list[dict[str, Any]],
        tool_specs: dict[str, Any],
        mode: str,
    ) -> tuple[dict[str, Any], list[str]]:
        intent = parse_universal_intent(
            question,
            df,
            semantic_profile,
            custom_metrics,
            ecommerce_available=ecommerce_available,
        )
        intent_plan = compile_intent_to_plan(
            intent,
            df,
            semantic_profile,
            custom_metrics,
            ecommerce_available=ecommerce_available,
        )
        if intent_plan:
            return intent_plan, []

        rule_plan = _rule_based_plan(question, df, ecommerce_available, semantic_profile, custom_metrics, mode)
        if rule_plan:
            rule_plan["intent"] = intent.to_dict()
            return rule_plan, []
        if mode == "fast":
            fallback_plan = _single_step_plan(_fallback_selection(question, ecommerce_available), "fast fallback")
            fallback_plan["intent"] = intent.to_dict()
            return fallback_plan, []

        selection = self._select_tool(question, df, column_types, ecommerce_available, semantic_profile, custom_metrics, tool_specs)
        if selection.get("error"):
            fallback = _fallback_selection(question, ecommerce_available)
            fallback_plan = _single_step_plan(fallback, "fallback after router error")
            fallback_plan["intent"] = intent.to_dict()
            return fallback_plan, [selection["error"]]
        plan = _single_step_plan(selection, "llm router")
        plan["intent"] = intent.to_dict()
        return plan, []

    def _select_tool(
        self,
        question: str,
        df,
        column_types: dict[str, str],
        ecommerce_available: bool,
        semantic_profile: DatasetSemanticProfile,
        custom_metrics: list[dict[str, Any]],
        tool_specs: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = {
            "columns": list(df.columns),
            "column_types": column_types,
            "ecommerce_available": ecommerce_available,
            "semantic_profile": _compact_semantic_profile(semantic_profile),
            "custom_metrics": [{"name": metric.get("name"), "label": metric.get("label"), "expression": metric.get("expression")} for metric in custom_metrics],
            "allowed_tools": tool_specs,
            "user_question": question,
            "rules": [
                "Return only valid JSON matching the output_schema.",
                "Choose exactly one allowed tool. If a specific tool fits (e.g. retail, marketing, or HR tools), use it first. If no specialized tool fits, use 'python_code_interpreter' with custom pandas code.",
                "When using 'python_code_interpreter', write a valid, single-step python/pandas expression in the 'code' argument. The pandas dataframe is preloaded as 'df'.",
                "Ensure any generated pandas code uses exact columns from the provided list. E.g., for HR attrition, use columns like 'Attrition', 'MonthlyIncome', 'Department', 'JobRole', 'YearsAtCompany', 'OverTime' exactly as they are capitalized.",
                "For Aggregations: always aggregate numeric metrics (like MonthlyIncome, YearsAtCompany, Salary, Revenue) by categorical groups.",
                "Do not invent column names. Refer strictly to the columns and roles in semantic_profile.",
                "Do not calculate numbers yourself. Always let Python/Pandas compute them.",
            ],
            "output_schema": {"tool_name": "one allowed tool name", "arguments": {}},
        }
        messages = [
            {"role": "system", "content": "You are a data analyst tool router. Return only JSON."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ]
        try:
            if hasattr(self.provider, "route"):
                content = self.provider.route(messages, format_json=True)
            else:
                content = self.provider.chat(messages, format_json=True)
        except Exception as exc:
            if hasattr(self.provider, "chat"):
                try:
                    content = self.provider.chat(messages, format_json=True, timeout=settings.ollama_router_timeout)
                except TypeError:
                    try:
                        content = self.provider.chat(messages, format_json=True)
                    except Exception:
                        return {"error": f"Router failed: {exc}"}
                except Exception:
                    return {"error": f"Router failed: {exc}"}
            else:
                return {"error": f"Router failed: {exc}"}

        try:
            selection = json.loads(content)
        except json.JSONDecodeError:
            return {"error": "Ollama did not return valid JSON for tool selection."}
        tool_name = selection.get("tool_name")
        if tool_name not in tool_specs:
            return {"error": f"Unknown or unsupported tool: {tool_name}"}
        arguments = selection.get("arguments", {})
        if not isinstance(arguments, dict):
            return {"error": "Tham số công cụ phải là một JSON object."}
        return {"tool_name": tool_name, "arguments": arguments}

    def _execute_tool_cached(
        self,
        dataset_id: str,
        signature: dict[str, Any],
        tool_name: str,
        arguments: dict[str, Any],
        raw_df,
        ecommerce_available: bool,
        semantic_profile: DatasetSemanticProfile,
        custom_metrics: list[dict[str, Any]],
    ) -> tuple[Any, bool]:
        key = stable_cache_key("tool", dataset_id, signature, tool_name, arguments, custom_metrics)
        return tool_result_cache.get_or_set(
            key,
            lambda: self._execute_tool(tool_name, arguments, raw_df, ecommerce_available, semantic_profile, custom_metrics),
        )

    def _execute_tool(self, tool_name: str, arguments: dict[str, Any], raw_df, ecommerce_available: bool, semantic_profile: DatasetSemanticProfile, custom_metrics: list[dict[str, Any]]) -> Any:
        generic_tools: dict[str, Callable[[], Any]] = {
            "get_dataset_overview": lambda: get_dataset_overview(raw_df),
            "get_missing_values": lambda: get_missing_values(raw_df),
            "get_duplicate_rows": lambda: get_duplicate_rows(raw_df),
            "groupby_aggregate": lambda: groupby_aggregate(raw_df, group_by=arguments.get("group_by", ""), metric=arguments.get("metric", ""), aggregation=arguments.get("aggregation", "")),
            "correlation_analysis": lambda: correlation_analysis(raw_df, columns=arguments.get("columns")),
            "semantic_overview": lambda: semantic_overview(raw_df, semantic_profile),
            "semantic_time_series": lambda: semantic_time_series(raw_df, semantic_profile, metric_role=arguments.get("metric_role")),
            "semantic_breakdown": lambda: semantic_breakdown(raw_df, semantic_profile, by_role=arguments.get("by_role", "category"), metric_role=arguments.get("metric_role", "revenue"), limit=int(arguments.get("limit", 20))),
            "semantic_target_summary": lambda: semantic_target_summary(raw_df, semantic_profile, by_role=arguments.get("by_role")),
            "retail_margin_summary": lambda: retail_margin_summary(raw_df, semantic_profile),
            "retail_loss_analysis": lambda: retail_loss_analysis(raw_df, semantic_profile, by_role=arguments.get("by_role", "category")),
            "retail_discount_effect": lambda: retail_discount_effect(raw_df, semantic_profile),
            "retail_interaction": lambda: retail_interaction(raw_df, semantic_profile),
            "retail_top_opportunities": lambda: retail_top_opportunities(raw_df, semantic_profile, by_role=arguments.get("by_role", "category")),
            "marketing_response_by_segment": lambda: marketing_response_by_segment(raw_df, semantic_profile, by_role=arguments.get("by_role", "country")),
            "marketing_campaign_acceptance": lambda: marketing_campaign_acceptance(raw_df, semantic_profile),
            "marketing_rfm_summary": lambda: marketing_rfm_summary(raw_df, semantic_profile),
            "marketing_income_band_response": lambda: marketing_income_band_response(raw_df, semantic_profile),
            "marketing_purchase_channel_summary": lambda: marketing_purchase_channel_summary(raw_df),
            "hr_attrition_by_role": lambda: hr_attrition_by_role(raw_df, semantic_profile, by_role=arguments.get("by_role", "department"), min_rows=int(arguments.get("min_rows", 1))),
            "hr_income_band_attrition": lambda: hr_income_band_attrition(raw_df, semantic_profile),
            "hr_tenure_risk": lambda: hr_tenure_risk(raw_df, semantic_profile),
            "hr_high_risk_segments": lambda: hr_high_risk_segments(raw_df, semantic_profile, min_rows=int(arguments.get("min_rows", 1))),
            "compare_segments": lambda: compare_segments(raw_df, segment_column=arguments.get("segment_column", ""), segment_a=arguments.get("segment_a", ""), segment_b=arguments.get("segment_b", ""), metric_column=arguments.get("metric_column", ""), aggregation=arguments.get("aggregation", "mean")),
            "detect_outliers": lambda: detect_outliers(raw_df, metric_column=arguments.get("metric_column", ""), method=arguments.get("method", "iqr")),
            "trend_analysis": lambda: trend_analysis(raw_df, date_column=arguments.get("date_column", ""), metric_column=arguments.get("metric_column", ""), freq=arguments.get("freq", "M"), aggregation=arguments.get("aggregation", "sum")),
            "period_over_period_change": lambda: period_over_period_change(raw_df, date_column=arguments.get("date_column", ""), metric_column=arguments.get("metric_column", ""), period_a_start=arguments.get("period_a_start", ""), period_a_end=arguments.get("period_a_end", ""), period_b_start=arguments.get("period_b_start", ""), period_b_end=arguments.get("period_b_end", ""), aggregation=arguments.get("aggregation", "sum")),
            "top_bottom_contributors": lambda: top_bottom_contributors(raw_df, group_column=arguments.get("group_column", ""), metric_column=arguments.get("metric_column", ""), n=int(arguments.get("n", 5))),
            "pareto_analysis": lambda: pareto_analysis(raw_df, category_column=arguments.get("category_column", ""), metric_column=arguments.get("metric_column", "")),
            "cohort_summary": lambda: cohort_summary(raw_df, cohort_date_column=arguments.get("cohort_date_column", ""), activity_date_column=arguments.get("activity_date_column", ""), user_id_column=arguments.get("user_id_column", "")),
            "anomaly_detection": lambda: anomaly_detection(raw_df, date_column=arguments.get("date_column", ""), metric_column=arguments.get("metric_column", ""), freq=arguments.get("freq", "M")),
            "forecast_next_period": lambda: forecast_next_period(raw_df, date_column=arguments.get("date_column", ""), metric_column=arguments.get("metric_column", ""), periods=int(arguments.get("periods", 3))),
            "explain_metric_change": lambda: explain_metric_change(raw_df, date_column=arguments.get("date_column", ""), metric_column=arguments.get("metric_column", ""), dimension_column=arguments.get("dimension_column", ""), period_a_start=arguments.get("period_a_start", ""), period_a_end=arguments.get("period_a_end", ""), period_b_start=arguments.get("period_b_start", ""), period_b_end=arguments.get("period_b_end", "")),
            "evaluate_custom_metric": lambda: evaluate_metric_summary(raw_df, semantic_profile, find_metric(custom_metrics, arguments.get("metric_name", ""))),
            "custom_metric_breakdown": lambda: metric_breakdown(raw_df, semantic_profile, find_metric(custom_metrics, arguments.get("metric_name", "")), by_role=arguments.get("by_role"), by_column=arguments.get("by_column"), limit=int(arguments.get("limit", 20))),
        }
        if tool_name in generic_tools:
            return generic_tools[tool_name]()
        if tool_name == "generate_chart_spec":
            return generate_chart_spec(raw_df, chart_type=arguments.get("chart_type", "bar"), x=arguments.get("x", ""), y=arguments.get("y"))
        if tool_name == "python_code_interpreter":
            return self._execute_python_tool(raw_df, arguments.get("code", ""))
        if not ecommerce_available:
            raise ValueError("Ecommerce tools are not available for this dataset.")
        prepared = prepare_amazon_sales_dataframe(raw_df)
        ecommerce_tools: dict[str, Callable[[], Any]] = {
            "get_sales_overview": lambda: get_sales_overview(prepared),
            "revenue_by_month": lambda: revenue_by_month(prepared),
            "revenue_by_category": lambda: revenue_by_category(prepared),
            "top_states_by_revenue": lambda: top_states_by_revenue(prepared, n=int(arguments.get("n", 10))),
            "cancellation_summary": lambda: cancellation_summary(prepared),
            "top_skus_by_revenue": lambda: top_skus_by_revenue(prepared, n=int(arguments.get("n", 20))),
            "revenue_by_size": lambda: revenue_by_size(prepared),
            "category_cancellation_summary": lambda: category_cancellation_summary(prepared),
            "fulfilment_summary": lambda: fulfilment_summary(prepared),
            "courier_summary": lambda: courier_summary(prepared),
            "promotion_summary": lambda: promotion_summary(prepared),
            "b2b_summary": lambda: b2b_summary(prepared),
            "top_cities_by_revenue": lambda: top_cities_by_revenue(prepared, n=int(arguments.get("n", 20))),
            "state_cancellation_summary": lambda: state_cancellation_summary(prepared, min_orders=int(arguments.get("min_orders", 1000)), n=int(arguments.get("n", 20))),
        }
        if tool_name not in ecommerce_tools:
            raise ValueError(f"Unsupported tool: {tool_name}")
        return ecommerce_tools[tool_name]()

    def _execute_python_tool(self, raw_df, code: str) -> dict[str, Any]:
        current_code = code
        for retry_count in range(3):
            run_result = execute_pandas_code(raw_df, current_code)
            if run_result["success"]:
                return {"stdout": run_result["stdout"], "result": run_result["result"], "code_executed": current_code}
            if retry_count == 2 or not run_result.get("traceback"):
                raise ValueError(run_result["error"])
            debug_prompt = [
                {"role": "system", "content": "You are a professional Python/Pandas debugging assistant. Correct the code to make it run successfully. Return ONLY valid JSON with key 'code'."},
                {"role": "user", "content": json.dumps({"code": current_code, "error": run_result["error"], "traceback": run_result["traceback"], "valid_columns": list(raw_df.columns)}, ensure_ascii=False)},
            ]
            try:
                content = self.provider.chat(debug_prompt, format_json=True, timeout=settings.ollama_explain_timeout)
                current_code = json.loads(content).get("code", current_code)
            except Exception as exc:
                raise ValueError(f"Self-correction failed: {exc}") from exc
        raise ValueError("Code execution failed.")

    def _explain_result(
        self,
        question: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        result_summary: dict[str, Any],
        mode: str,
        semantic_profile: DatasetSemanticProfile | None,
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        deterministic_card = compose_answer_card(
            question=question,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            result_summary=result_summary,
            semantic_profile=semantic_profile,
            warnings=warnings or [],
            answer_source="deterministic_composer",
        )
        deterministic_answer = answer_card_to_text(deterministic_card)
        if mode == "fast":
            return {"answer": deterministic_answer, "answer_card": deterministic_card, "source": "deterministic_fallback", "warnings": []}
        explain_result = _compact_result_for_llm(result)
        content = {
            "question": question,
            "tool_name": tool_name,
            "arguments": arguments,
            "domain": getattr(semantic_profile, "domain", "generic") if semantic_profile else "generic",
            "semantic_roles": _compact_semantic_profile(semantic_profile) if semantic_profile else {},
            "deterministic_answer_card": deterministic_card,
            "tool_result": explain_result,
            "rules": [
                "BẮT BUỘC trả ONLY valid JSON theo schema AnswerCard. Không markdown, không text ngoài JSON.",
                "Viết hoàn toàn bằng Tiếng Việt chuyên nghiệp, thân thiện.",
                "Chỉ được polish headline, summary, key_takeaways, why_it_matters, recommended_next_questions.",
                "Không thay evidence, data_warnings, calculation_notes từ deterministic_answer_card.",
                "Tuyệt đối không bịa số liệu hoặc thêm số ngoài tool_result/deterministic_answer_card.",
            ],
        }
        messages = [
            {"role": "system", "content": "You are a senior business intelligence consultant. Return ONLY valid JSON matching the AnswerCard schema. Write in professional Vietnamese. Do not invent numbers."},
            {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
        ]
        try:
            if hasattr(self.provider, "explain"):
                answer = self.provider.explain(messages)
            else:
                try:
                    answer = self.provider.chat(messages, timeout=settings.ollama_explain_timeout)
                except TypeError:
                    answer = self.provider.chat(messages)
        except Exception as exc:
            return {"answer": deterministic_answer, "answer_card": deterministic_card, "source": "deterministic_fallback", "warnings": [f"Đã dùng fallback deterministic vì LLM không tạo được phần diễn giải: {str(exc)}"]}
        cleaned = answer.strip()
        if not cleaned:
            return {"answer": deterministic_answer, "answer_card": deterministic_card, "source": "deterministic_fallback", "warnings": ["LLM trả về diễn giải rỗng, nên hệ thống đã dùng fallback deterministic."]}
        try:
            llm_card = json.loads(cleaned)
            polished_card = merge_llm_answer_card(deterministic_card, llm_card)
            return {"answer": answer_card_to_text(polished_card), "answer_card": polished_card, "source": "llm", "warnings": []}
        except Exception as exc:
            return {
                "answer": deterministic_answer,
                "answer_card": deterministic_card,
                "source": "deterministic_fallback",
                "warnings": [f"Đã dùng fallback deterministic vì LLM trả về answer card không hợp lệ: {str(exc)}"],
            }

    def status(self) -> dict[str, Any]:
        if hasattr(self.provider, "status"):
            return self.provider.status()
        return {"available": True, "base_url": None, "model": None, "router_model": None, "model_loaded": None, "router_model_loaded": None, "models": [], "error": None}


def _single_step_plan(selection: dict[str, Any], strategy: str) -> dict[str, Any]:
    return {
        "plan_id": str(uuid.uuid4()),
        "strategy": strategy,
        "max_steps": 3,
        "steps": [{
            "tool_name": selection["tool_name"],
            "arguments": selection.get("arguments", {}) or {},
            "purpose": selection.get("reason") or strategy,
        }],
    }


def _multi_step_plan(strategy: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    return {"plan_id": str(uuid.uuid4()), "strategy": strategy, "max_steps": 3, "steps": steps[:3]}


def _rule_based_plan(question: str, df, ecommerce_available: bool, semantic_profile: DatasetSemanticProfile, custom_metrics: list[dict[str, Any]], mode: str) -> dict[str, Any] | None:
    text = _normalize_question(question)
    domain = semantic_profile.domain

    custom_selection = _custom_metric_selection(text, semantic_profile, custom_metrics)
    if custom_selection:
        return _single_step_plan(custom_selection, "custom metric rule-based")

    if ecommerce_available and _has_any(text, ["revenue", "doanh thu", "sales"]) and _has_any(text, ["cancel", "huy", "huỷ", "risk", "rui ro", "rủi ro"]):
        if _has_any(text, ["state", "bang", "tinh", "location", "dia diem"]):
            return _multi_step_plan("ecommerce revenue plus cancellation risk by state", [
                {"tool_name": "top_states_by_revenue", "arguments": {"n": _extract_limit(text, 20)}, "purpose": "Find high revenue states."},
                {"tool_name": "state_cancellation_summary", "arguments": {"min_orders": 100, "n": _extract_limit(text, 20)}, "purpose": "Find state cancellation risk."},
            ])
        return _multi_step_plan("ecommerce category revenue plus cancellation risk", [
            {"tool_name": "revenue_by_category", "arguments": {}, "purpose": "Find category revenue leaders."},
            {"tool_name": "category_cancellation_summary", "arguments": {}, "purpose": "Find category cancellation risk."},
        ])

    if domain == "retail" and _has_any(text, ["margin", "profit", "loi nhuan", "lợi nhuận", "loss", "lo", "lỗ"]):
        return _multi_step_plan("retail margin and opportunity analysis", [
            {"tool_name": "retail_margin_summary", "arguments": {}, "purpose": "Calculate overall margin."},
            {"tool_name": "retail_top_opportunities", "arguments": {"by_role": "category"}, "purpose": "Find high revenue low margin groups."},
            {"tool_name": "retail_loss_analysis", "arguments": {"by_role": "category"}, "purpose": "Find loss-making groups."},
        ])

    if domain == "marketing" and _has_any(text, ["campaign", "chien dich", "chiến dịch", "response", "conversion"]) and _has_any(text, ["best", "tot nhat", "cao nhat", "phan tich", "sau", "deep"]):
        return _multi_step_plan("marketing response analysis", [
            {"tool_name": "marketing_campaign_acceptance", "arguments": {}, "purpose": "Rank campaign acceptance."},
            {"tool_name": "marketing_response_by_segment", "arguments": {"by_role": "country"}, "purpose": "Compare response by customer group."},
            {"tool_name": "marketing_rfm_summary", "arguments": {}, "purpose": "Summarize RFM-like behavior."},
        ])

    if domain == "hr" and _has_any(text, ["attrition", "nghi viec", "nghi việc", "risk", "rui ro"]) and _has_any(text, ["risk", "rui ro", "cao", "highest", "nhom", "nhóm", "vi sao"]):
        return _multi_step_plan("hr attrition risk analysis", [
            {"tool_name": "hr_attrition_by_role", "arguments": {"by_role": "department", "min_rows": 1}, "purpose": "Find attrition by department."},
            {"tool_name": "hr_income_band_attrition", "arguments": {}, "purpose": "Find income band attrition."},
            {"tool_name": "hr_high_risk_segments", "arguments": {"min_rows": 1}, "purpose": "Find combined high-risk segments."},
        ])

    single = _rule_based_selection(question, df, ecommerce_available, semantic_profile)
    return _single_step_plan(single, "rule-based") if single else None


def _rule_based_selection(question: str, df, ecommerce_available: bool, semantic_profile: DatasetSemanticProfile | None = None) -> dict[str, Any] | None:
    text = _normalize_question(question)
    semantic_domain = getattr(semantic_profile, "domain", "generic")
    if _has_any(text, ["missing", "null", "nan", "thieu du lieu", "du lieu thieu", "gia tri thieu"]):
        return {"tool_name": "get_missing_values", "arguments": {}}
    if _has_any(text, ["duplicate", "trung lap", "trung dong", "dupe"]):
        return {"tool_name": "get_duplicate_rows", "arguments": {}}
    if _has_any(text, ["tong quan", "overview", "summary", "mo ta dataset", "gioi thieu dataset"]):
        return {"tool_name": "get_sales_overview" if ecommerce_available else "get_dataset_overview", "arguments": {}}
    if _has_any(text, ["correlation", "tuong quan"]):
        return {"tool_name": "correlation_analysis", "arguments": {}}
    chart_selection = _chart_selection(text, df, ecommerce_available)
    if chart_selection:
        return chart_selection
    if not ecommerce_available:
        if _has_any(text, ["attrition", "nghi viec", "nghi việc"]):
            return {"tool_name": "semantic_target_summary", "arguments": {"by_role": "department"}}
        if _has_any(text, ["conversion", "response", "campaign", "chien dich", "chiến dịch"]):
            return {"tool_name": "semantic_target_summary", "arguments": {"by_role": "campaign"}}
        if _has_any(text, ["month", "thang", "trend", "xu huong", "monthly", "doanh thu theo thang"]):
            metric_role = "cost" if _has_any(text, ["cost", "chi phi", "chi phí", "shipping"]) else "profit" if _has_any(text, ["profit", "loi nhuan", "lợi nhuận"]) else "quantity" if _has_any(text, ["quantity", "qty", "so luong", "số lượng", "ridership", "accident", "complaint", "response"]) else None
            return {"tool_name": "semantic_time_series", "arguments": {"metric_role": metric_role} if metric_role else {}}
        if _has_any(text, ["category", "segment", "state", "country", "department", "doanh thu", "revenue", "sales"]):
            by_role = "department" if "department" in text else "state" if _has_any(text, ["state", "tinh", "bang"]) else "country" if "country" in text else "category"
            metric_role = "salary" if semantic_domain == "hr" else "revenue"
            return {"tool_name": "semantic_breakdown", "arguments": {"by_role": by_role, "metric_role": metric_role}}
        return None
    if _has_any(text, ["sku", "san pham", "product", "ma hang"]):
        return {"tool_name": "top_skus_by_revenue", "arguments": {"n": _extract_limit(text, 20)}}
    if _has_any(text, ["size", "kich co", "co nao"]):
        return {"tool_name": "revenue_by_size", "arguments": {}}
    if _has_any(text, ["promotion", "promo", "khuyen mai", "ma giam gia"]):
        return {"tool_name": "promotion_summary", "arguments": {}}
    if _has_any(text, ["b2b", "business", "doanh nghiep"]):
        return {"tool_name": "b2b_summary", "arguments": {}}
    if _has_any(text, ["fulfilment", "fulfillment", "xu ly don", "don vi xu ly"]):
        return {"tool_name": "fulfilment_summary", "arguments": {}}
    if _has_any(text, ["courier", "van chuyen", "giao hang", "ship status"]):
        return {"tool_name": "courier_summary", "arguments": {}}
    if _has_any(text, ["cancel", "cancellation", "huy", "huỷ", "risk", "rui ro"]):
        if _has_any(text, ["state", "bang", "tinh", "thanh pho", "city", "location", "dia diem"]):
            return {"tool_name": "state_cancellation_summary", "arguments": {"min_orders": 100, "n": _extract_limit(text, 20)}}
        if _has_any(text, ["category", "danh muc", "nganh hang"]):
            return {"tool_name": "category_cancellation_summary", "arguments": {}}
        if _has_any(text, ["fulfilment", "fulfillment"]):
            return {"tool_name": "fulfilment_summary", "arguments": {}}
        return {"tool_name": "cancellation_summary", "arguments": {}}
    if _has_any(text, ["month", "thang", "trend", "xu huong", "monthly"]):
        return {"tool_name": "revenue_by_month", "arguments": {}}
    if _has_any(text, ["category", "danh muc", "nganh hang"]):
        return {"tool_name": "revenue_by_category", "arguments": {}}
    if _has_any(text, ["city", "thanh pho"]):
        return {"tool_name": "top_cities_by_revenue", "arguments": {"n": _extract_limit(text, 20)}}
    if _has_any(text, ["state", "bang", "tinh", "location", "dia diem", "khu vuc"]):
        return {"tool_name": "top_states_by_revenue", "arguments": {"n": _extract_limit(text, 10)}}
    if _has_any(text, ["revenue", "doanh thu", "sales"]):
        return {"tool_name": "get_sales_overview", "arguments": {}}
    return None


def _deterministic_explanation(tool_name: str, arguments: dict[str, Any], result: Any) -> str | None:
    if tool_name == "multi_step" and isinstance(result, dict):
        parts = []
        for item in result.get("tool_results", [])[:3]:
            summary = _deterministic_explanation(item["tool_name"], item.get("arguments", {}), item.get("result"))
            if summary:
                parts.append(summary)
        return " ".join(parts) if parts else "Mình đã chạy nhiều tool deterministic để trả lời câu hỏi này."
    if tool_name == "generate_chart_spec":
        return f"Mình đã tạo biểu đồ `{arguments.get('chart_type', 'chart')}` với trục X là `{arguments.get('x')}`" + (f" và trục Y là `{arguments.get('y')}`." if arguments.get("y") else ".")
    if tool_name == "get_sales_overview" and isinstance(result, dict):
        return f"Tổng quan ecommerce: doanh thu {_fmt_number(result.get('total_revenue'))}, {_fmt_number(result.get('unique_orders'))} đơn hàng unique, tỉ lệ huỷ {_fmt_percent(result.get('cancel_rate'))}, tổng số lượng {_fmt_number(result.get('total_qty'))}."
    if tool_name == "get_dataset_overview" and isinstance(result, dict):
        return f"Tổng quan dataset: {_fmt_number(result.get('rows'))} dòng, {_fmt_number(result.get('columns'))} cột, {_fmt_number(result.get('duplicate_rows'))} dòng trùng lặp."
    if tool_name in {"get_missing_values", "get_duplicate_rows"} and isinstance(result, dict):
        return f"Công cụ `{tool_name}` đã chạy xong. Xem chi tiết trong kết quả công cụ."
    if tool_name in {"promotion_summary", "b2b_summary", "retail_margin_summary", "marketing_rfm_summary"} and isinstance(result, dict):
        metric, value = _best_metric(result)
        return f"Kết quả nổi bật từ `{tool_name}`: `{metric}` = {_fmt_number(value)}."
    if tool_name in {"cancellation_summary"} and isinstance(result, dict):
        return f"Tỉ lệ huỷ tổng thể là {_fmt_percent(result.get('overall_cancel_rate'))}."
    if isinstance(result, list):
        if not result:
            return f"Công cụ `{tool_name}` đã chạy nhưng không có dòng kết quả phù hợp."
        first = result[0]
        label = _best_label(first)
        metric_name, metric_value = _best_metric(first)
        extra = f", cancel/positive rate {_fmt_percent(first.get('cancel_rate') or first.get('positive_rate') or first.get('attrition_rate'))}" if any(key in first for key in ["cancel_rate", "positive_rate", "attrition_rate"]) else ""
        return f"Công cụ `{tool_name}` đã chạy thành công. Kết quả nổi bật: `{label}` đứng đầu theo `{metric_name}` với giá trị {_fmt_number(metric_value)}{extra}."
    if isinstance(result, dict) and "items" in result:
        return _deterministic_explanation(tool_name, arguments, result.get("items") or [])
    if tool_name == "correlation_analysis" and isinstance(result, dict):
        correlations = result.get("correlations") or []
        useful = [row for row in correlations if row.get("column_a") != row.get("column_b") and isinstance(row.get("correlation"), (int, float))]
        if not useful:
            return result.get("warning") or "Chưa có đủ cột numeric để phân tích tương quan."
        top = max(useful, key=lambda row: abs(row["correlation"]))
        return f"Tương quan mạnh nhất là `{top['column_a']}` với `{top['column_b']}`, hệ số {top['correlation']:.3f}."
    return None


def _result_summary(result: Any, tool_name: str) -> dict[str, Any]:
    has_chart = tool_name == "generate_chart_spec"
    if tool_name == "multi_step" and isinstance(result, dict):
        rows = result.get("tool_results", [])
        return {"row_count": len(rows), "top_item": rows[0] if rows else None, "primary_metric": "tool_steps", "primary_metric_value": len(rows), "has_chart": any(item.get("tool_name") == "generate_chart_spec" for item in rows), "result_type": "multi_step"}
    if isinstance(result, list):
        top_item = result[0] if result else None
        metric, value = _best_metric(top_item or {})
        return {"row_count": len(result), "top_item": top_item, "primary_metric": metric, "primary_metric_value": value, "has_chart": has_chart, "result_type": "list"}
    if isinstance(result, dict):
        if has_chart:
            return {"row_count": len(result.get("data", [])) if isinstance(result.get("data"), list) else None, "top_item": None, "primary_metric": "chart_traces", "primary_metric_value": len(result.get("data", [])) if isinstance(result.get("data"), list) else None, "has_chart": True, "result_type": "chart"}
        rows = result.get("items") if isinstance(result.get("items"), list) else None
        if rows is not None:
            top_item = rows[0] if rows else None
            metric, value = _best_metric(top_item or {})
            return {"row_count": len(rows), "top_item": top_item, "primary_metric": metric, "primary_metric_value": value, "has_chart": False, "result_type": "dict_with_items"}
        metric, value = _best_metric(result)
        return {"row_count": None, "top_item": None, "primary_metric": metric, "primary_metric_value": value, "has_chart": False, "result_type": "dict"}
    return {"row_count": None, "top_item": result, "primary_metric": None, "primary_metric_value": None, "has_chart": has_chart, "result_type": type(result).__name__}


def _quick_actions(tool_name: str, result: Any, result_summary: dict[str, Any]) -> list[dict[str, Any]]:
    actions = [{"action": "export_result", "label": "Xuất kết quả", "payload": {"format": "json"}}]
    if result_summary.get("has_chart"):
        actions.insert(0, {"action": "view_chart", "label": "Xem biểu đồ", "payload": {}})
    actions.append({"action": "ask_followup", "label": "Hỏi tiếp", "payload": {"question": _followup_question(tool_name)}})
    actions.append({"action": "add_to_report", "label": "Thêm vào báo cáo", "payload": {}})
    actions.append({"action": "explain_calculation", "label": "Giải thích cách tính", "payload": {}})
    return actions


def _followup_question(tool_name: str) -> str:
    followups = {
        "multi_step": "Insight nào quan trọng nhất từ các tool vừa chạy?",
        "retail_top_opportunities": "Segment nào margin thấp dù sales cao?",
        "marketing_campaign_acceptance": "Campaign nào response tốt nhất?",
        "hr_high_risk_segments": "Nhóm nhân viên nào attrition risk cao?",
        "top_skus_by_revenue": "Vẽ biểu đồ top SKU theo doanh thu.",
        "revenue_by_category": "Category nào revenue cao nhưng cancel rate cũng cao?",
    }
    return followups.get(tool_name, "Gợi ý insight tiếp theo từ kết quả này.")


def _compact_result_for_llm(result: Any) -> Any:
    if isinstance(result, list):
        return result[:10]
    if isinstance(result, dict):
        if "data" in result and "layout" in result:
            return {"chart": True, "trace_count": len(result.get("data", [])) if isinstance(result.get("data"), list) else None}
        compact = {}
        for key, value in result.items():
            if isinstance(value, list):
                compact[key] = value[:10]
            elif isinstance(value, dict):
                compact[key] = dict(list(value.items())[:20])
            else:
                compact[key] = value
        return compact
    return result


def _compact_semantic_profile(profile: DatasetSemanticProfile) -> dict[str, Any]:
    return {"domain": profile.domain, "roles": {role: match.column for role, match in profile.roles.items()}, "warnings": profile.warnings}


def _fallback_selection(question: str, ecommerce_available: bool) -> dict[str, Any]:
    if ecommerce_available:
        return {"tool_name": "get_sales_overview", "arguments": {}, "reason": "fallback to ecommerce overview"}
    return {"tool_name": "get_dataset_overview", "arguments": {}, "reason": "fallback to dataset overview"}


def _custom_metric_selection(text: str, semantic_profile: DatasetSemanticProfile, custom_metrics: list[dict[str, Any]]) -> dict[str, Any] | None:
    metric = _matching_custom_metric(text, custom_metrics)
    if not metric:
        return None
    by_role = None
    for role, keywords in {
        "category": ["category", "danh muc", "nganh hang"],
        "segment": ["segment", "phan khuc"],
        "state": ["state", "tinh", "bang"],
        "country": ["country", "quoc gia"],
        "department": ["department", "phong ban"],
        "job_role": ["job role", "jobrole", "chuc danh"],
        "campaign": ["campaign", "chien dich"],
    }.items():
        if role in semantic_profile.roles and _has_any(text, keywords):
            by_role = role
            break
    if by_role:
        return {"tool_name": "custom_metric_breakdown", "arguments": {"metric_name": metric["name"], "by_role": by_role}, "reason": f"custom metric `{metric['name']}` breakdown"}
    return {"tool_name": "evaluate_custom_metric", "arguments": {"metric_name": metric["name"]}, "reason": f"custom metric `{metric['name']}` evaluation"}


def _matching_custom_metric(text: str, custom_metrics: list[dict[str, Any]]) -> dict[str, Any] | None:
    for metric in custom_metrics:
        names = [str(metric.get("name", "")), str(metric.get("label", ""))]
        for name in names:
            if name and _normalize_question(name).replace("_", " ") in text.replace("_", " "):
                return metric
    return None


def _tool_error_response(tool_name: str, arguments: dict[str, Any], exc: Exception, timeline: list[dict[str, Any]], started_at: float) -> dict[str, Any]:
    _timeline(timeline, started_at, "completed", "error", "Agent response completed with a tool error.")
    answer_card = compose_tool_error_card(tool_name, arguments, str(exc))
    return {
        "answer": answer_card_to_text(answer_card),
        "answer_card": answer_card,
        "tool_call": {"tool_name": tool_name, "arguments": arguments, "result": None, "error": str(exc)},
        "data": None,
        "chart": None,
        "warnings": [str(exc)],
        "execution_timeline": timeline,
        "result_summary": {"row_count": None, "top_item": None, "primary_metric": None, "primary_metric_value": None, "has_chart": False, "result_type": "error"},
        "explanation_source": "tool_error",
        "quick_actions": [{"action": "ask_followup", "label": "Hỏi lại rõ hơn", "payload": {"question": "Hãy tổng quan dataset này trước."}}],
    }


def _timeline(timeline: list[dict[str, Any]], started_at: float, step: str, status: str, detail: str | None = None, metadata: dict[str, Any] | None = None) -> None:
    timeline.append({"step": step, "status": status, "detail": detail, "elapsed_ms": _elapsed_ms(started_at), "metadata": metadata or {}})


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 2)


def _best_label(row: dict[str, Any]) -> str:
    for key in ["sku", "category", "Segment", "segment", "size", "ship_state", "ship_city", "order_month", "fulfilment", "courier_status", "department", "jobrole", "campaign", "channel", "country"]:
        if key in row:
            return str(row.get(key))
    first_key = next(iter(row), "row")
    return str(row.get(first_key))


def _best_metric(row: dict[str, Any]) -> tuple[str, Any]:
    for key in ["value", "revenue", "Sales", "Profit", "profit", "margin", "total_revenue", "orders", "qty", "cancel_rate", "positive_rate", "attrition_rate", "avg_amount", "rows"]:
        if key in row:
            return key, row.get(key)
    for key, value in row.items():
        if isinstance(value, (int, float)):
            return key, value
    return "value", None


def _fmt_number(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    if value is None:
        return "Không có dữ liệu"
    return str(value)


def _fmt_percent(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value * 100:.2f}%"
    return "Không có dữ liệu"


def _chart_selection(text: str, df, ecommerce_available: bool) -> dict[str, Any] | None:
    if not _has_any(text, ["chart", "plot", "visual", "bieu do", "biểu đồ", "ve ", "vẽ "]):
        return None
    if ecommerce_available:
        if _has_any(text, ["month", "thang", "trend", "xu huong"]):
            return {"tool_name": "generate_chart_spec", "arguments": {"chart_type": "line", "x": "Date", "y": "Amount"}}
        if _has_any(text, ["category", "danh muc", "nganh hang"]):
            return {"tool_name": "generate_chart_spec", "arguments": {"chart_type": "bar", "x": "Category", "y": "Amount"}}
    return _fallback_chart_selection(df)


def _fallback_chart_selection(df) -> dict[str, Any]:
    numeric_columns = [column for column in df.columns if hasattr(df[column], "dtype") and str(df[column].dtype) != "object"]
    categorical_columns = [column for column in df.columns if hasattr(df[column], "dtype") and str(df[column].dtype) == "object"]
    preferred_x = ["Category", "category", "Segment", "segment", "State", "ship-state", "Date", "date"]
    preferred_y = ["Amount", "Sales", "Revenue", "Total", "Price", "Qty", "Quantity"]
    x = next((column for column in preferred_x if column in df.columns), None) or (categorical_columns[0] if categorical_columns else next(iter(df.columns), ""))
    y = next((column for column in preferred_y if column in df.columns and column in numeric_columns), None) or (numeric_columns[0] if numeric_columns else None)
    chart_type = "line" if str(x).lower() in {"date", "order_date", "created_at"} else "bar"
    return {"tool_name": "generate_chart_spec", "arguments": {"chart_type": chart_type, "x": x, "y": y}}


def _normalize_question(question: str) -> str:
    replacements = {
        "đ": "d", "Đ": "d",
        "á": "a", "à": "a", "ả": "a", "ã": "a", "ạ": "a", "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a", "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
        "é": "e", "è": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e", "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
        "í": "i", "ì": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
        "ó": "o", "ò": "o", "ỏ": "o", "õ": "o", "ọ": "o", "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o", "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
        "ú": "u", "ù": "u", "ủ": "u", "ũ": "u", "ụ": "u", "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
        "ý": "y", "ỳ": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
    }
    text = question.lower()
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _has_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _extract_limit(text: str, default: int) -> int:
    match = re.search(r"\btop\s*(\d+)|\b(\d+)\s*(sku|san pham|state|city|tinh|thanh pho)", text)
    if not match:
        return default
    value = next(group for group in match.groups() if group and group.isdigit())
    return max(1, min(int(value), 100))


def _looks_like_amazon_sales(df) -> bool:
    required = {"Order ID", "Date", "Status", "Category", "Qty", "Amount"}
    normalized = {column.strip() for column in df.columns}
    return required.issubset(normalized)


def _result_mentions_missing_amount(result: Any) -> bool:
    if isinstance(result, dict):
        if result.get("missing_amount_rows"):
            return True
        return any(_result_mentions_missing_amount(value) for value in result.values())
    if isinstance(result, list):
        return any(_result_mentions_missing_amount(item) for item in result)
    return False
