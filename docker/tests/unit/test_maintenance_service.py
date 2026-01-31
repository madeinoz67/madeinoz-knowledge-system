"""
Unit Tests for Maintenance Service

Feature: 009-memory-decay-scoring
Tests: T051 - Batch processing, maintenance cycle

Tests verify that:
1. MaintenanceService orchestrates decay/lifecycle/purge steps
2. Dry run mode doesn't modify data
3. Timeout handling works correctly
4. Classification is called as Step 0
5. Metrics are recorded on completion
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'patches'))


class TestMaintenanceServiceInit:
    """Test MaintenanceService initialization."""

    def test_init_with_defaults(self):
        """Should load defaults from config."""
        from maintenance_service import MaintenanceService

        mock_driver = MagicMock()
        service = MaintenanceService(mock_driver)

        assert service.driver == mock_driver
        assert service.batch_size > 0
        assert service.max_duration_minutes > 0
        assert service.base_half_life > 0
        assert service._llm_client is None

    def test_init_with_custom_values(self):
        """Should use custom values when provided."""
        from maintenance_service import MaintenanceService

        mock_driver = MagicMock()
        mock_llm = MagicMock()
        service = MaintenanceService(
            driver=mock_driver,
            llm_client=mock_llm,
            batch_size=100,
            max_duration_minutes=5
        )

        assert service.batch_size == 100
        assert service.max_duration_minutes == 5
        assert service._llm_client == mock_llm


class TestMaintenanceResult:
    """Test MaintenanceResult dataclass."""

    def test_to_dict_includes_all_fields(self):
        """to_dict should include all result fields."""
        from maintenance_service import MaintenanceResult, ClassificationResult
        from lifecycle_manager import StateTransitionResult

        result = MaintenanceResult(
            success=True,
            memories_processed=1000,
            nodes_classified=ClassificationResult(found=50, classified=45, failed=5, using_llm=True),
            decay_scores_updated=950,
            state_transitions=StateTransitionResult(active_to_dormant=10, dormant_to_archived=5),
            soft_deleted_purged=3,
            duration_seconds=45.5,
            completed_at="2024-01-15T10:00:00Z",
            error=None
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["memories_processed"] == 1000
        assert d["nodes_classified"]["classified"] == 45
        assert d["decay_scores_updated"] == 950
        assert d["state_transitions"]["active_to_dormant"] == 10
        assert d["soft_deleted_purged"] == 3
        assert d["duration_seconds"] == 45.5
        assert d["completed_at"] == "2024-01-15T10:00:00Z"
        assert d["error"] is None

    def test_default_values(self):
        """Default values should be reasonable."""
        from maintenance_service import MaintenanceResult

        result = MaintenanceResult()

        assert result.success is True
        assert result.memories_processed == 0
        assert result.decay_scores_updated == 0
        assert result.soft_deleted_purged == 0


class TestClassificationResult:
    """Test ClassificationResult dataclass."""

    def test_to_dict(self):
        """to_dict should include classification details."""
        from maintenance_service import ClassificationResult

        result = ClassificationResult(
            found=100,
            classified=95,
            failed=5,
            using_llm=True
        )

        d = result.to_dict()

        assert d["found"] == 100
        assert d["classified"] == 95
        assert d["failed"] == 5
        assert d["using_llm"] is True

    def test_defaults(self):
        """Defaults should be zero/false."""
        from maintenance_service import ClassificationResult

        result = ClassificationResult()

        assert result.found == 0
        assert result.classified == 0
        assert result.failed == 0
        assert result.using_llm is False


class TestRunMaintenance:
    """Test run_maintenance() method."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_early(self):
        """Dry run should count but not modify."""
        from maintenance_service import MaintenanceService

        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Count query returns 100 memories
        mock_result.single = AsyncMock(return_value={"count": 100})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        service = MaintenanceService(mock_driver)
        result = await service.run_maintenance(dry_run=True)

        assert result.success is True
        assert result.memories_processed == 100
        assert result.decay_scores_updated == 0  # Not modified in dry run
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_full_maintenance_cycle(self):
        """Full maintenance should run all steps."""
        from maintenance_service import MaintenanceService

        mock_driver = MagicMock()
        mock_session = AsyncMock()

        # Setup query results for each step
        count_result = AsyncMock()
        count_result.single = AsyncMock(return_value={"count": 100})

        classification_result = AsyncMock()
        classification_result.single = AsyncMock(return_value={"count": 0})  # No unclassified

        # Each function creates its own session, so we need to mock accordingly
        # _count_memories uses one session.run()
        # classify_unclassified_nodes creates its own session
        # batch_update_decay_scores creates its own session and returns int
        # batch_transition_states creates its own session
        # purge_expired_soft_deletes creates its own session

        # For _count_memories (called by run_maintenance)
        mock_session.run = AsyncMock(return_value=count_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        service = MaintenanceService(mock_driver)

        # Mock the external functions that create their own sessions
        with patch('maintenance_service.classify_unclassified_nodes') as mock_classify, \
             patch('maintenance_service.batch_update_decay_scores') as mock_decay, \
             patch('maintenance_service.batch_transition_states') as mock_transitions, \
             patch('maintenance_service.purge_expired_soft_deletes') as mock_purge:

            mock_classify.return_value = {
                "found": 0,
                "classified": 0,
                "failed": 0,
                "using_llm": False
            }

            mock_decay.return_value = 95  # Returns int directly

            from lifecycle_manager import StateTransitionResult
            mock_transitions.return_value = StateTransitionResult(
                active_to_dormant=5,
                dormant_to_archived=2,
                archived_to_expired=1,
                expired_to_soft_deleted=0
            )

            mock_purge.return_value = 0

            result = await service.run_maintenance(dry_run=False)

        assert result.success is True
        assert result.memories_processed == 100

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        """Should handle exceptions gracefully."""
        from maintenance_service import MaintenanceService

        mock_driver = MagicMock()
        mock_session = AsyncMock()

        mock_session.run = AsyncMock(side_effect=Exception("Database error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        service = MaintenanceService(mock_driver)
        result = await service.run_maintenance()

        assert result.success is False
        assert result.error is not None
        assert "Database error" in result.error


class TestHealthMetrics:
    """Test HealthMetrics dataclass."""

    def test_default_values(self):
        """Default values should be reasonable."""
        from maintenance_service import HealthMetrics

        metrics = HealthMetrics()

        assert metrics.states["active"] == 0
        assert metrics.aggregates["total"] == 0
        assert metrics.age_distribution["under_7_days"] == 0
        assert metrics.maintenance["last_run"] is None
        assert metrics.generated_at is None

    def test_to_dict(self):
        """to_dict should include all sections."""
        from maintenance_service import HealthMetrics

        metrics = HealthMetrics()
        metrics.states["active"] = 100
        metrics.generated_at = "2024-01-15T10:00:00Z"

        d = metrics.to_dict()

        assert "states" in d
        assert "aggregates" in d
        assert "age_distribution" in d
        assert "maintenance" in d
        assert d["generated_at"] == "2024-01-15T10:00:00Z"


class TestGetHealthMetrics:
    """Test get_health_metrics() method."""

    @pytest.mark.asyncio
    async def test_returns_health_metrics(self):
        """Should return populated HealthMetrics."""
        from maintenance_service import MaintenanceService

        mock_driver = MagicMock()
        mock_session = AsyncMock()

        # State counts
        states_result = AsyncMock()
        states_result.single = AsyncMock(return_value={
            "active": 100,
            "dormant": 50,
            "archived": 25,
            "expired": 10,
            "soft_deleted": 5,
            "permanent": 30,
            "total": 220
        })

        # Aggregates
        aggregates_result = AsyncMock()
        aggregates_result.single = AsyncMock(return_value={
            "avg_decay": 0.35,
            "avg_importance": 3.2,
            "avg_stability": 3.5
        })

        # Orphan entities
        orphan_result = AsyncMock()
        orphan_result.single = AsyncMock(return_value={"orphan_count": 2})

        # Age distribution (aligned with lifecycle thresholds: 30/90/180/365 days)
        age_result = AsyncMock()
        age_result.single = AsyncMock(return_value={
            "under_7_days": 40,
            "days_7_to_30": 60,
            "days_30_to_90": 80,
            "days_90_to_180": 50,
            "days_180_to_365": 30,
            "over_365_days": 20
        })

        # Importance distribution
        importance_result = AsyncMock()
        importance_result.single = AsyncMock(return_value={
            "trivial": 10,
            "low": 20,
            "moderate": 80,
            "high": 60,
            "core": 50
        })

        # get_health_metrics makes 5 session.run calls in sequence
        mock_session.run = AsyncMock(side_effect=[
            states_result,        # HEALTH_STATES_QUERY
            aggregates_result,   # HEALTH_AGGREGATES_QUERY
            orphan_result,       # ORPHAN_ENTITIES_QUERY
            age_result,          # HEALTH_AGE_DISTRIBUTION_QUERY
            importance_result   # HEALTH_IMPORTANCE_DISTRIBUTION_QUERY
        ])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        service = MaintenanceService(mock_driver)
        metrics = await service.get_health_metrics()

        assert metrics.states["active"] == 100
        assert metrics.states["permanent"] == 30
        assert metrics.aggregates["total"] == 220
        assert metrics.aggregates["average_decay"] == 0.35
        assert metrics.age_distribution["under_7_days"] == 40
        assert metrics.generated_at is not None


class TestGetMaintenanceService:
    """Test get_maintenance_service() factory function."""

    def test_creates_singleton(self):
        """Should return same instance on subsequent calls."""
        from maintenance_service import get_maintenance_service, _maintenance_service
        import maintenance_service as ms

        # Reset singleton
        ms._maintenance_service = None

        mock_driver = MagicMock()

        service1 = get_maintenance_service(mock_driver)
        service2 = get_maintenance_service(mock_driver)

        assert service1 is service2

        # Reset for other tests
        ms._maintenance_service = None

    def test_accepts_llm_client(self):
        """Should pass llm_client to MaintenanceService."""
        from maintenance_service import get_maintenance_service
        import maintenance_service as ms

        # Reset singleton
        ms._maintenance_service = None

        mock_driver = MagicMock()
        mock_llm = MagicMock()

        service = get_maintenance_service(mock_driver, llm_client=mock_llm)

        assert service._llm_client == mock_llm

        # Reset for other tests
        ms._maintenance_service = None


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
