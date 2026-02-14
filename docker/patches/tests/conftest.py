"""
Pytest configuration and fixtures for LKAP tests (Feature 022)
Local Knowledge Augmentation Platform
"""

import pytest
import os
import tempfile
from pathlib import Path


@pytest.fixture
def temp_inbox():
    """Temporary inbox directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        inbox = Path(tmpdir) / "inbox"
        inbox.mkdir()
        yield inbox


@pytest.fixture
def temp_processed():
    """Temporary processed directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        processed = Path(tmpdir) / "processed"
        processed.mkdir()
        yield processed


@pytest.fixture
def sample_document(temp_inbox):
    """Create a sample document for testing"""
    doc_path = temp_inbox / "test_document.txt"
    doc_path.write_text(
        "This is a test document for LKAP unit tests. "
        "It contains technical content about microcontrollers "
        "and GPIO configuration for embedded systems."
    )
    return doc_path


# Testcontainers configuration for integration tests
def pytest_configure(config):
    """Pytest configuration"""
    # LKAP environment variables for testing
    os.environ.setdefault("LKAP_INBOX_PATH", "/tmp/test_inbox")
    os.environ.setdefault("LKAP_PROCESSED_PATH", "/tmp/test_processed")
    os.environ.setdefault("MADEINOZ_KNOWLEDGE_QDRANT_URL", "http://localhost:6333")
    os.environ.setdefault("MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION", "test_documents")
    # Embedding configuration (reuses existing Graphiti variables)
    os.environ.setdefault("MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER_URL", "http://localhost:11434")
    os.environ.setdefault("MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER", "ollama")
    os.environ.setdefault("MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL", "bge-large-en-v1.5")
    os.environ.setdefault("MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS", "1024")
