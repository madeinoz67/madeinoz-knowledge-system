#!/usr/bin/env python3
"""
Graphiti MCP Server - Exposes Graphiti functionality through the Model Context Protocol (MCP)

Madeinoz Patch: Modified to search ALL groups by default when no group_ids specified.
This ensures knowledge stored in different groups (e.g., osint-profiles, main) is discoverable.

SECURITY HARDENING: Rate limiting added to prevent DoS abuse.
"""

import argparse
import asyncio
import logging
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from graphiti_core import Graphiti
from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EpisodeType, EpisodicNode
from graphiti_core.search.search_filters import SearchFilters
from graphiti_core.utils.maintenance.graph_data_operations import clear_data
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config.schema import GraphitiConfig, ServerConfig
from models.response_types import (
    EpisodeSearchResponse,
    ErrorResponse,
    FactSearchResponse,
    NodeResult,
    NodeSearchResponse,
    StatusResponse,
    SuccessResponse,
)
from services.factories import DatabaseDriverFactory, EmbedderFactory, LLMClientFactory
from services.queue_service import QueueService
from utils.formatting import format_fact_result

# Feature 006: Gemini Prompt Caching - Initialize metrics exporter
try:
    from utils.metrics_exporter import initialize_metrics_exporter
    _metrics_exporter_available = True
except ImportError:
    _metrics_exporter_available = False

# Feature 009: Decay metrics exporter
try:
    from utils.metrics_exporter import initialize_decay_metrics_exporter, get_decay_metrics_exporter
    _decay_metrics_available = True
except ImportError:
    _decay_metrics_available = False

# Feature 017: Queue metrics exporter
try:
    from utils.metrics_exporter import initialize_queue_metrics_exporter, get_queue_metrics_exporter
    _queue_metrics_available = True
except ImportError:
    _queue_metrics_available = False

# ==============================================================================
# Feature 009: Memory Decay Scoring - Import decay modules
# ==============================================================================
try:
    from utils.decay_config import get_decay_config
    from utils.decay_types import LifecycleState, MemoryDecayAttributes
    from utils.importance_classifier import classify_memory as classify_memory_impl, classify_unclassified_nodes, is_permanent
    from utils.memory_decay import (
        DecayCalculator,
        calculate_weighted_score,
        apply_weighted_scoring,
        WeightedSearchResult,
    )
    from utils.lifecycle_manager import (
        LifecycleManager,
        update_access_on_retrieval,
        recover_soft_deleted as recover_soft_deleted_impl,
    )
    from utils.maintenance_service import (
        MaintenanceService,
        get_maintenance_service,
        MaintenanceResult,
        HealthMetrics,
    )
    _decay_modules_available = True
except ImportError as e:
    _decay_modules_available = False
    logging.getLogger(__name__).debug(f'Decay modules not available: {e}')
# ==============================================================================
# Feature 018: STIX 2.1 Importer - Import stix modules
# ==============================================================================
try:
    from utils.stix_importer import (
        parse_stix_bundle,
        load_and_parse_stix_file,
        load_stix_from_url,
        process_stix_bundle,
        get_import_session_status,
        resume_import,
        InvalidSTIXError,
        generate_import_id,
    )
    _stix_importer_available = True
except ImportError as e:
    _stix_importer_available = False
    logging.getLogger(__name__).debug(f'STIX importer not available: {e}')
# ==============================================================================

# ==============================================================================
# Feature 018: OSINT/CTI Ontology Support - Import ontology modules
# ==============================================================================
try:
    from utils.ontology_config import (
        load_ontology_config,
        get_entity_types_dict,
        list_ontology_types as list_ontology_types_impl,
        validate_ontology_config,
        reload_ontology_config,
        get_decay_config_for_type,
        is_entity_type_permanent,
        get_ontology_config,
        OntologyConfig,
        OntologyDecayConfig,
    )
    _ontology_modules_available = True
except ImportError as e:
    _ontology_modules_available = False
    logging.getLogger(__name__).debug(f'Ontology modules not available: {e}')
# ==============================================================================

# ============================================================================
# Madeinoz Patch: Date Input Parsing for Temporal Search
# ============================================================================
def parse_date_input(date_str: str | None) -> datetime | None:
    """
    Parse ISO 8601 or relative date strings to datetime.

    Supports:
    - ISO 8601: "2026-01-26", "2026-01-26T00:00:00Z"
    - Relative: "today", "yesterday"
    - Duration: "7d", "7 days", "7 days ago", "1w", "1 week", "1m", "1 month"

    Args:
        date_str: Date string to parse (ISO or relative)

    Returns:
        datetime object in UTC, or None if input is None/empty

    Raises:
        ValueError: If date string cannot be parsed
    """
    if not date_str:
        return None

    # Try ISO format first
    try:
        # Handle ISO with or without Z suffix
        normalized = date_str.replace('Z', '+00:00')
        # Handle date-only format (add time)
        if 'T' not in normalized and len(normalized) == 10:
            normalized = f"{normalized}T00:00:00+00:00"
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    # Relative date parsing
    date_str_lower = date_str.lower().strip()
    now = datetime.now(timezone.utc)

    if date_str_lower == 'today':
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if date_str_lower == 'yesterday':
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    if date_str_lower == 'now':
        return now

    # Parse "Nd", "N days", "N days ago", "1w", "1 week", "1m", "1 month"
    match = re.match(r'(\d+)\s*(d|days?|w|weeks?|m|months?)(\s+ago)?', date_str_lower)
    if match:
        num = int(match.group(1))
        unit = match.group(2)[0]  # d, w, or m
        if unit == 'd':
            return now - timedelta(days=num)
        elif unit == 'w':
            return now - timedelta(weeks=num)
        elif unit == 'm':
            return now - timedelta(days=num * 30)  # Approximate month

    raise ValueError(f"Cannot parse date: {date_str}")


# ============================================================================
# Madeinoz Patch: FalkorDB Lucene Sanitization
# ============================================================================
# Import and apply the FalkorDB Lucene sanitization patch
# This fixes RediSearch syntax errors with special characters in group_ids
# and episode content. Addresses Graphiti issues #815, #1118.
try:
    # Try to import from patches directory (for Docker builds)
    from utils.falkordb_lucene import patch_falkor_driver
    _lucene_patch_applied = patch_falkor_driver()
except ImportError:
    # Patches directory not available (development mode)
    _lucene_patch_applied = False
# ============================================================================

# ============================================================================
# Feature 023: Qdrant RAG Migration - Import Qdrant modules
# ============================================================================
try:
    from patches.qdrant_client import QdrantClient, get_qdrant_client
    from patches.docling_ingester import DoclingIngester, IngestionConfig, get_docling_ingester
    _qdrant_available = True
    logging.getLogger(__name__).info("Madeinoz Patch: Feature 023 - Qdrant RAG migration (active)")
except ImportError as e:
    _qdrant_available = False
    logging.getLogger(__name__).debug(f'Qdrant client not available: {e}')
# ============================================================================

# Load .env file from mcp_server directory
mcp_server_dir = Path(__file__).parent.parent
env_file = mcp_server_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    # Try current working directory as fallback
    load_dotenv()


# ============================================================================
# SECURITY: Rate Limiting Middleware
# ============================================================================

class RateLimiter:
    """
    Simple in-memory rate limiter to prevent DoS attacks.

    Uses sliding window algorithm: tracks request timestamps per client
    and allows up to max_requests requests per time_window_seconds.

    SECURITY NOTE:
    - For production with multiple workers, use Redis-based rate limiting
    - This implementation is suitable for single-instance deployments
    """

    def __init__(
        self,
        max_requests: int = 60,
        time_window_seconds: int = 60,
        cleanup_interval: int = 300,
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed per window
            time_window_seconds: Time window in seconds
            cleanup_interval: How often to clean old entries (seconds)
        """
        self.max_requests = max_requests
        self.time_window = time_window_seconds
        self.cleanup_interval = cleanup_interval
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.last_cleanup = time.time()

    def is_allowed(self, client_id: str) -> bool:
        """
        Check if request from client is allowed.

        Args:
            client_id: Unique identifier for the client (IP address)

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()

        # Periodic cleanup of old entries
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup(now)

        # Get recent requests from this client
        client_requests = self.requests[client_id]

        # Remove requests outside the time window
        self.requests[client_id] = [
            req_time for req_time in client_requests
            if now - req_time < self.time_window
        ]

        # Check if limit exceeded
        if len(self.requests[client_id]) >= self.max_requests:
            return False

        # Record this request
        self.requests[client_id].append(now)
        return True

    def _cleanup(self, now: float) -> None:
        """Remove old request timestamps from all clients."""
        cutoff = now - self.time_window * 2  # Keep slightly more than window
        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > cutoff
            ]
            # Remove empty client entries
            if not self.requests[client_id]:
                del self.requests[client_id]
        self.last_cleanup = now


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware for rate limiting MCP requests.

    Applies rate limiting to all HTTP endpoints except /health.
    """

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path == '/health':
            return await call_next(request)

        # Get client IP (respect X-Forwarded-For for proxy deployments)
        client_ip = self._get_client_ip(request)

        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip):
            self.logger.warning(f'Rate limit exceeded for {client_ip}')
            return JSONResponse(
                {'error': 'Rate limit exceeded', 'retry_after': self.rate_limiter.time_window},
                status_code=429,
            )

        # Process request
        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request, handling proxy scenarios.

        Priority:
        1. X-Forwarded-For header (when behind proxy)
        2. X-Real-IP header (nginx-style)
        3. Direct client address
        """
        # Check X-Forwarded-For (may contain multiple IPs, take first)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        # Check X-Real-IP
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip

        # Fall back to direct address
        if request.client:
            return request.client.host

        return 'unknown'


# Global rate limiter instance (configured at startup)
rate_limiter: Optional[RateLimiter] = None


# ============================================================================
# SECURITY: Configuration Path Validation
# ============================================================================

class ConfigPathError(Exception):
    """Raised when configuration path validation fails."""
    pass


def validate_config_path(config_path: Path, allow_directories: bool = False) -> Path:
    """
    Validate that configuration file path is safe to use.

    SECURITY: Prevents directory traversal and access to sensitive files.

    Args:
        config_path: Path to configuration file
        allow_directories: If True, allow directories (for config dirs)

    Returns:
        The validated path (resolved to absolute path)

    Raises:
        ConfigPathError: If path is invalid or unsafe

    Security rules:
    - Path must be within allowed directories
    - No parent directory traversal (..) in final path
    - For files: must have .yaml or .yml extension
    - Path must exist
    """
    # Resolve to absolute path (this also normalizes ../..)
    try:
        resolved = config_path.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as e:
        raise ConfigPathError(f'Configuration path does not exist: {config_path}') from e

    # Security check: Ensure no parent directory traversal in final path
    # This is redundant with resolve() above, but we keep it for defense in depth
    path_str = str(resolved)
    if '../' in path_str or '..\\' in path_str:
        raise ConfigPathError(f'Parent directory traversal not allowed: {config_path}')

    # Allowed base directories for config files
    # In production, these should be further restricted
    allowed_bases = [
        Path('/app/mcp/config'),  # Container default
        Path('/app/config'),       # Alternative container path
        Path.cwd(),                # Current working directory
        Path.home() / '.config',   # User config directory
    ]

    # Check if path is within allowed directories
    is_allowed = False
    for base in allowed_bases:
        try:
            resolved.relative_to(base)
            is_allowed = True
            break
        except ValueError:
            # Path is not within this base directory
            continue

    if not is_allowed:
        # Check if it's in the current project structure (for development)
        try:
            project_root = Path(__file__).parent.parent.parent
            resolved.relative_to(project_root)
            is_allowed = True
        except ValueError:
            pass

    if not is_allowed:
        raise ConfigPathError(
            f'Configuration path must be within allowed directories: {config_path}\n'
            f'Allowed bases: {allowed_bases}'
        )

    # For files, check extension
    if not allow_directories and resolved.is_file():
        if resolved.suffix.lower() not in ['.yaml', '.yml']:
            raise ConfigPathError(
                f'Configuration file must have .yaml or .yml extension: {config_path}'
            )

    return resolved


# Semaphore limit for concurrent Graphiti operations.
SEMAPHORE_LIMIT = int(os.getenv('SEMAPHORE_LIMIT', 10))

# Madeinoz Patch: Enable searching across ALL groups when no group_ids specified
# Set to 'true' to enable, any other value (or unset) to disable
SEARCH_ALL_GROUPS = os.getenv('GRAPHITI_SEARCH_ALL_GROUPS', 'false').lower() == 'true'

# ============================================================================
# SECURITY: Rate Limiting Configuration
# ============================================================================
# Rate limiting to prevent DoS abuse
# RATE_LIMIT_MAX_REQUESTS: Maximum requests per time window per IP
# RATE_LIMIT_WINDOW_SECONDS: Time window in seconds
# RATE_LIMIT_ENABLED: Set to 'false' to disable (not recommended for production)
RATE_LIMIT_MAX_REQUESTS = int(os.getenv('RATE_LIMIT_MAX_REQUESTS', '60'))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv('RATE_LIMIT_WINDOW_SECONDS', '60'))
RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'


# Configure structured logging with timestamps
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    stream=sys.stderr,
)

