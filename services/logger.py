"""
Structured logging service for Elli application.

Provides centralized logging with JSON output for production monitoring,
query audit trails, and comprehensive error tracking.

Phase 7.1: Structured Logging Framework
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


class StructuredLogger:
    """
    Structured logging with JSON output for production monitoring.

    Features:
    - JSON-formatted logs for easy parsing and monitoring
    - Query audit trail for all user interactions
    - API call tracking with duration and success status
    - RAG search logging with relevance scores
    - Comprehensive error logging with context
    """

    def __init__(self):
        """Initialize structured logger with configuration from environment"""
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("LOG_FORMAT", "json")  # 'json' or 'text'
        self.log_file = os.getenv("LOG_FILE", "logs/elli.log")
        self.query_audit_file = os.getenv("QUERY_AUDIT_FILE", "logs/query_audit.jsonl")

        # Create logs directory if it doesn't exist
        log_dir = Path(self.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Setup main logger
        self.logger = self._setup_logger("elli", self.log_file)

        # Setup query audit logger (always JSON lines format)
        self.audit_logger = self._setup_audit_logger()

    def _setup_logger(self, name: str, log_file: str) -> logging.Logger:
        """Setup logger with appropriate format and handlers"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, self.log_level))

        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.log_level))

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, self.log_level))

        # Set formatter based on configuration
        if self.log_format == "json":
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def _setup_audit_logger(self) -> logging.Logger:
        """Setup separate logger for query audit trail (always JSON lines)"""
        audit_logger = logging.getLogger("elli.audit")
        audit_logger.setLevel(logging.INFO)
        audit_logger.handlers.clear()

        # Create audit log directory
        audit_dir = Path(self.query_audit_file).parent
        audit_dir.mkdir(parents=True, exist_ok=True)

        # File handler for audit trail
        audit_handler = logging.FileHandler(self.query_audit_file)
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(JSONLinesFormatter())

        audit_logger.addHandler(audit_handler)
        audit_logger.propagate = False  # Don't propagate to root logger

        return audit_logger

    def info(self, message: str, **kwargs):
        """Log info message with optional context"""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with optional context"""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with optional context"""
        self.logger.error(message, extra=kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with optional context"""
        self.logger.debug(message, extra=kwargs)

    def log_query(
        self,
        user_id: str,
        channel_id: str,
        query: str,
        query_type: str,
        duration_ms: float,
        success: bool,
        sources_used: Optional[List[str]] = None,
        results_count: Optional[int] = None,
        error: Optional[str] = None
    ):
        """
        Log user query to audit trail.

        Args:
            user_id: Slack user ID
            channel_id: Slack channel/thread ID
            query: User's query text
            query_type: Type of query (rag_search, direct_ai, salesforce_update)
            duration_ms: Query processing duration in milliseconds
            success: Whether query succeeded
            sources_used: List of source types used (e.g., ["document", "salesforce_record"])
            results_count: Number of results returned
            error: Error message if query failed
        """
        audit_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "channel_id": channel_id,
            "query": query[:500],  # Truncate long queries
            "query_type": query_type,
            "duration_ms": round(duration_ms, 2),
            "success": success,
            "sources_used": sources_used or [],
            "results_count": results_count,
            "error": error
        }

        self.audit_logger.info(json.dumps(audit_data))

        # Also log to main logger at INFO level
        status = "succeeded" if success else "failed"
        self.logger.info(
            f"Query {status}: {query[:100]}...",
            extra={
                "user_id": user_id,
                "query_type": query_type,
                "duration_ms": duration_ms,
                "success": success
            }
        )

    def log_api_call(
        self,
        service: str,
        method: str,
        duration_ms: float,
        success: bool,
        error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log external API call.

        Args:
            service: Service name (salesforce, snowflake, slack)
            method: Method/endpoint called
            duration_ms: Call duration in milliseconds
            success: Whether call succeeded
            error: Error message if call failed
            context: Additional context (request params, response size, etc.)
        """
        log_data = {
            "service": service,
            "method": method,
            "duration_ms": round(duration_ms, 2),
            "success": success,
            "error": error,
            **(context or {})
        }

        status = "succeeded" if success else "failed"
        level = logging.INFO if success else logging.ERROR

        self.logger.log(
            level,
            f"API call {status}: {service}.{method} ({duration_ms:.0f}ms)",
            extra=log_data
        )

    def log_rag_search(
        self,
        query: str,
        sources_found: int,
        relevance_scores: List[float],
        duration_ms: float,
        search_types: Optional[List[str]] = None
    ):
        """
        Log RAG search operation.

        Args:
            query: Search query
            sources_found: Number of sources retrieved
            relevance_scores: Relevance scores of retrieved sources
            duration_ms: Search duration in milliseconds
            search_types: Types of sources found (document, salesforce_record, memory)
        """
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0

        self.logger.info(
            f"RAG search: {sources_found} sources found (avg relevance: {avg_relevance:.2%})",
            extra={
                "query": query[:200],
                "sources_found": sources_found,
                "avg_relevance": round(avg_relevance, 4),
                "max_relevance": round(max(relevance_scores), 4) if relevance_scores else 0,
                "min_relevance": round(min(relevance_scores), 4) if relevance_scores else 0,
                "duration_ms": round(duration_ms, 2),
                "search_types": search_types or []
            }
        )

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log error with full context for debugging.

        Args:
            error: Exception that occurred
            context: Additional context (user_id, query, service, etc.)
        """
        import traceback

        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            **(context or {})
        }

        self.logger.error(
            f"Error: {type(error).__name__}: {str(error)}",
            extra=error_data
        )

    def log_workflow(
        self,
        workflow_type: str,
        user_id: str,
        action: str,
        success: bool,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log workflow execution (Salesforce updates, etc.).

        Args:
            workflow_type: Type of workflow (salesforce_update, opportunity_create)
            user_id: User who triggered workflow
            action: Specific action taken
            success: Whether workflow succeeded
            duration_ms: Workflow duration in milliseconds
            details: Additional workflow details
        """
        status = "succeeded" if success else "failed"

        self.logger.info(
            f"Workflow {status}: {workflow_type}.{action}",
            extra={
                "workflow_type": workflow_type,
                "user_id": user_id,
                "action": action,
                "success": success,
                "duration_ms": round(duration_ms, 2),
                **(details or {})
            }
        )

    def log_memory_operation(
        self,
        operation: str,
        user_id: str,
        thread_id: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log semantic memory operations (summarization, retrieval).

        Args:
            operation: Operation type (summarize, retrieve, store)
            user_id: User associated with memory
            thread_id: Thread ID
            success: Whether operation succeeded
            details: Additional details (message_count, memories_found, etc.)
        """
        self.logger.info(
            f"Memory {operation}: {thread_id}",
            extra={
                "operation": operation,
                "user_id": user_id,
                "thread_id": thread_id,
                "success": success,
                **(details or {})
            }
        )


class JSONFormatter(logging.Formatter):
    """Format log records as JSON"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in ["name", "msg", "args", "created", "filename", "funcName",
                              "levelname", "levelno", "lineno", "module", "msecs",
                              "message", "pathname", "process", "processName",
                              "relativeCreated", "thread", "threadName", "exc_info",
                              "exc_text", "stack_info"]:
                    log_data[key] = value

        return json.dumps(log_data)


class JSONLinesFormatter(logging.Formatter):
    """Format log records as JSON Lines (one JSON object per line)"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string (no newline added by formatter)"""
        # The message is already JSON from log_query()
        return record.getMessage()


# Singleton instance
_logger_instance: Optional[StructuredLogger] = None


def get_logger() -> StructuredLogger:
    """
    Get singleton logger instance.

    Returns:
        StructuredLogger: Singleton logger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StructuredLogger()
    return _logger_instance


# Convenience exports
logger = get_logger()
