param(
  [string]$Port = '5184',
  [string]$Out  = '.\_shots'
)

# 双主题截图 + 像素级校验。
# VitePress 会跟随系统，用 --blink-settings=preferredColorScheme 固定首帧主题；
# data-theme 写入后由 CSS 接管，localStorage 不会被 headless 持久化，无需播种。
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$dist = (Resolve-Path '.\site\.vitepress\dist').Path
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$outPath = (Resolve-Path $Out).Path
$tmp = Join-Path $env:TEMP ('k12shot_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

Add-Type -AssemblyName System.Drawing

$pages = @(
  @{ n = 'home';     u = '/index.html';                           w = 1440; h = 1000 },
  @{ n = 'home-mob'; u = '/index.html';                           w = 414;  h = 900  },
  @{ n = 'poem';     u = '/poems/小学/三年级上册/望天门山.html'; w = 1440; h = 1000 },
  @{ n = 'print';    u = '/print.html';                           w = 1440; h = 1000 }
)

function Run-Chrome([string[]]$a) {
  $p = Start-Process -FilePath $chrome -ArgumentList $a -PassThru -WindowStyle Hidden `
       -RedirectStandardError (Join-Path $tmp 'e.txt') -RedirectStandardOutput (Join-Path $tmp 'o.txt')
  $p.WaitForExit()
}

foreach ($p in $pages) {
  foreach ($s in @(@{ n = 'light'; sch = '1' }, @{ n = 'dark'; sch = '0' })) {
    $shot = Join-Path $outPath ('{0}-{1}.png' -f $p.n, $s.n)
    if (Test-Path $shot) { Remove-Item $shot -Force }

    Run-Chrome @(
      '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
      '--no-first-run', '--disable-sync', '--disable-extensions',
      '--force-color-profile=srgb',
      ('--blink-settings=preferredColorScheme=' + $s.sch),
      ('--user-data-dir=' + (Join-Path $tmp ($p.n + '_' + $s.n))),
      ('--window-size=' + $p.w + ',' + $p.h),
      '--virtual-time-budget=15000',
      ('--screenshot=' + $shot),
      ('http://127.0.0.1:' + $Port + $p.u)
    )

    if (-not (Test-Path $shot)) { Write-Output ('MISS  ' + $p.n + '-' + $s.n); continue }

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
    Write-Output ('{0,-10} {1,-5} rgb({2,3},{3,3},{4,3}) lum={5,3} {6}' -f `
      $p.n, $s.n, $r, $g, $b, $lum, $(if ($lum -lt 90) { 'DARK' } else { 'LIGHT' }))
  }
}

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue