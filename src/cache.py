"""Cache utilities for LLM response caching."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from src.database import LLMCache


def generate_cache_key(
    provider_name: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    json_schema: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Generate deterministic SHA256 cache key from request parameters.

    Args:
        provider_name: Name of the LLM provider (e.g., "cerebras")
        model: Model identifier (e.g., "llama3.1-70b")
        messages: Chat messages array
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        top_p: Nucleus sampling parameter
        json_schema: JSON schema for structured outputs
        **kwargs: Additional parameters that affect output

    Returns:
        64-character hex string (SHA256 hash)
    """
    payload: dict[str, Any] = {
        "v": "1",  # Cache version for future invalidation
        "provider": provider_name.lower(),
        "model": model.lower(),
        "messages": messages,
        "temperature": round(temperature, 2),
    }

    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if top_p is not None:
        payload["top_p"] = round(top_p, 2)
    if json_schema is not None:
        payload["json_schema"] = json_schema

    # Add any extra params that affect output
    for k in sorted(kwargs.keys()):
        if kwargs[k] is not None:
            payload[k] = kwargs[k]

    content = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class CacheRepository:
    """Repository for LLM response cache operations."""

    def __init__(self, session: Session):
        """Initialize with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def get(self, cache_key: str) -> Optional[str]:
        """Get cached response by key.

        Args:
            cache_key: The cache key to look up

        Returns:
            Response string if found, None otherwise
        """
        entry = (
            self.session.query(LLMCache)
            .filter(LLMCache.cache_key == cache_key)
            .first()
        )
        if entry:
            # Increment hit count
            entry.hit_count += 1
            self.session.commit()
            return entry.response
        return None

    def put(
        self,
        cache_key: str,
        provider_name: str,
        model: str,
        prompt_preview: str,
        response: str,
    ) -> None:
        """Store response in cache. Upserts if key exists.

        Args:
            cache_key: The cache key
            provider_name: Name of the LLM provider
            model: Model identifier
            prompt_preview: First 200 chars of prompt for debugging
            response: The full response to cache
        """
        stmt = insert(LLMCache).values(
            cache_key=cache_key,
            provider_name=provider_name,
            model=model,
            prompt_preview=prompt_preview[:200],
            response=response,
            created_at=datetime.now(timezone.utc),
            hit_count=0,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["cache_key"],
            set_=dict(
                response=stmt.excluded.response,
                created_at=stmt.excluded.created_at,
                hit_count=0,
            ),
        )
        self.session.execute(stmt)
        self.session.commit()

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Count of deleted entries
        """
        count = self.session.query(LLMCache).delete()
        self.session.commit()
        return count

    def stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with total_entries and total_hits
        """
        total = self.session.query(func.count(LLMCache.cache_key)).scalar() or 0
        total_hits = self.session.query(func.sum(LLMCache.hit_count)).scalar() or 0
        return {"total_entries": total, "total_hits": total_hits}
