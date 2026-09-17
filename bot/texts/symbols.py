"""Approved Telegram UI glyphs (see telegram_skills.md).

Every glyph is declared as an escape sequence so all source files stay pure
ASCII; call sites import names instead of pasting characters.
"""

HEADER = "\u2756"
SECTION = "\u2726"
FEATURE = "\u2726"
BULLET = "\u2022"
SUB = "\u25aa"
DOT = "\u00b7"
RULE_CHAR = "\u2501"
RULE = RULE_CHAR * 20

PREV = "\u2039"
NEXT = "\u203a"
FIRST = "\u00ab"
LAST = "\u00bb"

STAR = "\u2606"
STAR_ON = "\u2605"

CHECK = "\u2713"
CROSS = "\u2715"
ACTIVE = "\u25c6"
PENDING = "\u25c7"
DOWNLOAD = "\u21e9"
JUMP = "\u2197"

TABS_ON = "\u25c6"
TABS_OFF = "\u25c7"
