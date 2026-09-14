"""Exception hierarchy for the ctele SDK.

Kept small and specific on purpose so callers embedding this in a FastAPI
route or an aiogram handler can catch precisely what they care about:

    try:
        post = await ctele.get_post(url)
    except RequestError as e:
        # network / HTTP-status problem — safe to retry or show "site down"
        ...
    except ParseError as e:
        # the page loaded fine but didn't look like a CosplayTele post —
        # usually means the site's markup changed
        ...
"""

from __future__ import annotations


class CTeleError(Exception):
    """Base class for every error raised by this SDK."""


class RequestError(CTeleError):
    """Raised when an HTTP request fails or returns a non-2xx status."""

    def __init__(self, message: str, *, url: str, status_code: int | None = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        base = super().__str__()
        if self.status_code is not None:
            return f"{base} (status={self.status_code}, url={self.url})"
        return f"{base} (url={self.url})"


class ParseError(CTeleError):
    """Raised when expected content couldn't be found in a fetched page.

    Almost always means CosplayTele changed its HTML structure and the
    CSS selectors in ``ctele.parsing`` need to be updated.
    """

    def __init__(self, message: str, *, url: str):
        super().__init__(message)
        self.url = url

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{super().__str__()} (url={self.url})"
