param(
  [string]$Url,
  [int]$WaitMs = 40000
)

# 用 Chrome headless 打开探针页，把 <pre id="out"> 的内容抓出来。
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$outDir = Join-Path $env:TEMP ('dcprobe_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$dump = Join-Path $outDir 'dump.html'

$args = @(
  '--headless=new',
  '--disable-gpu',
  '--no-sandbox',
  '--hide-scrollbars',
  '--no-first-run',
  '--disable-sync',
  '--disable-extensions',
  "--user-data-dir=$(Join-Path $outDir 'p')",
  "--virtual-time-budget=$WaitMs",
  '--dump-dom',
  $Url
)

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $chrome
$psi.Arguments = ($args -join ' ')
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$proc = [System.Diagnostics.Process]::Start($psi)
$html = $proc.StandardOutput.ReadToEnd()
$proc.WaitForExit()

[System.IO.File]::WriteAllText($dump, $html, [System.Text.Encoding]::UTF8)

$m = [regex]::Match($html, '(?s)<pre id="out">(.*?)</pre>')
if (-not $m.Success) {
  Write-Output 'NO OUTPUT CAPTURED'
  Write-Output ($html.Substring(0, [Math]::Min(800, $html.Length)))
  exit 1
}

$txt = $m.Groups[1].Value
$txt = $txt -replace '&lt;', '<' -replace '&gt;', '>' -replace '&amp;', '&' -replace '&quot;', '"'
Write-Output $txt

Remove-Item -Recurse -Force $outDir -ErrorAction SilentlyContinue