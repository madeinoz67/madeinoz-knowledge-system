"""
Unit Tests for Source Trust Scoring (GAP-013)
Feature 023 Enhancement: RAG Book Compliance

Tests for trust scoring to prevent knowledge poisoning.

RAG Book Reference:
"The Stack Overflow attack succeeded because we treated all sources equally.
Every document gets a trust score based on:
- Source authority: Official docs > Verified KB > Employee posts > Community wiki > Unverified forums"
"""

import pytest
from datetime import datetime, timedelta
import os
import sys

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'patches'))


class TestTrustLevel:
    """Unit tests for TrustLevel enum."""

    def test_trust_levels_exist(self):
        """Test all trust levels are defined."""
        from trust_scoring import TrustLevel

        assert TrustLevel.OFFICIAL.value == "official"
        assert TrustLevel.VERIFIED.value == "verified"
        assert TrustLevel.TRUSTED.value == "trusted"
        assert TrustLevel.COMMUNITY.value == "community"
        assert TrustLevel.UNVERIFIED.value == "unverified"


class TestTrustScores:
    """Unit tests for trust score values."""

    def test_default_trust_scores(self):
        """Test default trust scores match RAG Book guidance."""
        from trust_scoring import TRUST_SCORES, TrustLevel

        assert TRUST_SCORES[TrustLevel.OFFICIAL] == 1.0
        assert TRUST_SCORES[TrustLevel.VERIFIED] == 0.9
        assert TRUST_SCORES[TrustLevel.TRUSTED] == 0.7
        assert TRUST_SCORES[TrustLevel.COMMUNITY] == 0.4
        assert TRUST_SCORES[TrustLevel.UNVERIFIED] == 0.2

    def test_trust_score_ordering(self):
        """Test trust scores are properly ordered."""
        from trust_scoring import TRUST_SCORES, TrustLevel

        scores = [TRUST_SCORES[level] for level in TrustLevel]
        assert scores == sorted(scores, reverse=True)


