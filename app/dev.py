"""Dev server with automatic port fallback when the preferred port is taken."""

from __future__ import annotations

import os
import socket
import subprocess
import sys


def find_free_port(start: int, attempts: int = 100) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port found in range {start}-{start + attempts - 1}")


def main() -> None:
    preferred = int(os.environ.get("PORT", "8000"))
    port = find_free_port(preferred)
    if port != preferred:
        print(f"Port {preferred} in use — starting on http://127.0.0.1:{port}")

    cmd = ["fastapi", "dev", "--port", str(port), *sys.argv[1:]]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
