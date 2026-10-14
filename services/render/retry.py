from typing import Optional

PERMANENT_ERROR_KEYWORDS = {
    "file not found",
    "invalid dimensions",
    "invalid framerate",
    "unknown export preset",
    "invalid container",
    "zero candidate slices",
    "missing source",
}


class RenderRetryManager:
    """Classifies render errors into transient vs permanent and calculates exponential backoff."""

    def __init__(self, max_retries: int = 2, base_delay_sec: float = 1.0):
        self.max_retries = max_retries
        self.base_delay_sec = base_delay_sec

    def is_transient_error(self, error: Exception | str) -> bool:
        err_msg = str(error).lower()
        if any(keyword in err_msg for keyword in PERMANENT_ERROR_KEYWORDS):
            return False
        if isinstance(error, (FileNotFoundError, ValueError)):
            return False
        return True

    def should_retry(self, error: Exception | str, current_retry_count: int) -> bool:
        if current_retry_count >= self.max_retries:
            return False
        return self.is_transient_error(error)

    def compute_backoff_sec(self, current_retry_count: int) -> float:
        # Exponential backoff: 1.0s, 2.0s
        return self.base_delay_sec * (2 ** current_retry_count)
