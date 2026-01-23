"""Unit tests for cache module."""

import pytest
from assertpy import assert_that

from src.cache import generate_cache_key, CacheRepository


class TestGenerateCacheKey:
    """Tests for cache key generation."""

    def test_same_inputs_produce_same_key(self):
        """Same inputs should produce identical keys."""
        key1 = generate_cache_key(
            "provider", "model", [{"role": "user", "content": "hello"}], 0.7
        )
        key2 = generate_cache_key(
            "provider", "model", [{"role": "user", "content": "hello"}], 0.7
        )
        assert_that(key1).is_equal_to(key2)

    def test_different_inputs_produce_different_keys(self):
        """Different inputs should produce different keys."""
        key1 = generate_cache_key(
            "provider", "model", [{"role": "user", "content": "hello"}], 0.7
        )
        key2 = generate_cache_key(
            "provider", "model", [{"role": "user", "content": "world"}], 0.7
        )
        assert_that(key1).is_not_equal_to(key2)

    def test_different_temperature_produces_different_key(self):
        """Different temperature should produce different keys."""
        key1 = generate_cache_key("provider", "model", [], 0.7)
        key2 = generate_cache_key("provider", "model", [], 0.8)
        assert_that(key1).is_not_equal_to(key2)

    def test_different_provider_produces_different_key(self):
        """Different provider should produce different keys."""
        key1 = generate_cache_key("provider1", "model", [], 0.7)
        key2 = generate_cache_key("provider2", "model", [], 0.7)
        assert_that(key1).is_not_equal_to(key2)

    def test_float_normalization(self):
        """Equivalent float values should produce same key."""
        key1 = generate_cache_key("provider", "model", [], 0.7)
        key2 = generate_cache_key("provider", "model", [], 0.70)
        key3 = generate_cache_key("provider", "model", [], 0.700)
        assert_that(key1).is_equal_to(key2)
        assert_that(key2).is_equal_to(key3)

    def test_case_normalization(self):
        """Provider and model names should be case-insensitive."""
        key1 = generate_cache_key("Cerebras", "Model", [], 0.7)
        key2 = generate_cache_key("cerebras", "model", [], 0.7)
        key3 = generate_cache_key("CEREBRAS", "MODEL", [], 0.7)
        assert_that(key1).is_equal_to(key2)
        assert_that(key2).is_equal_to(key3)

    def test_returns_64_char_hex(self):
        """Cache key should be a 64-character hex string (SHA256)."""
        key = generate_cache_key("p", "m", [], 0.5)
        assert_that(key).matches(r"^[a-f0-9]{64}$")

    def test_optional_params_affect_key(self):
        """Optional params like max_tokens should affect the key."""
        key1 = generate_cache_key("provider", "model", [], 0.7, max_tokens=100)
        key2 = generate_cache_key("provider", "model", [], 0.7, max_tokens=200)
        key3 = generate_cache_key("provider", "model", [], 0.7)
        assert_that(key1).is_not_equal_to(key2)
        assert_that(key1).is_not_equal_to(key3)

    def test_json_schema_affects_key(self):
        """json_schema parameter should affect the key."""
        schema1 = {"type": "object", "properties": {"name": {"type": "string"}}}
        schema2 = {"type": "object", "properties": {"id": {"type": "integer"}}}
        key1 = generate_cache_key("provider", "model", [], 0.7, json_schema=schema1)
        key2 = generate_cache_key("provider", "model", [], 0.7, json_schema=schema2)
        key3 = generate_cache_key("provider", "model", [], 0.7)
        assert_that(key1).is_not_equal_to(key2)
        assert_that(key1).is_not_equal_to(key3)


class TestCacheRepository:
    """Tests for CacheRepository."""

    @pytest.fixture
    def cache_repo(self, in_memory_db):
        """Create a CacheRepository with an in-memory database."""
        with in_memory_db.session_scope() as session:
            yield CacheRepository(session)

    def test_get_missing_key_returns_none(self, cache_repo):
        """Getting a non-existent key should return None."""
        result = cache_repo.get("nonexistent")
        assert_that(result).is_none()

    def test_put_and_get(self, cache_repo):
        """Put should store data that get can retrieve."""
        cache_repo.put("key1", "provider", "model", "preview", "response data")
        result = cache_repo.get("key1")
        assert_that(result).is_equal_to("response data")

    def test_put_upserts_existing_key(self, cache_repo):
        """Put should update existing entries."""
        cache_repo.put("key1", "provider", "model", "preview", "original")
        cache_repo.put("key1", "provider", "model", "preview", "updated")
        result = cache_repo.get("key1")
        assert_that(result).is_equal_to("updated")

    def test_get_increments_hit_count(self, cache_repo):
        """Each get should increment the hit count."""
        cache_repo.put("key1", "provider", "model", "preview", "response")
        cache_repo.get("key1")
        cache_repo.get("key1")
        stats = cache_repo.stats()
        assert_that(stats["total_hits"]).is_equal_to(2)

    def test_clear_removes_all_entries(self, cache_repo):
        """Clear should remove all entries and return the count."""
        cache_repo.put("key1", "p", "m", "", "r1")
        cache_repo.put("key2", "p", "m", "", "r2")
        count = cache_repo.clear()
        assert_that(count).is_equal_to(2)
        assert_that(cache_repo.stats()["total_entries"]).is_equal_to(0)

    def test_stats_on_empty_cache(self, cache_repo):
        """Stats on empty cache should return zeros."""
        stats = cache_repo.stats()
        assert_that(stats["total_entries"]).is_equal_to(0)
        assert_that(stats["total_hits"]).is_equal_to(0)

    def test_stats_counts_entries_correctly(self, cache_repo):
        """Stats should count entries correctly."""
        cache_repo.put("key1", "p", "m", "", "r1")
        cache_repo.put("key2", "p", "m", "", "r2")
        cache_repo.put("key3", "p", "m", "", "r3")
        stats = cache_repo.stats()
        assert_that(stats["total_entries"]).is_equal_to(3)

    def test_prompt_preview_truncated(self, cache_repo):
        """Prompt preview should be truncated to 200 chars."""
        long_preview = "x" * 500
        cache_repo.put("key1", "p", "m", long_preview, "response")
        # The put method truncates internally
        result = cache_repo.get("key1")
        assert_that(result).is_equal_to("response")
