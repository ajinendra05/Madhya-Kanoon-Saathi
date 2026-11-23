"""Fill the three app secrets in Secret Manager (DEC-086, DEC-089). Run once, by Malik.

    uv run python scripts/set_app_secrets.py

- TELEGRAM_BOT_TOKEN, SARVAM_API_KEY: copied from the environment or the local .env
  (common/env.secret; the values are never printed).
- TELEGRAM_WEBHOOK_SECRET: generated here (Telegram allows 1-256 chars of A-Z a-z 0-9 _ -,
  core.telegram.org/bots/api#setwebhook); it only ever exists in Secret Manager.

Each value is handed to gcloud on stdin, never on the command line or in a file. A secret that
already has a version is skipped, so re-running is safe. Prints only gcloud's status lines.
"""

from __future__ import annotations

import secrets
import shutil
import subprocess
import sys

from madhya_kanoon_saathi.common.env import secret

PROJECT = "mks-prod-515410"


def has_version(gcloud: str, name: str) -> bool:
    out = subprocess.run(
        [gcloud, "secrets", "versions", "list", name, "--project", PROJECT, "--format=value(name)"],
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(out.stdout.strip())


def add(gcloud: str, name: str, value: str) -> int:
    done = subprocess.run(
        [gcloud, "secrets", "versions", "add", name, "--project", PROJECT, "--data-file=-"],
        input=value.encode("utf-8"),
        capture_output=True,
    )
    print(done.stderr.decode("utf-8", "replace").strip())  # status only, never the value
    return done.returncode


def main() -> int:
    # Windows: the SDK ships a bash script "gcloud" next to "gcloud.cmd"; only the .cmd runs here
    gcloud = shutil.which("gcloud.cmd") if sys.platform == "win32" else None
    gcloud = gcloud or shutil.which("gcloud")
    if not gcloud:
        print("gcloud not found on PATH; reopen the terminal")
        return 1
    values = {
        "TELEGRAM_BOT_TOKEN": lambda: secret("TELEGRAM_BOT_TOKEN"),
        "SARVAM_API_KEY": lambda: secret("SARVAM_API_KEY"),
        "TELEGRAM_WEBHOOK_SECRET": lambda: secrets.token_urlsafe(48),
    }
    failed = 0
    for name, make in values.items():
        if has_version(gcloud, name):
            print(f"{name}: already set, skipped")
            continue
        failed |= add(gcloud, name, make())
    return failed


if __name__ == "__main__":
    sys.exit(main())
