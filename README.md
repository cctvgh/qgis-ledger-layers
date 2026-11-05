# 台账坐标转 QGIS 图层（qgis-ledger-layers）

> TeleAgent 技能 | 含经纬度的 Excel/CSV 台账 → QGIS 可编辑、可补点图层 + 覆盖圈空间分析

## 功能特性

- **台账转图层**：GeoPackage 多图层 + 双击即开 `.qgs` 项目（分类配色、默认视图范围、WGS84 CRS、内置 Esri 卫星底图），全部可编辑、可补点
- **空间覆盖分析**：测地线半径圆（1.5km 等）、Haversine 圈内对象计数、≥N 规则高亮、字段标注、按字段分类汇总并导出 Excel
- **内网友好**：零外部 Python 依赖（QGIS 自带 ogr2ogr + 无头 python-qgis），底图瓦片主机逐个连通性实测后再推荐
- **实战坑全记录**：打开白板根因（缺 defaultViewExtent/CRS）、缓冲圆无效几何（PROJ Invalid latitude）、UTF-8 BOM 破坏 ogr2ogr 列匹配、控制台 GBK 误显、Esri 瓦片 `{z}/{y}/{x}` 顺序、GCJ-02 偏移

## 快速开始

环境：Windows + QGIS 3.36+（`bin\ogr2ogr.exe`、`bin\python-qgis.bat`）+ 系统 Python（pandas/openpyxl）

1. 完整六步流程与 API 速查见 **SKILL.md** 与 `references/`
2. 覆盖圆一键脚本（需 QGIS 自带 Python）：

```
python-qgis.bat scripts/coverage_circle.py --gpkg X.gpkg --center 中心层 --target 对象层 \
    --radius_km 1.5 --out 圆层名 --center_field 基站名称 [--target_field 村名]
```

## 适用场景

运营商网优/客响/规划（基站工参、铁塔站址、投效评估、乡村覆盖规划）、监控与点位台账（防溺水/治安/接入网机房）、园区与物业点位管理——凡是"Excel 里有经纬度、想在 GIS 上看、画圈、数数量"的场景。

## 目录结构

```
SKILL.md                            技能主文档（六步流程 + 空间分析 + FAQ）
references/qgis-headless-api.md     无头 Python API 速查（3.36 实测）
references/qgis-spatial-analysis.md 覆盖圈与统计：Haversine/测地线/规则渲染/标注
references/basemap-sources.md       底图源清单与连通实测
scripts/coverage_circle.py          覆盖圆+计数脚本（参数化）
scripts/test_basemap_connectivity.ps1  底图主机连通探测
```

## 打赏支持

如果这个技能帮到了你，欢迎请作者喝杯茶 ☕

<img src="donate-wechat.jpg" alt="微信收款码" width="200"/>
<img src="donate-alipay.jpg" alt="支付宝收款码" width="200"/>

<sub>微信 / 支付宝收款码（赞赏支持，请注明你的昵称）</sub>

## License

MIT © 2026 cctvgh