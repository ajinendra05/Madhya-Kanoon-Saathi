"""Tests for the corpus downloader. No internet: a fake downloader or a localhost server."""

import http.server
import io
import json
import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfWriter

from madhya_kanoon_saathi.ingestion import fetch
from madhya_kanoon_saathi.ingestion.fetch import (
    USER_AGENT,
    detect_text_layer,
    fetch_all,
    http_download,
    local_name,
    validate_sources,
)

# ----------------------------------------------------------------------------- PDF fixtures


def _text_pdf(pages: list[str]) -> bytes:
    """Minimal valid PDF; an empty string makes a page with no text (like a scan)."""
    objects: list[bytes] = []
    n = len(pages)
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode())
    font_id = 3 + 2 * n
    for i, text in enumerate(pages):
        content_id = 4 + 2 * i
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_id} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode()
        )
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode() if text else b""
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return out.getvalue()


LONG = "This sample page has plenty of extractable text for detection"


def _blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_text_layer_detection() -> None:
    assert detect_text_layer(_text_pdf([LONG, LONG]), "application/pdf") == "born_digital"
    assert detect_text_layer(_blank_pdf(), "application/pdf") == "scanned"
    assert detect_text_layer(_text_pdf([LONG, ""]), "application/pdf") == "mixed"
    assert detect_text_layer(b"<html>hi</html>", "text/html") == "born_digital"


def test_latin_ocr_layer_in_hindi_document_counts_as_scanned() -> None:
    # Real case: a Hindi scan whose embedded OCR layer is Latin garbage (0% Devanagari).
    pdf = _text_pdf([LONG])
    assert detect_text_layer(pdf, "application/pdf", "en") == "born_digital"
    assert detect_text_layer(pdf, "application/pdf", "hi") == "scanned"
    assert detect_text_layer(pdf, "application/pdf") == "born_digital"


def test_unreadable_pdf_raises() -> None:
    with pytest.raises(ValueError):
        detect_text_layer(b"%PDF-1.4 garbage", "application/pdf")


def test_local_name() -> None:
    assert local_name("IN.X2000@en@1", "application/pdf", "https://a/b") == "IN.X2000_en_1.pdf"
    assert local_name("IN.X2000@hi@1", "text/html", "https://a/b") == "IN.X2000_hi_1.html"


# ----------------------------------------------------------------------------- end to end


def _instrument() -> dict[str, Any]:
    return {
        "instrument_id": "IN.TESTACT2000",
        "type": "act",
        "jurisdiction": "IN",
        "title_en": "Test Act, 2000",
    }


def _source(doc_id: str = "IN.TESTACT2000@en@1", **extra: Any) -> dict[str, Any]:
    row = {
        "doc_id": doc_id,
        "instrument_id": "IN.TESTACT2000",
        "url": "https://example.gov.in/act.pdf",
        "language": "en",
        "status": "in_force",
        "publisher": "Example ministry",
        "applies_to": {"level": "national"},
        "target_mode": "index",
    }
    row.update(extra)
    return row


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema_version": 1, "instruments": [_instrument()], "documents": []}),
        encoding="utf-8",
    )
    _write_sources(tmp_path, [_source()])
    return tmp_path


def _write_sources(root: Path, rows: list[dict[str, Any]]) -> None:
    (root / "sources.json").write_text(
        json.dumps({"schema_version": 1, "sources": rows}), encoding="utf-8"
    )


DOWNLOADS: list[str] = []


def _run(root: Path, body: bytes, **kw: Any) -> list[fetch.FetchResult]:
    calls: list[str] = []

    def fake(url: str) -> tuple[bytes, str]:
        calls.append(url)
        return body, "application/pdf"

    results = fetch_all(
        root / "sources.json",
        root / "manifest.json",
        root / "data",
        delay_s=0,
        download=fake,
        now=lambda: datetime(2026, 11, 6, 10, 0, tzinfo=UTC),
        **kw,
    )
    DOWNLOADS[:] = calls
    return results


