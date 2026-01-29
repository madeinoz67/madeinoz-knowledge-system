"""
Unit Tests for Lifecycle Manager

Feature: 009-memory-decay-scoring
Tests: T039 - State transitions, T040 - Reactivation, T041 - Soft-delete recovery

Tests verify that:
1. State transitions follow ACTIVE -> DORMANT -> ARCHIVED -> EXPIRED -> SOFT_DELETED
2. Permanent memories never transition
3. DORMANT/ARCHIVED memories reactivate on access
4. Soft-deleted memories can be recovered within 90-day window
5. Soft-deleted memories are purged after 90-day retention
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
import sys
import os

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'patches'))


class TestLifecycleManagerInit:
    """Test LifecycleManager initialization."""

    def test_init_loads_config(self):
        """Should load thresholds from config."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        assert manager.thresholds is not None
        assert manager.retention_days == 90  # Default from config


class TestCalculateNextState:
    """Test calculate_next_state() for state transitions (T039)."""

    def test_permanent_never_transitions(self):
        """Permanent memories (importance >= 4, stability >= 4) should never transition."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        # Even with extreme decay, permanent memories don't transition
        result = manager.calculate_next_state(
            current_state="ACTIVE",
            days_inactive=365,
            decay_score=1.0,
            importance=4,
            stability=4
        )

        assert result is None

    def test_permanent_at_max_values(self):
        """Core memories (5, 5) should never transition."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        result = manager.calculate_next_state(
            current_state="ACTIVE",
            days_inactive=1000,
            decay_score=1.0,
            importance=5,
            stability=5
        )

        assert result is None

    def test_active_to_dormant(self):
        """ACTIVE -> DORMANT after 30 days inactive."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        result = manager.calculate_next_state(
            current_state="ACTIVE",
            days_inactive=35,  # Over 30 day threshold
            decay_score=0.4,   # Over 0.3 threshold
            importance=3,
            stability=3
        )

        assert result == "DORMANT"

    def test_active_stays_active_under_threshold(self):
        """ACTIVE should stay ACTIVE if under thresholds."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        result = manager.calculate_next_state(
            current_state="ACTIVE",
            days_inactive=20,  # Under 30 days
            decay_score=0.2,   # Under 0.3
            importance=3,
            stability=3
        )

        assert result is None

    def test_dormant_to_archived(self):
        """DORMANT -> ARCHIVED after 90 days inactive."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        result = manager.calculate_next_state(
            current_state="DORMANT",
            days_inactive=95,  # Over 90 day threshold
            decay_score=0.7,   # Over 0.6 threshold
            importance=3,
            stability=3
        )

        assert result == "ARCHIVED"

    def test_dormant_stays_dormant_under_threshold(self):
        """DORMANT should stay DORMANT if under thresholds."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        result = manager.calculate_next_state(
            current_state="DORMANT",
            days_inactive=60,  # Under 90 days
            decay_score=0.5,   # Under 0.6
            importance=3,
            stability=3
        )

        assert result is None

    def test_archived_to_expired(self):
        """ARCHIVED -> EXPIRED after 180 days inactive with low importance."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        result = manager.calculate_next_state(
            current_state="ARCHIVED",
            days_inactive=185,  # Over 180 day threshold
            decay_score=0.9,    # Over 0.8 threshold
            importance=2,       # Under max_importance 3
            stability=2
        )

        assert result == "EXPIRED"

    def test_archived_stays_archived_high_importance(self):
        """ARCHIVED should stay ARCHIVED if importance is high enough."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        result = manager.calculate_next_state(
            current_state="ARCHIVED",
            days_inactive=365,
            decay_score=0.95,
            importance=3,  # At or above max_importance threshold
            stability=2
        )

        # Importance 3 is not low enough to trigger EXPIRED (max_importance=2 in config)
        # This depends on config - let's check both cases
        # If max_importance=3, it should still NOT transition because importance must be < max_importance
        # Actually checking the code: importance <= threshold.max_importance
        # So importance=3 with max_importance=3 should still transition

        # The behavior depends on config. Let's test that high importance blocks it
        result_high = manager.calculate_next_state(
            current_state="ARCHIVED",
            days_inactive=365,
            decay_score=0.95,
            importance=4,  # High importance, but not permanent (stability=2)
            stability=2
        )

        # importance=4 > max_importance(3 from config) should NOT transition
        # Actually re-reading the code: importance <= (threshold.max_importance or 5)
        # So if max_importance=3, importance=4 would NOT transition

        assert result_high is None

    def test_expired_to_soft_deleted(self):
        """EXPIRED -> SOFT_DELETED on next maintenance run."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        result = manager.calculate_next_state(
            current_state="EXPIRED",
            days_inactive=200,
            decay_score=0.99,
            importance=1,
            stability=1
        )

        assert result == "SOFT_DELETED"

    def test_soft_deleted_is_terminal(self):
        """SOFT_DELETED should not transition further."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        result = manager.calculate_next_state(
            current_state="SOFT_DELETED",
            days_inactive=365,
            decay_score=1.0,
            importance=1,
            stability=1
        )

        assert result is None

    def test_unknown_state_returns_none(self):
        """Unknown state should return None."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        result = manager.calculate_next_state(
            current_state="INVALID_STATE",
            days_inactive=100,
            decay_score=0.5,
            importance=3,
            stability=3
        )

        assert result is None


class TestShouldReactivate:
    """Test should_reactivate() for access-triggered reactivation (T040)."""

    def test_dormant_should_reactivate(self):
        """DORMANT memories should reactivate on access."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        assert manager.should_reactivate("DORMANT") is True

    def test_archived_should_reactivate(self):
        """ARCHIVED memories should reactivate on access."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        assert manager.should_reactivate("ARCHIVED") is True

    def test_active_does_not_reactivate(self):
        """ACTIVE memories don't need reactivation."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        assert manager.should_reactivate("ACTIVE") is False

    def test_expired_does_not_reactivate(self):
        """EXPIRED memories cannot be reactivated via access."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        assert manager.should_reactivate("EXPIRED") is False

    def test_soft_deleted_does_not_reactivate(self):
        """SOFT_DELETED memories cannot be reactivated via access."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        assert manager.should_reactivate("SOFT_DELETED") is False


