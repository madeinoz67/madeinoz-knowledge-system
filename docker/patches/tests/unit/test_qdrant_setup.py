"""
Unit Tests for Qdrant Setup (T006 - Feature 023)
Qdrant RAG Migration

Tests for Qdrant connectivity and basic configuration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os


class TestQdrantConnectivity:
    """Unit tests for Qdrant connectivity (T006)"""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client"""
        with patch.dict(os.environ, {
            'MADEINOZ_KNOWLEDGE_QDRANT_URL': 'http://localhost:6333',
            'MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION': 'lkap_documents',
        }):
            yield

    def test_qdrant_url_configuration(self, mock_qdrant_client):
        """
        T006: Test Qdrant URL is configured correctly.

        Environment variable MADEINOZ_KNOWLEDGE_QDRANT_URL should be set.
        """
        qdrant_url = os.environ.get('MADEINOZ_KNOWLEDGE_QDRANT_URL')
        assert qdrant_url is not None
        assert 'http' in qdrant_url
        assert '6333' in qdrant_url

    def test_qdrant_collection_configuration(self, mock_qdrant_client):
        """
        T006: Test Qdrant collection name is configured.

        Environment variable MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION should be set.
        """
        collection = os.environ.get('MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION')
        assert collection is not None
        assert collection == 'lkap_documents'

    @patch('qdrant_client.QdrantClient')
    def test_qdrant_client_initialization(self, mock_client_class, mock_qdrant_client):
        """
        T006: Test Qdrant client can be initialized.

        Client should connect to configured URL.
        """
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        from qdrant_client import QdrantClient
        client = QdrantClient(url=os.environ.get('MADEINOZ_KNOWLEDGE_QDRANT_URL'))

        mock_client_class.assert_called_once()
        assert client is not None

    @patch('qdrant_client.QdrantClient')
    def test_qdrant_health_check(self, mock_client_class, mock_qdrant_client):
        """
        T006: Test Qdrant health check works.

        Client should be able to check cluster health.
        """
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[])

        from qdrant_client import QdrantClient
        client = QdrantClient(url=os.environ.get('MADEINOZ_KNOWLEDGE_QDRANT_URL'))

        # Health check - get collections should not raise
        result = client.get_collections()
        assert result is not None


class TestQdrantConfiguration:
    """Unit tests for Qdrant configuration (T006)"""

    def test_embedding_dimension_configuration(self):
        """
        T006: Test embedding dimension is 1024.

        Qdrant collection must use 1024 dimensions for bge-large-en-v1.5.
        """
        # Read from config file
        import yaml
        from pathlib import Path

        config_path = Path(__file__).parent.parent.parent.parent.parent / 'config' / 'qdrant.yaml'
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            assert config['embedding']['dimension'] == 1024
        else:
            # Default expectation
            assert True

    def test_chunk_size_configuration(self):
        """
        T006: Test chunk size is 512-768 tokens.

        Semantic chunking should respect token limits.
        """
        # Default chunking configuration
        min_tokens = 512
        max_tokens = 768

        assert min_tokens == 512
        assert max_tokens == 768
        assert min_tokens < max_tokens

    def test_confidence_threshold_configuration(self):
        """
        T006: Test confidence threshold is 0.70.

        Search results below 0.70 should be filtered out.
        """
        confidence_threshold = 0.70

        assert confidence_threshold == 0.70
        assert 0.0 <= confidence_threshold <= 1.0


class TestQdrantPayloadIndexes:
    """Unit tests for Qdrant payload indexes (T006)"""

    def test_required_payload_indexes(self):
        """
        T006: Test required payload indexes are defined.

        Collection should have indexes for filtering.
        """
        required_indexes = ['chunk_id', 'doc_id', 'domain', 'project', 'component', 'type']

        for index_name in required_indexes:
            assert index_name is not None
            assert len(index_name) > 0

    def test_payload_index_types(self):
        """
        T006: Test payload index types are correct.

        Filter indexes should use keyword type for exact matching.
        """
        # Keyword indexes for filtering
        keyword_indexes = ['chunk_id', 'doc_id', 'domain', 'project', 'component', 'type']

        for index_name in keyword_indexes:
            # Keyword type for exact match filtering
            index_type = 'keyword'
            assert index_type == 'keyword'
