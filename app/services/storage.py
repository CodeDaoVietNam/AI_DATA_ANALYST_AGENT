from pathlib import Path
import uuid
import pandas as pd

from app.database import SessionLocal, DatasetMetadata

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DatasetStore:
    def save_dataframe(self, df: pd.DataFrame, filename: str) -> str:
        dataset_id = str(uuid.uuid4())
        path = UPLOAD_DIR / f"{dataset_id}.csv"
        df.to_csv(path, index=False)
        
        with SessionLocal() as db:
            stat = path.stat()
            meta = DatasetMetadata(
                dataset_id=dataset_id,
                filename=filename,
                path=str(path),
                size=stat.st_size,
                semantic_overrides_json='{"domain": null, "roles": {}}',
                data_dictionary_json="{}",
                custom_metrics_json="[]",
                semantic_version=1
            )
            db.add(meta)
            db.commit()
        return dataset_id

    def load_dataframe(self, dataset_id: str) -> pd.DataFrame:
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if not meta:
                # Fallback to check file system directly in case of un-migrated dev data
                path = UPLOAD_DIR / f"{dataset_id}.csv"
                if not path.exists():
                    raise ValueError(f"Dataset {dataset_id} not found.")
                return pd.read_csv(path, low_memory=False)
            
            path = Path(meta.path)
            if not path.exists():
                raise ValueError(f"Dataset {dataset_id} file missing from disk.")
            return pd.read_csv(path, low_memory=False)

    def get_filename(self, dataset_id: str) -> str:
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if meta:
                return meta.filename
            return "unknown.csv"

    def get_dataset_signature(self, dataset_id: str) -> dict[str, object]:
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if not meta:
                path = UPLOAD_DIR / f"{dataset_id}.csv"
                if not path.exists():
                    raise ValueError(f"Dataset {dataset_id} not found.")
                stat = path.stat()
                return {
                    "dataset_id": dataset_id,
                    "path": str(path),
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "semantic_version": 0,
                }
            
            path = Path(meta.path)
            if not path.exists():
                raise ValueError(f"Dataset {dataset_id} not found.")
            stat = path.stat()
            return {
                "dataset_id": dataset_id,
                "path": str(path),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "semantic_version": meta.semantic_version,
            }

    def get_semantic_overrides(self, dataset_id: str) -> dict[str, object]:
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if not meta:
                return {"domain": None, "roles": {}}
            overrides = meta.semantic_overrides
            if not isinstance(overrides, dict):
                return {"domain": None, "roles": {}}
            roles = overrides.get("roles") if isinstance(overrides.get("roles"), dict) else {}
            return {"domain": overrides.get("domain"), "roles": dict(roles)}

    def get_data_dictionary(self, dataset_id: str) -> dict | None:
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if not meta:
                return None
            return meta.data_dictionary

    def set_data_dictionary(self, dataset_id: str, dictionary: dict) -> dict:
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if not meta:
                path = UPLOAD_DIR / f"{dataset_id}.csv"
                if not path.exists():
                    raise ValueError(f"Dataset {dataset_id} not found.")
                stat = path.stat()
                meta = DatasetMetadata(
                    dataset_id=dataset_id,
                    filename=path.name,
                    path=str(path),
                    size=stat.st_size,
                    semantic_overrides_json='{"domain": null, "roles": {}}',
                    data_dictionary_json="{}",
                    custom_metrics_json="[]",
                    semantic_version=1,
                )
                db.add(meta)
                db.commit()
                db.refresh(meta)
            meta.data_dictionary = dictionary
            meta.semantic_version += 1
            db.commit()
            db.refresh(meta)
            return meta.data_dictionary or {"domain": None, "fields": []}

    def clear_data_dictionary(self, dataset_id: str) -> None:
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if not meta:
                raise ValueError(f"Dataset {dataset_id} not found.")
            meta.data_dictionary = None
            meta.semantic_version += 1
            db.commit()

    def get_custom_metrics(self, dataset_id: str) -> list[dict]:
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if not meta:
                return []
            return meta.custom_metrics

    def set_custom_metric(self, dataset_id: str, metric: dict) -> dict:
        metric_name = str(metric.get("name") or "").strip()
        if not metric_name:
            raise ValueError("Metric name is required.")
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if not meta:
                path = UPLOAD_DIR / f"{dataset_id}.csv"
                if not path.exists():
                    raise ValueError(f"Dataset {dataset_id} not found.")
                stat = path.stat()
                meta = DatasetMetadata(
                    dataset_id=dataset_id,
                    filename=path.name,
                    path=str(path),
                    size=stat.st_size,
                    semantic_overrides_json='{"domain": null, "roles": {}}',
                    data_dictionary_json="{}",
                    custom_metrics_json="[]",
                    semantic_version=1,
                )
                db.add(meta)
                db.commit()
                db.refresh(meta)
            metrics = [item for item in meta.custom_metrics if item.get("name") != metric_name]
            metrics.append(metric)
            meta.custom_metrics = metrics
            meta.semantic_version += 1
            db.commit()
            db.refresh(meta)
            return metric

    def delete_custom_metric(self, dataset_id: str, metric_name: str) -> None:
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if not meta:
                raise ValueError(f"Dataset {dataset_id} not found.")
            metrics = meta.custom_metrics
            next_metrics = [item for item in metrics if item.get("name") != metric_name]
            if len(next_metrics) == len(metrics):
                raise ValueError(f"Custom metric not found: {metric_name}")
            meta.custom_metrics = next_metrics
            meta.semantic_version += 1
            db.commit()

    def set_semantic_overrides(
        self,
        dataset_id: str,
        *,
        domain: str | None = None,
        roles: dict[str, str | None] | None = None,
    ) -> dict[str, object]:
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if not meta:
                path = UPLOAD_DIR / f"{dataset_id}.csv"
                if not path.exists():
                    raise ValueError(f"Dataset {dataset_id} not found.")
                stat = path.stat()
                meta = DatasetMetadata(
                    dataset_id=dataset_id,
                    filename=path.name,
                    path=str(path),
                    size=stat.st_size,
                    semantic_overrides_json='{"domain": null, "roles": {}}',
                    data_dictionary_json="{}",
                    custom_metrics_json="[]",
                    semantic_version=1
                )
                db.add(meta)
                db.commit()
                db.refresh(meta)

            current = meta.semantic_overrides
            next_roles = dict(current.get("roles", {}))
            for role, column in (roles or {}).items():
                if column is None or column == "":
                    next_roles.pop(role, None)
                else:
                    next_roles[role] = column
            
            meta.semantic_overrides = {
                "domain": domain if domain is not None else current.get("domain"),
                "roles": next_roles,
            }
            meta.semantic_version += 1
            db.commit()
            db.refresh(meta)
            return meta.semantic_overrides

    def clear_semantic_overrides(self, dataset_id: str) -> None:
        with SessionLocal() as db:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
            if not meta:
                raise ValueError(f"Dataset {dataset_id} not found.")
            meta.semantic_overrides = {"domain": None, "roles": {}}
            meta.semantic_version += 1
            db.commit()

    @property
    def datasets(self) -> dict:
        if hasattr(self, "_datasets_mock"):
            return self._datasets_mock
        # Compatibility property for the `/datasets` listing endpoint and health check count
        with SessionLocal() as db:
            all_meta = db.query(DatasetMetadata).all()
            return {
                m.dataset_id: {
                    "filename": m.filename,
                    "path": m.path,
                    "semantic_version": m.semantic_version,
                }
                for m in all_meta
            }

    @datasets.setter
    def datasets(self, value: dict):
        self._datasets_mock = value

dataset_store = DatasetStore()
