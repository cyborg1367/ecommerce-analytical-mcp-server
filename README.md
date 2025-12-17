# E-commerce Analytical MCP Server

A PostgreSQL-backed **Model Context Protocol (MCP)** server that exposes a curated set of **analytics**, **operations**, **schema**, and **safe SQL** tools for working with an e-commerce database — so an AI agent (IDE assistant, chat app, etc.) can explore data, generate reports, and produce dashboards without ad-hoc SQL.

Built with **FastMCP**, **SQLAlchemy**, and **psycopg**, with schema reflection to adapt to common variations in real-world e-commerce schemas.

---

## Why this exists

If you’ve ever wanted an AI assistant to reliably answer questions like:

- “What changed this week?”
- “Which products are driving revenue?”
- “Are we building a backlog?”
- “What should we reorder now?”

…using your **actual database** (not guesses), this project provides a clean, controlled MCP interface over Postgres.

---

## Key features

- **Analytics tools**: Revenue and orders by day, top products, top customers, repeat purchase rate, gross margin, and sales KPIs.
- **Ops and reporting tools**: One-page sales and ops reports in Markdown, table counts, low-stock insights, and operational health checks.
- **Visual dashboards**: A 2×2 composite **sales dashboard PNG** (revenue trend, orders trend, top products, KPI tiles).
- **Schema tools**: Schema overview, table listing, table descriptions, and schema cache refresh.
- **Safe SQL access**: A hardened, read-only SQL tool that only allows `SELECT`/`WITH`/`SHOW`/`EXPLAIN`.
- **Demo data seeding**: Realistic synthetic e-commerce data generator for local experiments.
- **Prompt helpers**: Opinionated prompt templates for exec briefs, sales deep dives, ops triage, inventory planning, and data-quality smoke tests.

---

## Architecture overview

- **MCP server**: Implemented using `fastmcp` and started via the `ecom-mcp` console script.
- **Configuration**: Centralized in `Settings` (Pydantic `BaseSettings`), loading from environment variables and an optional `.env` file.
- **Database access**: SQLAlchemy with a pooled `Engine` and a small Unit-of-Work abstraction.
- **Schema reflection**: Automatically inspects tables and columns in the `public` schema to work with common e-commerce schemas (even if column names differ slightly).
- **Services**:
  - **AnalyticsService**: High-level reporting queries (revenue, customers, products, margins, etc.).
  - **OpsService**: Markdown reports for sales and operations.
  - **SchemaService**: Introspection helpers for tables and columns.
  - **SqlService**: Read-only SQL execution with safety checks and timeouts.
  - **SeedService**: Demo-data writer with safety guardrails.

---

## Requirements

- **Python**: `>= 3.13`
- **PostgreSQL**: Any reasonably recent PostgreSQL version
- **Network access**: The MCP host must be able to connect to the database provided in the DSN

---

## Quickstart (recommended with `uv`)

```bash
git clone https://github.com/<your-org>/<your-repo>.git
cd <your-repo>

# Install dependencies
uv sync

# Run the MCP server (stdio)
uv run ecom-mcp
```

Alternatively:

```bash
uv run python -m app.main
```

---

## Installation (pip)

```bash
git clone https://github.com/<your-org>/<your-repo>.git
cd <your-repo>

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install .
```

After installation, the `ecom-mcp` console script will be available on your `PATH`.

---

## Configuration

Configuration is handled by `app.config.settings.Settings`, which reads from:

- environment variables
- an optional `.env` file in the project root

### Main settings

- **`POSTGRES_DSN`** (required): PostgreSQL connection string  
  - Accepts `postgresql+psycopg://...`, `postgresql://...`, or `postgres://...`.

- **`ALLOW_WRITES`** (optional, default: `true`): Enables write-capable tools (notably demo data seeding).  
  - In production, you typically want this **disabled**.

- **`LOG_LEVEL`** (optional, default: `INFO`): Python logging level (`DEBUG`, `INFO`, `WARNING`, ...)

