# -*- coding: utf-8 -*-
"""
广州各区人口变化分析 —— 数据集构建脚本 v3（可复现）
=====================================================
数据来源全部为广州市统计局官方资料（详见《数据来源与口径说明.md》）：
  1) 历年《广州统计年鉴》(1999-2025 版) 第二章人口篇 + 第一章区县主要指标 + 2002版第18章五普附录
  2) 广州市历年《人口规模及分布情况》公报 (2024/2025 年发布版)
  3) 六普公报、七普公报、《广州市区域人口分布和人口流动情况分析》(七普专项)
产出：raw/*.csv 长表
"""
import json, csv, re, os, glob

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, 'raw')
os.makedirs(RAW, exist_ok=True)

WAN = 10000.0

def to_float(s):
    if s is None: return None
    s = str(s).replace(',', '').replace('—', '-').replace('…', '').strip()
    if not s: return None
    try: return float(s)
    except Exception: return None

def read_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def parse_ole(path):
    import xlrd
    wb = xlrd.open_workbook(path, on_demand=True)
    sh = wb.sheet_by_index(0)
    return [[str(sh.cell_value(r, c)).replace('\n', ' ').strip() for c in range(sh.ncols)] for r in range(sh.nrows)]

def norm_district(nm):
    nm = re.sub(r'\s+', '', str(nm))
    return nm.replace('番禺市', '番禺区').replace('花都市', '花都区')

ALLD = {'东山区','越秀区','海珠区','荔湾区','天河区','白云区','黄埔区','芳村区',
        '番禺区','花都区','南沙区','萝岗区','增城市','增城区','从化市','从化区'}

def extract_district_rows(rows):
    start = None
    for i, r in enumerate(rows):
        joined = re.sub(r'\s+', '', ' '.join(r))
        if ('全市' in joined or 'Total' in joined) and any(to_float(c) is not None for c in r[1:]):
            start = i
            break
    if start is None:
        return []
    data = []
    for r in rows[start:]:
        if len(r) < 2:
            continue
        nm = re.sub(r'\s+', '', str(r[0]))
        if not nm:
            continue
        if any(k in nm for k in ['注', '单位', '人口', '面积', '合计', '年份', '地区', '项', '主要年份', '手册', '统计', '婴儿', '平均']):
            continue
        if nm in ('全市', '广州市', 'Total', '总计'):
            label = '全市'
        elif nm in ('市区', '市 区', '县级市'):
            label = nm
        elif nm in ALLD:
            label = norm_district(nm)
        else:
            if re.search(r'[\u4e00-\u9fff]', nm) and len(nm) <= 6:
                label = norm_district(nm)
            else:
                continue
        vals = [to_float(c) for c in r[1:]]
        if vals and all(v is None for v in vals):
            continue
        data.append((label, vals))
    return data

def district_dict(data):
    return {label: vals for label, vals in data if label not in ('全市', '市区', '县级市')}

# ---------------- 表号与列映射（按年鉴版） ----------------
TABLES = {
    'nj1999': {'pop': '02-05', 'natural': '02-08', 'migration': '02-07'},
    'nj2000': {'pop': '02-05', 'natural': '02-08', 'migration': '02-07'},
    'nj2001': {'pop': '02-06', 'natural': '02-09', 'migration': '02-08'},
    'nj2002': {'pop': '02-05', 'natural': '02-08', 'migration': '02-07'},
    'nj2003': {'pop': '02-05', 'natural': '02-08', 'migration': '02-07'},
    'nj2004': {'pop': '2-5',   'natural': '2-6',   'migration': '2-7'},
    'nj2008': {'pop': '2-8',   'natural': '2-9_2-10', 'migration': '2-9_2-10'},
    'nj2009': {'pop': '2-8',   'natural': '2-9',   'migration': '2-10'},
    'nj2010': {'pop': '2-8',   'natural': '2-9',   'migration': '2-10'},
    'nj2011': {'pop': '2-8',   'natural': '2-9',   'migration': '2-10'},
    'nj2012': {'pop': '2-8',   'natural': '2-9',   'migration': '2-10'},
    'nj2013': {'pop': '2-8',   'natural': '2-9',   'migration': '2-10'},
}
# 列映射 (avg, births, br, deaths, dr, infant) / (in, in_rate, out, out_rate, net, net_rate) / pop 列
NAT_COL = {'nj1999': (0,1,2,3,5,6), 'nj2000': (0,1,2,3,5,6), 'nj2001': (0,1,2,3,5,6), 'nj2002': (0,1,2,3,5,6),
           'nj2003': (0,1,2,3,4,5), 'nj2004': (1,2,3,4,5,6), 'nj2008': (1,2,3,4,5,6), 'nj2009': (1,2,3,4,5,6),
           'nj2010': (1,2,3,4,5,6), 'nj2011': (1,2,3,4,5,6), 'nj2012': (1,2,3,4,5,6), 'nj2013': (1,2,3,4,5,6)}
