from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    select,
    func,
    cast,
    Date,
    literal_column,
    case,
    Numeric,
)
from sqlalchemy.orm import Session

from app.infrastructure.db.reflection import SchemaReflection
from app.infrastructure.db.tables import TableRegistry


class AnalyticsService:
    def __init__(self, reflection: SchemaReflection, registry: TableRegistry):
        self.reflection = reflection
        self.registry = registry

    # -------- column picking (dynamic schema-friendly) --------

    def _pick_col(self, table_name: str, candidates: tuple[str, ...]) -> str:
        cols = self.reflection.columns_for(table_name)
        for c in candidates:
            if c in cols:
                return c
        raise RuntimeError(f"Could not find any of {list(candidates)} in table '{table_name}'.")

    def _orders_ts_col(self) -> str:
        return self._pick_col("orders", ("placed_at", "ordered_at", "created_at", "order_date"))

    def _orders_total_col(self) -> str:
        return self._pick_col("orders", ("total_amount", "grand_total", "total"))

    def _orders_status_col(self) -> str | None:
        cols = self.reflection.columns_for("orders")
        return "status" if "status" in cols else None

    def _order_items_qty_col(self) -> str:
        return self._pick_col("order_items", ("quantity", "qty"))

    def _order_items_price_col(self) -> str | None:
        cols = self.reflection.columns_for("order_items")
        if "unit_price" in cols:
            return "unit_price"
        if "price" in cols:
            return "price"
        return None

    def _order_items_line_total_col(self) -> str | None:
        cols = self.reflection.columns_for("order_items")
        return "line_total" if "line_total" in cols else None

    def _order_items_cost_col(self) -> str | None:
        cols = self.reflection.columns_for("order_items")
        return "unit_cost" if "unit_cost" in cols else None

    def _order_items_snapshot_cols(self) -> tuple[str | None, str | None]:
        cols = self.reflection.columns_for("order_items")
        sku = "sku_snapshot" if "sku_snapshot" in cols else None
        name = "name_snapshot" if "name_snapshot" in cols else None
        return sku, name

    # -------- analytics queries --------

    def revenue_by_day(self, session: Session, days: int) -> list[dict]:
        self.reflection.require_tables("orders")

        Orders = self.registry.get("orders")
        ts = Orders.c[self._orders_ts_col()]
        total = Orders.c[self._orders_total_col()]
        status_name = self._orders_status_col()
        status_col = Orders.c[status_name] if status_name else None

        start = datetime.now(timezone.utc) - timedelta(days=days)
        where = [ts >= start]
        if status_col is not None:
            where.append(status_col != "cancelled")

        stmt = (
            select(
                cast(ts, Date).label("day"),
                func.count().label("orders"),
                func.round(func.coalesce(func.sum(total), 0), 2).label("revenue"),
            )
            .where(*where)
            .group_by(literal_column("day"))
            .order_by(literal_column("day"))
        )

        return [dict(r) for r in session.execute(stmt).mappings().all()]

    def top_products_last_days(self, session: Session, days: int, limit: int) -> list[dict]:
        self.reflection.require_tables("orders", "order_items")

        Orders = self.registry.get("orders")
        Items = self.registry.get("order_items")

        ts = Orders.c[self._orders_ts_col()]
        status_name = self._orders_status_col()
        status_col = Orders.c[status_name] if status_name else None
        qty = Items.c[self._order_items_qty_col()]

        line_total_name = self._order_items_line_total_col()
        unit_price_name = self._order_items_price_col()

        if line_total_name:
            revenue_expr = func.sum(Items.c[line_total_name])
        elif unit_price_name:
            revenue_expr = func.sum(qty * Items.c[unit_price_name])
        else:
            raise RuntimeError("order_items needs line_total or (quantity + unit_price).")

        start = datetime.now(timezone.utc) - timedelta(days=days)
        where = [ts >= start]
        if status_col is not None:
            where.append(status_col != "cancelled")

        sku_snap, name_snap = self._order_items_snapshot_cols()

        if sku_snap and name_snap:
            sku_col = Items.c[sku_snap].label("sku")
            name_col = Items.c[name_snap].label("name")
            stmt = (
                select(
                    sku_col,
                    name_col,
                    func.sum(qty).label("units"),
                    func.round(revenue_expr, 2).label("revenue"),
                )
                .select_from(Items.join(Orders, Orders.c.order_id == Items.c.order_id))
                .where(*where)
                .group_by(sku_col, name_col)
                .order_by(literal_column("revenue").desc())
                .limit(limit)
            )
        else:
            self.reflection.require_tables("products")
            Products = self.registry.get("products")
            stmt = (
                select(
                    Products.c.sku.label("sku"),
                    Products.c.name.label("name"),
                    func.sum(qty).label("units"),
                    func.round(revenue_expr, 2).label("revenue"),
                )
                .select_from(
                    Items.join(Orders, Orders.c.order_id == Items.c.order_id).join(
                        Products, Products.c.product_id == Items.c.product_id
                    )
                )
                .where(*where)
                .group_by(Products.c.sku, Products.c.name)
                .order_by(literal_column("revenue").desc())
                .limit(limit)
            )

        return [dict(r) for r in session.execute(stmt).mappings().all()]

    def top_customers_last_days(self, session: Session, days: int, limit: int) -> list[dict]:
        self.reflection.require_tables("orders", "customers")

        Orders = self.registry.get("orders")
        Customers = self.registry.get("customers")

        ts = Orders.c[self._orders_ts_col()]
        total = Orders.c[self._orders_total_col()]
        status_name = self._orders_status_col()
        status_col = Orders.c[status_name] if status_name else None

        start = datetime.now(timezone.utc) - timedelta(days=days)
        where = [ts >= start]
        if status_col is not None:
            where.append(status_col != "cancelled")

        stmt = (
            select(
                Customers.c.customer_id,
                Customers.c.email,
                Customers.c.full_name,
                func.count().label("orders"),
                func.round(func.sum(total), 2).label("revenue"),
            )
            .select_from(Orders.join(Customers, Customers.c.customer_id == Orders.c.customer_id))
            .where(*where)
            .group_by(Customers.c.customer_id, Customers.c.email, Customers.c.full_name)
            .order_by(literal_column("revenue").desc())
            .limit(limit)
        )

        return [dict(r) for r in session.execute(stmt).mappings().all()]

    def repeat_purchase_rate(self, session: Session, days: int) -> dict:
        self.reflection.require_tables("orders")

        Orders = self.registry.get("orders")
        ts = Orders.c[self._orders_ts_col()]
        status_name = self._orders_status_col()
        status_col = Orders.c[status_name] if status_name else None

        start = datetime.now(timezone.utc) - timedelta(days=days)
        where = [ts >= start]
        if status_col is not None:
            where.append(status_col != "cancelled")

        cust_orders = (
            select(Orders.c.customer_id.label("customer_id"), func.count().label("n"))
            .where(*where)
            .group_by(Orders.c.customer_id)
            .cte("cust_orders")
        )

        repeat_customers_expr = func.sum(case((cust_orders.c.n >= 2, 1), else_=0))
        active_customers_expr = func.count()

        stmt = select(
            active_customers_expr.label("active_customers"),
            repeat_customers_expr.label("repeat_customers"),
            case(
                (active_customers_expr == 0, 0),
                else_=func.round(cast(repeat_customers_expr, Numeric) / active_customers_expr, 4),
            ).label("repeat_rate"),
        ).select_from(cust_orders)

        row = session.execute(stmt).mappings().one()
        return {"days": days, **dict(row)}

    def gross_margin_last_days(self, session: Session, days: int) -> dict:
        self.reflection.require_tables("orders", "order_items")

        Orders = self.registry.get("orders")
        Items = self.registry.get("order_items")

        ts = Orders.c[self._orders_ts_col()]
        status_name = self._orders_status_col()
        status_col = Orders.c[status_name] if status_name else None

        qty = Items.c[self._order_items_qty_col()]
        line_total_name = self._order_items_line_total_col()
        unit_price_name = self._order_items_price_col()
        unit_cost_name = self._order_items_cost_col()

        if line_total_name:
            revenue_expr = func.sum(Items.c[line_total_name])
        elif unit_price_name:
            revenue_expr = func.sum(qty * Items.c[unit_price_name])
        else:
            raise RuntimeError("order_items needs line_total or (quantity + unit_price).")

        start = datetime.now(timezone.utc) - timedelta(days=days)
        where = [ts >= start]
        if status_col is not None:
            where.append(status_col != "cancelled")

        joins = Items.join(Orders, Orders.c.order_id == Items.c.order_id)
        if unit_cost_name:
            cost_expr = func.sum(qty * Items.c[unit_cost_name])
        else:
            self.reflection.require_tables("products")
            Products = self.registry.get("products")
            if "cost" not in self.reflection.columns_for("products"):
                raise RuntimeError("No unit_cost in order_items and no cost column in products.")
            joins = joins.join(Products, Products.c.product_id == Items.c.product_id)
            cost_expr = func.sum(qty * Products.c.cost)

        stmt = (
            select(
                func.round(revenue_expr, 2).label("revenue"),
                func.round(func.coalesce(cost_expr, 0), 2).label("cost"),
                func.round(revenue_expr - func.coalesce(cost_expr, 0), 2).label("gross_margin"),
                case(
                    (revenue_expr == 0, 0),
                    else_=func.round((revenue_expr - func.coalesce(cost_expr, 0)) / revenue_expr, 4),
                ).label("margin_rate"),
            )
            .select_from(joins)
            .where(*where)
        )

        row = session.execute(stmt).mappings().one()
        return {"days": days, **dict(row)}

    # -------- ops helpers --------

    def _inventory_source_select(self):
        if self.reflection.relation_exists("v_inventory_on_hand"):
            Inv = self.registry.get("v_inventory_on_hand")
            Products = self.registry.get("products")
            return (
                select(Products.c.sku, Products.c.name, Inv.c.on_hand)
                .select_from(Inv.join(Products, Products.c.product_id == Inv.c.product_id))
            )

        if self.reflection.table_exists("inventory"):
            Inv = self.registry.get("inventory")
            Products = self.registry.get("products")
            cols = self.reflection.columns_for("inventory")
            on_hand_col = "on_hand" if "on_hand" in cols else ("quantity_on_hand" if "quantity_on_hand" in cols else None)
            if not on_hand_col:
                raise RuntimeError("Found inventory table but no on_hand/quantity_on_hand column.")
            return (
                select(Products.c.sku, Products.c.name, Inv.c[on_hand_col].label("on_hand"))
                .select_from(Inv.join(Products, Products.c.product_id == Inv.c.product_id))
            )

        raise RuntimeError("No inventory source found (expected v_inventory_on_hand view or inventory table).")

    def low_stock(self, session: Session, threshold: int, limit: int) -> list[dict]:
        inv_stmt = self._inventory_source_select().cte("inv")
        stmt = (
            select(inv_stmt.c.sku, inv_stmt.c.name, inv_stmt.c.on_hand)
            .where(inv_stmt.c.on_hand <= threshold)
            .order_by(inv_stmt.c.on_hand.asc(), inv_stmt.c.sku.asc())
            .limit(limit)
        )
        return [dict(r) for r in session.execute(stmt).mappings().all()]

    def table_counts(self, session: Session) -> dict:
        candidates = ["customers", "categories", "products", "orders", "order_items", "promo_codes", "order_promotions"]
        existing = [t for t in candidates if self.reflection.table_exists(t)]
        if not existing:
            return {"tables": {}, "note": "No known tables found."}

        out: dict[str, int] = {}
        for t in existing:
            T = self.registry.get(t)
            n = session.execute(select(func.count()).select_from(T)).scalar_one()
            out[t] = int(n)

        return {"tables": out}

    def sales_kpis(self, session: Session, days: int) -> dict:
        """
        Orders, revenue, AOV for the last N days (excludes cancelled if status exists).
        Returns: {"days": N, "orders": int, "revenue": float, "aov": float}
        """
        self.reflection.require_tables("orders")

        Orders = self.registry.get("orders")
        ts = Orders.c[self._orders_ts_col()]
        total = Orders.c[self._orders_total_col()]
        status_name = self._orders_status_col()
        status_col = Orders.c[status_name] if status_name else None

        from datetime import datetime, timedelta, timezone

        start = datetime.now(timezone.utc) - timedelta(days=days)
        where = [ts >= start]
        if status_col is not None:
            where.append(status_col != "cancelled")

        count_expr = func.count()

        stmt = select(
            count_expr.label("orders"),
            func.round(func.coalesce(func.sum(total), 0), 2).label("revenue"),
            case((count_expr == 0, 0), else_=func.round(func.avg(total), 2)).label("aov"),
        ).select_from(Orders).where(*where)

        row = session.execute(stmt).mappings().one()
        return {"days": days, **dict(row)}
