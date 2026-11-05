#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""为GPKG中一个点图层生成半径圆(测地线)，统计圈内另一图层点数，写出圆polygon图层。

用法(用QGIS自带python跑，环境需osgeo):
  python coverage_circle.py --gpkg X.gpkg --center 中心层 --target 对象层 \\
       --radius_km 1.5 --out 圆层名 --center_field 基站名称 [--target_field 村名] [--center_town_field 乡镇]

要点: 计数用Haversine大圆距离; 圆几何用测地线法(不依赖PROJ投影, 避免Invalid latitude无效几何)。
"""
import argparse, csv, sys
from math import radians, degrees, sin, cos, asin, atan2, pi

try:
    from osgeo import ogr
except ImportError:
    sys.exit("需要osgeo(用QGIS自带python-qgis运行): python-qgis.bat 本脚本")

R = 6371000.0
STEPS = 64

def hav(lon1, lat1, lon2, lat2):
    p1 = radians(lat1); p2 = radians(lat2)
    dp = radians(lat2-lat1); dl = radians(lon2-lon1)
    a = sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
    return R*2*asin(a**0.5)

def circle_ring(lat, lon, radius_m):
    d = radius_m/R; lat1 = radians(lat); lon1 = radians(lon); ring = []
    for i in range(STEPS):
        b = 2*pi*i/STEPS
        lat2 = asin(sin(lat1)*cos(d)+cos(lat1)*sin(d)*cos(b))
        lon2 = lon1 + atan2(sin(b)*sin(d)*cos(lat1), cos(d)-sin(lat1)*sin(lat2))
        ring.append((degrees(lon2), degrees(lat2)))
    ring.append(ring[0]); return ring

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpkg", required=True, help="GeoPackage路径")
    ap.add_argument("--center", required=True, help="中心点图层名")
    ap.add_argument("--target", required=True, help="目标对象点图层名")
    ap.add_argument("--radius_km", type=float, default=1.5)
    ap.add_argument("--out", required=True, help="输出圆图层名")
    ap.add_argument("--center_field", required=True, help="中心点名称字段")
    ap.add_argument("--center_town_field", default=None, help="中心点乡镇字段(可选)")
    ap.add_argument("--target_field", default=None, help="目标对象名称字段(可选, 缺省取首个字符串字段)")
    a = ap.parse_args()

    ds = ogr.Open(a.gpkg, 1)
    center_lyr = ds.GetLayerByName(a.center)
    target_lyr = ds.GetLayerByName(a.target)

    # 目标点
    tfield = a.target_field
    if not tfield:
        for i in range(target_lyr.GetLayerDefn().GetFieldCount()):
            if target_lyr.GetLayerDefn().GetFieldDefn(i).GetType() == ogr.OFTString:
                tfield = target_lyr.GetLayerDefn().GetFieldDefn(i).GetName(); break
    targets = []
    target_lyr.ResetReading()
    for f in target_lyr:
        g = f.GetGeometryRef()
        if g is None: continue
        p = g.GetPoint()
        if p and len(p) >= 2:
            name = (f.GetField(tfield) or "") if tfield else ""
            targets.append((str(name).strip(), p[0], p[1]))

    # 中心点
    centers = []
    center_lyr.ResetReading()
    for f in center_lyr:
        g = f.GetGeometryRef()
        if g is None: continue
        p = g.GetPoint()
        if p and len(p) >= 2:
            name = (f.GetField(a.center_field) or "").strip()
            town = (f.GetField(a.center_town_field) or "").strip() if a.center_town_field else ""
            centers.append((name, town, p[0], p[1]))

    if ds.GetLayerByName(a.out):
        ds.DeleteLayer(a.out)
    out_lyr = ds.CreateLayer(a.out, None, ogr.wkbPolygon)
    for nm, tp in [("中心名称", ogr.OFTString), ("乡镇", ogr.OFTString),
                   ("覆盖对象数", ogr.OFTInteger), ("对象清单", ogr.OFTString)]:
        fd = ogr.FieldDefn(nm, tp)
        if tp == ogr.OFTString: fd.SetWidth(254)
        out_lyr.CreateField(fd)

    radius = a.radius_km * 1000.0
    total = 0
    for name, town, clon, clat in centers:
        cnt = 0; names = []
        for tn, tl, ta in targets:
            if hav(clon, clat, tl, ta) <= radius:
                cnt += 1
                if tn: names.append(tn)
        ring = circle_ring(clat, clon, radius)
        lr = ogr.Geometry(ogr.wkbLinearRing)
        for pt in ring: lr.AddPoint(pt[0], pt[1])
        poly = ogr.Geometry(ogr.wkbPolygon); poly.AddGeometry(lr)
        feat = ogr.Feature(out_lyr.GetLayerDefn())
        feat.SetField("中心名称", name); feat.SetField("乡镇", town)
        feat.SetField("覆盖对象数", cnt); feat.SetField("对象清单", "、".join(names[:40]))
        feat.SetGeometry(poly); out_lyr.CreateFeature(feat)
        total += cnt
        print(f"{name}: 覆盖 {cnt}")

    print(f"总覆盖次数: {total}; 圆要素: {out_lyr.GetFeatureCount()}; 目标点: {len(targets)}")
    ds = None

if __name__ == "__main__":
    main()