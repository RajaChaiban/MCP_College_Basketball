"""
Rate limiting for chat API calls.
Limits questions per IP address to prevent abuse and control costs.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Tuple

# Import configuration
from dashboard.config.rate_limits import (
    MAX_QUESTIONS_PER_HOUR,
    MAX_QUESTIONS_PER_DAY,
    MAX_GLOBAL_CALLS_PER_DAY,
    RATE_LIMITING_ENABLED,
)

# Tracking
ip_questions = defaultdict(list)  # {ip: [timestamp, timestamp, ...]}
global_calls_today = 0
global_lock = Lock()
reset_date = datetime.now().date()


def get_client_ip(request) -> str:
    """Extract client IP from Flask request."""
    # Handle X-Forwarded-For header (for proxies/Railway)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or "unknown"


def check_rate_limit(user_ip: str) -> Tuple[bool, str]:
    """
    Check if user exceeded rate limits.

    Returns:
        (allowed: bool, message: str)
    """
    global global_calls_today, reset_date

    # Skip rate limiting if disabled
    if not RATE_LIMITING_ENABLED:
        return True, "OK"

    now = datetime.now()

    # --- Per-IP Hourly Limit ---
    one_hour_ago = now - timedelta(hours=1)
    ip_questions[user_ip] = [
        q_time for q_time in ip_questions[user_ip]
        if q_time > one_hour_ago
    ]

    if len(ip_questions[user_ip]) >= MAX_QUESTIONS_PER_HOUR:
        oldest_question = min(ip_questions[user_ip])
        retry_time = oldest_question + timedelta(hours=1)
        minutes_until = max(1, (retry_time - now).seconds // 60)
        return False, f"Rate limit: {MAX_QUESTIONS_PER_HOUR} questions/hour. Try again in ~{minutes_until} minutes."

    # --- Per-IP Daily Limit ---
    one_day_ago = now - timedelta(days=1)
    daily_questions = [
        q_time for q_time in ip_questions[user_ip]
        if q_time > one_day_ago
    ]

    if len(daily_questions) >= MAX_QUESTIONS_PER_DAY:
        return False, f"Daily limit reached: {MAX_QUESTIONS_PER_DAY} questions/day. Come back tomorrow!"

    # --- Global Daily Limit ---
    with global_lock:
        # Reset counter daily
        if datetime.now().date() > reset_date:
            global_calls_today = 0
            reset_date = datetime.now().date()

        if global_calls_today >= MAX_GLOBAL_CALLS_PER_DAY:
            return False, "Server rate limit reached. Please try again later or come back tomorrow."

        global_calls_today += 1
        ip_questions[user_ip].append(now)

    return True, "OK"


def get_remaining_questions(user_ip: str) -> dict:
    """Get remaining question count for user."""
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)

    hourly = len([q for q in ip_questions[user_ip] if q > one_hour_ago])
    daily = len([q for q in ip_questions[user_ip] if q > one_day_ago])

    return {
        "hourly_remaining": max(0, MAX_QUESTIONS_PER_HOUR - hourly),
        "hourly_limit": MAX_QUESTIONS_PER_HOUR,
        "daily_remaining": max(0, MAX_QUESTIONS_PER_DAY - daily),
        "daily_limit": MAX_QUESTIONS_PER_DAY,
    }


def reset_ip_limit(user_ip: str) -> None:
    """Reset rate limit for specific IP (admin only)."""
    if user_ip in ip_questions:
        del ip_questions[user_ip]
