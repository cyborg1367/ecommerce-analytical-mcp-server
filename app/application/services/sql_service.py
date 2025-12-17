from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.db.sql_safety import normalize_sql, is_readonly_sql


class SqlService:
    def sql_readonly(self, session: Session, query: str, max_rows: int, timeout_ms: int) -> dict:
        q = normalize_sql(query)
        if not is_readonly_sql(q):
            raise ValueError("sql_readonly only allows SELECT/WITH/SHOW/EXPLAIN (single statement).")

        # SET LOCAL requires an active transaction
        with session.begin():
            session.execute(text("SET LOCAL statement_timeout = :ms"), {"ms": f"{int(timeout_ms)}ms"})
            result = session.execute(text(q))
            rows = result.mappings().fetchmany(max_rows)
            return {"rows": [dict(r) for r in rows], "returned": len(rows), "max_rows": max_rows}
