from __future__ import annotations

from app.container import Container


def register(mcp, container: Container) -> None:
    @mcp.tool(
        title="Revenue by day",
        description="Orders + revenue by day for the last N days (excludes cancelled if status exists).",
        tags={"analytics", "sales"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def revenue_by_day(days: int = 30) -> dict:
        with container.uow_factory() as uow:
            rows = container.analytics.revenue_by_day(uow.session, days=days)
            return {"days": days, "rows": list(rows)}

    @mcp.tool(
        title="Top products",
        description="Top products by revenue for the last N days (excludes cancelled if status exists).",
        tags={"analytics", "sales", "catalog"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def top_products_last_days(days: int = 30, limit: int = 10) -> dict:
        with container.uow_factory() as uow:
            rows = container.analytics.top_products_last_days(uow.session, days=days, limit=limit)
            return {"days": days, "limit": limit, "rows": list(rows)}

    @mcp.tool(
        title="Top customers",
        description="Top customers by revenue for the last N days (excludes cancelled if status exists).",
        tags={"analytics", "sales", "customer"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def top_customers_last_days(days: int = 90, limit: int = 10) -> dict:
        with container.uow_factory() as uow:
            rows = container.analytics.top_customers_last_days(uow.session, days=days, limit=limit)
            return {"days": days, "limit": limit, "rows": list(rows)}

    @mcp.tool(
        title="Repeat purchase rate",
        description="Repeat purchase rate over last N days (share of customers with 2+ orders).",
        tags={"analytics", "customer"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def repeat_purchase_rate(days: int = 180) -> dict:
        with container.uow_factory() as uow:
            row = container.analytics.repeat_purchase_rate(uow.session, days=days)
            return dict(row)

    @mcp.tool(
        title="Gross margin",
        description="Gross margin for last N days (uses order_items unit_cost if available, else products.cost).",
        tags={"analytics", "finance"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def gross_margin_last_days(days: int = 30) -> dict:
        with container.uow_factory() as uow:
            row = container.analytics.gross_margin_last_days(uow.session, days=days)
            return dict(row)
