# -*- coding: utf-8 -*-
"""
广州各区人口变化分析 —— HTML 可视化报告生成器
读取 raw/*.csv 生成自包含 HTML（内联 ECharts via CDN）。
"""
import csv, json, os, math

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, 'raw')
OUT = os.path.join(BASE, '广州各区人口变化分析.html')

def load(fn):
    with open(os.path.join(RAW, fn), encoding='utf-8-sig') as f:
        return list(csv.reader(f))

def num(s):
    if s is None or s == '':
        return None
    try:
        return float(s)
    except Exception:
        return None

# ---------- 数据 ----------
hk = load('分区户籍人口_1998_2025.csv')
cz = load('分区常住人口_2000_2025.csv')
nat = load('分区自然变动_1998_2025.csv')
mig = load('分区户籍迁移_1998_2025.csv')
ld = load('普查跨市流入与净流入_2010_2020.csv')
city = load('全市长序列_1978_2025.csv')

D11 = ['荔湾区', '越秀区', '海珠区', '天河区', '白云区', '黄埔区', '番禺区', '花都区', '南沙区', '从化区', '增城区']

def series_by(rows, dist_filter=None, val_idx=2, year_idx=0, dist_idx=1):
    """{year: {dist: val}}；区名归一：增城市→增城区、从化市→从化区"""
    out = {}
    for r in rows[1:]:
        y = int(r[year_idx]); d = r[dist_idx]
        d = d.replace('增城市', '增城区').replace('从化市', '从化区')
        if dist_filter and d not in dist_filter:
            continue
        v = num(r[val_idx])
        if v is None:
            continue
        out.setdefault(y, {})[d] = v
    return out

hkS = series_by(hk)
czS = series_by(cz)
natS = series_by(nat, val_idx=3)      # 出生(人)
natD = series_by(nat, val_idx=5)      # 死亡(人)
natBR = series_by(nat, val_idx=4)     # 出生率‰
natDR = series_by(nat, val_idx=6)     # 死亡率‰
migI = series_by(mig, val_idx=2)      # 迁入(人)
migO = series_by(mig, val_idx=4)      # 迁出(人)
migN = series_by(mig, val_idx=6)      # 净增(人)
migNR = series_by(mig, val_idx=7)     # 净增率‰

# 全市（分区合计口径，当代年鉴口径）
city_hk = {}
for y, d in sorted(hkS.items()):
    city_hk[y] = round(sum(d.values()), 2)
city_cz = {}
for y, d in sorted(czS.items()):
    city_cz[y] = round(sum(d.values()), 2)

# 长序列（2024 年鉴修订口径 + 公报）
ser_city = {}
for r in city[1:]:
    y = int(r[0]); ind = r[1]; v = num(r[2])
    if v is None:
        continue
    if '户籍总人口' in ind and '全市' not in ind:
        ser_city.setdefault(y, {})['户籍(修订序列)'] = v
    elif '常住人口' in ind:
        ser_city.setdefault(y, {})['常住'] = v
    elif '出生' in ind:
        ser_city.setdefault(y, {})['出生'] = v
    elif '死亡' in ind:
        ser_city.setdefault(y, {})['死亡'] = v
    elif '迁入' in ind:
        ser_city.setdefault(y, {})['迁入'] = v
    elif '迁出' in ind:
        ser_city.setdefault(y, {})['迁出'] = v
    elif '迁移净增' in ind:
        ser_city.setdefault(y, {})['迁移净增'] = v

# ---------- 关键指标 ----------
def grow(d1, d2):
    return round(d2 - d1, 2), round((d2 / d1 - 1) * 100, 1)

hk98 = {d: v for y, d in hkS.items() if y == 1998 for d, v in d.items()}
hk25 = {d: v for y, d in hkS.items() if y == 2025 for d, v in d.items()}
cz00 = {d: v for y, d in czS.items() if y == 2000 for d, v in d.items()}
cz25 = {d: v for y, d in czS.items() if y == 2025 for d, v in d.items()}

# 合并口径（东山→越秀、芳村→荔湾；萝岗→黄埔）下 1998→2025 各区户籍增量
merge = {'越秀区': ['越秀区', '东山区'], '荔湾区': ['荔湾区', '芳村区'], '黄埔区': ['黄埔区', '萝岗区']}
def merged_val(src, dist):
    parts = merge.get(dist, [dist])
    return sum(src.get(p, 0) for p in parts)
