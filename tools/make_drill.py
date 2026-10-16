#!/usr/bin/env python3
"""一問一答ドリルの JSON から、印刷用 PDF（A4・問題編／解答編）を作る。

使い方:
    python3 tools/make_drill.py drills/chiri/20261016-chiri-drill.json

同じフォルダに <名前>-mondai.pdf と <名前>-kaitou.pdf を出力する。
PDF 化は Chromium（Node の playwright）で行う。日本語フォントは Noto Sans CJK JP。

JSON の形:
    {"title": ..., "subject": ..., "exam": ..., "source": ..., "date": ...,
     "sections": [{"title": ..., "items": [["問題", "解答"], ["問題", "解答", 1], ...]}, ...]}
    3番目の要素が 1 の問題は重要問題（★）
"""
import html
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

CSS = """
@page { size: A4; margin: 12mm 12mm 14mm 12mm; }
* { box-sizing: border-box; }
body { font-family: "Noto Sans CJK JP", sans-serif; font-size: 10pt; color: #111; margin: 0; }
header { display: flex; justify-content: space-between; align-items: flex-end;
         border-bottom: 2px solid #111; padding-bottom: 4px; margin-bottom: 6px; }
h1 { font-size: 14pt; margin: 0; white-space: nowrap; }
.meta { font-size: 8.5pt; color: #333; text-align: right; line-height: 1.6; white-space: nowrap; }
.howto { font-size: 8.5pt; color: #333; margin: 0 0 6px; }
.fill { display: inline-block; border-bottom: 1px solid #111; width: 16mm; }
.group { font-size: 12.5pt; font-weight: bold; margin: 14px 0 2px; padding-bottom: 2px; border-bottom: 1.5px solid #111; break-after: avoid; }
h2 { font-size: 11pt; margin: 10px 0 3px; padding: 2px 6px; background: #e8e8e8;
     break-after: avoid; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; }
td { border-bottom: 0.6px solid #999; padding: 4px 4px; vertical-align: top; line-height: 1.45; }
tr { break-inside: avoid; }
td.no { width: 12mm; text-align: right; font-weight: bold; white-space: nowrap; }
.star { font-size: 8pt; margin-right: 1px; }
td.chk { width: 11mm; text-align: center; color: #666; letter-spacing: 1px; }
td.q { width: 52%; }
td.a { border-left: 0.6px dotted #999; }
.kaitou td.a { font-weight: bold; }
.kaitou td.q { color: #444; }
"""


def render(data, answers):
    edition = "解答編" if answers else "問題編"
    out = [f"<!doctype html><html lang='ja'><head><meta charset='utf-8'><style>{CSS}</style></head>"]
    out.append(f"<body class='{'kaitou' if answers else 'mondai'}'>")
    out.append("<header><div>")
    out.append(f"<h1>{html.escape(data['title'])}【{edition}】</h1></div>")
    out.append("<div class='meta'>")
    out.append(f"{html.escape(data['subject'])}　試験 {html.escape(data['exam'])}<br>")
    if answers:
        out.append(f"出典: {html.escape(data['source'])}")
    else:
        out.append("1周目 <span class='fill'></span>点　2周目 <span class='fill'></span>点")
    out.append("</div></header>")
    if not answers:
        out.append("<p class='howto'>□□ は 1周目／2周目 のチェック欄。間違えた問題に印をつけ、"
                   "2周目は印のある問題だけ解く。★は重要問題。</p>")
    n = 0
    group = None
    for sec in data["sections"]:
        if sec.get("group") and sec["group"] != group:
            group = sec["group"]
            out.append(f"<div class='group'>{html.escape(group)}</div>")
        out.append(f"<h2>{html.escape(sec['title'])}</h2><table>")
        for q, a, *flag in sec["items"]:
            n += 1
            ans = html.escape(a) if answers else ""
            star = "<span class='star'>★</span>" if flag and flag[0] else ""
            out.append(
                f"<tr><td class='no'>{star}{n}</td><td class='chk'>□□</td>"
                f"<td class='q'>{html.escape(q)}</td><td class='a'>{ans}</td></tr>"
            )
        out.append("</table>")
    out.append("</body></html>")
    return "".join(out), n


NODE_PDF = r"""
const { chromium } = require('playwright');
(async () => {
  const [src, dst] = process.argv.slice(1);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + src);
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: dst, format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#666">' +
      '<span class="pageNumber"></span> / <span class="totalPages"></span></div>' });
  await browser.close();
})();
"""


def to_pdf(html_path, pdf_path):
    node_path = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    subprocess.run(
        ["node", "-e", NODE_PDF, str(html_path), str(pdf_path)],
        check=True, env={**__import__("os").environ, "NODE_PATH": node_path},
    )


def main():
    src = pathlib.Path(sys.argv[1]).resolve()
    data = json.loads(src.read_text(encoding="utf-8"))
    stem = src.with_suffix("")
    for answers, suffix in ((False, "mondai"), (True, "kaitou")):
        doc, n = render(data, answers)
        html_path = stem.parent / f".{stem.name}-{suffix}.html"
        html_path.write_text(doc, encoding="utf-8")
        pdf_path = stem.parent / f"{stem.name}-{suffix}.pdf"
        to_pdf(html_path, pdf_path)
        html_path.unlink()
        print(f"{pdf_path.relative_to(ROOT)}  ({n}問)")


if __name__ == "__main__":
    main()
