param(
  [string]$RepoPath = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
  [string]$OutDir = "",
  [int]$LogLines = 250
)

$ErrorActionPreference = "Stop"

if (-not $OutDir) {
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $OutDir = Join-Path $RepoPath "docs\AGENTS_COLLABORATION\phone_tests\$stamp"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$adb = Get-Command adb -ErrorAction SilentlyContinue
$localAdb = "C:\Users\saint\Documents\Codex\tools\android-platform-tools\platform-tools\adb.exe"
if (-not $adb -and (Test-Path -LiteralPath $localAdb)) {
  $adbPath = $localAdb
} elseif ($adb) {
  $adbPath = $adb.Source
} else {
  Write-Host "ADB introuvable dans le PATH Windows."
  Write-Host "Installer Android Platform Tools ou ajouter adb.exe au PATH."
  exit 2
}

$devicesPath = Join-Path $OutDir "adb_devices.txt"
$screenPath = Join-Path $OutDir "screen.png"
$logPath = Join-Path $OutDir "logcat_tail.txt"
$metaPath = Join-Path $OutDir "README.md"

& $adbPath devices | Set-Content -LiteralPath $devicesPath -Encoding UTF8
$devices = Get-Content -LiteralPath $devicesPath -Raw

if ($devices -notmatch "\tdevice") {
  Write-Host "Aucun telephone Android autorise en mode device."
  Write-Host "Verifier le cable USB, le mode developpeur et l'autorisation ADB sur le telephone."
  Write-Host "Resultat ecrit : $devicesPath"
  exit 3
}

& $adbPath exec-out screencap -p > $screenPath
& $adbPath logcat -d -t $LogLines | Set-Content -LiteralPath $logPath -Encoding UTF8

@"
# Capture telephone Luna

Date : $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Script : tools/agents/phone_snapshot.ps1

Fichiers :

- adb_devices.txt
- screen.png
- logcat_tail.txt

Regles :

- capture non destructive ;
- aucun clic ;
- aucune action sensible ;
- logs courts uniquement.
"@ | Set-Content -LiteralPath $metaPath -Encoding UTF8

Write-Host "Capture telephone terminee : $OutDir"
Write-Host "Screenshot : $screenPath"
Write-Host "Logcat : $logPath"
