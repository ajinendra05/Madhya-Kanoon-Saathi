"""Create version 1 of the MKS_CHAT_HASH_KEY secret (DEC-087). Run once, by Malik.

    uv run python scripts/set_chat_hash_key.py

Generates 64 random hex characters and hands them to gcloud in memory (stdin), so the value is
never printed, written to a file, or passed through a PowerShell pipe. Refuses to run if the
secret already has a version: a new key would break the link between old and new chat hashes.
"""

from __future__ import annotations

import secrets
import shutil
import subprocess
import sys

PROJECT = "mks-prod-515410"
SECRET = "MKS_CHAT_HASH_KEY"


def main() -> int:
    # Windows: the SDK ships a bash script "gcloud" next to "gcloud.cmd"; only the .cmd runs here
    gcloud = shutil.which("gcloud.cmd") if sys.platform == "win32" else None
    gcloud = gcloud or shutil.which("gcloud")
    if not gcloud:
        print("gcloud not found on PATH; reopen the terminal after installing the Google Cloud SDK")
        return 1
    base = [gcloud, "secrets", "versions"]
    listed = subprocess.run(
        [*base, "list", SECRET, "--project", PROJECT, "--format=value(name)"],
        capture_output=True,
        text=True,
    )
    if listed.returncode != 0:
        print("could not list versions:\n" + listed.stderr)
        return 1
    if listed.stdout.strip():
        print(f"{SECRET} already has a version; nothing done (a new key would break chat hashes)")
        return 1
    added = subprocess.run(
        [*base, "add", SECRET, "--project", PROJECT, "--data-file=-"],
        input=secrets.token_hex(32).encode("ascii"),
        capture_output=True,
    )
    # gcloud reports on stderr; it never echoes the secret value
    print(added.stderr.decode("utf-8", "replace").strip())
    return added.returncode


if __name__ == "__main__":
    sys.exit(main())
