
## E-commerce Analytical MCP Server

E-commerce Analytical MCP Server is a PostgreSQL-backed **Model Context Protocol (MCP)** server
that exposes a curated set of **analytics**, **operations**, **schema**, and **SQL** tools
for working with an e-commerce database. It is built on top of `fastmcp`, `SQLAlchemy`,
and `psycopg`, with schema reflection to adapt to common variations in e-commerce schemas.

The server is designed to be attached to an MCP host (such as modern IDEs or AI tools),
so that an AI agent can explore your data, run safe queries, and generate dashboards
and reports without writing ad-hoc SQL.

### Key features

- **Analytics tools**: Revenue and orders by day, top products, top customers,
  repeat purchase rate, gross margin, and sales KPIs.
- **Ops and reporting tools**: One-page sales and ops reports in Markdown, table counts,
  low-stock insights, and operational health checks.
- **Visual dashboards**: A 2×2 composite **sales dashboard PNG** (trends, top products, KPIs).
- **Schema tools**: Schema overview, table listing, table descriptions, and schema cache refresh.
- **Safe SQL access**: A hardened, read-only SQL tool that only allows `SELECT`/`WITH`/`SHOW`/`EXPLAIN`.
- **Demo data seeding**: Realistic synthetic e-commerce data generator for local experiments.
- **Prompt helpers**: Opinionated prompt templates for exec briefs, sales deep dives, ops triage,
  inventory planning, and data-quality smoke tests.

---

### Architecture overview

- **MCP server**: Implemented using `fastmcp` and started via the `ecom-mcp` console script.
- **Configuration**: Centralised in `Settings` (Pydantic `BaseSettings`), loading from environment
  variables and an optional `.env` file.
- **Database access**: Uses SQLAlchemy with a pooled `Engine` and a small unit-of-work abstraction.
- **Schema reflection**: Automatically inspects tables and columns in the `public` schema to work
  with common e-commerce schemas (even if column names differ slightly).
- **Services**:
  - **AnalyticsService**: High-level reporting queries (revenue, customers, products, margins, etc.).
  - **OpsService**: Markdown reports for sales and operations.
  - **SchemaService**: Introspection helpers for tables and columns.
  - **SqlService**: Read-only SQL execution with safety checks and timeouts.
  - **SeedService**: Demo-data writer with safety guardrails.

---

### Requirements

- **Python**: `>= 3.13`
- **PostgreSQL**: Any reasonably recent PostgreSQL version (tested against standard setups)
- **Network access**: The MCP host must be able to connect to the database provided in the DSN.

---

### Installation

Clone the repository and install it as a Python package (system-wide, virtual environment,
or via a tool like `uv`):

```bash
git clone https://github.com/<your-org>/ecommerce-analytical-mcp-server.git
cd ecommerce-analytical-mcp-server

# Recommended: install into a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install .
```

After installation, the `ecom-mcp` console script will be available on your `PATH`.

---

### Configuration

Configuration is handled by `app.config.settings.Settings`, which reads from:

- Environment variables
- An optional `.env` file in the project root

The main settings are:

- **`POSTGRES_DSN`** (required): PostgreSQL connection string.
  - Accepts `postgresql+psycopg://...`, `postgresql://...`, or `postgres://...`.
- **`ALLOW_WRITES`** (optional, default: `true`): Enables write-capable tools
  (notably demo data seeding). In production, you typically want this **disabled**.
- **`LOG_LEVEL`** (optional, default: `INFO`): Python logging level (e.g. `DEBUG`, `INFO`, `WARNING`).

Example `.env`:

```bash
POSTGRES_DSN=postgresql://user:password@localhost:5432/ecom_db
ALLOW_WRITES=false
LOG_LEVEL=INFO
```

> **Note**: `ALLOW_WRITES=false` (or `0`) will block tools that modify data, such as `seed_demo_data`.

---

### Running the MCP server

Once installed and configured, start the MCP server:

```bash
ecom-mcp
```

This starts a FastMCP server named **`ecom-postgres`** that communicates over **stdio**,
which is the expected transport for most MCP hosts.

Alternatively, you can run the module directly:

```bash
python -m app.main
```

To integrate with an MCP host (for example, an AI assistant or IDE that supports MCP),
configure it to launch `ecom-mcp` in the project directory with the appropriate environment
variables (or `.env`) in scope.

---

### MCP tools

The server registers several categories of MCP tools. Names below correspond to the
tool identifiers exposed by FastMCP (usually the Python function name).

#### Health

- **`db_ping`** (`health`):
  - Connectivity check returning current database, user, schema, and server time.

#### Schema and metadata

- **`refresh_schema_cache`** (`schema`):
  - Clears cached schema metadata. Use after migrations or schema changes.
- **`schema_overview`** (`schema`):
  - Returns a Markdown overview of tables and columns in `public`, plus structured JSON.
- **`list_tables`** (`schema`):
  - Lists all tables in the `public` schema.
- **`describe_table`** (`schema`):
  - Returns columns, types, nullability, and default values for a given table.
- **`table_counts`** (`schema`, `debug`):
  - Row counts for common e-commerce tables (only those that exist).

#### Analytics

- **`revenue_by_day`** (`analytics`, `sales`):
  - Orders and revenue by day for the last `N` days (excludes cancelled orders when a
    `status` column exists).
- **`top_products_last_days`** (`analytics`, `sales`, `catalog`):
  - Top products by revenue for the last `N` days.
