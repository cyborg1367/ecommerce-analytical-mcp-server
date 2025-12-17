from __future__ import annotations

import random
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config.settings import Settings
from app.infrastructure.db.reflection import SchemaReflection
from app.infrastructure.db.tables import TableRegistry


def slugify(text_: str) -> str:
    s = (text_ or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "category"


class SeedService:
    def __init__(self, settings: Settings, reflection: SchemaReflection, registry: TableRegistry):
        self.settings = settings
        self.reflection = reflection
        self.registry = registry

    def _require_writes_enabled(self) -> None:
        if not self.settings.allow_writes:
            raise PermissionError("Writes are disabled. Set ALLOW_WRITES=1 to enable seed/insert/update tools.")

    def _dynamic_truncate(self, session: Session) -> None:
        ordered = [
            "order_status_events",
            "shipments",
            "refunds",
            "payments",
            "order_promotions",
            "promo_codes",
            "stock_movements",
            "order_items",
            "orders",
            "product_images",
            "products",
            "categories",
            "customer_addresses",
            "addresses",
            "customers",
        ]
        existing = [t for t in ordered if self.reflection.table_exists(t)]
        if existing:
            session.execute(text(f"TRUNCATE {', '.join(existing)} RESTART IDENTITY CASCADE;"))

    def seed_demo_data(self, session: Session, size: str, reset_first: bool, seed: int) -> dict:
        self._require_writes_enabled()
        self.reflection.require_tables("customers", "categories", "products", "orders", "order_items")

        size = (size or "").lower().strip()
        if size not in ("small", "medium", "large"):
            raise ValueError("size must be one of: small, medium, large")

        rng = random.Random(seed)
        if size == "small":
            n_customers, n_products, n_orders = 50, 150, 600
        elif size == "medium":
            n_customers, n_products, n_orders = 300, 900, 7000
        else:
            n_customers, n_products, n_orders = 1500, 4000, 40000

        Categories = self.registry.get("categories")
        Customers = self.registry.get("customers")
        Products = self.registry.get("products")
        Orders = self.registry.get("orders")
        Items = self.registry.get("order_items")

        cat_cols = self.reflection.columns_for("categories")
        prod_cols = self.reflection.columns_for("products")
        order_cols = self.reflection.columns_for("orders")
        oi_cols = self.reflection.columns_for("order_items")

        gen_orders = self.reflection.generated_columns("orders")
        gen_items = self.reflection.generated_columns("order_items")

        ts_col = self.reflection.pick_col("orders", ("placed_at", "ordered_at", "created_at", "order_date"))
        status_col = "status" if "status" in order_cols else None
        total_col = self.reflection.pick_col("orders", ("total_amount", "grand_total", "total"))
        can_write_total = (total_col in order_cols) and (total_col not in gen_orders)

        qty_col = self.reflection.pick_col("order_items", ("quantity", "qty"))

        has_order_number = "order_number" in order_cols
        has_currency_orders = "currency_code" in order_cols

        has_subtotal = "subtotal_amount" in order_cols and "subtotal_amount" not in gen_orders
        has_discount = "discount_amount" in order_cols and "discount_amount" not in gen_orders
        has_tax = "tax_amount" in order_cols and "tax_amount" not in gen_orders
        has_shipping = "shipping_amount" in order_cols and "shipping_amount" not in gen_orders

        has_unit_price = "unit_price" in oi_cols
        has_unit_cost = "unit_cost" in oi_cols
        has_item_discount = "item_discount" in oi_cols
        has_item_tax = "item_tax" in oi_cols
        has_sku_snap = "sku_snapshot" in oi_cols
        has_name_snap = "name_snapshot" in oi_cols

        if not (has_unit_price and has_sku_snap and has_name_snap):
            raise RuntimeError("order_items must have unit_price, sku_snapshot, name_snapshot for this seeder.")

        can_write_line_subtotal = ("line_subtotal" in oi_cols) and ("line_subtotal" not in gen_items)
        can_write_line_total = ("line_total" in oi_cols) and ("line_total" not in gen_items)

        has_prod_cost = "cost" in prod_cols
        has_prod_attrs = "attributes" in prod_cols
        has_prod_currency = "currency_code" in prod_cols
        has_prod_is_active = "is_active" in prod_cols

        has_stock_movements = self.reflection.table_exists("stock_movements")
        Stock = self.registry.get("stock_movements") if has_stock_movements else None
        sm_cols = self.reflection.columns_for("stock_movements") if has_stock_movements else set()
        sm_has_ref_order = "reference_order_id" in sm_cols
        sm_has_movement_type = "movement_type" in sm_cols
        sm_has_note = "note" in sm_cols

        categories = ["Electronics", "Books", "Home", "Clothing", "Beauty", "Sports", "Toys"]

        def rand_price() -> float:
            base = rng.choice([6.99, 9.99, 14.99, 19.99, 29.99, 49.99, 79.99, 129.99, 199.99])
            return round(max(1.0, base + rng.uniform(-0.5, 0.5)), 2)

        def rand_cost(price: float) -> float:
            return round(max(0.2, price * rng.uniform(0.35, 0.75)), 2)

        statuses = ["paid", "shipped", "delivered", "pending", "cancelled", "refunded"]
        weights = [0.35, 0.20, 0.25, 0.10, 0.07, 0.03]

        run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        order_seq = 0

        with session.begin():
            if reset_first:
                self._dynamic_truncate(session)
                self.reflection.clear_cache()
                self.registry.clear_cache()

            # Categories
            cat_rows = []
            for name in categories:
                row = {"name": name}
                if "slug" in cat_cols:
                    row["slug"] = slugify(name)
                cat_rows.append(row)

            stmt = pg_insert(Categories).values(cat_rows)
            if "name" in cat_cols:
                stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
            else:
                stmt = stmt.on_conflict_do_nothing()
            session.execute(stmt)

            cat_map = {
                r["name"]: r["category_id"]
                for r in session.execute(text("SELECT category_id, name FROM categories;")).mappings().all()
            }

            # Customers
            cust_rows = [{"email": f"customer{i:05d}@example.com", "full_name": f"Customer {i:05d}"} for i in range(1, n_customers + 1)]
            session.execute(pg_insert(Customers).values(cust_rows).on_conflict_do_nothing(index_elements=["email"]))

            customer_ids = [r["customer_id"] for r in session.execute(text("SELECT customer_id FROM customers;")).mappings().all()]

            # Products
            names = ["Cable", "Keyboard", "Mug", "Lamp", "Notebook", "T-shirt", "Serum", "Book", "Headphones", "Chair"]
            suffix = ["Classic", "Pro", "Mini", "XL", "Eco", "Plus"]

            prod_rows = []
            for i in range(1, n_products + 1):
                sku = f"SKU-{i:06d}"
                pname = f"{rng.choice(names)} {rng.choice(suffix)}"
                cid = cat_map[rng.choice(categories)]
                price = rand_price()
                cost = rand_cost(price)

                row = {"sku": sku, "name": pname, "category_id": cid, "price": price}
                if has_prod_cost:
                    row["cost"] = cost
                if has_prod_currency:
                    row["currency_code"] = "EUR"
                if has_prod_attrs:
                    row["attributes"] = {
                        "brand": rng.choice(["Acme", "Nova", "ZenCo", "Peak", "Solaria"]),
                        "color": rng.choice(["black", "white", "red", "blue", "green"]),
                        "rating": round(rng.uniform(3.2, 4.9), 1),
                    }
                if has_prod_is_active:
                    row["is_active"] = True

                prod_rows.append(row)

            session.execute(pg_insert(Products).values(prod_rows).on_conflict_do_nothing(index_elements=["sku"]))

            prod_sel_cols = ["product_id", "sku", "name", "price"] + (["cost"] if has_prod_cost else [])
            prod_rows_db = session.execute(text(f"SELECT {', '.join(prod_sel_cols)} FROM products;")).mappings().all()

            product_ids = [p["product_id"] for p in prod_rows_db]
            sku_by_pid = {p["product_id"]: p["sku"] for p in prod_rows_db}
            name_by_pid = {p["product_id"]: p["name"] for p in prod_rows_db}
            price_by_pid = {p["product_id"]: float(p["price"]) for p in prod_rows_db}
            cost_by_pid = {p["product_id"]: float(p["cost"]) for p in prod_rows_db} if has_prod_cost else {}

            # Initial stock movements
            if has_stock_movements and Stock is not None:
                sm_rows = []
                for pid in product_ids:
                    initial = rng.randint(50, 400)
                    row = {"product_id": pid, "quantity_delta": initial}
                    if sm_has_movement_type:
                        row["movement_type"] = "purchase"
                    if sm_has_ref_order:
                        row["reference_order_id"] = None
                    if sm_has_note:
                        row["note"] = "Seed initial stock"
                    sm_rows.append(row)
                session.execute(pg_insert(Stock).values(sm_rows))

            # Orders + Items (batched)
            item_batch: list[dict] = []
            sale_sm_batch: list[dict] = []

            for _ in range(n_orders):
                cust = rng.choice(customer_ids)
                st = rng.choices(statuses, weights=weights, k=1)[0]
                placed_at = datetime.now(timezone.utc) - timedelta(
                    days=rng.randint(0, 179),
                    hours=rng.randint(0, 23),
                    minutes=rng.randint(0, 59),
                )

                order_row = {"customer_id": cust, ts_col: placed_at}
                if has_order_number:
                    order_seq += 1
                    order_row["order_number"] = f"ORD-{run_id}-{order_seq:06d}"
                if status_col:
                    order_row[status_col] = st
                if has_currency_orders:
                    order_row["currency_code"] = "EUR"

                if has_subtotal:
                    order_row["subtotal_amount"] = 0.0
                if has_discount:
                    order_row["discount_amount"] = 0.0
                if has_tax:
                    order_row["tax_amount"] = 0.0
                if has_shipping:
                    order_row["shipping_amount"] = 0.0
                if (not any([has_subtotal, has_discount, has_tax, has_shipping])) and can_write_total:
                    order_row[total_col] = 0.0

                order_id = session.execute(pg_insert(Orders).values(order_row).returning(Orders.c.order_id)).scalar_one()

                chosen = rng.sample(product_ids, k=rng.randint(1, 5))
                subtotal = 0.0

                for pid in chosen:
                    qty = rng.randint(1, 3)
                    unit_price = price_by_pid[pid]
                    unit_cost = cost_by_pid.get(pid, round(unit_price * 0.6, 2))
                    subtotal += qty * unit_price

                    item = {
                        "order_id": order_id,
                        "product_id": pid,
                        qty_col: qty,
                        "unit_price": unit_price,
                        "unit_cost": unit_cost,
                        "sku_snapshot": sku_by_pid[pid],
                        "name_snapshot": name_by_pid[pid],
                    }
                    if has_item_discount:
                        item["item_discount"] = 0.0
                    if has_item_tax:
                        item["item_tax"] = 0.0
                    if can_write_line_subtotal:
                        item["line_subtotal"] = round(qty * unit_price, 2)
                    if can_write_line_total:
                        item["line_total"] = round(qty * unit_price, 2)

                    item_batch.append(item)

                    if has_stock_movements and Stock is not None:
                        sm = {"product_id": pid, "quantity_delta": -qty}
                        if sm_has_movement_type:
                            sm["movement_type"] = "sale"
                        if sm_has_ref_order:
                            sm["reference_order_id"] = order_id
                        if sm_has_note:
                            sm["note"] = "Seed sale"
                        sale_sm_batch.append(sm)

                subtotal = round(subtotal, 2)

                # Update totals (only writable)
                if any([has_subtotal, has_discount, has_tax, has_shipping]):
                    shipping = rng.choice([0.0, 2.9, 4.9, 5.9, 7.9]) if has_shipping else 0.0
                    tax_rate = rng.choice([0.0, 10.0, 24.0]) if has_tax else 0.0
                    tax = round(subtotal * (tax_rate / 100.0), 2) if has_tax else 0.0
                    discount = 0.0

                    upd = {}
                    if has_subtotal:
                        upd["subtotal_amount"] = subtotal
                    if has_discount:
                        upd["discount_amount"] = discount
                    if has_tax:
                        upd["tax_amount"] = tax
                    if has_shipping:
                        upd["shipping_amount"] = shipping
                    if can_write_total:
                        upd[total_col] = round(subtotal - discount + tax + shipping, 2)

                    if upd:
                        set_clause = ", ".join([f"{k}=:v_{i}" for i, k in enumerate(upd.keys())])
                        params = {f"v_{i}": v for i, v in enumerate(upd.values())}
                        params["oid"] = order_id
                        session.execute(text(f"UPDATE orders SET {set_clause} WHERE order_id=:oid"), params)

                elif can_write_total:
                    session.execute(
                        text(f"UPDATE orders SET {total_col}=:t WHERE order_id=:oid"),
                        {"t": subtotal, "oid": order_id},
                    )

                if len(item_batch) >= 5000:
                    session.execute(pg_insert(Items).values(item_batch))
                    item_batch.clear()
                if has_stock_movements and Stock is not None and len(sale_sm_batch) >= 5000:
                    session.execute(pg_insert(Stock).values(sale_sm_batch))
                    sale_sm_batch.clear()

            if item_batch:
                session.execute(pg_insert(Items).values(item_batch))
            if has_stock_movements and Stock is not None and sale_sm_batch:
                session.execute(pg_insert(Stock).values(sale_sm_batch))

        return {
            "ok": True,
            "size": size,
            "reset_first": reset_first,
            "seed": seed,
            "inserted": {"customers": n_customers, "products": n_products, "orders": n_orders},
            "note": "Seed complete. Try sales_report(days=30) or the sales_deep_dive prompt.",
        }
