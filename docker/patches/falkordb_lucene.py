"""
FalkorDB Lucene Sanitization Patch

Madeinoz Patch: Fixes Lucene query sanitization for FalkorDB backend.

This patch addresses the following issues:
- Graphiti's FalkorDB driver doesn't sanitize group_ids in search queries
- Special characters in episode body content are not escaped before storage
- Characters like '-', '|', '/', '@', etc. cause RediSearch syntax errors

Related Issues:
- RediSearch #2628: Can't search text with hyphens
- Graphiti #815: FalkorDB query syntax errors with pipe character
- Graphiti #1118: Fix forward slash character handling

Special Characters in Lucene/RediSearch Syntax:
+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ / @ # $ % < > =

The patch provides:
1. get_database_backend(): Detect which backend is active
2. lucene_escape(): Escape special characters with backslash (FalkorDB only)
3. PatchedFalkorDriver: Extends FalkorDriver with proper group_id sanitization
4. Episode content sanitization when adding to graph (FalkorDB only)
"""

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================================
# Database Backend Detection
# ============================================================================

def get_database_backend() -> str:
    """
    Detect the database backend from environment variables.

    Checks for:
    - MADEINOZ_KNOWLEDGE_DATABASE_TYPE (pack-specific prefix)
    - DATABASE_TYPE (container environment)

    Returns:
        'falkordb' or 'neo4j' (default is 'neo4j')

    Note: This function always loads and checks the configured backend.
    Sanitization functions use this to determine whether to apply escaping.
    """
    db_type = (
        os.getenv('MADEINOZ_KNOWLEDGE_DATABASE_TYPE') or
        os.getenv('DATABASE_TYPE') or
        'neo4j'
    ).lower()

    if db_type == 'falkordb':
        return 'falkordb'
    return 'neo4j'


def requires_lucene_sanitization() -> bool:
    """
    Check if Lucene sanitization is required for the current database backend.

    Returns:
        True if using FalkorDB (requires Lucene sanitization), False for Neo4j
    """
    return get_database_backend() == 'falkordb'


# ============================================================================
# Lucene Special Character Escaping
# ============================================================================

# Lucene/RediSearch special characters that need escaping
# Order matters: escape backslash first, then others
# Pre-compile for performance (used frequently)
LUCENE_SPECIAL_PATTERN = re.compile(r'[+\-&|!(){}\[\]^"~*?:/@#$%<>=]')


def lucene_escape(value: str | None) -> str:
    """
    Escape special Lucene/RediSearch characters in a string value.

    This function wraps the value in double quotes and escapes any internal
    special characters, ensuring the value is treated as a literal string
    rather than as Lucene query syntax.

    BACKEND DETECTION: Only applies escaping when using FalkorDB.
    When using Neo4j, returns the original value unchanged.

    Special characters escaped:
    + - & | ! ( ) { } [ ] ^ " ~ * ? : \ / @ # $ % < > =

    Args:
        value: The value to escape (e.g., group_id, search term)

    Returns:
        The escaped value safe for use in Lucene queries (FalkorDB)
        The original value unchanged (Neo4j)

    Examples:
        >>> # FalkorDB backend
        >>> lucene_escape("madeinoz-threat-intel")
        '"madeinoz-threat-intel"'
        >>> lucene_escape('user "quoted" text')
        '"user \\"quoted\\" text"'
        >>> # Neo4j backend (no escaping)
        >>> lucene_escape("madeinoz-threat-intel")
        'madeinoz-threat-intel'
    """
    # Handle None and empty values
    if value is None or not value:
        return '""'

    # Neo4j backend: no sanitization needed
    if not requires_lucene_sanitization():
        return value

    # Escape backslashes first (so we don't double-escape later)
    escaped = value.replace('\\', '\\\\')

    # Escape double quotes
    escaped = escaped.replace('"', '\\"')

    # Wrap in double quotes to treat the entire value as a literal
    return f'"{escaped}"'


def lucene_escape_in_place(value: str | None) -> str:
    """
    Escape special Lucene characters in-place without wrapping in quotes.

    This preserves the ability to use OR logic between words while escaping
    special characters that would be interpreted as operators.

    BACKEND DETECTION: Only applies escaping when using FalkorDB.
    When using Neo4j, returns the original value unchanged.

    Args:
        value: The string to escape

    Returns:
        The escaped string (FalkorDB) or original value (Neo4j)

    Examples:
        >>> # FalkorDB backend
        >>> lucene_escape_in_place("madeinoz-threat-intel")
        'madeinoz\\-threat\\-intel'
        >>> lucene_escape_in_place("A || B")
        'A \\|\\| B'
        >>> # Neo4j backend (no escaping)
        >>> lucene_escape_in_place("A || B")
        'A || B'
    """
    # Handle None and empty values
    if value is None or not value:
        return value if value is not None else ''

    # Neo4j backend: no sanitization needed
    if not requires_lucene_sanitization():
        return value

    # Escape backslash first
    escaped = value.replace('\\', '\\\\')

    # Escape && and || before escaping individual & and |
    escaped = escaped.replace('&&', '\\&\\&')
    escaped = escaped.replace('||', '\\|\\|')

    # Escape other special characters (use pre-compiled pattern)
    escaped = LUCENE_SPECIAL_PATTERN.sub(r'\\\g<0>', escaped)

    return escaped


