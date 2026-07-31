#Requires -Version 5.1
<#
.SYNOPSIS
    Probe Windows de capture d’écran lecture seule pour l’UI Orchestrator.

.DESCRIPTION
    Ce script NE CLIQUE PAS, NE DÉPLACE PAS la souris, NE CHANGE PAS le focus
    et N’ENVOIE AUCUNE TOUCHE. Il se contente de :
      - lister les fenêtres visibles (mode -ListOnly) ;
      - capturer la fenêtre active au moment de l’appel et sauvegarder le
        screenshot dans AGENT_SHARED\ui_orchestrator\screenshots\.

    Sortie : un objet JSON sur stdout avec les métadonnées et le chemin de
    l’image capturée.
#>

param(
    [string]$MissionId = "VISION-PROBE-001",
    [string]$OutputDir = "C:\Users\saint\Documents\Codex\AGENT_SHARED\ui_orchestrator\screenshots",
    [switch]$ListOnly
)

# -----------------------------------------------------------------------------
# Imports .NET
# -----------------------------------------------------------------------------
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

# -----------------------------------------------------------------------------
# P/Invoke pour Win32 : fenêtres visibles, foreground window, bounds, PID
# -----------------------------------------------------------------------------
$code = @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public class WinApi {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", SetLastError = true)]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern int GetWindowTextLength(IntPtr hWnd);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
}
"@

Add-Type -TypeDefinition $code -Language CSharp

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
function Get-WindowTitle($hWnd) {
    $len = [WinApi]::GetWindowTextLength($hWnd)
    if ($len -eq 0) { return "" }
    $sb = New-Object System.Text.StringBuilder($len + 1)
    [void][WinApi]::GetWindowText($hWnd, $sb, $sb.Capacity)
    return $sb.ToString()
}

function Get-WindowBounds($hWnd) {
    $rect = New-Object WinApi+RECT
    if ([WinApi]::GetWindowRect($hWnd, [ref]$rect)) {
        return @{
            x      = $rect.Left
            y      = $rect.Top
            width  = $rect.Right - $rect.Left
            height = $rect.Bottom - $rect.Top
        }
    }
    return $null
}

function Get-WindowProcessInfo($hWnd) {
    $processId = 0
    [void][WinApi]::GetWindowThreadProcessId($hWnd, [ref]$processId)
    try {
        $proc = Get-Process -Id $processId -ErrorAction Stop
        return @{
            processId   = $proc.Id
            processName = $proc.ProcessName
        }
    }
    catch {
        return @{
            processId   = $processId
            processName = "unknown"
        }
    }
}

function Get-VisibleWindows() {
    $windows = New-Object System.Collections.ArrayList
    $callback = {
        param([IntPtr]$hWnd, [IntPtr]$lParam)
        if ([WinApi]::IsWindowVisible($hWnd)) {
            $title = Get-WindowTitle -hWnd $hWnd
            $bounds = Get-WindowBounds -hWnd $hWnd
            $proc = Get-WindowProcessInfo -hWnd $hWnd
            [void]$windows.Add(@{
                handle    = $hWnd.ToInt64()
                title     = $title
                process   = $proc.processName
                processId = $proc.processId
                bounds    = $bounds
            })
        }
        return $true
    }
    $proc = [WinApi+EnumWindowsProc]$callback
    [void][WinApi]::EnumWindows($proc, [IntPtr]::Zero)
    return $windows
}

function Capture-ActiveWindow($hWnd, $outputPath) {
    $bounds = Get-WindowBounds -hWnd $hWnd
    if (-not $bounds -or $bounds.width -le 0 -or $bounds.height -le 0) {
        throw "Impossible de déterminer les dimensions de la fenêtre active."
    }

    $bitmap = New-Object System.Drawing.Bitmap($bounds.width, $bounds.height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen(
            [System.Drawing.Point]::new($bounds.x, $bounds.y),
            [System.Drawing.Point]::new(0, 0),
            [System.Drawing.Size]::new($bounds.width, $bounds.height)
        )
    }
    finally {
        $graphics.Dispose()
    }

    $bitmap.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $bitmap.Dispose()
    return $outputPath
}

# -----------------------------------------------------------------------------
# Exécution principale
# -----------------------------------------------------------------------------
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

if ($ListOnly) {
    $windows = Get-VisibleWindows
    $result = @{
        missionId      = $MissionId
        mode           = "list_only"
        timestamp      = (Get-Date -Format "o")
        windowCount    = $windows.Count
        windows        = $windows
        screenshotPath = $null
        realClick      = $false
        focusChanged   = $false
    }
    Write-Output ($result | ConvertTo-Json -Depth 5)
    exit 0
}

$fgHwnd = [WinApi]::GetForegroundWindow()
$title = Get-WindowTitle -hWnd $fgHwnd
$proc = Get-WindowProcessInfo -hWnd $fgHwnd
$bounds = Get-WindowBounds -hWnd $fgHwnd

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$filename = "capture_${MissionId}_${timestamp}.png"
$outputPath = Join-Path $OutputDir $filename

try {
    $savedPath = Capture-ActiveWindow -hWnd $fgHwnd -outputPath $outputPath
    $result = @{
        missionId      = $MissionId
        mode           = "capture_active_window"
        timestamp      = (Get-Date -Format "o")
        window         = @{
            handle    = $fgHwnd.ToInt64()
            title     = $title
            process   = $proc.processName
            processId = $proc.processId
            bounds    = $bounds
        }
        screenshotPath = $savedPath
        realClick      = $false
        focusChanged   = $false
    }
    Write-Output ($result | ConvertTo-Json -Depth 5)
    exit 0
}
catch {
    $result = @{
        missionId      = $MissionId
        mode           = "capture_active_window"
        timestamp      = (Get-Date -Format "o")
        error          = $_.Exception.Message
        screenshotPath = $null
        realClick      = $false
        focusChanged   = $false
    }
    Write-Output ($result | ConvertTo-Json -Depth 5)
    exit 1
}
