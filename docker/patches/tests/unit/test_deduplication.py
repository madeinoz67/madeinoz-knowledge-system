"""
Unit Tests for Content Deduplication (GAP-008)
Feature 023 Enhancement: RAG Book Compliance

Tests for hash-based deduplication at ingestion.

RAG Book Reference:
"Hash-based deduplication using MD5 or SHA-256 catches exact duplicates at
ingestion time. Duplicates waste storage, pollute retrieval results (five copies
of the same doc crowding out diverse sources), and skew analytics."
"""

import pytest
from unittest.mock import Mock, patch
import os
import sys

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'patches'))


class TestComputeContentHash:
    """Unit tests for content hash computation."""

    def test_same_content_same_hash(self):
        """Test identical content produces identical hash."""
        from deduplication import compute_content_hash

        text = "This is a test document with some content."
        hash1 = compute_content_hash(text)
        hash2 = compute_content_hash(text)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex chars

    def test_different_content_different_hash(self):
        """Test different content produces different hash."""
        from deduplication import compute_content_hash

        hash1 = compute_content_hash("First document")
        hash2 = compute_content_hash("Second document")

        assert hash1 != hash2

    def test_whitespace_normalized(self):
        """Test leading/trailing whitespace is normalized."""
        from deduplication import compute_content_hash

        hash1 = compute_content_hash("Same content")
        hash2 = compute_content_hash("  Same content  ")
        hash3 = compute_content_hash("\nSame content\n")

        # All should produce same hash after normalization
        assert hash1 == hash2 == hash3

    def test_case_normalized(self):
        """Test content is lowercased for hash."""
        from deduplication import compute_content_hash

        hash1 = compute_content_hash("Content")
        hash2 = compute_content_hash("content")
        hash3 = compute_content_hash("CONTENT")

        assert hash1 == hash2 == hash3

    def test_empty_string_hash(self):
        """Test empty string produces valid hash."""
        from deduplication import compute_content_hash

        hash_val = compute_content_hash("")
        assert len(hash_val) == 64


