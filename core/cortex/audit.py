"""
AUDIT TRAIL + SUIVI COUTS + EXPORT PDF — Les ecrits restent.

3 classes:
- CortexAuditLogger: Persiste chaque action dans Redis
- CortexCostTracker: Suit les couts API/SMS par jour
- CortexPDFExporter: Genere des PDFs en memoire (BytesIO)

Redis keys:
  cortex:audit              — list, 10000 entries max
  cortex:costs:YYYY-MM-DD   — hash, couts du jour
  cortex:costs:months:YYYY-MM — hash, resume mensuel
"""

import hashlib
import io
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger("cortex.audit")

# ── Constantes ──
DEFAULT_AUDIT_RETENTION = 10_000
SMS_COST_EUR = 0.07  # Twilio France
VOICE_COST_PER_MIN = 0.08  # OpenAI Realtime voix (mars 2026)
TAVUS_COST_PER_MIN = 0.50  # Tavus visio Growth plan (mars 2026, inclut infra)

# Cout par token gpt-4o-mini (mars 2026)
OPENAI_COST_INPUT_PER_1K = 0.00015
OPENAI_COST_OUTPUT_PER_1K = 0.0006


# ══════════════════════════════════════════
#  AUDIT ENTRY
# ══════════════════════════════════════════

@dataclass
class AuditEntry:
    """Une entree du journal d'audit."""
    timestamp: float = field(default_factory=time.time)
    actor_id: str = ""          # "telegram:123456" ou "+33658..."
    actor_name: str = ""        # username
    role: str = ""              # founder, exploitant, system
    source: str = ""            # telegram, sms, api, auto
    command: str = ""           # STATUS, BAN, LOCKDOWN...
    args: str = ""              # arguments bruts
    level: str = "read"         # read, write, critical
    result: str = ""            # reponse tronquee
    success: bool = True
    cost_eur: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["result"] = d["result"][:300] if d["result"] else ""
        d["args"] = d["args"][:200] if d["args"] else ""
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


# ══════════════════════════════════════════
#  AUDIT LOGGER
# ══════════════════════════════════════════

class CortexAuditLogger:
    """Persiste chaque action Cortex dans Redis."""

    def __init__(self, redis_client=None,
                 retention: int = DEFAULT_AUDIT_RETENTION):
        self.redis = redis_client
        self.retention = retention
        self._key = "cortex:audit"

    async def log(self, actor_id: str, role: str, source: str,
                  command: str, args: str = "", result: str = "",
                  success: bool = True, cost_eur: float = 0.0,
                  actor_name: str = "",
                  metadata: Optional[dict] = None):
        """Enregistre une action dans le journal d'audit."""
        from .auth import COMMAND_LEVELS, LEVEL_READ
        level = COMMAND_LEVELS.get(command.upper(), LEVEL_READ)

        entry = AuditEntry(
            actor_id=actor_id,
            actor_name=actor_name or actor_id[:20],
            role=role,
            source=source,
            command=command.upper(),
            args=args,
            level=level,
            result=result,
            success=success,
            cost_eur=cost_eur,
            metadata=metadata or {},
        )

        if not self.redis:
            logger.debug(f"Audit (no redis): {entry.command} par {entry.actor_id}")
            return

        try:
            data = json.dumps(entry.to_dict())
            if hasattr(self.redis, "lpush"):
                await self.redis.lpush(self._key, data)
                await self.redis.ltrim(self._key, 0, self.retention - 1)
        except Exception as e:
            logger.error(f"Audit log erreur: {e}")

    async def get_entries(self, count: int = 100,
                          offset: int = 0) -> list[AuditEntry]:
        """Recupere des entrees depuis Redis."""
        if not self.redis:
            return []
        try:
            raw = await self.redis.lrange(self._key, offset,
                                          offset + count - 1)
            entries = []
            for r in raw:
                try:
                    data = json.loads(r)
                    entries.append(AuditEntry.from_dict(data))
                except (json.JSONDecodeError, TypeError):
                    pass
            return entries
        except Exception as e:
            logger.error(f"Audit read erreur: {e}")
            return []

    async def get_entries_for_period(self, days: int = 1) -> list[AuditEntry]:
        """Toutes les entrees des N derniers jours."""
        cutoff = time.time() - (days * 86400)
        all_entries = []
        batch_size = 500
        offset = 0
        while True:
            batch = await self.get_entries(count=batch_size, offset=offset)
            if not batch:
                break
            for entry in batch:
                if entry.timestamp >= cutoff:
                    all_entries.append(entry)
                else:
                    return all_entries
            offset += batch_size
        return all_entries

    async def count(self) -> int:
        """Nombre total d'entrees."""
        if not self.redis or not hasattr(self.redis, "llen"):
            return 0
        try:
            return await self.redis.llen(self._key)
        except Exception:
            return 0


