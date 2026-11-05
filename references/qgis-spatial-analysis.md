# QGIS 空间覆盖圈与统计（3.36 实测）

本文件记录"给点图层做半径圆缓冲 + 统计圈内覆盖对象 + 规则高亮 + 按字段统计导出"的完整经验与坑。

## 一、核心坑：缓冲圆几何为什么会"不显示"

**症状**：为基站点生成 1.5km 缓冲圆图层后，QGIS 里半透明圆一个都不显示，只有点。

**根因**：用 `ogr` 的 `.Buffer()` 前把几何 `Transform()` 到 UTM/Web墨卡托(3857) 再 Buffer，**个别坐标触发 `PROJ: utm/webmerc: Invalid latitude`**，生成的圆几何无效 → QGIS 不画。两种投影（UTM 32650 / 3857）都踩过。

**铁律**：
1. **不要**用"投影→Buffer→再转回 4326"的方式做米制圆（易产生无效几何）。
2. 计数用 **Haversine 大圆距离**（纯 Python，不碰投影，绝对准确）。
3. 画圆用**测地线法**直接按大圆距离算圆上各点经纬度（不依赖投影变换），生成的 Polygon 必然有效。

```python
from math import radians, degrees, sin, cos, asin, atan2, pi
R = 6371000.0

def hav(lon1, lat1, lon2, lat2):            # 大圆距离(米)
    p1=radians(lat1); p2=radians(lat2); dp=radians(lat2-lat1); dl=radians(lon2-lon1)
    a=sin(dp/2)**2+cos(p1)*cos(p2)*sin(dl/2)**2
    return R*2*asin(a**0.5)

def circle_ring(lat, lon, radius_m, steps=64):   # 测地线圆：沿各方位角取等距点
    d=radius_m/R; lat1=radians(lat); lon1=radians(lon); ring=[]
    for i in range(steps):
        b=2*pi*i/steps
        lat2=asin(sin(lat1)*cos(d)+cos(lat1)*sin(d)*cos(b))
        lon2=lon1+atan2(sin(b)*sin(d)*cos(lat1), cos(d)-sin(lat1)*sin(lat2))
        ring.append((degrees(lon2), degrees(lat2)))
    ring.append(ring[0]); return ring
```

- 圈内判定：`hav(基站lon,基站lat, 村lon,村lat) <= radius_m`
- 用 `ogr.Geometry(ogr.wkbLinearRing)` + `AddPoint(lon,lat)` 组装，`wkbPolygon` 包环。

## 二、写入圆多边形到 GPKG（og_create 参数坑）

```python
from osgeo import ogr
ds = ogr.Open(gpkg, 1)                       # update 模式
if ds.GetLayerByName(OUT): ds.DeleteLayer(OUT)   # 重写前必删旧层，否则数据翻倍
lyr = ds.CreateLayer(OUT, None, ogr.wkbPolygon)  # ★几何类型是第3参；第2参是 srs(None=沿用)
for nm,tp in [("基站名称",ogr.OFTString),("覆盖自然村数",ogr.OFTInteger),("覆盖村清单",ogr.OFTString)]:
    fd=ogr.FieldDefn(nm,tp)
    if tp==ogr.OFTString: fd.SetWidth(254)
    lyr.CreateField(fd)
# 每要素：SetField + SetGeometry(polygon) + CreateFeature
```

> 坑：`CreateLayer(name, geom_type)` 这样写会把几何类型当 srs 报 `OSRSpatialReferenceShadow` 错，必须 `CreateLayer(name, None, ogr.wkbPolygon)`。
> **DeleteLayer 是破坏性操作**——务必确认新层能建成再删，否则旧数据直接没了（本次曾因 CreateLayer 参数错，圆层被删且未重建，导致全空）。

## 三、规则渲染高亮（≥N 单独高亮）

用 `QgsRuleBasedRenderer`（替代分类渲染器），API 3.36 实测：