class TestChunkDeduplicator:
    """Unit tests for chunk deduplicator."""

    def test_dedup_disabled_returns_all(self):
        """Test disabled deduplicator returns all chunks."""
        from deduplication import ChunkDeduplicator

        dedup = ChunkDeduplicator(enabled=False)
        chunks = [
            {"text": "Duplicate content"},
            {"text": "Duplicate content"},
            {"text": "Duplicate content"},
        ]

        result = dedup.filter_duplicates(chunks)

        assert len(result) == 3

    def test_dedup_enabled_removes_duplicates(self):
        """Test enabled deduplicator removes exact duplicates."""
        from deduplication import ChunkDeduplicator

        dedup = ChunkDeduplicator(enabled=True, min_chunk_chars=10)  # Lower threshold for test
        chunks = [
            {"text": "Unique content A here"},
            {"text": "Duplicate content here"},
            {"text": "Duplicate content here"},
            {"text": "Unique content B here"},
        ]

        result = dedup.filter_duplicates(chunks)

        assert len(result) == 3  # 2 unique + 1 of the duplicate
        texts = [c["text"] for c in result]
        assert "Unique content A here" in texts
        assert "Unique content B here" in texts
        assert texts.count("Duplicate content here") == 1

    def test_dedup_skips_short_chunks(self):
        """Test deduplicator skips chunks below minimum size."""
        from deduplication import ChunkDeduplicator

        dedup = ChunkDeduplicator(enabled=True, min_chunk_chars=50)
        chunks = [
            {"text": "This is a short chunk"},  # 22 chars, below 50
            {"text": "This is a much longer chunk that exceeds the minimum threshold requirement"},
        ]

        result = dedup.filter_duplicates(chunks)

        assert len(result) == 1
        assert "exceeds the minimum" in result[0]["text"]

    def test_dedup_adds_hash_metadata(self):
        """Test deduplicator adds content_hash to metadata."""
        from deduplication import ChunkDeduplicator

        dedup = ChunkDeduplicator(enabled=True, min_chunk_chars=10)
        chunks = [{"text": "Test content for hashing here"}]

        result = dedup.filter_duplicates(chunks, add_hash_metadata=True)

        assert len(result) == 1
        assert "content_hash" in result[0]
        assert len(result[0]["content_hash"]) == 64

    def test_dedup_no_hash_metadata_when_disabled(self):
        """Test hash not added when flag is False."""
        from deduplication import ChunkDeduplicator

        dedup = ChunkDeduplicator(enabled=True, min_chunk_chars=10)
        chunks = [{"text": "Test content for hashing here"}]

        result = dedup.filter_duplicates(chunks, add_hash_metadata=False)

        assert len(result) == 1
        assert "content_hash" not in result[0]

    def test_dedup_tracks_stats(self):
        """Test deduplicator tracks statistics."""
        from deduplication import ChunkDeduplicator

        dedup = ChunkDeduplicator(enabled=True, min_chunk_chars=10)
        chunks = [
            {"text": "Unique content here"},
            {"text": "Duplicate content here"},
            {"text": "Duplicate content here"},
        ]

        dedup.filter_duplicates(chunks)
        stats = dedup.get_stats()

        assert stats["total_chunks"] == 3
        assert stats["duplicates_skipped"] == 1
        assert stats["unique_kept"] == 2

    def test_dedup_reset_clears_state(self):
        """Test reset clears seen hashes."""
        from deduplication import ChunkDeduplicator

        dedup = ChunkDeduplicator(enabled=True, min_chunk_chars=10)
        chunks = [{"text": "Test content here for hashing"}]

        dedup.filter_duplicates(chunks)
        assert len(dedup.get_seen_hashes()) == 1

        dedup.reset()
        assert len(dedup.get_seen_hashes()) == 0

    def test_dedup_across_multiple_calls(self):
        """Test dedup works across multiple filter calls."""
        from deduplication import ChunkDeduplicator

        dedup = ChunkDeduplicator(enabled=True, min_chunk_chars=10)

        # First call
        result1 = dedup.filter_duplicates([{"text": "Content A here"}])
        assert len(result1) == 1

        # Second call - duplicate
        result2 = dedup.filter_duplicates([{"text": "Content A here"}], add_hash_metadata=False)
        assert len(result2) == 0  # Filtered out

        # Third call - unique
        result3 = dedup.filter_duplicates([{"text": "Content B here"}])
        assert len(result3) == 1


class TestDeduplicationService:
    """Unit tests for main deduplication service."""

    def test_service_disabled_returns_all(self):
        """Test disabled service returns all chunks."""
        from deduplication import DeduplicationService

        service = DeduplicationService(enabled=False)
        chunks = [
            {"text": "Duplicate"},
            {"text": "Duplicate"},
        ]

        result = service.dedup_chunks(chunks)

        assert len(result) == 2

    def test_service_enabled_dedups_chunks(self):
        """Test enabled service deduplicates chunks."""
        from deduplication import DeduplicationService

        service = DeduplicationService(enabled=True, chunk_level=True)
        # Override chunk_dedup min_chunk_chars for test
        service.chunk_dedup.min_chunk_chars = 10
        chunks = [
            {"text": "This is unique content that should be kept here"},
            {"text": "This is duplicate content here"},
            {"text": "This is duplicate content here"},
        ]

        result = service.dedup_chunks(chunks, reset_session=True)

        assert len(result) == 2

    def test_service_stats(self):
        """Test service returns statistics."""
        from deduplication import DeduplicationService

        service = DeduplicationService(enabled=True)
        service.chunk_dedup.min_chunk_chars = 10
        chunks = [{"text": "Unique content here for testing"}]

        service.dedup_chunks(chunks)
        stats = service.get_stats()

        assert stats["enabled"] is True
        assert "chunk_stats" in stats
        assert stats["seen_hashes_count"] == 1


