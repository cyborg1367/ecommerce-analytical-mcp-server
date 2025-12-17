from __future__ import annotations

from app.config.logging import configure_logging
from app.config.settings import Settings
from app.container import build_container
from app.presentation.mcp_server import build_mcp_server


def main() -> None:
    settings = Settings()  # loads .env automatically
    configure_logging(settings.log_level)

    container = build_container(settings)
    mcp = build_mcp_server(container)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
