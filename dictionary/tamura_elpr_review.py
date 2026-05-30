"""Tiny local web UI to manually check Tamura ELPR extraction against the scans.

For each PDF page it shows, side by side:
  - the cropped page image (what the OCR saw)
  - the raw Gemini OCR text
  - the PARSED output produced by the real routing functions (corpus sentences
    with restored ain-kana, or dictionary rows) — so you verify what actually
    lands in the PRs.

Run:
  uv run --with pyyaml --with more-itertools \
      python -m dictionary.tamura_elpr_review        # then open http://localhost:8765

No build step, no JS framework — stdlib http.server only.
"""

from __future__ import annotations

import html
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dictionary import tamura_elpr_route as R
from dictionary.tamura_elpr_parse import parse_vocab_page

OCR_DIR = R.OCR_DIR
MODEL_FILE = R.MODEL_FILE
PORT = 8791

# Map each PDF page to (kind, label). kind drives which parser the viewer runs.
# Ranges mirror tamura_elpr_route.
def _build_page_map() -> dict[int, tuple[str, str]]:
    m: dict[int, tuple[str, str]] = {}

    def mark(rng, kind, label):
        for p in rng:
            m[p] = (kind, label)

    # Part I 藤山ハル — interlinear corpus
    mark(range(18, 27), "interlinear", "I 藤山ハル · UCASKUMA 1 → corpus")
    mark(range(37, 43), "interlinear", "I 藤山ハル · UCASKUMA 2 → corpus")
    mark(range(47, 55), "interlinear", "I 藤山ハル · UCASKUMA 3 → corpus")
    mark(range(63, 96), "interlinear", "I 藤山ハル · UCASKUMA 4 → corpus")
    mark(range(112, 146), "interlinear", "I 藤山ハル · TUYTAH (言い伝え5) → corpus")
    mark(range(157, 171), "interlinear", "I 藤山ハル · 歌 (IHUNKE/SINOHSA) → corpus")
    # Part II 山田ハヨ
    mark(range(183, 198), "vocab_bare", "II 山田ハヨ · 語彙 → dictionary")
    mark(range(198, 200), "yamada_oral", "II 山田ハヨ · 口頭文芸 → corpus")
    # Part III 北風磯吉
    mark(range(215, 217), "interlinear", "III 北風磯吉 · 001 散文説話 → corpus")
    mark(range(218, 242), "kitakaze", "III 北風磯吉 · 問答・例文 002–145 → corpus")
    # Part IV 徹辺重次郎
    mark(range(258, 314), "vocab", "IV 徹辺重次郎 · 語彙 → dictionary")
    mark(range(316, 322), "interlinear", "IV 徹辺重次郎 · ウチャシクマ → corpus")
    return m


PAGE_MAP = _build_page_map()
CONTENT_PAGES = sorted(PAGE_MAP)


def ocr_text(p: int) -> str:
    f = OCR_DIR / f"page-{p:03d}" / "ocr" / MODEL_FILE
    return f.read_text(encoding="utf-8") if f.exists() else "(no OCR)"


def image_path(p: int) -> Path:
    return OCR_DIR / f"page-{p:03d}" / "images" / "cropped_page.png"


def parsed_rows(p: int, kind: str) -> tuple[list[str], list[list[str]]]:
    """Return (header, rows) for the parsed view of one page."""
    if kind in ("interlinear",):
        doc = R.build_interlinear_doc(range(p, p + 1), "")
        return (["ain (Latin)", "ain-kana (fixed)", "jpn"],
                [[s.get("ain", ""), s.get("ain-kana", ""), s.get("jpn", "")] for s in doc["sentences"]])
    if kind == "kitakaze":
        doc = R.build_kitakaze_doc(range(p, p + 1), "")
        return (["ain (incl. code-switch)", "jpn (prompt)"],
                [[s.get("ain", ""), s.get("jpn", "")] for s in doc["sentences"]])
    if kind == "yamada_oral":
        doc = R.build_yamada_oral_doc(range(p, p + 1), "")
        return (["ain (Latin)", "jpn"], [[s.get("ain", ""), s.get("jpn", "")] for s in doc["sentences"]])
    if kind in ("vocab", "vocab_bare"):
        rows, _ = parse_vocab_page(ocr_text(p), bare_num=(kind == "vocab_bare"))
        return (["num", "cat", "gloss_ja", "lemma", "notes"],
                [[str(r.num), r.category, r.gloss_ja, r.lemma, r.notes] for r in rows])
    return ([], [])


