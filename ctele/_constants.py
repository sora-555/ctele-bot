"""Constants pulled directly from the decompiled extension.

Every value here has a comment pointing at the original obfuscated class
it came from (see README.md for the full class-by-class writeup) so a
future reverse-engineering pass against a newer extension build can spot
what changed at a glance.
"""

from __future__ import annotations

import re

BASE_URL = "https://cosplaytele.com"  # keiyoushi.source.Generated.getBaseUrl()
SOURCE_NAME = "CosplayTele"  # keiyoushi.source.Generated.getName()

# HttpSource popular/latest page size. `h.b` (byte, value 20).
DEFAULT_PAGE_SIZE = 20

# `h.g`: Regex(".*/(tag|category)/.*") — used to pick out taxonomy links
# from an arbitrary block of anchors (both on a post's detail page, where
# it yields that post's genres, and on /explore-categories/, where it
# yields the full category list).
TAXONOMY_HREF_RE = re.compile(r".*/(tag|category)/.*")

# `o.a`: the small built-in category list used before the live
# /explore-categories/ page has been fetched (or if it fails). Returned
# by get_categories() as a fallback so the SDK is usable without a
# network round trip if you only need the common categories.
DEFAULT_CATEGORIES: list[tuple[str, str]] = [
    ("All", ""),
    ("Cosplay Nude", "category/nude"),
    ("Cosplay Ero", "category/no-nude"),
    ("Cosplay", "category/cosplay"),
]

# Default `range` query param for the popular-posts endpoint (`h.a()`).
DEFAULT_POPULAR_RANGE = "last7days"

# `h.headersBuilder()` sets Referer to "{baseUrl}/" on every request —
# most WordPress hotlink-protection plugins check this. A realistic
# desktop UA avoids naive UA-sniffing blocks; override via the client's
# `headers=` kwarg if the site ever tightens this further.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 20.0
