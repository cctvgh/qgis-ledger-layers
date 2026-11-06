# QGIS 3.36 无头 Python API 速查（python-qgis.bat 实测可用）

所有代码在 `C:\Program Files\QGIS 3.36.0\bin\python-qgis.bat` 下验证通过。
PowerShell 调用方式（**勿用 `-c` 内联**，引号嵌套必炸；一律写 .py 文件）：

```powershell
& "C:\Program Files\QGIS 3.36.0\bin\python-qgis.bat" ".temp\script.py"
```

## 1. 初始化 / 退出

```python
from qgis.core import QgsApplication
qgs = QgsApplication([], False)
qgs.setPrefixPath("C:/Program Files/QGIS 3.36.0/apps/qgis", True)
qgs.initQgis()
# ... 业务代码 ...
qgs.exitQgis()
```

## 2. 加载 GPKG 图层

```python
from qgis.core import QgsVectorLayer
uri = gpkg_path + "|layername=" + layer_name     # 注意 |layername= 语法
layer = QgsVectorLayer(uri, layer_name, "ogr")
layer.isValid()        # True 才可用
layer.featureCount()   # 要素数
[f.name() for f in layer.fields()]   # 字段名（中文正常）
```

## 3. 符号与渲染器

```python
from qgis.core import (QgsMarkerSymbol, QgsSingleSymbolRenderer,
                       QgsCategorizedSymbolRenderer, QgsRendererCategory)
# 单符号
sym = QgsMarkerSymbol.createSimple({'color': '#2A5CAA', 'color_border': '#ffffff',
                                    'outline_width': '0.4', 'name': 'circle', 'size': '3'})
layer.setRenderer(QgsSingleSymbolRenderer(sym))
# 分类（如按投效评级 A绿/B蓝/C琥珀/D红）
COLORS = {'A': '#2A7D3F', 'B': '#2A5CAA', 'C': '#C58A24', 'D': '#B00020'}
values = sorted({f['投效评级'] for f in layer.getFeatures()})   # 先取实际值
cats = [QgsRendererCategory(v, QgsMarkerSymbol.createSimple(
            {'color': COLORS.get(v[:1], '#9AA0A6'), 'size': '4'}), v)
        for v in values]
layer.setRenderer(QgsCategorizedSymbolRenderer('投效评级', cats))
```

- **不存在 `QgsSimpleMarkerSymbol`**（import 即报错），一律 `QgsMarkerSymbol.createSimple`
- 分类字段不存在时降级为单符号，别让脚本崩
- **分类渲染空值/NULL 隐形**（分类着色的图层补点时评级留空 → 点不显示颜色，看着像丢）：
  - 空串 `''` 与 SQL `NULL` 是**两个不同值**，必须**分开建两个分类**才能都显示：
    ```python
    gray_b = QgsMarkerSymbol.createSimple({'color':'154,160,166,255','size':'2'})
    gray_n = QgsMarkerSymbol.createSimple({'color':'176,0,32,255','size':'2'})
    r.addCategory(QgsRendererCategory('',   gray_b, '未评级(空)'))    # value 必须是单值 str ''
    r.addCategory(QgsRendererCategory(None, gray_n, '未评级(NULL)'))  # value 用 None 表示 SQL NULL
    ```
  - **陷阱**：`addCategory` 后 `QgsRendererCategory` 的 value **不要用 list**（如 `[None,'']` 会被 QGIS 规整成 `['','']`，导致 `categoryIndexForValue('')`/`(None)` 都返回 -1，空值**仍不显示**）
  - **验证必做**（不用离屏渲染，直接查匹配索引）：
    ```python
    assert r.categoryIndexForValue('')   >= 0   # 空串命中「未评级(空)」
    assert r.categoryIndexForValue(None) >= 0   # NULL 命中「未评级(NULL)」
    ```
- **分类渲染器增删改**：`addCategory` / `deleteCategory(idx)` / `updateCategoryValue(idx, val)` / `categories()`（返回 list，`c.value()` 取值）

## 4. 图层树（顺序 = 渲染顺序，第一个在最上、最后一个垫底）

```python
p.addMapLayer(layer, False)          # 先入项目（不自动进树）
root = p.layerTreeRoot()
root.addLayer(layer)                 # 追加到末尾 = 最底（底图用这招）
root.insertLayer(0, layer)           # 插到顶部
root.insertLayer(idx, layer)         # 插到指定位置
nodes = root.children()              # 子节点列表（没有 count()，用 len()）
[n.name() for n in root.children()]  # 自顶向下顺序，验证用
```

- **没有 `insertNode` / `count`**（实测报 AttributeError）
- 更新图层时先移除同名旧层防重复：

```python
for lid, l in list(p.mapLayers().items()):
    if l.name() == NAME:
        p.removeMapLayer(lid)
```

## 5. 项目保存与防白板两件套

