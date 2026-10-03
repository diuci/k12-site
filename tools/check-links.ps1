param(
  [string]$Dist = '.\site\.vitepress\dist'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path $Dist).Path

# 站点内部可访问集合：目录 -> index.html，文件 -> 自身
$routes = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)

Get-ChildItem $root -Recurse -File -Filter *.html | ForEach-Object {
  $rel = $_.FullName.Substring($root.Length).TrimStart('\', '/') -replace '\\', '/'
  if ($rel -eq 'index.html') {
    [void]$routes.Add('/')
  } elseif ($rel -eq '404.html') {
    [void]$routes.Add('/404.html')
  } else {
    [void]$routes.Add('/' + $rel)
    [void]$routes.Add('/' + $rel.Substring(0, $rel.Length - 5))   # 目录形式
  }
}
Get-ChildItem $root -Recurse -File | Where-Object { $_.Extension -ne '.html' } | ForEach-Object {
  $rel = $_.FullName.Substring($root.Length).TrimStart('\', '/') -replace '\\', '/'
  [void]$routes.Add('/' + $rel)
}

$broken = New-Object 'System.Collections.Generic.List[string]'
$checked = 0

Get-ChildItem $root -Recurse -File -Filter *.html | ForEach-Object {
  $file = $_
  $relSrc = $file.FullName.Substring($root.Length).TrimStart('\', '/') -replace '\\', '/'
  $html = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)

  # href="..."（跳过外链、锚点、mailto、data:、协议相对）
  [regex]::Matches($html, 'href="([^"]*)"') | ForEach-Object {
    $href = $_.Groups[1].Value
    if ($href -eq '' -or $href.StartsWith('#') -or $href -match '^(https?:|mailto:|data:|//|javascript:)') { return }
    $checked++

    # 去掉 query 与 hash
    $p = ($href -split '[?#]')[0]
    if ($p -eq '') { return }
    if (-not $p.StartsWith('/')) { return }
    $p = [System.Uri]::UnescapeDataString($p)

    if ($routes.Contains($p)) { return }
    # /foo/ 与 /foo 等价
    if ($p.EndsWith('/') -and $routes.Contains($p.TrimEnd('/'))) { return }
    if (-not $p.EndsWith('/') -and $routes.Contains($p + '/')) { return }
    # 目录形式：/foo -> /foo/index.html
    if ($routes.Contains($p + '/index.html')) { return }

    $broken.Add("$relSrc -> $href")
  }
}

"scanned html : $((Get-ChildItem $root -Recurse -File -Filter *.html).Count)"
"internal href: $checked"
"broken       : $($broken.Count)"
$broken | Sort-Object -Unique | Select-Object -First 40