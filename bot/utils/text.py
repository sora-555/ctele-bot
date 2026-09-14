from html import escape
def safe(value): return escape(str(value or ''))
