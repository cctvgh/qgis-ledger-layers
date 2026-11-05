# 底图瓦片主机连通性探测（443 端口）
# 用途：向用户推荐 QGIS XYZ 底图前，先实测内网防火墙是否放行该主机
# 运行：powershell -ExecutionPolicy Bypass -File test_basemap_connectivity.ps1

$tileHosts = @(
    'server.arcgisonline.com',    # Esri World Imagery（免key, WGS84, 首选）
    'services.arcgisonline.com',  # Esri 老节点（常不通）
    'tile.openstreetmap.org',     # OSM（内网常不通）
    't0.tianditu.gov.cn',         # 天地图新节点（需key）
    'webmap0.tianditu.gov.cn',    # 天地图老节点（常不通）
    'webrd01.is.autonavi.com'     # 高德（GCJ-02 会偏移，仅应急）
)

foreach ($h in $tileHosts) {
    $r = Test-NetConnection -ComputerName $h -Port 443 -WarningAction SilentlyContinue -InformationLevel Quiet
    if ($r) { Write-Output "[OK  ] $h" } else { Write-Output "[FAIL] $h" }
}

Write-Output ""
Write-Output "推荐：server.arcgisonline.com 通 => 用 Esri World Imagery（免key/WGS84/URL顺序{z}/{y}/{x}）"
Write-Output "提醒：高德/百度为 GCJ-02 火星坐标，直接叠加 WGS84 工参会整体偏移"
