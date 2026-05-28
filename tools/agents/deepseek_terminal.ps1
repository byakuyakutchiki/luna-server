#Requires -Version 5
<#
.SYNOPSIS
    Terminal visible DeepSeek pour Luna.

.DESCRIPTION
    Lit la queue agents, appelle DeepSeek via la cle Continue locale,
    et affiche une reponse dans le terminal. Par defaut, ne modifie aucun fichier.

.EXAMPLE
    .\tools\agents\deepseek_terminal.ps1
    .\tools\agents\deepseek_terminal.ps1 -TaskId TASK-011-DEEPSEEK-AUDIT-CODE
#>

param(
    [string]$RepoPath = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$TaskId = "",
    [switch]$WriteChannel
)

$ErrorActionPreference = "Stop"

function Say($text, $color = "Gray") {
    Write-Host $text -ForegroundColor $color
}

function Read-DeepSeekKey {
    $envFile = Join-Path $env:USERPROFILE ".continue\.env"
    if (-not (Test-Path $envFile)) {
        throw "Fichier $envFile introuvable. Continue/DeepSeek n'est pas configure."
    }
    $line = Get-Content $envFile | Where-Object { $_ -match '^DEEPSEEK_API_KEY=' } | Select-Object -First 1
    if (-not $line) {
        throw "DEEPSEEK_API_KEY introuvable dans $envFile."
    }
    return ($line -replace '^DEEPSEEK_API_KEY=', '').Trim()
}

function Get-TaskBlock($queueText, $taskId) {
    if (-not $taskId) { return "" }
    $pattern = "(?m)^### $([regex]::Escape($taskId))\r?\n(?:- .*(?:\r?\n|$))+"
    $match = [regex]::Match($queueText, $pattern)
    if ($match.Success) { return $match.Value.Trim() }
    return ""
}

$queuePath = Join-Path $RepoPath "docs\AGENTS_COLLABORATION\QUEUE.md"
$channelPath = Join-Path $RepoPath "docs\AGENTS_COLLABORATION\AGENT_CHANNEL.md"
$codexAuditPath = Join-Path $RepoPath "docs\AGENTS_COLLABORATION\agents\CODEX_AUDIT_011_P0_CONFIRMATIONS.md"

Say ""
Say "=== DeepSeek Terminal Luna ===" "Cyan"
Say "Repo : $RepoPath"
Say "Mode : audit visible, aucune action sensible, aucun deploiement." "Yellow"
Say ""

if (-not (Test-Path $queuePath)) { throw "QUEUE.md introuvable : $queuePath" }

$queueText = Get-Content -Raw $queuePath
$taskBlock = Get-TaskBlock $queueText $TaskId
if (-not $taskBlock) {
    $taskBlock = "Aucune tache precise fournie. Lire QUEUE.md et proposer la prochaine action DeepSeek niveau 0."
}

$codexAudit = ""
if (Test-Path $codexAuditPath) {
    $codexAudit = Get-Content -Raw $codexAuditPath
}

$prompt = @"
Tu es DeepSeek, agent technique Luna visible dans le terminal VS Code.

Contraintes absolues :
- Niveau 0 uniquement.
- Ne pas deployer.
- Ne pas envoyer SMS/email/appel/paiement/reservation.
- Ne pas modifier secrets, Cloud, base de donnees ou donnees utilisateur.
- Reponse courte, actionnable, en francais.

Queue actuelle :
$taskBlock

Audit Codex disponible :
$codexAudit

Reponds au format :
Agent :
Objectif :
Type :
Resume : 5 lignes max
Fichier concerne :
Risque :
Decision Ludovic requise : oui/non
Action proposee :

Puis indique exactement ce que Kimi ou Codex doit faire ensuite.
"@

$apiKey = Read-DeepSeekKey
$body = @{
    model = "deepseek-chat"
    messages = @(
        @{ role = "system"; content = "Tu es un auditeur technique senior, sobre et precis." },
        @{ role = "user"; content = $prompt }
    )
    temperature = 0.1
    max_tokens = 1200
} | ConvertTo-Json -Depth 6 -Compress

$headers = @{
    Authorization = "Bearer $apiKey"
    "Content-Type" = "application/json"
}

Say "Appel DeepSeek API..." "Cyan"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
$response = Invoke-RestMethod -Uri "https://api.deepseek.com/chat/completions" -Method Post -Headers $headers -Body $bytes -TimeoutSec 90
$answer = $response.choices[0].message.content

Say ""
Say "=== Reponse DeepSeek ===" "Green"
Write-Host $answer
Say ""

if ($WriteChannel) {
    $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = @"

---
Agent : DeepSeek
Heure : $now
Tache : $TaskId
Type : terminal
Resume : DeepSeek execute depuis terminal visible VS Code. Voir sortie terminal pour detail.
Fichier concerne : $channelPath
Risque : faible, coordination uniquement
Decision Ludovic requise : non
Action proposee : suivre la recommandation DeepSeek affichee dans le terminal.
"@
    Add-Content -Path $channelPath -Value $entry -Encoding UTF8
    Say "Entree courte ajoutee a AGENT_CHANNEL.md" "Green"
}

Say "Termine. Aucun deploiement, aucune action sensible." "Yellow"