# ══════════════════════════════════════════
#  COST TRACKER
# ══════════════════════════════════════════

class CortexCostTracker:
    """Suit les couts API/SMS par jour et par mois."""

    def __init__(self, redis_client=None):
        self.redis = redis_client

    def _day_key(self, date: Optional[datetime] = None) -> str:
        d = date or datetime.now(timezone.utc)
        return f"cortex:costs:{d.strftime('%Y-%m-%d')}"

    def _month_key(self, date: Optional[datetime] = None) -> str:
        d = date or datetime.now(timezone.utc)
        return f"cortex:costs:months:{d.strftime('%Y-%m')}"

    async def track_sms(self):
        """Enregistre un SMS envoye (0.07 EUR)."""
        if not self.redis:
            return
        try:
            day_key = self._day_key()
            pipe = self.redis.pipeline()
            pipe.hincrby(day_key, "sms_count", 1)
            pipe.hincrbyfloat(day_key, "sms_cost", SMS_COST_EUR)
            pipe.hincrbyfloat(day_key, "total_cost", SMS_COST_EUR)
            pipe.expire(day_key, 90 * 86400)
            await pipe.execute()
            # Mensuel
            month_key = self._month_key()
            pipe2 = self.redis.pipeline()
            pipe2.hincrby(month_key, "sms_count", 1)
            pipe2.hincrbyfloat(month_key, "sms_cost", SMS_COST_EUR)
            pipe2.hincrbyfloat(month_key, "total_cost", SMS_COST_EUR)
            pipe2.expire(month_key, 365 * 86400)
            await pipe2.execute()
        except Exception as e:
            logger.debug(f"Cost tracking SMS erreur: {e}")

    async def track_openai(self, tokens_in: int = 0, tokens_out: int = 0,
                           tenant_id: int = None):
        """Enregistre un appel OpenAI (global + par tenant si fourni)."""
        if not self.redis:
            return
        cost = (tokens_in / 1000 * OPENAI_COST_INPUT_PER_1K +
                tokens_out / 1000 * OPENAI_COST_OUTPUT_PER_1K)
        try:
            day_key = self._day_key()
            pipe = self.redis.pipeline()
            pipe.hincrby(day_key, "openai_tokens_in", tokens_in)
            pipe.hincrby(day_key, "openai_tokens_out", tokens_out)
            pipe.hincrbyfloat(day_key, "openai_cost", cost)
            pipe.hincrbyfloat(day_key, "total_cost", cost)
            pipe.expire(day_key, 90 * 86400)
            await pipe.execute()
            # Mensuel
            month_key = self._month_key()
            pipe2 = self.redis.pipeline()
            pipe2.hincrby(month_key, "openai_tokens_in", tokens_in)
            pipe2.hincrby(month_key, "openai_tokens_out", tokens_out)
            pipe2.hincrbyfloat(month_key, "openai_cost", cost)
            pipe2.hincrbyfloat(month_key, "total_cost", cost)
            pipe2.expire(month_key, 365 * 86400)
            await pipe2.execute()
            # Par tenant si fourni
            if tenant_id is not None:
                month = datetime.now(timezone.utc).strftime("%Y-%m")
                key = f"cortex:costs:tenant:{tenant_id}:{month}"
                pipe3 = self.redis.pipeline()
                pipe3.hincrby(key, "openai_tokens_in", tokens_in)
                pipe3.hincrby(key, "openai_tokens_out", tokens_out)
                pipe3.hincrbyfloat(key, "openai_cost", cost)
                pipe3.expire(key, 365 * 86400)
                await pipe3.execute()
        except Exception as e:
            logger.debug(f"Cost tracking OpenAI erreur: {e}")

    async def track_sms_tenant(self, tenant_id: int):
        """Enregistre un SMS envoye pour un tenant specifique."""
        if not self.redis:
            return
        try:
            # Global (comme avant)
            await self.track_sms()
            # Par tenant
            month = datetime.now(timezone.utc).strftime("%Y-%m")
            key = f"cortex:costs:tenant:{tenant_id}:{month}"
            pipe = self.redis.pipeline()
            pipe.hincrby(key, "sms_count", 1)
            pipe.hincrbyfloat(key, "sms_cost", SMS_COST_EUR)
            pipe.expire(key, 365 * 86400)
            await pipe.execute()
        except Exception as e:
            logger.debug(f"Cost tracking SMS tenant erreur: {e}")

    async def track_voice_tenant(self, tenant_id: int, minutes: float):
        """Enregistre un appel vocal pour un tenant."""
        if not self.redis:
            return
        cost = minutes * VOICE_COST_PER_MIN
        try:
            day_key = self._day_key()
            pipe = self.redis.pipeline()
            pipe.hincrbyfloat(day_key, "voice_minutes", minutes)
            pipe.hincrbyfloat(day_key, "voice_cost", cost)
            pipe.hincrbyfloat(day_key, "total_cost", cost)
            pipe.expire(day_key, 90 * 86400)
            await pipe.execute()
            month_key = self._month_key()
            pipe2 = self.redis.pipeline()
            pipe2.hincrbyfloat(month_key, "voice_minutes", minutes)
            pipe2.hincrbyfloat(month_key, "voice_cost", cost)
            pipe2.hincrbyfloat(month_key, "total_cost", cost)
            pipe2.expire(month_key, 365 * 86400)
            await pipe2.execute()
            # Par tenant
            month = datetime.now(timezone.utc).strftime("%Y-%m")
            key = f"cortex:costs:tenant:{tenant_id}:{month}"
            pipe3 = self.redis.pipeline()
            pipe3.hincrbyfloat(key, "voice_minutes", minutes)
            pipe3.hincrbyfloat(key, "voice_cost", cost)
            pipe3.expire(key, 365 * 86400)
            await pipe3.execute()
        except Exception as e:
            logger.debug(f"Cost tracking voice tenant erreur: {e}")

    async def track_tavus_tenant(self, tenant_id: int, minutes: float):
        """Enregistre une session Tavus visio pour un tenant."""
        if not self.redis:
            return
        cost = minutes * TAVUS_COST_PER_MIN
        try:
            # Global
            day_key = self._day_key()
            pipe = self.redis.pipeline()
            pipe.hincrbyfloat(day_key, "tavus_minutes", minutes)
            pipe.hincrbyfloat(day_key, "tavus_cost", cost)
            pipe.hincrbyfloat(day_key, "total_cost", cost)
            pipe.expire(day_key, 90 * 86400)
            await pipe.execute()
            month_key = self._month_key()
            pipe2 = self.redis.pipeline()
            pipe2.hincrbyfloat(month_key, "tavus_minutes", minutes)
            pipe2.hincrbyfloat(month_key, "tavus_cost", cost)
            pipe2.hincrbyfloat(month_key, "total_cost", cost)
            pipe2.expire(month_key, 365 * 86400)
            await pipe2.execute()
            # Par tenant
            month = datetime.now(timezone.utc).strftime("%Y-%m")
            key = f"cortex:costs:tenant:{tenant_id}:{month}"
            pipe3 = self.redis.pipeline()
            pipe3.hincrbyfloat(key, "tavus_minutes", minutes)
            pipe3.hincrbyfloat(key, "tavus_cost", cost)
            pipe3.expire(key, 365 * 86400)
            await pipe3.execute()
        except Exception as e:
            logger.debug(f"Cost tracking Tavus tenant erreur: {e}")

    async def get_tenant_month_usage(self, tenant_id: int,
                                       date: Optional[datetime] = None) -> dict:
        """Usage reel du mois pour un tenant (SMS, voix, visio, OpenAI)."""
        empty = {"sms_count": 0, "sms_cost": 0.0,
                 "voice_minutes": 0.0, "voice_cost": 0.0,
                 "tavus_minutes": 0.0, "tavus_cost": 0.0,
                 "openai_cost": 0.0, "openai_tokens_in": 0, "openai_tokens_out": 0,
                 "total_cost": 0.0}
        if not self.redis:
            return empty
        d = date or datetime.now(timezone.utc)
        month = d.strftime("%Y-%m")
        key = f"cortex:costs:tenant:{tenant_id}:{month}"
        try:
            data = await self.redis.hgetall(key)
            if not data:
                return empty
            d_clean = {}
            for k, v in data.items():
                k_str = k.decode() if isinstance(k, bytes) else k
                v_str = v.decode() if isinstance(v, bytes) else v
                d_clean[k_str] = v_str
            sms_count = int(float(d_clean.get("sms_count", 0)))
            sms_cost = float(d_clean.get("sms_cost", 0))
            voice_min = round(float(d_clean.get("voice_minutes", 0)), 1)
            voice_cost = float(d_clean.get("voice_cost", 0))
            tavus_min = round(float(d_clean.get("tavus_minutes", 0)), 1)
            tavus_cost = float(d_clean.get("tavus_cost", 0))
            openai_cost = float(d_clean.get("openai_cost", 0))
            openai_in = int(float(d_clean.get("openai_tokens_in", 0)))
            openai_out = int(float(d_clean.get("openai_tokens_out", 0)))
            total = sms_cost + voice_cost + tavus_cost + openai_cost
            return {
                "sms_count": sms_count, "sms_cost": round(sms_cost, 2),
                "voice_minutes": voice_min, "voice_cost": round(voice_cost, 2),
                "tavus_minutes": tavus_min, "tavus_cost": round(tavus_cost, 2),
                "openai_cost": round(openai_cost, 2),
                "openai_tokens_in": openai_in, "openai_tokens_out": openai_out,
                "total_cost": round(total, 2),
            }
        except Exception as e:
            logger.debug(f"Tenant month usage erreur: {e}")
            return empty

    async def get_month_costs_per_tenant(self,
                                          date: Optional[datetime] = None
                                          ) -> dict[str, dict]:
        """Couts du mois par tenant. Retourne {tenant_id: {sms_count, sms_cost, tavus_minutes, tavus_cost}}."""
        if not self.redis:
            return {}
        d = date or datetime.now(timezone.utc)
        month = d.strftime("%Y-%m")
        pattern = f"cortex:costs:tenant:*:{month}"
        result = {}
        try:
            keys = await self.redis.keys(pattern)
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                # cortex:costs:tenant:3:2026-02
                parts = key_str.split(":")
                if len(parts) >= 5:
                    tid = parts[3]
                    data = await self.redis.hgetall(key)
                    if data:
                        # Handle bytes keys
                        d_clean = {}
                        for k, v in data.items():
                            k_str = k.decode() if isinstance(k, bytes) else k
                            v_str = v.decode() if isinstance(v, bytes) else v
                            d_clean[k_str] = v_str
                        sms_c = float(d_clean.get("sms_cost", 0))
                        voice_c = float(d_clean.get("voice_cost", 0))
                        tavus_c = float(d_clean.get("tavus_cost", 0))
                        openai_c = float(d_clean.get("openai_cost", 0))
                        result[tid] = {
                            "sms_count": int(float(d_clean.get("sms_count", 0))),
                            "sms_cost": round(sms_c, 2),
                            "voice_minutes": round(float(d_clean.get("voice_minutes", 0)), 1),
                            "voice_cost": round(voice_c, 2),
                            "tavus_minutes": round(float(d_clean.get("tavus_minutes", 0)), 1),
                            "tavus_cost": round(tavus_c, 2),
                            "openai_cost": round(openai_c, 2),
                            "total_cost": round(sms_c + voice_c + tavus_c + openai_c, 2),
                        }
        except Exception as e:
            logger.debug(f"Cost per tenant erreur: {e}")
        return result

    async def get_day_costs(self, date: Optional[datetime] = None) -> dict:
        """Couts d'un jour specifique."""
        empty = {"sms_count": 0, "sms_cost": 0.0,
                 "openai_cost": 0.0, "voice_minutes": 0.0,
                 "voice_cost": 0.0, "tavus_minutes": 0.0,
                 "tavus_cost": 0.0, "total_cost": 0.0}
        if not self.redis:
            return empty
        try:
            data = await self.redis.hgetall(self._day_key(date))
            if not data:
                return empty
            return {
                "sms_count": int(float(data.get("sms_count", 0))),
                "sms_cost": float(data.get("sms_cost", 0)),
                "openai_tokens_in": int(float(data.get("openai_tokens_in", 0))),
                "openai_tokens_out": int(float(data.get("openai_tokens_out", 0))),
                "openai_cost": float(data.get("openai_cost", 0)),
                "voice_minutes": float(data.get("voice_minutes", 0)),
                "voice_cost": float(data.get("voice_cost", 0)),
                "tavus_minutes": float(data.get("tavus_minutes", 0)),
                "tavus_cost": float(data.get("tavus_cost", 0)),
                "total_cost": float(data.get("total_cost", 0)),
            }
        except Exception as e:
            logger.debug(f"Cost read erreur: {e}")
            return empty

    async def get_month_costs(self, date: Optional[datetime] = None) -> dict:
        """Couts d'un mois."""
        empty = {"sms_count": 0, "sms_cost": 0.0,
                 "openai_cost": 0.0, "voice_minutes": 0.0,
                 "voice_cost": 0.0, "tavus_minutes": 0.0,
                 "tavus_cost": 0.0, "total_cost": 0.0}
        if not self.redis:
            return empty
        try:
            data = await self.redis.hgetall(self._month_key(date))
            if not data:
                return empty
            # Handle bytes keys
            d = {}
            for k, v in data.items():
                k_str = k.decode() if isinstance(k, bytes) else k
                v_str = v.decode() if isinstance(v, bytes) else v
                d[k_str] = v_str
            return {
                "sms_count": int(float(d.get("sms_count", 0))),
                "sms_cost": float(d.get("sms_cost", 0)),
                "openai_cost": float(d.get("openai_cost", 0)),
                "voice_minutes": float(d.get("voice_minutes", 0)),
                "voice_cost": float(d.get("voice_cost", 0)),
                "tavus_minutes": float(d.get("tavus_minutes", 0)),
                "tavus_cost": float(d.get("tavus_cost", 0)),
                "total_cost": float(d.get("total_cost", 0)),
            }
        except Exception as e:
            return empty

    async def get_period_costs(self, days: int = 30) -> list[dict]:
        """Couts quotidiens sur N jours."""
        result = []
        now = datetime.now(timezone.utc)
        for i in range(days):
            d = now - timedelta(days=i)
            costs = await self.get_day_costs(d)
            costs["date"] = d.strftime("%Y-%m-%d")
            result.append(costs)
        return result


