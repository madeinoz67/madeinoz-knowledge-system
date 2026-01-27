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


class GraphitiService:
    """Graphiti service using the unified configuration system."""

    def __init__(self, config: GraphitiConfig, semaphore_limit: int = 10):
        self.config = config
        self.semaphore_limit = semaphore_limit
        self.semaphore = asyncio.Semaphore(semaphore_limit)
        self.client: Graphiti | None = None
        self.entity_types = None

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
            custom_types = None
            if self.config.graphiti.entity_types:
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

            # Store entity types for later use
            self.entity_types = custom_types

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

        # Submit to queue service for async processing
        await queue_service.add_episode(
            group_id=effective_group_id,
            name=name,
            content=episode_body,
            source_description=source_description,
            episode_type=episode_type,
            entity_types=graphiti_service.entity_types,
            uuid=uuid or None,
        )

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
) -> NodeSearchResponse | ErrorResponse:
    """Search for nodes in the graph memory with optional temporal filtering.

    Args:
        query: The search query
        group_ids: Optional list of group IDs to filter results
        max_nodes: Maximum number of nodes to return (default: 10)
        entity_types: Optional list of entity type names to filter by
        created_after: Return nodes created after this date (ISO 8601 or relative: "today", "7d", "1 week ago")
        created_before: Return nodes created before this date (ISO 8601 or relative)
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

        # If temporal filtering is needed, fetch more results to filter
        fetch_limit = max_nodes * 3 if has_temporal_filter else max_nodes

        results = await client.search_(
            query=query,
            config=NODE_HYBRID_SEARCH_RRF,
            group_ids=effective_group_ids,
            search_filter=search_filters,
        )

        # Extract nodes from results
        nodes = results.nodes if results.nodes else []

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

        # Apply limit after filtering
        nodes = nodes[:max_nodes]

        if not nodes:
            return NodeSearchResponse(message='No relevant nodes found', nodes=[])

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
) -> FactSearchResponse | ErrorResponse:
    """Search the graph memory for relevant facts with optional temporal filtering.

    Args:
        query: The search query
        group_ids: Optional list of group IDs to filter results
        max_facts: Maximum number of facts to return (default: 10)
        center_node_uuid: Optional UUID of a node to center the search around
        created_after: Return facts created after this date (ISO 8601 or relative: "today", "7d", "1 week ago")
        created_before: Return facts created before this date (ISO 8601 or relative)
    """
    global graphiti_service

    if graphiti_service is None:
        return ErrorResponse(error='Graphiti service not initialized')

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

        # If temporal filtering is needed, fetch more results to filter
        fetch_limit = max_facts * 3 if has_temporal_filter else max_facts

        relevant_edges = await client.search(
            group_ids=effective_group_ids,
            query=query,
            num_results=fetch_limit,
            center_node_uuid=center_node_uuid,
        )

        if not relevant_edges:
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
            relevant_edges = filtered_edges[:max_facts]
            logger.debug(f'Madeinoz Patch: Temporal filter applied, {len(relevant_edges)} facts remaining')
        else:
            relevant_edges = relevant_edges[:max_facts]

        if not relevant_edges:
            return FactSearchResponse(message='No relevant facts found', facts=[])

        facts = [format_fact_result(edge) for edge in relevant_edges]
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


@mcp.custom_route('/health', methods=['GET'])
async def health_check(request) -> JSONResponse:
    """
    Health check endpoint for Docker and load balancers.

    SECURITY: Minimal information disclosure.
    Only returns status - no internal configuration details exposed.
    """
    return JSONResponse({'status': 'healthy'})


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


async def run_mcp_server():
    """Run the MCP server in the current event loop."""
    global rate_limiter

    mcp_config = await initialize_server()

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


def main():
    """Main function to run the Graphiti MCP server."""
    # Feature 006: Initialize Gemini Prompt Caching metrics exporter
    if _metrics_exporter_available:
        try:
            metrics_port = int(os.getenv("MADEINOZ_KNOWLEDGE_METRICS_PORT", "9090"))
            metrics_enabled = os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED", "true").lower() == "true"
            initialize_metrics_exporter(enabled=metrics_enabled, port=metrics_port)
            logger.info("Madeinoz Patch: Feature 006 - Gemini prompt caching with cost tracking and Prometheus metrics (active)")
            logger.info(f"Prompt caching metrics exporter initialized (enabled={metrics_enabled}, port={metrics_port})")
        except Exception as e:
            logger.warning(f"Failed to initialize metrics exporter: {e}")

    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logger.info('Server shutting down...')
    except Exception as e:
        logger.error(f'Error initializing Graphiti MCP server: {str(e)}')
        raise


if __name__ == '__main__':
    main()