growth = {}
base_year = {}
for d in D11:
    v25 = hk25.get(d)
    # 基准年：1998（未设区的用建区首年，如南沙 2005）
    base = 1998
    v98 = merged_val(hk98, d)
    if not v98:
        for y in sorted(hkS):
            v98 = merged_val(hkS[y], d)
            if v98:
                base = y
                break
    if v98 and v25:
        growth[d] = (v98, v25, round(v25 - v98, 2), round((v25 / v98 - 1) * 100, 1))
        base_year[d] = base

# 2024 分区迁移净增（人）
net24 = {d: migN[2024][d] for d in D11 if migN.get(2024, {}).get(d) is not None}
# 2024 分区出生/死亡率
br24 = {d: natBR[2024][d] for d in D11 if natBR.get(2024, {}).get(d) is not None}
dr24 = {d: natDR[2024][d] for d in D11 if natDR.get(2024, {}).get(d) is not None}

# ---------- 工具 ----------
def series_data(series, years, dists, key):
    return [[series.get(y, {}).get(d) for d in dists] for y in years]

# 各区户籍序列（含旧区）
hk_all_dists = []
for y in sorted(hkS):
    for d in hkS[y]:
        if d not in hk_all_dists:
            hk_all_dists.append(d)

# 现 11 区户籍序列（1998-2025，含合并口径）
d11_hk_years = sorted(hkS)
d11_hk = {}
for d in D11:
    s = []
    for y in d11_hk_years:
        if y <= 2004:
            v = merged_val({dd: vv for y2, dd in hkS.items() if y2 == y for dd, vv in dd.items()}, d)
        else:
            v = hkS[y].get(d)
        s.append(round(v, 2) if v else None)
    d11_hk[d] = s

# 常住 11 区（年度+普查）
cz_d11 = {}
for d in D11:
    cz_d11[d] = [czS.get(y, {}).get(d) for y in sorted(czS)]

# ---------- 组装 HTML ----------
def line_opt(title, x, series, yname='万人', legend=True, stack=None, area=False, mark_break=True):
    """series: [{name, data}]"""
    se = []
    for s in series:
        item = {'name': s['name'], 'type': 'line', 'data': s['data'], 'symbolSize': 4,
                'lineStyle': {'width': 2}}
        if s.get('dash'):
            item['lineStyle']['type'] = 'dashed'
        if area:
            item['areaStyle'] = {'opacity': 0.12}
        se.append(item)
    opt = {
        'title': {'text': title, 'left': 'center', 'textStyle': {'fontSize': 15}},
        'tooltip': {'trigger': 'axis', 'triggerOn': 'click', 'renderMode': 'richText', 'confine': True},
        'legend': {'top': 30, 'type': 'scroll'},
        'grid': {'left': 50, 'right': 30, 'top': 70, 'bottom': 50, 'containLabel': True},
        'xAxis': {'type': 'category', 'data': [str(y) for y in x], 'name': '年份'},
        'yAxis': {'type': 'value', 'name': yname},
        'series': se,
    }
    return opt

def bar_opt(title, x, series, yname, horizontal=False, color_series=None):
    se = []
    for s in series:
        item = {'name': s['name'], 'type': 'bar', 'data': s['data'], 'barGap': '10%'}
        if s.get('stack'):
            item['stack'] = s['stack']
        se.append(item)
    opt = {
        'title': {'text': title, 'left': 'center', 'textStyle': {'fontSize': 15}},
        'tooltip': {'trigger': 'axis', 'triggerOn': 'click', 'renderMode': 'richText', 'confine': True},
        'legend': {'top': 30},
        'grid': {'left': 50, 'right': 30, 'top': 70, 'bottom': 50, 'containLabel': True},
        'series': se,
    }
    if horizontal:
        opt['xAxis'] = {'type': 'value', 'name': yname}
        opt['yAxis'] = {'type': 'category', 'data': x, 'inverse': True}
    else:
        opt['xAxis'] = {'type': 'category', 'data': x, 'name': yname}
        opt['yAxis'] = {'type': 'value', 'name': yname}
    return opt

charts = []
js = []

# 图1: 全市户籍 vs 常住（1998—2025 有效区间）
years_all = sorted(set(city_hk) | set(city_cz))
y_hk = [city_hk.get(y) for y in years_all]
y_cz = [city_cz.get(y) for y in years_all]
charts.append(line_opt('全市户籍人口与常住人口（1998—2025）', years_all,
                       [{'name': '户籍人口(分区合计)', 'data': y_hk},
                        {'name': '常住人口', 'data': y_cz, 'dash': True}],
                       yname='万人', area=True))
