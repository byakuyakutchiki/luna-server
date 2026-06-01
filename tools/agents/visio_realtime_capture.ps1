param(
  [int]$DurationSeconds = 35,
  [string]$Phone = "192.168.1.98:5555",
  [string]$Adb = "C:\Users\saint\Documents\Codex\tools\android-platform-tools\platform-tools\adb.exe",
  [string]$Node = "C:\Users\saint\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe",
  [string]$OutRoot = "docs\AGENTS_COLLABORATION\phone_tests"
)

$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outDir = Join-Path $repo (Join-Path $OutRoot "visio-realtime-$stamp")
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

function Save-Step($name, $content) {
  $path = Join-Path $outDir $name
  Set-Content -LiteralPath $path -Value $content -Encoding UTF8
}

Push-Location $repo
try {
  & $Adb connect $Phone | Tee-Object -FilePath (Join-Path $outDir "adb_connect.txt") | Out-Null
  & $Adb devices -l | Tee-Object -FilePath (Join-Path $outDir "adb_devices.txt") | Out-Null

  $unix = & $Adb shell cat /proc/net/unix
  Save-Step "proc_net_unix.txt" ($unix -join "`n")
  $remote = ($unix | Select-String -Pattern "webview_devtools_remote_\d+" | Select-Object -Last 1).Matches.Value
  if ($remote) {
    & $Adb forward tcp:9222 "localabstract:$remote" | Tee-Object -FilePath (Join-Path $outDir "adb_forward.txt") | Out-Null
    try {
      Invoke-RestMethod "http://127.0.0.1:9222/json" | ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath (Join-Path $outDir "webview_targets.json") -Encoding UTF8
    } catch {
      Save-Step "webview_targets_error.txt" $_.Exception.Message
    }
  } else {
    Save-Step "adb_forward.txt" "No webview_devtools_remote socket found."
  }

  $consoleJob = $null
  if ($remote) {
    $consoleOut = Join-Path $outDir "webview_console_visio.jsonl"
    $consoleScript = Join-Path $repo "tools\agents\webview_console_capture.mjs"
    $consoleJob = Start-Job -ScriptBlock {
      param($node, $durationMs, $out, $script)
      & $node $script $durationMs $out
    } -ArgumentList $Node, (($DurationSeconds + 3) * 1000), $consoleOut, $consoleScript
  }

  $logcatJob = Start-Job -ScriptBlock {
    param($adb, $seconds, $out)
    & $adb logcat -c | Out-Null
    $p = Start-Process -FilePath $adb -ArgumentList @("logcat", "-v", "time") -NoNewWindow -RedirectStandardOutput $out -PassThru
    Start-Sleep -Seconds $seconds
    if (!$p.HasExited) { Stop-Process -Id $p.Id -Force }
  } -ArgumentList $Adb, $DurationSeconds, (Join-Path $outDir "logcat_visio.txt")

  & $Adb shell screenrecord --time-limit $DurationSeconds /sdcard/luna_visio_test.mp4
  & $Adb pull /sdcard/luna_visio_test.mp4 (Join-Path $outDir "luna_visio_test.mp4") | Out-Null
  & $Adb exec-out screencap -p > (Join-Path $outDir "after_visio.png")

  Wait-Job $logcatJob -Timeout 5 | Out-Null
  Receive-Job $logcatJob -ErrorAction SilentlyContinue | Out-Null
  Remove-Job $logcatJob -Force -ErrorAction SilentlyContinue

  if ($consoleJob) {
    Wait-Job $consoleJob -Timeout 5 | Out-Null
    Receive-Job $consoleJob -ErrorAction SilentlyContinue | Out-Null
    Remove-Job $consoleJob -Force -ErrorAction SilentlyContinue
  }

  Save-Step "README.txt" @"
Visio realtime capture
DurationSeconds=$DurationSeconds
Phone=$Phone
Files:
- luna_visio_test.mp4 : video ecran telephone
- after_visio.png : capture finale
- webview_console_visio.jsonl : console JS WebView si disponible
- logcat_visio.txt : logcat Android pendant le test
- webview_targets.json : cibles DevTools detectees
"@

  Write-Host "Capture terminee : $outDir"
} finally {
  Pop-Location
}