MIG_COL = {'nj1999': (0,1,2,3,4,5), 'nj2000': (0,1,2,3,4,5), 'nj2001': (0,1,2,3,4,5), 'nj2002': (0,1,2,3,4,5),
           'nj2003': (0,1,2,3,4,5), 'nj2004': (1,2,3,4,5,6), 'nj2008': (1,2,3,4,5,6), 'nj2009': (1,2,3,4,5,6),
           'nj2010': (1,2,3,4,5,6), 'nj2011': (1,2,3,4,5,6), 'nj2012': (1,2,3,4,5,6), 'nj2013': (1,2,3,4,5,6)}
POP_IDX = {'nj1999': 0, 'nj2000': 0, 'nj2001': 0, 'nj2002': 0, 'nj2003': 0,
           'nj2004': 2, 'nj2008': 2, 'nj2009': 2, 'nj2010': 2, 'nj2011': 2, 'nj2012': 2, 'nj2013': 2}
DATA_YEAR = {'nj1999': 1998, 'nj2000': 1999, 'nj2001': 2000, 'nj2002': 2001, 'nj2003': 2002,
             'nj2004': 2003, 'nj2008': 2007, 'nj2009': 2008, 'nj2010': 2009, 'nj2011': 2010,
             'nj2012': 2011, 'nj2013': 2012}

# ---------------- 载入旧表 ----------------
old_html = read_json('/tmp/old_html_tables.json')
old_ole = read_json('/tmp/old_ole_tables.json')

def get_store_data(store, edition, tno):
    """按精确表号前缀取 (label, vals) 列表。"""
    for k, v in store.items():
        if v.get('edition') == edition and k.split(':', 1)[-1].startswith(tno):
            return v['data']
    return None

# 1998 / 2007 特殊表
old1998 = {k: extract_district_rows(parse_ole(f'/tmp/old_nj/nj1999y/{tno}.xls'))
           for tno, k in [('02-05', 'pop'), ('02-08', 'natural'), ('02-07', 'migration')]}
nj2008_comb = parse_ole('/tmp/old_nj/nj2008y/2-9_2-10.xls')
split_idx = next(i for i, r in enumerate(nj2008_comb) if '2-10' in ' '.join(r))
old2007 = {'natural': extract_district_rows(nj2008_comb[:split_idx]),
           'migration': extract_district_rows(nj2008_comb[split_idx:])}

def load_old(year, kind):
    ed = next(e for e, y in DATA_YEAR.items() if y == year)
    if year == 1998:
        return district_dict(old1998[kind]), dict(old1998[kind]).get('全市')
    if year == 2007:
        if kind == 'pop':
            data = get_store_data(old_ole, ed, TABLES[ed]['pop'])
        else:
            data = old2007[kind]
    else:
        store = old_html if year <= 2002 else old_ole
        if ed == 'nj2013':
            f = glob.glob(f'/tmp/old_nj/nj2013y/{TABLES[ed][kind]}*.xls')[0]
            data = extract_district_rows(parse_ole(f))
        else:
            data = get_store_data(store, ed, TABLES[ed][kind])
    d = district_dict(data or [])
    city = None
    for label, vals in (data or []):
        if label == '全市':
            city = vals
            break
    return d, city

