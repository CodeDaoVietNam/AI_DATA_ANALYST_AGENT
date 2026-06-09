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
            logger.warning("embedding unavailable: Ollama response status code not 200 or embeddings empty")
            return None
        except Exception as exc:
            logger.warning(f"embedding unavailable: Failed to generate embedding for cache: {exc}")
            return None

    def query_cache_detailed(self, dataset_id: str, question: str, threshold: float = 0.88) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        # Log embedding request
        try:
            current_embedding = self.get_embedding(question)
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            logger.info("cache lookup skipped due to error")
            return None, {
                "status": "error",
                "reason": f"Error generating embedding: {str(e)}",
                "similarity": None
            }

        if not current_embedding:
            logger.info("embedding unavailable: cache lookup skipped")
            # Fallback to exact keyword matching
            try:
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
                        res = json.loads(cached.response_json)
                        res["explanation_source"] = "semantic_cache_exact"
                        logger.info(f"Semantic Cache HIT! (Exact match) for question: '{question}'")
                        return res, {
                            "status": "hit",
                            "reason": "Exact match found without embedding",
                            "similarity": 1.0
                        }
            except Exception as e:
                logger.error(f"Exact match check failed: {e}")
                return None, {
                    "status": "error",
                    "reason": f"Exact match failed: {str(e)}",
                    "similarity": None
                }
            
            return None, {
                "status": "skipped",
                "reason": "Embedding model unavailable",
                "similarity": None
            }

        # Compare cosine similarity with all cached entries for this dataset
        best_similarity = -1.0
        best_cached = None

        try:
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
        except Exception as e:
            logger.error(f"Failed to query semantic cache database: {e}")
            logger.info("cache lookup skipped: database query failed")
            return None, {
                "status": "error",
                "reason": f"Database query failed: {str(e)}",
                "similarity": None
            }

        if best_cached and best_similarity >= threshold:
            try:
                res = json.loads(best_cached.response_json)
                res["explanation_source"] = f"semantic_cache (similarity: {best_similarity:.2f})"
                logger.info(f"Semantic Cache HIT! Match score: {best_similarity:.4f} for question: '{question}'")
                return res, {
                    "status": "hit",
                    "reason": f"Match score: {best_similarity:.4f}",
                    "similarity": round(best_similarity, 4)
                }
            except Exception as e:
                logger.error(f"Error loading response from hit: {e}")
                return None, {
                    "status": "error",
                    "reason": f"JSON parse of cached response failed: {str(e)}",
                    "similarity": round(best_similarity, 4)
                }

        logger.info(f"Semantic Cache MISS. Best score: {best_similarity:.4f} for question: '{question}'")
        return None, {
            "status": "miss",
            "reason": f"Best similarity score: {best_similarity:.4f} below threshold {threshold}",
            "similarity": round(best_similarity, 4) if best_similarity >= 0 else None
        }

    def query_cache(self, dataset_id: str, question: str, threshold: float = 0.88) -> dict[str, Any] | None:
        res, _ = self.query_cache_detailed(dataset_id, question, threshold)
        return res

    def add_to_cache(self, dataset_id: str, question: str, response: dict[str, Any]) -> None:
        try:
            # Avoid caching errors
            if "error" in response:
                logger.info("cache write skipped: response contains error")
                return

            embedding = self.get_embedding(question)
            if not embedding:
                logger.info("cache write skipped: embedding unavailable")
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
