#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
房价数据分析 — raw 数据源转录脚本
==================================
读取 raw/ 目录下带 YAML front-matter 的数据源记录（.md），
解析其中的数据点元数据（city/year/metric/value/unit/note），
生成/更新 parsed/ 下的结构化数据文件：
  1. parsed/cities_comparison.csv  —— 9 城 2010/2026 成交均价与涨幅（本脚本主产物）
  2. 校验数据点完整性，输出转录报告

用法：
  python3 scripts/transcribe_raw.py
"""
import re
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
PARSED = ROOT / "parsed"

OUT_CSV = PARSED / "cities_comparison.csv"

# 城市归一化（raw 文件里的 city 键 → 输出城市名）
CITY_ALIAS = {
    "北京": "北京", "深圳": "深圳", "广州": "广州", "杭州": "杭州",
    "厦门": "厦门", "成都": "成都", "青岛": "青岛", "沈阳": "沈阳", "哈尔滨": "哈尔滨",
    "上海": "上海", "重庆": "重庆", "武汉": "武汉", "南京": "南京",
    "天津": "天津", "长沙": "长沙",
    "洛阳": "洛阳", "汕头": "汕头", "湛江": "湛江", "徐州": "徐州",
    "九江": "九江", "济宁": "济宁",
}

# 城市梯队（用于 CSV tier 列）
CITY_TIER = {
    "北京": "一线核心", "深圳": "一线核心", "广州": "一线核心", "上海": "一线核心",
    "杭州": "新一线", "厦门": "强二线", "成都": "新一线", "青岛": "北方二线", "沈阳": "东北二线",
    "哈尔滨": "东北二线", "重庆": "新一线", "武汉": "新一线", "南京": "新一线",
    "天津": "北方二线", "长沙": "新一线",
    "洛阳": "三线", "汕头": "三线", "湛江": "三线",
    "徐州": "三线", "九江": "四线", "济宁": "四线",
}

# 需要转录的 21 城（一二线 15 城 + 三四线 6 城，各含 2010 与 2026 两个数据点）
TARGET_CITIES = ["北京", "深圳", "广州", "杭州", "厦门", "成都", "青岛", "沈阳", "哈尔滨",
                 "上海", "重庆", "武汉", "南京", "天津", "长沙",
                 "洛阳", "汕头", "湛江", "徐州", "九江", "济宁"]


def parse_front_matters(text: str) -> list:
    """解析 YAML front-matter 块，支持一个文件内多个数据点（--- 包裹的键值块）。"""
    blocks = re.findall(r"^---\n(.*?)\n---\n", text, re.S | re.M)
    metas = []
    for block in blocks:
        meta = {}
        for line in block.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        if meta:
            metas.append(meta)
    return metas


def scan_raw() -> dict:
    """扫描 raw/*.md，返回 {(city, year): {metric, value, source, url, note}}。"""
    points = {}
    for f in sorted(RAW.glob("*.md")):
        for meta in parse_front_matters(f.read_text(encoding="utf-8")):
            if "city" not in meta or "year" not in meta:
                continue
            city = CITY_ALIAS.get(meta["city"], meta["city"])
            if city in ("三四线2010新房均价", "三四线2026二手房均价"):
                continue  # 总表文件仅作溯源记录，不直接转录
            key = (city, meta["year"])
            points[key] = {
                "metric": meta.get("metric", ""),
                "value": meta.get("value", ""),
                "source": meta.get("source", f.name),
                "url": meta.get("url", ""),
                "note": meta.get("note", ""),
            }
    return points


def main() -> int:
    points = scan_raw()
    problems = []
    rows = []

    for city in TARGET_CITIES:
        p10 = points.get((city, "2010"))
        p26 = points.get((city, "2026"))
        if not p10:
            problems.append(f"{city}: 缺 2010 数据点")
            continue
        if not p26:
            problems.append(f"{city}: 缺 2026 数据点")

        def num(p):
            try:
                return float(p["value"]) if p and p["value"] not in ("", "null") else None
            except ValueError:
                return None

        v10, v26 = num(p10), num(p26)
        growth = None
        if v10 and v26:
            growth = round((v26 / v10 - 1) * 100, 1)

        rows.append({
            "city": city,
            "tier": CITY_TIER.get(city, ""),
            "price_2010": v10 if v10 is not None else "",
            "price_2026": v26 if v26 is not None else "",
            "growth_pct": growth if growth is not None else "",
            "note_2010": p10["note"] if p10 else "",
            "note_2026": p26["note"] if p26 else "",
            "source_2010": p10["source"] if p10 else "",
            "source_2026": p26["source"] if p26 else "",
        })

    # 写 CSV（覆盖式更新）
    fieldnames = ["city", "tier", "price_2010", "price_2026", "growth_pct", "note_2010", "note_2026", "source_2010", "source_2026"]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # 输出转录报告
    print(f"[transcribe] 已扫描 {len(points)} 个数据点，转录 {len(rows)} 个城市至 {OUT_CSV.name}")
    for r in rows:
        g = r["growth_pct"] if r["growth_pct"] != "" else "（缺）"
        print(f"  {r['city']}: 2010={r['price_2010'] or '缺'} → 2026={r['price_2026'] or '缺'}  涨幅={g}%")
    if problems:
        print(f"[WARN] {len(problems)} 个问题:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("[PASS] 21 城数据点完整。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
