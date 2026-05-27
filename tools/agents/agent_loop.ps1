#Requires -Version 5
<#
.SYNOPSIS
    Runner local GitHub pour agents Luna - boucle de coordination sans serveur.

.DESCRIPTION
    Lit la queue dans docs/AGENTS_COLLABORATION/QUEUE.md,
    execute les taches autorisees pour l'agent courant,
    ecrit les resultats, commit/push, attend, recommence.

.PARAMETER Agent
    Nom de l'agent : Kimi | DeepSeek | Codex | Claude

.PARAMETER RepoPath
    Chemin absolu du depot Luna. Defaut : repertoire parent du script.

.PARAMETER IntervalSeconds
    Temps d'attente entre deux cycles. Defaut : 180 (3 min).

.PARAMETER DryRun
    Mode simulation : affiche ce qu'il ferait sans commit/push.

.EXAMPLE
    .\agent_loop.ps1 -Agent Kimi -IntervalSeconds 120
    .\agent_loop.ps1 -Agent DeepSeek -DryRun
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Kimi", "DeepSeek", "Codex", "Claude")]
    [string]$Agent,

    [string]$RepoPath = (Join-Path $PSScriptRoot ".." ".." | Resolve-Path).Path,

    [int]$IntervalSeconds = 180,

    [switch]$DryRun
)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
$ErrorActionPreference = "Stop"
$DocsDir        = Join-Path $RepoPath "docs"
$CollabDir      = Join-Path $DocsDir "AGENTS_COLLABORATION"
$QueueFile      = Join-Path $CollabDir "QUEUE.md"
$ChannelFile    = Join-Path $CollabDir "AGENT_CHANNEL.md"
$GitCommand     = Get-Command git -ErrorAction SilentlyContinue
$GitExe         = if ($GitCommand) { $GitCommand.Source } else { $null }
$StartTime      = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

if (-not $GitExe) { throw "git introuvable. Installez Git et ajoutez-le au PATH." }

# Niveaux autorises par agent
$NiveauxAutorises = @{
    "Kimi"      = @(0, 1)
    "DeepSeek"  = @(0)
    "Codex"     = @(0, 1)
    "Claude"    = @(0, 1, 2)  # 3 = validation Ludovic obligatoire quand meme
}

# ---------------------------------------------------------------------------
# FONCTIONS
# ---------------------------------------------------------------------------

function Log([string]$msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] [$Agent] $msg"
}

function GitPull {
    Log "git pull..."
    & $GitExe -C $RepoPath pull --ff-only 2>&1 | ForEach-Object { Log "  $_" }
}

function GitPush([string]$msg) {
    if ($DryRun) {
        Log "[DRY-RUN] git add + commit + push omis"
        return
    }
    Log "git add + commit + push..."
    & $GitExe -C $RepoPath add -A 2>&1 | Out-Null
    & $GitExe -C $RepoPath commit -m "$msg" 2>&1 | ForEach-Object { Log "  $_" }
    & $GitExe -C $RepoPath push origin HEAD 2>&1 | ForEach-Object { Log "  $_" }
}

function LireQueue {
    if (-not (Test-Path $QueueFile)) {
        Log "QUEUE.md introuvable. Arret."
        exit 1
    }
    $content = Get-Content -Raw $QueueFile
    # Extraction simple des blocs TASK
    $tasks = @()
    $regex = [regex]::new('(?m)^### (TASK-[\w-]+)\s*$\n((?:- .*\n)+)', [System.Text.RegularExpressions.RegexOptions]::Multiline)
    $matches = $regex.Matches($content)
    foreach ($m in $matches) {
        $id = $m.Groups[1].Value
        $lines = $m.Groups[2].Value -split "\n" | Where-Object { $_ -match '^- ' } | ForEach-Object { $_.Substring(2).Trim() }
        $task = @{ Id = $id }
        foreach ($line in $lines) {
            if ($line -match '^([^:]+)\s*:\s*(.*)$') {
                $task[$Matches[1].Trim()] = $Matches[2].Trim()
            }
        }
        $tasks += $task
    }
    return $tasks
}

function FiltrerTaches([array]$tasks) {
    $autorises = $NiveauxAutorises[$Agent]
    return $tasks | Where-Object {
        $_.Statut -eq "open" -and
        ($_.Agent -split ",").Trim() -contains $Agent -and
        [int]$_.Niveau -in $autorises
    }
}

function EcrireChannel([string]$taskId, [string]$type, [string]$resume) {
    $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = @"

---
Agent : $Agent
Heure : $now
Tache : $taskId
Type : $type
Resume : $resume
"@
    Add-Content -Path $ChannelFile -Value $entry -Encoding UTF8
    Log "Entree ecrite dans AGENT_CHANNEL.md"
}

