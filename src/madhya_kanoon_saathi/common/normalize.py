"""Shared text normaliser for everything that is compared or indexed (CLAUDE.md; DEC-026).

`normalize()` is lossy on purpose: it builds comparison keys (BM25 tokens, quote checks,
OCR metrics), never the text we store or show. Steps, in order:

1. Unicode NFC, so the same visible text has one code-point sequence.
2. Drop invisible format characters that PDFs and OCR engines insert inconsistently:
   ZWSP U+200B, ZWNJ U+200C, ZWJ U+200D, BOM/ZWNBSP U+FEFF, soft hyphen U+00AD.
3. Nukta folding: remove the Devanagari nukta U+093C, so "ज़रूरी" and "जरूरी" compare equal.
   The precomposed nukta letters (U+0929, U+0931, U+0934, U+0958-U+095F) are decomposed
   first so they fold too.
4. Optionally collapse runs of whitespace to one space and strip the ends.

Why fold the nukta: users (and OCR) often omit it, and in legal text it never distinguishes
two provisions.
"""

from __future__ import annotations

import re
import unicodedata

NUKTA = "़"
_INVISIBLE = dict.fromkeys(map(ord, "​‌‍﻿­"))
# Letters whose canonical decomposition is <base, NUKTA>.
_NUKTA_LETTERS = {
    ch: unicodedata.normalize("NFD", ch)[0]
    for ch in map(chr, (0x0929, 0x0931, 0x0934, *range(0x0958, 0x0960)))
}
_FOLD = {ord(k): v for k, v in _NUKTA_LETTERS.items()} | {ord(NUKTA): None}
_SPACE = re.compile(r"\s+")


def normalize(text: str, *, fold_nukta: bool = True, collapse_space: bool = False) -> str:
    """Return the comparison form of `text` (see module docstring)."""
    out = unicodedata.normalize("NFC", text).translate(_INVISIBLE)
    if fold_nukta:
        out = out.translate(_FOLD)
    if collapse_space:
        out = _SPACE.sub(" ", out).strip()
    return out
