"""図つき問題（雨温図・世界地図）の SVG を作る。

make_drill.py（PDF）と build_share.py（共有ページ）の両方から使う。
色は CSS のクラス（.fig-*）で付けるので、ページ側・PDF側でそれぞれ色を決める。

問題の形（drills の items に辞書で書く）:
    {"q": 問題文, "choices": [選択肢...], "a": 正解の選択肢, "note": 解説, "star": 1,
     "fig": {"climo": "東京"}}                          … 雨温図（data/climate_normals.json の都市）
     "fig": {"map": [["A", 経度, 緯度], ...], "view": [西経度, 東経度, 南緯度, 北緯度]}
                                                        … 世界地図に A〜D の地点（view で範囲を切り出す）
     "fig": {"climo": ..., "map": [...]}                 … 雨温図と地図を並べる
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLIMATE = json.loads((ROOT / "data/climate_normals.json").read_text(encoding="utf-8"))["cities"]
LAND = (ROOT / "data/world_land_110m.path").read_text().strip()

# 雨温図の軸（全問で共通にして見比べられるようにする）
T_MIN, T_MAX = -30, 35      # 気温（左軸・℃）
P_MAX = 500                 # 降水量（右軸・mm）


def defs():
    """地図の陸地データ（ページ・PDF に1回だけ置き、各地図から <use> で参照する）。"""
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
            f'<defs><path id="world-land" d="{LAND}"/></defs></svg>')


def climograph(city):
    c = CLIMATE[city]
    w, h = 340, 236
    x0, x1, y0, y1 = 46, 296, 22, 182
    bw = (x1 - x0) / 12
    ty = lambda t: y1 - (t - T_MIN) / (T_MAX - T_MIN) * (y1 - y0)
    py = lambda p: y1 - min(p, P_MAX) / P_MAX * (y1 - y0)
    out = [f'<svg class="fig-climo" viewBox="0 0 {w} {h}" role="img" aria-label="雨温図">']
    for t in range(T_MIN, T_MAX + 1, 10):
        y = ty(t)
        out.append(f'<line class="fig-grid{" fig-zero" if t == 0 else ""}" x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="fig-ax" x="{x0 - 5}" y="{y + 3.5:.1f}" text-anchor="end">{t}</text>')
    for p in range(0, P_MAX + 1, 100):
        out.append(f'<text class="fig-ax" x="{x1 + 5}" y="{py(p) + 3.5:.1f}">{p}</text>')
    for i, p in enumerate(c["prec"]):
        x = x0 + i * bw + bw * 0.18
        out.append(f'<rect class="fig-bar" x="{x:.1f}" y="{py(p):.1f}" width="{bw * 0.64:.1f}" height="{y1 - py(p):.1f}"/>')
        out.append(f'<text class="fig-ax" x="{x0 + (i + 0.5) * bw:.1f}" y="{y1 + 13}" text-anchor="middle">{i + 1}</text>')
    pts = " ".join(f"{x0 + (i + 0.5) * bw:.1f},{ty(t):.1f}" for i, t in enumerate(c["temp"]))
    out.append(f'<polyline class="fig-line" points="{pts}"/>')
    for i, t in enumerate(c["temp"]):
        out.append(f'<circle class="fig-dot" cx="{x0 + (i + 0.5) * bw:.1f}" cy="{ty(t):.1f}" r="2.6"/>')
    out.append(f'<text class="fig-ax" x="{x0 - 5}" y="12" text-anchor="end">℃</text>')
    out.append(f'<text class="fig-ax" x="{x1 + 5}" y="12">mm</text>')
    mean = sum(c["temp"]) / 12
    total = sum(c["prec"])
    out.append(f'<text class="fig-cap" x="{w / 2}" y="{h - 12}" text-anchor="middle">'
               f'年平均気温 {mean:.1f}℃　年降水量 {total:,}mm　（折れ線＝気温・棒＝降水量）</text>')
    out.append("</svg>")
    return "".join(out)


def worldmap(points, view=None):
    west, east, south, north = view or (-180, 180, -75, 85)
    X = lambda lon: (lon + 180) * 2
    Y = lambda lat: (90 - lat) * 2
    vx, vy, vw, vh = X(west), Y(north), (east - west) * 2, (north - south) * 2
    k = vw / 720                               # 拡大したときも印と文字の大きさをそろえる
    tall = " fig-tall" if vh / vw > 0.7 else ""     # 縦長の切り出し（南米など）は幅を控えめにする
    out = [f'<svg class="fig-map{tall}" viewBox="{vx:g} {vy:g} {vw:g} {vh:g}" role="img" aria-label="世界地図">',
           f'<rect class="fig-sea" x="{vx:g}" y="{vy:g}" width="{vw:g}" height="{vh:g}"/>',
           f'<use href="#world-land" class="fig-land" style="stroke-width:{0.5 * k:.2f}"/>',
           f'<line class="fig-eq" x1="{vx:g}" x2="{vx + vw:g}" y1="180" y2="180" style="stroke-width:{0.8 * k:.2f};stroke-dasharray:{4 * k:.1f} {3 * k:.1f}"/>']
    for label, lon, lat in points:
        x, y = X(lon), Y(lat)
        out.append(f'<circle class="fig-mk" cx="{x:.1f}" cy="{y:.1f}" r="{6.5 * k:.2f}" style="stroke-width:{1.8 * k:.2f}"/>')
        out.append(f'<text class="fig-mkl" x="{x + 8 * k:.1f}" y="{y - 6 * k:.1f}" '
                   f'style="font-size:{26 * k:.1f}px;stroke-width:{5 * k:.2f}">{label}</text>')
    out.append("</svg>")
    return "".join(out)


def render(item):
    """問題の辞書から SVG を作る（図がなければ空文字）。"""
    fig = item.get("fig") or {}
    parts = []
    if "climo" in fig:
        parts.append(climograph(fig["climo"]))
    if "map" in fig:
        parts.append(worldmap(fig["map"], fig.get("view")))
    if len(parts) == 2:                     # 雨温図と地図を並べる総合問題
        return f'<div class="figpair">{"".join(parts)}</div>'
    return "".join(parts)
