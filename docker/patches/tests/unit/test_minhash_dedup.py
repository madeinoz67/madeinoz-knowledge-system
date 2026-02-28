"""
Unit Tests for MinHash Near-Duplicate Detection (GAP-008b)
Feature 023 Enhancement: RAG Book Compliance

Tests for MinHash-based near-duplicate detection.

RAG Book Reference:
"Five copies of the same doc crowding out diverse sources"
"""

import pytest
import os
import sys

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'patches'))


class TestShingleGenerator:
    """Unit tests for shingle generation."""

    def test_basic_shingling(self):
        """Test basic shingle generation."""
        from minhash_dedup import ShingleGenerator

        shingler = ShingleGenerator(k=3)
        shingles = shingler.generate("hello")

        # "hello" has shingles: "hel", "ell", "llo"
        assert "hel" in shingles
        assert "ell" in shingles
        assert "llo" in shingles
        assert len(shingles) == 3

    def test_short_text(self):
        """Test shingling text shorter than k."""
        from minhash_dedup import ShingleGenerator

        shingler = ShingleGenerator(k=5)
        shingles = shingler.generate("hi")

        # Text shorter than k returns whole text as single shingle
        assert len(shingles) == 1
        assert "hi" in shingles

    def test_empty_text(self):
        """Test shingling empty text."""
        from minhash_dedup import ShingleGenerator

        shingler = ShingleGenerator(k=3)
        shingles = shingler.generate("")

        assert len(shingles) == 0

    def test_normalization(self):
        """Test text normalization."""
        from minhash_dedup import ShingleGenerator

        shingler = ShingleGenerator(k=3)

        # Extra whitespace should be normalized
        shingles1 = shingler.generate("hello world")
        shingles2 = shingler.generate("hello    world")

        assert shingles1 == shingles2

    def test_case_insensitive(self):
        """Test case insensitivity."""
        from minhash_dedup import ShingleGenerator

        shingler = ShingleGenerator(k=3)

        shingles1 = shingler.generate("HELLO")
        shingles2 = shingler.generate("hello")

        assert shingles1 == shingles2


class TestMinHash:
    """Unit tests for MinHash signatures."""

    def test_signature_length(self):
        """Test signature has correct length."""
        from minhash_dedup import MinHash, ShingleGenerator

        minhash = MinHash(num_perm=128)
        shingler = ShingleGenerator()

        shingles = shingler.generate("test content")
        signature = minhash.create_signature(shingles)

        assert len(signature) == 128

    def test_identical_texts_same_signature(self):
        """Test identical texts produce same signature."""
        from minhash_dedup import MinHash, ShingleGenerator

        minhash = MinHash(num_perm=128)
        shingler = ShingleGenerator()

        text = "This is a test document for minhash"
        shingles = shingler.generate(text)

        sig1 = minhash.create_signature(shingles)
        sig2 = minhash.create_signature(shingles)

        assert sig1 == sig2

    def test_empty_shingles(self):
        """Test empty shingle set."""
        from minhash_dedup import MinHash

        minhash = MinHash(num_perm=64)
        signature = minhash.create_signature(set())

        assert len(signature) == 64
        assert all(s == minhash.MAX_HASH for s in signature)

    def test_jaccard_similarity_identical(self):
        """Test Jaccard of identical signatures is 1.0."""
        from minhash_dedup import MinHash, ShingleGenerator

        minhash = MinHash(num_perm=128)
        shingler = ShingleGenerator()

        text = "Test document for similarity"
        sig = minhash.create_signature(shingler.generate(text))

        similarity = minhash.jaccard_similarity(sig, sig)

        assert similarity == 1.0

    def test_jaccard_similarity_different(self):
        """Test Jaccard of different texts."""
        from minhash_dedup import MinHash, ShingleGenerator

        minhash = MinHash(num_perm=256)  # More permutations = better accuracy
        shingler = ShingleGenerator()

        text1 = "The quick brown fox jumps over the lazy dog"
        text2 = "A fast auburn fox leaps above the sleepy canine"

        sig1 = minhash.create_signature(shingler.generate(text1))
        sig2 = minhash.create_signature(shingler.generate(text2))

        similarity = minhash.jaccard_similarity(sig1, sig2)

        # These are different texts, similarity should be < 1
        assert 0.0 <= similarity < 1.0

    def test_jaccard_similarity_near_duplicate(self):
        """Test Jaccard of near-duplicate texts."""
        from minhash_dedup import MinHash, ShingleGenerator

        minhash = MinHash(num_perm=256)
        shingler = ShingleGenerator()

        text1 = "This is the original document with important information about the system configuration and settings"
        text2 = "This is the original document with important information about the system configuration and setting"  # Missing 's'

        sig1 = minhash.create_signature(shingler.generate(text1))
        sig2 = minhash.create_signature(shingler.generate(text2))

        similarity = minhash.jaccard_similarity(sig1, sig2)

        # Very similar texts should have high similarity
        assert similarity > 0.9

    def test_signature_length_mismatch(self):
        """Test error on signature length mismatch."""
        from minhash_dedup import MinHash

        minhash = MinHash()

        with pytest.raises(ValueError):
            minhash.jaccard_similarity([1, 2, 3], [1, 2])


