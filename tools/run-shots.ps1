param(
  [string]$Out = '.\_shots'
)

# 两站移动端底部标签栏对照截图：验证视觉一致性与各自的菜单项差异。
# --blink-settings 只影响首帧系统偏好；data-theme 落地后由 CSS 接管。
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$outPath = (Resolve-Path $Out).Path
$tmp = Join-Path $env:TEMP ('tab_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

Add-Type -AssemblyName System.Drawing

$pages = @(
  @{ n = 'www-mob-light'; u = 'http://127.0.0.1:5191/index.html'; sch = '1'; w = 414; h = 860 },
  @{ n = 'www-mob-dark';  u = 'http://127.0.0.1:5191/index.html'; sch = '0'; w = 414; h = 860 },
  @{ n = 'www-desk';      u = 'http://127.0.0.1:5191/index.html'; sch = '1'; w = 1440; h = 900 },
  @{ n = 'k12-mob-light'; u = 'http://127.0.0.1:5192/';sch = '1'; w = 414; h = 860 },
  @{ n = 'k12-mob-dark';  u = 'http://127.0.0.1:5192/';           sch = '0'; w = 414; h = 860 }
)

function Run-Chrome([string[]]$a) {
  $p = Start-Process -FilePath $chrome -ArgumentList $a -PassThru -WindowStyle Hidden `
       -RedirectStandardError (Join-Path $tmp 'e.txt') -RedirectStandardOutput (Join-Path $tmp 'o.txt')
  $p.WaitForExit()
}

foreach ($p in $pages) {
  $shot = Join-Path $outPath ($p.n + '.png')
  if (Test-Path $shot) { Remove-Item $shot -Force }

  Run-Chrome @(
    '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
    '--no-first-run', '--disable-sync', '--disable-extensions', '--no-proxy-server',
    '--force-color-profile=srgb',
    ('--blink-settings=preferredColorScheme=' + $p.sch),
    ('--user-data-dir=' + (Join-Path $tmp $p.n)),
    ('--window-size=' + $p.w + ',' + $p.h),
    '--virtual-time-budget=20000',
    ('--screenshot=' + $shot),
    $p.u
  )

  if (-not (Test-Path $shot)) { Write-Output ('MISS  ' + $p.n); continue }

  $bmp = [System.Drawing.Bitmap]::FromFile($shot)
  $sr = 0; $sg = 0; $sb = 0; $n2 = 0
  for ($y = 300; $y -lt 340; $y++) {
    for ($x = 6; $x -lt 46; $x++) {
      $c = $bmp.GetPixel($x, $y)
      $sr += $c.R; $sg += $c.G; $sb += $c.B; $n2++
    }
  }
  $bmp.Dispose()
  $r = [int]($sr / $n2); $g = [int]($sg / $n2); $b = [int]($sb / $n2)
  $lum = [int](0.299 * $r + 0.587 * $g + 0.114 * $b)
  Write-Output ('{0,-16} rgb({1,3},{2,3},{3,3}) lum={4,3} {5}' -f `
    $p.n, $r, $g, $b, $lum, $(if ($lum -lt 90) { 'DARK' } else { 'LIGHT' }))
}

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue