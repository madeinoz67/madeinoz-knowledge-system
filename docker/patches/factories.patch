"""Factory classes for creating LLM, Embedder, and Database clients.

Madeinoz Patch v2: Extended OpenAI-compatible API support.
- Supports local LLMs via Ollama (localhost endpoints)
- Supports cloud providers via OpenRouter, Together AI, and other OpenAI-compatible APIs
- Fixes GitHub issue #1116 where the MCP server ignores api_base/base_url configuration.

OpenAI-compatible providers:
- OpenAI Direct: https://api.openai.com/v1 (default, uses native client)
- OpenRouter: https://openrouter.ai/api/v1 (requires API key)
- Together AI: https://api.together.xyz/v1 (requires API key)
- Ollama: http://localhost:11434/v1 or http://host.docker.internal:11434/v1 (no key needed)
"""

from openai import AsyncAzureOpenAI

from config.schema import (
    DatabaseConfig,
    EmbedderConfig,
    LLMConfig,
)

# Try to import FalkorDriver if available
try:
    from graphiti_core.driver.falkordb_driver import FalkorDriver  # noqa: F401

    HAS_FALKOR = True
except ImportError:
    HAS_FALKOR = False

from graphiti_core.embedder import EmbedderClient, OpenAIEmbedder
from graphiti_core.llm_client import LLMClient, OpenAIClient
from graphiti_core.llm_client.config import LLMConfig as GraphitiLLMConfig

# Madeinoz Patch: Import OpenAIGenericClient for Ollama/custom endpoint support
try:
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient

    HAS_GENERIC_CLIENT = True
except ImportError:
    HAS_GENERIC_CLIENT = False

# Try to import additional providers if available
try:
    from graphiti_core.embedder.azure_openai import AzureOpenAIEmbedderClient

    HAS_AZURE_EMBEDDER = True
except ImportError:
    HAS_AZURE_EMBEDDER = False

try:
    from graphiti_core.embedder.gemini import GeminiEmbedder

    HAS_GEMINI_EMBEDDER = True
except ImportError:
    HAS_GEMINI_EMBEDDER = False

try:
    from graphiti_core.embedder.voyage import VoyageAIEmbedder

    HAS_VOYAGE_EMBEDDER = True
except ImportError:
    HAS_VOYAGE_EMBEDDER = False

try:
    from graphiti_core.llm_client.azure_openai_client import AzureOpenAILLMClient

    HAS_AZURE_LLM = True
except ImportError:
    HAS_AZURE_LLM = False

try:
    from graphiti_core.llm_client.anthropic_client import AnthropicClient

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    from graphiti_core.llm_client.gemini_client import GeminiClient

    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    from graphiti_core.llm_client.groq_client import GroqClient

    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
from utils.utils import create_azure_credential_token_provider


# Madeinoz Patch: Default OpenAI endpoint for comparison
DEFAULT_OPENAI_URL = 'https://api.openai.com/v1'

# Known OpenAI-compatible cloud providers (require API keys)
OPENAI_COMPATIBLE_CLOUD_PROVIDERS = [
    'openrouter.ai',
    'api.together.xyz',
    'api.fireworks.ai',
    'api.deepinfra.com',
    'api.perplexity.ai',
    'api.mistral.ai',
]

# Known local/self-hosted providers (don't require API keys)
LOCAL_PROVIDERS = [
    'localhost',
    '127.0.0.1',
    'host.docker.internal',
    '10.0.0.',  # Common home network prefix
    '192.168.',  # Common home network prefix
]


def _validate_api_key(provider_name: str, api_key: str | None, logger) -> str:
    """Validate API key is present.

    Args:
        provider_name: Name of the provider (e.g., 'OpenAI', 'Anthropic')
        api_key: The API key to validate
        logger: Logger instance for output

    Returns:
        The validated API key

    Raises:
        ValueError: If API key is None or empty
    """
    if not api_key:
        raise ValueError(
            f'{provider_name} API key is not configured. Please set the appropriate environment variable.'
        )

    logger.info(f'Creating {provider_name} client')

    return api_key


def _is_custom_endpoint(api_url: str | None) -> bool:
    """Check if the API URL is a custom endpoint (not default OpenAI).

    Madeinoz Patch: Used to determine whether to use OpenAIGenericClient for
    Ollama/local LLMs and OpenAI-compatible cloud providers.

    Args:
        api_url: The API URL to check

    Returns:
        True if custom endpoint, False if default OpenAI
    """
    if not api_url:
        return False
    # Normalize URLs for comparison
    normalized_url = api_url.rstrip('/')
    normalized_default = DEFAULT_OPENAI_URL.rstrip('/')
    return normalized_url.lower() != normalized_default.lower()


def _is_local_endpoint(api_url: str | None) -> bool:
    """Check if the API URL points to a local/self-hosted service (like Ollama).

    Madeinoz Patch v2: Distinguish local endpoints that don't need API keys
    from cloud providers that do.

    Args:
        api_url: The API URL to check

    Returns:
        True if local endpoint (Ollama, etc.), False if cloud provider
    """
    if not api_url:
        return False
    url_lower = api_url.lower()
    return any(prefix in url_lower for prefix in LOCAL_PROVIDERS)


def _get_provider_name_from_url(api_url: str | None) -> str:
    """Extract a human-readable provider name from the API URL.

    Madeinoz Patch v2: Used for logging and error messages.

    Args:
        api_url: The API URL

    Returns:
        Provider name string
    """
    if not api_url:
        return 'OpenAI'

    url_lower = api_url.lower()

    if 'openrouter.ai' in url_lower:
        return 'OpenRouter'
    elif 'together.xyz' in url_lower:
        return 'Together AI'
    elif 'fireworks.ai' in url_lower:
        return 'Fireworks AI'
    elif 'deepinfra.com' in url_lower:
        return 'DeepInfra'
    elif 'perplexity.ai' in url_lower:
        return 'Perplexity'
    elif 'mistral.ai' in url_lower:
        return 'Mistral AI'
    elif _is_local_endpoint(api_url):
        return 'Ollama (local)'
    else:
        return 'OpenAI-compatible'