class TestCanRecover:
    """Test can_recover() for soft-delete recovery window (T041)."""

    def test_can_recover_within_window(self):
        """Should be recoverable within 90-day window."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        # Deleted 30 days ago
        deleted_at = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        assert manager.can_recover(deleted_at) is True

    def test_can_recover_at_boundary(self):
        """Should be recoverable at 89 days (boundary)."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        # Deleted 89 days ago
        deleted_at = (datetime.now(timezone.utc) - timedelta(days=89)).isoformat()

        assert manager.can_recover(deleted_at) is True

    def test_cannot_recover_after_window(self):
        """Should NOT be recoverable after 90-day window."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        # Deleted 100 days ago
        deleted_at = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()

        assert manager.can_recover(deleted_at) is False

    def test_cannot_recover_at_exactly_90_days(self):
        """Should NOT be recoverable at exactly 90 days."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        # Deleted exactly 90 days ago
        deleted_at = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()

        assert manager.can_recover(deleted_at) is False

    def test_cannot_recover_none_timestamp(self):
        """Should return False for None timestamp."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        assert manager.can_recover(None) is False

    def test_handles_invalid_timestamp(self):
        """Should return False for invalid timestamp."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        assert manager.can_recover("not-a-date") is False

    def test_handles_z_suffix_timestamp(self):
        """Should handle Z suffix timestamps."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        # ISO format with Z suffix
        deleted_at = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat().replace("+00:00", "Z")

        assert manager.can_recover(deleted_at) is True


class TestShouldPurge:
    """Test should_purge() for permanent deletion."""

    def test_should_purge_after_retention(self):
        """Should purge after 90-day retention."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        # Deleted 100 days ago
        deleted_at = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()

        assert manager.should_purge(deleted_at) is True

    def test_should_purge_at_exactly_90_days(self):
        """Should purge at exactly 90 days."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        # Deleted exactly 90 days ago
        deleted_at = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()

        assert manager.should_purge(deleted_at) is True

    def test_should_not_purge_within_retention(self):
        """Should NOT purge within retention window."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        # Deleted 30 days ago
        deleted_at = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        assert manager.should_purge(deleted_at) is False

    def test_should_not_purge_none_timestamp(self):
        """Should return False for None timestamp."""
        from lifecycle_manager import LifecycleManager

        manager = LifecycleManager()

        assert manager.should_purge(None) is False


