from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from app.services.data_loader import load_tabular_file


def load_manifest(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    datasets = raw.get("datasets") if isinstance(raw, dict) else raw
    if not isinstance(datasets, list):
        raise ValueError("Manifest must contain a `datasets` list.")
    return datasets


def snapshot_dataframe(df: pd.DataFrame, destination: Path, max_rows: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if max_rows and len(df) > max_rows:
        df = df.head(max_rows).copy()
    df = df.copy()
    df.columns = [str(column).strip() for column in df.columns]
    df.to_csv(destination, index=False)


def read_source_file(path: Path) -> pd.DataFrame:
    return load_tabular_file(path.read_bytes(), path.name)


def download_direct(dataset: dict[str, Any]) -> pd.DataFrame:
    url = dataset.get("download_url")
    if not url:
        raise ValueError("Missing download_url for auto_download dataset.")
    response = requests.get(url, timeout=int(dataset.get("download_timeout", 15)))
    response.raise_for_status()
    content = response.content
    filename = Path(url.split("?", 1)[0]).name or f"{dataset['id']}.csv"
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            member = dataset.get("zip_member") or _first_tabular_member(archive)
            if not member:
                raise ValueError(f"No CSV/XLS/XLSX file found in zip for {dataset['id']}.")
            return read_tabular_bytes(archive.read(member), Path(member).name, dataset)
    return read_tabular_bytes(content, filename, dataset)


def read_tabular_bytes(content: bytes, filename: str, dataset: dict[str, Any]) -> pd.DataFrame:
    separator = dataset.get("csv_separator")
    if separator and Path(filename).suffix.lower() == ".csv":
        return pd.read_csv(io.BytesIO(content), sep=str(separator), low_memory=False)
    return load_tabular_file(content, filename)


def _first_tabular_member(archive: zipfile.ZipFile) -> str | None:
    for name in archive.namelist():
        suffix = Path(name).suffix.lower()
        if suffix in {".csv", ".xls", ".xlsx"} and not name.endswith("/"):
            return name
    return None


def process_dataset(dataset: dict[str, Any], root: Path, *, force: bool) -> str:
    destination = root / dataset["local_path"]
    if destination.exists() and not force:
        return f"exists: {dataset['id']} -> {destination}"

    max_rows = int(dataset.get("max_rows") or 10000)
    acquisition = dataset.get("acquisition")

    if dataset.get("source_path"):
        source = root / dataset["source_path"]
        if not source.exists():
            return f"missing local source: {dataset['id']} expected {source}"
        df = read_source_file(source)
        snapshot_dataframe(df, destination, max_rows)
        return f"snapshot: {dataset['id']} -> {destination}"

    if acquisition == "auto_download":
        df = download_direct(dataset)
        snapshot_dataframe(df, destination, max_rows)
        return f"downloaded: {dataset['id']} -> {destination}"

    return (
        f"manual: {dataset['id']} | download from {dataset.get('source_url')} "
        f"and place CSV/XLS/XLSX snapshot at {destination}"
    )


def validate_presence(datasets: list[dict[str, Any]], root: Path) -> tuple[int, list[str]]:
    missing = []
    for dataset in datasets:
        if not (root / dataset["local_path"]).exists():
            missing.append(dataset["local_path"])
    return len(datasets) - len(missing), missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Download or snapshot Phase U5 eval datasets.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default="evals/manifest.json")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    datasets = load_manifest(root / args.manifest)

    if args.validate:
        present, missing = validate_presence(datasets, root)
        print(f"Datasets present: {present}/{len(datasets)}")
        for item in missing:
            print(f"missing: {item}")
        return 0 if present == len(datasets) else 1

    for dataset in datasets:
        try:
            print(process_dataset(dataset, root, force=args.force), flush=True)
        except Exception as exc:
            print(f"error: {dataset.get('id')}: {exc}", flush=True)

    present, missing = validate_presence(datasets, root)
    print(f"Datasets present: {present}/{len(datasets)}", flush=True)
    if missing:
        print("Missing datasets:", flush=True)
        for item in missing:
            print(f"- {item}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
