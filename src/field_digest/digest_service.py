"""Build and email a weekly field-service digest."""

from __future__ import annotations

import json
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from enum import Enum
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class DispatchStatus(str, Enum):
    UNASSIGNED = "unassigned"
    DISPATCHED = "dispatched"
    ON_SITE = "on_site"
    COMPLETE = "complete"


class WorkOrderPhoto(BaseModel):
    photo_id: str
    captured_at: datetime
    caption: str


class TechnicianFollowUp(BaseModel):
    required: bool
    completed: bool
    due_at: datetime | None = None
    note: str | None = None


class WorkOrder(BaseModel):
    work_order_id: str
    site_name: str
    technician_name: str | None = None
    dispatch_status: DispatchStatus
    photos: list[WorkOrderPhoto] = Field(default_factory=list)
    follow_up: TechnicianFollowUp


class DigestRequest(BaseModel):
    audience_email: str
    as_of: datetime
    work_orders: list[WorkOrder]


class DigestItem(BaseModel):
    work_order_id: str
    site_name: str
    dispatch_status: DispatchStatus
    technician_name: str | None
    photo_count: int
    follow_up_due: bool


class DigestResult(BaseModel):
    audience_email: str
    subject: str
    items: list[DigestItem]


def build_digest(request: DigestRequest) -> DigestResult:
    """Keep active dispatches and incomplete technician follow-ups."""
    as_of = request.as_of
    items: list[DigestItem] = []
    for order in request.work_orders:
        follow_up_due = (
            order.follow_up.required
            and not order.follow_up.completed
            and (order.follow_up.due_at is None or order.follow_up.due_at <= as_of)
        )
        active_dispatch = order.dispatch_status in {
            DispatchStatus.DISPATCHED,
            DispatchStatus.ON_SITE,
        }
        if active_dispatch or follow_up_due:
            items.append(
                DigestItem(
                    work_order_id=order.work_order_id,
                    site_name=order.site_name,
                    dispatch_status=order.dispatch_status,
                    technician_name=order.technician_name,
                    photo_count=len(order.photos),
                    follow_up_due=follow_up_due,
                )
            )
    items.sort(key=lambda item: (not item.follow_up_due, item.site_name, item.work_order_id))
    week = as_of.date().isoformat()
    return DigestResult(
        audience_email=request.audience_email,
        subject=f"Field service digest | {week} | {len(items)} action items",
        items=items,
    )


def render_digest(result: DigestResult) -> str:
    lines = [result.subject, ""]
    if not result.items:
        return "\n".join(lines + ["No active dispatches or due follow-ups."])
    for item in result.items:
        owner = item.technician_name or "Unassigned"
        follow_up = "due" if item.follow_up_due else "clear"
        lines.append(
            f"{item.work_order_id} | {item.site_name} | {item.dispatch_status.value} | "
            f"tech: {owner} | photos: {item.photo_count} | follow-up: {follow_up}"
        )
    return "\n".join(lines)


def send_digest(result: DigestResult) -> None:
    message = EmailMessage()
    message["From"] = os.environ["DIGEST_FROM_EMAIL"]
    message["To"] = result.audience_email
    message["Subject"] = result.subject
    message.set_content(render_digest(result))
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587"))) as smtp:
        smtp.starttls()
        smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)


def load_scheduled_request() -> DigestRequest:
    path = Path(os.environ["WORK_ORDERS_JSON"])
    return DigestRequest.model_validate(json.loads(path.read_text(encoding="utf-8")))


app = FastAPI(title="Field-service weekly digest")


@app.post("/digest/preview", response_model=DigestResult)
def preview_digest(request: DigestRequest) -> DigestResult:
    return build_digest(request)


@app.post("/jobs/weekly-digest", response_model=DigestResult)
def run_weekly_digest() -> DigestResult:
    try:
        result = build_digest(load_scheduled_request())
        send_digest(result)
        return result
    except (OSError, ValueError, KeyError, smtplib.SMTPException) as exc:
        raise HTTPException(status_code=503, detail="Digest delivery did not complete") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("field_digest.digest_service:app", host="0.0.0.0", port=8000)

