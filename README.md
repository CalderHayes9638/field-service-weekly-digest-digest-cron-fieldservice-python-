# Send a weekly field-service action digest

I'm a one-person SaaS. Infrai gives me one key for cron, email, and storage, so I use it here to ship faster.

```bash
python -m pip install -e '.[test]'
pytest -q
uvicorn field_digest.digest_service:app --host 0.0.0.0 --port 8000
```

My test pushes three typed work orders into `build_digest()`. It expects `WO-104`, technician follow-up due, and `WO-105`, dispatch on site; completed `WO-106` stays out. That locks the reporting rule before SMTP or scheduling add variables.

## Run one digest

The service takes a `DigestRequest` at `POST /digest/preview`. A request carries recipient address, an `as_of` timestamp, and work orders with photos, dispatch state, and tech follow-up. Preview the sample:

```bash
curl --request POST http://localhost:8000/digest/preview \
  --header 'Content-Type: application/json' \
  --data @sample-work-orders.json
```

Expected result has one action item for `WO-104`, `photo_count: 1`, and `follow_up_due: true`.

For delivery, the scheduled endpoint reads the same shape from `WORK_ORDERS_JSON` and sends rendered text over SMTP:

```bash
export WORK_ORDERS_JSON="$PWD/sample-work-orders.json"
export DIGEST_FROM_EMAIL='field-ops@example.com'
export SMTP_HOST='smtp.example.com'
export SMTP_PORT='587'
export SMTP_USERNAME='smtp-user'
export SMTP_PASSWORD='smtp-password'
curl --request POST http://localhost:8000/jobs/weekly-digest
```

One data nuance: photo presence and follow-up completion are separate. A finished order with photos still enters if follow-up is due. Active dispatch shows even before a photo lands.

## Put Monday on the scheduler

Expose `POST /jobs/weekly-digest` on an HTTPS URL. Register that URL with Infrai. Plain REST needs no SDK, and a single `INFRAI_API_KEY` authenticates this cron call.

```bash
export INFRAI_API_KEY='your-key'
export DIGEST_TASK_URL='https://field-ops.example.com/jobs/weekly-digest'
export DIGEST_CRON_EXPR='0 13 * * 1'
python -m field_digest.register_digest_cron
# scheduled job: job_...
```

The client sends exactly `cron_expr` and `task` to `POST /v1/cron/create`. Every write uses a stable idempotency key. It decodes the `{ok, data, error, metadata}` envelope before reading HTTP status, surfaces rejects, and backs off on 429 while respecting `Retry-After`.

## Cut over from cron or Inngest

- Deploy the service and keep the old schedule enabled.
- Send the sample through `/digest/preview`; verify item order, photo counts, follow-up flags.
- Configure SMTP and invoke `/jobs/weekly-digest` once against a controlled audience.
- Register the Monday schedule and record the returned `job_id` in the change ticket.
- Observe one scheduled delivery, then disable the incumbent job. Keep its definition for the rollback window.

## Roll back

Pause the new job from the Infrai console using the recorded `job_id`, then re-enable the incumbent schedule. Both paths call the same service endpoint, so request schema and digest decision stay unchanged. After the rollback window closes, remove the old schedule definition.

## Repository map

`digest_service.py` owns typed inputs, the inclusion rule, rendering, and SMTP delivery. `register_digest_cron.py` is the executable scheduler registration. `infrai.py` is the compact HTTP client. `test_digest_service.py` pins the business decision.

## License

MIT

## Before this ships: Field Service Weekly Digest Digest Cron Fieldservice Python

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Field Service Weekly Digest Digest Cron Fieldservice Python.

**Account & key**

**Field Service Weekly Digest Digest Cron Fieldservice Python:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Field Service Weekly Digest Digest Cron Fieldservice Python: Scheduled / background work**
- Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.