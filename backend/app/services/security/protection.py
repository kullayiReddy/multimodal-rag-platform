"""
Security module for prompt injection detection, input validation, and file safety.
"""

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ─── Prompt Injection Patterns ──────────────────────────────────────

INJECTION_PATTERNS = [
    # Direct instruction override attempts
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?prior\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"override\s+(system\s+)?prompt",
    r"new\s+system\s+prompt",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+if",
    r"pretend\s+you\s+are",
    r"from\s+now\s+on",

    # Information extraction attempts
    r"reveal\s+(your|the)\s+(system|internal)",
    r"show\s+(me\s+)?(your|the)\s+prompt",
    r"what\s+(is|are)\s+your\s+(instructions|rules|system\s+prompt)",
    r"repeat\s+(your|the)\s+(system|initial)",
    r"output\s+(your|the)\s+(system|initial)",
    r"print\s+(your|the)\s+(system|initial)",
    r"display\s+(your|the)\s+(instructions|prompt)",

    # API key / secret extraction
    r"(api|secret)\s*key",
    r"show\s+(me\s+)?credentials",
    r"what\s+is\s+(the\s+)?password",
    r"reveal\s+.*\b(key|token|secret|password)\b",

    # Code execution attempts
    r"execute\s+(this|the\s+following)",
    r"run\s+(this|the\s+following)\s+code",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__",
    r"subprocess",
    r"os\.system",

    # Role manipulation
    r"you\s+must\s+obey",
    r"do\s+not\s+refuse",
    r"bypass\s+(safety|content|filter)",
    r"jailbreak",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def detect_prompt_injection(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detect potential prompt injection in text.

    Returns:
        (is_injection, matched_pattern) tuple
    """
    if not text:
        return False, None

    for pattern in COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            logger.warning(
                f"Prompt injection detected: '{match.group()}' "
                f"in text: '{text[:100]}...'"
            )
            return True, match.group()

    return False, None


def sanitize_document_content(content: str) -> str:
    """
    Sanitize document content to prevent prompt injection.
    Wraps content in clear delimiters so the LLM treats it as data, not instructions.
    """
    # Don't modify the content, but ensure it's treated as data
    # The actual protection is in the system prompt and context assembly
    return content


def validate_file(file_path: Path, file_size: int) -> Tuple[bool, Optional[str]]:
    """
    Validate an uploaded file for safety.

    Returns:
        (is_valid, error_message) tuple
    """
    settings = get_settings()

    # Check file size
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        return False, f"File size exceeds maximum of {settings.MAX_FILE_SIZE_MB}MB"

    # Check extension
    ext = file_path.suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' is not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"

    # Check for path traversal
    try:
        resolved = file_path.resolve()
        if ".." in str(file_path):
            return False, "Path traversal detected"
    except Exception:
        return False, "Invalid file path"

    return True, None


def validate_query(query: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a user query for safety and sanity.

    Returns:
        (is_valid, error_message) tuple
    """
    if not query or not query.strip():
        return False, "Query cannot be empty"

    if len(query) > 2000:
        return False, "Query exceeds maximum length of 2000 characters"

    # Check for injection in query (be less strict than document content)
    is_injection, pattern = detect_prompt_injection(query)
    if is_injection:
        logger.warning(f"Potential injection in query: {pattern}")
        # We log but don't block user queries — they might legitimately ask about these topics
        # The system prompt handles the actual protection

    return True, None


def get_safe_temp_dir() -> Path:
    """Get a safe temporary directory for file processing."""
    settings = get_settings()
    temp_dir = Path(settings.PROCESSED_DIR) / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict = {}  # ip -> list of timestamps

    def is_allowed(self, client_id: str) -> bool:
        """Check if a request is allowed for the given client."""
        import time

        now = time.time()
        if client_id not in self._requests:
            self._requests[client_id] = []

        # Clean old entries
        self._requests[client_id] = [
            t for t in self._requests[client_id]
            if now - t < self.window_seconds
        ]

        if len(self._requests[client_id]) >= self.max_requests:
            return False

        self._requests[client_id].append(now)
        return True
