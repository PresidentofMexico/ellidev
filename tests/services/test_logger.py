"""
Tests for services/logger.py

Tests the structured logging service including JSON formatting,
query audit trail, and various logging methods.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from services.logger import StructuredLogger, JSONFormatter, get_logger


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create temporary log directory"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def test_logger(temp_log_dir, monkeypatch):
    """Create test logger with temporary log files"""
    log_file = str(temp_log_dir / "test.log")
    audit_file = str(temp_log_dir / "test_audit.jsonl")

    monkeypatch.setenv("LOG_FILE", log_file)
    monkeypatch.setenv("QUERY_AUDIT_FILE", audit_file)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "json")

    logger = StructuredLogger()
    yield logger, log_file, audit_file


class TestStructuredLogger:
    """Tests for StructuredLogger class"""

    def test_logger_initialization(self, test_logger):
        """Test logger initializes with correct configuration"""
        logger, log_file, audit_file = test_logger

        assert logger.log_level == "DEBUG"
        assert logger.log_format == "json"
        assert logger.log_file == log_file
        assert logger.query_audit_file == audit_file

    def test_info_logging(self, test_logger):
        """Test INFO level logging"""
        logger, log_file, _ = test_logger

        logger.info("Test message", extra_field="value")

        # Read log file
        with open(log_file, 'r') as f:
            log_line = f.read()

        assert "Test message" in log_line
        assert "INFO" in log_line

    def test_error_logging(self, test_logger):
        """Test ERROR level logging"""
        logger, log_file, _ = test_logger

        logger.error("Error occurred", error_code=500)

        with open(log_file, 'r') as f:
            log_line = f.read()

        assert "Error occurred" in log_line
        assert "ERROR" in log_line

    def test_log_query(self, test_logger):
        """Test query logging to audit trail"""
        logger, _, audit_file = test_logger

        logger.log_query(
            user_id="U12345",
            channel_id="C67890",
            query="What opportunities are open?",
            query_type="rag_search",
            duration_ms=245.3,
            success=True,
            sources_used=["salesforce_record", "document"],
            results_count=3
        )

        # Read audit log
        with open(audit_file, 'r') as f:
            audit_line = f.readline()
            audit_data = json.loads(audit_line)

        assert audit_data["user_id"] == "U12345"
        assert audit_data["channel_id"] == "C67890"
        assert audit_data["query_type"] == "rag_search"
        assert audit_data["duration_ms"] == 245.3
        assert audit_data["success"] is True
        assert "salesforce_record" in audit_data["sources_used"]
        assert audit_data["results_count"] == 3

    def test_log_query_failure(self, test_logger):
        """Test query logging for failed queries"""
        logger, _, audit_file = test_logger

        logger.log_query(
            user_id="U12345",
            channel_id="C67890",
            query="Show me revenue",
            query_type="direct_ai",
            duration_ms=123.4,
            success=False,
            error="ConnectionError: Could not connect to Snowflake"
        )

        with open(audit_file, 'r') as f:
            audit_line = f.readline()
            audit_data = json.loads(audit_line)

        assert audit_data["success"] is False
        assert "ConnectionError" in audit_data["error"]

    def test_log_api_call_success(self, test_logger):
        """Test successful API call logging"""
        logger, log_file, _ = test_logger

        logger.log_api_call(
            service="salesforce",
            method="search_opportunities",
            duration_ms=156.8,
            success=True,
            context={"company_name": "Acme Corp", "results_count": 2}
        )

        with open(log_file, 'r') as f:
            log_content = f.read()

        assert "salesforce" in log_content
        assert "search_opportunities" in log_content
        assert "succeeded" in log_content.lower()

    def test_log_api_call_failure(self, test_logger):
        """Test failed API call logging"""
        logger, log_file, _ = test_logger

        logger.log_api_call(
            service="snowflake",
            method="cortex.complete",
            duration_ms=234.5,
            success=False,
            error="TimeoutError: Request timed out"
        )

        with open(log_file, 'r') as f:
            log_content = f.read()

        assert "snowflake" in log_content
        assert "failed" in log_content.lower()
        assert "TimeoutError" in log_content

    def test_log_rag_search(self, test_logger):
        """Test RAG search logging"""
        logger, log_file, _ = test_logger

        logger.log_rag_search(
            query="What are our payment terms?",
            sources_found=3,
            relevance_scores=[0.95, 0.87, 0.76],
            duration_ms=187.5,
            search_types=["document", "salesforce_record"]
        )

        with open(log_file, 'r') as f:
            log_content = f.read()

        assert "RAG search" in log_content
        assert "3 sources found" in log_content

    def test_log_error_with_exception(self, test_logger):
        """Test error logging with exception object"""
        logger, log_file, _ = test_logger

        try:
            raise ValueError("Invalid value provided")
        except ValueError as e:
            logger.log_error(e, context={"user_id": "U12345", "query": "Test query"})

        with open(log_file, 'r') as f:
            log_content = f.read()

        assert "ValueError" in log_content
        assert "Invalid value provided" in log_content
        assert "stack_trace" in log_content.lower() or "traceback" in log_content.lower()

    def test_log_workflow(self, test_logger):
        """Test workflow logging"""
        logger, log_file, _ = test_logger

        logger.log_workflow(
            workflow_type="salesforce_update",
            user_id="U12345",
            action="update_opportunity_stage",
            success=True,
            duration_ms=178.4,
            details={"opp_id": "006xx", "opp_name": "Acme Corp", "new_stage": "Closed Won"}
        )

        with open(log_file, 'r') as f:
            log_content = f.read()

        assert "salesforce_update" in log_content
        assert "succeeded" in log_content.lower()

    def test_log_memory_operation(self, test_logger):
        """Test memory operation logging"""
        logger, log_file, _ = test_logger

        logger.log_memory_operation(
            operation="summarize",
            user_id="U12345",
            thread_id="1234567890.123456",
            success=True,
            details={"memory_id": "mem_abc123", "message_count": 10}
        )

        with open(log_file, 'r') as f:
            log_content = f.read()

        assert "Memory summarize" in log_content or "summarize" in log_content

    def test_query_truncation(self, test_logger):
        """Test that long queries are truncated"""
        logger, _, audit_file = test_logger

        long_query = "A" * 1000

        logger.log_query(
            user_id="U12345",
            channel_id="C67890",
            query=long_query,
            query_type="rag_search",
            duration_ms=100.0,
            success=True
        )

        with open(audit_file, 'r') as f:
            audit_line = f.readline()
            audit_data = json.loads(audit_line)

        # Should be truncated to 500 chars
        assert len(audit_data["query"]) <= 500


class TestJSONFormatter:
    """Tests for JSONFormatter class"""

    def test_json_format_basic(self):
        """Test basic JSON formatting"""
        import logging

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed

    def test_json_format_with_extra_fields(self):
        """Test JSON formatting with extra fields"""
        import logging

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=None
        )
        record.user_id = "U12345"
        record.error_code = 500

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["user_id"] == "U12345"
        assert parsed["error_code"] == 500


class TestGetLogger:
    """Tests for get_logger singleton function"""

    def test_get_logger_singleton(self):
        """Test that get_logger returns singleton instance"""
        logger1 = get_logger()
        logger2 = get_logger()

        assert logger1 is logger2

    def test_get_logger_returns_structured_logger(self):
        """Test that get_logger returns StructuredLogger instance"""
        logger = get_logger()

        assert isinstance(logger, StructuredLogger)


@pytest.mark.integration
class TestLoggerIntegration:
    """Integration tests for logger with actual file I/O"""

    def test_multiple_queries_logged(self, test_logger):
        """Test logging multiple queries"""
        logger, _, audit_file = test_logger

        for i in range(5):
            logger.log_query(
                user_id=f"U{i}",
                channel_id="C67890",
                query=f"Query {i}",
                query_type="rag_search",
                duration_ms=100.0 + i,
                success=True
            )

        with open(audit_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 5

        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["user_id"] == f"U{i}"
            assert data["query"] == f"Query {i}"

    def test_concurrent_logging(self, test_logger):
        """Test that logger handles concurrent writes"""
        logger, log_file, _ = test_logger

        # Simulate concurrent logging
        for i in range(10):
            logger.info(f"Message {i}", extra=f"value{i}")
            logger.error(f"Error {i}", code=i)

        with open(log_file, 'r') as f:
            content = f.read()

        # Check that all messages are present
        for i in range(10):
            assert f"Message {i}" in content
            assert f"Error {i}" in content