js.append(json.dumps({'id': 'c1', 'opt': charts[0]}, ensure_ascii=False))

# 图2: 各区户籍 1998-2025（现 11 区合并口径）
charts.append(line_opt('各区户籍人口（1998—2025，现11区口径）', d11_hk_years,
                       [{'name': d, 'data': d11_hk[d]} for d in D11], yname='万人'))
js.append(json.dumps({'id': 'c2', 'opt': charts[1]}, ensure_ascii=False))

# 图3: 各区常住（年度+普查）
charts.append(line_opt('各区常住人口（2000—2025）', sorted(czS),
                       [{'name': d, 'data': cz_d11[d]} for d in D11], yname='万人'))
js.append(json.dumps({'id': 'c3', 'opt': charts[2]}, ensure_ascii=False))

# 图4: 2024 年分区出生率/死亡率（横向柱）
br_x = [d for d in sorted(br24, key=lambda x: br24[x])]
charts.append(bar_opt('2024 年各区户籍出生率与死亡率（‰）', br_x,
                      [{'name': '出生率‰', 'data': [round(br24[d], 2) for d in br_x]},
                       {'name': '死亡率‰', 'data': [round(dr24[d], 2) for d in br_x]}],
                      yname='‰', horizontal=True))
js.append(json.dumps({'id': 'c4', 'opt': charts[3]}, ensure_ascii=False))

# 图5: 2024 年各区迁移净增（横向柱）
net_x = [d for d in sorted(net24, key=lambda x: net24[x])]
charts.append(bar_opt('2024 年各区户籍迁移净增（人）', net_x,
                      [{'name': '迁移净增(人)', 'data': [int(net24[d]) for d in net_x]}],
                      yname='人', horizontal=True))
js.append(json.dumps({'id': 'c5', 'opt': charts[4]}, ensure_ascii=False))

# 图6: 跨市流入 2010 vs 2020（分组柱）
ld_map = {r[0]: {'f20': num(r[1]), 'f10': num(r[2]), 'n20': num(r[3]), 'n10': num(r[4])} for r in ld[1:]}
ld_x = [d for d in D11]
charts.append(bar_opt('跨市流入人口（2010 vs 2020，普查口径，万人）', ld_x,
                      [{'name': '2020跨市流入', 'data': [ld_map[d]['f20'] for d in ld_x]},
                       {'name': '2010跨市流入', 'data': [ld_map[d]['f10'] for d in ld_x]}],
                      yname='万人'))
js.append(json.dumps({'id': 'c6', 'opt': charts[5]}, ensure_ascii=False))

# 图7: 净流入（常住-户籍）2010 vs 2020（含负值，分组柱）
charts.append(bar_opt('净流入人口=常住-户籍（2010 vs 2020，万人）', ld_x,
                      [{'name': '2020净流入', 'data': [ld_map[d]['n20'] for d in ld_x]},
                       {'name': '2010净流入', 'data': [ld_map[d]['n10'] for d in ld_x]}],
                      yname='万人'))
js.append(json.dumps({'id': 'c7', 'opt': charts[6]}, ensure_ascii=False))

# 图8/图9: 全市出生/死亡/迁入/迁出（1998 起，修订序列仅户籍总人口覆盖更早年份）
nat_years = sorted(y for y in ser_city if ser_city[y].get('出生') is not None)
b = [ser_city[y].get('出生') for y in nat_years]
dd = [ser_city[y].get('死亡') for y in nat_years]
charts.append(line_opt('全市户籍出生与死亡（1998—2025，人）', nat_years,
                       [{'name': '出生(人)', 'data': b}, {'name': '死亡(人)', 'data': dd}], yname='人'))
js.append(json.dumps({'id': 'c8', 'opt': charts[7]}, ensure_ascii=False))

# 图9: 全市迁入/迁出（1998-2024 分区合计 + 2025 公报）
mi = [ser_city[y].get('迁入') for y in nat_years]
mo = [ser_city[y].get('迁出') for y in nat_years]
charts.append(line_opt('全市户籍迁入与迁出（1998—2025，人）', nat_years,
                       [{'name': '迁入(人)', 'data': mi}, {'name': '迁出(人)', 'data': mo}], yname='人'))
js.append(json.dumps({'id': 'c9', 'opt': charts[8]}, ensure_ascii=False))

