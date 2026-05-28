#!/usr/bin/env bash
# Runner local GitHub pour agents Luna — boucle de coordination sans serveur.
# Équivalent bash de agent_loop.ps1 pour Linux/macOS.
#
# Usage:
#   ./agent_loop.sh --agent Kimi --interval 120
#   ./agent_loop.sh --agent DeepSeek --dry-run
#   ./agent_loop.sh --agent Codex --repo-path /home/moi/luna-server

set -euo pipefail

# ---------------------------------------------------------------------------
# ARGS
# ---------------------------------------------------------------------------
AGENT=""
REPO_PATH=""
INTERVAL_SECONDS=180
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent|-a)       AGENT="$2"; shift 2 ;;
    --repo-path|-r)   REPO_PATH="$2"; shift 2 ;;
    --interval|-i)    INTERVAL_SECONDS="$2"; shift 2 ;;
    --dry-run|-d)     DRY_RUN=true; shift ;;
    *) echo "Option inconnue : $1"; exit 1 ;;
  esac
done

VALID_AGENTS=("Kimi" "DeepSeek" "Codex" "Claude")
if [[ -z "$AGENT" ]]; then
  echo "Erreur : --agent requis (Kimi | DeepSeek | Codex | Claude)"
  exit 1
fi
found=false
for a in "${VALID_AGENTS[@]}"; do
  [[ "$a" == "$AGENT" ]] && found=true
done
if [[ "$found" == false ]]; then
  echo "Erreur : agent '$AGENT' invalide."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$REPO_PATH" ]]; then
  REPO_PATH="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

QUEUE_FILE="$REPO_PATH/docs/AGENTS_COLLABORATION/QUEUE.md"
CHANNEL_FILE="$REPO_PATH/docs/AGENTS_COLLABORATION/AGENT_CHANNEL.md"

if ! command -v git &>/dev/null; then
  echo "Erreur : git introuvable. Installez Git."
  exit 1
fi

# ---------------------------------------------------------------------------
# NIVEAUX AUTORISES
# ---------------------------------------------------------------------------
declare -A NIVEAUX_AUTORISES
NIVEAUX_AUTORISES[Kimi]="0 1"
NIVEAUX_AUTORISES[DeepSeek]="0"
NIVEAUX_AUTORISES[Codex]="0 1"
NIVEAUX_AUTORISES[Claude]="0 1 2"

# ---------------------------------------------------------------------------
# FONCTIONS
# ---------------------------------------------------------------------------
log() {
  local ts
  ts=$(date +"%H:%M:%S")
  echo "[$ts] [$AGENT] $1"
}

git_pull() {
  log "git pull..."
  git -C "$REPO_PATH" pull --ff-only 2>&1 | while IFS= read -r line; do
    log "  $line"
  done
}

git_push() {
  local msg="$1"
  if [[ "$DRY_RUN" == true ]]; then
    log "[DRY-RUN] git add + commit + push omis"
    return
  fi
  log "git add + commit + push..."
  git -C "$REPO_PATH" add -A 2>/dev/null || true
  git -C "$REPO_PATH" commit -m "$msg" 2>&1 | while IFS= read -r line; do
    log "  $line"
  done || true
  git -C "$REPO_PATH" push origin HEAD 2>&1 | while IFS= read -r line; do
    log "  $line"
  done
}

# Helpers Python inline pour parser/déplacer
_lire_queue_py() {
python3 - "$QUEUE_FILE" << 'PYEOF'
import sys, re
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Extraction des blocs TASK
pattern = re.compile(r'(?m)^### (TASK-[\w-]+)\s*\n((?:- .*\n)+)')
for m in pattern.finditer(content):
    task_id = m.group(1)
    lines = m.group(2).strip().split("\n")
    print(f"ID:{task_id}")
    for line in lines:
        line = line.strip()
        if line.startswith("-"):
            line = line[1:].strip()
            if ":" in line:
                k, v = line.split(":", 1)
                print(f"{k.strip()}:{v.strip()}")
    print("---")
PYEOF
}

lire_queue() {
  if [[ ! -f "$QUEUE_FILE" ]]; then
    log "QUEUE.md introuvable. Arrêt."
    exit 1
  fi
  _lire_queue_py "$QUEUE_FILE"
}

filtrer_taches() {
  local niveaux="${NIVEAUX_AUTORISES[$AGENT]}"
  local in_task=false
  local id=""
  local agent_val=""
  local statut=""
  local niveau=""
  local desc=""
  local print_task=false

  while IFS= read -r line; do
    if [[ "$line" == ID:TASK-* ]]; then
      id="${line#ID:}"
      in_task=true
      agent_val=""; statut=""; niveau=""; desc=""
      print_task=false
    elif [[ "$line" == "---" ]]; then
      if [[ "$in_task" == true && "$statut" == "open" ]]; then
        # Vérifier agent
        local ok_agent=false
        IFS=',' read -ra ags <<< "$agent_val"
        for a in "${ags[@]}"; do
          [[ "${a// /}" == "$AGENT" ]] && ok_agent=true
        done
        # Vérifier niveau
        local ok_niveau=false
        for n in $niveaux; do
          [[ "$n" == "$niveau" ]] && ok_niveau=true
        done
        if [[ "$ok_agent" == true && "$ok_niveau" == true ]]; then
          print_task=true
        fi
      fi
      if [[ "$print_task" == true ]]; then
        echo "ID:$id"
        echo "Agent:$agent_val"
        echo "Niveau:$niveau"
        echo "Tache:$desc"
        echo "---"
      fi
      in_task=false
    elif [[ "$in_task" == true ]]; then
      local key="${line%%:*}"
      local val="${line#*:}"
      case "$key" in
        Agent) agent_val="$val" ;;
        Statut) statut="$val" ;;
        Niveau) niveau="$val" ;;
        Tache) desc="$val" ;;
      esac
    fi
  done
}

