from __future__ import annotations

from app.container import Container


def register(mcp, container: Container) -> None:
    @mcp.prompt(
        title="Weekly exec brief",
        description="One-page executive brief: KPIs, what changed, risks, and next actions.",
        tags={"exec", "report"},
        meta={"audience": "exec"},
    )
    def weekly_exec_brief(days: int = 7) -> str:
        return f"""
Create a one-page executive brief for the last {days} days.

Use tools:
- sales_report(days={days})
- ops_health_report(days={days}, low_stock_threshold=10)
- repeat_purchase_rate(days=max(30,{days}))
- gross_margin_last_days(days={days})

Output (Markdown):
- Summary (max 5 bullets)
- KPI snapshot (include revenue, orders, AOV, margin%, repeat rate)
- What changed (refer to daily trend)
- Risks (ops + inventory)
- Next actions (3–7 bullets)

Rules: evidence-first, no invented numbers.
""".strip()

    @mcp.prompt(
        title="Sales deep dive",
        description="Detailed sales analysis for a period: trend, product/customer drivers, and recommendations.",
        tags={"analytics", "sales"},
        meta={"audience": "growth"},
    )
    def sales_deep_dive(days: int = 30, top_n: int = 15) -> str:
        return f"""
Analyze sales performance for the last {days} days.

Use tools:
- revenue_by_day(days={days})
- top_products_last_days(days={days}, limit={top_n})
- top_customers_last_days(days=max({days},90), limit={top_n})
- gross_margin_last_days(days={days})

Deliver (Markdown):
1) Trend narrative (spikes/dips)
2) Top products table + interpretation
3) Top customers table + interpretation
4) Profitability notes (margin implications)
5) Recommendations (5–10 bullets)

Prefer tools over raw SQL.
""".strip()

    @mcp.prompt(
        title="Investigate revenue drop",
        description="Compare periods, isolate drivers, propose fixes (root-cause playbook).",
        tags={"analytics", "anomaly"},
        meta={"audience": "analytics"},
    )
    def investigate_revenue_drop(days: int = 14, compare_days: int = 14) -> str:
        return f"""
We suspect revenue dropped. Compare last {days} days vs the prior {compare_days} days.

Use tools:
- revenue_by_day(days={days + compare_days})
- top_products_last_days(days={days}, limit=20)
- top_customers_last_days(days=max({days},90), limit=20)
- ops_health_report(days={days}, low_stock_threshold=10)

If needed, use sql_readonly for a clean KPI comparison across the two windows.

Output (Markdown):
- Evidence (tables + key differences)
- Likely causes (ranked)
- Remediations (ranked by impact/effort)
- Monitoring plan (what to watch next)
""".strip()

    @mcp.prompt(
        title="Ops triage",
        description="Operations triage: backlog, status issues, inventory risks, immediate actions.",
        tags={"ops", "report"},
        meta={"audience": "ops"},
    )
    def ops_triage(days: int = 14) -> str:
        return f"""
Run an ops triage for the last {days} days.

Use tools:
- ops_health_report(days={days}, low_stock_threshold=10)
- table_counts()

Output (Markdown):
- What’s urgent (today)
- What’s risky (this week)
- Recommended actions (specific)
""".strip()

    @mcp.prompt(
        title="Inventory reorder plan",
        description="Reorder plan: low stock list + sales velocity context.",
        tags={"inventory", "ops"},
        meta={"audience": "ops"},
    )
    def inventory_reorder_plan(days: int = 30, low_stock_threshold: int = 10) -> str:
        return f"""
Create an inventory reorder plan.

Use tools:
- low_stock(threshold={low_stock_threshold}, limit=50)
- top_products_last_days(days={days}, limit=20)

Output (Markdown):
- Reorder now (low stock + high sales)
- Watchlist (low stock + low sales)
- Notes / assumptions
""".strip()

    @mcp.prompt(
        title="Data quality smoke test",
        description="Fast sanity checks after seeding or schema changes.",
        tags={"data-quality", "debug"},
        meta={"audience": "engineering"},
    )
    def data_quality_smoke_test() -> str:
        return """
Run a data-quality smoke test.

Use tools:
- db_ping()
- schema_overview()
- table_counts()
- sales_report(days=30)

If anomalies appear, use sql_readonly for targeted checks.
Output: pass/fail summary + fixes.
""".strip()