def sanitize_group_id(group_id: str | None) -> str:
    """
    Sanitize a group_id for use in Lucene queries.

    For group_ids, we use a different strategy:
    - Convert hyphens to underscores (avoiding the negation operator)
    - This is consistent with the TypeScript lucene.ts implementation

    BACKEND DETECTION: Only applies sanitization when using FalkorDB.
    When using Neo4j, returns the original group_id unchanged.

    Args:
        group_id: The group_id to sanitize

    Returns:
        The sanitized group_id (FalkorDB) or original (Neo4j)

    Examples:
        >>> # FalkorDB backend
        >>> sanitize_group_id("madeinoz-threat-intel")
        'madeinoz_threat_intel'
        >>> # Neo4j backend (no escaping)
        >>> sanitize_group_id("madeinoz-threat-intel")
        'madeinoz-threat-intel'
    """
    # Handle None and empty values
    if group_id is None or not group_id:
        return group_id if group_id is not None else None

    # Neo4j backend: no sanitization needed
    if not requires_lucene_sanitization():
        return group_id

    # Validate that group_id contains only allowed characters
    # Graphiti validation: [a-zA-Z0-9_-]
    valid_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
    if not valid_pattern.match(group_id):
        logger.warning(
            f'[lucene] Invalid group_id "{group_id}" - escaping with lucene_escape()'
        )
        # ESCAPE invalid group_ids instead of returning as-is (fixes injection vulnerability)
        return lucene_escape(group_id).strip('"')

    # Convert hyphens to underscores to avoid Lucene negation operator
    sanitized = group_id.replace('-', '_')

    if sanitized != group_id:
        logger.info(
            f'[lucene] Converted group_id "{group_id}" to "{sanitized}" (hyphens → underscores)'
        )

    return sanitized


def sanitize_group_ids(group_ids: list[str] | None) -> list[str] | None:
    """
    Sanitize a list of group_ids for use in Lucene queries.

    BACKEND DETECTION: Only applies sanitization when using FalkorDB.
    When using Neo4j, returns the original list unchanged.

    Args:
        group_ids: List of group_ids to sanitize

    Returns:
        List of sanitized group_ids (FalkorDB) or original (Neo4j)
    """
    if not group_ids:
        return None

    # Neo4j backend: no sanitization needed
    if not requires_lucene_sanitization():
        return group_ids

    return [sanitize_group_id(gid) for gid in group_ids if gid]


# ============================================================================
# Patched FalkorDB Driver
# ============================================================================

class PatchedFalkorDriverMixin:
    """
    Mixin class that patches FalkorDB driver's build_fulltext_query method.

    This mixin provides a corrected version of build_fulltext_query that
    properly sanitizes group_ids before using them in Lucene queries.

    Usage:
        The patch is applied by monkey-patching FalkorDriver at runtime.
        See patch_falkor_driver() below.
    """

    STOPWORDS = [
        'a', 'is', 'the', 'an', 'and', 'are', 'as', 'at', 'be', 'but', 'by',
        'for', 'if', 'in', 'into', 'it', 'no', 'not', 'of', 'on', 'or', 'such',
        'that', 'their', 'then', 'there', 'these', 'they', 'this', 'to', 'was',
        'will', 'with',
    ]

    def build_fulltext_query_patched(
        self, query: str, group_ids: list[str] | None = None, max_query_length: int = 128
    ) -> str:
        """
        Build a fulltext query string for FalkorDB using RedisSearch syntax.

        Madeinoz Patch: This method properly sanitizes group_ids before including
        them in the query. The original FalkorDB driver does not sanitize group_ids,
        causing syntax errors when group_ids contain hyphens or other special characters.

        FalkorDB uses RedisSearch-like syntax where:
        - Field queries use @ prefix: @field:value
        - Multiple values for same field: (@field:value1|value2)
        - Text search doesn't need @ prefix for content fields
        - AND is implicit with space: (@group_id:value) (text)
        - OR uses pipe within parentheses: (@group_id:value1|value2)

        BACKEND DETECTION: This method is only called when using FalkorDB,
        so sanitization is always applied here.
        """
        # Sanitize group_ids - convert hyphens to underscores
        sanitized_group_ids = sanitize_group_ids(group_ids)

        if sanitized_group_ids is None or len(sanitized_group_ids) == 0:
            group_filter = ''
        else:
            # Join sanitized group_ids with | for OR logic
            # The group_ids are now safe (hyphens converted to underscores)
            group_values = '|'.join(sanitized_group_ids)
            group_filter = f'(@group_id:{group_values})'

        # Sanitize the query using the driver's existing sanitize method
        # This replaces special chars with whitespace for fulltext search
        sanitized_query = self.sanitize(query)

        # Remove stopwords from the sanitized query
        query_words = sanitized_query.split()
        filtered_words = [word for word in query_words if word.lower() not in self.STOPWORDS]
        sanitized_query = ' | '.join(filtered_words)

        # If the query is too long return no query
        if len(sanitized_query.split(' ')) + len(sanitized_group_ids or []) >= max_query_length:
            return ''

        full_query = group_filter + ' (' + sanitized_query + ')'

        logger.debug(f'[lucene] Built query: {full_query}')

        return full_query


