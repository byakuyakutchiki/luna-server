"""Client minimal pour les webhooks n8n du Luna Local Runner."""

import json
import urllib.request
from typing import Any, Dict, Optional


class N8NClient:
    def __init__(
        self,
        next_job_url: str,
        report_url: str,
        header_name: str,
        header_value: str,
        runner_id: str,
        timeout: int = 30,
    ):
        self.next_job_url = next_job_url
        self.report_url = report_url
        self.header_name = header_name
        self.header_value = header_value
        self.runner_id = runner_id
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.header_name and self.header_value:
            headers[self.header_name] = self.header_value
        return headers

    def _post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                if not body:
                    return {"_raw_status": resp.status}
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    return {"_raw_status": resp.status, "_raw_body": body}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {
                "_error": True,
                "_raw_status": e.code,
                "_raw_body": body,
                "message": f"n8n returned HTTP {e.code}",
            }
        except urllib.error.URLError as e:
            return {
                "_error": True,
                "message": f"Connection error: {e.reason}",
            }
        except Exception as e:
            return {
                "_error": True,
                "message": f"Request error: {e}",
            }

    def poll_next_job(self, device_status: str, current_job_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {
            "runner_id": self.runner_id,
            "device_status": device_status,
            "current_job_id": current_job_id,
        }
        return self._post(self.next_job_url, payload)

    def send_report(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(self.report_url, result)