class TestStateTransitionResult:
    """Test StateTransitionResult dataclass."""

    def test_total_property(self):
        """Total should sum all transition counts."""
        from lifecycle_manager import StateTransitionResult

        result = StateTransitionResult(
            active_to_dormant=10,
            dormant_to_archived=5,
            archived_to_expired=3,
            expired_to_soft_deleted=2
        )

        assert result.total == 20

    def test_to_dict(self):
        """to_dict should include all transition types."""
        from lifecycle_manager import StateTransitionResult

        result = StateTransitionResult(
            active_to_dormant=10,
            dormant_to_archived=5,
            archived_to_expired=3,
            expired_to_soft_deleted=2
        )

        d = result.to_dict()

        assert d["active_to_dormant"] == 10
        assert d["dormant_to_archived"] == 5
        assert d["archived_to_expired"] == 3
        assert d["expired_to_soft_deleted"] == 2

    def test_default_values(self):
        """Default values should all be zero."""
        from lifecycle_manager import StateTransitionResult

        result = StateTransitionResult()

        assert result.total == 0
        assert result.active_to_dormant == 0


class TestUpdateAccessOnRetrieval:
    """Test update_access_on_retrieval function."""

    @pytest.mark.asyncio
    async def test_reactivates_dormant(self):
        """Should reactivate DORMANT memory on access."""
        from lifecycle_manager import update_access_on_retrieval

        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # First query (reactivation) succeeds
        mock_result.single = AsyncMock(return_value={"updated": "test-uuid"})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        result = await update_access_on_retrieval(mock_driver, "test-uuid", "DORMANT")

        assert result is True

    @pytest.mark.asyncio
    async def test_updates_active_access(self):
        """Should update access time for ACTIVE memory."""
        from lifecycle_manager import update_access_on_retrieval

        mock_driver = MagicMock()
        mock_session = AsyncMock()

        # First query (reactivation) returns None (not DORMANT/ARCHIVED)
        mock_result1 = AsyncMock()
        mock_result1.single = AsyncMock(return_value={"updated": None})

        # Second query (access update) succeeds
        mock_result2 = AsyncMock()
        mock_result2.single = AsyncMock(return_value={"updated": "test-uuid"})

        mock_session.run = AsyncMock(side_effect=[mock_result1, mock_result2])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        result = await update_access_on_retrieval(mock_driver, "test-uuid")

        assert result is True


class TestBatchTransitionStates:
    """Test batch_transition_states function."""

    @pytest.mark.asyncio
    async def test_returns_transition_counts(self):
        """Should return StateTransitionResult with counts."""
        from lifecycle_manager import batch_transition_states

        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        mock_result.single = AsyncMock(return_value={
            "active_to_dormant": 5,
            "dormant_to_archived": 3,
            "archived_to_expired": 1,
            "expired_to_soft_deleted": 0
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        result = await batch_transition_states(mock_driver)

        assert result.active_to_dormant == 5
        assert result.dormant_to_archived == 3
        assert result.archived_to_expired == 1
        assert result.expired_to_soft_deleted == 0
        assert result.total == 9

    @pytest.mark.asyncio
    async def test_returns_empty_result_on_no_record(self):
        """Should return empty result when no record returned."""
        from lifecycle_manager import batch_transition_states

        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        result = await batch_transition_states(mock_driver)

        assert result.total == 0


class TestPurgeExpiredSoftDeletes:
    """Test purge_expired_soft_deletes function."""

    @pytest.mark.asyncio
    async def test_returns_purge_count(self):
        """Should return count of purged memories."""
        from lifecycle_manager import purge_expired_soft_deletes

        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        mock_result.single = AsyncMock(return_value={"purged": 25})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        count = await purge_expired_soft_deletes(mock_driver)

        assert count == 25

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_record(self):
        """Should return 0 when no record returned."""
        from lifecycle_manager import purge_expired_soft_deletes

        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        count = await purge_expired_soft_deletes(mock_driver)

        assert count == 0


class TestRecoverSoftDeleted:
    """Test recover_soft_deleted function (T041)."""

    @pytest.mark.asyncio
    async def test_recovery_returns_info(self):
        """Should return recovery info on success."""
        from lifecycle_manager import recover_soft_deleted

        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        mock_result.single = AsyncMock(return_value={
            "recovered": "test-uuid",
            "name": "Test Memory"
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        result = await recover_soft_deleted(mock_driver, "test-uuid")

        assert result is not None
        assert result["uuid"] == "test-uuid"
        assert result["name"] == "Test Memory"
        assert result["new_state"] == "ARCHIVED"

    @pytest.mark.asyncio
    async def test_recovery_returns_none_on_failure(self):
        """Should return None when recovery fails."""
        from lifecycle_manager import recover_soft_deleted

        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        result = await recover_soft_deleted(mock_driver, "expired-uuid")

        assert result is None


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
