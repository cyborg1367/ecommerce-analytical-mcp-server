from __future__ import annotations

from pydantic import Field

from app.container import Container


def register(mcp, container: Container) -> None:
    @mcp.tool(
        title="Refresh schema cache",
        description="Clear cached schema metadata (use after running migrations).",
        tags={"schema", "debug"},
        meta={"read": True},
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    def refresh_schema_cache() -> dict:
        container.schema.clear_cache()
        return {"ok": True, "note": "Schema cache cleared."}

    @mcp.tool(
        title="Schema overview",
        description="List tables + columns in the public schema (Claude-friendly).",
        tags={"schema"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def schema_overview() -> dict:
        return container.schema.schema_overview()

    @mcp.tool(
        title="List tables",
        description="List all tables in public schema.",
        tags={"schema"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def list_tables() -> dict:
        return container.schema.list_tables()

    @mcp.tool(
        title="Describe table",
        description="Describe a table: columns, types, nullability, and default values (best effort).",
        tags={"schema"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def describe_table(table_name: str = Field(description="Table name in public schema.")) -> dict:
        return container.schema.describe_table(table_name)
