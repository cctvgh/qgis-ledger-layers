# 更新日志

## v1.1.0 - 2026-11-05

- 新增**空间覆盖圈与统计**能力（SKILL.md 第七章节）：
  - 测地线半径圆生成（规避 PROJ `Invalid latitude` 无效几何）
  - Haversine 大圆距离圈内对象计数
  - QgsRuleBasedRenderer 规则高亮（≥N 单独高亮）
  - QgsPalLayerSettings 属性式标注 API（3.36 实测）
  - 跨层按字段关联汇总（如投效评级 ABCD）导出 Excel
- 新增 `references/qgis-spatial-analysis.md`（完整坑与代码）
- 新增 `scripts/coverage_circle.py`（参数化覆盖圆脚本，实测 58 圆/总覆盖 162 与手工一致）
- 记录关键教训：`CreateLayer(name, None, wkbPolygon)` 三参写法；`DeleteLayer` 破坏性操作须先确认新层可建成

## v1.0.0 - 2026-11-05

- 初版：台账坐标转 QGIS 图层六步流程（pandas 清洗 → UTF-8 无 BOM CSV → ogr2ogr → GPKG → 无头 .qgs → 离屏渲染验证）
- 防白板两件套（defaultViewExtent + 项目 CRS）
- 在线底图：Esri World Imagery 内置 + 内网主机连通性实测脚本
- 编码排障铁律（控制台 GBK 误显 ≠ 文件损坏）