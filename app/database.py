import json
from datetime import datetime

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"

    dataset_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    size = Column(Integer, default=0)
    semantic_version = Column(Integer, default=0)
    
    # Store semantic overrides as JSON string
    semantic_overrides_json = Column(Text, default="{}")
    data_dictionary_json = Column(Text, default="{}")
    custom_metrics_json = Column(Text, default="[]")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @property
    def semantic_overrides(self) -> dict:
        try:
            return json.loads(self.semantic_overrides_json)
        except Exception:
            return {"domain": None, "roles": {}}
            
    @semantic_overrides.setter
    def semantic_overrides(self, value: dict):
        self.semantic_overrides_json = json.dumps(value)

    @property
    def data_dictionary(self) -> dict | None:
        try:
            data = json.loads(self.data_dictionary_json or "{}")
        except Exception:
            return None
        return data or None

    @data_dictionary.setter
    def data_dictionary(self, value: dict | None):
        self.data_dictionary_json = json.dumps(value or {})

    @property
    def custom_metrics(self) -> list[dict]:
        try:
            data = json.loads(self.custom_metrics_json or "[]")
        except Exception:
            return []
        return data if isinstance(data, list) else []

    @custom_metrics.setter
    def custom_metrics(self, value: list[dict] | None):
        self.custom_metrics_json = json.dumps(value or [])


class SemanticCache(Base):
    __tablename__ = "semantic_caches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dataset_id = Column(String, index=True)
    question = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=False)
    response_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_dataset_metadata_columns()


def _ensure_dataset_metadata_columns() -> None:
    inspector = inspect(engine)
    if "dataset_metadata" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("dataset_metadata")}
    with engine.begin() as connection:
        if "data_dictionary_json" not in columns:
            connection.execute(text("ALTER TABLE dataset_metadata ADD COLUMN data_dictionary_json TEXT DEFAULT '{}'"))
        if "custom_metrics_json" not in columns:
            connection.execute(text("ALTER TABLE dataset_metadata ADD COLUMN custom_metrics_json TEXT DEFAULT '[]'"))


init_database()
