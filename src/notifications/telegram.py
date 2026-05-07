import sys
import time
from pathlib import Path

import httpx

TELEGRAM_API_BASE = "https://api.telegram.org"
RETRY_DELAY = 5
NETWORK_KEYWORDS = [
    "connection refused", "connection reset", "dns", "timeout",
    "network", "unreachable", "could not connect",
    "cannot connect", "no route to host", "host unreachable",
    "timed out", "read operation",
]


def _is_network_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    for kw in NETWORK_KEYWORDS:
        if kw in msg:
            return True
    return False


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, timeout: float = 30):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self._base_url = f"{TELEGRAM_API_BASE}/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML",
                     verbose: bool = False) -> bool:
        url = f"{self._base_url}/sendMessage"
        body = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        last_error = None
        for attempt in (1, 2):
            try:
                response = httpx.post(url, json=body, timeout=self.timeout)
                data = response.json()
                if not data.get("ok"):
                    last_error = data.get("description", "unknown error")
                    if verbose:
                        print(f"  [telegram] sendMessage failed: {last_error}",
                              file=sys.stderr)
                    return False
                return True
            except Exception as exc:
                last_error = str(exc)
                if attempt == 1 and _is_network_error(exc):
                    if verbose:
                        print(f"  [telegram] network error, retrying...",
                              file=sys.stderr)
                    time.sleep(RETRY_DELAY)
                    continue
                if verbose:
                    print(f"  [telegram] sendMessage error: {exc}",
                          file=sys.stderr)
                return False
        return False

    def send_document(self, file_path: Path, caption: str | None = None,
                      verbose: bool = False) -> bool:
        url = f"{self._base_url}/sendDocument"
        data = {"chat_id": self.chat_id}
        if caption:
            data["caption"] = caption

        last_error = None
        for attempt in (1, 2):
            try:
                with open(file_path, "rb") as f:
                    files = {"document": (file_path.name, f)}
                    response = httpx.post(url, data=data, files=files,
                                          timeout=self.timeout)
                resp_data = response.json()
                if not resp_data.get("ok"):
                    last_error = resp_data.get("description", "unknown error")
                    if verbose:
                        print(f"  [telegram] sendDocument failed: {last_error}",
                              file=sys.stderr)
                    return False
                return True
            except Exception as exc:
                last_error = str(exc)
                if attempt == 1 and _is_network_error(exc):
                    if verbose:
                        print(f"  [telegram] network error, retrying...",
                              file=sys.stderr)
                    time.sleep(RETRY_DELAY)
                    continue
                if verbose:
                    print(f"  [telegram] sendDocument error: {exc}",
                          file=sys.stderr)
                return False
        return False
