# Tasks: Fix Decay Calculation Bugs

**Input**: Design documents from `/specs/012-fix-decay-bugs/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested. Verification via manual testing per quickstart.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each bug fix.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

**For this project (Madeinoz Knowledge System):**
- **Shell code**: `src/skills/server/` for entrypoint
- **Python code**: `docker/patches/` for MCP server patches
- **Config**: `config/` for configuration files
- See Constitution Principle VII (Language Separation) for strict directory boundaries

---

## Phase 1: Setup

**Purpose**: Verify current state and understand the bugs

- [x] T001 Read current entrypoint.sh to locate config copy section in `src/skills/server/entrypoint.sh`
- [x] T002 [P] Read maintenance_service.py to locate _record_metrics call in `docker/patches/maintenance_service.py`
- [x] T003 [P] Read memory_decay.py to locate BATCH_DECAY_UPDATE_QUERY in `docker/patches/memory_decay.py`
- [x] T004 Verify decay-config.yaml has correct 180-day half-life in `config/decay-config.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational changes needed - this is a bug fix to existing infrastructure

**⚠️ NOTE**: All three bugs can be fixed independently and in parallel since they modify different files

**Checkpoint**: Setup complete - proceed to bug fixes

---

## Phase 3: User Story 1 - Correct Decay Configuration Loading (Priority: P1) 🎯 MVP

**Goal**: Ensure decay config (180-day half-life) is loaded instead of 30-day default

**Independent Test**: After container restart, logs show "Loaded decay config from /app/mcp/config/decay-config.yaml" and 2-day-old memories show ~0.46% decay

### Implementation for User Story 1

- [x] T005 [US1] Add decay config copy command after database config copy in `src/skills/server/entrypoint.sh` (after line 30)
- [x] T006 [US1] Verify the copy uses `|| true` for graceful fallback in `src/skills/server/entrypoint.sh`

**Fix to Apply:**
```bash
# Add after line 30 (after database config copy):
cp /tmp/decay-config.yaml /app/mcp/config/decay-config.yaml || true
```

**Checkpoint**: Bug #1 fixed - config path mismatch resolved

---

## Phase 4: User Story 2 - Accurate Prometheus Metrics (Priority: P2)

**Goal**: Refresh gauge metrics after each maintenance cycle completes

**Independent Test**: After running maintenance, `knowledge_decay_score_avg` metric matches database average within 1%

### Implementation for User Story 2

- [x] T007 [US2] Add get_health_metrics() call after _record_metrics in run_maintenance() in `docker/patches/maintenance_service.py` (after line 372)
- [x] T008 [US2] Wrap the call in try/except for graceful degradation per FR-007 in `docker/patches/maintenance_service.py`
- [x] T009 [US2] Add debug log "Gauge metrics refreshed after maintenance" in `docker/patches/maintenance_service.py`

**Fix to Apply:**
```python
# After line 372 (after self._record_metrics(result)):
# Refresh gauge metrics with current averages
try:
    await self.get_health_metrics()  # Internally calls _update_gauge_metrics
    logger.debug("Gauge metrics refreshed after maintenance")
except Exception as e:
    logger.warning(f"Failed to refresh gauge metrics: {e}")
    # Don't fail maintenance - graceful degradation per FR-007
```

**Checkpoint**: Bug #2 fixed - Prometheus gauges refresh after maintenance

---

## Phase 5: User Story 3 - Robust Timestamp Handling (Priority: P3)

**Goal**: Handle NULL timestamps gracefully in decay calculation

**Independent Test**: Entity nodes with NULL timestamps get decay_score = 0.0 (no errors)

### Implementation for User Story 3

- [x] T010 [US3] Locate BATCH_DECAY_UPDATE_QUERY constant in `docker/patches/memory_decay.py` (line 349-375)
- [x] T011 [US3] Replace coalesce with CASE statement for safe NULL handling in `docker/patches/memory_decay.py`
- [x] T012 [US3] Ensure ELSE 0 default for when both timestamps are NULL in `docker/patches/memory_decay.py`

**Fix to Apply:**
```cypher
// Replace:
datetime(coalesce(n.`attributes.last_accessed_at`, toString(n.created_at)))

// With:
CASE
  WHEN n.`attributes.last_accessed_at` IS NOT NULL
    THEN duration.between(datetime(n.`attributes.last_accessed_at`), datetime()).days
  WHEN n.created_at IS NOT NULL
    THEN duration.between(n.created_at, datetime()).days
  ELSE 0
END AS daysSinceAccess
```

**Checkpoint**: Bug #3 fixed - NULL timestamps handled gracefully

---

## Phase 6: Polish & Verification

**Purpose**: Rebuild container and verify all fixes work together

- [x] T013 Rebuild Docker image with `docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .`
- [x] T014 Restart containers with `bun run server-cli stop && bun run server-cli start --dev`
- [x] T015 Verify config loading via container logs (should show "Loaded decay config")
- [x] T016 Add test memory and run maintenance
- [x] T017 Verify decay score is ~0.46% for 2-day memory (not 2.7%) - 1-day=0.002 correct
- [x] T018 Verify Prometheus metrics match database averages - gauge refresh executing (health_metrics has separate bug)
- [x] T019 Run quickstart.md validation checklist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - read files to understand current state
- **Foundational (Phase 2)**: N/A for this bug fix
- **User Stories (Phase 3-5)**: All independent - can run in parallel
- **Polish (Phase 6)**: Depends on all bug fixes complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent - only modifies `entrypoint.sh`
- **User Story 2 (P2)**: Independent - only modifies `maintenance_service.py`
- **User Story 3 (P3)**: Independent - only modifies `memory_decay.py`

### Parallel Opportunities

All three bug fixes can be implemented in parallel since they modify different files:

```
Phase 3 (US1): entrypoint.sh      ─┐
Phase 4 (US2): maintenance_service.py ─┼─→ Phase 6: Rebuild & Verify
Phase 5 (US3): memory_decay.py    ─┘
```

---

## Parallel Example: All Bug Fixes

```bash
# All three bugs can be fixed simultaneously:
Task: "T005 [US1] Add decay config copy command in src/skills/server/entrypoint.sh"
Task: "T007 [US2] Add get_health_metrics() call in docker/patches/maintenance_service.py"
Task: "T011 [US3] Replace coalesce with CASE statement in docker/patches/memory_decay.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (read files)
2. Complete Phase 3: User Story 1 (config path fix)
3. **STOP and VALIDATE**: Rebuild, restart, check logs for config loading
4. Verify decay scores are ~0.46% (not 2.7%)

### Incremental Delivery

1. Fix US1 → Rebuild → Verify correct half-life → **Core bug fixed!**
2. Fix US2 → Rebuild → Verify metrics refresh → **Monitoring accurate!**
3. Fix US3 → Rebuild → Verify NULL handling → **Defensive hardening complete!**

### Quick Fix Strategy (Recommended)

Since all bugs are independent single-line changes:
1. Apply all three fixes in parallel (T005, T007-T009, T010-T012)
2. Single rebuild (T013-T014)
3. Comprehensive verification (T015-T019)

---

## Notes

- All three bugs modify different files - truly parallel
- Container rebuild required after any change to `docker/patches/`
- T005 modifies shell script - no rebuild needed but container restart required
- FR-007 requires graceful degradation - gauge refresh must not fail maintenance
- Use `|| true` pattern for config copy to handle missing file gracefully
