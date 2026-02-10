from __future__ import annotations

import os
import socket
import sys
from typing import Literal, cast

from app.mcp_server import create_mcp_server

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 18081
DEFAULT_TRANSPORT = "stdio"
DEFAULT_STREAMABLE_HTTP_PATH = "/mcp"
DEFAULT_SSE_MOUNT_PATH = "/"


def _resolve_port(raw_value: str) -> int:
    try:
        port = int(raw_value)
    except ValueError as exc:
        raise ValueError("MCP_PORT must be an integer") from exc

    if not 10000 <= port <= 99999:
        raise ValueError("MCP_PORT must be a 5-digit number (10000-99999)")

    return port


def _is_port_free(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
    except OSError:
        return False
    finally:
        sock.close()

    return True


def _resolve_transport(raw_value: str) -> Literal["stdio", "streamable-http", "sse"]:
    transport = raw_value.strip().lower()
    if transport not in {"stdio", "streamable-http", "sse"}:
        raise ValueError("MCP_TRANSPORT must be one of: stdio, streamable-http, sse")
    return cast(Literal["stdio", "streamable-http", "sse"], transport)


def main() -> None:
    raw_transport = os.getenv("MCP_TRANSPORT", DEFAULT_TRANSPORT)
    host = os.getenv("MCP_HOST", DEFAULT_HOST)
    raw_port = os.getenv("MCP_PORT", str(DEFAULT_PORT))
    streamable_http_path = os.getenv("MCP_STREAMABLE_HTTP_PATH", DEFAULT_STREAMABLE_HTTP_PATH)
    sse_mount_path = os.getenv("MCP_SSE_MOUNT_PATH", DEFAULT_SSE_MOUNT_PATH)

    try:
        transport = _resolve_transport(raw_transport)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    if transport == "stdio":
        server = create_mcp_server()
        server.run(transport="stdio")
        return

    try:
        port = _resolve_port(raw_port)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    if not _is_port_free(host, port):
        print(f"Port {port} is already in use. Choose another free port.", file=sys.stderr)
        raise SystemExit(1)

    server = create_mcp_server(
        host=host,
        port=port,
        streamable_http_path=streamable_http_path,
    )

    if transport == "sse":
        server.run(transport="sse", mount_path=sse_mount_path)
        return

    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
