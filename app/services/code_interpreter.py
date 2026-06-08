"""
Sandboxed Python/Pandas code execution with:
- Process isolation via ProcessPoolExecutor
- Hard timeout (default 10s) to prevent runaway code
- Restricted builtins (no os, sys, subprocess, etc.)
- Stdout capture
- Multi-table support via LazyDataFrameDict
"""
from __future__ import annotations

import concurrent.futures
import contextlib
import io
import traceback
from typing import Any

import pandas as pd

from app.services.storage import dataset_store


# ── Constants ─────────────────────────────────────────────────────────────────
MAX_EXEC_SECONDS = 10
MAX_RESULT_ROWS = 100

_UNSAFE_KEYWORDS: list[str] = [
    "os.", "sys.", "subprocess", "open(", "eval(", "exec(",
    "import ", "getattr", "setattr", "globals", "__import__",
    "__class__", "__bases__", "__subclasses__", "builtins",
]

_SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
    "chr": chr, "dict": dict, "dir": dir, "divmod": divmod,
    "enumerate": enumerate, "filter": filter, "float": float,
    "format": format, "hash": hash, "hex": hex, "id": id,
    "int": int, "isinstance": isinstance, "issubclass": issubclass,
    "iter": iter, "len": len, "list": list, "map": map, "max": max,
    "min": min, "next": next, "object": object, "oct": oct,
    "ord": ord, "pow": pow, "print": print, "range": range,
    "repr": repr, "reversed": reversed, "round": round, "set": set,
    "slice": slice, "sorted": sorted, "str": str, "sum": sum,
    "tuple": tuple, "type": type, "zip": zip,
}


# ── Multi-file lazy loader ────────────────────────────────────────────────────

class LazyDataFrameDict(dict):
    """Loads DataFrames on-demand for multi-table operations via `dfs['file.csv']`."""

    def __init__(self, store: Any, datasets_meta: dict[str, Any]) -> None:
        self.store = store
        self.meta = datasets_meta
        self.name_to_id: dict[str, str] = {
            meta["filename"]: did for did, meta in datasets_meta.items()
        }
        super().__init__()

    def __getitem__(self, key: str) -> pd.DataFrame:
        if key in self.name_to_id:
            return self.store.load_dataframe(self.name_to_id[key])
        available = list(self.name_to_id.keys())
        raise KeyError(f"Dataset '{key}' not found. Available: {available}")

    def __contains__(self, key: object) -> bool:
        return key in self.name_to_id

    def keys(self):  # type: ignore[override]
        return self.name_to_id.keys()


# ── Core execution (runs in subprocess) ──────────────────────────────────────

def _execute_in_subprocess(
    code: str,
    df_records: list[dict[str, Any]],
    df_columns: list[str],
    datasets_meta: dict[str, Any],
    upload_dir: str,
) -> dict[str, Any]:
    """
    Isolated execution context — runs in a separate process.
    Reconstructs DataFrame from records to avoid pickling issues.
    """
    import io as _io
    import contextlib as _ctx
    import traceback as _tb
    import pandas as _pd
    from pathlib import Path

    df = _pd.DataFrame(df_records, columns=df_columns)
    stdout_buf = _io.StringIO()

    # Minimal lazy-loader that doesn't depend on store object (pickling issue)
    class _SimpleLazy(dict):
        def __getitem__(self, key):
            for did, meta in datasets_meta.items():
                if meta.get("filename") == key:
                    path = Path(upload_dir) / f"{did}.csv"
                    return _pd.read_csv(str(path), low_memory=False)
            raise KeyError(f"Dataset '{key}' not found.")
        def __contains__(self, key):
            return any(m.get("filename") == key for m in datasets_meta.values())
        def keys(self):
            return [m.get("filename") for m in datasets_meta.values()]

    local_vars: dict[str, Any] = {
        "df": df,
        "pd": _pd,
        "dfs": _SimpleLazy(),
    }
    global_vars: dict[str, Any] = {"__builtins__": _SAFE_BUILTINS}

    try:
        with _ctx.redirect_stdout(stdout_buf):
            exec(code, global_vars, local_vars)  # noqa: S102
        stdout_out = stdout_buf.getvalue()
        result_val = local_vars.get("result")

        if isinstance(result_val, _pd.DataFrame):
            result_val = (
                result_val.head(MAX_RESULT_ROWS)
                .astype(object)
                .where(_pd.notna(result_val.head(MAX_RESULT_ROWS)), None)
                .to_dict(orient="records")
            )
        elif isinstance(result_val, _pd.Series):
            result_val = result_val.head(MAX_RESULT_ROWS).to_dict()

        return {
            "success": True,
            "error": None,
            "stdout": stdout_out,
            "result": result_val if result_val is not None else stdout_out,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "traceback": _tb.format_exc(),
            "stdout": stdout_buf.getvalue(),
            "result": None,
        }


# ── Public API ────────────────────────────────────────────────────────────────

def execute_pandas_code(df: pd.DataFrame, code: str) -> dict[str, Any]:
    """
    Execute Python/Pandas code safely with:
    1. Keyword security scan
    2. Process isolation (separate Python process)
    3. Hard timeout (MAX_EXEC_SECONDS)
    """
    # 1. Security keyword scan
    for keyword in _UNSAFE_KEYWORDS:
        if keyword in code:
            return {
                "success": False,
                "error": f"Security Block: unsafe keyword '{keyword}' is not allowed.",
                "stdout": "",
                "result": None,
            }

    # 2. Submit to isolated process
    df_records = df.to_dict(orient="records")
    df_columns = list(df.columns)
    datasets_meta = dict(dataset_store.datasets)
    upload_dir = "data/uploads"

    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _execute_in_subprocess,
                code,
                df_records,
                df_columns,
                datasets_meta,
                upload_dir,
            )
            try:
                return future.result(timeout=MAX_EXEC_SECONDS)
            except concurrent.futures.TimeoutError:
                future.cancel()
                return {
                    "success": False,
                    "error": f"Execution timed out after {MAX_EXEC_SECONDS} seconds.",
                    "stdout": "",
                    "result": None,
                }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Process execution error: {exc}",
            "traceback": traceback.format_exc(),
            "stdout": "",
            "result": None,
        }
