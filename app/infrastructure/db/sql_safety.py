from __future__ import annotations

READ_ONLY_START = ("select", "with", "show", "explain")


def normalize_sql(sql: str) -> str:
    s = (sql or "").strip()
    while s.endswith(";"):
        s = s[:-1].rstrip()
    if ";" in s:
        raise ValueError("Only a single SQL statement is allowed (no internal semicolons).")
    return s


def is_readonly_sql(sql: str) -> bool:
    s = normalize_sql(sql).lower()
    if not s:
        return False
    first = s.split(None, 1)[0]
    return first in READ_ONLY_START
