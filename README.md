# 城市研究分析项目

基于公开统计数据的房价与人口研究，分两个独立业务：

| 业务 | 目录 | 报告入口 |
|------|------|----------|
| **城市房价分析** | `city_housing/` | `city_housing/dist/房价基本面分析报告.html` |
| **人口变化分析** | `population_analysis/` | `population_analysis/广州各区人口变化分析.html` |

GitHub Pages 导航首页：<https://ycbc-team.github.io/house_prices_analysis/>

## 目录结构

```
house_prices_analysis/
├── city_housing/          城市房价分析业务（三变量估值模型）
│   ├── raw/                原始来源文件（URL + 摘录 + 口径）
│   ├── scripts/            转录与校验脚本
│   ├── parsed/             结构化数据（CSV/JSON）
│   └── dist/              最终 HTML 报告 + assets
├── population_analysis/    人口变化分析业务（1998—2025 分区全景）
│   ├── build_dataset.py    数据构建脚本
│   ├── build_report.py     HTML 报告生成脚本
│   ├── raw/                派生长表数据
│   └── 广州各区人口变化分析.html
└── docs/                   GitHub Pages 发布层（首页 + 各业务报告副本）
    ├── index.html          导航首页
    ├── housing/index.html  房价报告
    └── population/index.html  人口报告
```

## 城市房价分析（摘要）

核心框架为「常住人口 × 人均收入 × 住房供给」三变量模型，覆盖广州 7 区、9 个一二线城市、6 个三四线城市与山东三城样本。

```bash
python3 city_housing/scripts/transcribe_raw.py   # 转录 raw → parsed
python3 city_housing/scripts/validate_data.py    # 校验数据
```

## 人口变化分析（摘要）

广州各区 1998—2025 年户籍/常住人口、自然变动（出生/死亡）、户籍迁移（迁入/迁出）、普查口径跨市流入与净流入，数据来自历年《广州统计年鉴》、统计局公报与第五/六/七次人口普查。

```bash
python3 population_analysis/build_dataset.py    # 重建数据集
python3 population_analysis/build_excel.py       # 导出 Excel
python3 population_analysis/build_report.py     # 重建 HTML 报告
```

> 本仓库数据仅供研究参考，不构成购房建议。