def col(vals, idx):
    return vals[idx] if idx is not None and idx < len(vals) else None

# =========================================================
# 3) 分区户籍人口 1998-2025（万人）
# =========================================================
hukou_rows = []
VALID = {}
for year in [1998, 1999, 2000, 2001, 2002, 2003, 2007, 2008, 2009, 2010, 2011, 2012]:
    ed = next(e for e, y in DATA_YEAR.items() if y == year)
    d, city = load_old(year, 'pop')
    if not d:
        continue
    if year == 1999:
        # nj2000 pop 表县级市段行标签错位：番禺区(标)=县级市合计, 花都区(标)=番禺市, 县级市(标)=花都市
        # district_dict 已剔除“县级市”行，此处基于原始表重建县级市段并合并
        raw = get_store_data(old_html, ed, TABLES[ed]['pop'])
        raw_map = {}
        for label, vals in raw or []:
            raw_map[norm_district(label)] = vals
        d = {k: v for k, v in d.items() if k not in ('番禺区', '花都区')}  # 保留 8 市区行
        if '花都区' in raw_map:
            d['番禺区'] = raw_map['花都区']   # 实为番禺市
        if '县级市' in raw_map:
            d['花都区'] = raw_map['县级市']   # 实为花都市
        if '增城市' in raw_map:
            d['增城市'] = raw_map['增城市']
        if '从化市' in raw_map:
            d['从化市'] = raw_map['从化市']
    for dist, vals in d.items():
        v = col(vals, POP_IDX[ed])
        if v is not None:
            hukou_rows.append([year, dist, round(v / WAN, 2), f'统计年鉴{year}年'])
    if city and len(city) > POP_IDX[ed]:
        VALID[year] = (round(sum(col(v, POP_IDX[ed]) or 0 for v in d.values()) / WAN, 2),
                       round(col(city, POP_IDX[ed]) / WAN, 2))

# 2004: nj2005 1-28 各区主要指标（转置表：区县在列、指标在行，年末总人口(人)）
def parse_2004_pop(path):
    import xlrd
    wb = xlrd.open_workbook(path, on_demand=True)
    sh = wb.sheet_by_index(0)
    rows = [[str(sh.cell_value(r, c)).replace('\n', ' ').strip() for c in range(sh.ncols)] for r in range(sh.nrows)]
    hdr = rows[2]
    out = {}
    pop_row = None
    for r in rows:
        if '年末总人口' in r[0]:
            pop_row = r
            break
    if pop_row is None:
        return out
    for c in range(2, sh.ncols):
        nm = re.sub(r'\s+', '', hdr[c])
        nm = re.sub(r'[A-Za-z]+.*$', '', nm)
        if not nm or len(nm) > 6 or not re.search(r'[\u4e00-\u9fff]', nm):
            continue
        v = to_float(pop_row[c])
        if v:
            out[norm_district(nm)] = v
    return out

d128 = parse_2004_pop('/tmp/old_nj/nj2005x/1-28.xls')
for dist, v in d128.items():
    hukou_rows.append([2004, dist, round(v / WAN, 2), '统计年鉴2004年'])
VALID[2004] = (round(sum(d128.values()) / WAN, 2), None)  # 该表无独立全市行，锚点取分区合计

# 2005-2014: 2023 年鉴 2-4（万人，户籍块+常住块）
t24 = read_json('/tmp/nj_tables_parsed.json')['2023_02-04']['data']
years_24 = list(range(2005, 2015))
hukou_0504, cz_0504 = {}, {}
for i, r in enumerate(t24):
    if i < 13:
        hukou_0504[r[0]] = r[1]
    elif i < 26:
        cz_0504[r[0]] = r[1]
for dist, vals in hukou_0504.items():
    if dist in ('全市', '市区', '县级市'):
        continue
    for j, y in enumerate(years_24):
        v = to_float(vals[j + 1]) if j + 1 < len(vals) else None
        if v is not None:
            hukou_rows.append([y, dist, round(v, 2), '统计年鉴2-4(2005-2014)'])
