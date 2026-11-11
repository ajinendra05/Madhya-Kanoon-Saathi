"""HTML guides: markup shapes copied from the saved pages (IN.ESHRAMFAQ2026@en@1, MP.SLSALAGUIDE2025@en@1)."""

from dataclasses import replace

from madhya_kanoon_saathi.ingestion.chunker import build_chunks, qa
from madhya_kanoon_saathi.ingestion.html_guide import parse_faq, parse_headed

FAQ = """<html><body><nav><a>Home</a></nav><div class="container faqcontainer"><div class="accordion">
<div class="panel"><h4 class="panel-title"><a href="#collapse29" id="heading29">Q - 29. Are there any income criteria?</a></h4>
<div class="panel-collapse collapse" id="collapse29"><div class="panel-body">There are no income criteria for
registering on eShram as unorganised worker.</div></div></div>
<div class="panel"><h4 class="panel-title"><a href="#collapse31" id="heading31">Q - 31. What essential documents are required?</a></h4>
<div class="panel-collapse collapse" id="collapse31"><div class="panel-body">Following is required by the worker:
<ul><li>Aadhaar Number.</li><li>Aadhaar linked Mobile number.</li></ul></div></div></div>
</div></div><script>var x = 1;</script></body></html>"""

HEADED = """<html><body><button>High Contrast</button><main>
<h2>1. Legal Services</h2><h3>What is legal aid?</h3><p>Legal Aid is the method adopted to provide legal services.</p>
<h3>Who are Entitled to Free Legal Services?</h3><ul><li>A member of a Scheduled Caste or Scheduled Tribe.</li>
<li>A woman or a child.</li></ul><h2>Useful Links</h2><ul><li>NALSA</li></ul></main></body></html>"""


def test_faq_one_unit_per_question_with_answer_anchor() -> None:
    parsed = parse_faq("IN.ESHRAMFAQ2026", FAQ)
    assert [u.uid for u in parsed.units] == ["IN.ESHRAMFAQ2026:para29", "IN.ESHRAMFAQ2026:para31"]
    q31 = parsed.units[1]
    assert q31.selector == "#collapse31" and q31.heading == "What essential documents are required?"
    assert [ln.text for ln in q31.lines][-2:] == [
        "Aadhaar Number.",
        "Aadhaar linked Mobile number.",
    ]
    assert all(ln.para_start for ln in q31.lines)
    assert not any("var x" in ln.text or "Home" in ln.text for u in parsed.units for ln in u.lines)


def test_headed_page_sections_stop_at_useful_links() -> None:
    parsed = parse_headed("MP.SLSALAGUIDE2025", HEADED)
    assert [u.uid.split(":", 1)[1] for u in parsed.units] == ["para1", "para1:sp1", "para1:sp2"]
    assert parsed.units[2].selector == "(//h3)[2]"
    assert not any("NALSA" in ln.text for u in parsed.units for ln in u.lines)


def test_html_chunks_get_html_locator_and_keep_blocks_as_paragraphs() -> None:
    from test_chunker import DOC, INST  # shared fixtures

    doc = replace(
        DOC,
        doc_id="IN.ESHRAMFAQ2026@en@1",
        instrument_id="IN.ESHRAMFAQ2026",
        content_type="text/html",
        source_url="https://eshram.gov.in/faqs",
    )
    inst = replace(INST, instrument_id="IN.ESHRAMFAQ2026", type="official_guide", commenced_on=None)
    res = qa(build_chunks(parse_faq("IN.ESHRAMFAQ2026", FAQ), doc, inst, [], "html"))
    assert res.errors == []
    c = res.chunks[1]
    assert c.locator == {
        "kind": "html",
        "url": "https://eshram.gov.in/faqs",
        "selector": "#collapse31",
        "heading_path": [
            "Frequently Asked Questions",
            "31. What essential documents are required?",
        ],
    }
    assert c.text.endswith(
        "Following is required by the worker:\nAadhaar Number.\nAadhaar linked Mobile number."
    )
