"""Appel des agents IA en mode non interactif.

Chaque agent retourne un JSON structuré au format décisionnel.
Le superviseur valide et exécute l'action demandée ; l'agent ne modifie
jamais directement le dépôt ou le téléphone.
"""

import json
import logging
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentCallError(Exception):
    pass


class InvalidDecisionError(Exception):
    pass


class AgentDecision:
    """Représente la décision structurée retournée par un agent."""

    REQUIRED_FIELDS = {"summary", "decision", "requested_action", "files_relevant", "expected_result"}
    VALID_DECISIONS = {"execute", "review", "audit", "complete", "blocked"}
    VALID_ACTION_TYPES = {
        "read_files", "edit_files", "run_tests", "build_debug", "install_debug",
        "collect_adb", "commit_local", "none",
    }

    def __init__(self, raw: Dict[str, Any], agent_name: str):
        self.raw = raw
        self.agent_name = agent_name
        self._validate()

    def _validate(self) -> None:
        missing = self.REQUIRED_FIELDS - set(self.raw.keys())
        if missing:
            raise InvalidDecisionError(f"Champs manquants dans la décision: {sorted(missing)}")

        if self.raw["decision"] not in self.VALID_DECISIONS:
            raise InvalidDecisionError(
                f"Décision invalide: {self.raw['decision']!r}. "
                f"Valeurs acceptées: {self.VALID_DECISIONS}"
            )

        action = self.raw.get("requested_action") or {}
        action_type = action.get("type", "none")
        if action_type not in self.VALID_ACTION_TYPES:
            raise InvalidDecisionError(f"Type d'action invalide: {action_type!r}")

        if not isinstance(self.raw.get("files_relevant"), list):
            raise InvalidDecisionError("files_relevant doit être une liste")

        if not isinstance(self.raw.get("requires_human_validation"), bool):
            self.raw["requires_human_validation"] = False

    @property
    def summary(self) -> str:
        return str(self.raw.get("summary", ""))

    @property
    def decision(self) -> str:
        return str(self.raw.get("decision", ""))

    @property
    def requested_action(self) -> Dict[str, Any]:
        return self.raw.get("requested_action") or {"type": "none"}

    @property
    def files_relevant(self) -> List[str]:
        return [str(x) for x in self.raw.get("files_relevant", [])]

    @property
    def expected_result(self) -> str:
        return str(self.raw.get("expected_result", ""))

    @property
    def requires_human_validation(self) -> bool:
        return bool(self.raw.get("requires_human_validation", False))

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.raw)


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extrait le premier bloc JSON ou objet JSON d'un texte."""
    text = text.strip()
    if not text:
        return None

    # Essaie de parser directement
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Cherche un bloc ```json ... ```
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Cherche le premier objet JSON { ... }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