Example `.env`:

```bash
POSTGRES_DSN=postgresql://user:password@localhost:5432/ecom_db
ALLOW_WRITES=false
LOG_LEVEL=INFO
```

> Note: `ALLOW_WRITES=false` (or `0`) will block tools that modify data, such as `seed_demo_data`.

---

## Running the MCP server

Start the server via console script:

```bash
ecom-mcp
```

This starts a FastMCP server named **`ecom-postgres`** that communicates over **stdio**, which is the expected transport for most MCP hosts.

Or run the module directly:

```bash
python -m app.main
```

---

## Connecting to MCP hosts

This project runs over **stdio** by default.

### Claude Desktop / Cursor / Trae (JSON with `mcpServers`)

```json
{
  "mcpServers": {
    "ecom_postgres": {
      "command": "uv",
      "args": ["--directory", "E:\\projects\\ecom-mcp", "run", "ecom-mcp"]
    }
  }
}
```

### VS Code (create `.vscode/mcp.json`)

VS Code uses a different top-level key (`servers`) and requires `type: "stdio"`:

```json
{
  "servers": {
    "ecomPostgres": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "${workspaceFolder}", "run", "ecom-mcp"],
      "envFile": "${workspaceFolder}\\.env"
    }
  }
}
```

---

## MCP tools

Tool identifiers typically match the Python function name.

### Health

- **`db_ping`** (`health`):  
  Connectivity check returning current database, user, schema, and server time.

### Schema and metadata

- **`refresh_schema_cache`** (`schema`):  
  Clears cached schema metadata. Use after migrations or schema changes.

- **`schema_overview`** (`schema`):  
  Returns a Markdown overview of tables and columns in `public`, plus structured JSON.

- **`list_tables`** (`schema`):  
  Lists all tables in the `public` schema.

- **`describe_table`** (`schema`):  
  Returns columns, types, nullability, and default values for a given table.

- **`table_counts`** (`schema`, `debug`):  
  Row counts for common e-commerce tables (only those that exist).

### Analytics

- **`revenue_by_day(days=30)`** (`analytics`, `sales`):  
  Orders and revenue by day for the last `N` days (excludes cancelled orders when a `status` column exists).

- **`top_products_last_days(days=30, limit=10)`** (`analytics`, `sales`, `catalog`):  
  Top products by revenue for the last `N` days.

- **`top_customers_last_days(days=90, limit=10)`** (`analytics`, `sales`, `customer`):  
  Top customers by revenue for the last `N` or 90 days.

- **`repeat_purchase_rate(days=180)`** (`analytics`, `customer`):  
  Share of customers with 2+ orders over the chosen window.

- **`gross_margin_last_days(days=30)`** (`analytics`, `finance`):  
  Revenue, cost, gross margin, and margin rate for the last `N` days.

### Operations and reporting

- **`low_stock(threshold=10, limit=50)`** (`ops`, `inventory`):  
  Lists low-stock items (requires either a `v_inventory_on_hand` view or an `inventory` table).

- **`ops_health_report(days=14, low_stock_threshold=10)`** (`ops`, `report`):  
  Markdown report summarizing order status mix, backlog, and inventory risks.

- **`sales_report(days=30, top_n=10)`** (`analytics`, `report`, `sales`):  
  One-page Markdown sales report with KPIs, daily trend, and top products.

### Dashboards

- **`sales_dashboard(days=30, top_n=10)`** (`analytics`, `report`, `charts`):  
  Generates a 2×2 PNG dashboard (revenue trend, orders trend, top products, KPI tiles).  
  Returns both a Markdown description and the PNG image bytes.

> Note: Rendering of tool-returned images depends on the MCP host. Some clients show inline images; others display base64.

### SQL (read-only)

- **`sql_readonly(query, max_rows=200, timeout_ms=5000)`** (`sql`):  
  Executes a **single** read-only SQL statement (`SELECT`/`WITH`/`SHOW`/`EXPLAIN` only).  
  Enforces:
  - Normalized SQL with trailing semicolons stripped
  - No internal semicolons (single statement only)
  - Server-side statement timeout (`timeout_ms`)
  - Row limit (`max_rows`)

### Seeding and demo data

- **`seed_demo_data(size="small|medium|large", reset_first=True, seed=42)`** (`seed`, `demo`):
  Inserts realistic demo e-commerce data, optionally truncating existing data first.

  - Requires `ALLOW_WRITES=true` (or `1`) — otherwise raises a permission error.
  - Sizes:
    - **small**: ~50 customers, 150 products, 600 orders
    - **medium**: ~300 customers, 900 products, 7,000 orders
    - **large**: ~1,500 customers, 4,000 products, 40,000 orders

---

## Prompt helpers

The server registers several **MCP prompts** that guide an AI agent to use tools effectively:

- **`weekly_exec_brief(days=7)`**: One-page executive brief (KPIs, what changed, risks, next actions).
- **`sales_deep_dive(days=30, top_n=15)`**: Detailed sales analysis (trend, drivers, profitability, recommendations).
- **`investigate_revenue_drop(days=14, compare_days=14)`**: Root-cause playbook comparing two windows.
- **`ops_triage(days=14)`**: Ops triage focusing on backlog, status mix, and inventory risks.
- **`inventory_reorder_plan(days=30, low_stock_threshold=10)`**: Inventory plan using low-stock + sales velocity.
- **`data_quality_smoke_test()`**: Fast sanity checks after seeding or schema changes.

Prompts strongly prefer built-in analytics tools and use `sql_readonly` only when needed.

---

## Expected schema (high level)

The server is designed to adapt to common e-commerce schemas via reflection, but works best when the following tables (or equivalents) exist in the `public` schema:

- **`customers`**
  - Recommended columns: `customer_id`, `email`, `full_name`

- **`categories`** (optional but used by the seeder)
  - Recommended columns: `category_id`, `name`, `slug`

- **`products`**
  - Recommended columns: `product_id`, `sku`, `name`, `category_id`, `price`
  - Recommended extras: `cost`, `currency_code`, `attributes`, `is_active`

- **`orders`**
  - Timestamp: one of `placed_at`, `ordered_at`, `created_at`, `order_date`
  - Total: one of `total_amount`, `grand_total`, `total`
  - Optional: `status`, `order_number`, `currency_code`,
    `subtotal_amount`, `discount_amount`, `tax_amount`, `shipping_amount`

- **`order_items`**
  - Quantity: `quantity` or `qty`
  - Required for seeding: `unit_price`, `sku_snapshot`, `name_snapshot`
  - Optional: `unit_cost`, `line_subtotal`, `line_total`, `item_discount`, `item_tax`

- **Inventory**
  - Either a `v_inventory_on_hand` view or an `inventory` table with `on_hand` or `quantity_on_hand`,
    plus a relation to `products`

- **Stock movements** (optional)
  - `stock_movements` table, used by the seeder when present

The code attempts to pick the right columns dynamically and raises clear runtime errors if required tables or columns are missing.

---

## Safety and best practices

- Prefer analytics/reporting tools over raw SQL (`revenue_by_day`, `sales_report`, `ops_health_report`, etc.).
- Lock down writes in production: set `ALLOW_WRITES=false`.
- Refresh schema cache after migrations: call `refresh_schema_cache`.

---

## Development

- **Code style**: `ruff` (see `[tool.ruff]` in `pyproject.toml`)
- **Editable install**:

```bash
uv pip install -e .
```

You can then run `ecom-mcp` from your environment while iterating on the code.

---

## License

MIT License

Copyright (c) 2025 Masoud Ahangary

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


## Contributing

Issues and PRs are welcome. If you add new tools, please include:

- expected schema assumptions
- sample outputs
- safety considerations (read/write permissions, timeouts, limits)
