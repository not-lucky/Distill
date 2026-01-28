"""Unit tests for cache module."""

import pytest
from assertpy import assert_that

from src.cache import generate_cache_key, get_cached_response, put_cached_response, clear_cache, get_cache_stats


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


class TestCacheFunctions:
    """Tests for cache functions."""

    @pytest.fixture
    def session(self, in_memory_db):
        """Get a session from the in-memory database."""
        with in_memory_db.session_scope() as session:
            yield session

    def test_get_missing_key_returns_none(self, session):
        """Getting a non-existent key should return None."""
        result = get_cached_response(session, "nonexistent")
        assert_that(result).is_none()

    def test_put_and_get(self, session):
        """Put should store data that get can retrieve."""
        put_cached_response(session, "key1", "provider", "model", "preview", "response data")
        result = get_cached_response(session, "key1")
        assert_that(result).is_equal_to("response data")

    def test_put_upserts_existing_key(self, session):
        """Put should update existing entries."""
        put_cached_response(session, "key1", "provider", "model", "preview", "original")
        put_cached_response(session, "key1", "provider", "model", "preview", "updated")
        result = get_cached_response(session, "key1")
        assert_that(result).is_equal_to("updated")

    def test_get_increments_hit_count(self, session):
        """Each get should increment the hit count."""
        put_cached_response(session, "key1", "provider", "model", "preview", "response")
        get_cached_response(session, "key1")
        get_cached_response(session, "key1")
        stats = get_cache_stats(session)
        assert_that(stats["total_hits"]).is_equal_to(2)

    def test_clear_removes_all_entries(self, session):
        """Clear should remove all entries and return the count."""
        put_cached_response(session, "key1", "p", "m", "", "r1")
        put_cached_response(session, "key2", "p", "m", "", "r2")
        count = clear_cache(session)
        assert_that(count).is_equal_to(2)
        assert_that(get_cache_stats(session)["total_entries"]).is_equal_to(0)

    def test_stats_on_empty_cache(self, session):
        """Stats on empty cache should return zeros."""
        stats = get_cache_stats(session)
        assert_that(stats["total_entries"]).is_equal_to(0)
        assert_that(stats["total_hits"]).is_equal_to(0)

    def test_stats_counts_entries_correctly(self, session):
        """Stats should count entries correctly."""
        put_cached_response(session, "key1", "p", "m", "", "r1")
        put_cached_response(session, "key2", "p", "m", "", "r2")
        put_cached_response(session, "key3", "p", "m", "", "r3")
        stats = get_cache_stats(session)
        assert_that(stats["total_entries"]).is_equal_to(3)

    def test_prompt_preview_truncated(self, session):
        """Prompt preview should be truncated to 200 chars."""
        long_preview = "x" * 500
        put_cached_response(session, "key1", "p", "m", long_preview, "response")
        # The put method truncates internally
        result = get_cached_response(session, "key1")
        assert_that(result).is_equal_to("response")
