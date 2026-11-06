---
name: qgis-ledger-layers
description: "Convert Excel/CSV ledgers containing longitude/latitude to editable QGIS layers - multi-layer GeoPackage plus .qgs project with editable layers, default zoom, project CRS and built-in XYZ basemap. Also runs spatial coverage analysis: geodesic radius buffer circles, Haversine in-circle counting, rule-based highlight (e.g. at-least-N), field labeling, and aggregate stats exported to Excel. Pipeline: pandas clean to UTF-8 CSV to ogr2ogr to GPKG to QGIS headless Python to offscreen render. Covers blank-canvas cause (missing defaultViewExtent/CRS), invalid buffer geometry (PROJ InvalidLatitude - use geodesic), UTF-8 BOM, Esri tile URL order, GCJ-02 offset, intranet basemap connectivity. Trigger on 转为QGIS图层/加入图层/可补点可编辑/gpkg/qgs/叠加图层/台账上图/点位转图层/划圆/覆盖圆/缓冲圈/覆盖多少/覆盖分析/统计汇总/村名标注/村委会/全量自然村/村委会位置."
name_cn: "台账坐标转QGIS图层"
description_cn: "含经纬度台账转QGIS可编辑图层(GeoPackage+.qgs项目+内置底图)，并支持覆盖圈分析：半径圆、圈内覆盖对象计数、规则高亮(如≥N)、字段标注、按字段汇总导出。含白板/无效几何(PROJ坑)/编码陷阱/无头API速查/底图连通性实测。"
---

# 台账坐标转 QGIS 图层（qgis-ledger-layers）

把**含经纬度列的表格数据**（Excel/CSV 台账、点位清单）转为 **QGIS 可编辑、可补点的矢量图层**，交付可直接双击打开的项目文件。

- 触发词：转为QGIS图层 / 加入图层 / 可补点可编辑 / GeoPackage / gpkg / qgs / 叠加地图、底图 / 台账上图 / 点位转图层
- 典型输入：基站工参台账（LTE/5G/联通共享/铁塔站址）、投效比评估表、乡村覆盖规划表、接入网点清单、防溺水/监控点位台账
- 典型输出：`<名称>.gpkg`（多图层）+ `<名称>.qgs`（配色+默认视图+CRS+内置底图）+ `使用说明.md`
- 边界：要 HTML 地图可视化报告而非可编辑 GIS 图层时走 wireless-scout / html-generator；本技能只管 QGIS 矢量图层与项目

## 环境前提（Windows + QGIS 3.36 实测）

- QGIS 装于 `C:\Program Files\QGIS 3.36.0`：`bin\ogr2ogr.exe`、`bin\ogrinfo.exe`、`bin\python-qgis.bat`（自带 osgeo/PyQt5 的无头 Python）
- 系统 Python 有 pandas/openpyxl、**没有** osgeo/geopandas → 几何写入一律走 ogr2ogr，项目操作一律走 python-qgis.bat
- 内网防火墙**选择性放行**底图瓦片主机 → 推荐底图前必须逐主机实测（第五步）

## 六步流程

### 1. 读取与清洗（系统 Python + pandas）

- Excel：`pd.read_excel(path, sheet_name=..., engine='openpyxl', dtype=str, header=0)`；**双行合并表头用 `header=1` 读第二行**
- CSV：编码按 `utf-8 → gbk → gb18030` 依次尝试（运营商导出常为 GBK）
- 列名清洗（中文全角括号、`&/()[]{}<>*?"'，。、；：`、换行制表符都会给 GPKG/表达式埋雷）：

```python
import re
SPECIAL = re.compile(r'[&/\\()（）\[\]{}<>*?"\'，。、；：\n\r\t]+')
def clean_col(name):
    n = SPECIAL.sub('_', str(name).strip())
    n = n.replace('-', '_').replace(' ', '_').replace('.', '_')
    return re.sub(r'_+', '_', n).strip('_') or 'field'
```

- 坐标列转 float，按本地范围校验（湛江：lon 105–116 / lat 18–25），NaN/0/越界剔除并**计数报告**（"有效 N / 剔除 M"）
- 表头可能有错别字：如"纬度"写成"**维度**"——按列名+值域双重识别
- 扇区表按基站名 `drop_duplicates(subset=[key], keep='first')` 另出"物理站点"去重层

### 2. 导出 CSV —— 必须 UTF-8 **无 BOM**

