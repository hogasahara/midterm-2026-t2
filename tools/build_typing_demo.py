#!/usr/bin/env python3
"""EA 日英タイピング（デモ）のページを作る。

drills/ea/*-vocab.json の単語から、日本語を見て英語をタイピングする練習ページ
share/ea-typing-demo.html を出力する。本番の EA 共有ページ（share/ea.html）とは別ページ。

使い方:  python3 tools/build_typing_demo.py

採点の考え方（ページの JS と合わせる）:
  - 大文字小文字・前後の空白・句読点は無視。ハイフンとスラッシュは空白と同じ扱い
  - 「~」「A」「J」「...」などの置き場所の記号は、書いても書かなくてもよい
  - 「/」で区切られた別の言い方は、どれでも正解（this/that のような語の中の / も同じ）
  - ( ) の中は書いても書かなくてもよい
  - 文の形を覚える文法項目（例: There is N -ing/-en）はタイピング向きでないので外す
"""
import itertools
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLACEHOLDERS = {"~", "A", "J", "N", "...", "…"}
SKIP = {"The main question raised", "portrayal of J as a ...", "There is N -ing/-en",
        "Kyoto be erased from ~", "~, for there were ...", "A after A"}
# 機械的に分けると不自然になるものは手で正解を決める
OVERRIDES = {
    "shed a tear / tears": ["shed a tear", "shed tears"],
    "either-or / either/or": ["either-or", "either/or"],
    "post-": ["post-", "post"],
    "GI": ["GI", "G.I."],
}


def variants(en):
    if en in OVERRIDES:
        return OVERRIDES[en]
    out = []
    for alt in [a.strip() for a in en.split(" / ")]:
        alt = re.sub(r",\s*~$", "", alt)                          # Long story short, ~
        opts = {alt}
        if "(" in alt:                                            # consistent (with ~)
            opts = {re.sub(r"\s*\(([^)]*)\)", r" \1", alt), re.sub(r"\s*\([^)]*\)", "", alt)}
        for o in opts:
            toks = [t for t in o.split() if t not in PLACEHOLDERS]
            # this/that のような語の中の / を展開する
            choices = [t.split("/") if "/" in t and len(t) > 1 else [t] for t in toks]
            for combo in itertools.product(*choices):
                out.append(" ".join(combo))
    return list(dict.fromkeys(v for v in out if v))


def main():
    src = sorted((ROOT / "drills/ea").glob("*-vocab.json"))[-1]
    data = json.loads(src.read_text(encoding="utf-8"))
    words = []
    for u in data["units"]:
        for en, pos, ja, note, star, *_ in u["words"]:
            if en in SKIP:
                continue
            words.append({"en": en, "pos": pos, "ja": ja, "note": note, "star": star,
                          "unit": u["unit"], "accept": variants(en)})
    units = list(dict.fromkeys(w["unit"] for w in words))
    tpl = (ROOT / "share/typing_demo_template.html").read_text(encoding="utf-8")
    page = tpl.replace("/*__WORDS__*/null", json.dumps({"words": words, "units": units}, ensure_ascii=False))
    out = ROOT / "share/ea-typing-demo.html"
    out.write_text(page, encoding="utf-8")
    print(f"{out.relative_to(ROOT)}  ({len(words)}語)")


if __name__ == "__main__":
    main()
