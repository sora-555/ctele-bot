"""Approved Unicode UI symbols.

The bot never uses emoji for decoration or structure - only the glyphs below,
each with a fixed semantic meaning (see AGENTS.md).
"""

HEADER = "\u2756"
SECTION = "\u2726"
ITEM = "\u25b8"
SUCCESS = "\u2713"
CHECK = "\u2714"
IMPORTANT = "\u25c6"
PENDING = "\u25c7"
INACTIVE = "\u25cb"
ACCENT = "\u27e1"
PREV = "\u2039"
NEXT = "\u203a"
LEFT = "\u00ab"
RIGHT = "\u00bb"

SEPARATOR = "\u2501" * 20
BULLET = "\u00b7"
KV = "\u00b7"
TREE_BRANCH = "\u251c\u2500"
TREE_LAST = "\u2514\u2500"

ALERT_OPEN = "\u3010"
ALERT_CLOSE = "\u3011"


def header(text: str) -> str:
    return f"{HEADER} {text}"


def section(text: str) -> str:
    return f"{SECTION} {text}"


def item(label: str, value: object) -> str:
    return f"{ITEM} {label} {KV} {value}"


def alert(text: str) -> str:
    return f"{ALERT_OPEN} {text} {ALERT_CLOSE}"


def card(title: str, body: str) -> str:
    return f"{header(title)}\n{SEPARATOR}\n\n{body}\n\n{SEPARATOR}"