`df.to_csv(path, index=False, encoding='utf-8')`（**不是** `utf-8-sig`）

> 陷阱：BOM 粘在首列列名上，ogr2ogr 的 `X_POSSIBLE_NAMES=LON` 匹配失败，坐标列识别不出。

### 3. ogr2ogr 写入 GeoPackage

坐标列统一命名 `LON/LAT`，用 Python subprocess 调 QGIS 自带 ogr2ogr（实测最稳）：

```python
cmd = [OGR2OGR, "-f", "GPKG", out_gpkg, in_csv, "-nln", layer_name,
       "-oo", "X_POSSIBLE_NAMES=LON", "-oo", "Y_POSSIBLE_NAMES=LAT",
       "-oo", "KEEP_ATTR_COLUMNS=YES", "-oo", "AUTODETECT_TYPE=YES",
       "-a_srs", "EPSG:4326", "-nlt", "POINT",
       "-lco", "ENCODING=UTF-8"]            # 首层：创建文件
# 后续层追加新图层：cmd += ["-update", "-append"]
# 重写同图层（脚本重跑防数据翻倍）：cmd += ["-update", "-overwrite"]
subprocess.run(cmd)
```

- 中文图层名/字段名 GPKG 完整支持（`·`、`=` 等字符也能保留）
- AUTODETECT_TYPE 对含空值的数值列（如方位角）判为 String——不影响使用，QGIS 表达式 `to_real("列名")` 转换，交付说明注明
- 验证：`ogrinfo -so <gpkg>` 列图层；`ogrinfo -al -so <gpkg> <layer>` 看 Feature Count / Extent / SRS

### 4. 无头生成 .qgs（"打开白板"的根因就在这步）

用户双击打开**白板/无反应**的两大根因：**项目没写 defaultViewExtent**（画布落在空范围）+ **项目 CRS 为 none**。必做：

```python
project.setCrs(QgsCoordinateReferenceSystem.fromEpsgId(4326))
vs = project.viewSettings()
vs.setDefaultViewExtent(QgsReferencedRectangle(
    QgsRectangle(109.4, 20.1, 111.2, 22.0),      # 数据全域范围
    QgsCoordinateReferenceSystem.fromEpsgId(4326)))
project.write(qgs_path)
```

API 陷阱（QGIS 3.36 实测，完整速查见 references/qgis-headless-api.md）：

- `setDefaultViewExtent` 只收 `QgsReferencedRectangle`，构造是 `(QgsRectangle, crs)` 两参，不是四坐标+crs
- `QgsCoordinateReferenceSystem(4326)` 已弃用 → `fromEpsgId(4326)`
- 图层树：置底 `root.addLayer(layer)`、置顶/插位 `root.insertLayer(idx, layer)`；**没有** `insertNode`/`count`
- 符号：`QgsMarkerSymbol.createSimple({...})`；**不存在** `QgsSimpleMarkerSymbol`
- PowerShell 调 `python-qgis.bat -c "..."` 引号嵌套必炸 → 一律写 .py 文件再 `& "...\python-qgis.bat" ".temp\x.py"`

### 5. 在线底图（XYZ）

首选 **Esri World Imagery**（免 key、WGS84、与工参吻合）：

```
https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}
```

> **Esri 顺序是 {z}/{y}/{x}**（OSM 是 {z}/{x}/{y}），粘错不出图。

```python
uri = ("type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/"
       "World_Imagery/MapServer/tile/{z}/{y}/{x}&zmin=0&zmax=19&crs=EPSG:3857")
esri = QgsRasterLayer(uri, "Esri卫星影像", "wms")
p.addMapLayer(esri, False); p.layerTreeRoot().addLayer(esri)   # 置底
```

- **推荐前必逐主机实测连通性**（内网选择性放行）：跑 `scripts/test_basemap_connectivity.ps1`；本机实测 OSM / services.arcgisonline / webmap0.tianditu 不通，server.arcgisonline / t0.tianditu / webrd01(高德) 通
- 高德/百度 = GCJ-02 火星坐标，直接叠 WGS84 工参整体偏移需纠偏；Esri/OSM/天地图`_w` 基本吻合
- URL 清单与坐标系对照详见 references/basemap-sources.md

### 6. 离屏渲染验证（防"交付即白板"）

用项目 defaultViewExtent 渲染整幅 PNG 并统计非白像素比例：纯点图层 ≈10–15% 即点位可见；含底图 ≈100%（瓦片铺满）。代码见 references/qgis-headless-api.md 第 7 节。另读回项目验证图层数、图层树顺序、EXTENT、PROJCRS。