- **`top_customers_last_days`** (`analytics`, `sales`, `customer`):
  - Top customers by revenue for the last `N` or 90 days.
- **`repeat_purchase_rate`** (`analytics`, `customer`):
  - Share of customers with 2+ orders over the chosen window.
- **`gross_margin_last_days`** (`analytics`, `finance`):
  - Revenue, cost, gross margin, and margin rate for the last `N` days.

#### Operations and reporting

- **`low_stock`** (`ops`, `inventory`):
  - Lists low-stock items (requires either a `v_inventory_on_hand` view or an `inventory` table).
- **`ops_health_report`** (`ops`, `report`):
  - Markdown report summarising order status mix, backlog, and inventory risks.
- **`sales_report`** (`analytics`, `report`, `sales`):
  - One-page Markdown sales report with KPIs, daily trend, and top products.

#### Dashboards

- **`sales_dashboard`** (`analytics`, `report`, `charts`):
  - Generates a 2×2 PNG dashboard (revenue trend, orders trend, top products, KPI tiles).
  - Returns both a Markdown description and the PNG image bytes.

#### SQL (read-only)

- **`sql_readonly`** (`sql`):
  - Executes a **single** read-only SQL statement (`SELECT`/`WITH`/`SHOW`/`EXPLAIN` only).
  - Enforces:
    - Normalised SQL with trailing semicolons stripped.
    - No internal semicolons (single statement only).
    - Server-side statement timeout (configurable via `timeout_ms`).
    - Row limit (`max_rows`).

#### Seeding and demo data

- **`seed_demo_data`** (`seed`, `demo`):
  - Inserts realistic demo e-commerce data, optionally truncating existing data first.
  - **Requires** `ALLOW_WRITES=true` (or `1`); otherwise it raises a permission error.
  - Supports sizes:
    - **`small`**: ~50 customers, 150 products, 600 orders.
    - **`medium`**: ~300 customers, 900 products, 7,000 orders.
    - **`large`**: ~1,500 customers, 4,000 products, 40,000 orders.

---

### Prompt helpers

The server also registers several **MCP prompts** that guide an AI agent to use the
tools effectively:

- **`weekly_exec_brief`**:
  - One-page executive brief for the last _N_ days (KPIs, changes, risks, and actions).
- **`sales_deep_dive`**:
  - Detailed sales analysis (trend, drivers, profitability, and recommendations).
- **`investigate_revenue_drop`**:
  - Root-cause style playbook comparing recent performance vs a prior window.
- **`ops_triage`**:
  - Operations triage focusing on backlog, status mix, and inventory risks.
- **`inventory_reorder_plan`**:
  - Inventory plan combining low-stock lists with sales velocity.
- **`data_quality_smoke_test`**:
  - Quick data-quality pass after seeding or schema changes.

These prompts are defined to strongly prefer using the built-in analytics tools and
`sql_readonly` instead of ad-hoc SQL.

---

### Expected schema (high level)

The server is designed to adapt to common e-commerce schemas via reflection, but works
best when the following tables (or equivalents) exist in the `public` schema:

- **`customers`**:
  - **Recommended columns**: `customer_id`, `email`, `full_name`.
- **`categories`** (optional but used by the seeder):
  - **Recommended columns**: `category_id`, `name`, `slug`.
- **`products`**:
  - **Recommended columns**: `product_id`, `sku`, `name`, `category_id`, `price`,
    and ideally `cost`, `currency_code`, `attributes`, `is_active`.
- **`orders`**:
  - **Required/expected columns** (or compatible alternatives):
    - Timestamp: one of `placed_at`, `ordered_at`, `created_at`, `order_date`.
    - Total: one of `total_amount`, `grand_total`, `total`.
    - Optional: `status`, `order_number`, `currency_code`,
      `subtotal_amount`, `discount_amount`, `tax_amount`, `shipping_amount`.
- **`order_items`**:
  - **Required for seeding and analytics**:
    - Quantity: `quantity` or `qty`.
    - Pricing/snapshots: `unit_price`, `sku_snapshot`, `name_snapshot`.
  - **Optional but recommended**:
    - `unit_cost`, `line_subtotal`, `line_total`, `item_discount`, `item_tax`.
- **Inventory**:
  - Either a `v_inventory_on_hand` view or an `inventory` table, with an `on_hand`
    or `quantity_on_hand` column, plus a relation to `products`.
- **Stock movements** (optional):
  - `stock_movements` table for initial and sales-related stock movements, used by the seeder
    when present.

The code attempts to pick the right columns dynamically and will raise clear runtime errors
if expected tables or columns are missing.

---

### Safety and best practices

- **Prefer analytics/reporting tools over raw SQL**:
  - Use `revenue_by_day`, `sales_report`, `ops_health_report`, etc. before `sql_readonly`.
- **Lock down writes in production**:
  - Set `ALLOW_WRITES=false` so that only read-only tools can be used in shared or production
    environments.
- **Refresh schema cache after migrations**:
  - Run `refresh_schema_cache` after altering tables so that reflection stays accurate.

---

### Development

- **Code style**: The project is configured with `ruff` (see `[tool.ruff]` in `pyproject.toml`)
  for linting and formatting conventions.
- **Editable install for local changes**:

```bash
pip install -e .
```

You can then run `ecom-mcp` from your virtual environment while iterating on the code.


