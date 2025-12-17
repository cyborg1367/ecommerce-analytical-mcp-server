from __future__ import annotations

from fastmcp import FastMCP

from app.container import Container

from app.presentation.tools.health_tools import register as register_health
from app.presentation.tools.schema_tools import register as register_schema
from app.presentation.tools.sql_tools import register as register_sql
from app.presentation.tools.analytics_tools import register as register_analytics
from app.presentation.tools.ops_tools import register as register_ops
from app.presentation.tools.seed_tools import register as register_seed
from app.presentation.tools.dashboard_tools import register as register_dashboards

from app.presentation.prompts.prompts import register as register_prompts


def build_mcp_server(container: Container) -> FastMCP:
    mcp = FastMCP(
        name="ecom-postgres",
        instructions=(
            "Postgres tools for an e-commerce database + analytics. "
            "Prefer report/analytics tools over raw SQL. Use sql_readonly only when needed."
        ),
    )

    register_health(mcp, container)
    register_schema(mcp, container)
    register_sql(mcp, container)
    register_analytics(mcp, container)
    register_ops(mcp, container)
    register_seed(mcp, container)
    register_prompts(mcp, container)
    register_dashboards(mcp, container)

    return mcp