# 图10: 1998→2025 各区户籍增量（合并口径，横向柱）
g_x = [d for d in sorted(growth, key=lambda x: growth[x][2])]
charts.append(bar_opt('各区户籍人口增量（基准年→2025，万人，含区划合并口径）', g_x,
                      [{'name': '增量(万人)', 'data': [growth[d][2] for d in g_x]}],
                      yname='万人', horizontal=True))
js.append(json.dumps({'id': 'c10', 'opt': charts[9]}, ensure_ascii=False))

# ---------- 文字结论 ----------
def fmt(v):
    return f"{v:,.0f}"

hk_g, hk_p = grow(city_hk[1998], city_hk[2025])
cz_g, cz_p = grow(city_cz[2000], city_cz[2025])
gap25 = round(city_cz[2025] - city_hk[2025], 2)
gap10 = round(city_cz[2010] - city_hk[2010], 2) if 2010 in city_cz and 2010 in city_hk else None
gap00 = round(city_cz[2000] - city_hk[2000], 2) if 2000 in city_cz and 2000 in city_hk else None

# 高/低增长区
top_g = sorted(growth.items(), key=lambda x: -x[1][2])[:3]
low_g = sorted(growth.items(), key=lambda x: x[1][2])[:3]

# 出生率高低
br_sorted = sorted(br24.items(), key=lambda x: -x[1])
dr_sorted = sorted(dr24.items(), key=lambda x: -x[1])

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>广州各区人口变化分析（1998—2025）</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 0; background: #f5f6fa; color: #2c3e50; }}
  .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px 16px 60px; }}
  h1 {{ font-size: 24px; color: #1f4e79; margin-bottom: 4px; }}
  .sub {{ color: #666; font-size: 13px; margin-bottom: 24px; }}
  .card {{ background: #fff; border-radius: 10px; padding: 18px 20px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }}
  .card h2 {{ font-size: 16px; color: #1f4e79; margin: 0 0 10px; }}
  .card p, .card li {{ font-size: 14px; line-height: 1.75; }}
  .chart {{ width: 100%; height: 460px; }}
  .kpi {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 14px 0; }}
  .kpi div {{ flex: 1 1 200px; background: #f0f4fa; border-radius: 8px; padding: 12px 14px; }}
  .kpi .n {{ font-size: 22px; font-weight: 700; color: #1f4e79; }}
  .kpi .t {{ font-size: 12px; color: #666; }}
  .tag {{ display: inline-block; background: #e8f0fb; color: #1f4e79; border-radius: 4px; padding: 1px 8px; font-size: 12px; margin-right: 6px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: right; }}
  th {{ background: #1f4e79; color: #fff; }}
  td:first-child, th:first-child {{ text-align: left; }}
  .note {{ font-size: 12px; color: #888; line-height: 1.7; }}
</style>
</head>
<body>
<div class="wrap">
<h1>广州各区人口变化分析（1998—2025）</h1>
<div class="sub">数据来源：历年《广州统计年鉴》（1999—2025 版）· 广州市历年《人口规模及分布情况》公报 · 第五/六/七次全国人口普查公报及七普专项《广州市区域人口分布和人口流动情况分析》｜口径：户籍人口（公安户籍）与常住人口；区划沿革断档见各图注释</div>

<div class="card">
<h2>一、全市总览：常住与户籍的差距 = 净流入规模</h2>
<div class="kpi">
  <div><div class="n">{hk_g:+,.0f} 万</div><div class="t">户籍人口 1998→2025 增量（{hk_p:+.1f}%）</div></div>
  <div><div class="n">{cz_g:+,.0f} 万</div><div class="t">常住人口 2000→2025 增量（{cz_p:+.1f}%）</div></div>
  <div><div class="n">{gap25:,.0f} 万</div><div class="t">2025 年末常住−户籍（净流入规模）</div></div>
  <div><div class="n">{gap10:,.0f} 万 → {gap00:,.0f} 万</div><div class="t">净流入规模 2010 年 → 2000 年（常住−户籍）</div></div>
</div>
<p>全市户籍人口从 <b>{city_hk[1998]:,.2f} 万</b>（1998 年末）增至 <b>{city_hk[2025]:,.2f} 万</b>（2025 年末），27 年净增 <b>{hk_g:+,.0f} 万</b>（{hk_p:+.1f}%）；常住人口从 <b>{city_cz[2000]:,.2f} 万</b>（五普时点）增至 <b>{city_cz[2025]:,.2f} 万</b>，25 年净增 <b>{cz_g:+,.0f} 万</b>（{cz_p:+.1f}%）。常住与户籍之差即净流入人口（常住−户籍），2025 年末约 <b>{gap25:,.0f} 万</b>，约为户籍人口的 {gap25/city_hk[2025]*100:.0f}%，说明广州的人口增长高度依赖跨市迁入。注：1998—2003 年户籍数采用当年年鉴分区表合计口径，与 2024 版年鉴"主要年份"修订序列（1998 年 670.47 万）有系统性小幅差异，已在《数据来源与口径说明.md》注明。</p>
<div id="c1" class="chart"></div>
</div>

<div class="card">
<h2>二、分区户籍人口：天河、黄埔、番禺领跑，中心老区稳中有升</h2>
<p>按现 11 区口径（2005 年东山区并入越秀、芳村区并入荔湾；2015 年萝岗并入黄埔）回拼后：<b>{top_g[0][0]} {top_g[0][1][2]:+.2f} 万</b>、<b>{top_g[1][0]} {top_g[1][1][2]:+.2f} 万</b>、<b>{top_g[2][0]} {top_g[2][1][2]:+.2f} 万</b> 是户籍增量最大的三区；{low_g[0][0]}（{low_g[0][1][2]:+.2f} 万）、{low_g[1][0]}（{low_g[1][1][2]:+.2f} 万）、{low_g[2][0]}（{low_g[2][1][2]:+.2f} 万）增量最小。老城越秀、荔湾因空间饱和、户籍人口基数高，增速明显低于外围。南沙区 2012 年起接收番禺大岗/东涌/榄核三镇，其户籍数在 2011→2012 年由 15.68 万跳升至 36.74 万，属区划调整而非人口实际暴增。</p>
<div id="c2" class="chart"></div>
</div>

<div class="card">
<h2>三、分区常住人口：白云、天河、番禺为常住人口大户</h2>
<p>2025 年末常住人口前三：<b>白云 {city_cz and max(czS[2025].items(), key=lambda x:x[1])[1]:,.2f} 万</b>、<b>番禺 {czS[2025]['番禺区']:,.2f} 万</b>、<b>天河 {czS[2025]['天河区']:,.2f} 万</b>。常住口径下各区与户籍排位差异明显（如白云常住约为户籍的 2.9 倍），反映出各区吸引非户籍常住人口的能力差异。2000—2010 与 2015—2020 为常住人口快速扩张期。普查时点（2000/2010/2020，11 月 1 日）与年末口径存在系统性差异，图中 2000/2010/2020 采用普查公报值，其余为年鉴/公报年末值。</p>
<div id="c3" class="chart"></div>
</div>

<div class="card">
<h2>四、自然变动：出生率分化明显，黄埔/南沙高、老城低</h2>
<p>2024 年各区户籍出生率：<b>{br_sorted[0][0]} {br_sorted[0][1]:.2f}‰</b> 最高，其后为 {'、'.join(f'{d} {v:.2f}‰' for d, v in br_sorted[1:4])}；<b>{dr_sorted[0][0]} {dr_sorted[0][1]:.2f}‰</b> 死亡率最高，{'、'.join(f'{d} {v:.2f}‰' for d, v in dr_sorted[1:3])} 次之。新区（黄埔、南沙、增城）出生率明显高于老城（越秀、荔湾、海珠），老城区人口年龄结构更老。注意：2004—2006 年分区自然变动无公开数据（对应版年鉴文件加密），图中该段留空；2025 年分区明细尚未发布。</p>
<div id="c4" class="chart"></div>
</div>

<div class="card">
<h2>五、户籍迁移：白云、番禺、天河是迁入大户</h2>
<p>2024 年各区户籍迁移净增（迁入−迁出）：<b>{'、'.join(f'{d} {int(v):+,} 人' for d, v in sorted(net24.items(), key=lambda x:-x[1])[:4])}</b>。迁入集中于外围与产业新区，与新增就业、购房落户方向一致；越秀、荔湾等老城净增较小。2004—2006 年分区迁移数据同样缺公开来源，图中留空。</p>
<div id="c5" class="chart"></div>
</div>

<div class="card">
<h2>六、跨市流入与净流入（普查口径）</h2>
<p>按普查口径（居住本区且户口登记地在广州市外），全市跨市流入人口由 2010 年的 <b>475.98 万</b>增至 2020 年的 <b>937.88 万</b>，十年接近翻番。分区看，2020 年跨市流入前三为 <b>白云 {ld_map['白云区']['f20']:.2f} 万</b>、<b>番禺 {ld_map['番禺区']['f20']:.2f} 万</b>、<b>天河 {ld_map['天河区']['f20']:.2f} 万</b>。净流入（常住−户籍）方面，<b>越秀区是唯一净流出区</b>（2010 年 −1.20 万、2020 年 −13.47 万），其余 10 区均为净流入，白云（261.58 万）、番禺（157.15 万）、天河（123.13 万）净流入规模最大。</p>
<div id="c6" class="chart"></div>
<div id="c7" class="chart"></div>
</div>

<div class="card">
<h2>七、全市出生/死亡与迁入/迁出走势</h2>
<p>全市户籍出生人数 1998 年约 {fmt(ser_city[1998]['出生'])} 人，2016—2018 年"全面二孩"效应期间冲高（2017 年 {fmt(ser_city[2017]['出生'])} 人），此后回落至 2025 年约 {fmt(ser_city[2025]['出生'])} 人；死亡人数缓慢上升（1998 年 {fmt(ser_city[1998]['死亡'])} 人 → 2025 年 {fmt(ser_city[2025]['死亡'])} 人），自然增长整体收窄。户籍迁入在 2000—2001 年（{fmt(ser_city[2000]['迁入'])} / {fmt(ser_city[2001]['迁入'])} 人）与 2013 年前后形成两个高峰，2024 年迁入 {fmt(ser_city[2024]['迁入'])} 人、迁出 {fmt(ser_city[2024]['迁出'])} 人，机械增长仍是户籍人口增长的主引擎。</p>
<div id="c8" class="chart"></div>
<div id="c9" class="chart"></div>
</div>

<div class="card">
<h2>八、小结</h2>
<ul>
<li><b>总量</b>：户籍 674→1091 万（1998—2025，+{hk_p:.0f}%），常住 994→1910 万（2000—2025，+{cz_p:.0f}%）；常住增幅显著高于户籍，人口集聚度提升。</li>
<li><b>结构</b>：增长呈现"外围快于老城、新区承接人口"格局；天河、黄埔、番禺（含南沙承接番禺三镇）为户籍增长主力，白云、番禺、天河为常住与跨市流入主力。</li>
<li><b>自然变动</b>：新区出生率高、老城死亡率高；全市自然增长趋缓，2025 年自然增长仅 {fmt(ser_city[2025]['出生'] - ser_city[2025]['死亡'])} 人。</li>
<li><b>机械变动</b>：跨市迁入是人口增长绝对主引擎；净流入 2025 年约 {gap25:,.0f} 万，占常住人口 {gap25/city_cz[2025]*100:.0f}%。越秀区为唯一净流出区。</li>
<li><b>数据缺口</b>：2004—2006 年分区自然/迁移明细无公开来源；2025 年分区自然/迁移明细未发布；区划调整（2005、2012、2015 年）造成口径断档，跨期对比均已注明。</li>
</ul>
</div>

<div class="card">
<h2>附录：1998→2025 各区户籍增量明细（合并口径，万人）</h2>
<table>
<tr><th>区</th><th>基准年</th><th>基准值</th><th>2025</th><th>增量</th><th>增幅</th></tr>
{"".join(f"<tr><td>{d}</td><td>{base_year[d]}</td><td>{growth[d][0]:,.2f}</td><td>{growth[d][1]:,.2f}</td><td>{growth[d][2]:+,.2f}</td><td>{growth[d][3]:+.1f}%</td></tr>" for d in D11)}
</table>
<p class="note">注：越秀区 1998 年含东山区、荔湾区含芳村区、黄埔区含萝岗区（2005/2015 年并入）；番禺与南沙 2012 年存在三镇划转，跨期对比需注意口径断档；1998 年南沙区尚未设立（2005 年建区），图中南沙从 2005 年起算。</p>
</div>

</div>
<script>
var charts = {json.dumps(json.loads('[' + ','.join(js) + ']') if False else [json.loads(x) for x in js], ensure_ascii=False)};
window.addEventListener('resize', function(){{ Object.values(charts).forEach(function(c){{ var inst = echarts.getInstanceByDom(document.getElementById(c.id)); if (inst) inst.resize(); }}); }});
Object.values(charts).forEach(function(c){{ var el = document.getElementById(c.id); var inst = echarts.init(el); inst.setOption(c.opt); }});
</script>
</body>
</html>
"""

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)
print('REPORT OK:', OUT, len(html), 'bytes')