# Configure specific loggers
logging.getLogger('uvicorn').setLevel(logging.INFO)
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
logging.getLogger('mcp.server.streamable_http_manager').setLevel(logging.WARNING)


def configure_uvicorn_logging():
    """Configure uvicorn loggers to match our format after they're created."""
    for logger_name in ['uvicorn', 'uvicorn.error', 'uvicorn.access']:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        uvicorn_logger.addHandler(handler)
        uvicorn_logger.propagate = False


logger = logging.getLogger(__name__)

# Create global config instance - will be properly initialized later
config: GraphitiConfig

# ============================================================================
# Madeinoz Patch: Dynamic group_id discovery with short-lived cache
# ============================================================================
# Cache for all group_ids - refreshes every 30 seconds
_group_ids_cache: list[str] = []
_group_ids_cache_time: float = 0
_GROUP_IDS_CACHE_TTL: float = 30.0  # seconds


async def get_all_group_ids(client: Graphiti) -> list[str]:
    """
    Dynamically fetch all distinct group_ids from the database.

    Uses a short-lived cache (30 seconds) to avoid excessive DB queries
    while ensuring new groups are discoverable quickly.

    Madeinoz Patch: This function enables searching across ALL groups by default.
    """
    global _group_ids_cache, _group_ids_cache_time

    current_time = time.time()

    # Return cached value if still fresh
    if _group_ids_cache and (current_time - _group_ids_cache_time) < _GROUP_IDS_CACHE_TTL:
        return _group_ids_cache

    try:
        # Query for all distinct group_ids
        async with client.driver.session() as session:
            result = await session.run(
                'MATCH (n) WHERE n.group_id IS NOT NULL RETURN DISTINCT n.group_id AS group_id'
            )
            records = [record async for record in result]
            group_ids = [record['group_id'] for record in records if record['group_id']]

        # Update cache
        _group_ids_cache = group_ids
        _group_ids_cache_time = current_time

        logger.debug(f'Madeinoz Patch: Discovered {len(group_ids)} group_ids: {group_ids}')
        return group_ids

    except Exception as e:
        logger.warning(f'Madeinoz Patch: Failed to fetch group_ids, using cache: {e}')
        # Return stale cache or empty list on error
        return _group_ids_cache if _group_ids_cache else []


async def get_effective_group_ids(
    client: Graphiti,
    provided_group_ids: list[str] | None,
    fallback_group_id: str | None = None
) -> list[str]:
    """
    Get the effective group_ids for a search operation.

    Madeinoz Patch: When no group_ids are provided AND GRAPHITI_SEARCH_ALL_GROUPS=true,
    fetches ALL groups dynamically instead of falling back to a single default group.

    Args:
        client: The Graphiti client
        provided_group_ids: Group IDs explicitly provided by the caller
        fallback_group_id: Legacy fallback (used when patch disabled or empty database)

    Returns:
        List of group_ids to search
    """
    if provided_group_ids is not None:
        # Explicit group_ids provided - use them
        return provided_group_ids

    # Madeinoz Patch: Check if search-all-groups is enabled
    if SEARCH_ALL_GROUPS:
        # No group_ids provided - search ALL groups
        all_groups = await get_all_group_ids(client)

        if all_groups:
            logger.debug(f'Madeinoz Patch: Searching across all {len(all_groups)} groups')
            return all_groups

    # Fallback to default group (original behavior or empty database)
    if fallback_group_id:
        return [fallback_group_id]

    return []
# ============================================================================


# MCP server instructions
GRAPHITI_MCP_INSTRUCTIONS = """
Graphiti is a memory service for AI agents built on a knowledge graph. Graphiti performs well
with dynamic data such as user interactions, changing enterprise data, and external information.

Graphiti transforms information into a richly connected knowledge network, allowing you to
capture relationships between concepts, entities, and information. The system organizes data as episodes
(content snippets), nodes (entities), and facts (relationships between entities), creating a dynamic,
queryable memory store that evolves with new information. Graphiti supports multiple data formats, including
structured JSON data, enabling seamless integration with existing data pipelines and systems.

Facts contain temporal metadata, allowing you to track the time of creation and whether a fact is invalid
(superseded by new information).

Key capabilities:
1. Add episodes (text, messages, or JSON) to the knowledge graph with the add_memory tool
2. Search for nodes (entities) in the graph using natural language queries with search_nodes
3. Find relevant facts (relationships between entities) with search_facts
4. Retrieve specific entity edges or episodes by UUID
5. Manage the knowledge graph with tools like delete_episode, delete_entity_edge, and clear_graph

The server connects to a database for persistent storage and uses language models for certain operations.
Each piece of information is organized by group_id, allowing you to maintain separate knowledge domains.

When adding information, provide descriptive names and detailed content to improve search quality.
When searching, use specific queries and consider filtering by group_id for more relevant results.

For optimal performance, ensure the database is properly configured and accessible, and valid
API keys are provided for any language model operations.
"""

# MCP server instance
mcp = FastMCP(
    'Graphiti Agent Memory',
    instructions=GRAPHITI_MCP_INSTRUCTIONS,
)

# Global services
graphiti_service: Optional['GraphitiService'] = None
queue_service: QueueService | None = None

# Global client for backward compatibility
graphiti_client: Graphiti | None = None
semaphore: asyncio.Semaphore

# Feature 009: Global maintenance service reference for shutdown
_maintenance_service: Optional[Any] = None

# Feature 017: Global queue metrics exporter reference
_queue_metrics_exporter: Optional[Any] = None


class GraphitiService:
    """Graphiti service using the unified configuration system."""

    def __init__(self, config: GraphitiConfig, semaphore_limit: int = 10):
        self.config = config
        self.semaphore_limit = semaphore_limit
        self.semaphore = asyncio.Semaphore(semaphore_limit)
        self.client: Graphiti | None = None
        self.entity_types = None
        self.llm_client = None

    async def initialize(self) -> None:
        """Initialize the Graphiti client with factory-created components."""
        try:
            # Create clients using factories
            llm_client = None
            embedder_client = None

            # Create LLM client based on configured provider
            try:
                llm_client = LLMClientFactory.create(self.config.llm)
            except Exception as e:
                logger.warning(f'Failed to create LLM client: {e}')

            # Create embedder client based on configured provider
            try:
                embedder_client = EmbedderFactory.create(self.config.embedder)
            except Exception as e:
                logger.warning(f'Failed to create embedder client: {e}')

            # Get database configuration
            db_config = DatabaseDriverFactory.create_config(self.config.database)

            # Build entity types from configuration
            # Feature 018: Load ontology configuration for custom entity/relationship types
            custom_types = None
            ontology_config = None

            # First, try loading from ontology YAML file
            if _ontology_modules_available:
                try:
                    ontology_config = load_ontology_config()
                    if ontology_config.entity_types:
                        logger.info(f'Feature 018: Loading {len(ontology_config.entity_types)} custom entity types from ontology configuration')
                        custom_types = {}
                        for entity_type in ontology_config.entity_types:
                            entity_model = type(
                                entity_type.name,
                                (BaseModel,),
                                {
                                    '__doc__': entity_type.description,
                                },
                            )
                            custom_types[entity_type.name] = entity_model
                            logger.debug(f'  - Registered entity type: {entity_type.name}')
                except Exception as e:
                    logger.warning(f'Feature 018: Failed to load ontology configuration: {e}')

            # Fall back to legacy config.entity_types if ontology didn't load
            if not custom_types and self.config.graphiti.entity_types:
                custom_types = {}
                for entity_type in self.config.graphiti.entity_types:
                    entity_model = type(
                        entity_type.name,
                        (BaseModel,),
                        {
                            '__doc__': entity_type.description,
                        },
                    )
                    custom_types[entity_type.name] = entity_model

            # Store entity types and ontology config for later use
            self.entity_types = custom_types
            self.ontology_config = ontology_config

            # Feature 018 T042: Store relationship types for extraction
            self.relationship_types = {}
            if _ontology_modules_available and ontology_config and ontology_config.relationship_types:
                logger.info(f'Feature 018: Loading {len(ontology_config.relationship_types)} custom relationship types from ontology configuration')
                for rel_type in ontology_config.relationship_types:
                    self.relationship_types[rel_type.name] = rel_type
                    logger.debug(f'  - Registered relationship type: {rel_type.name}')
                    logger.debug(f'    Source types: {rel_type.source_entity_types}')
                    logger.debug(f'    Target types: {rel_type.target_entity_types}')

            # Initialize Graphiti client with appropriate driver
            try:
                if self.config.database.provider.lower() == 'falkordb':
                    from graphiti_core.driver.falkordb_driver import FalkorDriver

                    falkor_driver = FalkorDriver(
                        host=db_config['host'],
                        port=db_config['port'],
                        password=db_config['password'],
                        database=db_config['database'],
                    )

                    self.client = Graphiti(
                        graph_driver=falkor_driver,
                        llm_client=llm_client,
                        embedder=embedder_client,
                        max_coroutines=self.semaphore_limit,
                    )
                else:
                    # For Neo4j (default), use the original approach
                    self.client = Graphiti(
                        uri=db_config['uri'],
                        user=db_config['user'],
                        password=db_config['password'],
                        llm_client=llm_client,
                        embedder=embedder_client,
                        max_coroutines=self.semaphore_limit,
                    )
            except Exception as db_error:
                error_msg = str(db_error).lower()
                if 'connection refused' in error_msg or 'could not connect' in error_msg:
                    db_provider = self.config.database.provider
                    if db_provider.lower() == 'falkordb':
                        raise RuntimeError(
                            f'\n{"=" * 70}\n'
                            f'Database Connection Error: FalkorDB is not running\n'
                            f'{"=" * 70}\n\n'
                            f'FalkorDB at {db_config["host"]}:{db_config["port"]} is not accessible.\n\n'
                            f'To start FalkorDB:\n'
                            f'  - Using Docker Compose: cd mcp_server && docker compose up\n'
                            f'  - Or run FalkorDB manually: docker run -p 6379:6379 falkordb/falkordb\n\n'
                            f'{"=" * 70}\n'
                        ) from db_error
                    elif db_provider.lower() == 'neo4j':
                        raise RuntimeError(
                            f'\n{"=" * 70}\n'
                            f'Database Connection Error: Neo4j is not running\n'
                            f'{"=" * 70}\n\n'
                            f'Neo4j at {db_config.get("uri", "unknown")} is not accessible.\n\n'
                            f'To start Neo4j:\n'
                            f'  - Using Docker Compose: cd mcp_server && docker compose -f docker/docker-compose-neo4j.yml up\n'
                            f'  - Or install Neo4j Desktop from: https://neo4j.com/download/\n'
                            f'  - Or run Neo4j manually: docker run -p 7474:7474 -p 7687:7687 neo4j:latest\n\n'
                            f'{"=" * 70}\n'
                        ) from db_error
                    else:
                        raise RuntimeError(
                            f'\n{"=" * 70}\n'
                            f'Database Connection Error: {db_provider} is not running\n'
                            f'{"=" * 70}\n\n'
                            f'{db_provider} at {db_config.get("uri", "unknown")} is not accessible.\n\n'
                            f'Please ensure {db_provider} is running and accessible.\n\n'
                            f'{"=" * 70}\n'
                        ) from db_error
                raise

            # Build indices
            await self.client.build_indices_and_constraints()

            # Feature 022: Initialize promotion module with Graphiti client
            # This enables kg.promoteFromEvidence and kg.promoteFromQuery MCP tools
            try:
                from . import promotion
                promotion.init_graphiti(self.client)
                logger.info('Feature 022: LKAP promotion module initialized with Graphiti client')
            except ImportError:
                logger.debug('Feature 022: Promotion module not available (LKAP not installed)')
            except Exception as init_err:
                logger.warning(f'Feature 022: Failed to initialize promotion module (non-critical): {init_err}')

            # Store llm_client for later use in maintenance service
            self.llm_client = llm_client

            logger.info('Successfully initialized Graphiti client')
            if SEARCH_ALL_GROUPS:
                logger.info('Madeinoz Patch: Search will query ALL groups when none specified')
            else:
                logger.info('Madeinoz Patch: Search-all-groups DISABLED (set GRAPHITI_SEARCH_ALL_GROUPS=true to enable)')

            # Log Lucene patch status - check if sanitization is actually active
            # Import the detection function to check runtime behavior
            try:
                from utils.falkordb_lucene import requires_lucene_sanitization, get_database_backend

                lucene_active = requires_lucene_sanitization()
                detected_backend = get_database_backend()

                if _lucene_patch_applied:
                    if lucene_active:
                        logger.info(f'Madeinoz Patch: FalkorDB Lucene sanitization ACTIVE (backend: {detected_backend})')
                    else:
                        logger.info(f'Madeinoz Patch: FalkorDB Lucene sanitization INACTIVE (backend: {detected_backend}, no escaping needed)')
                else:
                    if detected_backend == 'falkordb':
                        logger.warning(f'Madeinoz Patch: FalkorDB backend detected but Lucene sanitization NOT APPLIED - special characters may cause errors')
                    else:
                        logger.debug(f'Madeinoz Patch: Using {detected_backend} backend (no Lucene sanitization needed)')
            except ImportError:
                # Patch module not available - this is OK for development
                logger.debug('Madeinoz Patch: Lucene sanitization module not available (development mode)')

            if llm_client:
                logger.info(
                    f'Using LLM provider: {self.config.llm.provider} / {self.config.llm.model}'
                )
            else:
                logger.info('No LLM client configured - entity extraction will be limited')

            if embedder_client:
                logger.info(f'Using Embedder provider: {self.config.embedder.provider}')
            else:
                logger.info('No Embedder client configured - search will be limited')

            if self.entity_types:
                entity_type_names = list(self.entity_types.keys())
                logger.info(f'Using custom entity types: {", ".join(entity_type_names)}')
            else:
                logger.info('Using default entity types')

            logger.info(f'Using database: {self.config.database.provider}')
            logger.info(f'Using group_id: {self.config.graphiti.group_id}')

            # Feature 009: Initialize decay system if available
            if _decay_modules_available:
                try:
                    from utils.decay_migration import run_migration
                    migration_result = await run_migration(
                        self.client.driver,
                        create_indexes=True,
                        backfill=True,
                        dry_run=False,
                    )
                    if migration_result.get('backfill', {}).get('nodes_updated', 0) > 0:
                        logger.info(f"Feature 009: Backfilled {migration_result['backfill']['nodes_updated']} nodes with decay attributes")
                    if migration_result.get('indexes', {}):
                        logger.info('Feature 009: Decay indexes created/verified')
                    logger.info('Feature 009: Memory decay scoring system initialized')

                    # Feature 009: Calculate initial health metrics to update dashboard counts
                    try:
                        from utils.maintenance_service import get_maintenance_service
                        global _maintenance_service
                        maintenance = get_maintenance_service(self.client.driver, llm_client=self.llm_client)
                        _maintenance_service = maintenance  # Store for shutdown
                        health_metrics = await maintenance.get_health_metrics()
                        total_memories = health_metrics.aggregates.get('total', 0)
                        logger.info(f"Feature 009: Initial health metrics calculated - {total_memories} memories, dashboard counts updated")

                        # Feature 009: Start scheduled maintenance if configured
                        await maintenance.start_scheduled_maintenance()
                    except Exception as health_err:
                        logger.warning(f'Feature 009: Initial health metrics calculation failed (non-critical): {health_err}')

                except Exception as decay_err:
                    logger.warning(f'Feature 009: Decay migration failed (non-critical): {decay_err}')
            else:
                logger.debug('Feature 009: Decay modules not available')

        except Exception as e:
            logger.error(f'Failed to initialize Graphiti client: {e}')
            raise

    async def get_client(self) -> Graphiti:
        """Get the Graphiti client, initializing if necessary."""
        if self.client is None:
            await self.initialize()
        if self.client is None:
            raise RuntimeError('Failed to initialize Graphiti client')
        return self.client

    def get_ontology_types(self, include_builtin: bool = False) -> dict:
        """
        Get loaded ontology types (entity and relationship types).

        Feature 018: Returns custom ontology types loaded from configuration.

        Args:
            include_builtin: Include Graphiti built-in types (Person, Organization, etc.)

        Returns:
            Dictionary with "entity_types" and "relationship_types" lists
        """
        if _ontology_modules_available:
            return list_ontology_types_impl(include_builtin=include_builtin)
        return {"entity_types": [], "relationship_types": []}