for y in years_24:
    j = y - 2005
    city_v = to_float(hukou_0504.get('全市', [])[j + 1]) if j + 1 < len(hukou_0504.get('全市', [])) else None
    dsum = round(sum(to_float(v[j + 1]) for d_, v in hukou_0504.items() if d_ not in ('全市', '市区', '县级市') and j + 1 < len(v) and to_float(v[j + 1])) or 0, 2)
    if city_v is not None:
        VALID[y] = (dsum, round(city_v, 2))

# 2015-2023: 2024 年鉴 2-2（万人）
t22 = read_json('/tmp/nj_probe/2024_02-02.json')['data']
years_22 = list(range(2015, 2024))
hukou_1523, cz_1523 = {}, {}
hk_city_22, cz_city_22 = None, None
block = 0
for r in t22:
    nm = re.sub(r'\s+', '', str(r[0]))
    if nm in ('户籍人口', '常住人口'):
        block = 0 if '户籍' in nm else 1
        continue
    if nm in ('全市', 'Total'):
        vals = r[1:]
        if block == 0:
            hk_city_22 = vals[:10]
        else:
            cz_city_22 = vals[:10]
        continue
    if nm in ALLD or '注' in nm:
        vals = r[1:]
        if block == 0 and len(vals) >= 10:
            hukou_1523[nm] = vals[:10]
        elif block == 1 and len(vals) >= 10:
            cz_1523[nm] = vals[:10]
for dist, vals in hukou_1523.items():
    if dist in ('全市', '市区'):
        continue
    for j, y in enumerate(years_22):
        v = to_float(vals[j + 1]) if j + 1 < len(vals) else None
        if v is not None:
            hukou_rows.append([y, dist, round(v, 2), '统计年鉴2-2(2015-2023)'])
for y in years_22:
    j = y - 2015
    city_v = to_float(hk_city_22[j + 1]) if hk_city_22 and j + 1 < len(hk_city_22) else None
    dsum = round(sum(to_float(v[j + 1]) for d_, v in hukou_1523.items() if d_ not in ('全市', '市区') and j + 1 < len(v) and to_float(v[j + 1])) or 0, 2)
    if city_v is not None:
        VALID[y] = (dsum, round(city_v, 2))

gb2024_hukou = {'荔湾区': 81.39, '越秀区': 116.51, '海珠区': 111.58, '天河区': 110.57, '白云区': 126.02,
                '黄埔区': 73.63, '番禺区': 123.71, '花都区': 92.36, '南沙区': 58.11, '从化区': 66.68, '增城区': 114.46}
gb2024_cz = {'荔湾区': 113.50, '越秀区': 98.00, '海珠区': 176.99, '天河区': 224.31, '白云区': 369.56,
             '黄埔区': 123.52, '番禺区': 284.53, '花都区': 175.06, '南沙区': 98.39, '从化区': 73.97, '增城区': 159.97}
gb2025_hukou = {'荔湾区': 82.21, '越秀区': 115.77, '海珠区': 112.01, '天河区': 111.45, '白云区': 129.04,
                '黄埔区': 76.59, '番禺区': 126.66, '花都区': 93.94, '南沙区': 59.64, '从化区': 67.01, '增城区': 116.82}
gb2025_cz = {'荔湾区': 112.90, '越秀区': 97.16, '海珠区': 177.07, '天河区': 225.60, '白云区': 373.19,
             '黄埔区': 125.08, '番禺区': 287.23, '花都区': 176.67, '南沙区': 99.32, '从化区': 73.75, '增城区': 162.13}
for dist, v in gb2024_hukou.items():
    hukou_rows.append([2024, dist, v, '2024公报表2'])
for dist, v in gb2025_hukou.items():
    hukou_rows.append([2025, dist, v, '2025公报表2'])
