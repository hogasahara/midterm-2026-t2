"""用語カード JSON（"kind": "cards"）を4択の選択問題に展開する。

make_drill.py（PDF）と build_share.py（共有ページ）の両方から使う。

用語カードの形:
    {"kind": "cards", "title": ..., "units": [{"unit": "カタカナ語①社会（359〜366）",
      "cards": [[語, 意味, メモ, 重要(1/0)], ...]}],
     "confusable": [[まぎらわしい語, ...], ...]}

展開後は「意味→語」「語→意味」の2グループ × 単元のセクションになる。
誤りの選択肢は confusable で同じ組の語を優先し、残りは同じ種類の語（外来語どうし・それ以外どうし）から選ぶ。
選び方は語ごとに決まった乱数なので、何度作り直しても同じ問題になる。
"""

import random
import re

MODES = ("意味→語", "語→意味")
GROUP_NOTES = {
    "意味→語": "意味を読んで、あてはまる語を4つから選ぶ",
    "語→意味": "語を見て、正しい意味を4つから選ぶ",
}

# 外来語＝3文字以上のカタカナ語（ハレ・ケのようなカタカナ書きの和語は外来語に入れない）
katakana = re.compile(r"^[ァ-ヶー・]{3,}$")


def expand(data):
    cards = [(u["unit"], *c) for u in data["units"] for c in u["cards"]]
    words = [c[1] for c in cards]
    meaning = {c[1]: c[2] for c in cards}
    groups = data.get("confusable", [])
    sections = []
    for mode in MODES:
        for u in data["units"]:
            items = []
            for word, mean, memo, star in u["cards"]:
                rng = random.Random(f"{data['title']}|{mode}|{word}")
                near = [w for g in groups if word in g for w in g if w != word and w in meaning]
                rng.shuffle(near)
                same = [w for w in words if w != word and w not in near
                        and bool(katakana.match(w)) == bool(katakana.match(word))]
                rng.shuffle(same)
                wrong = list(dict.fromkeys(near + same))[:3]
                if mode == "意味→語":
                    q, a, choices = f"「{mean}」を表す語は。", word, [word] + wrong
                else:
                    q, a, choices = f"「{word}」の意味は。", mean, [mean] + [meaning[w] for w in wrong]
                rng.shuffle(choices)
                note = f"{word}＝{mean}" + (f"　［{memo}］" if memo else "")
                items.append({"q": q, "choices": choices, "a": a, "note": note, "star": star})
            sections.append({"title": f"{mode}｜{u['unit']}", "group": mode, "items": items})
    out = {k: v for k, v in data.items() if k not in ("units", "kind", "confusable")}
    out["sections"] = sections
    out["group_notes"] = {**GROUP_NOTES, **data.get("group_notes", {})}
    return out
