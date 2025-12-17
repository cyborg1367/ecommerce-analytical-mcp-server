from __future__ import annotations

from app.infrastructure.db.reflection import SchemaReflection


class SchemaService:
    def __init__(self, reflection: SchemaReflection):
        self.reflection = reflection

    def clear_cache(self) -> None:
        self.reflection.clear_cache()

    def list_tables(self) -> dict:
        tables = self.reflection.list_tables()
        return {"tables": tables}

    def describe_table(self, table_name: str) -> dict:
        cols = self.reflection.describe_table(table_name)
        return {"table": table_name, "columns": cols}

    def schema_overview(self) -> dict:
        tables = self.reflection.list_tables()
        by_table: dict[str, list[dict]] = {t: self.reflection.describe_table(t) for t in tables}

        md_lines = ["# Public schema", ""]
        if not tables:
            md_lines.append("_No tables found in public schema._")
        else:
            for t in tables:
                md_lines.append(f"## {t}")
                for c in by_table[t]:
                    md_lines.append(
                        f"- `{c['column']}` ({c['type']}) nullable={c['nullable']}"
                        + (f" default={c['default']}" if c.get("default") else "")
                    )
                md_lines.append("")

        return {"tables": tables, "columns": by_table, "markdown": "\n".join(md_lines).strip()}