class LLMClientFactory:
    """Factory for creating LLM clients based on configuration."""

    @staticmethod
    def create(config: LLMConfig) -> LLMClient:
        """Create an LLM client based on the configured provider."""
        import logging

        logger = logging.getLogger(__name__)

        provider = config.provider.lower()

        match provider:
            case 'openai':
                if not config.providers.openai:
                    raise ValueError('OpenAI provider configuration not found')

                api_key = config.providers.openai.api_key
                api_url = config.providers.openai.api_url

                # Madeinoz Patch v2: Enhanced API key handling for different provider types
                provider_name = _get_provider_name_from_url(api_url)
                is_custom = _is_custom_endpoint(api_url)
                is_local = _is_local_endpoint(api_url)

                if not is_custom:
                    # Default OpenAI endpoint - require valid API key
                    _validate_api_key('OpenAI', api_key, logger)
                elif is_local:
                    # Local endpoint (Ollama) - allow dummy key
                    logger.info(f'Creating client for local endpoint ({provider_name}): {api_url}')
                    if not api_key:
                        api_key = 'ollama'  # Default dummy key for Ollama
                else:
                    # Cloud OpenAI-compatible provider (OpenRouter, Together, etc.) - require real key
                    logger.info(f'Creating client for {provider_name}: {api_url}')
                    _validate_api_key(provider_name, api_key, logger)

                from graphiti_core.llm_client.config import LLMConfig as CoreLLMConfig

                # Madeinoz Patch Simplified: Use same model for all tasks (main + small)
                # No separate small model - user configures one LLM model in env
                small_model = config.model

                # Madeinoz Patch v2: Include base_url in config for all custom endpoints
                llm_config = CoreLLMConfig(
                    api_key=api_key,
                    base_url=api_url if is_custom else None,
                    model=config.model,
                    small_model=small_model,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                )

                # Madeinoz Patch v3: Use OpenAIClient for cloud providers, OpenAIGenericClient for local
                # Per GitHub issue #912, OpenAIClient has better structured output support
                # which prevents EdgeDuplicate Pydantic validation errors.
                # - OpenAIClient: Uses parse API with strict schema enforcement (better for OpenRouter)
                # - OpenAIGenericClient: Uses basic json_object mode (needed for Ollama)
                if is_custom:
                    if is_local:
                        # Local endpoints (Ollama) - use generic client
                        if not HAS_GENERIC_CLIENT:
                            raise ValueError(
                                'OpenAIGenericClient not available. '
                                'Local endpoints require graphiti-core >= 0.5.0'
                            )
                        logger.info(f'Madeinoz Patch v3: Using OpenAIGenericClient for local {provider_name}')
                        return OpenAIGenericClient(config=llm_config)
                    else:
                        # Cloud providers (OpenRouter, Together, etc.) - use standard OpenAI client
                        # These providers proxy to OpenAI models and support the parse API
                        logger.info(f'Madeinoz Patch v3: Using OpenAIClient for cloud {provider_name}')
                        return OpenAIClient(config=llm_config)

                # Standard OpenAI endpoint - use regular client
                if is_reasoning_model:
                    return OpenAIClient(config=llm_config, reasoning='minimal', verbosity='low')
                else:
                    return OpenAIClient(config=llm_config, reasoning=None, verbosity=None)

            case 'azure_openai':
                if not HAS_AZURE_LLM:
                    raise ValueError(
                        'Azure OpenAI LLM client not available in current graphiti-core version'
                    )
                if not config.providers.azure_openai:
                    raise ValueError('Azure OpenAI provider configuration not found')
                azure_config = config.providers.azure_openai

                if not azure_config.api_url:
                    raise ValueError('Azure OpenAI API URL is required')

                # Handle Azure AD authentication if enabled
                api_key: str | None = None
                azure_ad_token_provider = None
                if azure_config.use_azure_ad:
                    logger.info('Creating Azure OpenAI LLM client with Azure AD authentication')
                    azure_ad_token_provider = create_azure_credential_token_provider()
                else:
                    api_key = azure_config.api_key
                    _validate_api_key('Azure OpenAI', api_key, logger)

                # Create the Azure OpenAI client first
                azure_client = AsyncAzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=azure_config.api_url,
                    api_version=azure_config.api_version,
                    azure_deployment=azure_config.deployment_name,
                    azure_ad_token_provider=azure_ad_token_provider,
                )

                # Then create the LLMConfig
                from graphiti_core.llm_client.config import LLMConfig as CoreLLMConfig

                llm_config = CoreLLMConfig(
                    api_key=api_key,
                    base_url=azure_config.api_url,
                    model=config.model,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                )

                return AzureOpenAILLMClient(
                    azure_client=azure_client,
                    config=llm_config,
                    max_tokens=config.max_tokens,
                )

            case 'anthropic':
                if not HAS_ANTHROPIC:
                    raise ValueError(
                        'Anthropic client not available in current graphiti-core version'
                    )
                if not config.providers.anthropic:
                    raise ValueError('Anthropic provider configuration not found')

                api_key = config.providers.anthropic.api_key
                _validate_api_key('Anthropic', api_key, logger)

                llm_config = GraphitiLLMConfig(
                    api_key=api_key,
                    model=config.model,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                )
                return AnthropicClient(config=llm_config)

            case 'gemini':
                if not HAS_GEMINI:
                    raise ValueError('Gemini client not available in current graphiti-core version')
                if not config.providers.gemini:
                    raise ValueError('Gemini provider configuration not found')

                api_key = config.providers.gemini.api_key
                _validate_api_key('Gemini', api_key, logger)

                llm_config = GraphitiLLMConfig(
                    api_key=api_key,
                    model=config.model,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                )
                return GeminiClient(config=llm_config)

            case 'groq':
                if not HAS_GROQ:
                    raise ValueError('Groq client not available in current graphiti-core version')
                if not config.providers.groq:
                    raise ValueError('Groq provider configuration not found')

                api_key = config.providers.groq.api_key
                _validate_api_key('Groq', api_key, logger)

                llm_config = GraphitiLLMConfig(
                    api_key=api_key,
                    base_url=config.providers.groq.api_url,
                    model=config.model,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                )
                return GroqClient(config=llm_config)

            case _:
                raise ValueError(f'Unsupported LLM provider: {provider}')


