#Requires -Version 5
<#
.SYNOPSIS
    Probe Windows pour luna-ui-orchestrator.

.DESCRIPTION
    Liste les fenêtres visibles (titre, processus, handle, bounds).
    Aucun clic, aucun changement de focus, aucune lecture de contenu sensible.

.PARAMETER OutputPath
    Chemin du fichier JSON de sortie. Si vide, écrit sur la sortie standard.
#>

param(
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

# Import des API Windows nécessaires (lecture seule)
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public class WindowProbe {
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
}
"@

$windows = New-Object System.Collections.Generic.List[System.Object]

$callback = [WindowProbe+EnumWindowsProc] {
    param([IntPtr]$hWnd, [IntPtr]$lParam)

    if (-not [WindowProbe]::IsWindowVisible($hWnd)) {
        return $true
    }

    $titleBuilder = New-Object System.Text.StringBuilder(256)
    [void][WindowProbe]::GetWindowText($hWnd, $titleBuilder, 256)
    $title = $titleBuilder.ToString()

    $processName = "unknown"
    $processId = 0
    [void][WindowProbe]::GetWindowThreadProcessId($hWnd, [ref]$processId)
    if ($processId -ne 0) {
        try {
            $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($process) {
                $processName = $process.ProcessName
            }
        } catch {
            $processName = "inaccessible"
        }
    }

    $rect = New-Object WindowProbe+RECT
    [void][WindowProbe]::GetWindowRect($hWnd, [ref]$rect)

    $windows.Add(@{
        title        = $title
        process_name = $processName
        handle       = $hWnd.ToInt64()
        bounds       = @{
            left   = $rect.Left
            top    = $rect.Top
            right  = $rect.Right
            bottom = $rect.Bottom
        }
    })

    return $true
}

[void][WindowProbe]::EnumWindows($callback, [IntPtr]::Zero)

$output = $windows | ConvertTo-Json -Depth 4

if ($OutputPath) {
    $output | Set-Content -Path $OutputPath -Encoding UTF8
    Write-Host "Probe Windows ecrit : $OutputPath"
} else {
    Write-Output $output
}
