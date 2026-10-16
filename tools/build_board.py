"""data/plan.json を埋め込んで対策ボードを生成する。

出力:
  board/index.html     … ブラウザで直接開く／GitHub Pages 用（完全なHTML文書）
  board/artifact.html  … claude.ai アーティファクト再公開用（doctype等なし）

使い方:  python tools/build_board.py
"""
import json, pathlib

root = pathlib.Path(__file__).resolve().parent.parent
plan = json.loads((root / "data/plan.json").read_text(encoding="utf-8"))
tpl = (root / "board/template.html").read_text(encoding="utf-8")
body = tpl.replace("/*__PLAN__*/null", json.dumps(plan, ensure_ascii=False))
(root / "board/artifact.html").write_text(body, encoding="utf-8")
full = ('<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>\n'
        + body + '</body></html>\n')
(root / "board/index.html").write_text(full, encoding="utf-8")
total = sum(t["hours"] for d in plan["days"] for t in d["tasks"])
print(f"built board/index.html, board/artifact.html  (計画 {total}h)")
