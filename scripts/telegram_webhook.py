"""Point the Telegram bot at the cloud ingress, check it, or switch back to local polling.

    uv run python scripts/telegram_webhook.py set <ingress_url>   # go live (DEC-086)
    uv run python scripts/telegram_webhook.py info                # url, pending, last error
    uv run python scripts/telegram_webhook.py delete              # back to scripts/run_bot.py

The bot token and webhook secret are read from Secret Manager into memory with gcloud and never
printed. setWebhook (core.telegram.org/bots/api#setwebhook, read 2026-11-21): ``secret_token`` is
sent back in the ``X-Telegram-Bot-Api-Secret-Token`` header; ``allowed_updates`` = messages only;
``drop_pending_updates`` skips a backlog so the cloud bot does not answer old messages;
``max_connections`` caps parallel deliveries. While a webhook is set, local polling (getUpdates)
fails with 409, so the laptop bot cannot run at the same time.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from madhya_kanoon_saathi.bot.telegram import TelegramClient

PROJECT = "mks-prod-515410"


def from_secret_manager(name: str) -> str:
    gcloud = (shutil.which("gcloud.cmd") if sys.platform == "win32" else None) or shutil.which(
        "gcloud"
    )
    if not gcloud:
        raise SystemExit("gcloud not found on PATH")
    out = subprocess.run(
        [gcloud, "secrets", "versions", "access", "latest", "--secret", name, "--project", PROJECT],
        capture_output=True,
        check=True,
    )
    return out.stdout.decode("utf-8").strip()


def info(client: TelegramClient) -> None:
    w = client.call("getWebhookInfo", {})
    print(f"url: {w.get('url') or '(none: local polling mode)'}")
    print(f"pending updates: {w.get('pending_update_count', 0)}")
    print(f"allowed updates: {w.get('allowed_updates', 'default')}")
    if w.get("last_error_message"):
        print(f"last error: {w['last_error_message']} (unix time {w.get('last_error_date')})")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("set", "info", "delete"):
        print(__doc__)
        return 2
    client = TelegramClient(from_secret_manager("TELEGRAM_BOT_TOKEN"), timeout=30)
    cmd = sys.argv[1]
    if cmd == "set":
        if len(sys.argv) != 3 or not sys.argv[2].startswith("https://"):
            print("usage: set https://<ingress-url>")
            return 2
        client.call(
            "setWebhook",
            {
                "url": sys.argv[2].rstrip("/") + "/",
                "secret_token": from_secret_manager("TELEGRAM_WEBHOOK_SECRET"),
                "allowed_updates": ["message"],
                "drop_pending_updates": True,
                "max_connections": 10,
            },
        )
        print("webhook set")
    elif cmd == "delete":
        client.call("deleteWebhook", {"drop_pending_updates": False})
        print("webhook removed; local polling (scripts/run_bot.py) works again")
    info(client)
    return 0


if __name__ == "__main__":
    sys.exit(main())
