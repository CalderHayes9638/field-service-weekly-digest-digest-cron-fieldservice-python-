"""Register the weekly field-service digest callback."""

from __future__ import annotations

import hashlib
import os

from field_digest import infrai
from field_digest.infrai import InfraiError


def register() -> str:
    task_url = os.environ["DIGEST_TASK_URL"]
    cron_expr = os.environ.get("DIGEST_CRON_EXPR", "0 13 * * 1")
    request_identity = hashlib.sha256(f"{cron_expr}\n{task_url}".encode()).hexdigest()
    data = infrai.cron.create(
        cron_expr=cron_expr,
        task=task_url,
        idempotency_key=f"field-digest-{request_identity}",
    )
    return str(data["job_id"])


if __name__ == "__main__":
    try:
        print(f"scheduled job: {register()}")
    except InfraiError as exc:
        raise SystemExit(f"schedule rejected: {exc}") from exc
