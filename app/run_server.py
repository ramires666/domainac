from __future__ import annotations

import os
import socket
import sys

import uvicorn

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 18080


def _resolve_port(raw_value: str) -> int:
    try:
        port = int(raw_value)
    except ValueError as exc:
        raise ValueError("PORT must be an integer") from exc

    if not 10000 <= port <= 99999:
        raise ValueError("PORT must be a 5-digit number (10000-99999)")

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


def main() -> None:
    host = os.getenv("HOST", DEFAULT_HOST)
    raw_port = os.getenv("PORT", str(DEFAULT_PORT))

    try:
        port = _resolve_port(raw_port)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    if not _is_port_free(host, port):
        print(f"Port {port} is already in use. Choose another free port.", file=sys.stderr)
        raise SystemExit(1)

    uvicorn.run("app.main:app", host=host, port=port)


if __name__ == "__main__":
    main()