class EmbedderFactory:
    """Factory for creating Embedder clients based on configuration."""

    @staticmethod
    def create(config: EmbedderConfig) -> EmbedderClient:
        """Create an Embedder client based on the configured provider."""
        import logging

        logger = logging.getLogger(__name__)

        provider = config.provider.lower()

        match provider:
            case 'openai':
                if not config.providers.openai:
                    raise ValueError('OpenAI provider configuration not found')

                api_key = config.providers.openai.api_key
                api_url = config.providers.openai.api_url

                # Madeinoz Patch v2: Enhanced API key handling for different provider types
                provider_name = _get_provider_name_from_url(api_url)
                is_custom = _is_custom_endpoint(api_url)
                is_local = _is_local_endpoint(api_url)

                if not is_custom:
                    # Default OpenAI endpoint - require valid API key
                    _validate_api_key('OpenAI Embedder', api_key, logger)
                elif is_local:
                    # Local endpoint (Ollama) - allow dummy key
                    logger.info(f'Creating embedder for local endpoint ({provider_name}): {api_url}')
                    if not api_key:
                        api_key = 'ollama'
                else:
                    # Cloud OpenAI-compatible provider (OpenRouter, Together, etc.) - require real key
                    logger.info(f'Creating embedder for {provider_name}: {api_url}')
                    _validate_api_key(f'{provider_name} Embedder', api_key, logger)

                from graphiti_core.embedder.openai import OpenAIEmbedderConfig

                # Madeinoz Patch v2: Include base_url for all custom endpoints
                embedder_config = OpenAIEmbedderConfig(
                    api_key=api_key,
                    embedding_model=config.model,
                    base_url=api_url if is_custom else None,
                    # Madeinoz Patch v2: Pass dimensions for custom endpoints
                    # Required for Ollama models, optional for cloud providers
                    embedding_dim=config.dimensions if is_custom else None,
                )

                if is_custom:
                    logger.info(f'Madeinoz Patch v2: Using {provider_name} for embeddings: {api_url}')
                    logger.info(f'Madeinoz Patch v2: Embedding model: {config.model}, dimensions: {config.dimensions}')

                return OpenAIEmbedder(config=embedder_config)

            case 'azure_openai':
                if not HAS_AZURE_EMBEDDER:
                    raise ValueError(
                        'Azure OpenAI embedder not available in current graphiti-core version'
                    )
                if not config.providers.azure_openai:
                    raise ValueError('Azure OpenAI provider configuration not found')
                azure_config = config.providers.azure_openai

                if not azure_config.api_url:
                    raise ValueError('Azure OpenAI API URL is required')

                # Handle Azure AD authentication if enabled
                api_key: str | None = None
                azure_ad_token_provider = None
                if azure_config.use_azure_ad:
                    logger.info(
                        'Creating Azure OpenAI Embedder client with Azure AD authentication'
                    )
                    azure_ad_token_provider = create_azure_credential_token_provider()
                else:
                    api_key = azure_config.api_key
                    _validate_api_key('Azure OpenAI Embedder', api_key, logger)

                # Create the Azure OpenAI client first
                azure_client = AsyncAzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=azure_config.api_url,
                    api_version=azure_config.api_version,
                    azure_deployment=azure_config.deployment_name,
                    azure_ad_token_provider=azure_ad_token_provider,
                )

                return AzureOpenAIEmbedderClient(
                    azure_client=azure_client,
                    model=config.model or 'text-embedding-3-small',
                )

            case 'gemini':
                if not HAS_GEMINI_EMBEDDER:
                    raise ValueError(
                        'Gemini embedder not available in current graphiti-core version'
                    )
                if not config.providers.gemini:
                    raise ValueError('Gemini provider configuration not found')

                api_key = config.providers.gemini.api_key
                _validate_api_key('Gemini Embedder', api_key, logger)

                from graphiti_core.embedder.gemini import GeminiEmbedderConfig

                gemini_config = GeminiEmbedderConfig(
                    api_key=api_key,
                    embedding_model=config.model or 'models/text-embedding-004',
                    embedding_dim=config.dimensions or 768,
                )
                return GeminiEmbedder(config=gemini_config)

            case 'voyage':
                if not HAS_VOYAGE_EMBEDDER:
                    raise ValueError(
                        'Voyage embedder not available in current graphiti-core version'
                    )
                if not config.providers.voyage:
                    raise ValueError('Voyage provider configuration not found')

                api_key = config.providers.voyage.api_key
                _validate_api_key('Voyage Embedder', api_key, logger)

                from graphiti_core.embedder.voyage import VoyageAIEmbedderConfig

                voyage_config = VoyageAIEmbedderConfig(
                    api_key=api_key,
                    embedding_model=config.model or 'voyage-3',
                    embedding_dim=config.dimensions or 1024,
                )
                return VoyageAIEmbedder(config=voyage_config)

            case 'ollama':
                # Madeinoz Patch: Ollama embedder support
                # Ollama provides an OpenAI-compatible embeddings API
                import os
                logger.info('Creating Ollama embedder client')

                # Read EMBEDDER_PROVIDER_URL directly from environment (set by container env)
                # This avoids issues with YAML variable substitution timing
                api_url = os.environ.get('EMBEDDER_PROVIDER_URL', 'http://host.docker.internal:11434')

                logger.info(f'Ollama embedder URL: {api_url}')

                from graphiti_core.embedder.openai import OpenAIEmbedderConfig

                embedder_config = OpenAIEmbedderConfig(
                    api_key='ollama',  # Dummy key for Ollama
                    embedding_model=config.model or 'mxbai-embed-large',
                    base_url=api_url,
                    embedding_dim=config.dimensions or 1024,
                )

                logger.info(f'Madeinoz Patch: Ollama embedder using model {config.model}, dimensions {config.dimensions}')
                return OpenAIEmbedder(config=embedder_config)

            case _:
                raise ValueError(f'Unsupported Embedder provider: {provider}')