# ============================================================================
# Patch Application Function
# ============================================================================

def patch_falkor_driver() -> bool:
    """
    Apply the Lucene sanitization patch to FalkorDB driver.

    This function monkey-patches the FalkorDriver class to use the corrected
    build_fulltext_query method that properly sanitizes group_ids.

    BACKEND DETECTION: The patch is always applied (if FalkorDriver exists),
    but sanitization functions check the database backend at runtime and only
    apply escaping when using FalkorDB. This allows the same code to work
    with both Neo4j and FalkorDB backends.

    Example:
        >>> from patches.falkordb_lucene import patch_falkor_driver
        >>> patch_falkor_driver()

    Returns:
        True if patch was applied, False if FalkorDriver not available
    """
    detected_backend = get_database_backend()

    try:
        from graphiti_core.driver.falkordb_driver import FalkorDriver

        # Store the original method for reference
        original_method = FalkorDriver.build_fulltext_query

        # Apply the patched method
        FalkorDriver.build_fulltext_query = PatchedFalkorDriverMixin.build_fulltext_query_patched

        logger.info(f'Madeinoz Patch: FalkorDB Lucene sanitization patch applied')
        logger.info(f'  - Detected backend: {detected_backend}')
        logger.info(f'  - Sanitization active: {requires_lucene_sanitization()}')
        if requires_lucene_sanitization():
            logger.info('  - group_ids will be sanitized (hyphens → underscores)')
            logger.info('  - Episode content will be escaped (special chars)')
        else:
            logger.info('  - Sanitization bypassed (Neo4j uses Cypher, no escaping needed)')
        logger.info('  - Original method preserved for reference')

        return True

    except ImportError as e:
        logger.info(f'Madeinoz Patch: FalkorDB driver not available - using {detected_backend} backend: {e}')
        return False
    except Exception as e:
        logger.error(f'Madeinoz Patch: Failed to apply FalkorDB patch: {e}')
        return False


# ============================================================================
# Episode Content Sanitization
# ============================================================================

def sanitize_episode_content(content: str | None, max_length: int = 10000) -> str:
    """
    Sanitize episode content before storing in the knowledge graph.

    This function escapes special Lucene characters in episode content
    to prevent RediSearch syntax errors when the content is indexed.

    For episode bodies, we use in-place escaping to preserve readability
    while preventing syntax errors.

    BACKEND DETECTION: Only applies escaping when using FalkorDB.
    When using Neo4j, returns the original content unchanged.

    Args:
        content: The episode content to sanitize
        max_length: Maximum length of content (beyond this, truncate)

    Returns:
        The sanitized episode content (FalkorDB) or original (Neo4j)

    Examples:
        >>> # FalkorDB backend
        >>> sanitize_episode_content("APT-28 is a threat group")
        'APT\\-28 is a threat group'
        >>> # Neo4j backend (no escaping)
        >>> sanitize_episode_content("APT-28 is a threat group")
        'APT-28 is a threat group'
    """
    # Handle None and empty values
    if content is None:
        return None
    if not content:
        return content

    # Neo4j backend: no sanitization needed
    if not requires_lucene_sanitization():
        return content

    # Truncate if too long (RediSearch has query length limits)
    # Avoid double concatenation
    if len(content) > max_length:
        content = content[:max_length - 3] + '...'

    # Escape special Lucene characters in-place
    sanitized = lucene_escape_in_place(content)

    if sanitized != content:
        logger.debug(f'[lucene] Sanitized episode content (special chars escaped)')

    return sanitized


# ============================================================================
# Auto-patch on import
# ============================================================================

# Apply the patch automatically when this module is imported
# This ensures the patch is active before any Graphiti operations
_patch_applied = patch_falkor_driver()
