import os
import time

import httpx

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


class AIClient:
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class OpenAIClient(AIClient):
    def __init__(self, model: str, base_url: str | None = None,
                 api_key: str | None = None, timeout: float = 120):
        self.model = model
        self.base_url = (base_url or "https://opencode.ai/zen/go/v1").rstrip("/")
        self.api_key = api_key or os.getenv("OPENCODE_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        self.timeout = timeout

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        last_error = None
        for attempt in (1, 2):
            try:
                response = httpx.post(url, json=body, headers=headers,
                                      timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as exc:
                last_error = exc
                if attempt == 1 and _is_network_error(exc):
                    time.sleep(RETRY_DELAY)
                    continue
                raise RuntimeError(f"AI API call failed: {exc}") from exc

        raise RuntimeError(f"AI API call failed after retry: {last_error}")


class OllamaClient(AIClient):
    def __init__(self, model: str, base_url: str | None = None,
                 timeout: float = 120):
        self.model = model
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.timeout = timeout

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/api/chat"
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }

        last_error = None
        for attempt in (1, 2):
            try:
                response = httpx.post(url, json=body, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]
            except Exception as exc:
                last_error = exc
                if attempt == 1 and _is_network_error(exc):
                    time.sleep(RETRY_DELAY)
                    continue
                raise RuntimeError(f"Ollama API call failed: {exc}") from exc

        raise RuntimeError(f"Ollama API call failed after retry: {last_error}")
