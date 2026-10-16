#!/usr/bin/env python3
"""クラス共有用の教科別ページ（claude.ai アーティファクト）を生成する。

drills/<教科>/*.json（一問一答ドリル）を share/template.html に埋め込み、
share/<教科フォルダ名>.html を出力する。複数の JSON がある教科は1ページにまとめる。

使い方:  python3 tools/build_share.py

共有ページには個人名や家庭の学習計画を入れない（ドリルの問題と試験日程だけ）。
公開先 URL は CLAUDE.md の「クラス共有ページ」に記録する。
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
YEAR = 2026

# 教科ごとのアクセント色（ライト／ダーク）。淡い面の色は背景と混ぜて作る
ACCENTS = {
    "ea": ("#2d5aa8", "#8fb3f0"),
    "kobun": ("#8a3b5c", "#e3a0bd"),
    "chiri": ("#2f6f5e", "#6cc2a6"),
    "math-beta": ("#5a4aa0", "#b3a6f0"),
    "chem": ("#a0522d", "#f0a77a"),
    "gendaibun": ("#7a5c1e", "#e0c27a"),
    "eb": ("#1f6f8b", "#7cc7e0"),
    "rekishi": ("#7d3c2a", "#e3a590"),
    "math-alpha": ("#4a5aa0", "#a6b3f0"),
    "kanbun": ("#5c6b2a", "#c2d17a"),
}


def mix(color, base, t):
    """color を割合 t で base に混ぜた色（#rrggbb）。"""
    c = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(base[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(b[k] + (c[k] - b[k]) * t):02x}" for k in range(3))


def exam_info(plan, subject):
    for day in plan["exams"]:
        for p in day["periods"]:
            if p["subject"] == subject:
                m, d = (int(x) for x in day["date"].split("/"))
                label = f"{day['date']}（{day['weekday']}）{p['period']}"
                return label, f"{YEAR}-{m:02d}-{d:02d}", p["label"]
    raise KeyError(subject)


def main():
    plan = json.loads((ROOT / "data/plan.json").read_text(encoding="utf-8"))
    tpl = (ROOT / "share/template.html").read_text(encoding="utf-8")
    by_folder = {v["folder"]: k for k, v in plan["subjects"].items()}

    for folder, subject in by_folder.items():
        files = sorted((ROOT / "drills" / folder).glob("*.json"))
        if not files:
            continue
        drills = [json.loads(f.read_text(encoding="utf-8")) for f in files]
        exam, exam_date, course = exam_info(plan, subject)
        sections = [s for d in drills for s in d["sections"]]
        data = {
            "id": folder,
            "course": f"二学期中間テスト（高1）・{course}",
            "title": " ／ ".join(d["title"] for d in drills),
            "exam": exam,
            "exam_date": exam_date,
            "source": "、".join(d.get("share_source", "授業ノート") for d in drills),
            "updated": max(d["date"] for d in drills),
            "sections": sections,
        }
        light, dark = ACCENTS[folder]
        page = (tpl.replace("__TITLE__", f"{course} 中間ドリル")
                   .replace("__ACCENT_SOFT_LIGHT__", mix(light, "#ffffff", 0.12))
                   .replace("__ACCENT_SOFT_DARK__", mix(dark, "#1a201d", 0.16))
                   .replace("__ACCENT_LIGHT__", light)
                   .replace("__ACCENT_DARK__", dark)
                   .replace("/*__DRILL__*/null", json.dumps(data, ensure_ascii=False)))
        out = ROOT / "share" / f"{folder}.html"
        out.write_text(page, encoding="utf-8")
        n = sum(len(s["items"]) for s in sections)
        print(f"{out.relative_to(ROOT)}  ({course}・{n}問)")


if __name__ == "__main__":
    main()
