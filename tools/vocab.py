"""単語集 JSON（"kind": "vocab"）を一問一答ドリルの形に展開する。

make_drill.py（PDF）と build_share.py（共有ページ）の両方から使う。

単語集の形:
    {"kind": "vocab", "title": ..., "units": [{"unit": "① Singapore",
      "words": [[英語, 品詞, 意味, メモ, 重要(1/0), 例文({}が空欄), 例文の訳, 空欄に入る形], ...]}]}

展開後は「英日」「日英」「空欄補充」の3グループ × 単元のセクションになる。
各問題は [問題, 答え, 重要, 単語番号, ヒント]。単語番号で「間違えた単語集」をまとめる。
日英・空欄補充の頭文字はヒントとして別に持ち、ページでは「ヒントを表示」で出す（PDFには載せない）。
"""

MODES = ("英日", "日英", "空欄補充")
GROUP_NOTES = {
    "英日": "英語 → 日本語",
    "日英": "日本語 → 英語（頭文字ヒントあり）",
    "空欄補充": "例文の（ ）に入る語",
}


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
                    items.append([f"{ja}（{pos}）", en + memo, star, wid, initial(en)])
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