VALID[2024] = (round(sum(gb2024_hukou.values()), 2), 1075.02)
VALID[2025] = (round(sum(gb2025_hukou.values()), 2), 1091.14)
hukou_rows.sort(key=lambda r: (r[0], r[1]))
with open(os.path.join(RAW, '分区户籍人口_1998_2025.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['年份', '地区', '户籍人口(万人)', '数据来源'])
    w.writerows(hukou_rows)

# =========================================================
# 4) 分区常住人口 2000-2025（万人）
# =========================================================
cz_rows = []
wp2000 = read_json('/tmp/nj_probe/wp2000_district.json')['data']
for r in wp2000:
    nm = norm_district(re.sub(r'\s+', '', str(r[0])))
    if nm in ALLD:
        v = to_float(r[4])
        if v:
            cz_rows.append([2000, nm, round(v / WAN, 2), '五普2000(普查时点)'])
for dist, vals in cz_0504.items():
    if dist in ('全市', '市区', '县级市'):
        continue
    for j, y in enumerate(years_24):
        v = to_float(vals[j + 1]) if j + 1 < len(vals) else None
        if v is not None:
            cz_rows.append([y, dist, round(v, 2), '统计年鉴2-4(2005-2014)'])
for dist, vals in cz_1523.items():
    if dist in ('全市', '市区'):
        continue
    for j, y in enumerate(years_22):
        v = to_float(vals[j + 1]) if j + 1 < len(vals) else None
        if v is not None:
            cz_rows.append([y, dist, round(v, 2), '统计年鉴2-2(七普修订)'])
liupu = {'荔湾区': 898204, '越秀区': 1157277, '海珠区': 1558663, '天河区': 1432431, '白云区': 2222658,
         '黄埔区': 457930, '番禺区': 1764869, '花都区': 945053, '南沙区': 259899, '萝岗区': 373670,
         '增城市': 1036731, '从化市': 593415}
for dist, v in liupu.items():
    cz_rows.append([2010, dist, round(v / WAN, 2), '六普公报2010(普查时点)'])
qipu = {'荔湾区': 124.16, '越秀区': 103.66, '海珠区': 181.98, '天河区': 225.10, '白云区': 375.91,
        '黄埔区': 126.92, '番禺区': 267.26, '花都区': 165.09, '南沙区': 84.90, '从化区': 71.98, '增城区': 147.07}
for dist, v in qipu.items():
    cz_rows.append([2020, dist, v, '七普公报2020(普查时点)'])
for dist, v in gb2024_cz.items():
    cz_rows.append([2024, dist, v, '2024公报表1'])
for dist, v in gb2025_cz.items():
    cz_rows.append([2025, dist, v, '2025公报表1'])
cz_rows.sort(key=lambda r: (r[0], r[1]))
with open(os.path.join(RAW, '分区常住人口_2000_2025.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['年份', '地区', '常住人口(万人)', '数据来源'])
    w.writerows(cz_rows)

# =========================================================
# 5) 分区自然变动 1998-2025
# =========================================================
nat_rows = []
for year in [1998, 1999, 2000, 2001, 2002, 2003, 2007, 2008, 2009, 2010, 2011, 2012]:
    ed = next(e for e, y in DATA_YEAR.items() if y == year)
    am, bm, brm, dm, drm, irm = NAT_COL[ed]
    d, _ = load_old(year, 'natural')
    for dist, vals in d.items():
        nat_rows.append([year, dist, col(vals, am), col(vals, bm), col(vals, brm),
                         col(vals, dm), col(vals, drm), col(vals, irm)])
with open(os.path.join(RAW, 'natural_raw_2013_2023.csv'), encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        dist = row['地区']
        if dist in ('全市', '市区'):
            continue
        nat_rows.append([int(row['数据年']), dist,
                         to_float(row['年平均人数']), to_float(row['出生人数']), to_float(row['出生率千分']),
                         to_float(row['死亡人数']), to_float(row['死亡率千分']), to_float(row['婴儿死亡率千分'])])
nat2024 = {'荔湾区': [809309, 6224, 7.69, 6445, 7.96, 2.44], '越秀区': [1167606, 7359, 6.30, 8361, 7.16, 1.20],
           '海珠区': [1112806, 8221, 7.39, 7628, 6.85, 1.39], '天河区': [1099664, 11426, 10.39, 3742, 3.40, 1.85],
           '白云区': [1244544, 14464, 11.62, 5882, 4.73, 1.59], '黄埔区': [720305, 11413, 15.84, 2468, 3.43, 1.10],
           '番禺区': [1221167, 14937, 12.23, 4442, 3.64, 0.97], '花都区': [914547, 10374, 11.34, 4432, 4.85, 1.87],
           '南沙区': [572132, 7797, 13.63, 2772, 4.85, 1.60], '从化区': [665066, 7148, 10.75, 3605, 5.42, 2.19],
           '增城区': [1131009, 14971, 13.24, 5004, 4.42, 1.29]}
for dist, v in nat2024.items():
    nat_rows.append([2024, dist, v[0], v[1], v[2], v[3], v[4], v[5]])
nat_rows.sort(key=lambda r: (r[0], r[1]))
with open(os.path.join(RAW, '分区自然变动_1998_2025.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['年份', '地区', '年平均人数(人)', '出生(人)', '出生率(‰)', '死亡(人)', '死亡率(‰)', '婴儿死亡率(‰)'])
    w.writerows(nat_rows)

# =========================================================
# 6) 分区户籍迁移 1998-2025
# =========================================================
mig_rows = []
for year in [1998, 1999, 2000, 2001, 2002, 2003, 2007, 2008, 2009, 2010, 2011, 2012]:
    ed = next(e for e, y in DATA_YEAR.items() if y == year)
    im, imr, om, omr, nm_, nmr = MIG_COL[ed]
    d, _ = load_old(year, 'migration')
    for dist, vals in d.items():
        mig_rows.append([year, dist, col(vals, im), col(vals, imr), col(vals, om), col(vals, omr),
                         col(vals, nm_), col(vals, nmr)])
with open(os.path.join(RAW, 'migration_raw_2013_2023.csv'), encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        dist = row['地区']
        if dist in ('全市', '市区'):
            continue
        mig_rows.append([int(row['数据年']), dist,
                         to_float(row['迁入人数']), to_float(row['迁入率千分']), to_float(row['迁出人数']),
                         to_float(row['迁出率千分']), to_float(row['净增人数']), to_float(row['净增率千分'])])
mig2024 = {'荔湾区': [8506, 10.51, 1975, 2.44, 6531, 8.07], '越秀区': [11788, 10.10, 4620, 3.96, 7168, 6.14],
           '海珠区': [12216, 10.98, 4771, 4.29, 7445, 6.69], '天河区': [25877, 23.53, 9657, 8.78, 16220, 14.75],
           '白云区': [22231, 17.86, 3478, 2.79, 18753, 15.07], '黄埔区': [15943, 22.13, 2345, 3.26, 13598, 18.87],
           '番禺区': [23826, 19.51, 6723, 5.51, 17103, 14.00], '花都区': [13255, 14.49, 2023, 2.21, 11232, 12.28],
           '南沙区': [10669, 18.65, 1281, 2.24, 9388, 16.41], '从化区': [3016, 4.53, 1352, 2.03, 1664, 2.50],
           '增城区': [17907, 15.83, 2309, 2.04, 15598, 13.65]}
for dist, v in mig2024.items():
    mig_rows.append([2024, dist, v[0], v[1], v[2], v[3], v[4], v[5]])
mig_rows.sort(key=lambda r: (r[0], r[1]))
with open(os.path.join(RAW, '分区户籍迁移_1998_2025.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['年份', '地区', '迁入(人)', '迁入率(‰)', '迁出(人)', '迁出率(‰)', '净增(人)', '净增率(‰)'])
    w.writerows(mig_rows)

# =========================================================
# 7) 普查跨市流入 / 净流入（万人）
# =========================================================
flow2020 = {'荔湾区': 55.59, '越秀区': 29.06, '海珠区': 79.36, '天河区': 131.80, '白云区': 237.56,
            '黄埔区': 69.46, '番禺区': 150.56, '花都区': 79.92, '南沙区': 39.19, '从化区': 14.75, '增城区': 50.63}
flow2010 = {'荔湾区': 25.29, '越秀区': 24.15, '海珠区': 50.66, '天河区': 64.73, '白云区': 121.93,
            '黄埔区': 44.59, '番禺区': 72.22, '花都区': 29.20, '南沙区': 11.12, '从化区': 6.96, '增城区': 25.13}
net2020 = {'荔湾区': 46.93, '越秀区': -13.47, '海珠区': 73.56, '天河区': 123.13, '白云区': 261.58,
           '黄埔区': 66.41, '番禺区': 157.15, '花都区': 80.30, '南沙区': 35.48, '从化区': 6.79, '增城区': 44.68}
net2010 = {'荔湾区': 18.89, '越秀区': -1.20, '海珠区': 60.59, '天河区': 66.18, '白云区': 139.13,
           '黄埔区': 44.29, '番禺区': 76.09, '花都区': 28.31, '南沙区': 10.58, '从化区': 1.47, '增城区': 19.73}
liudong_rows = []
for dist in ['荔湾区', '越秀区', '海珠区', '天河区', '白云区', '黄埔区', '番禺区', '花都区', '南沙区', '从化区', '增城区']:
    liudong_rows.append([dist, flow2020[dist], flow2010[dist], net2020[dist], net2010[dist]])
with open(os.path.join(RAW, '普查跨市流入与净流入_2010_2020.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['地区', '跨市流入2020(万人)', '跨市流入2010(万人)', '净流入2020(万人)', '净流入2010(万人)'])
    w.writerows(liudong_rows)

# =========================================================
# 8) 全市长序列
# =========================================================
city_rows = []
t25 = read_json('/tmp/nj_tables_parsed.json')['2024_02-05']['data']
for r in t25:
    y = str(r[0]); vals = r[1]
    if re.fullmatch(r'\d{4}', y) and len(vals) >= 2 and to_float(vals[1]):
        city_rows.append([int(y), '户籍总人口(万人)', round(to_float(vals[1]) / WAN, 2), '2024年鉴2-5'])
city_rows.append([2024, '户籍总人口(万人)', 1075.02, '2024公报'])
city_rows.append([2025, '户籍总人口(万人)', 1091.14, '2025公报'])
cz_city = {}
for r in wp2000:
    if re.sub(r'\s+', '', str(r[0])) == '全市':
        v = to_float(r[4])
        if v:
            cz_city[2000] = v / WAN
for dist, vals in cz_0504.items():
    if dist == '全市':
        for j, y in enumerate(years_24):
            v = to_float(vals[j + 1]) if j + 1 < len(vals) else None
            if v is not None:
                cz_city[y] = v
if cz_city_22:
    for j, y in enumerate(years_22):
        v = to_float(cz_city_22[j + 1]) if j + 1 < len(cz_city_22) else None
        if v is not None:
            cz_city[y] = v
cz_city[2024] = 1897.80
cz_city[2025] = 1910.10
for y in sorted(cz_city):
    city_rows.append([y, '常住人口(万人)', round(cz_city[y], 2), '年鉴/公报/普查(口径见说明)'])
nat_city = {}
for r in nat_rows:
    y, dist, avg, b, br, dd, dr, ir = r
    if y not in nat_city:
        nat_city[y] = [0, 0]
    nat_city[y][0] += b or 0
    nat_city[y][1] += dd or 0
for y in sorted(nat_city):
    city_rows.append([y, '全市户籍出生(人)', nat_city[y][0], '分区表合计'])
    city_rows.append([y, '全市户籍死亡(人)', nat_city[y][1], '分区表合计'])
city_rows.append([2025, '全市户籍出生(人)', 108000, '2025公报'])
city_rows.append([2025, '全市户籍死亡(人)', 55600, '2025公报'])
mig_city = {}
for r in mig_rows:
    y, dist, im, imr, om, omr, net, netr = r
    if y not in mig_city:
        mig_city[y] = [0, 0, 0]
    mig_city[y][0] += im or 0
    mig_city[y][1] += om or 0
    mig_city[y][2] += net or 0
for y in sorted(mig_city):
    city_rows.append([y, '全市户籍迁入(人)', mig_city[y][0], '分区表合计'])
    city_rows.append([y, '全市户籍迁出(人)', mig_city[y][1], '分区表合计'])
    city_rows.append([y, '全市户籍迁移净增(人)', mig_city[y][2], '分区表合计'])
city_rows.append([2025, '全市户籍迁入(人)', 150600, '2025公报'])
city_rows.append([2025, '全市户籍迁出(人)', 40800, '2025公报'])
city_rows.append([2025, '全市户籍迁移净增(人)', 109800, '2025公报'])
city_rows.sort(key=lambda r: (r[0], r[1]))
with open(os.path.join(RAW, '全市长序列_1978_2025.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['年份', '指标', '数值', '数据来源'])
    w.writerows(city_rows)

# =========================================================
# 校验输出
# =========================================================
print("BUILD OK")
print("--- 户籍人口 分区合计 vs 全市（表内） ---")
for y, (dsum, city) in sorted(VALID.items()):
    if city is None:
        print(f"  {y}: 分区 {dsum}（无表内全市行，取分区合计）")
        continue
    flag = 'OK' if abs(dsum - city) < 0.06 else '** MISMATCH **'
    print(f"  {y}: 分区 {dsum} vs 全市 {city}  {flag}")
print("--- 常住合计（年度口径 vs 普查时点口径分开校验） ---")
for y, target in [(2000, 994.20), (2024, 1897.80), (2025, 1910.10)]:
    s = round(sum(r[2] for r in cz_rows if r[0] == y), 2)
    print(f"  {y}: 分区合计 {s} vs 锚点 {target}  {'OK' if abs(s-target) < 0.5 else '** 注意(口径) **'}")
s10 = round(sum(r[2] for r in cz_rows if r[0] == 2010 and r[3].startswith('统计年鉴')), 2)
s10c = round(sum(r[2] for r in cz_rows if r[0] == 2010 and r[3].startswith('六普')), 2)
print(f"  2010: 年度口径合计 {s10} (锚点 1270.96) | 六普时点合计 {s10c} (锚点 1270.08)")
s20 = round(sum(r[2] for r in cz_rows if r[0] == 2020 and r[3].startswith('统计年鉴')), 2)
s20c = round(sum(r[2] for r in cz_rows if r[0] == 2020 and r[3].startswith('七普')), 2)
print(f"  2020: 年度口径合计 {s20} (锚点 1874.03) | 七普时点合计 {s20c} (锚点 1874.03)")
print("--- 自然/迁移 全市合计（公报/年鉴锚点） ---")
anchors = [(1998, 67695, 40981, 140570, 94128), (1999, 81485, 39176, 155276, 96936),
           (2000, 71248, 39987, 177480, 107175), (2003, 57277, 41082, 130222, 93663),
           (2007, 71332, 42548, 159696, 55417), (2012, 101782, 50538, 131458, 103973),
           (2024, 114334, 54781, 165234, 40534)]
for y, ab, ad, aim, aom in anchors:
    b = sum(r[3] for r in nat_rows if r[0] == y and r[3])
    dd = sum(r[5] for r in nat_rows if r[0] == y and r[5])
    im = sum(r[2] for r in mig_rows if r[0] == y and r[2])
    om = sum(r[4] for r in mig_rows if r[0] == y and r[4])
    ok = abs(b-ab) < 1 and abs(dd-ad) < 1 and abs(im-aim) < 1 and abs(om-aom) < 1
    print(f"  {y}: 出生 {b:,}/{ab:,} 死亡 {dd:,}/{ad:,} 迁入 {im:,}/{aim:,} 迁出 {om:,}/{aom:,}  {'OK' if ok else '** MISMATCH **'}")