```python
from qgis.core import (QgsRectangle, QgsReferencedRectangle,
                       QgsCoordinateReferenceSystem)
p.setCrs(QgsCoordinateReferenceSystem.fromEpsgId(4326))     # ① 项目 CRS 必设
vs = p.viewSettings()
vs.setDefaultViewExtent(QgsReferencedRectangle(             # ② 打开即缩放到数据全域
    QgsRectangle(109.4, 20.1, 111.2, 22.0),
    QgsCoordinateReferenceSystem.fromEpsgId(4326)))
p.write(qgs_path)    # 返回 bool
```

缺 ①② 任一项，用户双击打开就是**白板**（画布落在空范围 / CRS 未知）。

## 6. XYZ 在线底图

```python
from qgis.core import QgsRasterLayer
uri = ("type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/"
       "World_Imagery/MapServer/tile/{z}/{y}/{x}&zmin=0&zmax=19&crs=EPSG:3857")
esri = QgsRasterLayer(uri, "Esri卫星影像", "wms")    # provider 是 "wms"
p.addMapLayer(esri, False)
p.layerTreeRoot().addLayer(esri)                     # 置底
```

- Esri 瓦片 URL 顺序 **{z}/{y}/{x}**（OSM 是 {z}/{x}/{y}）
- 瓦片需联网；断网时底图空白但矢量层正常显示可编辑

## 7. 离屏渲染验证（防交付白板）

```python
from qgis.core import QgsMapSettings, QgsMapRendererCustomPainterJob
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QImage, QColor, QPainter
ms = QgsMapSettings()
ms.setOutputSize(QSize(1600, 1200))
ms.setDestinationCrs(p.crs())
ms.setExtent(p.viewSettings().defaultViewExtent())   # QgsReferencedRectangle 可直接传
ms.setLayers(list(p.mapLayers().values()))
img = QImage(QSize(1600, 1200), QImage.Format_ARGB32)
img.fill(QColor(255, 255, 255, 255))
pr = QPainter(img)
job = QgsMapRendererCustomPainterJob(ms, pr)
job.start(); job.waitForFinished(); pr.end()
img.save(out_png, "PNG")
# 步长采样统计非白像素：
w, h, nonwhite = img.width(), img.height(), 0
for x in range(0, w, 4):
    for y in range(0, h, 4):
        c = img.pixelColor(x, y)
        if c.red() < 250 or c.green() < 250 or c.blue() < 250:
            nonwhite += 1
ratio = nonwhite / ((w // 4) * (h // 4))
```

判读：纯点图层 ratio≈0.10–0.15 即点位可见；含底图应≈1.0（瓦片铺满）。

## 8. 读回验证

```python
p2 = QgsProject.instance()
p2.read(qgs_path)
for l in p2.mapLayers().values():
    print(l.name(), l.featureCount())
print(p2.viewSettings().defaultViewExtent())
print(p2.crs().authid())     # 应为 EPSG:4326
```

## 9. 报错对照表（实测踩坑）

| 报错 | 原因 | 修正 |
|---|---|---|
| `cannot import name 'QgsSimpleMarkerSymbol'` | 类不存在 | `QgsMarkerSymbol.createSimple({...})` |
| `setDefaultViewExtent(): unexpected type 'QgsRectangle'` | 需带 CRS 矩形 | `QgsReferencedRectangle(QgsRectangle(...), crs)` |
| `QgsReferencedRectangle(): arguments did not match any overloaded call` | 传了四坐标+crs | 改 `(QgsRectangle, crs)` 两参 |
| `'QgsLayerTree' object has no attribute 'insertNode'/'count'` | API 名不同 | `insertLayer(idx, layer)` / `addLayer(layer)` / `len(root.children())` |
| `'QgsMapSettings' object has no attribute 'setProjectionsEnabled'` | 已移除 | 只 `setDestinationCrs` |
| `'QgsReferencedRectangle' object has no attribute 'rect'` | 无此方法 | 对象直接传 `setExtent` |
| `QgsCoordinateReferenceSystem constructor is deprecated` | 弃用警告 | `fromEpsgId(4326)` |
| PowerShell `The string is missing the terminator` | `-c "..."` 引号嵌套 | 写 .py 文件再调用 |
| 进程退出码 `-1073741819`(0xC0000005 段错误)，无任何 Python 输出 | 无头环境调了 `QgsRenderContext.fromMapSettings(ms)` 渲染上下文 | **不要用渲染上下文**验证；改 `renderer.categoryIndexForValue(val)` 做逻辑匹配 |
| Python `SyntaxError: f-string expression part cannot include a backslash` | **Python 3.12+ 的 f-string 表达式里不允许 `\`**，如 `f"{f['字段']!r}"` 里的反斜杠 | 先取到变量再拼：`name=str(f['字段'])` → 再 `f"...{name}..."`，或用 `%` 格式化 |