function DeplacerTache([string]$taskId, [string]$from, [string]$to) {
    $lines = @(Get-Content $QueueFile)
    $sectionFromMarker = "## $from"
    $sectionToMarker   = "## $to"
    $taskMarker        = "### $taskId"

    $inSectionFrom = $false
    $inTask        = $false
    $taskLines     = @()
    $resultLines   = @()
    $found         = $false

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]

        if ($line -eq $sectionFromMarker) {
            $inSectionFrom = $true
            $resultLines += $line
            continue
        }

        if ($line -match '^## ' -and $line -ne $sectionFromMarker) {
            $inSectionFrom = $false
            if ($inTask) { $inTask = $false }
        }

        if ($inSectionFrom -and $line -eq $taskMarker) {
            $inTask = $true
            $found  = $true
            $taskLines += $line
            continue
        }

        if ($inTask) {
            if ($line -match '^### ' -or $line -match '^## ') {
                $inTask = $false
                $inSectionFrom = $false
                $resultLines += $line
            } else {
                $taskLines += $line
            }
        } else {
            $resultLines += $line
        }
    }

    if (-not $found) {
        Log "Tache $taskId non trouvee dans $from"
        return
    }

    # Mise a jour du statut
    $newStatus = $to.ToLowerInvariant().Replace(" ", "_")
    for ($i = 0; $i -lt $taskLines.Count; $i++) {
        if ($taskLines[$i] -match '^- Statut\s*:\s*.*$') {
            $taskLines[$i] = "- Statut : $newStatus"
        }
    }

    # Supprimer lignes vides en fin de bloc
    while ($taskLines.Count -gt 0 -and [string]::IsNullOrWhiteSpace($taskLines[$taskLines.Count - 1])) {
        $taskLines = $taskLines[0..($taskLines.Count - 2)]
    }

    # Inserer dans la section cible
    $newResult = @()
    for ($i = 0; $i -lt $resultLines.Count; $i++) {
        $line = $resultLines[$i]
        $newResult += $line

        if ($line -eq $sectionToMarker) {
            $newResult += ""
            $newResult += $taskLines
        }
    }

    # Garde-fou : ne pas ecrire un fichier vide ou trop court
    if ($newResult.Count -lt 5) {
        Log "ERREUR CRITIQUE : DeplacerTache aurait vide QUEUE.md. Operation annulee."
        return
    }

    Set-Content -Path $QueueFile -Value $newResult -Encoding UTF8
    Log "Tache $taskId deplacee : $from -> $to"
}

# ---------------------------------------------------------------------------
# BOUCLE PRINCIPALE
# ---------------------------------------------------------------------------

Log "Runner Luna demarre"
Log "Agent=$Agent | Repo=$RepoPath | Interval=${IntervalSeconds}s | DryRun=$DryRun"
Log "Niveaux autorises : $($NiveauxAutorises[$Agent] -join ', ')"

while ($true) {
    try {
        GitPull
        $tasks = LireQueue
        $candidates = FiltrerTaches $tasks

        if (-not $candidates) {
            Log "Aucune tache ouverte pour $Agent (niveaux autorises)."
        } else {
            $task = $candidates | Select-Object -First 1
            $id = $task.Id
            $niveau = $task.Niveau
            $tacheDesc = $task.Tache

            Log "Tache detectee : $id (niveau $niveau)"
            Log "Description : $tacheDesc"

            if ($DryRun) {
                Log "[DRY-RUN] Traitement simule. Pas d'ecriture."
                EcrireChannel $id "dry-run" "Simulation traitee pour $id"
            } else {
                # Deplacer en IN PROGRESS
                DeplacerTache $id "TODO" "IN PROGRESS"

                # TODO : l'agent execute ici son travail reel (audit, correction, test)
                # Pour V1, le script ne pilote pas l'IA automatiquement.
                # Il prepare le contexte et attend l'action manuelle ou semi-auto.
                Log ">>> ACTION REQUISE : executez votre tache localement, puis relancez le runner."
                Log ">>> Appuyez sur Ctrl+C pour arreter, faites votre travail, puis relancez."

                EcrireChannel $id "runner-detecte" "Tache $id detectee et prete. L'agent doit executer son audit/correction localement."

                # Deplacer en DONE (a deplacer manuellement si la tache n'est pas finie)
                # DeplacerTache $id "IN PROGRESS" "DONE"
            }

            GitPush "agent($Agent): runner cycle - tache $id detectee"
        }
    }
    catch {
        Log "ERREUR : $_"
        if ($DryRun) { break }
    }

    Log "Attente ${IntervalSeconds}s... (Ctrl+C pour arreter)"
    Start-Sleep -Seconds $IntervalSeconds
}
