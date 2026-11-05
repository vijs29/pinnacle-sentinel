"""Pushover alert for failed or missed scheduled jobs.

Best-effort and fail-silent: a delivery problem must never break or mask the job that triggered it.
No-op when PUSHOVER_USER_KEY / PUSHOVER_APP_TOKEN are not set (local development).
Day Close (pinnacle-infra) separately checks data freshness every night and offers an approval link
for a fix; this alert only makes sure a failure is heard about the same morning.
"""
import logging
import os
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def send_push(title: str, message: str, priority: int = 1) -> bool:
    user, token = os.getenv("PUSHOVER_USER_KEY"), os.getenv("PUSHOVER_APP_TOKEN")
    if not user or not token:
        return False
    try:
        data = urllib.parse.urlencode({"token": token, "user": user, "title": title[:250],
                                       "message": message[:1000], "priority": priority}).encode()
        urllib.request.urlopen(urllib.request.Request(PUSHOVER_URL, data=data), timeout=10)
        return True
    except Exception as e:
        logger.warning(f"alerts: push failed: {e}")
        return False
