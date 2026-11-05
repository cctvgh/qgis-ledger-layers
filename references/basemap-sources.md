# QGIS 在线底图源清单（含内网连通性实测）

## 坐标系对照（选错会整体偏移）

| 底图 | 坐标系 | 与 WGS84 工参 |
|---|---|---|
| Esri World Imagery | WGS84 | 直接吻合 ✅ |
| OSM | WGS84 | 直接吻合 ✅ |
| 天地图 `_w` 系列 | CGCS2000（Web 墨卡托） | 基本吻合（几乎不偏移）✅ |
| 高德 | GCJ-02（火星坐标） | 偏移几十~几百米，需纠偏 ⚠️ |
| 百度 | BD-09 | 偏移更大，需纠偏 ⚠️ |

运营商工参/台账经纬度基本是 GPS 实采 WGS84；高德/百度底图直接叠加会整体错位。

## URL 清单（QGIS 浏览器面板 → XYZ Tiles → 新建连接，直接粘贴）

**Esri World Imagery（免 key、WGS84、首选；注意 {z}/{y}/{x} 顺序！）**

```
https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}
```

**OSM（免 key；{z}/{x}/{y}）**

```
https://tile.openstreetmap.org/{z}/{x}/{y}.png
```

**天地图（需申请 tk；用 t0 新节点；参数名是 x/y/l）**

```
影像：https://t0.tianditu.gov.cn/DataServer?T=img_w&x={x}&y={y}&l={z}&tk=<KEY>
矢量：https://t0.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk=<KEY>
注记：https://t0.tianditu.gov.cn/DataServer?T=cia_w&x={x}&y={y}&l={z}&tk=<KEY>
```

key 申请：tianditu.gov.cn → 注册 → 控制台创建应用。`_w` = Web 墨卡托（与 WGS84 工参吻合）；`_c` = 经纬度投影。

**高德（免 key 但 GCJ-02 偏移，仅应急）**

```
矢量：https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}
影像：https://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=6&x={x}&y={y}&z={z}
```

## 连通性实测（内网必做）

公司内网防火墙**选择性放行**瓦片主机——推荐前必须逐主机实测（跑 `scripts/test_basemap_connectivity.ps1`）：

```powershell
Test-NetConnection -ComputerName <host> -Port 443 -InformationLevel Quiet
```

## 本机实测结果（湛江电信内网服务器，2026-11）

| 主机 | 结果 |
|---|---|
| server.arcgisonline.com（Esri） | ✅ 通 |
| t0.tianditu.gov.cn（天地图新节点） | ✅ 通 |
| webrd01.is.autonavi.com（高德） | ✅ 通 |
| tile.openstreetmap.org（OSM） | ❌ 不通 |
| services.arcgisonline.com（Esri 老节点） | ❌ 不通 |
| webmap0.tianditu.gov.cn（天地图老节点） | ❌ 不通 |

**结论**：首选 Esri World Imagery（免 key + WGS84 + 实测可连）；天地图 t0 需 key；高德仅应急（偏移）。
注意：连通性随防火墙策略变化，换环境/隔段时间应重测。

## 内网全不通时的替代

- 本地离线影像/栅格：图层 → 添加栅格图层（GeoTIFF/影像文件）
- 内网 WMTS/WMS 服务（向省公司/网管申请地址）
- 断网不影响矢量图层显示与编辑补点，仅底图空白
