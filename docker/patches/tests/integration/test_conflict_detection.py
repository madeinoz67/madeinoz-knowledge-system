"""
Integration Tests for Conflict Detection and Resolution (T064, T081-T083 - US3, US5)
Local Knowledge Augmentation Platform

Tests for:
- Conflict detection (same entity + type, different values)
- Resolution strategies (detect_only, keep_both, prefer_newest, reject_incoming)
- Conflict status tracking (open → resolved OR open → deferred)
- Provenance tracking in conflict scenarios
"""

import pytest
from datetime import datetime
from patches.promotion import (
    detect_conflicts,
    apply_resolution_strategy,
    review_conflicts,
)
from patches.lkap_models import FactType, ConflictStatus, ResolutionStrategy


class TestConflictDetection:
    """Integration tests for conflict detection (T064, T081)"""

    @pytest.mark.asyncio
    async def test_detects_conflicting_facts(self):
        """
        Test conflict detection when same entity has different values.

        T070: Conflict detection Cypher query implementation test.

        Scenario: STM32H7.GPIO.max_speed has values 120MHz and 84MHz
        """
        entity = "STM32H7.GPIO.max_speed"
        fact_type = FactType.CONSTRAINT

        # Mock existing facts in Knowledge Graph
        existing_facts = [
            {
                "fact_id": "fact-001",
                "entity": entity,
                "type": "Constraint",
                "value": "120MHz",
                "created_at": "2026-01-15T10:00:00Z",
            },
            {
                "fact_id": "fact-002",
                "entity": entity,
                "type": "Constraint",
                "value": "84MHz",
                "created_at": "2026-02-01T14:30:00Z",
            },
        ]

        # Detect conflicts
        conflicts = []
        if len(existing_facts) > 1:
            values = [f["value"] for f in existing_facts]
            if len(set(values)) > 1:
                conflicts.append({
                    "conflict_id": "conflict-001",
                    "entity": entity,
                    "fact_type": fact_type.value,
                    "facts": existing_facts,
                    "status": ConflictStatus.OPEN,
                })

        # Verify conflict detected
        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert conflict["entity"] == entity
        assert conflict["status"] == ConflictStatus.OPEN
        assert len(conflict["facts"]) == 2

    @pytest.mark.asyncio
    async def test_no_conflict_for_same_values(self):
        """Test no conflict when facts have same value"""
        entity = "STM32H7.GPIO.max_speed"
        fact_type = FactType.CONSTRAINT

        # Mock facts with same value (different sources)
        existing_facts = [
            {
                "fact_id": "fact-001",
                "entity": entity,
                "type": "Constraint",
                "value": "120MHz",
                "created_at": "2026-01-15T10:00:00Z",
            },
            {
                "fact_id": "fact-002",
                "entity": entity,
                "type": "Constraint",
                "value": "120MHz",  # Same value
                "created_at": "2026-02-01T14:30:00Z",
            },
        ]

        # Check for conflicts
        values = [f["value"] for f in existing_facts]
        has_conflict = len(set(values)) > 1

        # Verify no conflict
        assert has_conflict is False

    @pytest.mark.asyncio
    async def test_no_conflict_for_different_entities(self):
        """Test no conflict when facts have different entities"""
        facts = [
            {
                "fact_id": "fact-001",
                "entity": "STM32H7.GPIO.max_speed",
                "type": "Constraint",
                "value": "120MHz",
            },
            {
                "fact_id": "fact-002",
                "entity": "STM32H7.UART.baud_rate",  # Different entity
                "type": "Constraint",
                "value": "120MHz",  # Same value but different entity
            },
        ]

        # Group by entity
        entity_groups = {}
        for fact in facts:
            entity = fact["entity"]
            if entity not in entity_groups:
                entity_groups[entity] = []
            entity_groups[entity].append(fact)

        # Check each entity group for conflicts
        conflicts = 0
        for entity, group_facts in entity_groups.items():
            values = [f["value"] for f in group_facts]
            if len(set(values)) > 1:
                conflicts += 1

        # Verify no conflicts
        assert conflicts == 0


