"""
Rate limiting configuration for chat API.
Adjust these values based on your API costs and user limits.
"""

import os
from typing import Optional

# Read from environment variables with defaults
def get_int_env(key: str, default: int) -> int:
    """Get integer from environment variable."""
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


# Per-IP limits
MAX_QUESTIONS_PER_HOUR = get_int_env("CBB_RATE_LIMIT_HOURLY", 10)
MAX_QUESTIONS_PER_DAY = get_int_env("CBB_RATE_LIMIT_DAILY", 100)

# Global limit (across all IPs)
MAX_GLOBAL_CALLS_PER_DAY = get_int_env("CBB_RATE_LIMIT_GLOBAL", 10000)

# Enable/disable rate limiting
RATE_LIMITING_ENABLED = os.environ.get("CBB_RATE_LIMITING_ENABLED", "true").lower() == "true"

print(f"""
[Rate Limiter Config]
  Per-IP Hourly: {MAX_QUESTIONS_PER_HOUR} questions
  Per-IP Daily:  {MAX_QUESTIONS_PER_DAY} questions
  Global Daily:  {MAX_GLOBAL_CALLS_PER_DAY} calls
  Enabled:       {RATE_LIMITING_ENABLED}

Set environment variables to customize:
  CBB_RATE_LIMIT_HOURLY=10
  CBB_RATE_LIMIT_DAILY=100
  CBB_RATE_LIMIT_GLOBAL=10000
  CBB_RATE_LIMITING_ENABLED=true
""")