def _manifest(root: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    return data


def test_fetch_adds_archive_row_and_file(repo: Path) -> None:
    body = _text_pdf([LONG])
    results = _run(repo, body)
    assert [r.outcome for r in results] == ["added"]
    doc = _manifest(repo)["documents"][0]
    assert doc["mode"] == "archive"  # never index straight from the downloader
    assert "target_mode=index" in doc["notes"]
    assert doc["text_layer"] == "born_digital"
    assert doc["bytes"] == len(body)
    assert doc["fetched_at"] == "2026-11-06T10:00:00+00:00"
    assert doc["source_url"] == "https://example.gov.in/act.pdf"
    assert (repo / "data" / doc["local_path"]).read_bytes() == body
    assert not list((repo / "data").rglob("*.part"))


def test_second_run_is_idempotent(repo: Path) -> None:
    body = _text_pdf([LONG])
    _run(repo, body)
    results = _run(repo, body)
    assert [r.outcome for r in results] == ["skipped"]
    assert DOWNLOADS == []
    assert len(_manifest(repo)["documents"]) == 1


def test_changed_source_is_not_applied(repo: Path) -> None:
    _run(repo, _text_pdf([LONG]))
    before = _manifest(repo)["documents"][0]
    (repo / "data" / before["local_path"]).unlink()  # force a re-download
    results = _run(repo, _text_pdf([LONG + " amended"]))
    assert results[0].outcome == "changed"
    assert _manifest(repo)["documents"][0] == before
    assert (repo / "data" / (before["local_path"] + ".new")).exists()


def test_missing_local_file_with_same_bytes_is_restored(repo: Path) -> None:
    body = _text_pdf([LONG])
    _run(repo, body)
    path = repo / "data" / _manifest(repo)["documents"][0]["local_path"]
    path.unlink()
    results = _run(repo, body)
    assert results[0].detail == "restored local file"
    assert path.read_bytes() == body


def test_only_filter_and_errors(repo: Path) -> None:
    _write_sources(repo, [_source(), _source("IN.TESTACT2000@hi@1", language="hi")])
    results = _run(repo, b"%PDF-1.4 broken", only=["IN.TESTACT2000@hi@1"])
    assert [(r.doc_id, r.outcome) for r in results] == [("IN.TESTACT2000@hi@1", "error")]
    assert _manifest(repo)["documents"] == []


def test_invalid_manifest_is_never_written(repo: Path) -> None:
    _write_sources(repo, [_source(instrument_id="IN.UNKNOWN2000", doc_id="IN.UNKNOWN2000@en@1")])
    before = (repo / "manifest.json").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="not written"):
        _run(repo, _text_pdf([LONG]))
    assert (repo / "manifest.json").read_text(encoding="utf-8") == before


def test_validate_sources() -> None:
    assert validate_sources({"schema_version": 1, "sources": [_source()]}) == []
    bad = validate_sources(
        {"schema_version": 1, "sources": [_source(target_mode="live", extra=1), _source()]}
    )
    assert any("target_mode" in e for e in bad)
    assert any("unknown field 'extra'" in e for e in bad)
    assert any("duplicate" in e for e in bad)
    assert validate_sources([]) != []


# --------------------------------------------------------------- real HTTP (localhost only)


@pytest.fixture
def server() -> Iterator[tuple[str, list[str]]]:
    agents: list[str] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            agents.append(self.headers.get("User-Agent", ""))
            body = b"%PDF-fake"
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf; charset=binary")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}/x.pdf", agents
    httpd.shutdown()


def test_http_download_sends_project_user_agent(server: tuple[str, list[str]]) -> None:
    url, agents = server
    body, content_type = http_download(url)
    assert body == b"%PDF-fake"
    assert content_type == "application/pdf"
    assert agents == [USER_AGENT]
    assert "@" not in USER_AGENT  # never a personal email


def test_http_download_rejects_other_schemes() -> None:
    with pytest.raises(ValueError):
        http_download("file:///etc/passwd")


# --------------------------------------------------------------- MP Labour DMS two-hop (localhost)


@pytest.fixture
def dms_server() -> Iterator[str]:
    """Fake of the DMS viewer: page links to a token URL that only works with the session cookie."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.startswith("/portal/services/ImageShow.aspx"):
                page = b'<a href="ShowPDF.axd?Path=abc%2b&amp;recID=1" id="PDF">View</a>'
                self.send_response(200)
                self.send_header("Set-Cookie", "sess=ok; Path=/")
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(page)
            elif self.path == "/portal/services/ShowPDF.axd?Path=abc%2b&recID=1" and (
                "sess=ok" in self.headers.get("Cookie", "")
            ):
                body = _text_pdf([LONG])
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args: Any) -> None:
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}/portal/services/ImageShow.aspx?src=eA=="
    httpd.shutdown()


def test_mp_labour_dms_two_hop_download(dms_server: str) -> None:
    body, content_type = fetch.mp_labour_dms_download(dms_server)
    assert body.startswith(b"%PDF") and content_type == "application/pdf"


def test_mp_labour_dms_url_is_base64_of_path() -> None:
    url = fetch.mp_labour_dms_url("/QL_Shram/DMS/Document/x.pdf")
    assert url == fetch.MP_LABOUR_DMS_VIEWER + "L1FMX1NocmFtL0RNUy9Eb2N1bWVudC94LnBkZg=="


def test_unknown_resolver_rejected() -> None:
    errors = validate_sources({"schema_version": 1, "sources": [_source(resolver="magic")]})
    assert any("unknown resolver" in e for e in errors)


def test_incomplete_read_is_retried_then_reported(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import http.client

    monkeypatch.setattr(fetch.time, "sleep", lambda _s: None)
    calls: list[int] = []

    def flaky_once() -> tuple[bytes, str]:
        calls.append(1)
        raise http.client.IncompleteRead(b"partial")

    with pytest.raises(OSError, match="download failed after"):
        fetch._with_retries(flaky_once)
    assert len(calls) == fetch.RETRIES

    def broken(url: str) -> tuple[bytes, str]:
        raise http.client.IncompleteRead(b"partial")

    results = fetch_all(
        repo / "sources.json", repo / "manifest.json", repo / "data", delay_s=0, download=broken
    )
    assert [r.outcome for r in results] == ["error"]
