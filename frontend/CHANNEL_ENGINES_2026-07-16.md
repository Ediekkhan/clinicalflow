# WhatsApp and SMS Channel Engines

## Webhook contracts

- `GET /api/v1/webhooks/whatsapp` implements provider verification with `WHATSAPP_VERIFY_TOKEN`.
- `POST /api/v1/webhooks/{whatsapp|sms}` validates an HMAC-SHA256 signature before parsing the body.
- Meta-style WhatsApp payloads and the documented normalized SMS gateway payload are converted into the shared intake contract.
- Delivery receipts update a persistent channel message record.

Configure production secrets:

```dotenv
CHANNEL_WEBHOOK_SECRET=replace-with-a-long-random-secret
WHATSAPP_VERIFY_TOKEN=replace-with-provider-verification-token
```

Signed requests use `X-Hub-Signature-256` or `X-SynaptiVerse-Signature` with `sha256=<hex digest>`. The default `change-me` secret deliberately rejects every webhook.

## Conversation behavior

Both channels share duplicate-phone interception, family ticket grouping, clinical intake, live slot lookup, appointment confirmation, and cancellation. Text commands support `1`/continue, `2`/new patient, `3` or `BOOK`, and `CANCEL`. WhatsApp can render the returned menu as interactive buttons; SMS receives concise numbered/text instructions.

`GET /api/v1/channels/templates` exposes versioned low-bandwidth queue, booking, and cancellation templates. The SMS canvas reads this endpoint rather than duplicating templates in the frontend.

## Provider boundary

The webhook response contains a normalized `reply` object for the provider adapter or gateway worker to deliver. Channel message IDs and delivery states are stored in `operational_records`; tickets and appointments remain in their authoritative relational tables. No provider credentials are committed to the repository.

For Meta production setup, point the application webhook to `/api/v1/webhooks/whatsapp`, configure the verify token, and have the outbound gateway translate `reply.menu` into interactive message buttons. For an SMS provider, normalize inbound fields to `from`, `text`, `message_id`, optional `intent`/`slot_id`, and sign the exact request bytes.
