from __future__ import annotations

from app.container import Container


def register(mcp, container: Container) -> None:
    @mcp.tool(
        title="Low stock",
        description="List low-stock items (requires v_inventory_on_hand view or inventory table).",
        tags={"ops", "inventory"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def low_stock(threshold: int = 10, limit: int = 50) -> dict:
        with container.uow_factory() as uow:
            rows = container.analytics.low_stock(uow.session, threshold=threshold, limit=limit)
            return {"threshold": threshold, "limit": limit, "rows": list(rows)}

    @mcp.tool(
        title="Ops health report",
        description="Operational health snapshot: status mix + pending backlog + optional low-stock summary.",
        tags={"ops", "report"},
        meta={"read": True, "format": "markdown"},
        annotations={"readOnlyHint": True},
    )
    def ops_health_report(days: int = 14, low_stock_threshold: int = 10) -> str:
        with container.uow_factory() as uow:
            return container.ops.ops_health_report(uow.session, days=days, low_stock_threshold=low_stock_threshold)

    @mcp.tool(
        title="Sales report",
        description="One-page Markdown sales report (KPIs + trend + top products).",
        tags={"analytics", "report", "sales"},
        meta={"read": True, "format": "markdown"},
        annotations={"readOnlyHint": True},
    )
    def sales_report(days: int = 30, top_n: int = 10) -> str:
        with container.uow_factory() as uow:
            return container.ops.sales_report(uow.session, days=days, top_n=top_n)

    @mcp.tool(
        title="Table counts",
        description="Row counts for common e-commerce tables (only those that exist).",
        tags={"schema", "debug"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def table_counts() -> dict:
        with container.uow_factory() as uow:
            return container.analytics.table_counts(uow.session)