# ══════════════════════════════════════════
#  PDF EXPORTER
# ══════════════════════════════════════════

class CortexPDFExporter:
    """Genere des PDFs en memoire (BytesIO) via fpdf2."""

    def __init__(self, audit_logger: CortexAuditLogger,
                 cost_tracker: CortexCostTracker):
        self.audit = audit_logger
        self.costs = cost_tracker

    @staticmethod
    def _clean(text: str) -> str:
        """Nettoie le texte pour fpdf2 Helvetica (Latin-1 only)."""
        replacements = {
            "\u2014": "-", "\u2013": "-",  # em/en dash
            "\u2018": "'", "\u2019": "'",  # smart quotes
            "\u201c": '"', "\u201d": '"',
            "\u2026": "...",               # ellipsis
            "\u00e9": "e", "\u00e8": "e",  # e accents
            "\u00ea": "e", "\u00eb": "e",
            "\u00e0": "a", "\u00e2": "a",
            "\u00f4": "o", "\u00fb": "u",
            "\u00ee": "i", "\u00ef": "i",
            "\u00e7": "c",                 # cedille
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        # Fallback : supprimer les caracteres hors Latin-1
        return text.encode("latin-1", errors="replace").decode("latin-1")

    async def generate_audit_pdf(self, days: int = 7) -> io.BytesIO:
        """PDF du journal d'audit pour les N derniers jours."""
        from fpdf import FPDF

        entries = await self.audit.get_entries_for_period(days)
        now = datetime.now()

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # ── En-tete ──
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "LUNA CORTEX - JOURNAL D'AUDIT", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        cutoff = (now - timedelta(days=days)).strftime("%d/%m/%Y")
        pdf.cell(0, 6, f"Periode: {cutoff} - {now.strftime('%d/%m/%Y')}",
                 ln=True, align="C")
        pdf.cell(0, 6,
                 f"Genere le: {now.strftime('%d/%m/%Y a %H:%M:%S')}",
                 ln=True, align="C")
        pdf.cell(0, 6, f"Total: {len(entries)} actions", ln=True, align="C")
        pdf.ln(5)

        # ── Resume ──
        read_n = sum(1 for e in entries if e.level == "read")
        write_n = sum(1 for e in entries if e.level == "write")
        crit_n = sum(1 for e in entries if e.level == "critical")
        actors = set(e.actor_name for e in entries if e.actor_name)
        sources: dict[str, int] = {}
        for e in entries:
            sources[e.source] = sources.get(e.source, 0) + 1
        errors = sum(1 for e in entries if not e.success)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "RESUME", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6,
                 f"READ: {read_n} | WRITE: {write_n} | CRITICAL: {crit_n}"
                 f" | Erreurs: {errors}",
                 ln=True)
        actors_str = self._clean(', '.join(actors) or 'aucun')
        pdf.cell(0, 6, f"Acteurs: {actors_str}", ln=True)
        src_str = ", ".join(f"{k} {v}" for k, v in sorted(sources.items()))
        pdf.cell(0, 6, f"Sources: {src_str or 'aucune'}", ln=True)
        pdf.ln(5)

        # ── Tableau ──
        pdf.set_font("Helvetica", "B", 7)
        cols = [18, 12, 28, 12, 25, 14, 80]
        hdrs = ["Date", "Heure", "Acteur", "Role", "Commande",
                "Niveau", "Resultat"]
        for w, h in zip(cols, hdrs):
            pdf.cell(w, 6, h, border=1)
        pdf.ln()

        pdf.set_font("Helvetica", "", 6.5)
        for entry in entries:
            dt = datetime.fromtimestamp(entry.timestamp)
            row = [
                dt.strftime("%d/%m/%y"),
                dt.strftime("%H:%M"),
                self._clean(entry.actor_name[:14]),
                entry.role[0].upper() if entry.role else "?",
                entry.command[:12],
                entry.level[:8],
                self._clean(entry.result[:50].replace("\n", " ")),
            ]
            for w, val in zip(cols, row):
                pdf.cell(w, 5, val, border=1)
            pdf.ln()

        # ── Signature ──
        self._add_signature(pdf, entries)

        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        return buffer

    async def generate_costs_pdf(self,
                                  month_str: Optional[str] = None
                                  ) -> io.BytesIO:
        """PDF du rapport de couts pour un mois."""
        from fpdf import FPDF

        now = datetime.now()
        if month_str and len(month_str) == 7:
            try:
                target = datetime.strptime(month_str, "%Y-%m")
            except ValueError:
                target = now
        else:
            target = now

        month_costs = await self.costs.get_month_costs(target)

        # Couts quotidiens du mois
        if target.month == now.month and target.year == now.year:
            nb_days = now.day
        else:
            next_m = target.replace(day=28) + timedelta(days=4)
            nb_days = (next_m - timedelta(days=next_m.day)).day

        daily = []
        for i in range(nb_days):
            d = target.replace(day=1) + timedelta(days=i)
            costs = await self.costs.get_day_costs(d)
            costs["date"] = d.strftime("%d/%m")
            daily.append(costs)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # ── En-tete ──
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "LUNA CORTEX - RAPPORT DE COUTS", ln=True,
                 align="C")
        pdf.set_font("Helvetica", "", 10)
        mois_fr = ["Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
                    "Juillet", "Aout", "Septembre", "Octobre", "Novembre",
                    "Decembre"]
        nom_mois = mois_fr[target.month - 1]
        pdf.cell(0, 6, f"Mois: {nom_mois} {target.year}",
                 ln=True, align="C")
        pdf.cell(0, 6,
                 f"Genere le: {now.strftime('%d/%m/%Y a %H:%M:%S')}",
                 ln=True, align="C")
        pdf.ln(5)

        # ── Resume global ──
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "COUTS GLOBAUX", ln=True)
        pdf.set_font("Helvetica", "", 10)
        sms_c = month_costs.get("sms_count", 0)
        sms_cost = month_costs.get("sms_cost", 0)
        ai_cost = month_costs.get("openai_cost", 0)
        total = month_costs.get("total_cost", 0)
        pdf.cell(0, 6,
                 f"SMS Twilio: {sms_c} x 0.07EUR = {sms_cost:.2f} EUR",
                 ln=True)
        pdf.cell(0, 6, f"OpenAI API: {ai_cost:.2f} EUR", ln=True)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"TOTAL: {total:.2f} EUR", ln=True)
        pdf.ln(5)

        # ── Tableau quotidien ──
        pdf.set_font("Helvetica", "B", 8)
        cols = [25, 30, 30, 30, 35]
        hdrs = ["Date", "SMS", "SMS EUR", "OpenAI EUR", "Total EUR"]
        for w, h in zip(cols, hdrs):
            pdf.cell(w, 6, h, border=1)
        pdf.ln()

        pdf.set_font("Helvetica", "", 7.5)
        for d in daily:
            if d.get("total_cost", 0) > 0 or d.get("sms_count", 0) > 0:
                row = [
                    d["date"],
                    str(d.get("sms_count", 0)),
                    f"{d.get('sms_cost', 0):.2f}",
                    f"{d.get('openai_cost', 0):.2f}",
                    f"{d.get('total_cost', 0):.2f}",
                ]
                for w, val in zip(cols, row):
                    pdf.cell(w, 5, val, border=1)
                pdf.ln()

        # ── Signature ──
        pdf.ln(10)
        content_hash = hashlib.sha256(
            json.dumps(month_costs, sort_keys=True).encode()
        ).hexdigest()
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, "SIGNATURE NUMERIQUE", ln=True)
        pdf.set_font("Courier", "", 8)
        pdf.cell(0, 5, f"SHA-256: {content_hash}", ln=True)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5,
                 "Ce document est un export authentifie - Luna Cortex v1.0",
                 ln=True)

        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        return buffer

    async def generate_combined_pdf(self, days: int = 30) -> io.BytesIO:
        """PDF combine: audit + couts."""
        from fpdf import FPDF

        entries = await self.audit.get_entries_for_period(days)
        now = datetime.now()

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # ── Titre ──
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "LUNA CORTEX - RAPPORT COMPLET", ln=True,
                 align="C")
        pdf.set_font("Helvetica", "", 10)
        cutoff = (now - timedelta(days=days)).strftime("%d/%m/%Y")
        pdf.cell(0, 6,
                 f"Periode: {cutoff} - {now.strftime('%d/%m/%Y')}",
                 ln=True, align="C")
        pdf.cell(0, 6,
                 f"Genere le: {now.strftime('%d/%m/%Y a %H:%M:%S')}",
                 ln=True, align="C")
        pdf.ln(8)

        # ── Section 1: Couts ──
        month_costs = await self.costs.get_month_costs()
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "1. COUTS DU MOIS", ln=True)
        pdf.set_font("Helvetica", "", 10)
        sms_c = month_costs.get("sms_count", 0)
        pdf.cell(0, 6,
                 f"SMS: {sms_c} x 0.07EUR = "
                 f"{month_costs.get('sms_cost', 0):.2f} EUR",
                 ln=True)
        pdf.cell(0, 6,
                 f"OpenAI: {month_costs.get('openai_cost', 0):.2f} EUR",
                 ln=True)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6,
                 f"TOTAL: {month_costs.get('total_cost', 0):.2f} EUR",
                 ln=True)
        pdf.ln(5)

        # ── Section 2: Audit ──
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8,
                 f"2. JOURNAL D'AUDIT ({len(entries)} actions)", ln=True)

        pdf.set_font("Helvetica", "B", 7)
        cols = [18, 12, 28, 12, 25, 14, 80]
        hdrs = ["Date", "Heure", "Acteur", "Role", "Commande",
                "Niveau", "Resultat"]
        for w, h in zip(cols, hdrs):
            pdf.cell(w, 6, h, border=1)
        pdf.ln()

        pdf.set_font("Helvetica", "", 6.5)
        for entry in entries:
            dt = datetime.fromtimestamp(entry.timestamp)
            row = [
                dt.strftime("%d/%m/%y"),
                dt.strftime("%H:%M"),
                self._clean(entry.actor_name[:14]),
                entry.role[0].upper() if entry.role else "?",
                entry.command[:12],
                entry.level[:8],
                self._clean(entry.result[:50].replace("\n", " ")),
            ]
            for w, val in zip(cols, row):
                pdf.cell(w, 5, val, border=1)
            pdf.ln()

        # ── Signature ──
        self._add_signature(pdf, entries)

        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        return buffer

    def _add_signature(self, pdf, entries: list[AuditEntry]):
        """Ajoute la signature SHA-256 au PDF."""
        pdf.ln(10)
        content_hash = hashlib.sha256(
            json.dumps([e.to_dict() for e in entries],
                       sort_keys=True).encode()
        ).hexdigest()
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, "SIGNATURE NUMERIQUE", ln=True)
        pdf.set_font("Courier", "", 8)
        pdf.cell(0, 5, f"SHA-256: {content_hash}", ln=True)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5,
                 "Ce document est un export authentifie - Luna Cortex v1.0",
                 ln=True)
