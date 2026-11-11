# Spec: `section_uid` and `chunk_id` (DEC-040)

Code: `src/madhya_kanoon_saathi/common/section_uid.py` · Tests: `tests/unit/test_section_uid.py`

## Why one ID matters
Chunks, golden-set rows, citations, eval scores and law-watch alerts all point at law through this ID.
It names the **provision** (e.g. "RTI Act s.8(1)(j)"), not one language or version of its text.

## Format
```
section_uid = <JUR> "." <CODE><YEAR> { ":" <segment> }
chunk_id    = <section_uid> "@" <lang> "@" <version> [ "~" <part> ]
version     = <YYYY-MM-DD> | "nd-" <first 8 hex of the document sha256>
```
- **version** (DEC-055 7d, DEC-056): the document's `valid_from`; else the provision's commencement override; else
  the latest amendment affecting the provision; else the instrument's `commenced_on`; else `enacted_on`; else
  `nd-<sha8>`. Never the fetch date.
- **part** (DEC-055 item 3): only when one clause is too long and is split; the first piece has no suffix, later
  pieces are `~2`, `~3`, ...
- `JUR`: `IN` (central) or `MP` (Madhya Pradesh). Visible in every log and citation; backs the jurisdiction guard (DEC-033.5).
- `CODE`: uppercase letters/digits starting with a letter; `YEAR`: 4 digits. Each instrument is listed once in the
  manifest (`docs/specs/manifest.md`) with its full Hindi/English titles.
- A uid with no segments means the whole instrument.
- Canonical uids are **ASCII only**. Devanagari digits or letters are rejected here; converting free-text references
  is the tokeniser's job (DEC-026).

## Segments
| Segment | Meaning | Shape | Level |
| --- | --- | --- | --- |
| `s<n>[A]` | section (inserted: `s13A`) | `s8`, `s13A` | top |
| `r<n>[A]` | rule | `r4` | top |
| `reg<n>[A]` | regulation | `reg5` | top |
| `para<n>[A]` | paragraph (top, or inside a schedule) | `para3` | top |
| `sch<n>[A]` | schedule | `sch1` | top |
| `form_<x>` | form | `form_a` | top |
| `ss<n>[A]` | sub-section / sub-rule | `ss1` | 1 |
| `cl_<a..zzz>` | clause, **alphabetic** numbering | `cl_j`, `cl_ja` | 2 |
| `clr_<roman>` | clause, **roman** numbering (DEC-045) | `clr_vii` | 2 |
| `scl_<roman>` | sub-clause, roman (must follow a clause) | `scl_ii` | 3 |
| `scla_<a..zzz>` | sub-clause, alphabetic (must follow a clause) | `scla_b` | 3 |
| `prov<n>` | proviso (n-th, attached to its parent) | `prov2` | last |
| `expl<n>` | explanation | `expl1` | last |

Numbering systems (DEC-045 item 7, U1): clauses and sub-clauses keep the system printed in the source. The segment
**kind** records it, so letter "(i)" is `cl_i` and numeral "(i)" is `clr_i`; they are different units. Roman values
must be canonical lowercase numerals 1–3999 (`iv`, not `iiii`). Hindi sources use Devanagari words or letters (e.g.
"(सात)"); they are mapped by structural alignment with the English text (rule 2), never written into the uid.

Order rules: the first segment is top-level; each next segment must be deeper; `para` may follow `sch`;
`prov`/`expl` end the uid. Numbers have no leading zeros and start at 1.

Examples (shapes only): `IN.RTI2005:s8:ss1:cl_j` · `MP.ACA1961:s12:ss1:cl_a` · `IN.COW2019:s17:prov2` ·
`IN.RTIR2012:r4` · `IN.CPA2019:sch1:para3`.

## Rules
1. **Provision, not version.** Each language and each amended text is a separate chunk with its own `chunk_id`.
   The citation validator checks `chunk_id`; eval scores on `section_uid`.
2. **Hindi alignment.** Hindi chunks get uids by matching the English structure position by position. Never map
   Devanagari clause letters to Latin ones (the sequences don't line up reliably).
3. **Parents are computed** from the uid (`parent()`, `ancestors()`), never stored separately. Chunks may carry a
   copy of `parent_uid` for speed, written at build time from the same function.
4. **Coverage (eval):** `covers(retrieved, expected)` is true if equal or the retrieved uid is an ancestor.
   Character prefixes don't count (`s1` does not cover `s10`).
5. **State amendments to a central Act** keep the central uid; the MP text is a separate version whose
   `applies_to` is MP only (manifest override).
6. `chunk_id` languages are `hi` and `en` only (DEC-016).