class DatabaseDriverFactory:
    """Factory for creating Database drivers based on configuration.

    Note: This returns configuration dictionaries that can be passed to Graphiti(),
    not driver instances directly, as the drivers require complex initialization.
    """

    @staticmethod
    def create_config(config: DatabaseConfig) -> dict:
        """Create database configuration dictionary based on the configured provider."""
        provider = config.provider.lower()

        match provider:
            case 'neo4j':
                # Use Neo4j config if provided, otherwise use defaults
                if config.providers.neo4j:
                    neo4j_config = config.providers.neo4j
                else:
                    # Create default Neo4j configuration
                    from config.schema import Neo4jProviderConfig

                    neo4j_config = Neo4jProviderConfig()

                # Check for environment variable overrides (for CI/CD compatibility)
                import os

                uri = os.environ.get('NEO4J_URI', neo4j_config.uri)
                username = os.environ.get('NEO4J_USER', neo4j_config.username)
                password = os.environ.get('NEO4J_PASSWORD', neo4j_config.password)

                return {
                    'uri': uri,
                    'user': username,
                    'password': password,
                    # Note: database and use_parallel_runtime would need to be passed
                    # to the driver after initialization if supported
                }

            case 'falkordb':
                if not HAS_FALKOR:
                    raise ValueError(
                        'FalkorDB driver not available in current graphiti-core version'
                    )

                # Use FalkorDB config if provided, otherwise use defaults
                if config.providers.falkordb:
                    falkor_config = config.providers.falkordb
                else:
                    # Create default FalkorDB configuration
                    from config.schema import FalkorDBProviderConfig

                    falkor_config = FalkorDBProviderConfig()

                # Check for environment variable overrides (for CI/CD compatibility)
                import os
                from urllib.parse import urlparse

                uri = os.environ.get('FALKORDB_URI', falkor_config.uri)
                password = os.environ.get('FALKORDB_PASSWORD', falkor_config.password)

                # Parse the URI to extract host and port
                parsed = urlparse(uri)
                host = parsed.hostname or 'localhost'
                port = parsed.port or 6379

                return {
                    'driver': 'falkordb',
                    'host': host,
                    'port': port,
                    'password': password,
                    'database': falkor_config.database,
                }

            case _:
                raise ValueError(f'Unsupported Database provider: {provider}')
