"""The image gets exactly the runtime files (DEC-086): Dockerfile and .dockerignore agree."""

from __future__ import annotations

import re
from pathlib import Path

DOCKERFILE = Path("docker/Dockerfile").read_text(encoding="utf-8")
ALLOWED = {
    line[1:].strip()
    for line in Path(".dockerignore").read_text(encoding="utf-8").splitlines()
    if line.startswith("!")
}


def copied_sources() -> list[str]:
    text = DOCKERFILE.replace("\\n", " ")
    out: list[str] = []
    for line in text.splitlines():
        m = re.match(r"\s*COPY\s+(?!--from)(.+)", line)
        if m:
            out += [p.rstrip("/") for p in m.group(1).split()[:-1]]
    return out


def test_every_copied_path_is_allowed_by_dockerignore() -> None:
    for src in copied_sources():
        assert src in ALLOWED, f"{src} is copied but excluded by .dockerignore"


def test_secrets_and_bulky_data_are_never_allowed() -> None:
    assert ".env" not in ALLOWED and not any(a.startswith(".env") for a in ALLOWED)
    for banned in ("data/raw", "data/ocr", "data/spend", "data/logs", "data/golden"):
        assert not any(a.startswith(banned) for a in ALLOWED), banned
    assert not any("fp32" in a for a in ALLOWED)


def test_dockerignore_starts_by_denying_everything() -> None:
    first = next(
        ln.strip()
        for ln in Path(".dockerignore").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    )
    assert first == "*"


def test_runtime_files_exist_locally() -> None:
    for src in copied_sources():
        assert Path(src).exists(), src


def test_base_images_are_pinned_by_digest() -> None:
    froms = re.findall(r"^FROM\s+(\S+)", DOCKERFILE, flags=re.M)
    assert froms and all("@sha256:" in f for f in froms)