ecrire_channel() {
  local task_id="$1"
  local type_val="$2"
  local resume="$3"
  local now
  now=$(date +"%Y-%m-%d %H:%M:%S")
  {
    echo ""
    echo "---"
    echo "Agent : $AGENT"
    echo "Heure : $now"
    echo "Tache : $task_id"
    echo "Type : $type_val"
    echo "Resume : $resume"
  } >> "$CHANNEL_FILE"
  log "Entree ecrite dans AGENT_CHANNEL.md"
}

_deplacer_tache_py() {
python3 - "$QUEUE_FILE" "$1" "$2" "$3" << 'PYEOF'
import sys, re
path, task_id, section_from, section_to = sys.argv[1:5]

with open(path, "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

section_from_marker = f"## {section_from}"
section_to_marker   = f"## {section_to}"
task_marker         = f"### {task_id}"

in_section_from = False
in_task         = False
task_lines      = []
result_lines    = []
found           = False

for line in lines:
    if line == section_from_marker:
        in_section_from = True
        result_lines.append(line)
        continue

    if line.startswith("## ") and line != section_from_marker:
        in_section_from = False
        if in_task:
            in_task = False

    if in_section_from and line == task_marker:
        in_task = True
        found   = True
        task_lines.append(line)
        continue

    if in_task:
        if line.startswith("### ") or line.startswith("## "):
            in_task = False
            in_section_from = False
            result_lines.append(line)
        else:
            task_lines.append(line)
    else:
        result_lines.append(line)

if not found:
    print(f"Tache {task_id} non trouvee dans {section_from}", file=sys.stderr)
    sys.exit(1)

# Mise a jour du statut
new_status = section_to.lower().replace(" ", "_")
for i in range(len(task_lines)):
    if re.match(r'^- Statut\s*:\s*', task_lines[i]):
        task_lines[i] = f"- Statut : {new_status}"

# Supprimer lignes vides en fin de bloc
while task_lines and task_lines[-1].strip() == "":
    task_lines.pop()

# Inserer dans la section cible
new_result = []
inserted = False
for line in result_lines:
    new_result.append(line)
    if line == section_to_marker and not inserted:
        new_result.append("")
        new_result.extend(task_lines)
        inserted = True

# Garde-fou
if len(new_result) < 5:
    print("ERREUR CRITIQUE : DeplacerTache aurait vide QUEUE.md. Operation annulee.", file=sys.stderr)
    sys.exit(1)

with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(new_result) + "\n")

print(f"Tache {task_id} deplacee : {section_from} -> {section_to}")
PYEOF
}

deplacer_tache() {
  local task_id="$1"
  local from_section="$2"
  local to_section="$3"
  local out
  out=$(_deplacer_tache_py "$task_id" "$from_section" "$to_section" 2>&1)
  log "$out"
}

# ---------------------------------------------------------------------------
# BOUCLE PRINCIPALE
# ---------------------------------------------------------------------------
log "Runner Luna demarre"
log "Agent=$AGENT | Repo=$REPO_PATH | Interval=${INTERVAL_SECONDS}s | DryRun=$DRY_RUN"
log "Niveaux autorises : ${NIVEAUX_AUTORISES[$AGENT]}"

while true; do
  if ! git_pull; then
    log "ERREUR git pull. Attente ${INTERVAL_SECONDS}s..."
    sleep "$INTERVAL_SECONDS"
    continue
  fi

  candidates=$(lire_queue | filtrer_taches)

  if [[ -z "$candidates" ]]; then
    log "Aucune tache ouverte pour $AGENT (niveaux autorises)."
  else
    # Extraire la première tâche
    id=""
    niveau=""
    tache_desc=""
    reading=false
    while IFS= read -r line; do
      if [[ "$line" == ID:TASK-* ]]; then
        id="${line#ID:}"
        reading=true
      elif [[ "$line" == "---" && "$reading" == true ]]; then
        break
      elif [[ "$reading" == true ]]; then
        key="${line%%:*}"
        val="${line#*:}"
        [[ "$key" == "Niveau" ]] && niveau="$val"
        [[ "$key" == "Tache" ]] && tache_desc="$val"
      fi
    done <<< "$candidates"

    log "Tache detectee : $id (niveau $niveau)"
    log "Description : $tache_desc"

    if [[ "$DRY_RUN" == true ]]; then
      log "[DRY-RUN] Traitement simule. Pas d'ecriture."
      ecrire_channel "$id" "dry-run" "Simulation traitee pour $id"
    else
      deplacer_tache "$id" "TODO" "IN PROGRESS"
      log ">>> ACTION REQUISE : executez votre tache localement, puis relancez le runner."
      log ">>> Appuyez sur Ctrl+C pour arreter, faites votre travail, puis relancez."
      ecrire_channel "$id" "runner-detecte" "Tache $id detectee et prete. L'agent doit executer son audit/correction localement."
    fi

    git_push "agent($AGENT): runner cycle — tache $id detectee"
  fi

  log "Attente ${INTERVAL_SECONDS}s... (Ctrl+C pour arreter)"
  sleep "$INTERVAL_SECONDS"
done
