param(
  [string]$Port = '5186',
  [string]$Out  = '.\_shots'
)

# 双主题 + 桌面/移动截图，覆盖首页、册次页、课文页。
# --blink-settings 只影响首帧系统偏好；data-theme 落地后由 CSS 接管。
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$outPath = (Resolve-Path $Out).Path
$tmp = Join-Path $env:TEMP ('k12s_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

Add-Type -AssemblyName System.Drawing

function Enc([string]$p) { return ([uri]::EscapeDataString($p)).Replace('%2F', '/') }

$pages = @(
  @{ n = 'home-desk-light'; u = '/';                sch = '1'; w = 1440; h = 1000 },
  @{ n = 'home-desk-dark';  u = '/';                sch = '0'; w = 1440; h = 1000 },
  @{ n = 'home-mob-light';  u = '/';                sch = '1'; w = 414;  h = 860  },
  @{ n = 'home-mob-dark';   u = '/';                sch = '0'; w = 414;  h = 860  },
  @{ n = 'vol-desk-light';  u = '/vol/小学/一年级上册'; sch = '1'; w = 1440; h = 1000 },
  @{ n = 'vol-mob-light';   u = '/vol/小学/一年级上册'; sch = '1'; w = 414;  h = 860  },
  @{ n = 'poem-desk-light'; u = '/poems/小学/三年级上册/望天门山'; sch = '1'; w = 1440; h = 1000 },
  @{ n = 'poem-mob-light';  u = '/poems/小学/三年级上册/望天门山'; sch = '1'; w = 414;  h = 860  }
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
    '--no-first-run', '--disable-sync', '--disable-extensions',
    '--force-color-profile=srgb',
    ('--blink-settings=preferredColorScheme=' + $p.sch),
    ('--user-data-dir=' + (Join-Path $tmp $p.n)),
    ('--window-size=' + $p.w + ',' + $p.h),
    '--virtual-time-budget=15000',
    ('--screenshot=' + $shot),
    ('http://127.0.0.1:' + $Port + (Enc $p.u))
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
  Write-Output ('{0,-18} rgb({1,3},{2,3},{3,3}) lum={4,3} {5}' -f `
    $p.n, $r, $g, $b, $lum, $(if ($lum -lt 90) { 'DARK' } else { 'LIGHT' }))
}

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue