from __future__ import annotations

from app.container import Container
from app.presentation.charts.sales_dashboard import render_sales_dashboard_png

# FastMCP Image import can vary by version; this makes it robust.
try:
    from fastmcp import Image  # type: ignore
except Exception:  # pragma: no cover
    from fastmcp.utilities.types import Image  # type: ignore


def register(mcp, container: Container) -> None:
    @mcp.tool(
        title="Sales dashboard",
        description="Professional one-page composite dashboard image (2x2): revenue trend, orders trend, "
                    "top products, KPI tiles.",
        tags={"analytics", "report", "charts"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def sales_dashboard(days: int = 30, top_n: int = 10):
        with container.uow_factory() as uow:
            # data (application services)
            trend = container.analytics.revenue_by_day(uow.session, days=days)
            top = container.analytics.top_products_last_days(uow.session, days=days, limit=top_n)
            kpis = container.analytics.sales_kpis(uow.session, days=days)
            margin = container.analytics.gross_margin_last_days(uow.session, days=days)

            png = render_sales_dashboard_png(
                trend_rows=trend,
                top_products=top,
                kpis=kpis,
                margin=margin,
                title=f"Sales dashboard — last {days} days",
            )

            md = (
                f"# Sales dashboard\n"
                f"- Window: last **{days} days**\n\n"
                f"## Figure 1 — Sales dashboard (composite)\n"
                f"This figure is a single-page dashboard with 4 panels:\n"
                f"- Revenue trend\n"
                f"- Orders trend\n"
                f"- Top products by revenue\n"
                f"- KPI snapshot (Revenue / Orders / AOV / Margin rate)\n"
            )

            return [md, Image(data=png, format="png")]
