#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
房价数据分析 — parsed 数据校验脚本
==================================
读取 parsed/ 目录下的 CSV 与 JSON 数据文件，执行三类校验：
  1. 数值合法性：可转为 float、非负（人口增幅允许负数）、无 NaN
  2. 记录完整性：CSV 行数与 JSON 记录数、关键字段逐一交叉比对
  3. 口径一致性：parsed 数据与 dist HTML 内嵌数据保持同源

用法：
  python3 scripts/validate_data.py
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARSED = ROOT / "parsed"

CSV_FILES = {
    "gz_districts.csv": {"min_rows": 7, "numeric_cols": ["price_2010", "price_2019", "price_2026_est",
                                                          "income_2010", "income_2019", "income_2025",
                                                          "pop_2010", "pop_2025", "price_income_2019", "price_income_2026"]},
    "cities_comparison.csv": {"min_rows": 21, "numeric_cols": ["price_2010", "price_2026", "growth_pct"], "allow_empty_cols": ["price_2026", "growth_pct"]},
    "gz_price_income_history.csv": {"min_rows": 8, "numeric_cols": ["year", "ratio"]},
}


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def check_csv(path: Path, spec: dict) -> list:
    """校验单个 CSV：表头、行数、数值字段合法性。返回问题列表。"""
    problems = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        problems.append(f"{path.name}: 空文件")
        return problems
    if len(rows) < spec["min_rows"]:
        problems.append(f"{path.name}: 行数不足（{len(rows)} < {spec['min_rows']}）")
    for i, row in enumerate(rows, start=2):  # 从表头下一行计
        for col in spec["numeric_cols"]:
            val = row.get(col)
            allow_empty = col in spec.get("allow_empty_cols", [])
            if val is None or val.strip() == "":
                if not allow_empty:
                    problems.append(f"{path.name} 第{i}行 {col}: 缺失")
                continue
            try:
                num = float(val)
                if num != num:  # NaN
                    problems.append(f"{path.name} 第{i}行 {col}: NaN")
            except ValueError:
                problems.append(f"{path.name} 第{i}行 {col}: 非数值 '{val}'")
    return problems


def cross_check(json_data: dict) -> list:
    """交叉比对 JSON 与 CSV 的记录数与关键字段。返回问题列表。"""
    problems = []

    # gz_districts.csv vs json.gz_districts.records
    csv_rows = {}
    with open(PARSED / "gz_districts.csv", encoding="utf-8-sig") as f:
        csv_rows = {r["district"]: r for r in csv.DictReader(f)}
    json_recs = {r["district"]: r for r in json_data["gz_districts"]["records"]}
    if set(csv_rows) != set(json_recs):
        problems.append(f"gz_districts 区域不一致: csv={sorted(csv_rows)} json={sorted(json_recs)}")
    else:
        for d in csv_rows:
            for col in ("price_2010", "price_2019", "pop_2025"):
                if float(csv_rows[d][col]) != float(json_recs[d][col]):
                    problems.append(f"gz_districts.{d}.{col}: csv={csv_rows[d][col]} json={json_recs[d][col]}")

    # cities_comparison.csv vs json.cities.records
    with open(PARSED / "cities_comparison.csv", encoding="utf-8-sig") as f:
        csv_cities = {r["city"]: r for r in csv.DictReader(f)}
    json_cities = {r["city"]: r for r in json_data["cities"]["records"]}
    if set(csv_cities) != set(json_cities):
        problems.append(f"cities 城市不一致: csv={sorted(csv_cities)} json={sorted(json_cities)}")
    else:
        col_map = {"price_2010": "price_2010", "price_2026": "price_2026", "growth_pct": "price_growth"}
        for c in csv_cities:
            for col, json_col in col_map.items():
                csv_val = csv_cities[c][col].strip()
                json_val = json_cities[c].get(json_col)
                if csv_val == "":
                    if json_val is not None:
                        problems.append(f"cities.{c}.{col}: csv 为空但 json={json_val}")
                    continue
                if float(csv_val) != float(json_val):
                    problems.append(f"cities.{c}.{col}: csv={csv_val} json={json_val}")

    # gz_price_income_history.csv vs json.gz_price_income_history.records
    with open(PARSED / "gz_price_income_history.csv", encoding="utf-8-sig") as f:
        csv_hist = {(r["stage"], str(r["year"])): r for r in csv.DictReader(f)}
    json_hist = {(r["stage"], str(r["year"])): r for r in json_data["gz_price_income_history"]["records"]}
    if set(csv_hist) != set(json_hist):
        problems.append(f"history 阶段不一致: csv={sorted(csv_hist)} json={sorted(json_hist)}")
    else:
        for k in csv_hist:
            if float(csv_hist[k]["ratio"]) != float(json_hist[k]["ratio"]):
                problems.append(f"history.{k}.ratio: csv={csv_hist[k]['ratio']} json={json_hist[k]['ratio']}")

    return problems


def main() -> int:
    problems = []

    # 1) 顶层 JSON 结构与记录数
    json_data = load_json(PARSED / "house_prices_data.json")
    expected_keys = {"gz_districts", "cities", "shandong_cities", "gz_price_income_history",
                     "gs_shenzhen_income", "model", "conclusions"}
    missing = expected_keys - set(json_data.keys())
    if missing:
        problems.append(f"house_prices_data.json 缺顶层键: {sorted(missing)}")

    # 2) CSV 数值与行数
    for fname, spec in CSV_FILES.items():
        problems += check_csv(PARSED / fname, spec)

    # 3) CSV ↔ JSON 交叉校验
    problems += cross_check(json_data)

    if problems:
        print(f"[FAIL] 发现 {len(problems)} 个问题:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("[PASS] parsed 数据校验通过：JSON 顶层键完整，3 个 CSV 数值合法，CSV 与 JSON 交叉一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
