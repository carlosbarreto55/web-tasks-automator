from selenium.common.exceptions import (
    NoSuchElementException,
    InvalidSelectorException,
    ElementNotInteractableException,
    InvalidArgumentException,
)

NETWORK_KEYWORDS = [
    "connection refused", "connection reset", "dns", "timeout",
    "network", "unreachable", "could not connect", "chrome not reachable",
    "cannot connect", "no route to host", "host unreachable",
    "err_connection", "err_name_not_resolved", "err_internet_disconnected",
]


def classify_error(exc: Exception) -> str:
    """Classify exception as 'client' (don't retry) or 'network' (do retry)."""
    if isinstance(exc, (NoSuchElementException, InvalidSelectorException,
                          ElementNotInteractableException, InvalidArgumentException)):
        return "client"
    msg = str(exc).lower()
    for kw in NETWORK_KEYWORDS:
        if kw in msg:
            return "network"
    return "client"