class TestMinHashLSH:
    """Unit tests for LSH indexing."""

    def test_add_and_query(self):
        """Test adding and querying LSH index."""
        from minhash_dedup import MinHashLSH, MinHash, ShingleGenerator

        lsh = MinHashLSH(num_perm=128)
        minhash = MinHash(num_perm=128)
        shingler = ShingleGenerator()

        text = "Test document"
        sig = minhash.create_signature(shingler.generate(text))

        lsh.add("doc1", sig)
        candidates = lsh.query(sig)

        assert "doc1" in candidates

    def test_find_similar(self):
        """Test finding similar documents."""
        from minhash_dedup import MinHashLSH, MinHash, ShingleGenerator

        lsh = MinHashLSH(num_perm=128, num_bands=16, rows_per_band=8)
        minhash = MinHash(num_perm=128)
        shingler = ShingleGenerator()

        # Similar texts
        text1 = "The quick brown fox jumps over the lazy dog in the park"
        text2 = "The quick brown fox jumps over the lazy dog in the garden"

        sig1 = minhash.create_signature(shingler.generate(text1))
        sig2 = minhash.create_signature(shingler.generate(text2))

        lsh.add("doc1", sig1)
        lsh.add("doc2", sig2)

        # Query should find both
        candidates = lsh.query(sig1)
        assert "doc2" in candidates


class TestNearDuplicate:
    """Unit tests for NearDuplicate dataclass."""

    def test_duplicate_creation(self):
        """Test NearDuplicate creation."""
        from minhash_dedup import NearDuplicate

        dup = NearDuplicate(
            chunk_id_1="chunk_1",
            chunk_id_2="chunk_2",
            similarity=0.92,
            text_preview_1="First text...",
            text_preview_2="Second text...",
        )

        assert dup.chunk_id_1 == "chunk_1"
        assert dup.similarity == 0.92


