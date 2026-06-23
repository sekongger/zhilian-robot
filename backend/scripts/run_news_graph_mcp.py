#!/usr/bin/env python3
"""Run the read-only IncCore news graph MCP sidecar."""

from __future__ import annotations

import argparse
import os

from app.news_graph_mcp.server import create_mcp_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IncCore news graph MCP server.")
    parser.add_argument("--transport", choices=("sse", "stdio"), default=os.getenv("NEWS_GRAPH_MCP_TRANSPORT", "sse"))
    parser.add_argument("--port", type=int, default=int(os.getenv("NEWS_GRAPH_MCP_PORT", "3010")))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = create_mcp_server(port=args.port)
    server.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
