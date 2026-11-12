"""BM25 index and filters (DEC-058). Chunk texts are shortened from the built chunks (data/parsed, 2026-11-11)."""

from datetime import date
from pathlib import Path

from madhya_kanoon_saathi.retrieval.bm25_index import Bm25Index, contained_tokens
from madhya_kanoon_saathi.retrieval.filters import current_ok, eligible, flags, jurisdiction_ok

DAY = date(2026, 11, 11)


def chunk(cid: str, text: str, heading: str = "", **meta: object) -> dict:
    uid = cid.split("@")[0]
    base = {
        "chunk_id": cid,
        "section_uid": uid,
        "doc_id": uid.split(":")[0] + "@en@1",
        "jurisdiction": uid[:2],
        "lang": "en",
        "status": "in_force",
        "applies_to": {"level": "national"},
        "valid_from": None,
        "valid_to": None,
        "expires_on": None,
        "text": text,
        "heading": heading,
    }
    base.update(meta)
    return base


CHUNKS = [
    chunk(
        "IN.RTI2005:s8:ss1@en@2025-11-13",
        "8. Exemption from disclosure of information.—(1) Notwithstanding anything contained in this Act, "
        "there shall be no obligation to give any citizen,—\n(a) information, disclosure of which would "
        "prejudicially affect the sovereignty\n[(j) information which relates to personal information;]",
        "Exemption from disclosure of information",
    ),
    chunk(
        "IN.ESHRAMFAQ2026:para29@en@nd-7c0ac8de",
        "Q - 29. Are there any income criteria?\nThere are no income criteria for registering on eShram as "
        "unorganised worker.",
    ),
    chunk(
        "MP.MWVDAOCT2026:s1@hi@2026-10-01",
        "minimum wages unskilled 12575",
        applies_to={"level": "state", "states": ["MP"]},
        valid_from="2026-10-01",
        valid_to="2027-03-31",
    ),
    chunk("IN.MTA2021:s2:cl_j@en@nd-e83830bf", "(j) tenancy agreement", status="model_law"),
]


def test_contained_clause_tokens() -> None:
    assert contained_tokens(CHUNKS[0]) == ["s8_1_a", "s8_1_j"]


def test_search_ranks_reference_and_words() -> None:
    ix = Bm25Index.build(CHUNKS)
    assert ix.search("RTI dhara 8(1)(j) personal information", on=DAY)[0].chunk_id.startswith(
        "IN.RTI2005:s8:ss1"
    )
    assert ix.search("eshram income criteria", on=DAY)[0].chunk_id.startswith(
        "IN.ESHRAMFAQ2026:para29"
    )
    assert ix.search("", on=DAY) == [] and ix.search("zzzz", on=DAY) == []


def test_filters_after_scoring() -> None:
    ix = Bm25Index.build(CHUNKS)
    assert [h.chunk_id[:15] for h in ix.search("minimum wages", on=DAY)] == ["MP.MWVDAOCT2026"]
    assert ix.search("minimum wages", on=date(2027, 4, 1)) == []  # past valid_to
    assert ix.search("minimum wages", on=DAY, states=frozenset({"UP"})) == []  # jurisdiction guard
    hit = ix.search("tenancy agreement", on=DAY)[0]
    assert hit.flags == ["model_law"]  # kept, but flagged for the answer layer


def test_filter_functions() -> None:
    assert jurisdiction_ok({"applies_to": {"level": "national"}})
    assert not jurisdiction_ok({"applies_to": {"level": "state", "states": ["UP"]}})
    assert not current_ok({"status": "repealed"}, DAY)
    assert not current_ok({"expires_on": "2026-03-31"}, DAY)
    assert eligible({"status": "draft", "applies_to": {"level": "state", "states": ["MP"]}}, DAY)
    assert flags({"status": "draft"}) == ["draft"] and flags({"status": "in_force"}) == []


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    ix = Bm25Index.build(CHUNKS)
    ix.save(tmp_path / "bm25")
    back = Bm25Index.load(tmp_path / "bm25")
    q = "eshram income criteria"
    assert [h.chunk_id for h in back.search(q, on=DAY)] == [
        h.chunk_id for h in ix.search(q, on=DAY)
    ]
    assert back.vocab_size == ix.vocab_size


def test_instrument_title_and_alias_tokens_dec_059() -> None:
    from madhya_kanoon_saathi.retrieval.bm25_index import instrument_tokens

    # IN.RTI2005 title_hi from the official India Code Hindi PDF p.1
    extra = instrument_tokens(
        {"IN.RTI2005": ("The Right to Information Act, 2005", "सूचना का अधिकार अधिनियम, 2005")},
        {"IN.RTI2005": ["RTI"]},
    )
    assert {"right", "information", "act", "2005", "सूचना", "अधिकार", "अधिनियम", "rti"} <= set(
        extra["IN.RTI2005"]
    )
    ix = Bm25Index.build(CHUNKS, extra)
    # a Hindi Act name now reaches the English RTI chunk
    assert ix.search("सूचना का अधिकार", on=DAY)[0].chunk_id.startswith("IN.RTI2005")
