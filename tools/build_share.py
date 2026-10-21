#!/usr/bin/env python3
"""クラス共有用の教科別ページ（claude.ai アーティファクト）を生成する。

drills/<教科>/*.json（一問一答ドリル）を share/template.html に埋め込み、
share/<教科フォルダ名>.html を出力する。複数の JSON がある教科は1ページにまとめる。

使い方:  python3 tools/build_share.py

JSON に "kind": "jiji" があるものは時事問題として扱い、教科ドリルの後ろに単元として足す。
section に "group" があると、ページのメニューにグループごとのボタンが出る（時事は「時事問題」グループ）。
共有ページには個人名や家庭の学習計画を入れない（ドリルの問題と試験日程だけ）。
公開先 URL は CLAUDE.md の「クラス共有ページ」に記録する。
"""
import json
import pathlib

import figures
import vocab

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


def arrange(raw, wmaps=None):
    """ページに並べる順のセクションを作る。各問題には、版をまたいで同じ問題を指すキーも付ける。

    単語集（kind: "vocab"）は英日・日英・空欄補充の問題に展開する。
    時事（kind: "jiji"）は教科のドリルのあとに「時事問題」グループとして並べる。
    wmaps は {ドリルの番号: 単語番号の付け替え}（古い版のキーを今の版にそろえるときに使う）。
    """
    drills = [vocab.expand(d) if d.get("kind") == "vocab" else d for d in raw]
    main = [i for i, d in enumerate(drills) if d.get("kind") != "jiji"] or list(range(len(drills)))
    jiji = [i for i, d in enumerate(drills) if d.get("kind") == "jiji"]
    sections, keys = [], []
    for di, group in [(i, None) for i in main] + [(i, "時事問題") for i in jiji]:
        wmap = (wmaps or {}).get(di, {})
        for si, s in enumerate(drills[di]["sections"]):
            s = {**s, "group": group} if group else s
            sections.append(s)
            for ii, it in enumerate(s["items"]):
                if raw[di].get("kind") == "vocab":
                    keys.append((di, s["group"], wmap.get(it[3], it[3])))
                else:
                    keys.append((di, group, si, ii))
    return drills, sections, keys


def migrations(raw):
    """単語を統合したときの、問題の通し番号の付け替え表（版 i → i+1 の {古い番号: 新しい番号}、消えたら null）。"""
    out = []
    for di, d in enumerate(raw):
        if d.get("kind") != "vocab":
            continue
        vs = vocab.versions(d)
        for i, m in enumerate(d.get("merged", [])):
            _, _, old = arrange(raw[:di] + [vs[i]] + raw[di + 1:], {di: vocab.wid_map(vs[i], vs[i + 1], m)})
            _, _, new = arrange(raw[:di] + [vs[i + 1]] + raw[di + 1:])
            pos = {k: n for n, k in enumerate(new, 1)}
            out.append({str(n): pos.get(k) for n, k in enumerate(old, 1) if pos.get(k) != n})
    return out


def main():
    plan = json.loads((ROOT / "data/plan.json").read_text(encoding="utf-8"))
    tpl = (ROOT / "share/template.html").read_text(encoding="utf-8")
    by_folder = {v["folder"]: k for k, v in plan["subjects"].items()}

    for folder, subject in by_folder.items():
        files = sorted((ROOT / "drills" / folder).glob("*.json"))
        if not files:
            continue
        raw = [json.loads(f.read_text(encoding="utf-8")) for f in files]
        drills, sections, _ = arrange(raw)
        main = [d for d in drills if d.get("kind") != "jiji"] or drills
        jiji = [d for d in drills if d.get("kind") == "jiji"]
        exam, exam_date, course = exam_info(plan, subject)
        # 図つきの選択問題（辞書の問題）は SVG を作って持たせる
        sections = [{**s, "items": [{**it, "svg": figures.render(it)} if isinstance(it, dict) else it
                                    for it in s["items"]]} for s in sections]
        has_map = any(isinstance(it, dict) and "map" in it.get("fig", {}) for s in sections for it in s["items"])
        group_notes = {k: v for d in main for k, v in d.get("group_notes", {}).items()}
        if jiji:
            group_notes["時事問題"] = jiji[0].get("range", "")
        data = {
            "id": folder,
            "course": f"二学期中間テスト（高1）・{course}",
            "title": " ／ ".join(d["title"] for d in main),
            "exam": exam,
            "exam_date": exam_date,
            "source": "、".join(d.get("share_source", "授業ノート") for d in drills),
            "updated": max(d["date"] for d in drills),
            "group_notes": group_notes,
            "vocab": [w for d in main for w in d.get("vocab", [])],
            "sections": sections,
            "migrations": migrations(raw),
        }
        light, dark = ACCENTS[folder]
        page = (tpl.replace("__TITLE__", f"{course} 中間ドリル")
                   .replace("__ACCENT_SOFT_LIGHT__", mix(light, "#ffffff", 0.12))
                   .replace("__ACCENT_SOFT_DARK__", mix(dark, "#1a201d", 0.16))
                   .replace("__ACCENT_LIGHT__", light)
                   .replace("__ACCENT_DARK__", dark)
                   .replace("<!--__FIG_DEFS__-->", figures.defs() if has_map else "")
                   .replace("/*__DRILL__*/null", json.dumps(data, ensure_ascii=False)))
        out = ROOT / "share" / f"{folder}.html"
        out.write_text(page, encoding="utf-8")
        n = sum(len(s["items"]) for s in sections)
        print(f"{out.relative_to(ROOT)}  ({course}・{n}問)")


if __name__ == "__main__":
    main()
