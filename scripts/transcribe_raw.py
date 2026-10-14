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
}

# 需要转录的 9 城（含 2010 与 2026 两个数据点）
TARGET_CITIES = ["北京", "深圳", "广州", "杭州", "厦门", "成都", "青岛", "沈阳", "哈尔滨"]


def parse_front_matter(text: str) -> dict:
    """解析 YAML front-matter（--- 包裹的键值块）。"""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def scan_raw() -> dict:
    """扫描 raw/*.md，返回 {(city, year): {metric, value, source, url, note}}。"""
    points = {}
    for f in sorted(RAW.glob("*.md")):
        meta = parse_front_matter(f.read_text(encoding="utf-8"))
        if not meta or "city" not in meta or "year" not in meta:
            continue
        key = (meta["city"], meta["year"])
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
            "price_2010": v10 if v10 is not None else "",
            "price_2026": v26 if v26 is not None else "",
            "growth_pct": growth if growth is not None else "",
            "note_2010": p10["note"] if p10 else "",
            "note_2026": p26["note"] if p26 else "",
            "source_2010": p10["source"] if p10 else "",
            "source_2026": p26["source"] if p26 else "",
        })

    # 写 CSV（覆盖式更新）
    fieldnames = ["city", "price_2010", "price_2026", "growth_pct", "note_2010", "note_2026", "source_2010", "source_2026"]
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
    print("[PASS] 9 城数据点完整。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
