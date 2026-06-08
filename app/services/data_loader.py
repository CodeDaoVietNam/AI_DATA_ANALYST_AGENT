from __future__ import annotations

from io import BytesIO

import pandas as pd


SUPPORTED_UPLOAD_EXTENSIONS = {".csv", ".xls", ".xlsx"}


def load_tabular_file(content: bytes, filename: str) -> pd.DataFrame:
    extension = _extension(filename)
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_UPLOAD_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{extension}'. Supported types: {allowed}.")

    buffer = BytesIO(content)
    if extension == ".csv":
        return pd.read_csv(buffer, low_memory=False)
    if extension == ".xls":
        return pd.read_excel(buffer, engine="xlrd")
    if extension == ".xlsx":
        return pd.read_excel(buffer, engine="openpyxl")

    raise ValueError(f"Unsupported file type '{extension}'.")


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()
