"""Guard: no control or invisible characters in Python source.

Background (2026-11-10/11): editing tools twice turned escapes like a backslash-b regex word boundary
or a zero-width-joiner escape into the raw characters, silently breaking a regex and hiding characters
from reviewers. Write such characters as escapes instead.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = {
    0x08: "backspace",
    0x200B: "zero-width space",
    0x200C: "zero-width non-joiner",
    0x200D: "zero-width joiner",
    0xFEFF: "byte-order mark",
    0x00AD: "soft hyphen",
}


def test_python_sources_have_no_invisible_characters() -> None:
    bad = []
    for folder in ("src", "scripts", "tests"):
        for f in (ROOT / folder).rglob("*.py"):
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                for ch in line:
                    if ord(ch) in FORBIDDEN:
                        bad.append(f"{f.relative_to(ROOT)}:{n}: {FORBIDDEN[ord(ch)]}")
    assert bad == []