## 编码排障铁律（本类任务最高频误诊）

**PowerShell 控制台按 GBK 显示 UTF-8 文件，中文看着是乱码（"婀涙睙…"）≠ 文件损坏。**

- 判断真实编码：Python `open(p,'rb').read().decode('utf-8')` 验证，别信控制台渲染
- **严禁**按控制台乱码做"逆编码修复"（GBK↔UTF-8 双重转换）——会把好文件改成"锟斤拷"真乱码；QGIS 无头写出的 .qgs 本来就是正确 UTF-8
- 动 .qgs 前先 `Copy-Item` 备份，改坏可回滚

## 补点自动填经纬度（让新增要素开箱即用）

生成项目后，为所有点图层的 `LON/LAT` 字段设置默认值 `$x`/`$y`，**新增要素时经纬度自动按几何坐标填入，无需手工录入**（否则 QGIS 桌面端手动补点时经纬度留空，使用者还得自己补算）。

```python
from qgis.core import QgsApplication, QgsProject, QgsDefaultValue, QgsVectorLayer
# 初始化/read 项目后：
for l in p.mapLayers().values():
    if not isinstance(l, QgsVectorLayer): continue
    lon_i = l.fields().indexOf("LON"); lat_i = l.fields().indexOf("LAT")
    if lon_i >= 0 and lat_i >= 0:
        l.setDefaultValueDefinition(lon_i, QgsDefaultValue("$x"))
        l.setDefaultValueDefinition(lat_i, QgsDefaultValue("$y"))
p.write(qgs_path)   # 必写回项目才持久化
```

- **类名**：QGIS 3.36 是 `QgsDefaultValue`（**不存在** `QgsDefaultValueDefinition`，import 会报 ImportError），构造 `QgsDefaultValue("$x")`
- `$x`/`$y` 取**几何坐标**；本项目 CRS=EPSG:4326，故新增点自动填 WGS84 经纬度，符合工参口径
- 写入后务必**重新读回项目**验证 `defaultValueDefinition(idx).isValid()` 为 True，确认已持久化

## 追加新图层（用户回头加表的标准动作）

用户常分多次把新台账加进同一项目：

1. 新表走第 1–3 步，`-update -overwrite` 写入同一 GPKG
2. python-qgis 读现有 .qgs → `p.removeMapLayer(lid)` 移除同名旧层 → 加新层 `root.insertLayer(idx, layer)` → 保存
3. 重跑离屏渲染验证 + 更新使用说明的图层清单表

## 配色建议

统一色盘：蓝 `#2A5CAA` / 绿 `#2A7D3F` / 琥珀 `#C58A24` / 红 `#B00020` / 紫 `#5B4B8A` / 灰 `#9AA0A6` / 酒红 `#8B1A2F`。评估类图层按评级分类着色（A绿/B蓝/C琥珀/D红），台账类按频段/制式分类，去重站点层用单符号。

## QGIS 桌面端常见问题（答复口径）

| 用户问题 | 答复 |
|---|---|
| 怎么补点/编辑 | 选中图层 → 点铅笔**编辑模式** → 点「添加要素」→ 图上点一下 → 弹属性窗填好 → 点**OK（仅确认图形）** → 必须再点铅笔右侧「**保存图层编辑**」（或 Ctrl+S）才真正写入 → 完成后退出编辑模式 |
| 图层拖不动 | 用图层面板工具栏「上移▲/下移▼」按钮；或按住图层名先水平移再竖拖，出现蓝色横线才松手 |
| 怎么改符号 | 图层右键 → 属性 → 符号化；换"值"字段即按乡镇/评级等重新分类着色；符号编辑器"应用于"选"所有分类"或"仅当前分类" |
| 底图没显示 | 先测瓦片主机连通性（内网拦截最常见），换实测可连的源；断网时矢量层仍正常显示可编辑 |
| 数值列是文本 | AUTODETECT 对含空值列判 String，表达式 `to_real("列名")` 转换 |
| 打开白板 | 项目缺 defaultViewExtent/CRS，按第 4 步重生成；应急让用户按 Ctrl+Shift+Z 缩放至全部图层 |
| 点OK后没保存，新点消失了 | 点「OK」只是确认图形，**未真正写入**；必须再点铅笔旁「保存图层编辑」/Ctrl+S。若退出编辑模式弹"保存更改?"务必选**保存**，否则本次补点丢失 |

