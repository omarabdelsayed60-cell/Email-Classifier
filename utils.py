import re
from typing import Callable, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from logger import logger


def clean_text(text: Any) -> str:
    """Sanitizes text by stripping whitespace and non-printable characters."""
    if not isinstance(text, str):
        return ""
    # Strip extra whitespace and line breaks
    cleaned = text.strip()
    cleaned = re.sub(r"\r\n", "\n", cleaned)
    return cleaned


def create_retry_decorator(
    max_attempts: int = 3, min_seconds: int = 2, max_seconds: int = 10
) -> Callable:
    """Creates a tenacity retry decorator for API calls with exponential backoff."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_seconds, max=max_seconds),
        before_sleep=lambda retry_state: logger.warning(
            f"API call failed. Retrying in {retry_state.next_action.sleep} seconds... (Attempt {retry_state.attempt_number}/{max_attempts})"
        ),
        reraise=True,
    )


def detect_email_columns(columns: list) -> tuple[str | None, str | None]:
    """Helper to detect probable Subject and Body columns in an uploaded file."""
    subject_col = None
    body_col = None

    col_lower = [str(c).strip().lower() for c in columns]

    # Detect subject column
    for original, lowered in zip(columns, col_lower):
        if "subject" in lowered or "title" in lowered or "header" in lowered:
            subject_col = original
            break

    # Detect body column
    for original, lowered in zip(columns, col_lower):
        if (
            "body" in lowered
            or "text" in lowered
            or "content" in lowered
            or "message" in lowered
            or "email" in lowered
            or "description" in lowered
        ):
            body_col = original
            break

    return subject_col, body_col
