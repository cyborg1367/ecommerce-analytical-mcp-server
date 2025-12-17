from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from app.application.services.analytics_service import AnalyticsService


class OpsService:
    def __init__(self, analytics: AnalyticsService):
        self.analytics = analytics

    def ops_health_report(self, session: Session, days: int, low_stock_threshold: int) -> str:
        self.analytics.reflection.require_tables("orders")

        Orders = self.analytics.registry.get("orders")
        ts = Orders.c[self.analytics._orders_ts_col()]
        status_name = self.analytics._orders_status_col()
        status_col = Orders.c[status_name] if status_name else None

        start = datetime.now(timezone.utc) - timedelta(days=days)

        md = ["# Ops health report", f"- Window: last **{days} days**", ""]

        md.append("## Order status mix")
        if status_col is None:
            md.append("_No `status` column on orders._")
            md.append("")
        else:
            stmt = (
                select(status_col.label("status"), func.count().label("orders"))
                .where(ts >= start)
                .group_by(status_col)
                .order_by(func.count().desc())
            )
            rows = session.execute(stmt).mappings().all()
            if not rows:
                md.append("_No orders in window._")
            else:
                for r in rows:
                    md.append(f"- **{r['status']}**: {r['orders']}")
            md.append("")

        md.append("## Backlog")
        older_than = datetime.now(timezone.utc) - timedelta(hours=24)

        where = [ts < older_than, ts >= start]
        if status_col is not None:
            where.append(status_col.in_(["pending", "processing"]))

        pending_count = session.execute(select(func.count()).select_from(Orders).where(*where)).scalar_one()
        md.append(f"- Orders older than 24h still pending/processing: **{int(pending_count)}**")
        md.append("")

        md.append("## Inventory (low stock)")
        try:
            rows = self.analytics.low_stock(session, threshold=low_stock_threshold, limit=15)
            if not rows:
                md.append(f"- None at/under {low_stock_threshold}.")
            else:
                md.append(f"- Threshold: {low_stock_threshold}")
                for r in rows:
                    md.append(f"  - `{r['sku']}` {r['name']} — on_hand={r['on_hand']}")
        except Exception as e:
            md.append(f"_Inventory check unavailable: {e}_")

        return "\n".join(md).strip()

    def sales_report(self, session: Session, days: int, top_n: int) -> str:
        self.analytics.reflection.require_tables("orders", "order_items")

        Orders = self.analytics.registry.get("orders")
        ts = Orders.c[self.analytics._orders_ts_col()]
        total = Orders.c[self.analytics._orders_total_col()]
        status_name = self.analytics._orders_status_col()
        status_col = Orders.c[status_name] if status_name else None

        start = datetime.now(timezone.utc) - timedelta(days=days)
        where = [ts >= start]
        if status_col is not None:
            where.append(status_col != "cancelled")

        count_expr = func.count()

        kpi_stmt = select(
            count_expr.label("orders"),
            func.round(func.coalesce(func.sum(total), 0), 2).label("revenue"),
            case((count_expr == 0, 0), else_=func.round(func.avg(total), 2)).label("aov"),
        ).select_from(Orders).where(*where)

        kpis = session.execute(kpi_stmt).mappings().one()

        trend = self.analytics.revenue_by_day(session, days=days)
        top = self.analytics.top_products_last_days(session, days=days, limit=top_n)

        md = []
        md.append("# Sales report")
        md.append(f"- Window: last **{days} days**")
        md.append("")
        md.append("## KPIs")
        md.append("| orders | revenue | AOV |")
        md.append("|---:|---:|---:|")
        md.append(f"| {kpis['orders']} | {kpis['revenue']} | {kpis['aov']} |")
        md.append("")
        md.append("## Trend (daily)")
        if not trend:
            md.append("_No rows._")
        else:
            md.append("| day | orders | revenue |")
            md.append("|---|---:|---:|")
            for r in trend[-min(len(trend), 30):]:
                md.append(f"| {r['day']} | {r['orders']} | {r['revenue']} |")
        md.append("")
        md.append("## Top products (by revenue)")
        if not top:
            md.append("_No rows._")
        else:
            md.append("| sku | name | units | revenue |")
            md.append("|---|---|---:|---:|")
            for r in top:
                md.append(f"| {r['sku']} | {r['name']} | {r['units']} | {r['revenue']} |")

        return "\n".join(md).strip()