## 七、空间覆盖圈与统计（缓冲/覆盖计数/高亮/统计导出）

台账上图层后的高频扩展：给点图层做半径圆、统计圈内覆盖对象数、按字段汇总。

1. **覆盖圆 + 计数**：直接用脚本（已测试）——
   ```
   & "...\python-qgis.bat" scripts/coverage_circle.py --gpkg X.gpkg \
       --center 中心层 --target 对象层 --radius_km 1.5 --out 圆层名 \
       --center_field 基站名称 [--center_town_field 乡镇] [--target_field 村名]
   ```
   输出圆 polygon 图层，含 `覆盖对象数`、`对象清单`。
2. **米制缓冲铁律**：**禁止**"投影→Buffer→转回 4326"——PROJ UTM/3857 会 `Invalid latitude` 生成无效几何 → 圆在 QGIS **不显示**。脚本内置 Haversine 大圆距离计数 + 测地线圆（不依赖投影，几何必有效）。
3. **高亮（≥N 单独高亮）**：`QgsRuleBasedRenderer`，根规则 `Rule(None)`，规则用 `setFilterExpression`/`setIsElse`/`setLabel`（**不要**构造 `Rule(sym,label,filter,0,0)`）。
4. **标注字段**：`QgsPalLayerSettings` **属性式** API（`pal.fieldName`/`pal.isExpression`/`pal.format`/`pal.placement`，无 `setFieldName` 等方法）+ `layer.setLabelsEnabled(True)`。
5. **跨层汇总**：两图层按名称 join，`defaultdict` 按字段（如投效评级 ABCD）汇总；勾稽口径=覆盖总数与逐站清单一致、未匹配=[]。
6. 圆放**中心点层下方** `root.insertLayer(idx, layer)`；半透明填充 `QgsFillSymbol.createSimple({'color':'rgba(42,92,170,45)'})`。
7. 详细坑、API 与代码见 `references/qgis-spatial-analysis.md`。

## 八、标注、地名底图与全量要素

- **标注字段 isExpression 陷阱**：字段引用必须 `pal.isExpression=True` + `pal.fieldName='"字段名"'`（带双引号表达式）；写成 `isExpression=False` + 带引号 → QGIS 找不到字段，**标注空白不出字**。
- **带地名底图**：Esri World Imagery 无地名，叠加 **Esri World Street Map**（同 `server.arcgisonline.com` 域名可连）看道路/地名；最可靠是给自然村层开村名标注。
- **村委会位置** = 按"所属大行政村/村委会"字段 `groupby` 取平均经纬度生成点层；**全量自然村** = 老 .xls 多 sheet `read_excel(header=1)` 读子表头 + 按"所属县级分公司"过滤区域，坐标列常为"村中心经度/纬度"。
- 全量密集标注字号小 + 白底描边，QGIS 自动避让。
- 详见 `references/qgis-spatial-analysis.md` 第八、九节。

## 交付物清单

- `<名称>.gpkg` — 多图层，WGS84/EPSG:4326，可编辑可补点
- `<名称>.qgs` — 双击打开：配色 + 默认视图范围 + CRS + 内置底图（提示用 QGIS 3.36+ 打开，旧版如 3.8 有兼容告警）
- `使用说明.md` — 图层清单表（自顶向下）+ 补点/编辑/底图操作 + 坐标系提示
- 可选 `QGIS底图叠加清单.md` — 可用 URL + 连通性实测 + 纠偏说明

## 支持文件

- `references/qgis-headless-api.md` — 无头 Python API 速查（初始化/图层/渲染器/图层树/防白板两件套/XYZ 底图/离屏渲染/报错对照表，全部 3.36 实测）
- `references/qgis-spatial-analysis.md` — 空间覆盖圈与统计：Haversine/测地线圆代码、PROJ 无效几何坑、规则高亮、标注属性式 API、跨层汇总、圆层归位
- `references/basemap-sources.md` — 底图源 URL 清单、坐标系对照（WGS84/CGCS2000/GCJ-02）、连通性实测命令与本机结果
- `scripts/test_basemap_connectivity.ps1` — 底图主机 443 连通性探测（可重复运行）
- `scripts/coverage_circle.py` — 覆盖圆+计数脚本（测地线圆/Haversine，参数化，已测试：58 圆/总覆盖 162）