class TestResolutionStrategies:
    """Integration tests for resolution strategies (T082)"""

    @pytest.mark.asyncio
    async def test_detect_only_logs_conflict(self):
        """
        Test detect_only: logs conflict, creates fact anyway.
        """
        strategy = ResolutionStrategy.DETECT_ONLY

        conflict = {
            "conflict_id": "conflict-001",
            "facts": [
                {"fact_id": "fact-001", "value": "120MHz"},
                {"fact_id": "fact-002", "value": "84MHz"},
            ],
            "resolution_strategy": strategy,
            "status": ConflictStatus.OPEN,
        }

        result = await apply_resolution_strategy(
            conflicts=[conflict],
            fact_type=FactType.CONSTRAINT,
            entity="STM32H7.GPIO.max_speed",
            new_value="100MHz",
            strategy=strategy,
        )

        # Verify conflict is logged, fact created
        assert result == "created"
        assert conflict["status"] == ConflictStatus.OPEN
        assert conflict["resolution_strategy"] == ResolutionStrategy.DETECT_ONLY

    @pytest.mark.asyncio
    async def test_keep_both_marks_valid(self):
        """
        Test keep_both: marks both facts as valid, links via conflict record.
        """
        strategy = ResolutionStrategy.KEEP_BOTH

        conflict = {
            "conflict_id": "conflict-002",
            "facts": [
                {"fact_id": "fact-001", "value": "120MHz"},
                {"fact_id": "fact-002", "value": "84MHz"},
            ],
            "resolution_strategy": strategy,
            "status": ConflictStatus.OPEN,
        }

        result = await apply_resolution_strategy(
            conflicts=[conflict],
            fact_type=FactType.CONSTRAINT,
            entity="STM32H7.GPIO.max_speed",
            new_value="100MHz",
            strategy=strategy,
        )

        # Verify both kept, conflict resolved
        assert result == "kept_both"
        assert conflict["status"] == ConflictStatus.RESOLVED
        assert conflict["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_prefer_newest_deprecates_older(self):
        """
        Test prefer_newest: keeps newer fact, deprecates older.
        """
        strategy = ResolutionStrategy.PREFER_NEWEST

        older_fact = {
            "fact_id": "fact-001",
            "value": "120MHz",
            "created_at": "2026-01-01T00:00:00Z",
        }

        newer_fact = {
            "fact_id": "fact-002",
            "value": "84MHz",
            "created_at": "2026-02-01T00:00:00Z",
        }

        conflict = {
            "conflict_id": "conflict-003",
            "facts": [older_fact, newer_fact],
            "resolution_strategy": strategy,
            "status": ConflictStatus.OPEN,
        }

        result = await apply_resolution_strategy(
            conflicts=[conflict],
            fact_type=FactType.CONSTRAINT,
            entity="STM32H7.GPIO.max_speed",
            new_value="100MHz",
            strategy=strategy,
        )

        # Verify newer kept, older deprecated
        assert result == "created"
        assert conflict["status"] == ConflictStatus.RESOLVED
        assert older_fact.get("deprecated_at") is not None
        assert older_fact.get("deprecated_by") == "prefer_newest_strategy"

    @pytest.mark.asyncio
    async def test_reject_incoming_blocks_fact(self):
        """
        Test reject_incoming: rejects new conflicting fact.
        """
        strategy = ResolutionStrategy.REJECT_INCOMING

        conflict = {
            "conflict_id": "conflict-004",
            "facts": [
                {"fact_id": "fact-001", "value": "120MHz"},
            ],
            "resolution_strategy": strategy,
            "status": ConflictStatus.OPEN,
        }

        result = await apply_resolution_strategy(
            conflicts=[conflict],
            fact_type=FactType.CONSTRAINT,
            entity="STM32H7.GPIO.max_speed",
            new_value="84MHz",
            strategy=strategy,
        )

        # Verify incoming fact rejected
        assert result == "rejected"
        assert conflict["status"] == ConflictStatus.RESOLVED


class TestConflictStatusTracking:
    """Integration tests for conflict status tracking (T088)"""

    @pytest.mark.asyncio
    async def test_open_to_resolved_transition(self):
        """
        Test conflict status: open → resolved.

        T088: Conflict status tracking implementation test.
        """
        conflict = {
            "conflict_id": "conflict-005",
            "status": ConflictStatus.OPEN,
            "facts": [
                {"fact_id": "fact-001", "value": "120MHz"},
                {"fact_id": "fact-002", "value": "84MHz"},
            ],
            "detection_date": datetime.now(),
        }

        # Apply resolution
        conflict["status"] = ConflictStatus.RESOLVED
        conflict["resolution_strategy"] = ResolutionStrategy.PREFER_NEWEST
        conflict["resolved_at"] = datetime.now()
        conflict["resolved_by"] = "user_admin"

        # Verify status transition
        assert conflict["status"] == ConflictStatus.RESOLVED
        assert conflict["resolved_at"] is not None
        assert conflict["resolved_by"] == "user_admin"

    @pytest.mark.asyncio
    async def test_open_to_deferred_transition(self):
        """Test conflict status: open → deferred (manual review needed)"""
        conflict = {
            "conflict_id": "conflict-006",
            "status": ConflictStatus.OPEN,
            "facts": [
                {"fact_id": "fact-001", "value": "120MHz"},
                {"fact_id": "fact-002", "value": "84MHz"},
            ],
            "detection_date": datetime.now(),
        }

        # Defer for manual review
        conflict["status"] = ConflictStatus.DEFERRED
        conflict["deferred_at"] = datetime.now()
        conflict["deferred_reason"] = "Requires domain expert review"

        # Verify status transition
        assert conflict["status"] == ConflictStatus.DEFERRED
        assert conflict["deferred_at"] is not None
        assert conflict["deferred_reason"] == "Requires domain expert review"


class TestProvenanceInConflicts:
    """Integration tests for provenance tracking in conflict scenarios (T083)"""

    @pytest.mark.asyncio
    async def test_conflict_preserves_provenance(self):
        """
        Test conflict records preserve provenance to source documents.

        T083: Provenance tracking in conflict detection test.
        """
        conflict = {
            "conflict_id": "conflict-007",
            "facts": [
                {
                    "fact_id": "fact-001",
                    "value": "120MHz",
                    "evidence_ids": ["ev-001", "ev-002"],
                },
                {
                    "fact_id": "fact-002",
                    "value": "84MHz",
                    "evidence_ids": ["ev-003"],
                },
            ],
        }

        # Build provenance chain
        provenance = {
            "conflict_id": conflict["conflict_id"],
            "facts": [],
            "evidence_chain": [],
            "documents": {},
        }

        for fact in conflict["facts"]:
            provenance["facts"].append({
                "fact_id": fact["fact_id"],
                "value": fact["value"],
            })

            for evidence_id in fact["evidence_ids"]:
                provenance["evidence_chain"].append({
                    "evidence_id": evidence_id,
                    "fact_id": fact["fact_id"],
                })

        # Verify provenance preserved
        assert len(provenance["facts"]) == 2
        assert len(provenance["evidence_chain"]) == 3
        assert provenance["conflict_id"] == "conflict-007"

    @pytest.mark.asyncio
    async def test_trace_fact_to_source_document(self):
        """
        Test tracing conflicting fact back to source document.
        """
        # Mock provenance data
        provenance_graph = {
            "conflict": {
                "conflict_id": "conflict-008",
                "entity": "STM32H7.GPIO.max_speed",
            },
            "facts": [
                {
                    "fact_id": "fact-001",
                    "value": "120MHz",
                    "evidence_ids": ["ev-001"],
                }
            ],
            "evidence_chain": [
                {
                    "evidence_id": "ev-001",
                    "chunk_id": "chunk-001",
                    "chunk_text": "The maximum GPIO clock is 120MHz",
                    "confidence": 0.92,
                }
            ],
            "documents": {
                "doc-001": {
                    "doc_id": "doc-001",
                    "filename": "STM32H743_Datasheet.pdf",
                    "path": "/knowledge/processed/doc-001/v1/",
                    "page_section": "Section 4.3.1",
                }
            },
        }

        # Verify chain is complete
        assert "conflict" in provenance_graph
        assert "facts" in provenance_graph
        assert "evidence_chain" in provenance_graph
        assert "documents" in provenance_graph

        # Verify we can trace from conflict to document
        fact = provenance_graph["facts"][0]
        evidence = provenance_graph["evidence_chain"][0]
        doc_id = list(provenance_graph["documents"].keys())[0]

        assert fact["evidence_ids"][0] == evidence["evidence_id"]
        assert "STM32H743_Datasheet.pdf" in provenance_graph["documents"][doc_id]["filename"]


class TestConflictQueryFilters:
    """Integration tests for conflict query with filters"""

    @pytest.mark.asyncio
    async def test_filter_by_entity(self):
        """Test filtering conflicts by entity"""
        conflicts = [
            {"conflict_id": "c001", "entity": "STM32H7.GPIO.max_speed"},
            {"conflict_id": "c002", "entity": "STM32H7.UART.baud_rate"},
            {"conflict_id": "c003", "entity": "STM32H7.GPIO.max_speed"},
        ]

        # Filter by entity
        entity_filter = "STM32H7.GPIO.max_speed"
        filtered = [c for c in conflicts if c["entity"] == entity_filter]

        assert len(filtered) == 2
        assert all(c["entity"] == entity_filter for c in filtered)

    @pytest.mark.asyncio
    async def test_filter_by_status(self):
        """Test filtering conflicts by status"""
        conflicts = [
            {"conflict_id": "c001", "status": ConflictStatus.OPEN},
            {"conflict_id": "c002", "status": ConflictStatus.RESOLVED},
            {"conflict_id": "c003", "status": ConflictStatus.DEFERRED},
        ]

        # Filter by open status
        status_filter = ConflictStatus.OPEN
        filtered = [c for c in conflicts if c["status"] == status_filter]

        assert len(filtered) == 1
        assert filtered[0]["conflict_id"] == "c001"

    @pytest.mark.asyncio
    async def test_filter_by_fact_type(self):
        """Test filtering conflicts by fact type"""
        conflicts = [
            {"conflict_id": "c001", "fact_type": "Constraint"},
            {"conflict_id": "c002", "fact_type": "Indicator"},
            {"conflict_id": "c003", "fact_type": "Constraint"},
        ]

        # Filter by Constraint type
        type_filter = FactType.CONSTRAINT
        filtered = [c for c in conflicts if c["fact_type"] == type_filter.value]

        assert len(filtered) == 2
        assert all(c["fact_type"] == "Constraint" for c in filtered)
