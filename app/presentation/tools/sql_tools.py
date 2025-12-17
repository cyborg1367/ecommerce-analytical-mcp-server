from __future__ import annotations

from pydantic import Field

from app.container import Container


def register(mcp, container: Container) -> None:
    @mcp.tool(
        title="SQL (read-only)",
        description="Run one read-only SQL statement (SELECT/WITH/SHOW/EXPLAIN). Returns rows as JSON.",
        tags={"sql"},
        meta={"read": True, "safety": "readonly"},
        annotations={"readOnlyHint": True, "openWorldHint": False},
    )
    def sql_readonly(
        query: str = Field(description="Single SQL statement (SELECT/WITH/SHOW/EXPLAIN). Semicolon allowed at end."),
        max_rows: int = Field(default=200, ge=1, le=2000, description="Max rows to return."),
        timeout_ms: int = Field(default=5000, ge=100, le=60000, description="Statement timeout in milliseconds."),
    ) -> dict:
        with container.uow_factory() as uow:
            return container.sql.sql_readonly(uow.session, query=query, max_rows=max_rows, timeout_ms=timeout_ms)
