from __future__ import annotations

from io import BytesIO

import pandas as pd


SUPPORTED_UPLOAD_EXTENSIONS = {".csv", ".xls", ".xlsx"}
CSV_ENCODING_CANDIDATES = ("utf-8-sig", "utf-8", "cp1252", "latin1")


def load_tabular_file(content: bytes, filename: str) -> pd.DataFrame:
    extension = _extension(filename)
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_UPLOAD_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{extension}'. Supported types: {allowed}.")

    buffer = BytesIO(content)
    if extension == ".csv":
        return _read_csv_with_encoding_fallback(content)
    if extension == ".xls":
        return pd.read_excel(buffer, engine="xlrd")
    if extension == ".xlsx":
        return pd.read_excel(buffer, engine="openpyxl")

    raise ValueError(f"Unsupported file type '{extension}'.")


def _read_csv_with_encoding_fallback(content: bytes) -> pd.DataFrame:
    errors: list[str] = []
    for encoding in CSV_ENCODING_CANDIDATES:
        try:
            return pd.read_csv(BytesIO(content), low_memory=False, encoding=encoding)
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
        except UnicodeError as exc:
            errors.append(f"{encoding}: {exc}")
    joined_errors = "; ".join(errors)
    raise ValueError(
        "CSV encoding is not supported. Tried encodings "
        f"{', '.join(CSV_ENCODING_CANDIDATES)}. Details: {joined_errors}"
    )


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()
