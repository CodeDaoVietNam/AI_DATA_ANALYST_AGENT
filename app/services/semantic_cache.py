import json
import logging
import requests
from typing import Any
from app.config import settings
from app.database import SessionLocal, SemanticCache

logger = logging.getLogger("app.services.semantic_cache")

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = sum(a * a for a in v1) ** 0.5
    norm_v2 = sum(b * b for b in v2) ** 0.5
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

class LocalSemanticCacheService:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model

    def get_embedding(self, text: str) -> list[float] | None:
        try:
            payload = {"model": self.model, "input": text}
            response = requests.post(
                f"{self.base_url}/api/embed", 
                json=payload, 
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                embeddings = data.get("embeddings")
                if embeddings and isinstance(embeddings, list) and len(embeddings) > 0:
                    return embeddings[0]
            return None
        except Exception as exc:
            logger.warning(f"Failed to generate embedding for cache: {exc}")
            return None

    def query_cache(self, dataset_id: str, question: str, threshold: float = 0.88) -> dict[str, Any] | None:
        # First, attempt to get embedding for the query
        current_embedding = self.get_embedding(question)
        if not current_embedding:
            # Fallback to exact keyword matching if embedding service is down
            with SessionLocal() as db:
                cached = (
                    db.query(SemanticCache)
                    .filter(
                        SemanticCache.dataset_id == dataset_id,
                        SemanticCache.question == question
                    )
                    .first()
                )
                if cached:
                    try:
                        res = json.loads(cached.response_json)
                        res["explanation_source"] = "semantic_cache_exact"
                        return res
                    except Exception:
                        return None
            return None

        # Compare cosine similarity with all cached entries for this dataset
        best_similarity = -1.0
        best_cached = None

        with SessionLocal() as db:
            records = db.query(SemanticCache).filter(SemanticCache.dataset_id == dataset_id).all()
            for record in records:
                try:
                    cached_emb = json.loads(record.embedding_json)
                    sim = cosine_similarity(current_embedding, cached_emb)
                    if sim > best_similarity:
                        best_similarity = sim
                        best_cached = record
                except Exception as exc:
                    logger.warning(f"Error parsing cached embedding: {exc}")
                    continue

        if best_cached and best_similarity >= threshold:
            try:
                res = json.loads(best_cached.response_json)
                res["explanation_source"] = f"semantic_cache (similarity: {best_similarity:.2f})"
                logger.info(f"Semantic Cache HIT! Match score: {best_similarity:.4f} for question: '{question}'")
                return res
            except Exception:
                pass
        return None

    def add_to_cache(self, dataset_id: str, question: str, response: dict[str, Any]) -> None:
        try:
            # Avoid caching errors
            if "error" in response:
                return

            embedding = self.get_embedding(question)
            if not embedding:
                return

            # Clean large raw dataset in the response cache if necessary to save DB space
            cache_response = dict(response)
            if "execution_timeline" in cache_response:
                cache_response.pop("execution_timeline")

            with SessionLocal() as db:
                # Check if exact question already exists
                existing = (
                    db.query(SemanticCache)
                    .filter(
                        SemanticCache.dataset_id == dataset_id,
                        SemanticCache.question == question
                    )
                    .first()
                )
                if existing:
                    existing.embedding_json = json.dumps(embedding)
                    existing.response_json = json.dumps(cache_response)
                else:
                    new_cache = SemanticCache(
                        dataset_id=dataset_id,
                        question=question,
                        embedding_json=json.dumps(embedding),
                        response_json=json.dumps(cache_response)
                    )
                    db.add(new_cache)
                db.commit()
            logger.info(f"Successfully cached query: '{question}'")
        except Exception as exc:
            logger.error(f"Failed to save semantic cache entry: {exc}")

    def clear_dataset_cache(self, dataset_id: str) -> None:
        try:
            with SessionLocal() as db:
                db.query(SemanticCache).filter(SemanticCache.dataset_id == dataset_id).delete()
                db.commit()
        except Exception as exc:
            logger.error(f"Failed to clear semantic cache for dataset {dataset_id}: {exc}")

semantic_cache_service = LocalSemanticCacheService()