class TestSourceClassification:
    """Unit tests for source classification."""

    def test_classify_official_docs(self):
        """Test classification of official documentation URLs."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService()

        # GitHub Pages
        level, _ = service.classify_source("https://docs.python.org/3/library/asyncio.html")
        assert level == TrustLevel.OFFICIAL

        # docs.company.com
        level, _ = service.classify_source("https://docs.aws.amazon.com/s3/")
        assert level == TrustLevel.OFFICIAL

    def test_classify_verified_sources(self):
        """Test classification of verified sources."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService()

        # Educational
        level, _ = service.classify_source("https://stanford.edu/cs101/notes")
        assert level == TrustLevel.VERIFIED

        # Wikipedia
        level, _ = service.classify_source("https://en.wikipedia.org/wiki/Python")
        assert level == TrustLevel.VERIFIED

        # ReadTheDocs
        level, _ = service.classify_source("https://sphinx.readthedocs.io/en/master/")
        assert level == TrustLevel.VERIFIED

    def test_classify_trusted_sources(self):
        """Test classification of trusted sources."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService()

        # Company blog
        level, _ = service.classify_source("https://blog.anthropic.com/research")
        assert level == TrustLevel.TRUSTED

        # Personal knowledge folder
        level, _ = service.classify_source("/home/user/knowledge/notes.md")
        assert level == TrustLevel.TRUSTED

        # Dev.to
        level, _ = service.classify_source("https://dev.to/user/article")
        assert level == TrustLevel.TRUSTED

    def test_classify_community_sources(self):
        """Test classification of community sources."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService()

        # Stack Overflow
        level, _ = service.classify_source("https://stackoverflow.com/questions/12345")
        assert level == TrustLevel.COMMUNITY

        # Reddit
        level, _ = service.classify_source("https://reddit.com/r/programming")
        assert level == TrustLevel.COMMUNITY

    def test_classify_unverified_sources(self):
        """Test classification of unverified sources."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService()

        # Pastebin
        level, _ = service.classify_source("https://pastebin.com/raw/abc123")
        assert level == TrustLevel.UNVERIFIED

        # Inbox folder (unprocessed)
        level, _ = service.classify_source("/home/user/inbox/draft.pdf")
        assert level == TrustLevel.UNVERIFIED

        # Drafts
        level, _ = service.classify_source("/docs/drafts/work-in-progress.md")
        assert level == TrustLevel.UNVERIFIED

    def test_classify_local_file_default(self):
        """Test local files default to TRUSTED."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService()

        # Unknown local file
        level, _ = service.classify_source("/home/user/documents/report.pdf")
        assert level == TrustLevel.TRUSTED

    def test_classify_unknown_url_default(self):
        """Test unknown URLs default to UNVERIFIED."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService()

        # Unknown external URL
        level, _ = service.classify_source("https://random-website.com/page")
        assert level == TrustLevel.UNVERIFIED


class TestAgeDecay:
    """Unit tests for age-based decay."""

    def test_no_decay_for_new_documents(self):
        """Test new documents have no decay."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService()

        # Brand new document
        decay = service.compute_age_decay(0)
        assert decay == 1.0

        # 1 day old
        decay = service.compute_age_decay(1)
        assert decay > 0.99

    def test_decay_at_half_life(self):
        """Test decay at half-life is 0.5."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService(decay_half_life_days=365)

        # At half-life (365 days), decay should be 0.5
        decay = service.compute_age_decay(365)
        assert abs(decay - 0.5) < 0.01  # Allow small floating point error

    def test_decay_at_double_half_life(self):
        """Test decay at 2x half-life is 0.25."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService(decay_half_life_days=365)

        # At 2x half-life (730 days), decay should be 0.25
        decay = service.compute_age_decay(730)
        assert abs(decay - 0.25) < 0.01

    def test_decay_minimum_floor(self):
        """Test decay doesn't go below minimum floor."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService()

        # Very old document
        decay = service.compute_age_decay(10000)  # ~27 years
        assert decay >= 0.1  # Floor

    def test_custom_half_life(self):
        """Test custom half-life configuration."""
        from trust_scoring import TrustScoringService

        # 30-day half-life
        service = TrustScoringService(decay_half_life_days=30)

        # At 30 days, decay should be 0.5
        decay = service.compute_age_decay(30)
        assert abs(decay - 0.5) < 0.01


class TestTrustScoreComputation:
    """Unit tests for full trust score computation."""

    def test_compute_score_official_recent(self):
        """Test score for official, recent document."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService()
        result = service.compute_trust_score(
            source_path="https://docs.python.org/3/library/asyncio.html",
            created_at=datetime.now()
        )

        assert result.trust_level == TrustLevel.OFFICIAL
        assert result.base_score == 1.0
        # Use approximate comparison for floating point
        assert result.age_adjusted_score > 0.999  # Near 1.0 for new doc
        assert result.final_score > 0.999

    def test_compute_score_community_old(self):
        """Test score for community, old document."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService(decay_half_life_days=365)
        old_date = datetime.now() - timedelta(days=365)
        result = service.compute_trust_score(
            source_path="https://stackoverflow.com/questions/12345",
            created_at=old_date
        )

        assert result.trust_level == TrustLevel.COMMUNITY
        assert result.base_score == 0.4
        assert abs(result.age_adjusted_score - 0.2) < 0.01  # 0.4 * 0.5 decay

    def test_compute_score_override_level(self):
        """Test override level forces specific trust."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService()
        result = service.compute_trust_score(
            source_path="https://pastebin.com/raw/abc",  # Would be UNVERIFIED
            override_level=TrustLevel.VERIFIED
        )

        assert result.trust_level == TrustLevel.VERIFIED
        assert result.classification_source == "override"

    def test_compute_score_verified_metadata(self):
        """Test metadata verification boosts trust."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService()
        result = service.compute_trust_score(
            source_path="https://random-site.com/article",
            metadata={"verified": True}
        )

        assert result.trust_level == TrustLevel.VERIFIED
        assert result.classification_source == "verified_metadata"

    def test_compute_score_author_trust(self):
        """Test author trust score affects classification."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService()
        result = service.compute_trust_score(
            source_path="https://random-site.com/article",
            metadata={"author_trust_score": 0.95}
        )

        # Should be promoted based on author trust
        assert result.base_score >= 0.9
        assert "author_trust" in result.classification_source

    def test_compute_score_disabled(self):
        """Test disabled service returns default."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService(enabled=False)
        result = service.compute_trust_score(
            source_path="https://any-site.com/article"
        )

        assert result.classification_source == "disabled"
        assert result.final_score == 0.7


class TestFilterByTrust:
    """Unit tests for filtering results by trust."""

    def test_filter_removes_low_trust(self):
        """Test filter removes results below threshold."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService(min_threshold=0.5)

        results = [
            {"id": "1", "score": 0.9, "trust_score": 0.9},
            {"id": "2", "score": 0.8, "trust_score": 0.3},  # Below threshold
            {"id": "3", "score": 0.7, "trust_score": 0.6},
        ]

        filtered = service.filter_by_trust(results)

        assert len(filtered) == 2
        assert filtered[0]["id"] == "1"
        assert filtered[1]["id"] == "3"

    def test_filter_keeps_all_above_threshold(self):
        """Test filter keeps all results at or above threshold."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService(min_threshold=0.4)

        results = [
            {"id": "1", "trust_score": 0.9},
            {"id": "2", "trust_score": 0.5},
            {"id": "3", "trust_score": 0.4},  # At threshold
        ]

        filtered = service.filter_by_trust(results)

        assert len(filtered) == 3

    def test_filter_default_trust_for_missing(self):
        """Test missing trust_score defaults to 0.5."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService(min_threshold=0.4)

        results = [
            {"id": "1"},  # No trust_score
            {"id": "2", "trust_score": 0.3},
        ]

        filtered = service.filter_by_trust(results)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_filter_disabled_returns_all(self):
        """Test disabled service returns all results."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService(enabled=False)

        results = [
            {"id": "1", "trust_score": 0.1},
            {"id": "2", "trust_score": 0.2},
        ]

        filtered = service.filter_by_trust(results)

        assert len(filtered) == 2


class TestBoostByTrust:
    """Unit tests for boosting results by trust."""

    def test_boost_adjusts_scores(self):
        """Test boost adjusts scores based on trust."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService()

        results = [
            {"id": "1", "score": 0.8, "trust_score": 1.0},
            {"id": "2", "score": 0.9, "trust_score": 0.4},
        ]

        boosted = service.boost_by_trust(results, boost_factor=0.3)

        # First result should get higher boosted score due to trust
        assert boosted[0]["id"] == "1"  # Reordered
        assert "boosted_score" in boosted[0]
        assert "original_score" in boosted[0]

    def test_boost_zero_factor(self):
        """Test boost with zero factor keeps original scores."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService()

        results = [
            {"id": "1", "score": 0.9, "trust_score": 0.2},
            {"id": "2", "score": 0.8, "trust_score": 1.0},
        ]

        boosted = service.boost_by_trust(results, boost_factor=0.0)

        # Order should stay the same (no boost applied)
        assert boosted[0]["id"] == "1"

    def test_boost_full_factor(self):
        """Test boost with full factor uses only trust."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService()

        results = [
            {"id": "1", "score": 0.9, "trust_score": 0.2},
            {"id": "2", "score": 0.1, "trust_score": 1.0},
        ]

        boosted = service.boost_by_trust(results, boost_factor=1.0)

        # Order by trust only
        assert boosted[0]["id"] == "2"


