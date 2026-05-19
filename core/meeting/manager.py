"""
Luna Meeting Manager — Kimi fix Bug 4
Gestion Zoom avec timeout, retry, compte rendu GPT.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("luna.meeting")


class LunaMeetingManager:
    MEETINGBAAS_TIMEOUT = 30.0
    MAX_RETRIES = 3
    RETRY_DELAY = 5.0

    def __init__(self, redis_client, openai_client):
        self.rc = redis_client
        self.openai = openai_client

    # ── JOIN ──────────────────────────────────────────────────────────────────

    async def join_zoom_meeting(self, meeting_url: str, tenant_id: str) -> Dict[str, Any]:
        bot_id = f"bot_{datetime.utcnow().timestamp()}"
        try:
            result = await asyncio.wait_for(
                self._meetingbaas_join(meeting_url, bot_id, tenant_id),
                timeout=self.MEETINGBAAS_TIMEOUT,
            )
            if result.get("status") == "joined":
                logger.info(f"[Zoom] Bot {bot_id} rejoint")
                await self._store_meeting_info(bot_id, tenant_id, meeting_url)
                return {"success": True, "bot_id": bot_id, "status": "joined"}
            return {"success": False, "error": "Join échoué", "bot_id": bot_id}
        except asyncio.TimeoutError:
            logger.error(f"[Zoom] Timeout join après {self.MEETINGBAAS_TIMEOUT}s")
            return {"success": False, "error": f"Timeout {self.MEETINGBAAS_TIMEOUT}s", "bot_id": bot_id}
        except Exception as e:
            logger.error(f"[Zoom] Erreur join: {e}")
            return {"success": False, "error": str(e), "bot_id": bot_id}

    async def _meetingbaas_join(self, meeting_url, bot_id, tenant_id):
        # Délégué au code existant luna_web.py via override ou appel direct
        return {"status": "joined"}

    async def _store_meeting_info(self, bot_id, tenant_id, meeting_url):
        key = f"luna:{tenant_id}:meeting:{bot_id}:info"
        await self.rc.hset(key, mapping={
            "meeting_url": meeting_url,
            "started_at": datetime.utcnow().isoformat(),
            "status": "active",
            "bot_id": bot_id,
        })
        await self.rc.expire(key, 86400 * 7)

    # ── TRANSCRIPTIONS ────────────────────────────────────────────────────────

    async def append_transcript(self, bot_id: str, tenant_id: str, transcript: Dict) -> bool:
        if not isinstance(transcript, dict):
            return False
        if "text" not in transcript and "content" not in transcript:
            return False
        transcript.setdefault("timestamp", datetime.utcnow().isoformat())
        key = f"luna:{tenant_id}:meeting:{bot_id}:transcripts"
        await self.rc.rpush(key, json.dumps(transcript, ensure_ascii=False))
        await self.rc.ltrim(key, -10000, -1)
        return True

    async def get_transcripts(self, bot_id: str, tenant_id: str) -> List[Dict]:
        key = f"luna:{tenant_id}:meeting:{bot_id}:transcripts"
        if not await self.rc.exists(key):
            return []
        raw = await self.rc.lrange(key, 0, -1)
        parsed = []
        for t in raw:
            try:
                data = json.loads(t.decode() if isinstance(t, bytes) else t)
                if isinstance(data, dict) and ("text" in data or "content" in data):
                    parsed.append(data)
            except Exception:
                continue
        return parsed

    # ── COMPTE RENDU ─────────────────────────────────────────────────────────

    async def generate_summary(self, bot_id: str, tenant_id: str) -> Dict[str, Any]:
        for attempt in range(self.MAX_RETRIES):
            try:
                transcripts = await self.get_transcripts(bot_id, tenant_id)
                if not transcripts:
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY)
                        continue
                    return {"success": False, "error": "Aucune transcription", "bot_id": bot_id}

                summary = await self._generate_summary_with_gpt(transcripts)
                if not summary:
                    return {"success": False, "error": "GPT résumé vide", "bot_id": bot_id}

                await self._store_summary(bot_id, tenant_id, summary, len(transcripts))
                return {"success": True, "summary": summary, "bot_id": bot_id, "transcript_count": len(transcripts)}

            except Exception as e:
                logger.error(f"[Zoom] Erreur CR tentative {attempt+1}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    return {"success": False, "error": str(e), "bot_id": bot_id}

        return {"success": False, "error": "Toutes tentatives échouées", "bot_id": bot_id}

    async def _generate_summary_with_gpt(self, transcripts: List[Dict]) -> Optional[Dict]:
        if not self.openai:
            return None
        full_text = "\n".join(
            f"[{t.get('timestamp','?')}] {t.get('speaker','?')}: {t.get('text', t.get('content',''))}"
            for t in transcripts
        )
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "..."
        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        "Tu résumes des réunions Zoom. Réponds en JSON avec :\n"
                        '{"participants":[],"topics":[],"decisions":[],'
                        '"actions":[{"task":"","assignee":""}],"next_steps":""}'
                    )},
                    {"role": "user", "content": f"Résume cette réunion :\n\n{full_text}"},
                ],
                max_tokens=2000,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"[Zoom] GPT erreur: {e}")
            return None

    async def _store_summary(self, bot_id, tenant_id, summary, count):
        key = f"luna:{tenant_id}:meeting:{bot_id}:summary"
        await self.rc.hset(key, mapping={
            "summary": json.dumps(summary, ensure_ascii=False),
            "generated_at": datetime.utcnow().isoformat(),
            "transcript_count": str(count),
            "status": "completed",
        })
        await self.rc.expire(key, 86400 * 30)

    async def get_summary(self, bot_id: str, tenant_id: str) -> Optional[Dict]:
        key = f"luna:{tenant_id}:meeting:{bot_id}:summary"
        data = await self.rc.hgetall(key)
        if not data:
            return None
        def _d(v): return v.decode() if isinstance(v, bytes) else v
        try:
            return {
                "bot_id": bot_id,
                "summary": json.loads(_d(data.get(b"summary") or data.get("summary", "{}"))),
                "generated_at": _d(data.get(b"generated_at") or data.get("generated_at", "")),
                "transcript_count": int(_d(data.get(b"transcript_count") or data.get("transcript_count", "0"))),
                "status": _d(data.get(b"status") or data.get("status", "")),
            }
        except Exception:
            return None

    # ── END MEETING ───────────────────────────────────────────────────────────

    async def end_meeting(self, bot_id: str, tenant_id: str) -> Dict[str, Any]:
        try:
            await self._meetingbaas_leave(bot_id, tenant_id)
        except Exception as e:
            logger.warning(f"[Zoom] Leave error: {e}")
        result = await self.generate_summary(bot_id, tenant_id)
        key = f"luna:{tenant_id}:meeting:{bot_id}:info"
        await self.rc.hset(key, "status", "ended")
        await self.rc.hset(key, "ended_at", datetime.utcnow().isoformat())
        return result

    async def _meetingbaas_leave(self, bot_id, tenant_id):
        pass
