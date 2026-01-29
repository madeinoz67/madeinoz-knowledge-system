"""
Decay Configuration Loader

Feature: 009-memory-decay-scoring
See: specs/009-memory-decay-scoring/data-model.md

This module loads decay configuration from YAML files.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import yaml

from utils.decay_types import DecayConfig

logger = logging.getLogger(__name__)

# Default configuration file location
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "decay-config.yaml"

# Environment variable for custom config path
CONFIG_PATH_ENV = "DECAY_CONFIG_PATH"

# Cached configuration
_config_cache: Optional[DecayConfig] = None


def load_decay_config(config_path: Optional[Path] = None, force_reload: bool = False) -> DecayConfig:
    """
    Load decay configuration from YAML file.

    Configuration is cached after first load. Use force_reload=True to reload.

    Args:
        config_path: Optional path to config file. If not provided:
                     1. Checks DECAY_CONFIG_PATH environment variable
                     2. Falls back to config/decay-config.yaml
        force_reload: Force reload from file even if cached

    Returns:
        DecayConfig instance with loaded or default values

    Raises:
        ValueError: If config file exists but contains invalid YAML
    """
    global _config_cache

    # Return cached config if available
    if _config_cache is not None and not force_reload:
        return _config_cache

    # Determine config path
    if config_path is None:
        env_path = os.environ.get(CONFIG_PATH_ENV)
        if env_path:
            config_path = Path(env_path)
        else:
            config_path = DEFAULT_CONFIG_PATH

    # Load from file if exists
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                raw_config = yaml.safe_load(f)

            if raw_config is None:
                logger.warning(f"Empty config file at {config_path}, using defaults")
                _config_cache = DecayConfig.default()
            else:
                _config_cache = DecayConfig.model_validate(raw_config)
                logger.info(f"Loaded decay config from {config_path}")

                # Validate weights sum to 1.0
                if not _config_cache.decay.weights.validate_sum():
                    weights = _config_cache.decay.weights
                    total = weights.semantic + weights.recency + weights.importance
                    logger.warning(
                        f"Search weights sum to {total:.3f}, not 1.0. "
                        f"Results may be unexpected."
                    )

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {config_path}: {e}")
            raise ValueError(f"Invalid YAML configuration: {e}") from e
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            raise ValueError(f"Error loading configuration: {e}") from e
    else:
        logger.info(f"Config file not found at {config_path}, using defaults")
        _config_cache = DecayConfig.default()

    return _config_cache


def get_decay_config() -> DecayConfig:
    """
    Get the current decay configuration (cached).

    Convenience function that loads config on first call and returns cached version.

    Returns:
        DecayConfig instance
    """
    return load_decay_config()


def reset_config_cache() -> None:
    """Reset the configuration cache (for testing)."""
    global _config_cache
    _config_cache = None


# Convenience accessors for common config values
def get_base_half_life() -> float:
    """Get base half-life in days."""
    return get_decay_config().decay.base_half_life_days


def get_weights() -> tuple[float, float, float]:
    """Get search weights as (semantic, recency, importance) tuple."""
    weights = get_decay_config().decay.weights
    return (weights.semantic, weights.recency, weights.importance)


def get_default_classification() -> tuple[int, int]:
    """Get default classification as (importance, stability) tuple."""
    cfg = get_decay_config().classification
    return (cfg.default_importance, cfg.default_stability)


def get_permanent_thresholds() -> tuple[int, int]:
    """Get permanent memory thresholds as (importance, stability) tuple."""
    cfg = get_decay_config().permanent
    return (cfg.importance_threshold, cfg.stability_threshold)