class AgentCaller(ABC):
    """Classe de base pour tous les callers d'agents."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    def is_available(self) -> bool:
        """Par défaut, disponible si la configuration minimale est présente."""
        return True

    @abstractmethod
    def call(self, mission: Dict[str, Any], context: str) -> AgentDecision:
        pass

    def _load_prompt(self, role: str) -> str:
        """Charge le prompt système pour un rôle donné."""
        prompt_path = Path(__file__).resolve().parent / "prompts" / f"{role}.txt"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return "Tu es un agent Luna. Réponds uniquement par un JSON de décision."


class KimiCaller(AgentCaller):
    """Appelle Kimi Code CLI en mode non interactif et parse la sortie JSON."""

    @property
    def name(self) -> str:
        return "kimi"

    def is_available(self) -> bool:
        return shutil.which(self.config.get("KIMI_CLI", "/home/ludo/.kimi-code/bin/kimi")) is not None

    def call(self, mission: Dict[str, Any], context: str) -> AgentDecision:
        kimi_bin = self.config.get("KIMI_CLI", "/home/ludo/.kimi-code/bin/kimi")
        if not shutil.which(kimi_bin):
            raise AgentCallError(f"Kimi CLI introuvable: {kimi_bin}")

        system_prompt = self._load_prompt(mission.get("role", "operator"))
        user_prompt = self._build_prompt(system_prompt, mission, context)

        cmd = [kimi_bin, "-p", user_prompt, "--output-format", "stream-json"]
        logger.info("Appel Kimi: %s", " ".join(cmd[:3]) + " ...")

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.config["PROJECT_PATH"],
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            raise AgentCallError("Kimi CLI a dépassé le délai de 300s")
        except Exception as e:
            raise AgentCallError(f"Échec de l'appel Kimi: {e}")

        if proc.returncode != 0 and not proc.stdout:
            raise AgentCallError(f"Kimi CLI a échoué: {proc.stderr}")

        return self._parse_output(proc.stdout, proc.stderr)

    def _build_prompt(self, system_prompt: str, mission: Dict[str, Any], context: str) -> str:
        return (
            f"{system_prompt}\n\n"
            f"=== MISSION ===\n"
            f"mission_id: {mission.get('mission_id', 'N/A')}\n"
            f"task_id: {mission.get('task_id', 'N/A')}\n"
            f"role: {mission.get('role', 'operator')}\n"
            f"objectif: {mission.get('objective', mission.get('description', ''))}\n\n"
            f"=== CONTEXTE ===\n{context}\n\n"
            f"=== INSTRUCTIONS ===\n"
            "Tu ne dois PAS modifier directement de fichiers ni exécuter de commandes. "
            "Tu dois analyser le contexte et retourner UNIQUEMENT un JSON valide au format suivant:\n\n"
            "{\"summary\": \"résumé de l'analyse\", "
            "\"decision\": \"execute|review|audit|complete|blocked\", "
            "\"requested_action\": {\"type\": \"read_files|edit_files|run_tests|build_debug|install_debug|collect_adb|commit_local|none\", \"parameters\": {}}, "
            "\"files_relevant\": [\"...\"], "
            "\"expected_result\": \"...\", "
            "\"requires_human_validation\": false}\n\n"
            "Réponds uniquement par ce JSON, sans texte avant ou après."
        )

    def _parse_output(self, stdout: str, stderr: str) -> AgentDecision:
        tool_calls: List[Dict[str, Any]] = []
        assistant_contents: List[str] = []

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            role = obj.get("role")
            if role == "assistant":
                if "tool_calls" in obj:
                    tool_calls.extend(obj["tool_calls"])
                if "content" in obj and obj["content"]:
                    assistant_contents.append(str(obj["content"]))

        if not assistant_contents:
            raise AgentCallError("Aucune réponse textuelle trouvée dans la sortie Kimi")

        last_content = assistant_contents[-1]
        parsed = _extract_json_from_text(last_content)
        if parsed is None:
            raise AgentCallError(f"Impossible d'extraire un JSON de la réponse Kimi:\n{last_content[:500]}")

        decision = AgentDecision(parsed, self.name)
        if tool_calls:
            logger.info("Kimi a utilisé %d appel(s) interne(s) lors de l'analyse", len(tool_calls))
        return decision


class DeepSeekCaller(AgentCaller):
    """Appelle l'API DeepSeek directement (le wrapper CLI est interactif uniquement)."""

    @property
    def name(self) -> str:
        return "deepseek"

    def is_available(self) -> bool:
        return bool(self.config.get("DEEPSEEK_API_KEY", ""))

    def call(self, mission: Dict[str, Any], context: str) -> AgentDecision:
        api_key = self.config.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise AgentCallError("DEEPSEEK_API_KEY manquante")

        system_prompt = self._load_prompt(mission.get("role", "auditor"))
        user_prompt = self._build_user_prompt(mission, context)

        payload = {
            "model": self.config.get("DEEPSEEK_MODEL", "deepseek-chat"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise AgentCallError(f"DeepSeek HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}")
        except Exception as e:
            raise AgentCallError(f"Échec appel DeepSeek: {e}")

        content = body["choices"][0]["message"]["content"]
        parsed = _extract_json_from_text(content)
        if parsed is None:
            raise AgentCallError(f"Impossible d'extraire un JSON de la réponse DeepSeek:\n{content[:500]}")
        return AgentDecision(parsed, self.name)

    def _build_user_prompt(self, mission: Dict[str, Any], context: str) -> str:
        return (
            f"mission_id: {mission.get('mission_id', 'N/A')}\n"
            f"task_id: {mission.get('task_id', 'N/A')}\n"
            f"objectif: {mission.get('objective', mission.get('description', ''))}\n\n"
            f"=== CONTEXTE ===\n{context}\n\n"
            "Réponds UNIQUEMENT par un JSON de décision. Tu ne dois pas modifier de fichiers."
        )


class OpenAICaller(AgentCaller):
    """Appelle l'API OpenAI pour le rôle Codex/coordinateur."""

    @property
    def name(self) -> str:
        return "codex"

    def is_available(self) -> bool:
        return bool(self.config.get("OPENAI_API_KEY", ""))

    def call(self, mission: Dict[str, Any], context: str) -> AgentDecision:
        api_key = self.config.get("OPENAI_API_KEY", "")
        if not api_key:
            raise AgentCallError("OPENAI_API_KEY manquante")

        system_prompt = self._load_prompt(mission.get("role", "coordinator"))
        user_prompt = self._build_user_prompt(mission, context)

        payload = {
            "model": self.config.get("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise AgentCallError(f"OpenAI HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}")
        except Exception as e:
            raise AgentCallError(f"Échec appel OpenAI: {e}")

        content = body["choices"][0]["message"]["content"]
        parsed = _extract_json_from_text(content)
        if parsed is None:
            raise AgentCallError(f"Impossible d'extraire un JSON de la réponse OpenAI:\n{content[:500]}")
        return AgentDecision(parsed, self.name)

    def _build_user_prompt(self, mission: Dict[str, Any], context: str) -> str:
        return (
            f"mission_id: {mission.get('mission_id', 'N/A')}\n"
            f"task_id: {mission.get('task_id', 'N/A')}\n"
            f"objectif: {mission.get('objective', mission.get('description', ''))}\n\n"
            f"=== CONTEXTE ===\n{context}\n\n"
            "Réponds UNIQUEMENT par un JSON de décision. Tu ne dois pas modifier de fichiers."
        )


class ReviewerCaller(KimiCaller):
    """Le reviewer utilise Kimi avec le prompt reviewer."""

    @property
    def name(self) -> str:
        return "review"

    def call(self, mission: Dict[str, Any], context: str) -> AgentDecision:
        # Force le rôle reviewer pour charger le bon prompt
        mission["role"] = "reviewer"
        return super().call(mission, context)


def get_caller(role: str, config: Dict[str, Any]) -> AgentCaller:
    """Retourne le caller adapté au rôle demandé."""
    role_lower = role.lower()
    if role_lower in ("operator", "kimi"):
        return KimiCaller(config)
    if role_lower in ("auditor", "deepseek"):
        caller = DeepSeekCaller(config)
        if caller.is_available():
            return caller
        logger.warning("DeepSeek indisponible, fallback sur Kimi pour auditor")
        return KimiCaller(config)
    if role_lower in ("coordinator", "codex"):
        caller = OpenAICaller(config)
        if caller.is_available():
            return caller
        logger.warning("OpenAI/Codex indisponible, fallback sur Kimi pour coordinator")
        return KimiCaller(config)
    if role_lower == "reviewer":
        return ReviewerCaller(config)
    raise AgentCallError(f"Rôle inconnu: {role}")