@mcp.tool()
async def add_memory(
    name: str,
    episode_body: str,
    group_id: str | None = None,
    source: str = 'text',
    source_description: str = '',
    uuid: str | None = None,
) -> SuccessResponse | ErrorResponse:
    """Add an episode to memory. This is the primary way to add information to the graph.

    This function returns immediately and processes the episode addition in the background.
    Episodes for the same group_id are processed sequentially to avoid race conditions.

    Args:
        name (str): Name of the episode
        episode_body (str): The content of the episode to persist to memory.
        group_id (str, optional): A unique ID for this graph.
        source (str, optional): Source type - MUST be one of: 'text', 'json', or 'message'. Defaults to 'text'.
        source_description (str, optional): Custom identifier for the source (e.g., 'osint-recon', 'user-input', 'api-import')
        uuid (str, optional): Optional UUID for the episode
    """
    global graphiti_service, queue_service

    if graphiti_service is None or queue_service is None:
        return ErrorResponse(error='Services not initialized')

    try:
        # Use the provided group_id or fall back to the default from config
        effective_group_id = group_id or config.graphiti.group_id

        # Try to parse the source as an EpisodeType enum, with fallback to text
        episode_type = EpisodeType.text
        if source:
            try:
                episode_type = EpisodeType[source.lower()]
            except (KeyError, AttributeError):
                logger.warning(f"Unknown source type '{source}'. Valid types: text, json, message. Use source_description for custom identifiers.")
                episode_type = EpisodeType.text

        # Feature 017: Record enqueue metric
        if _queue_metrics_exporter:
            try:
                _queue_metrics_exporter.record_enqueue(queue_name=effective_group_id, priority="normal")
            except Exception as metrics_err:
                logger.debug(f"Failed to record enqueue metric: {metrics_err}")

        # Submit to queue service for async processing
        processing_start = time.time()
        processing_success = True
        error_type = None

        try:
            await queue_service.add_episode(
                group_id=effective_group_id,
                name=name,
                content=episode_body,
                source_description=source_description,
                episode_type=episode_type,
                entity_types=graphiti_service.entity_types,
                uuid=uuid or None,
            )
        except Exception as add_err:
            processing_success = False
            error_type = type(add_err).__name__
            raise
        finally:
            # Feature 017: Record dequeue and processing complete metrics
            if _queue_metrics_exporter:
                try:
                    duration = time.time() - processing_start
                    _queue_metrics_exporter.record_dequeue(queue_name=effective_group_id)
                    _queue_metrics_exporter.record_processing_complete(
                        queue_name=effective_group_id,
                        duration=duration,
                        success=processing_success,
                        error_type=error_type
                    )
                except Exception as metrics_err:
                    logger.debug(f"Failed to record processing metrics: {metrics_err}")

        # Feature 011: Spawn immediate background classification for unclassified nodes
        try:
            client = await graphiti_service.get_client()
            asyncio.create_task(
                classify_unclassified_nodes(
                    driver=client.driver,
                    llm_client=graphiti_service.llm_client,
                    batch_size=100,
                    max_nodes=100,
                )
            )
            logger.info(f"Spawned immediate background classification for episode '{name}'")
        except Exception as classify_err:
            logger.warning(f"Failed to spawn background classification: {classify_err}")

        return SuccessResponse(
            message=f"Episode '{name}' queued for processing in group '{effective_group_id}'"
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error queuing episode: {error_msg}')
        return ErrorResponse(error=f'Error queuing episode: {error_msg}')


@mcp.tool()
async def search_nodes(
    query: str,
    group_ids: list[str] | None = None,
    max_nodes: int = 10,
    entity_types: list[str] | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    include_weighted_scores: bool = False,
    exclude_lifecycle_states: list[str] | None = None,
) -> NodeSearchResponse | ErrorResponse:
    logger.info(f"🔍 search_nodes CALLED: query='{query}', include_weighted_scores={include_weighted_scores}, _decay_modules_available={_decay_modules_available}")
    """Search for nodes in the graph memory with optional temporal filtering and weighted scoring.

    Args:
        query: The search query
        group_ids: Optional list of group IDs to filter results
        max_nodes: Maximum number of nodes to return (default: 10)
        entity_types: Optional list of entity type names to filter by
        created_after: Return nodes created after this date (ISO 8601 or relative: "today", "7d", "1 week ago")
        created_before: Return nodes created before this date (ISO 8601 or relative)
        include_weighted_scores: If True, apply weighted scoring (60% semantic + 25% recency + 15% importance) and include score breakdown
        exclude_lifecycle_states: Optional list of lifecycle states to exclude (e.g., ['SOFT_DELETED', 'EXPIRED'])
    """
    global graphiti_service

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    # Feature 009: Track search metrics
    import time
    search_start = time.time()

    try:
        client = await graphiti_service.get_client()

        # Madeinoz Patch: Use dynamic group_id discovery
        effective_group_ids = await get_effective_group_ids(
            client, group_ids, config.graphiti.group_id
        )

        # Madeinoz Patch: Parse temporal filters
        after_date = parse_date_input(created_after)
        before_date = parse_date_input(created_before)
        has_temporal_filter = after_date is not None or before_date is not None

        # Create search filters
        search_filters = SearchFilters(
            node_labels=entity_types,
        )

        # Use the search_ method with node search config
        from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

        # If temporal filtering or weighted scoring is needed, fetch more results
        fetch_limit = max_nodes * 3 if (has_temporal_filter or include_weighted_scores) else max_nodes

        results = await client.search_(
            query=query,
            config=NODE_HYBRID_SEARCH_RRF,
            group_ids=effective_group_ids,
            search_filter=search_filters,
        )

        # Extract nodes from results
        nodes = results.nodes if results.nodes else []

        # Feature 009: Filter by lifecycle state if requested
        if exclude_lifecycle_states and _decay_modules_available:
            exclude_states = set(s.upper() for s in exclude_lifecycle_states)
            filtered_nodes = []
            for node in nodes:
                attrs = node.attributes if hasattr(node, "attributes") else {}
                state = attrs.get('attributes.lifecycle_state', 'ACTIVE')
                if state.upper() not in exclude_states:
                    filtered_nodes.append(node)
            nodes = filtered_nodes
            logger.debug(f'Feature 009: Lifecycle filter applied, {len(nodes)} nodes remaining')

        # Madeinoz Patch: Apply temporal filtering if specified
        if has_temporal_filter and nodes:
            filtered_nodes = []
            for node in nodes:
                if node.created_at is None:
                    continue  # Skip nodes without creation date
                node_date = node.created_at
                # Make sure node_date is timezone-aware for comparison
                if node_date.tzinfo is None:
                    node_date = node_date.replace(tzinfo=timezone.utc)
                # Apply after filter
                if after_date and node_date < after_date:
                    continue
                # Apply before filter
                if before_date and node_date > before_date:
                    continue
                filtered_nodes.append(node)
            nodes = filtered_nodes
            logger.debug(f'Madeinoz Patch: Temporal filter applied, {len(nodes)} nodes remaining')

        if not nodes:
            # Feature 009: Record zero-result search metrics
            if _decay_metrics_available:
                try:
                    decay_metrics = get_decay_metrics_exporter()
                    if decay_metrics:
                        search_latency = time.time() - search_start
                        decay_metrics.record_search_execution(
                            query_latency_seconds=search_latency,
                            result_count=0,
                            is_zero_result=True
                        )
                except Exception as metrics_err:
                    logger.debug(f'Failed to record search metrics: {metrics_err}')
            return NodeSearchResponse(message='No relevant nodes found', nodes=[])

        # Feature 009: Apply weighted scoring if requested
        if include_weighted_scores and _decay_modules_available:
            logger.info(f"🎯 WEIGHTED SCORING ENABLED for query '{query}' with {len(nodes)} nodes")
            # Generate synthetic semantic scores (in production, these would come from the search)
            # For now, use position-based scores (first result = highest)
            semantic_scores = [1.0 - (i * 0.05) for i in range(len(nodes))]

            # Apply weighted scoring
            weighted_results = apply_weighted_scoring(nodes, semantic_scores)

            # Update access tracking for retrieved nodes (async, non-blocking)
            for node in nodes:
                try:
                    await update_access_on_retrieval(client.driver, node.uuid)
                except Exception as e:
                    logger.warning(f'Failed to update access for node {node.uuid}: {e}')

            # Apply limit after re-ranking
            weighted_results = weighted_results[:max_nodes]

            # Format results with weighted scores
            node_results = []
            for wr in weighted_results:
                node_results.append(
                    NodeResult(
                        uuid=wr.uuid,
                        name=wr.name,
                        labels=[],  # Labels not available in WeightedSearchResult
                        created_at=wr.last_accessed_at,  # Use last_accessed as created fallback
                        summary=wr.summary,
                        group_id='',  # Group ID not available in WeightedSearchResult
                        attributes={
                            'weighted_score': wr.weighted_score,
                            'score_breakdown': wr.score_breakdown,
                            'lifecycle_state': wr.lifecycle_state,
                            'importance': wr.importance,
                            'stability': wr.stability,
                            'decay_score': wr.decay_score,
                            'last_accessed_at': wr.last_accessed_at,
                        },
                    )
                )

            # Feature 009: Record search metrics for weighted results
            if _decay_metrics_available:
                try:
                    decay_metrics = get_decay_metrics_exporter()
                    if decay_metrics:
                        search_latency = time.time() - search_start
                        is_zero_result = len(node_results) == 0
                        decay_metrics.record_search_execution(
                            query_latency_seconds=search_latency,
                            result_count=len(node_results),
                            is_zero_result=is_zero_result
                        )
                        # Record memory access patterns for retrieved nodes
                        for wr in weighted_results:
                            try:
                                # Calculate days since last access
                                days_since_access = None
                                if wr.last_accessed_at:
                                    try:
                                        last_accessed = datetime.fromisoformat(wr.last_accessed_at.replace('Z', '+00:00'))
                                        days_since_access = (datetime.now(timezone.utc) - last_accessed).days
                                    except Exception:
                                        days_since_access = None

                                # Record access pattern with node attributes
                                decay_metrics.record_access_pattern(
                                    importance=wr.importance,
                                    lifecycle_state=wr.lifecycle_state,
                                    days_since_last_access=days_since_access
                                )
                            except Exception as attr_err:
                                logger.debug(f'Failed to record access pattern for {wr.uuid}: {attr_err}')

                        # Also record generic access count for compatibility
                        decay_metrics.record_memory_access(len(weighted_results))
                except Exception as metrics_err:
                    logger.debug(f'Failed to record search metrics: {metrics_err}')

            return NodeSearchResponse(
                message=f'Nodes retrieved with weighted scoring ({len(node_results)} results)',
                nodes=node_results
            )

        # Apply limit after filtering (standard path without weighted scoring)
        nodes = nodes[:max_nodes]

        # Format the results
        node_results = []
        for node in nodes:
            attrs = node.attributes if hasattr(node, 'attributes') else {}
            attrs = {k: v for k, v in attrs.items() if 'embedding' not in k.lower()}

            node_results.append(
                NodeResult(
                    uuid=node.uuid,
                    name=node.name,
                    labels=node.labels if node.labels else [],
                    created_at=node.created_at.isoformat() if node.created_at else None,
                    summary=node.summary,
                    group_id=node.group_id,
                    attributes=attrs,
                )
            )

        # Feature 009: Record search metrics
        if _decay_metrics_available:
            try:
                decay_metrics = get_decay_metrics_exporter()
                if decay_metrics:
                    search_latency = time.time() - search_start
                    is_zero_result = len(node_results) == 0
                    decay_metrics.record_search_execution(
                        query_latency_seconds=search_latency,
                        result_count=len(node_results),
                        is_zero_result=is_zero_result
                    )
                    # Record memory access patterns for retrieved nodes
                    for node in nodes:
                        try:
                            # Extract decay attributes from node
                            # Note: node.attributes from Graphiti search returns Neo4j properties
                            # with dot notation keys (e.g., 'attributes.importance', not 'importance')
                            attrs = node.attributes if hasattr(node, "attributes") else {}
                            importance = attrs.get("attributes.importance", 3)
                            lifecycle_state = attrs.get("attributes.lifecycle_state", "ACTIVE")
                            last_accessed_str = attrs.get("attributes.last_accessed_at")

                            # Calculate days since last access
                            days_since_access = None
                            if last_accessed_str:
                                try:
                                    if isinstance(last_accessed_str, str):
                                        last_accessed = datetime.fromisoformat(last_accessed_str.replace('Z', '+00:00'))
                                    else:
                                        last_accessed = last_accessed_str
                                    days_since_access = (datetime.now(timezone.utc) - last_accessed).days
                                except Exception:
                                    days_since_access = None

                            # Record access pattern with node attributes
                            decay_metrics.record_access_pattern(
                                importance=importance,
                                lifecycle_state=lifecycle_state,
                                days_since_last_access=days_since_access
                            )
                        except Exception as attr_err:
                            logger.warning(f'Failed to record access pattern for {getattr(node, "uuid", "unknown")}: {attr_err}')

                    # Also record generic access count for compatibility
                    decay_metrics.record_memory_access(len(nodes))
            except Exception as metrics_err:
                logger.debug(f'Failed to record search metrics: {metrics_err}')

        return NodeSearchResponse(message='Nodes retrieved successfully', nodes=node_results)
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error searching nodes: {error_msg}')
        return ErrorResponse(error=f'Error searching nodes: {error_msg}')


@mcp.tool()
async def search_memory_facts(
    query: str,
    group_ids: list[str] | None = None,
    max_facts: int = 10,
    center_node_uuid: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    relationship_types: list[str] | None = None,
) -> FactSearchResponse | ErrorResponse:
    """Search the graph memory for relevant facts with optional temporal and relationship type filtering.

    Feature 018 T044: Added relationship_types filter for custom ontology relationship types.

    Args:
        query: The search query
        group_ids: Optional list of group IDs to filter results
        max_facts: Maximum number of facts to return (default: 10)
        center_node_uuid: Optional UUID of a node to center the search around
        created_after: Return facts created after this date (ISO 8601 or relative: "today", "7d", "1 week ago")
        created_before: Return facts created before this date (ISO 8601 or relative)
        relationship_types: Optional list of relationship type names to filter by (e.g., ["uses", "targets"])
    """
    global graphiti_service

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    # Feature 009: Track search metrics
    import time
    search_start = time.time()

    try:
        if max_facts <= 0:
            return ErrorResponse(error='max_facts must be a positive integer')

        client = await graphiti_service.get_client()

        # Madeinoz Patch: Use dynamic group_id discovery
        effective_group_ids = await get_effective_group_ids(
            client, group_ids, config.graphiti.group_id
        )

        # Madeinoz Patch: Parse temporal filters
        after_date = parse_date_input(created_after)
        before_date = parse_date_input(created_before)
        has_temporal_filter = after_date is not None or before_date is not None

        # Feature 018 T044: Parse relationship types filter
        has_relationship_filter = relationship_types is not None and len(relationship_types) > 0
        if has_relationship_filter:
            relationship_types_set = set(relationship_types)
            logger.debug(f'Feature 018: Filtering by relationship types: {relationship_types}')

        # If temporal or relationship filtering is needed, fetch more results to filter
        fetch_limit = max_facts * 3 if (has_temporal_filter or has_relationship_filter) else max_facts

        relevant_edges = await client.search(
            group_ids=effective_group_ids,
            query=query,
            num_results=fetch_limit,
            center_node_uuid=center_node_uuid,
        )

        if not relevant_edges:
            # Feature 009: Record zero-result search metrics
            if _decay_metrics_available:
                try:
                    decay_metrics = get_decay_metrics_exporter()
                    if decay_metrics:
                        search_latency = time.time() - search_start
                        decay_metrics.record_search_execution(
                            query_latency_seconds=search_latency,
                            result_count=0,
                            is_zero_result=True
                        )
                except Exception as metrics_err:
                    logger.debug(f'Failed to record search metrics: {metrics_err}')
            return FactSearchResponse(message='No relevant facts found', facts=[])

        # Madeinoz Patch: Apply temporal filtering if specified
        if has_temporal_filter:
            filtered_edges = []
            for edge in relevant_edges:
                if edge.created_at is None:
                    continue  # Skip edges without creation date
                edge_date = edge.created_at
                # Make sure edge_date is timezone-aware for comparison
                if edge_date.tzinfo is None:
                    edge_date = edge_date.replace(tzinfo=timezone.utc)
                # Apply after filter
                if after_date and edge_date < after_date:
                    continue
                # Apply before filter
                if before_date and edge_date > before_date:
                    continue
                filtered_edges.append(edge)
            relevant_edges = filtered_edges
            logger.debug(f'Madeinoz Patch: Temporal filter applied, {len(relevant_edges)} facts remaining')

        # Feature 018 T044: Apply relationship type filtering if specified
        if has_relationship_filter:
            filtered_edges = []
            for edge in relevant_edges:
                # Get relationship type from edge
                # Edge type is stored as the edge label or in attributes
                edge_type = None
                if hasattr(edge, 'label') and edge.label:
                    edge_type = edge.label
                elif hasattr(edge, 'relationship_type') and edge.relationship_type:
                    edge_type = edge.relationship_type
                elif hasattr(edge, 'attributes') and edge.attributes:
                    edge_type = edge.attributes.get('relationship_type') or edge.attributes.get('fact_type')

                # Check if edge type matches any of the requested types
                if edge_type and edge_type in relationship_types_set:
                    filtered_edges.append(edge)

            relevant_edges = filtered_edges
            logger.debug(f'Feature 018: Relationship type filter applied, {len(relevant_edges)} facts remaining')

        # Apply max_facts limit after all filtering
        relevant_edges = relevant_edges[:max_facts]

        if not relevant_edges:
            # Feature 009: Record zero-result search metrics
            if _decay_metrics_available:
                try:
                    decay_metrics = get_decay_metrics_exporter()
                    if decay_metrics:
                        search_latency = time.time() - search_start
                        decay_metrics.record_search_execution(
                            query_latency_seconds=search_latency,
                            result_count=0,
                            is_zero_result=True
                        )
                except Exception as metrics_err:
                    logger.debug(f'Failed to record search metrics: {metrics_err}')
            return FactSearchResponse(message='No relevant facts found', facts=[])

        facts = [format_fact_result(edge) for edge in relevant_edges]

        # Feature 009: Record search metrics
        if _decay_metrics_available:
            try:
                decay_metrics = get_decay_metrics_exporter()
                if decay_metrics:
                    search_latency = time.time() - search_start
                    is_zero_result = len(facts) == 0
                    decay_metrics.record_search_execution(
                        query_latency_seconds=search_latency,
                        result_count=len(facts),
                        is_zero_result=is_zero_result
                    )
                    # Record memory access for retrieved facts
                    for _ in facts:
                        decay_metrics.record_memory_access()
            except Exception as metrics_err:
                logger.debug(f'Failed to record search metrics: {metrics_err}')

        return FactSearchResponse(message='Facts retrieved successfully', facts=facts)
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error searching facts: {error_msg}')
        return ErrorResponse(error=f'Error searching facts: {error_msg}')


@mcp.tool()
async def delete_entity_edge(uuid: str) -> SuccessResponse | ErrorResponse:
    """Delete an entity edge from the graph memory.

    Args:
        uuid: UUID of the entity edge to delete
    """
    global graphiti_service

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    try:
        client = await graphiti_service.get_client()
        entity_edge = await EntityEdge.get_by_uuid(client.driver, uuid)
        await entity_edge.delete(client.driver)
        return SuccessResponse(message=f'Entity edge with UUID {uuid} deleted successfully')
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error deleting entity edge: {error_msg}')
        return ErrorResponse(error=f'Error deleting entity edge: {error_msg}')


@mcp.tool()
async def delete_episode(uuid: str) -> SuccessResponse | ErrorResponse:
    """Delete an episode from the graph memory.

    Args:
        uuid: UUID of the episode to delete
    """
    global graphiti_service

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    try:
        client = await graphiti_service.get_client()
        episodic_node = await EpisodicNode.get_by_uuid(client.driver, uuid)
        await episodic_node.delete(client.driver)
        return SuccessResponse(message=f'Episode with UUID {uuid} deleted successfully')
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error deleting episode: {error_msg}')
        return ErrorResponse(error=f'Error deleting episode: {error_msg}')


@mcp.tool()
async def get_entity_edge(uuid: str) -> dict[str, Any] | ErrorResponse:
    """Get an entity edge from the graph memory by its UUID.

    Args:
        uuid: UUID of the entity edge to retrieve
    """
    global graphiti_service

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    try:
        client = await graphiti_service.get_client()
        entity_edge = await EntityEdge.get_by_uuid(client.driver, uuid)
        return format_fact_result(entity_edge)
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error getting entity edge: {error_msg}')
        return ErrorResponse(error=f'Error getting entity edge: {error_msg}')


@mcp.tool()
async def get_episodes(
    group_ids: list[str] | None = None,
    max_episodes: int = 10,
) -> EpisodeSearchResponse | ErrorResponse:
    """Get episodes from the graph memory.

    Args:
        group_ids: Optional list of group IDs to filter results
        max_episodes: Maximum number of episodes to return (default: 10)
    """
    global graphiti_service

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    try:
        client = await graphiti_service.get_client()

        # Madeinoz Patch: Use dynamic group_id discovery
        effective_group_ids = await get_effective_group_ids(
            client, group_ids, config.graphiti.group_id
        )

        from graphiti_core.nodes import EpisodicNode

        if effective_group_ids:
            episodes = await EpisodicNode.get_by_group_ids(
                client.driver, effective_group_ids, limit=max_episodes
            )
        else:
            episodes = []

        if not episodes:
            return EpisodeSearchResponse(message='No episodes found', episodes=[])

        # Format the results
        episode_results = []
        for episode in episodes:
            episode_dict = {
                'uuid': episode.uuid,
                'name': episode.name,
                'content': episode.content,
                'created_at': episode.created_at.isoformat() if episode.created_at else None,
                'source': episode.source.value
                if hasattr(episode.source, 'value')
                else str(episode.source),
                'source_description': episode.source_description,
                'group_id': episode.group_id,
            }
            episode_results.append(episode_dict)

        return EpisodeSearchResponse(
            message='Episodes retrieved successfully', episodes=episode_results
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error getting episodes: {error_msg}')
        return ErrorResponse(error=f'Error getting episodes: {error_msg}')


@mcp.tool()
async def clear_graph(group_ids: list[str] | None = None) -> SuccessResponse | ErrorResponse:
    """Clear all data from the graph for specified group IDs.

    Args:
        group_ids: Optional list of group IDs to clear. If not provided, clears the default group.
    """
    global graphiti_service

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    try:
        client = await graphiti_service.get_client()

        # NOTE: For clear_graph, we intentionally do NOT use dynamic group discovery
        # to prevent accidental deletion of all data. User must explicitly specify groups.
        effective_group_ids = (
            group_ids or [config.graphiti.group_id] if config.graphiti.group_id else []
        )

        if not effective_group_ids:
            return ErrorResponse(error='No group IDs specified for clearing')

        await clear_data(client.driver, group_ids=effective_group_ids)

        return SuccessResponse(
            message=f'Graph data cleared successfully for group IDs: {", ".join(effective_group_ids)}'
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error clearing graph: {error_msg}')
        return ErrorResponse(error=f'Error clearing graph: {error_msg}')


@mcp.tool()
async def get_status() -> StatusResponse:
    """Get the status of the Graphiti MCP server and database connection."""
    global graphiti_service

    if graphiti_service is None:
        return StatusResponse(status='error', message='Graphiti service not initialized')

    try:
        client = await graphiti_service.get_client()

        async with client.driver.session() as session:
            result = await session.run('MATCH (n) RETURN count(n) as count')
            if result:
                _ = [record async for record in result]

        provider_name = graphiti_service.config.database.provider
        return StatusResponse(
            status='ok',
            message=f'Graphiti MCP server is running and connected to {provider_name} database',
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error checking database connection: {error_msg}')
        return StatusResponse(
            status='error',
            message=f'Graphiti MCP server is running but database connection failed: {error_msg}',
        )


@mcp.tool()
async def investigate_entity(
    entity_name: str,
    max_depth: int = 1,
    relationship_types: list[str] | None = None,
    group_ids: list[str] | None = None,
    include_attributes: bool = True,
) -> dict | ErrorResponse:
    """Investigate an entity and return all its connected relationships.

    Feature 020: Performs graph traversal starting from a matched entity to find
    all connected entities up to the specified depth. Returns entities with their
    names, types, and UUIDs in a single query for AI consumption.

    Key features:
    - Configurable depth (1-3 hops) for comprehensive analysis
    - Relationship type filtering to reduce noise
    - Cycle detection and reporting
    - AI-friendly JSON response with full entity context

    Args:
        entity_name: The name or identifier of the entity to investigate (e.g., "+1-555-0199", "APT28")
        max_depth: Maximum number of hops to traverse (1-3, default: 1)
        relationship_types: Optional filter for specific relationship types (e.g., ["OWNED_BY", "USES"])
        group_ids: Optional list of group IDs to search (default: all groups)
        include_attributes: Include full entity attributes in response (default: True)

    Returns:
        InvestigateResult with entity, connections, metadata, and optional warning

    Example:
        investigate_entity(entity_name="+1-555-0199", max_depth=2)
        Returns the phone entity with all connected entities (Person, Account, etc.)
        up to 2 hops away, including names, types, and relationship information.
    """
    global graphiti_service

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    try:
        client = await graphiti_service.get_client()

        # Validate max_depth parameter
        if max_depth < 1 or max_depth > 3:
            return ErrorResponse(
                error=f'Invalid depth: {max_depth}. Must be between 1 and 3.'
            )

        # Madeinoz Patch: Use dynamic group_id discovery
        effective_group_ids = await get_effective_group_ids(
            client, group_ids, config.graphiti.group_id
        )

        # First, search for the entity by name
        from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

        search_results = await client.search_(
            query=entity_name,
            config=NODE_HYBRID_SEARCH_RRF,
            group_ids=effective_group_ids,
        )

        # Extract the best matching entity
        nodes = search_results.nodes if search_results.nodes else []

        if not nodes:
            return ErrorResponse(
                error=f'Entity not found: {entity_name}',
                details={
                    'query': entity_name,
                    'suggestion': 'Use search_nodes to find the exact entity name first.'
                }
            )

        # Use the best match (first result has highest score)
        start_entity = nodes[0]
        start_uuid = start_entity.uuid

        # Import graph traversal module
        from utils.graph_traversal import GraphTraversal
        from models import Entity, Connection, InvestigationMetadata

        # Perform graph traversal
        traversal = GraphTraversal(
            driver=client.driver,
            database_type=config.database.provider,
            logger=logger
        )

        traversal_result = await traversal.traverse(
            start_entity_uuid=start_uuid,
            max_depth=max_depth,
            relationship_types=relationship_types,
            group_ids=effective_group_ids
        )

        # Build InvestigateResult response
        # Convert the primary entity
        entity = Entity(
            uuid=start_entity.uuid,
            name=start_entity.name,
            labels=list(start_entity.labels) if hasattr(start_entity, 'labels') else [],
            summary=start_entity.summary if hasattr(start_entity, 'summary') else None,
            created_at=start_entity.created_at.isoformat() if hasattr(start_entity, 'created_at') and start_entity.created_at else None,
            group_id=start_entity.group_id if hasattr(start_entity, 'group_id') else None,
            attributes=None  # Could extract from start_entity.attributes if needed
        )

        # Convert connections
        connections = []
        for conn in traversal_result.connections:
            target_data = conn.get('target_entity', {})
            target_entity = Entity(
                uuid=target_data.get('uuid', ''),
                name=target_data.get('name', ''),
                labels=target_data.get('labels', []),
                summary=target_data.get('summary'),
                created_at=target_data.get('created_at'),
                group_id=target_data.get('group_id'),
                attributes=None
            )

            connection = Connection(
                relationship=conn.get('relationship', 'RELATED_TO'),
                direction=conn.get('direction', 'bidirectional'),
                target_entity=target_entity,
                hop_distance=conn.get('hop_distance', 1),
                confidence=conn.get('confidence'),
                fact=conn.get('fact')
            )
            connections.append(connection)

        # Build metadata
        metadata = InvestigationMetadata(
            depth_explored=traversal_result.depth_explored,
            total_connections_explored=traversal_result.total_connections_explored,
            connections_returned=traversal_result.connections_returned,
            cycles_detected=traversal_result.cycles_detected,
            cycles_pruned=traversal_result.cycles_pruned,
            entities_skipped=traversal_result.entities_skipped,
            relationship_types_filtered=relationship_types,
            query_duration_ms=traversal_result.query_duration_ms,
            max_connections_exceeded=traversal_result.max_connections_exceeded
        )

        # Build final result
        result = {
            'entity': entity.model_dump(exclude_none=True),
            'connections': [conn.model_dump(exclude_none=True) for conn in connections],
            'metadata': metadata.model_dump(exclude_none=True),
        }

        # Add warning if present
        if traversal_result.warning:
            result['warning'] = traversal_result.warning

        logger.info(
            f'🔍 investigate_entity: entity={entity_name}, '
            f'depth={max_depth}, connections={len(connections)}, '
            f'cycles={traversal_result.cycles_detected}'
        )

        return result

    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error investigating entity: {error_msg}')
        return ErrorResponse(error=f'Error investigating entity: {error_msg}')


@mcp.tool()
async def list_ontology_types(
    include_builtin: bool = False
) -> dict:
    """List all available ontology types (entity and relationship types).

    Feature 018: Returns custom ontology types loaded from YAML configuration.
    This allows querying the configured entity types (e.g., ThreatActor, Malware)
    and relationship types (e.g., uses, targets, exploits) that can be used for
    classification and filtering.

    Args:
        include_builtin: Include Graphiti built-in types (Person, Organization, etc.)

    Returns:
        Dictionary with:
        - entity_types: List of entity type definitions with name, description, attributes, decay_config
        - relationship_types: List of relationship type definitions with name, description, source/target entity types
    """
    global graphiti_service

    if graphiti_service is None:
        return {
            "entity_types": [],
            "relationship_types": [],
            "error": "Graphiti service not initialized"
        }

    try:
        return graphiti_service.get_ontology_types(include_builtin=include_builtin)
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error listing ontology types: {error_msg}')
        return {
            "entity_types": [],
            "relationship_types": [],
            "error": f'Error listing ontology types: {error_msg}'
        }


@mcp.custom_route('/health', methods=['GET'])
async def health_check(request) -> JSONResponse:
    """
    Health check endpoint for Docker and load balancers.

    SECURITY: Minimal information disclosure.
    Only returns status - no internal configuration details exposed.
    """
    return JSONResponse({'status': 'healthy'})


@mcp.custom_route('/health/decay', methods=['GET'])
async def health_decay_check(request) -> JSONResponse:
    """
    Decay system health check endpoint.

    Returns decay system status including last maintenance run time,
    next scheduled run, and metrics endpoint location.

    Per contracts/decay-api.yaml DecayHealthCheck schema.
    """
    import time

    global graphiti_service, _server_start_time

    # Default response for degraded state
    response = {
        'status': 'degraded',
        'last_maintenance': None,
        'next_scheduled': None,
        'metrics_endpoint': f"http://localhost:{os.getenv('METRICS_PORT', '9090')}/metrics",
        'uptime_seconds': time.time() - getattr(health_decay_check, '_start_time', time.time()),
    }

    if not _decay_modules_available:
        response['status'] = 'unhealthy'
        return JSONResponse(response)

    if graphiti_service is None:
        response['status'] = 'unhealthy'
        return JSONResponse(response)

    try:
        client = await graphiti_service.get_client()
        maintenance = get_maintenance_service(client.driver, llm_client=graphiti_service.llm_client)

        # Get last maintenance result if available
        if maintenance._last_result:
            response['last_maintenance'] = {
                'completed_at': maintenance._last_result.completed_at,
                'duration_seconds': round(maintenance._last_result.duration_seconds, 2),
                'success': maintenance._last_result.success,
            }
            response['status'] = 'healthy'
        else:
            # No maintenance run yet - still healthy, just no history
            response['status'] = 'healthy'

        return JSONResponse(response)

    except Exception as e:
        logger.error(f"Health decay check failed: {e}")
        response['status'] = 'unhealthy'
        return JSONResponse(response)


# Store server start time for uptime calculation
health_decay_check._start_time = time.time()


# ==============================================================================
# Feature 009: Memory Decay Scoring - MCP Tools
# ==============================================================================

@mcp.tool()
async def run_decay_maintenance(
    dry_run: bool = False,
) -> dict[str, Any] | ErrorResponse:
    """Run maintenance to recalculate decay scores and transition lifecycle states.

    This performs batch operations:
    1. Recalculates decay scores for all eligible memories
    2. Transitions lifecycle states based on thresholds (ACTIVE→DORMANT→ARCHIVED→EXPIRED→SOFT_DELETED)
    3. Purges soft-deleted memories past the 90-day retention window

    Args:
        dry_run: If True, calculate but don't apply changes (default: False)

    Returns:
        MaintenanceResult with operation counts and duration
    """
    global graphiti_service

    if not _decay_modules_available:
        return ErrorResponse(error='Decay modules not available')

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    try:
        client = await graphiti_service.get_client()
        maintenance = get_maintenance_service(client.driver, llm_client=graphiti_service.llm_client)
        result = await maintenance.run_maintenance(dry_run=dry_run)
        return result.to_dict()
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error running decay maintenance: {error_msg}')
        return ErrorResponse(error=f'Error running decay maintenance: {error_msg}')


@mcp.tool()
async def get_knowledge_health(
    group_id: str | None = None,
) -> dict[str, Any] | ErrorResponse:
    """Get health metrics for the knowledge graph.

    Returns aggregated statistics about memory lifecycle states,
    decay scores, importance/stability distributions, and age distribution.

    Args:
        group_id: Optional group ID to filter metrics (not yet implemented)

    Returns:
        HealthMetrics with state counts, aggregates, age distribution, and last maintenance info
    """
    global graphiti_service

    if not _decay_modules_available:
        return ErrorResponse(error='Decay modules not available')

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    try:
        client = await graphiti_service.get_client()
        maintenance = get_maintenance_service(client.driver, llm_client=graphiti_service.llm_client)
        metrics = await maintenance.get_health_metrics(group_id=group_id)
        return metrics.to_dict()
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error getting knowledge health: {error_msg}')
        return ErrorResponse(error=f'Error getting knowledge health: {error_msg}')


@mcp.tool()
async def recover_soft_deleted(
    uuid: str,
) -> dict[str, Any] | ErrorResponse:
    """Recover a soft-deleted memory within the 90-day retention window.

    Soft-deleted memories can be recovered if they haven't been permanently
    purged yet. Recovery transitions the memory back to ARCHIVED state.

    Args:
        uuid: UUID of the soft-deleted memory to recover

    Returns:
        Dictionary with recovered memory info (uuid, name, new_state) or error
    """
    global graphiti_service

    if not _decay_modules_available:
        return ErrorResponse(error='Decay modules not available')

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    try:
        client = await graphiti_service.get_client()
        result = await recover_soft_deleted_impl(client.driver, uuid)

        if result is None:
            return ErrorResponse(
                error=f'Memory {uuid} not found, not soft-deleted, or past retention window'
            )

        return {
            'message': f"Memory '{result['name']}' recovered successfully",
            'uuid': result['uuid'],
            'name': result['name'],
            'new_state': result['new_state'],
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error recovering soft-deleted memory: {error_msg}')
        return ErrorResponse(error=f'Error recovering memory: {error_msg}')


@mcp.tool()
async def classify_memory(
    content: str,
    source_description: str | None = None,
) -> dict[str, Any] | ErrorResponse:
    """Classify memory content for importance and stability scores.

    Uses LLM to analyze content and assign:
    - Importance (1-5): How critical is this information?
    - Stability (1-5): How likely is this to change over time?

    Memories with importance >= 4 AND stability >= 4 are marked as PERMANENT
    and exempt from decay.

    Args:
        content: The memory content to classify
        source_description: Optional source context for better classification

    Returns:
        Classification result with importance, stability, is_permanent, and source
    """
    global graphiti_service

    if not _decay_modules_available:
        return ErrorResponse(error='Decay modules not available')

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

    try:
        # Get LLM client from graphiti service (not from Graphiti client)
        llm_client = graphiti_service.llm_client

        importance, stability = await classify_memory_impl(
            content=content,
            llm_client=llm_client,
            source_description=source_description,
        )

        return {
            'importance': importance,
            'stability': stability,
            'is_permanent': is_permanent(importance, stability),
            'classification_source': 'llm' if llm_client else 'default',
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error classifying memory: {error_msg}')
        return ErrorResponse(error=f'Error classifying memory: {error_msg}')


# ==============================================================================
# Feature 018: STIX 2.1 Importer MCP Tools (User Story 3)
# ==============================================================================

if _stix_importer_available:

    @mcp.tool()
    async def import_stix_bundle(
        bundle_path: str,
        batch_size: int = 1000,
        continue_on_error: bool = True,
        group_ids: list[str] | None = None,
    ) -> dict[str, Any] | ErrorResponse:
        """Import STIX 2.1 JSON bundle into the knowledge graph.

        Args:
            bundle_path: Path or URL to STIX 2.1 JSON file
            batch_size: Number of objects per batch (default: 1000)
            continue_on_error: Continue importing on individual object failures (default: True)
            group_ids: Knowledge graph group IDs (default: from config or 'main')

        Returns:
            Import result with:
            - import_id: Unique import session identifier
            - status: Import status (IN_PROGRESS, COMPLETED, PARTIAL, FAILED)
            - total_objects: Total objects in bundle
            - imported_count: Successfully imported objects
            - failed_count: Failed objects
            - failed_objects: List of failed object details (stix_id, stix_type, error)
            - duration_seconds: Processing duration
        """
        global graphiti_service

        try:
            # Get effective group IDs
            client = await get_graphiti_client()
            effective_group_ids = await get_effective_group_ids(client, group_ids)
            group_id = effective_group_ids[0] if effective_group_ids else 'main'

            # Load STIX bundle (from file or URL)
            if bundle_path.startswith(('http://', 'https://')):
                bundle_data = await load_stix_from_url(bundle_path)
            else:
                bundle_data = load_and_parse_stix_file(bundle_path)

            # Process the bundle
            result = await process_stix_bundle(
                stix_bundle=bundle_data,
                graphiti_client=client,
                batch_size=batch_size,
                continue_on_error=continue_on_error,
                group_id=group_id
            )

            # Add source file info to result
            result['source_file'] = bundle_path

            return result

        except InvalidSTIXError as e:
            error_msg = f'Invalid STIX data: {e}'
            logger.error(f'STIX import error: {error_msg}')
            return ErrorResponse(error=error_msg)
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Error importing STIX bundle: {error_msg}')
            return ErrorResponse(error=f'Error importing STIX bundle: {error_msg}')


    @mcp.tool()
    async def get_import_status(
        import_id: str,
    ) -> dict[str, Any] | ErrorResponse:
        """Retrieve status of a previous STIX import.

        Args:
            import_id: Import session ID from import_stix_bundle

        Returns:
            Import status with:
            - import_id: Import session identifier
            - source_file: Original STIX bundle file path or URL
            - started_at: ISO 8601 datetime when import started
            - completed_at: ISO 8601 datetime when import completed (nullable)
            - status: Import status (IN_PROGRESS, COMPLETED, PARTIAL, FAILED)
            - total_objects: Total objects in bundle
            - imported_count: Successfully imported objects
            - failed_count: Failed objects
            - failed_object_ids: List of STIX IDs of failed objects
            - error_messages: List of error messages for failed objects
        """
        try:
            client = await get_graphiti_client()
            status = await get_import_session_status(import_id, client)

            if status is None:
                return ErrorResponse(error=f'Import session not found: {import_id}')

            return status

        except Exception as e:
            error_msg = str(e)
            logger.error(f'Error getting import status: {error_msg}')
            return ErrorResponse(error=f'Error getting import status: {error_msg}')


    @mcp.tool()
    async def resume_import(
        import_id: str,
        retry_failed_only: bool = True,
        group_ids: list[str] | None = None,
    ) -> dict[str, Any] | ErrorResponse:
        """Resume a partially failed STIX import.

        Retries failed objects from a previous import that ended with PARTIAL or FAILED status.

        Args:
            import_id: Import session ID to resume
            retry_failed_only: Only retry previously failed objects (default: True)
            group_ids: Knowledge graph group IDs (default: from config or 'main')

        Returns:
            Resume result with:
            - import_id: Import session identifier
            - status: Final import status (COMPLETED, PARTIAL, FAILED)
            - retried_count: Number of objects retried
            - imported_count: Successfully imported on retry
            - failed_count: Still failing after retry
        """
        try:
            client = await get_graphiti_client()
            status = await get_import_session_status(import_id, client)

            if status is None:
                return ErrorResponse(error=f'Import session not found: {import_id}')

            if status['status'] not in ['PARTIAL', 'FAILED']:
                return ErrorResponse(error=f'Cannot resume import with status: {status["status"]}')

            # Get the original bundle path
            bundle_path = status.get('source_file', '')
            if not bundle_path:
                return ErrorResponse(error='Cannot resume: original bundle path not stored')

            # Load the original bundle
            if bundle_path.startswith(('http://', 'https://')):
                bundle_data = await load_stix_from_url(bundle_path)
            else:
                bundle_data = load_and_parse_stix_file(bundle_path)

            # Get effective group IDs
            effective_group_ids = await get_effective_group_ids(client, group_ids)
            group_id = effective_group_ids[0] if effective_group_ids else 'main'

            # Resume the import
            result = await resume_import(
                import_id=import_id,
                stix_bundle=bundle_data,
                graphiti_client=client,
                retry_failed_only=retry_failed_only,
                batch_size=1000,
                group_id=group_id
            )

            return result

        except InvalidSTIXError as e:
            error_msg = f'Invalid STIX data: {e}'
            logger.error(f'STIX resume error: {error_msg}')
            return ErrorResponse(error=error_msg)
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Error resuming import: {error_msg}')
            return ErrorResponse(error=f'Error resuming import: {error_msg}')


# ==============================================================================



async def initialize_server() -> ServerConfig:
    """Parse CLI arguments and initialize the Graphiti server configuration."""
    global config, graphiti_service, queue_service, graphiti_client, semaphore

    parser = argparse.ArgumentParser(
        description='Run the Graphiti MCP server with YAML configuration support'
    )

    default_config = Path(__file__).parent.parent / 'config' / 'config.yaml'
    parser.add_argument(
        '--config',
        type=Path,
        default=default_config,
        help='Path to YAML configuration file (default: config/config.yaml)',
    )

    # SECURITY: Add option to skip config path validation (for development only)
    parser.add_argument(
        '--skip-config-validation',
        action='store_true',
        help=argparse.SUPPRESS,  # Hidden option - only for development/debugging
    )

    parser.add_argument(
        '--transport',
        choices=['sse', 'stdio', 'http'],
        help='Transport to use: http (recommended, default), stdio (standard I/O), or sse (deprecated)',
    )
    parser.add_argument('--host', help='Host to bind the MCP server to')
    parser.add_argument('--port', type=int, help='Port to bind the MCP server to')
    parser.add_argument(
        '--llm-provider',
        choices=['openai', 'azure_openai', 'anthropic', 'gemini', 'groq'],
        help='LLM provider to use',
    )
    parser.add_argument(
        '--embedder-provider',
        choices=['openai', 'azure_openai', 'gemini', 'voyage'],
        help='Embedder provider to use',
    )
    parser.add_argument(
        '--database-provider',
        choices=['neo4j', 'falkordb'],
        help='Database provider to use',
    )
    parser.add_argument('--model', help='Model name to use with the LLM client')
    parser.add_argument('--small-model', help='Small model name to use with the LLM client')
    parser.add_argument(
        '--temperature', type=float, help='Temperature setting for the LLM (0.0-2.0)'
    )
    parser.add_argument('--embedder-model', help='Model name to use with the embedder')
    parser.add_argument('--group-id', help='Namespace for the graph.')
    parser.add_argument('--user-id', help='User ID for tracking operations')
    parser.add_argument(
        '--destroy-graph',
        action='store_true',
        help='Destroy all Graphiti graphs on startup',
    )

    args = parser.parse_args()

    # SECURITY: Validate config path to prevent directory traversal
    if not getattr(args, 'skip_config_validation', False):
        try:
            validated_config_path = validate_config_path(args.config)
            os.environ['CONFIG_PATH'] = str(validated_config_path)
            logger.debug(f'Validated config path: {validated_config_path}')
        except ConfigPathError as e:
            logger.error(f'Configuration path validation failed: {e}')
            logger.error('Use --skip-config-validation only for development (not recommended for production)')
            raise
    else:
        logger.warning('Config path validation SKIPPED - security risk!')
        os.environ['CONFIG_PATH'] = str(args.config)

    config = GraphitiConfig()
    config.apply_cli_overrides(args)

    if hasattr(args, 'destroy_graph'):
        config.destroy_graph = args.destroy_graph

    logger.info('Using configuration:')
    logger.info(f'  - LLM: {config.llm.provider} / {config.llm.model}')
    logger.info(f'  - Embedder: {config.embedder.provider} / {config.embedder.model}')
    logger.info(f'  - Database: {config.database.provider}')
    logger.info(f'  - Group ID: {config.graphiti.group_id}')
    logger.info(f'  - Transport: {config.server.transport}')
    logger.info('  - Madeinoz Patch: Search ALL groups when none specified (enabled)')
    if _metrics_exporter_available:
        logger.info('  - Madeinoz Patch: Feature 006 - Gemini prompt caching (enabled)')

    # SECURITY: Warn about API keys in environment variables
    logger.warning('=' * 60)
    logger.warning('SECURITY NOTICE: API keys are loaded from environment variables')
    logger.warning('For production deployments, use secrets management solutions:')
    logger.warning('  - Docker secrets: https://docs.docker.com/engine/swarm/secrets/')
    logger.warning('  - HashiCorp Vault: https://www.vaultproject.io/')
    logger.warning('  - AWS Secrets Manager: https://aws.amazon.com/secrets-manager/')
    logger.warning('Never commit API keys to version control.')
    logger.warning('=' * 60)

    try:
        import graphiti_core

        graphiti_version = getattr(graphiti_core, '__version__', 'unknown')
        logger.info(f'  - Graphiti Core: {graphiti_version}')
    except Exception:
        version_file = Path('/app/.graphiti-core-version')
        if version_file.exists():
            graphiti_version = version_file.read_text().strip()
            logger.info(f'  - Graphiti Core: {graphiti_version}')
        else:
            logger.info('  - Graphiti Core: version unavailable')

    if hasattr(config, 'destroy_graph') and config.destroy_graph:
        logger.warning('Destroying all Graphiti graphs as requested...')
        temp_service = GraphitiService(config, SEMAPHORE_LIMIT)
        await temp_service.initialize()
        client = await temp_service.get_client()
        await clear_data(client.driver)
        logger.info('All graphs destroyed')

    graphiti_service = GraphitiService(config, SEMAPHORE_LIMIT)
    queue_service = QueueService()
    await graphiti_service.initialize()

    graphiti_client = await graphiti_service.get_client()
    semaphore = graphiti_service.semaphore

    await queue_service.initialize(graphiti_client)

    if config.server.host:
        mcp.settings.host = config.server.host
    if config.server.port:
        mcp.settings.port = config.server.port

    return config.server


# Feature 017: Background task for periodic consumer metric updates
async def _update_consumer_metrics_periodically():
    """
    Periodically update consumer health metrics every 30 seconds.

    Calculates saturation and lag based on current processing state.
    This is a background task that runs continuously.
    """
    global _queue_metrics_exporter

    while True:
        try:
            await asyncio.sleep(30)  # Update every 30 seconds

            if _queue_metrics_exporter is None:
                continue

            # Calculate consumer health metrics
            # Note: In a real implementation, these would be calculated from
            # actual queue state. For now, we use simple defaults.
            import time
            current_time = time.time()

            # Get queue depth (default queue)
            # Saturation: based on queue depth (depth > 10 indicates high saturation)
            queue_depth = 0  # Would be fetched from QueueService
            saturation = min(1.0, queue_depth / 100.0)  # 100 messages = 100% saturation

            # Lag: time to catch up = depth / processing_rate
            # Default: 0 depth = 0 lag
            lag_seconds = 0.0 if queue_depth == 0 else queue_depth * 0.1  # Assume 10 msgs/sec

            _queue_metrics_exporter.update_consumer_metrics(
                queue_name="default",
                consumer_group="workers",
                active=1,  # Single consumer
                saturation=saturation,
                lag_seconds=lag_seconds
            )

            logger.debug("Updated consumer metrics")
        except asyncio.CancelledError:
            logger.info("Consumer metrics update task cancelled")
            break
        except Exception as e:
            logger.error(f"Error updating consumer metrics: {e}")


async def run_mcp_server():
    """Run the MCP server in the current event loop."""
    global rate_limiter

    mcp_config = await initialize_server()

    # Feature 017: Start background task for periodic consumer metric updates
    if _queue_metrics_exporter:
        asyncio.create_task(_update_consumer_metrics_periodically())

    # Initialize rate limiter for HTTP transport
    if mcp_config.transport == 'http' and RATE_LIMIT_ENABLED:
        rate_limiter = RateLimiter(
            max_requests=RATE_LIMIT_MAX_REQUESTS,
            time_window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )
        logger.info(
            f'Rate limiting enabled: {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds'
        )
    elif not RATE_LIMIT_ENABLED:
        logger.warning('Rate limiting DISABLED - not recommended for production!')

    logger.info(f'Starting MCP server with transport: {mcp_config.transport}')
    if mcp_config.transport == 'stdio':
        await mcp.run_stdio_async()
    elif mcp_config.transport == 'sse':
        logger.info(
            f'Running MCP server with SSE transport on {mcp.settings.host}:{mcp.settings.port}'
        )
        logger.info(f'Access the server at: http://{mcp.settings.host}:{mcp.settings.port}/sse')
        await mcp.run_sse_async()
    elif mcp_config.transport == 'http':
        display_host = 'localhost' if mcp.settings.host == '0.0.0.0' else mcp.settings.host
        logger.info(
            f'Running MCP server with streamable HTTP transport on {mcp.settings.host}:{mcp.settings.port}'
        )
        logger.info('=' * 60)
        logger.info('MCP Server Access Information:')
        logger.info(f'  Base URL: http://{display_host}:{mcp.settings.port}/')
        logger.info(f'  MCP Endpoint: http://{display_host}:{mcp.settings.port}/mcp/')
        logger.info('  Transport: HTTP (streamable)')
        logger.info('  Madeinoz Patch: search-all-groups (active)')
        if RATE_LIMIT_ENABLED:
            logger.info(f'  Rate Limit: {RATE_LIMIT_MAX_REQUESTS} requests/{RATE_LIMIT_WINDOW_SECONDS}s per IP')
        else:
            logger.warning('  Rate Limit: DISABLED (security risk!)')

        if os.environ.get('BROWSER', '1') == '1':
            logger.info(f'  FalkorDB Browser UI: http://{display_host}:3000/')

        logger.info('=' * 60)
        logger.info('For MCP clients, connect to the /mcp/ endpoint above')

        configure_uvicorn_logging()

        # SECURITY: Add rate limiting middleware if enabled
        # Note: FastMCP may not expose .app attribute in all versions
        if rate_limiter is not None:
            try:
                if hasattr(mcp, 'app') and mcp.app is not None:
                    mcp.app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
                    logger.info('Rate limiting middleware added')
                else:
                    logger.warning('Rate limiting not available - FastMCP does not expose app attribute')
            except Exception as e:
                logger.warning(f'Could not add rate limiting middleware: {e}')

        await mcp.run_streamable_http_async()
    else:
        raise ValueError(
            f'Unsupported transport: {mcp_config.transport}. Use "sse", "stdio", or "http"'
        )


async def shutdown_maintenance():
    """Stop scheduled maintenance gracefully on shutdown."""
    global _maintenance_service
    if _maintenance_service is not None:
        try:
            await _maintenance_service.stop_scheduled_maintenance()
        except Exception as e:
            logger.warning(f'Error stopping scheduled maintenance: {e}')


@mcp.tool()
async def validate_ontology(
) -> dict[str, Any] | ErrorResponse:
    """Validate ontology configuration without loading it.

    Performs comprehensive validation including:
    - YAML syntax
    - Schema validation (Pydantic)
    - Circular dependency detection
    - Reserved attribute check
    - Relationship type references
    - Breaking change detection (if config was previously loaded)

    Returns:
        Dictionary with validation results including valid flag, errors, warnings, and breaking_changes
    """
    try:
        from utils.ontology_config import validate_ontology_config
        result = validate_ontology_config()
        return result
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error validating ontology config: {error_msg}')
        return ErrorResponse(error=f'Error validating ontology config: {error_msg}')


@mcp.tool()
async def reload_ontology(
) -> dict[str, Any] | ErrorResponse:
    """Hot-reload ontology configuration without container restart.

    Reloads the ontology configuration from the YAML file and validates it.
    If breaking changes are detected, returns warnings but does not apply the reload.

    Returns:
        Dictionary with reload status including success flag, entity_types loaded,
        relationship_types loaded, and any breaking_changes detected
    """
    try:
        from utils.ontology_config import (
            reload_ontology_config,
            load_ontology_config,
            get_entity_types_dict,
            get_relationship_types_dict,
        )

        # Attempt reload with breaking change detection
        result = reload_ontology_config()

        if not result.get("success", False):
            return {
                "success": False,
                "message": result.get("message", "Reload failed"),
                "breaking_changes": result.get("breaking_changes", []),
            }

        # Get new entity and relationship types
        config = load_ontology_config()
        entity_types = get_entity_types_dict(config)
        relationship_types = get_relationship_types_dict(config)

        return {
            "success": True,
            "message": "Ontology configuration reloaded successfully",
            "entity_types": list(entity_types.keys()),
            "relationship_types": list(relationship_types.keys()),
            "entity_type_count": len(entity_types),
            "relationship_type_count": len(relationship_types),
            "version": config.version,
            "name": config.name,
            "breaking_changes": result.get("breaking_changes", []),
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error reloading ontology config: {error_msg}')
        return ErrorResponse(error=f'Error reloading ontology config: {error_msg}')


# ============================================================================
# Feature 023: Qdrant RAG MCP Tools - T042, T043, T044, T047
# ============================================================================

@mcp.tool()
async def rag_search(
    query: str,
    domain: str | None = None,
    document_type: str | None = None,
    component: str | None = None,
    top_k: int = 10,
) -> dict[str, Any] | ErrorResponse:
    """Search Qdrant vector database for semantically similar document chunks.

    Feature 023 T042: Qdrant semantic search for document memory retrieval.

    Args:
        query: Natural language search query
        domain: Optional domain filter (embedded, security, web, etc.)
        document_type: Optional document type filter (pdf, markdown, text, etc.)
        component: Optional component filter (specific hardware/software component)
        top_k: Maximum number of results (1-100, default: 10)

    Returns:
        Dictionary with search results including chunk_id, text, source,
        page, confidence, and metadata for each result
    """
    if not _qdrant_available:
        return ErrorResponse(error='Qdrant client not available')

    try:
        if top_k <= 0 or top_k > 100:
            return ErrorResponse(error='top_k must be between 1 and 100')

        client = get_qdrant_client()

        # Build filters from parameters
        filters = {}
        if domain:
            filters['domain'] = domain
        if document_type:
            filters['type'] = document_type
        if component:
            filters['component'] = component

        # Perform semantic search
        results = await client.semantic_search(
            query=query,
            top_k=top_k,
            filters=filters if filters else None,
        )

        return {
            'success': True,
            'query': query,
            'result_count': len(results),
            'results': results,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error searching Qdrant: {error_msg}')
        return ErrorResponse(error=f'Error searching Qdrant: {error_msg}')


@mcp.tool()
async def rag_get_chunk(
    chunk_id: str,
) -> dict[str, Any] | ErrorResponse:
    """Get exact document chunk from Qdrant by chunk ID.

    Feature 023 T043: Retrieve precise chunk for verification and evidence review.

    Args:
        chunk_id: Unique chunk identifier (UUID)

    Returns:
        Dictionary with chunk data including text, source, page,
        and full metadata
    """
    if not _qdrant_available:
        return ErrorResponse(error='Qdrant client not available')

    try:
        if not chunk_id:
            return ErrorResponse(error='chunk_id is required')

        client = get_qdrant_client()

        # Get chunk
        chunk = await client.get_chunk(chunk_id)

        if chunk is None:
            return {
                'success': False,
                'error': f'Chunk not found: {chunk_id}',
                'chunk': None,
            }

        return {
            'success': True,
            'chunk': chunk,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error getting chunk from Qdrant: {error_msg}')
        return ErrorResponse(error=f'Error getting chunk from Qdrant: {error_msg}')


@mcp.tool()
async def rag_ingest(
    file_path: str | None = None,
    ingest_all: bool = False,
) -> dict[str, Any] | ErrorResponse:
    """Ingest documents into Qdrant vector database.

    Feature 023 T044: Document ingestion with Docling parser + semantic chunking.

    Args:
        file_path: Path to single document to ingest (relative to knowledge/inbox/)
        ingest_all: If True, ingest all documents in knowledge/inbox/

    Returns:
        Dictionary with ingestion results including doc_id, chunk_count, status
    """
    if not _qdrant_available:
        return ErrorResponse(error='Qdrant client not available')

    try:
        from pathlib import Path as PathlibPath

        client = get_qdrant_client()
        ingester = get_docling_ingester(client)

        if ingest_all:
            # Ingest all documents in inbox
            results = await ingester.ingest_directory()
            return {
                'success': True,
                'documents_processed': len(results),
                'results': [
                    {
                        'doc_id': r.doc_id,
                        'filename': r.filename,
                        'chunk_count': r.chunk_count,
                        'status': r.status.value,
                        'error_message': r.error_message,
                        'processing_time_ms': r.processing_time_ms,
                    }
                    for r in results
                ],
            }
        elif file_path:
            # Ingest single document
            full_path = PathlibPath(file_path)
            if not full_path.is_absolute():
                full_path = PathlibPath(ingester.config.inbox_path) / file_path

            if not full_path.exists():
                return ErrorResponse(error=f'File not found: {full_path}')

            result = await ingester.ingest(full_path)
            return {
                'success': result.status.value == 'completed',
                'doc_id': result.doc_id,
                'filename': result.filename,
                'chunk_count': result.chunk_count,
                'status': result.status.value,
                'error_message': result.error_message,
                'processing_time_ms': result.processing_time_ms,
            }
        else:
            return ErrorResponse(error='Either file_path or ingest_all must be specified')

    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error ingesting document: {error_msg}')
        return ErrorResponse(error=f'Error ingesting document: {error_msg}')


@mcp.tool()
async def rag_health() -> dict[str, Any]:
    """Check Qdrant vector database connectivity and status.

    Feature 023 T047: Health check for Qdrant connectivity.

    Returns:
        Dictionary with connection status, collection info, and vector count
    """
    if not _qdrant_available:
        return {
            'success': False,
            'available': False,
            'error': 'Qdrant client not available',
        }

    try:
        client = get_qdrant_client()
        health = await client.health_check()

        return {
            'success': health['connected'],
            'available': True,
            'connected': health['connected'],
            'collection_exists': health['collection_exists'],
            'vector_count': health['vector_count'],
            'collection_name': client.collection_name,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error checking Qdrant health: {error_msg}')
        return {
            'success': False,
            'available': True,
            'connected': False,
            'error': error_msg,
        }


# ============================================================================
# Feature 024: Multimodal Image Extraction MCP Tools
# ============================================================================

@mcp.tool()
async def rag_searchImages(
    query: str,
    classification: str | None = None,
    top_k: int = 10,
) -> dict[str, Any] | ErrorResponse:
    """Search for images in Qdrant by description similarity.

    Feature 024: Image search with Vision LLM-enriched descriptions.

    Search across extracted images from technical documents using natural
    language queries. Images are classified into types (schematic, pinout,
    waveform, photo, table, graph, flowchart) and enriched with descriptions
    generated by Vision LLM.

    Args:
        query: Natural language search query (e.g., "GPIO pinout diagram", "SPI timing waveform")
        classification: Optional filter by image type:
            - schematic: Circuit diagrams, block diagrams, architecture diagrams
            - pinout: Pin configuration diagrams, connector layouts
            - waveform: Timing diagrams, signal plots, oscilloscope traces
            - photo: Product photos, hardware images
            - table: Tables extracted as images
            - graph: Charts, bar graphs, line graphs
            - flowchart: Process diagrams, state machines
        top_k: Maximum number of results (1-50, default: 10)

    Returns:
        Dictionary with image search results including image_id, description,
        classification, source_page, source document, and base64 image_data
    """
    if not _qdrant_available:
        return ErrorResponse(error='Qdrant client not available')

    try:
        if top_k <= 0 or top_k > 50:
            return ErrorResponse(error='top_k must be between 1 and 50')

        client = get_qdrant_client()

        # Perform image search
        results = await client.search_images(
            query=query,
            classification=classification,
            top_k=top_k,
        )

        return {
            'success': True,
            'query': query,
            'classification_filter': classification,
            'result_count': len(results),
            'results': results,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error searching images in Qdrant: {error_msg}')
        return ErrorResponse(error=f'Error searching images: {error_msg}')


@mcp.tool()
async def rag_getImage(
    image_id: str,
) -> dict[str, Any] | ErrorResponse:
    """Get a specific image by ID with full metadata and base64 data.

    Feature 024: Retrieve individual image with all enrichment data.

    Args:
        image_id: Unique image identifier (UUID)

    Returns:
        Dictionary with image data including base64-encoded image, description,
        classification, source document, and page number
    """
    if not _qdrant_available:
        return ErrorResponse(error='Qdrant client not available')

    try:
        if not image_id:
            return ErrorResponse(error='image_id is required')

        client = get_qdrant_client()

        # Get image
        image = await client.get_image(image_id)

        if image is None:
            return {
                'success': False,
                'error': f'Image not found: {image_id}',
                'image': None,
            }

        return {
            'success': True,
            'image': image,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error getting image from Qdrant: {error_msg}')
        return ErrorResponse(error=f'Error getting image: {error_msg}')


@mcp.tool()
async def rag_listImages(
    doc_id: str | None = None,
    classification: str | None = None,
    limit: int = 50,
) -> dict[str, Any] | ErrorResponse:
    """List images with optional filters.

    Feature 024: List all images or filter by document/classification.

    Args:
        doc_id: Optional filter by document ID to list images from specific document
        classification: Optional filter by image type (schematic, pinout, waveform, etc.)
        limit: Maximum number of results (1-100, default: 50)

    Returns:
        Dictionary with list of images (without base64 data for performance)
    """
    if not _qdrant_available:
        return ErrorResponse(error='Qdrant client not available')

    try:
        if limit <= 0 or limit > 100:
            return ErrorResponse(error='limit must be between 1 and 100')

        client = get_qdrant_client()

        # List images
        images = await client.list_images(
            doc_id=doc_id,
            classification=classification,
            limit=limit,
        )

        return {
            'success': True,
            'doc_id_filter': doc_id,
            'classification_filter': classification,
            'image_count': len(images),
            'images': images,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error listing images from Qdrant: {error_msg}')
        return ErrorResponse(error=f'Error listing images: {error_msg}')


# ============================================================================
# Feature 022: LKAP Knowledge Promotion MCP Tools - T065, T066, T084, T085
# ============================================================================

@mcp.tool()
async def kg_promoteFromEvidence(
    evidence_id: str,
    fact_type: str,
    value: str,
    entity: str | None = None,
    scope: str | None = None,
    version: str | None = None,
    valid_until: str | None = None,
    resolution_strategy: str = "detect_only",
) -> dict[str, Any] | ErrorResponse:
    """Promote evidence to Knowledge Graph fact.

    Feature 022 T065: kg.promoteFromEvidence MCP tool implementation.
    T068: Evidence-to-fact linking (Evidence node → Fact node).

    Promotes a specific evidence chunk to a durable Knowledge Graph fact
    with full provenance tracking. Supports all 8 fact types:
    Constraint, Erratum, Workaround, API, BuildFlag, ProtocolRule, Detection, Indicator

    Args:
        evidence_id: Source evidence/chunk identifier from Qdrant
        fact_type: Type of fact to create (Constraint, Erratum, Workaround, API, BuildFlag, ProtocolRule, Detection, Indicator)
        value: Fact value (e.g., "120MHz", "Enable FIFO flush")
        entity: Optional entity name (e.g., "STM32H7.GPIO.max_speed")
        scope: Optional scope constraint for fact applicability
        version: Optional version this fact applies to
        valid_until: Optional expiration timestamp (ISO 8601)
        resolution_strategy: How to handle conflicts (detect_only, keep_both, prefer_newest, reject_incoming)

    Returns:
        Dictionary with created fact including fact_id, type, entity, value, evidence_ids, created_at
    """
    try:
        from patches.promotion import promote_from_evidence
        from patches.lkap_models import FactType, ResolutionStrategy

        # Parse fact type
        try:
            parsed_fact_type = FactType(fact_type)
        except ValueError:
            return ErrorResponse(error=f'Invalid fact_type: {fact_type}. Must be one of: Constraint, Erratum, Workaround, API, BuildFlag, ProtocolRule, Detection, Indicator')

        # Parse resolution strategy
        try:
            parsed_strategy = ResolutionStrategy(resolution_strategy)
        except ValueError:
            parsed_strategy = ResolutionStrategy.DETECT_ONLY

        # Parse valid_until if provided
        parsed_valid_until = None
        if valid_until:
            try:
                parsed_valid_until = parse_date_input(valid_until)
            except ValueError as e:
                return ErrorResponse(error=f'Invalid valid_until date: {e}')

        # Promote evidence to fact
        fact = await promote_from_evidence(
            evidence_id=evidence_id,
            fact_type=parsed_fact_type,
            value=value,
            entity=entity,
            scope=scope,
            version=version,
            valid_until=parsed_valid_until,
            resolution_strategy=parsed_strategy,
        )

        return {
            'success': True,
            'fact': {
                'fact_id': fact.fact_id,
                'type': fact.type.value,
                'entity': fact.entity,
                'value': fact.value,
                'scope': fact.scope,
                'version': fact.version,
                'valid_until': fact.valid_until.isoformat() if fact.valid_until else None,
                'evidence_ids': fact.evidence_ids,
                'created_at': fact.created_at.isoformat(),
            },
        }

    except ValueError as e:
        error_msg = str(e)
        logger.error(f'Validation error in promoteFromEvidence: {error_msg}')
        return ErrorResponse(error=f'Validation error: {error_msg}')
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error promoting evidence: {error_msg}')
        return ErrorResponse(error=f'Error promoting evidence: {error_msg}')


@mcp.tool()
async def kg_promoteFromQuery(
    query: str,
    fact_type: str,
    top_k: int = 5,
    scope: str | None = None,
    version: str | None = None,
    valid_until: str | None = None,
) -> dict[str, Any] | ErrorResponse:
    """Search for evidence and promote matching results to Knowledge Graph facts.

    Feature 022 T066: kg.promoteFromQuery MCP tool implementation.

    Combines semantic search (via Qdrant) with fact promotion in a single call.
    Searches for evidence chunks matching the query, then promotes the top-k results
    to Knowledge Graph facts with the specified type.

    Args:
        query: Natural language search query for finding evidence
        fact_type: Type of facts to create (Constraint, Erratum, Workaround, API, BuildFlag, ProtocolRule, Detection, Indicator)
        top_k: Maximum number of evidence chunks to promote (1-100, default: 5)
        scope: Optional scope constraint for facts
        version: Optional version facts apply to
        valid_until: Optional expiration timestamp (ISO 8601)

    Returns:
        Dictionary with created facts including fact_id, type, entity, value, evidence_ids, created_at
    """
    try:
        from patches.promotion import promote_from_query
        from patches.lkap_models import FactType

        # Parse fact type
        try:
            parsed_fact_type = FactType(fact_type)
        except ValueError:
            return ErrorResponse(error=f'Invalid fact_type: {fact_type}. Must be one of: Constraint, Erratum, Workaround, API, BuildFlag, ProtocolRule, Detection, Indicator')

        # Validate top_k
        if top_k <= 0 or top_k > 100:
            return ErrorResponse(error='top_k must be between 1 and 100')

        # Parse valid_until if provided
        parsed_valid_until = None
        if valid_until:
            try:
                parsed_valid_until = parse_date_input(valid_until)
            except ValueError as e:
                return ErrorResponse(error=f'Invalid valid_until date: {e}')

        # Promote from query
        facts = await promote_from_query(
            query=query,
            fact_type=parsed_fact_type,
            top_k=top_k,
            scope=scope,
            version=version,
            valid_until=parsed_valid_until,
        )

        return {
            'success': True,
            'query': query,
            'fact_count': len(facts),
            'facts': [
                {
                    'fact_id': f.fact_id,
                    'type': f.type.value,
                    'entity': f.entity,
                    'value': f.value,
                    'scope': f.scope,
                    'version': f.version,
                    'valid_until': f.valid_until.isoformat() if f.valid_until else None,
                    'evidence_ids': f.evidence_ids,
                    'created_at': f.created_at.isoformat(),
                }
                for f in facts
            ],
        }

    except ValueError as e:
        error_msg = str(e)
        logger.error(f'Validation error in promoteFromQuery: {error_msg}')
        return ErrorResponse(error=f'Validation error: {error_msg}')
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error promoting from query: {error_msg}')
        return ErrorResponse(error=f'Error promoting from query: {error_msg}')


@mcp.tool()
async def kg_reviewConflicts(
    entity: str | None = None,
    fact_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict[str, Any] | ErrorResponse:
    """Review conflicts with optional filters.

    Feature 022 T084: kg.reviewConflicts MCP tool implementation.

    Retrieves conflict records for review, with optional filtering by
    entity, fact type, or status. Useful for identifying and resolving
    conflicting facts in the Knowledge Graph.

    Args:
        entity: Optional entity filter (e.g., "STM32H7.GPIO.max_speed")
        fact_type: Optional fact type filter (Constraint, Erratum, etc.)
        status: Optional status filter (open, resolved, deferred)
        limit: Maximum results to return (default: 50)

    Returns:
        Dictionary with conflict records including conflict_id, facts (with conflicting values),
        detection_date, resolution_strategy, and status
    """
    try:
        from patches.promotion import review_conflicts
        from patches.lkap_models import FactType, ConflictStatus

        # Parse fact type if provided
        parsed_fact_type = None
        if fact_type:
            try:
                parsed_fact_type = FactType(fact_type)
            except ValueError:
                return ErrorResponse(error=f'Invalid fact_type: {fact_type}')

        # Parse status if provided
        parsed_status = None
        if status:
            try:
                parsed_status = ConflictStatus(status)
            except ValueError:
                return ErrorResponse(error=f'Invalid status: {status}. Must be one of: open, resolved, deferred')

        # Validate limit
        if limit <= 0 or limit > 1000:
            return ErrorResponse(error='limit must be between 1 and 1000')

        # Review conflicts
        conflicts = await review_conflicts(
            entity=entity,
            fact_type=parsed_fact_type,
            status=parsed_status,
            limit=limit,
        )

        return {
            'success': True,
            'conflict_count': len(conflicts),
            'conflicts': [
                {
                    'conflict_id': c.conflict_id,
                    'facts': [
                        {
                            'fact_id': f.fact_id,
                            'type': f.type.value,
                            'entity': f.entity,
                            'value': f.value,
                            'created_at': f.created_at.isoformat(),
                        }
                        for f in c.facts
                    ],
                    'detection_date': c.detection_date.isoformat(),
                    'resolution_strategy': c.resolution_strategy.value,
                    'status': c.status.value,
                    'resolved_at': c.resolved_at.isoformat() if c.resolved_at else None,
                }
                for c in conflicts
            ],
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error reviewing conflicts: {error_msg}')
        return ErrorResponse(error=f'Error reviewing conflicts: {error_msg}')


@mcp.tool()
async def kg_getProvenance(
    fact_id: str,
) -> dict[str, Any] | ErrorResponse:
    """Get provenance chain for a fact.

    Feature 022 T085: kg.getProvenance MCP tool implementation.
    T069: Provenance preservation (Fact → Evidence → Chunk → Document chain).

    Retrieves the complete provenance chain for a fact, showing all
    evidence chunks and source documents that support the fact. Useful
    for verification, auditing, and understanding fact origin.

    Args:
        fact_id: Fact identifier (UUID)

    Returns:
        Dictionary with fact, evidence_chain (chunk_id, text, confidence),
        and documents (doc_id, filename, path, page_section)
    """
    try:
        from patches.promotion import get_provenance

        if not fact_id:
            return ErrorResponse(error='fact_id is required')

        # Get provenance
        provenance = await get_provenance(fact_id)

        return {
            'success': True,
            'fact_id': fact_id,
            'provenance': provenance,
        }

    except ValueError as e:
        error_msg = str(e)
        logger.error(f'Fact not found: {error_msg}')
        return ErrorResponse(error=f'Fact not found: {error_msg}')
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error getting provenance: {error_msg}')
        return ErrorResponse(error=f'Error getting provenance: {error_msg}')


# ============================================================================
# End of Feature 022 MCP Tools
# ============================================================================

def main():
    """Initialize and run the MCP server with all patches."""

    # Feature 006: Initialize Gemini Prompt Caching metrics exporter
    if _metrics_exporter_available:
        try:
            metrics_enabled = os.getenv("PROMPT_CACHE_METRICS_ENABLED", "true").lower() == "true"
            initialize_metrics_exporter(enabled=metrics_enabled, port=metrics_port)
            logger.info("Madeinoz Patch: Feature 006 - Gemini prompt caching with cost tracking and Prometheus metrics (active)")
            logger.info(f"Prompt caching metrics exporter initialized (enabled={metrics_enabled}, port={metrics_port})")
        except Exception as e:
            logger.warning(f"Failed to initialize metrics exporter: {e}")

    # Feature 009: Initialize decay metrics exporter (shares meter with cache metrics)
    if _decay_metrics_available and _metrics_exporter_available:
        try:
            decay_exporter = initialize_decay_metrics_exporter()
            if decay_exporter:
                logger.info("Madeinoz Patch: Feature 009 - Decay metrics exporter initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize decay metrics exporter: {e}")

    # Feature 017: Initialize queue metrics exporter (shares meter with cache metrics)
    if _queue_metrics_available and _metrics_exporter_available:
        try:
            global _queue_metrics_exporter
            _queue_metrics_exporter = initialize_queue_metrics_exporter()
            if _queue_metrics_exporter:
                logger.info("Madeinoz Patch: Feature 017 - Queue metrics exporter initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize queue metrics exporter: {e}")

    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logger.info('Server shutting down...')
        # Feature 009: Stop scheduled maintenance
        try:
            asyncio.run(shutdown_maintenance())
        except Exception as shutdown_err:
            logger.warning(f'Error during maintenance shutdown: {shutdown_err}')
    except Exception as e:
        logger.error(f'Error initializing Graphiti MCP server: {str(e)}')
        raise


if __name__ == '__main__':
    main()
# Cache bust: 1770796169
