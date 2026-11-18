"""Read a secret by name. The environment comes first (production: injected from SSM, DEC-009),
else a local ``.env`` file. Values are never printed, logged or put into error messages.
(Module named env.py because .gitignore blocks file names containing "secrets".)"""

from __future__ import annotations

import os
from pathlib import Path


def secret(name: str, env_file: Path = Path(".env")) -> str:
    value = os.environ.get(name, "").strip()
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, _, raw = line.partition("=")
            if key.strip() == name:
                value = raw.strip().strip('"').strip("'")
    if not value:
        raise RuntimeError(f"{name} is not set (.env locally, SSM in production)")
    return value
