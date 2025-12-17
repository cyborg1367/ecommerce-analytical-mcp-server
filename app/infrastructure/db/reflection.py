from __future__ import annotations

from functools import lru_cache

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


class SchemaReflection:
    def __init__(self, engine: Engine, schema: str = "public"):
        self.engine = engine
        self.schema = schema

    def clear_cache(self) -> None:
        self.table_exists.cache_clear()
        self.relation_exists.cache_clear()
        self.columns_for.cache_clear()
        self.generated_columns.cache_clear()

    @lru_cache(maxsize=256)
    def table_exists(self, table: str) -> bool:
        insp = inspect(self.engine)
        return table in insp.get_table_names(schema=self.schema)

    @lru_cache(maxsize=256)
    def relation_exists(self, name: str) -> bool:
        insp = inspect(self.engine)
        return (name in insp.get_table_names(schema=self.schema)) or (name in insp.get_view_names(schema=self.schema))

    def list_tables(self) -> list[str]:
        insp = inspect(self.engine)
        return sorted(insp.get_table_names(schema=self.schema))

    def describe_table(self, table: str) -> list[dict]:
        insp = inspect(self.engine)
        cols = insp.get_columns(table, schema=self.schema)
        out = []
        for c in cols:
            out.append(
                {
                    "column": c.get("name"),
                    "type": str(c.get("type")),
                    "nullable": str(bool(c.get("nullable"))),
                    "default": c.get("default"),
                }
            )
        return out

    @lru_cache(maxsize=256)
    def columns_for(self, table: str) -> set[str]:
        insp = inspect(self.engine)
        cols = insp.get_columns(table, schema=self.schema)
        return {c["name"] for c in cols}

    def require_tables(self, *tables: str) -> None:
        missing = [t for t in tables if not self.table_exists(t)]
        if missing:
            raise RuntimeError(
                "Missing required tables in schema 'public': " + ", ".join(missing) + ". "
                "Create your schema first, then retry."
            )

    def pick_col(self, table: str, candidates: tuple[str, ...]) -> str:
        cols = self.columns_for(table)
        for c in candidates:
            if c in cols:
                return c
        raise RuntimeError(f"Could not find any of {list(candidates)} in table '{table}'.")

    @lru_cache(maxsize=256)
    def generated_columns(self, table: str) -> set[str]:
        # Best-effort for Postgres via information_schema
        q = text(
            """
            SELECT column_name, is_generated, generation_expression
            FROM information_schema.columns
            WHERE table_schema = :s AND table_name = :t
            """
        )
        gen: set[str] = set()
        with self.engine.connect() as conn:
            rows = conn.execute(q, {"s": self.schema, "t": table}).mappings().all()
            for r in rows:
                if str(r.get("is_generated") or "").upper() == "ALWAYS":
                    gen.add(r["column_name"])
                elif r.get("generation_expression"):
                    gen.add(r["column_name"])
        return gen