class TestConvenienceFunctions:
    """Unit tests for convenience functions."""

    def test_compute_trust_score_quick(self):
        """Test quick trust score computation."""
        from trust_scoring import compute_trust_score

        score = compute_trust_score("https://docs.python.org/3/library/")

        assert score == 1.0  # Official docs

    def test_compute_trust_score_with_date(self):
        """Test quick computation with date."""
        from trust_scoring import compute_trust_score

        old_date = datetime.now() - timedelta(days=365)
        score = compute_trust_score(
            "https://docs.python.org/3/library/",
            created_at=old_date
        )

        # Should have decay
        assert score < 1.0


class TestEnvironmentConfiguration:
    """Unit tests for environment configuration."""

    def test_default_configuration(self):
        """Test default configuration values."""
        from trust_scoring import TRUST_ENABLED, TRUST_MIN_THRESHOLD, TRUST_DECAY_HALF_LIFE

        assert TRUST_ENABLED is True
        assert TRUST_MIN_THRESHOLD == 0.3
        assert TRUST_DECAY_HALF_LIFE == 365

    def test_service_configuration_override(self):
        """Test service can override defaults."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService(
            enabled=False,
            min_threshold=0.5,
            decay_half_life_days=30
        )

        assert service.enabled is False
        assert service.min_threshold == 0.5
        assert service.decay_half_life_days == 30


class TestIntegrationScenarios:
    """Integration-style tests with realistic scenarios."""

    def test_stack_overflow_poisoning_scenario(self):
        """
        Test the Stack Overflow attack scenario from RAG Book.

        Scenario: Attacker posts fake rate limits on Stack Overflow.
        Official docs should rank higher than community content.
        """
        from trust_scoring import TrustScoringService

        service = TrustScoringService()

        results = [
            {
                "id": "official",
                "source": "https://docs.api.com/rate-limits",
                "score": 0.85,
                "trust_score": service.compute_trust_score(
                    "https://docs.api.com/rate-limits"
                ).final_score,
            },
            {
                "id": "stackoverflow",
                "source": "https://stackoverflow.com/questions/123",
                "score": 0.90,  # Higher similarity (coordinated upvotes)
                "trust_score": service.compute_trust_score(
                    "https://stackoverflow.com/questions/123"
                ).final_score,
            },
        ]

        boosted = service.boost_by_trust(results, boost_factor=0.3)

        # Official docs should rank first despite lower similarity
        assert boosted[0]["id"] == "official"

    def test_knowledge_base_with_mixed_sources(self):
        """Test filtering a knowledge base with mixed trust levels."""
        from trust_scoring import TrustScoringService

        service = TrustScoringService(min_threshold=0.5)

        # Simulate search results from various sources
        results = [
            {"id": "1", "source": "https://docs.python.org/3/", "trust_score": 1.0},
            {"id": "2", "source": "https://stanford.edu/cs101", "trust_score": 0.9},
            {"id": "3", "source": "/knowledge/notes.md", "trust_score": 0.7},
            {"id": "4", "source": "https://stackoverflow.com/q/1", "trust_score": 0.4},
            {"id": "5", "source": "https://pastebin.com/raw/x", "trust_score": 0.2},
        ]

        filtered = service.filter_by_trust(results)

        # Should keep official, verified, and trusted
        assert len(filtered) == 3
        assert all(r["trust_score"] >= 0.5 for r in filtered)

    def test_age_based_prioritization(self):
        """Test newer documents are prioritized over older ones."""
        from trust_scoring import TrustScoringService, TrustLevel

        service = TrustScoringService(decay_half_life_days=365)

        # Two official docs, different ages
        new_result = service.compute_trust_score(
            "https://docs.api.com/v2",
            created_at=datetime.now()
        )
        old_result = service.compute_trust_score(
            "https://docs.api.com/v1",
            created_at=datetime.now() - timedelta(days=730)  # 2 years old
        )

        # Newer should have higher score
        assert new_result.final_score > old_result.final_score