PAGE_CSS = """
*{box-sizing:border-box} body{margin:0;font:14px/1.5 system-ui,sans-serif;color:#1a1a1a}
header{position:sticky;top:0;background:#111;color:#fff;padding:8px 14px;display:flex;gap:12px;align-items:center;z-index:5}
header a{color:#9cf;text-decoration:none} header .label{color:#ffd479;font-weight:600}
.wrap{display:grid;grid-template-columns:minmax(380px,46vw) 1fr;gap:0;height:calc(100vh - 41px)}
.imgcol{overflow:auto;background:#2b2b2b;padding:10px} .imgcol img{width:100%;border:1px solid #444}
.datacol{overflow:auto;padding:14px}
h3{margin:14px 0 6px;font-size:13px;color:#666;text-transform:uppercase;letter-spacing:.04em}
pre{white-space:pre-wrap;background:#f6f6f6;border:1px solid #e2e2e2;border-radius:6px;padding:10px;font:12px/1.55 ui-monospace,monospace}
table{border-collapse:collapse;width:100%;font-size:13px} td,th{border:1px solid #e2e2e2;padding:4px 7px;vertical-align:top;text-align:left}
th{background:#fafafa} .kana{font-size:15px} tr:nth-child(even) td{background:#fbfbfb}
nav a{display:inline-block;padding:3px 9px;background:#eee;border-radius:5px;color:#111;text-decoration:none}
.idx{padding:14px} .idx h2{font-size:15px;margin:18px 0 6px} .idx a{display:inline-block;width:46px;text-align:center;margin:2px;padding:4px;background:#eef;border-radius:5px;text-decoration:none;color:#114}
"""


def render_index() -> str:
    secs: list[tuple[str, list[int]]] = []
    for p in CONTENT_PAGES:
        label = PAGE_MAP[p][1]
        if not secs or secs[-1][0] != label:
            secs.append((label, []))
        secs[-1][1].append(p)
    body = ["<div class=idx><h1>Tamura ELPR — extraction review</h1>",
            f"<p>{len(CONTENT_PAGES)} content pages. Click a PDF page to compare the scan against the parsed data.</p>"]
    for label, pages in secs:
        body.append(f"<h2>{html.escape(label)}</h2>")
        body.append("".join(f'<a href="/page/{p}">{p}</a>' for p in pages))
    body.append("</div>")
    return f"<!doctype html><meta charset=utf-8><title>Tamura ELPR review</title><style>{PAGE_CSS}</style>" + "".join(body)


def render_page(p: int) -> str:
    kind, label = PAGE_MAP.get(p, ("other", "(front/index matter)"))
    idx = CONTENT_PAGES.index(p) if p in CONTENT_PAGES else -1
    prev_p = CONTENT_PAGES[idx - 1] if idx > 0 else p
    next_p = CONTENT_PAGES[idx + 1] if 0 <= idx < len(CONTENT_PAGES) - 1 else p
    header, rows = parsed_rows(p, kind)
    if header:
        thead = "".join(f"<th>{html.escape(h)}</th>" for h in header)
        trows = []
        for r in rows:
            tds = "".join(
                f'<td class="{"kana" if header[i] in ("ain-kana (fixed)","ain (Latin)","ain (incl. code-switch)","lemma") else ""}">{html.escape(c)}</td>'
                for i, c in enumerate(r))
            trows.append(f"<tr>{tds}</tr>")
        parsed_html = f"<table><tr>{thead}</tr>{''.join(trows)}</table>" if rows else "<p>(no rows parsed)</p>"
    else:
        parsed_html = "<p>Front-matter / index page — OCR only.</p>"
    return f"""<!doctype html><meta charset=utf-8><title>page {p}</title><style>{PAGE_CSS}</style>
<header>
  <a href="/">← index</a>
  <nav><a href="/page/{prev_p}">‹ prev</a> <a href="/page/{next_p}">next ›</a></nav>
  <span>PDF page <b>{p}</b> (printed {p-7})</span>
  <span class=label>{html.escape(label)}</span>
</header>
<div class=wrap>
  <div class=imgcol><img src="/img/{p}" alt="page {p}"></div>
  <div class=datacol>
    <h3>Parsed output (what lands in the data)</h3>
    {parsed_html}
    <h3>Raw Gemini OCR</h3>
    <pre>{html.escape(ocr_text(p))}</pre>
  </div>
</div>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, body: bytes, ctype: str):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/":
                self._send(render_index().encode(), "text/html; charset=utf-8")
            elif path.startswith("/page/"):
                self._send(render_page(int(path.split("/")[-1])).encode(), "text/html; charset=utf-8")
            elif path.startswith("/img/"):
                ip = image_path(int(path.split("/")[-1]))
                if ip.exists():
                    self._send(ip.read_bytes(), "image/png")
                else:
                    self._send(b"no image", "text/plain")
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as exc:  # show errors in the browser
            self._send(f"<pre>{html.escape(repr(exc))}</pre>".encode(), "text/html; charset=utf-8")


def main() -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Tamura ELPR review UI → http://localhost:{PORT}  ({len(CONTENT_PAGES)} content pages)")
    print("Ctrl-C to stop.")
    srv.serve_forever()


if __name__ == "__main__":
    main()