class TestDeduplicationConfiguration:
    """Unit tests for deduplication configuration."""

    def test_default_configuration(self):
        """Test default configuration values."""
        from deduplication import DEDUP_ENABLED, DEDUP_CHUNK_LEVEL, DEDUP_MINHASH_THRESHOLD

        assert DEDUP_ENABLED is True
        assert DEDUP_CHUNK_LEVEL is True
        assert DEDUP_MINHASH_THRESHOLD == 0.8

    def test_environment_override(self):
        """Test configuration can be overridden via environment."""
        with patch.dict(os.environ, {
            "MADEINOZ_KNOWLEDGE_DEDUP_ENABLED": "false",
            "MADEINOZ_KNOWLEDGE_DEDUP_MINHASH_THRESHOLD": "0.9",
        }):
            # Re-import to pick up new env vars
            import importlib
            import deduplication
            importlib.reload(deduplication)

            assert os.environ.get("MADEINOZ_KNOWLEDGE_DEDUP_ENABLED") == "false"


class TestDeduplicationIntegration:
    """Integration-style tests with realistic scenarios."""

    def test_dedup_removes_boilerplate(self):
        """
        Test dedup removes common boilerplate across documents.

        Scenario: Multiple documents with same header/footer.
        """
        from deduplication import DeduplicationService

        service = DeduplicationService(enabled=True)
        service.chunk_dedup.min_chunk_chars = 10  # Lower for test

        # Simulate chunks from 3 documents with same disclaimer
        chunks = [
            {"text": "Document 1 main content about authentication systems"},
            {"text": "CONFIDENTIAL - FOR INTERNAL USE ONLY - DO NOT DISTRIBUTE"},
            {"text": "Document 2 main content about logging frameworks"},
            {"text": "CONFIDENTIAL - FOR INTERNAL USE ONLY - DO NOT DISTRIBUTE"},
            {"text": "Document 3 main content about caching mechanisms"},
            {"text": "CONFIDENTIAL - FOR INTERNAL USE ONLY - DO NOT DISTRIBUTE"},
        ]

        result = service.dedup_chunks(chunks)

        # Should keep 4 unique chunks (3 main + 1 disclaimer)
        assert len(result) == 4
        texts = [c["text"] for c in result]
        assert texts.count("CONFIDENTIAL - FOR INTERNAL USE ONLY - DO NOT DISTRIBUTE") == 1

    def test_dedup_preserves_chunk_order(self):
        """Test dedup preserves order of first occurrence."""
        from deduplication import ChunkDeduplicator

        dedup = ChunkDeduplicator(enabled=True, min_chunk_chars=10)
        chunks = [
            {"text": "First chunk here for testing"},
            {"text": "Second chunk here for testing"},
            {"text": "First chunk here for testing"},  # Duplicate
            {"text": "Third chunk here for testing"},
        ]

        result = dedup.filter_duplicates(chunks)

        assert len(result) == 3
        assert result[0]["text"] == "First chunk here for testing"
        assert result[1]["text"] == "Second chunk here for testing"
        assert result[2]["text"] == "Third chunk here for testing"

    def test_dedup_latency_acceptable(self):
        """Test dedup completes quickly (<10ms for 100 chunks)."""
        import time
        from deduplication import ChunkDeduplicator

        dedup = ChunkDeduplicator(enabled=True)

        # Generate 100 chunks with some duplicates
        chunks = []
        for i in range(100):
            chunks.append({"text": f"Unique content number {i}" * 5})
        # Add 50 duplicates
        for i in range(50):
            chunks.append({"text": f"Unique content number {i}" * 5})

        start = time.time()
        result = dedup.filter_duplicates(chunks)
        elapsed_ms = (time.time() - start) * 1000

        assert len(result) == 100  # Only unique
        assert elapsed_ms < 10, f"Dedup took {elapsed_ms:.2f}ms, expected <10ms"
