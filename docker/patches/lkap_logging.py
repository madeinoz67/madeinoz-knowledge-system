"""
LKAP Logging Configuration (Feature 022)
Local Knowledge Augmentation Platform

Basic logging infrastructure for errors and ingestion status (FR-036a).
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Configuration from environment
LOG_LEVEL = os.getenv("MADEINOZ_KNOWLEDGE_RAGFLOW_LOG_LEVEL", "INFO")
LOG_PATH = os.getenv("RAGFLOW_LOG_PATH", "/ragflow/logs/ragflow.log")


def setup_lkap_logging():
    """
    Configure logging for LKAP services.

    Creates:
    - Console handler for development
    - File handler for persistence (rotating)
    - Separate loggers for each component
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(LOG_PATH)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # Console handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)

    # File handler with rotation (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Component-specific loggers
    loggers = {
        "lkap.ingestion": "Document ingestion processing",
        "lkap.classification": "Progressive classification service",
        "lkap.promotion": "Evidence-to-KG promotion",
        "lkap.ragflow": "RAGFlow client operations",
        "lkap.embeddings": "Embedding generation",
        "lkap.chunking": "Document chunking",
    }

    for logger_name, description in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.info(f"Initialized: {description}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific LKAP component.

    Args:
        name: Logger name (e.g., "lkap.ingestion")

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class IngestionMetrics:
    """Track ingestion metrics for logging"""

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self.start_time = datetime.now()
        self.chunks_processed = 0
        self.chunks_total = 0
        self.errors = []

    def add_error(self, error: str):
        """Record an error during ingestion"""
        self.errors.append(error)

    def set_chunks_total(self, total: int):
        """Set expected total chunks"""
        self.chunks_total = total

    def increment_chunks(self):
        """Increment processed chunks counter"""
        self.chunks_processed += 1

    def get_summary(self) -> dict:
        """Get ingestion summary as dictionary"""
        duration = (datetime.now() - self.start_time).total_seconds()

        return {
            "doc_id": self.doc_id,
            "duration_seconds": duration,
            "chunks_processed": self.chunks_processed,
            "chunks_total": self.chunks_total,
            "errors": self.errors,
            "success": len(self.errors) == 0,
        }

    def log_summary(self, logger: logging.Logger):
        """Log ingestion summary"""
        summary = self.get_summary()

        if summary["success"]:
            logger.info(
                f"Ingestion complete for {self.doc_id}: "
                f"{summary['chunks_processed']}/{summary['chunks_total']} chunks "
                f"in {summary['duration_seconds']:.1f}s"
            )
        else:
            logger.error(
                f"Ingestion failed for {self.doc_id}: "
                f"{len(summary['errors'])} errors, "
                f"{summary['chunks_processed']}/{summary['chunks_total']} chunks processed"
            )
            for error in summary["errors"]:
                logger.error(f"  - {error}")


# Initialize logging on module import
setup_lkap_logging()
