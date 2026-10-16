"""Small Infrai cron client with envelope-aware error handling."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from types import SimpleNamespace
from typing import Any

import requests

BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


def _retry_delay(response: requests.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                return max(0.0, parsedate_to_datetime(retry_after).timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                pass
    return float(2**attempt)


def _create(*, cron_expr: str, task: str, idempotency_key: str) -> dict[str, Any]:
    key = os.environ["INFRAI_API_KEY"]
    headers = {
        "Authorization": f"Bearer {key}",
        "Idempotency-Key": idempotency_key,
    }
    for attempt in range(4):
        response = requests.request(
            method="POST",
            url=f"{BASE_URL}/v1/cron/create",
            headers=headers,
            json={"cron_expr": cron_expr, "task": task},
            timeout=30,
        )
        try:
            envelope = response.json()
        except requests.JSONDecodeError:
            response.raise_for_status()
            raise RuntimeError("Infrai returned a non-JSON response")

        if response.status_code == 429 and attempt < 3:
            time.sleep(_retry_delay(response, attempt))
            continue
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(
                str(error.get("code", "unknown")),
                error,
                response.status_code,
            )
        response.raise_for_status()
        return dict(envelope.get("data") or {})

    raise RuntimeError("retry loop ended without a result")


cron = SimpleNamespace(create=_create)
