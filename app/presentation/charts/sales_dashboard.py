from __future__ import annotations

import io
from typing import Any
import matplotlib.pyplot as plt

import matplotlib

matplotlib.use("Agg")  # headless (no GUI)


def _set_sparse_xticks(ax, labels: list[str], max_ticks: int = 10) -> None:
    if not labels:
        return
    n = len(labels)
    step = max(1, n // max_ticks)
    idx = list(range(0, n, step))
    ax.set_xticks(idx)
    ax.set_xticklabels([labels[i] for i in idx], rotation=45, ha="right")


def render_sales_dashboard_png(
    *,
    trend_rows: list[dict[str, Any]],
    top_products: list[dict[str, Any]],
    kpis: dict[str, Any],
    margin: dict[str, Any],
    title: str,
) -> bytes:
    """
    Single-page composite dashboard (2x2):
      1) Revenue trend
      2) Orders trend
      3) Top products by revenue
      4) KPI tiles (revenue/orders/AOV/margin%)
    Returns PNG bytes.
    """
    # Normalize data
    days = [str(r["day"]) for r in trend_rows]
    revenue = [float(r["revenue"]) for r in trend_rows]
    orders = [int(r["orders"]) for r in trend_rows]

    top = top_products[:10]
    top_labels = [str(r.get("sku") or "") for r in top]
    top_vals = [float(r.get("revenue") or 0.0) for r in top]

    fig = plt.figure(figsize=(12, 7), dpi=120)
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1])

    # --- (1) Revenue trend
    ax1 = fig.add_subplot(gs[0, 0])
    if revenue:
        ax1.plot(list(range(len(revenue))), revenue, marker="o")
    ax1.set_title("Revenue by day")
    ax1.set_ylabel("Revenue")
    _set_sparse_xticks(ax1, days)

    # --- (2) Orders trend
    ax2 = fig.add_subplot(gs[0, 1])
    if orders:
        ax2.plot(list(range(len(orders))), orders, marker="o")
    ax2.set_title("Orders by day")
    ax2.set_ylabel("Orders")
    _set_sparse_xticks(ax2, days)

    # --- (3) Top products bar
    ax3 = fig.add_subplot(gs[1, 0])
    if top_labels:
        ax3.bar(top_labels, top_vals)
        ax3.tick_params(axis="x", rotation=45)
    ax3.set_title("Top products (revenue)")
    ax3.set_ylabel("Revenue")

    # --- (4) KPI tiles
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")
    ax4.set_title("KPI snapshot")

    rev = kpis.get("revenue", 0)
    n_orders = kpis.get("orders", 0)
    aov = kpis.get("aov", 0)
    margin_rate = margin.get("margin_rate", 0)

    lines = [
        f"Revenue: {rev}",
        f"Orders: {n_orders}",
        f"AOV: {aov}",
        f"Margin rate: {margin_rate}",
    ]

    ax4.text(
        0.02,
        0.85,
        "\n".join(lines),
        fontsize=13,
        va="top",
        family="monospace",
    )

    fig.suptitle(title, fontsize=14, y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