```python
from qgis.core import QgsRuleBasedRenderer, QgsMarkerSymbol
high = QgsMarkerSymbol.createSimple({'color':'#D32F2F','color_border':'#ffffff','outline_width':'1.8','name':'diamond','size':'7'})
low  = QgsMarkerSymbol.createSimple({'color':'#9AA0A6','outline_width':'0.4','name':'diamond','size':'4'})
renderer = QgsRuleBasedRenderer(QgsRuleBasedRenderer.Rule(None))   # 根规则必须传 symbol(可 None)
r1 = QgsRuleBasedRenderer.Rule(high)
r1.setFilterExpression('"覆盖自然村数" >= 5'); r1.setLabel("覆盖>=5")
r2 = QgsRuleBasedRenderer.Rule(low); r2.setIsElse(True); r2.setLabel("覆盖<5")
renderer.rootRule().appendChild(r1); renderer.rootRule().appendChild(r2)
layer.setRenderer(renderer)
```

> 坑：`Rule()` **不能空参**（报 not enough arguments），`Rule(None)` 才行；构造 `Rule(sym,label,filter,0,0)` 第二参要字符串会报错，**一律用 setter**（setFilterExpression/setIsElse/setLabel/setSymbol）。

## 四、标注显示字段（QgsPalLayerSettings 3.36 属性式 API）

```python
from qgis.core import QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling
pal = QgsPalLayerSettings()
pal.fieldName = '"覆盖自然村数"'; pal.isExpression = False     # 字段
# 或表达式：pal.fieldName = 'concat("覆盖自然村数",\'村\')'; pal.isExpression = True
tf = QgsTextFormat(); tf.setSize(10); pal.setFormat(tf)
pal.placement = QgsPalLayerSettings.OverPoint
layer.setLabeling(QgsVectorLayerSimpleLabeling(pal)); layer.setLabelsEnabled(True)
```

> 坑：**没有** `setFieldName` / `setExpression` / `setPlacement`（3.36 改为属性赋值）；`CentroidInside` 枚举不存在（用 `OverPoint`）。离屏渲染不保证显示文字，需 QGIS 桌面端打开确认（labelsEnabled=True 已存）。

## 五、空间关联统计（两个图层按名称 join）

把"中心层覆盖数"与"评级层 ABCD"按名称关联，再分组汇总：

```python
cover={f["基站名称"]: f["覆盖自然村数"] for ...}   # 中心层
grade={f["基站名称"]: f["投效评级"][0].upper() for ...}   # 评级层，A/B/C/D
agg=defaultdict(lambda:[0,0])                    # grade -> [站数,覆盖总数]
for name,cnt in cover.items():
    g=grade.get(name,"?")
    agg[g][0]+=1; agg[g][1]+=(cnt or 0)
```
58 站全关联成功判据：`未匹配=[]`，且覆盖总数与逐站清单一致（勾稽）。

## 六、清单/统计导出

- 覆盖清单 CSV（`utf-8-sig`）→ pandas → openpyxl 写 xlsx；把顿号分隔清单 `split("、")` 拆多列（覆盖村1..N）。
- 统计表：`pd.read_csv(...); to_excel(...)`；表头 `PatternFill("solid", fgColor="2A5CAA")` + 白字 + freeze_panes="A2" + auto_filter。
- 交付口径在对话里给"Top N + 分类汇总表"，文件给全量。

## 七、归位与渲染验证

- 圆层放**中心点层下方**：`root.insertLayer(idx, layer)`（idx 随当前树调整）。
- 圆填充：`QgsFillSymbol.createSimple({'color':'rgba(42,92,170,45)','color_border':'#2A5CAA'})`（alpha 45 半透明）。
- 离屏渲染只验证"图层是否有效/有点"，不保证标注文字；逐像素统计：蓝色圆填充 `c.blue()>c.red() and c.blue()>120` 出现 >500 即圆可见；红点 `c.red()>170 and c.green()<100`。
- **图层对象在项目里多次重建会留冗余**（同 registry 多个同名）：每次重建前 `removeMapLayer(lid)` 清 registry + `removeChildNode` 清树，再 `addMapLayer+insertLayer`，避免同名重复。验证从 **layerTreeRoot().children()** 读（不要从 mapLayers().values() 读，会拿到 registry 里的旧副本）。