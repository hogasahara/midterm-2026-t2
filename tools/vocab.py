"""単語集 JSON（"kind": "vocab"）を一問一答ドリルの形に展開する。

make_drill.py（PDF）と build_share.py（共有ページ）の両方から使う。

単語集の形:
    {"kind": "vocab", "title": ..., "units": [{"unit": "① Singapore",
      "words": [[英語, 品詞, 意味, メモ, 重要(1/0), 例文({}が空欄), 例文の訳, 空欄に入る形], ...]}]}

展開後は「英日」「日英」「空欄補充」の3グループ × 単元のセクションになる。
各問題は [問題, 答え, 重要, 単語番号, ヒント, (日英だけ)タイピングの正解]。単語番号で「間違えた単語集」をまとめる。
日英はページでタイピングして答え、variants() の言い方のどれかに合えば ○（ページの JS で採点）。
日英・空欄補充の頭文字はヒントとして別に持ち、ページでは「ヒントを表示」で出す（PDFには載せない）。

単語を別の単語に統合して消したときは "merged" に記録する（{"unit", "index": 統合前の単元内の位置, "into": 統合先の英語, "row": 消した行}）。
共有ページの○×は問題の通し番号で保存されているので、versions() と wid_map() で古い番号を新しい番号に付け替える。

一部の単語だけを抜き出した単語集は {"kind": "vocab", "from": 元の単語集のパス, "pick": [英語, ...]} と書く（units の代わり）。
単語の中身は元の単語集から取るので、元を直せば抜き出し側にも反映される。
"""

import itertools
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

MODES = ("英日", "日英", "空欄補充")
GROUP_NOTES = {
    "英日": "英語 → 日本語",
    "日英": "日本語を見て英語をタイピング（自動で○×）",
    "空欄補充": "例文の（ ）に入る語",
}

PLACEHOLDERS = {"~", "A", "J", "N", "...", "…"}
# 文の形を覚える項目はタイピングで答えない（日英でも自己採点のまま）
TYPING_SKIP = {"The main question raised", "portrayal of J as a ...", "There is N -ing/-en",
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


def resolve(data):
    """pick の単語集は、元の単語集から選んだ単語を単元ごとに集めて units を作る（元の並び順のまま）。"""
    if "pick" not in data:
        return data
    src = json.loads((ROOT / data["from"]).read_text(encoding="utf-8"))
    pick = set(data["pick"])
    units = [{**u, "words": [w for w in u["words"] if w[0] in pick]} for u in src["units"]]
    found = {w[0] for u in units for w in u["words"]}
    if pick - found:
        raise SystemExit(f"元の単語集にない単語: {sorted(pick - found)}")
    return {**{k: v for k, v in data.items() if k not in ("from", "pick")}, "units": [u for u in units if u["words"]]}


def words(data):
    """単語の通し番号つき一覧 [(番号, 単元, 単語の行), ...]。"""
    out = []
    for u in data["units"]:
        for w in u["words"]:
            out.append((len(out), u["unit"], w))
    return out


BLANK = "( ＿＿＿＿ )"


def initial(text):
    """頭文字のヒント。"""
    return "頭文字：" + next((c for c in text if c.isalpha()), "")


def expand(data):
    """単語集を、sections を持つ一問一答ドリルに変換する。"""
    data = resolve(data)
    ws = words(data)
    sections = []
    for mode in MODES:
        for u in data["units"]:
            items = []
            for wid, unit, (en, pos, ja, note, star, sent, sent_ja, ans) in ws:
                if unit != u["unit"]:
                    continue
                memo = f"　［{note}］" if note else ""
                if mode == "英日":
                    items.append([f"{en}（{pos}）", ja + memo, star, wid])
                elif mode == "日英":
                    # 6番目はタイピングで正解とする言い方（タイピングしない項目は None）
                    accept = None if en in TYPING_SKIP else variants(en)
                    items.append([f"{ja}（{pos}）", en + memo, star, wid, initial(en), accept])
                elif sent:
                    q = sent.replace("{}", BLANK) + "\n" + sent_ja
                    a = ans if ans.lower() == en.lower() else f"{ans}（{en}）"
                    items.append([q, a, star, wid, initial(ans)])
            if items:
                sections.append({"title": f"{mode}｜{u['unit']}", "group": mode, "items": items})
    out = {k: v for k, v in data.items() if k not in ("units", "kind")}
    out["sections"] = sections
    out["group_notes"] = {**GROUP_NOTES, **data.get("group_notes", {})}
    out["vocab"] = [{"en": en, "pos": pos, "ja": ja} for _, _, (en, pos, ja, *_) in ws]
    return out


def versions(data):
    """統合の前後の単語集を古い順に返す。最後が今の単語集（merged が n 件なら n+1 個）。"""
    out = [data]
    cur = data
    for m in reversed(data.get("merged", [])):
        units = [{**u, "words": list(u["words"])} for u in cur["units"]]
        next(u for u in units if u["unit"] == m["unit"])["words"].insert(m["index"], m["row"])
        cur = {**cur, "units": units}
        out.insert(0, cur)
    return out


def wid_map(before, after, m):
    """統合 m の前の単語番号 → 後の単語番号。"""
    old = words(before)
    gone = next(w for w, unit, row in old if unit == m["unit"] and row is m["row"])
    into = next(w for w, _, row in words(after) if row[0] == m["into"])
    return {w: (into if w == gone else w - (w > gone)) for w, _, _ in old}
