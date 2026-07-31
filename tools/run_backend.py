"""Launch the DOPE Engine dev HTTP server (uvicorn).

Usage:
    python tools/run_backend.py [--host 127.0.0.1] [--port 8000] [--reload]

Data files are read from data/ at the repo root; override with the
DOPE_DATA_DIR environment variable if needed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

import uvicorn  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "dope_engine.adapters.http.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