class TestMinHashDeduplicator:
    """Unit tests for main deduplicator."""

    def test_disabled_dedup(self):
        """Test disabled deduplicator."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator(enabled=False)
        dedup.add_chunk("1", "test content")

        # Should not index when disabled
        assert len(dedup.lsh.signatures) == 0

    def test_add_chunks(self):
        """Test adding chunks."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator(enabled=True, threshold=0.85)

        dedup.add_chunk("chunk_1", "This is the first document")
        dedup.add_chunk("chunk_2", "This is the second document")

        assert len(dedup.lsh.signatures) == 2

    def test_find_near_duplicates(self):
        """Test finding near-duplicates."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator(enabled=True, threshold=0.85, num_perm=256)

        # Near-duplicate texts
        text1 = "The API rate limit is configured at 100 requests per minute for standard users and 1000 for premium"
        text2 = "The API rate limit is configured at 100 requests per minute for standard users and 1000 for premium."  # Just added period

        dedup.add_chunk("chunk_1", text1)
        dedup.add_chunk("chunk_2", text2)

        duplicates = dedup.find_duplicates("chunk_1")

        # Should find chunk_2 as near-duplicate
        assert len(duplicates) >= 1
        assert duplicates[0].similarity >= 0.85

    def test_no_duplicate_for_different_texts(self):
        """Test no duplicate for very different texts."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator(enabled=True, threshold=0.85)

        # Very different texts
        text1 = "Authentication is required for all API endpoints"
        text2 = "The database configuration settings are stored in YAML"

        dedup.add_chunk("chunk_1", text1)
        dedup.add_chunk("chunk_2", text2)

        duplicates = dedup.find_duplicates("chunk_1")

        # Should not find duplicate
        assert len(duplicates) == 0

    def test_find_all_duplicates(self):
        """Test finding all duplicate pairs."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator(enabled=True, threshold=0.85, num_perm=256)

        # Create pairs of near-duplicates
        text1a = "Configuration file located at /etc/app/config.yaml contains all settings"
        text1b = "Configuration file located at /etc/app/config.yaml contains all setting"
        text2a = "The authentication service runs on port 8080 and handles OAuth tokens"
        text2b = "The authentication service runs on port 8080 and handles OAuth token"

        dedup.add_chunk("d1a", text1a)
        dedup.add_chunk("d1b", text1b)
        dedup.add_chunk("d2a", text2a)
        dedup.add_chunk("d2b", text2b)

        all_dups = dedup.find_all_duplicates()

        # Should find at least some duplicates
        assert len(all_dups) >= 1

    def test_filter_duplicates(self):
        """Test filtering duplicates from chunk list."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator(enabled=True, threshold=0.85, num_perm=256)

        chunks = [
            {"chunk_id": "1", "text": "The system configuration is stored in the config file"},
            {"chunk_id": "2", "text": "The system configuration is stored in the config files"},  # Near-dup
            {"chunk_id": "3", "text": "Authentication requires valid credentials"},
        ]

        filtered = dedup.filter_duplicates(chunks)

        # Should remove one duplicate
        assert len(filtered) < len(chunks)
        assert len(filtered) >= 2  # At least 2 unique chunks

    def test_get_stats(self):
        """Test getting statistics."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator(enabled=True, threshold=0.9)

        dedup.add_chunk("1", "Test content")
        dedup.add_chunk("2", "Different content")

        stats = dedup.get_stats()

        assert stats["enabled"] is True
        assert stats["threshold"] == 0.9
        assert stats["chunks_processed"] == 2


class TestConvenienceFunctions:
    """Unit tests for convenience functions."""

    def test_check_near_duplicate_true(self):
        """Test check_near_duplicate for duplicates."""
        from minhash_dedup import check_near_duplicate

        text1 = "The configuration file is located in /etc/app/config.yaml"
        text2 = "The configuration file is located in /etc/app/config.yaml"  # Identical

        is_dup, similarity = check_near_duplicate(text1, text2, threshold=0.8)

        assert is_dup is True
        assert similarity == 1.0

    def test_check_near_duplicate_false(self):
        """Test check_near_duplicate for non-duplicates."""
        from minhash_dedup import check_near_duplicate

        text1 = "Authentication uses OAuth 2.0"
        text2 = "Database runs on PostgreSQL"

        is_dup, similarity = check_near_duplicate(text1, text2, threshold=0.8)

        assert is_dup is False
        assert similarity < 0.8

    def test_compute_jaccard_identical(self):
        """Test compute_jaccard for identical texts."""
        from minhash_dedup import compute_jaccard

        text = "Test content"
        similarity = compute_jaccard(text, text)

        assert similarity == 1.0

    def test_compute_jaccard_different(self):
        """Test compute_jaccard for different texts."""
        from minhash_dedup import compute_jaccard

        text1 = "abc def ghi"
        text2 = "xyz uvw rst"

        similarity = compute_jaccard(text1, text2)

        # No common shingles
        assert similarity < 0.5

    def test_compute_jaccard_empty(self):
        """Test compute_jaccard with empty text."""
        from minhash_dedup import compute_jaccard

        similarity = compute_jaccard("", "test")

        assert similarity == 0.0


class TestEnvironmentVariables:
    """Unit tests for environment configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        from minhash_dedup import (
            MINHASH_ENABLED,
            MINHASH_THRESHOLD,
            MINHASH_NUM_PERM,
        )

        assert isinstance(MINHASH_ENABLED, bool)
        assert isinstance(MINHASH_THRESHOLD, float)
        assert isinstance(MINHASH_NUM_PERM, int)

    def test_custom_values(self):
        """Test custom configuration via constructor."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator(
            enabled=False,
            threshold=0.95,
            num_perm=256,
            shingle_size=4,
        )

        assert dedup.enabled is False
        assert dedup.threshold == 0.95
        assert dedup.num_perm == 256


class TestEdgeCases:
    """Edge case tests."""

    def test_very_long_text(self):
        """Test handling of very long text."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator()

        long_text = "word " * 10000
        dedup.add_chunk("long", long_text)

        assert "long" in dedup.lsh.signatures

    def test_special_characters(self):
        """Test handling of special characters."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator()

        text = "Special chars: @#$%^&*()_+-=[]{}|;':\",./<>?"
        dedup.add_chunk("special", text)

        assert "special" in dedup.lsh.signatures

    def test_unicode_text(self):
        """Test handling of unicode text."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator()

        text = "Unicode test: 你好世界 🌍 مرحبا"
        dedup.add_chunk("unicode", text)

        assert "unicode" in dedup.lsh.signatures

    def test_single_character_text(self):
        """Test handling of single character."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator()

        dedup.add_chunk("single", "a")
        assert "single" in dedup.lsh.signatures

    def test_repeated_content(self):
        """Test detection of repeated content."""
        from minhash_dedup import MinHashDeduplicator

        dedup = MinHashDeduplicator(threshold=0.9)

        text1 = "word word word word word word word word"
        text2 = "word word word word word word word word"

        dedup.add_chunk("r1", text1)
        dedup.add_chunk("r2", text2)

        dups = dedup.find_duplicates("r1")

        assert len(dups) >= 1
