#Requires -Version 7
<#
.SYNOPSIS
    Runner local GitHub pour agents Luna — boucle de coordination sans serveur.

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
$QueueFile      = Join-Path $RepoPath "docs" "AGENTS_COLLABORATION" "QUEUE.md"
$ChannelFile    = Join-Path $RepoPath "docs" "AGENTS_COLLABORATION" "AGENT_CHANNEL.md"
$GitExe         = (Get-Command git -ErrorAction SilentlyContinue)?.Source
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
    $content = Get-Content -Raw $QueueFile
    $sectionFrom = "## $from"
    $sectionTo   = "## $to"

    # Regex pour capturer le bloc TASK complet
    $pattern = "(?ms)(### $taskId\r?\n(?:- .*\r?\n)+)"
    $match = [regex]::Match($content, $pattern)
    if (-not $match.Success) {
        Log "Tache $taskId non trouvee dans $from"
        return
    }
    $bloc = $match.Groups[1].Value
    $content = $content -replace [regex]::Escape($bloc), ""
    # Nettoyage des lignes vides residuelles
    $content = $content -replace "(?m)^\s*\r?\n{2,}", "`n"

    # Ajout dans la section cible
    $insertMarker = "$sectionTo\n"
    $content = $content -replace [regex]::Escape($insertMarker), ($insertMarker + $bloc + "`n")

    Set-Content -Path $QueueFile -Value $content -Encoding UTF8 -NoNewline
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

            GitPush "agent($Agent): runner cycle — tache $id detectee"
        }
    }
    catch {
        Log "ERREUR : $_"
        if ($DryRun) { break }
    }

    Log "Attente ${IntervalSeconds}s... (Ctrl+C pour arreter)"
    Start-Sleep -Seconds $IntervalSeconds
}
