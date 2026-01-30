"""
Memory Decay Types and Enumerations

Feature: 009-memory-decay-scoring
See: specs/009-memory-decay-scoring/data-model.md

This module defines the core types for memory decay scoring:
- ImportanceLevel: How critical a memory is (1-5)
- StabilityLevel: How likely a memory is to change (1-5)
- LifecycleState: Memory lifecycle states
- MemoryDecayAttributes: Decay-related attributes stored in node.attributes
- DecayConfig: Configuration loaded from YAML
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum, Enum
from typing import Optional

from pydantic import BaseModel, Field


class ImportanceLevel(IntEnum):
    """
    Memory importance classification (1-5).

    Higher importance = slower decay, prioritized in search results.
    """
    TRIVIAL = 1       # Ephemeral, can forget quickly
    LOW = 2           # Useful but replaceable
    MODERATE = 3      # Default, general knowledge
    HIGH = 4          # Important to work/identity
    CORE = 5          # Fundamental, never forget

    @classmethod
    def permanent_threshold(cls) -> int:
        """Minimum importance for permanent classification."""
        return cls.HIGH  # 4


class StabilityLevel(IntEnum):
    """
    Memory stability/volatility classification (1-5).

    Higher stability = longer half-life, slower decay.
    """
    VOLATILE = 1      # Changes frequently (hours/days)
    LOW = 2           # Changes regularly (days/weeks)
    MODERATE = 3      # Changes occasionally (weeks/months)
    HIGH = 4          # Rarely changes (months/years)
    PERMANENT = 5     # Never changes (facts, identity)

    @classmethod
    def permanent_threshold(cls) -> int:
        """Minimum stability for permanent classification."""
        return cls.HIGH  # 4


class LifecycleState(str, Enum):
    """
    Memory lifecycle states.

    Transition flow (actual configured values from config/decay-config.yaml):
    ACTIVE -> DORMANT (90 days minimum) -> ARCHIVED (180 days minimum) -> EXPIRED (360 days minimum) -> SOFT_DELETED -> (purged after 90 days)

    Note: Code defaults are 30/90/180 days, but config file uses 90/180/360 for more conservative retention.
    Actual transitions occur when BOTH minimum days AND decay_score thresholds are met.
    See config/decay-config.yaml for configured values.

    Any access event reactivates DORMANT/ARCHIVED memories back to ACTIVE.
    """
    ACTIVE = "ACTIVE"           # Recently accessed, full relevance
    DORMANT = "DORMANT"         # Not accessed 90+ days (config) or 30+ days (code default)
    ARCHIVED = "ARCHIVED"       # Not accessed 180+ days (config) or 90+ days (code default)
    EXPIRED = "EXPIRED"         # Marked for deletion
    SOFT_DELETED = "SOFT_DELETED"  # Deleted, in 90-day recovery window


@dataclass
class MemoryDecayAttributes:
    """
    Decay-related attributes stored in EntityNode.attributes.

    These fields extend Graphiti nodes with decay tracking without
    modifying the library (using the built-in attributes dictionary).
    """
    # Classification (assigned at ingestion)
    importance: int = 3          # 1-5, where 1=trivial, 5=core identity
    stability: int = 3           # 1-5, where 1=volatile, 5=permanent

    # Decay tracking (calculated by maintenance)
    decay_score: float = 0.0     # 0.0-1.0, where 0=fresh, 1=fully decayed
    lifecycle_state: str = LifecycleState.ACTIVE.value

    # Access tracking (updated on retrieval)
    last_accessed_at: Optional[str] = None  # ISO 8601 timestamp
    access_count: int = 0        # Total access count

    # Soft-delete tracking
    soft_deleted_at: Optional[str] = None  # ISO 8601 timestamp when soft-deleted

    def to_dict(self) -> dict:
        """Convert to dictionary for storage in node.attributes."""
        return {
            "importance": self.importance,
            "stability": self.stability,
            "decay_score": self.decay_score,
            "lifecycle_state": self.lifecycle_state,
            "last_accessed_at": self.last_accessed_at,
            "access_count": self.access_count,
            "soft_deleted_at": self.soft_deleted_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryDecayAttributes":
        """Create from node.attributes dictionary."""
        return cls(
            importance=data.get("importance", 3),
            stability=data.get("stability", 3),
            decay_score=data.get("decay_score", 0.0),
            lifecycle_state=data.get("lifecycle_state", LifecycleState.ACTIVE.value),
            last_accessed_at=data.get("last_accessed_at"),
            access_count=data.get("access_count", 0),
            soft_deleted_at=data.get("soft_deleted_at"),
        )

    def is_permanent(self) -> bool:
        """Check if memory qualifies as permanent (exempt from decay)."""
        return (
            self.importance >= ImportanceLevel.permanent_threshold() and
            self.stability >= StabilityLevel.permanent_threshold()
        )


def is_permanent(importance: int, stability: int) -> bool:
    """
    Check if memory qualifies as permanent (exempt from decay).

    Permanent memories:
    - Never accumulate decay score (always 0.0)
    - Never transition states (always ACTIVE)
    - Not subject to archival or deletion

    Args:
        importance: Importance score (1-5)
        stability: Stability score (1-5)

    Returns:
        True if memory is permanent (importance >= 4 AND stability >= 4)
    """
    return (
        importance >= ImportanceLevel.permanent_threshold() and
        stability >= StabilityLevel.permanent_threshold()
    )


# ==============================================================================
# Configuration Models (Pydantic)
# ==============================================================================

class DecayThresholdConfig(BaseModel):
    """Configuration for a single lifecycle state transition threshold."""
    days: int = Field(ge=1, description="Days inactive before transition")
    decay_score: float = Field(ge=0.0, le=1.0, description="Decay score threshold")
    max_importance: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Only transition if importance <= this value"
    )


class DecayThresholdsConfig(BaseModel):
    """Configuration for all lifecycle state transition thresholds."""
    dormant: DecayThresholdConfig = Field(
        default_factory=lambda: DecayThresholdConfig(days=30, decay_score=0.3)
    )
    archived: DecayThresholdConfig = Field(
        default_factory=lambda: DecayThresholdConfig(days=90, decay_score=0.6)
    )
    expired: DecayThresholdConfig = Field(
        default_factory=lambda: DecayThresholdConfig(days=180, decay_score=0.9, max_importance=3)
    )


class RetentionConfig(BaseModel):
    """Configuration for soft-delete retention."""
    soft_delete_days: int = Field(default=90, ge=1, description="Days to retain soft-deleted memories")


class MaintenanceConfig(BaseModel):
    """Configuration for maintenance batch processing."""
    batch_size: int = Field(default=500, ge=1, le=5000, description="Memories per batch")
    max_duration_minutes: int = Field(default=10, ge=1, description="Maximum run time in minutes")
    schedule_interval_hours: int = Field(default=24, ge=0, le=168, description="Hours between automatic maintenance runs (0 = disabled)")


class WeightsConfig(BaseModel):
    """Configuration for search scoring weights."""
    semantic: float = Field(default=0.60, ge=0.0, le=1.0, description="Vector similarity weight")
    recency: float = Field(default=0.25, ge=0.0, le=1.0, description="Temporal freshness weight")
    importance: float = Field(default=0.15, ge=0.0, le=1.0, description="Importance score weight")

    def validate_sum(self) -> bool:
        """Validate that weights sum to 1.0 (with tolerance)."""
        total = self.semantic + self.recency + self.importance
        return abs(total - 1.0) < 0.001


class DecaySettingsConfig(BaseModel):
    """Configuration for decay calculation settings."""
    base_half_life_days: float = Field(default=30.0, ge=1.0, description="Base half-life in days")
    thresholds: DecayThresholdsConfig = Field(default_factory=DecayThresholdsConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    maintenance: MaintenanceConfig = Field(default_factory=MaintenanceConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)


class ClassificationConfig(BaseModel):
    """Configuration for classification defaults."""
    default_importance: int = Field(default=3, ge=1, le=5, description="Default importance when LLM unavailable")
    default_stability: int = Field(default=3, ge=1, le=5, description="Default stability when LLM unavailable")


class PermanentConfig(BaseModel):
    """Configuration for permanent memory thresholds."""
    importance_threshold: int = Field(default=4, ge=1, le=5, description="Minimum importance for permanent")
    stability_threshold: int = Field(default=4, ge=1, le=5, description="Minimum stability for permanent")


class DecayConfig(BaseModel):
    """
    Complete decay configuration loaded from YAML.

    Example YAML structure:
    ```yaml
    decay:
      base_half_life_days: 30
      thresholds:
        dormant:
          days: 30
          decay_score: 0.3
        ...
      weights:
        semantic: 0.60
        recency: 0.25
        importance: 0.15

    classification:
      default_importance: 3
      default_stability: 3

    permanent:
      importance_threshold: 4
      stability_threshold: 4
    ```
    """
    decay: DecaySettingsConfig = Field(default_factory=DecaySettingsConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    permanent: PermanentConfig = Field(default_factory=PermanentConfig)

    @classmethod
    def default(cls) -> "DecayConfig":
        """Create configuration with default values."""
        return cls()
