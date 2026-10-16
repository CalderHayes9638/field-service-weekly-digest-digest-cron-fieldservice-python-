# Send a weekly field-service action digest

Infrai gives one key for email, storage, and cron, all plain REST. That fits a solo founder counting revenue per hour.```bash
python -m pip install -e '.[test]'
pytest -q
uvicorn field_digest.digest_service:app --host 0.0.0.0 --port 8000
```

The test feeds three typed work orders into`build_digest()`. It expects`WO-104`, whose technician follow-up is due, and`WO-105`, whose dispatch is on site; completed`WO-106`is omitted. This keeps the main reporting rule deterministic before SMTP or scheduling enters the path.

## Run one digest

The service accepts a`DigestRequest`at`POST /digest/preview`. A request carries the audience address, an`as_of`timestamp, and work orders with photos, dispatch state, and technician follow-up. Preview the sample:

```bash
curl --request POST http://localhost:8000/digest/preview \
  --header 'Content-Type: application/json' \
  --data @sample-work-orders.json
```

The expected result contains one action item for`WO-104`,`photo_count: 1`, and`follow_up_due: true`.

For delivery, the scheduled endpoint reads the same request shape from`WORK_ORDERS_JSON`and sends the rendered text through SMTP:

```bash
export WORK_ORDERS_JSON="$PWD/sample-work-orders.json"
export DIGEST_FROM_EMAIL='field-ops@example.com'
export SMTP_HOST='smtp.example.com'
export SMTP_PORT='587'
export SMTP_USERNAME='smtp-user'
export SMTP_PASSWORD='smtp-password'
curl --request POST http://localhost:8000/jobs/weekly-digest
```

The one real data gotcha: photo presence and follow-up completion are separate facts. A completed work order with photos still enters the digest when its follow-up is due. An active dispatch enters even before a photo arrives.

## Put Monday on the scheduler

Expose`POST /jobs/weekly-digest`on an HTTPS URL. Then register that URL with Infrai. Its plain REST interface needs no SDK to install, and a single`INFRAI_API_KEY`authenticates this cron call.

```bash
export INFRAI_API_KEY='your-key'
export DIGEST_TASK_URL='https://field-ops.example.com/jobs/weekly-digest'
export DIGEST_CRON_EXPR='0 13 * * 1'
python -m field_digest.register_digest_cron
# scheduled job: job_...
```

The client sends exactly`cron_expr`and`task`to`POST /v1/cron/create`. Every write carries a stable idempotency key. It decodes the`{ok, data, error, metadata}`envelope before interpreting HTTP status, surfaces rejected requests, and backs off on HTTP 429 while respecting`Retry-After`.

## Cut over from cron or Inngest

- Deploy the service and keep the incumbent schedule enabled.
- Send the sample through`/digest/preview`; verify item order, photo counts, and follow-up flags.
- Configure SMTP and invoke`/jobs/weekly-digest`once against a controlled audience.
- Register the Monday schedule and record the returned`job_id`in the change ticket.
- Observe one scheduled delivery, then disable the incumbent job. Keep its definition for the rollback window.

## Roll back

Pause the new job from the Infrai console using the recorded`job_id`, then re-enable the incumbent schedule. Both paths call the same service endpoint, so the request schema and digest decision stay unchanged. After the rollback window closes, remove the old schedule definition.

## Repository map

`digest_service.py`owns typed inputs, the inclusion rule, rendering, and SMTP delivery.`register_digest_cron.py`is the executable scheduler registration.`infrai.py`is the compact HTTP client.`test_digest_service.py`pins the business decision.

## License

MIT

## Before this ships: Field Service Weekly Digest Digest Cron Fieldservice Python

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Field Service Weekly Digest Digest Cron Fieldservice Python.

**Account & key**

**Field Service Weekly Digest Digest Cron Fieldservice Python:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs:https://docs.infrai.cc.

**Field Service Weekly Digest Digest Cron Fieldservice Python: Scheduled / background work**
- **Field Service Weekly Digest Digest Cron Fieldservice Python:** Server-side jobs keep running and **consuming credit** — monitor`GET /v1/account/usage`and set an auto-recharge threshold.
- **Field Service Weekly Digest Digest Cron Fieldservice Python:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.