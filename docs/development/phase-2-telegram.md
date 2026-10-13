# ClipForge Phase 2: Telegram Approval Gate & Webhook Integration Specs

This document outlines the architecture, security invariants, and payload specifications for the Telegram Bot API webhook integration and interactive approval gate in Phase 2 of **ClipForge**.

---

## 1. Webhook Architecture & Security Invariants

### Telegram Webhook Lifecycle
- **Endpoint:** `POST /api/v1/webhooks/telegram`
- **Security Check:** Every incoming webhook request from Telegram must include the `X-Telegram-Bot-Api-Secret-Token` header. This token is verified against a pre-shared environment secret (`TELEGRAM_WEBHOOK_SECRET`).
- **HMAC / Payload Integrity:** Requests failing secret validation are immediately dropped with HTTP `401 Unauthorized`.

---

## 2. Interactive Inline-Keyboard Approval Flow

### Notification Payload
When a short-form clip is rendered and queued for review, the worker sends a Telegram message with preview metadata:
- **Thumbnail / Video Preview:** Attached rendered MP4 or keyframe screenshot.
- **Caption:** Clip title, duration, source VOD ID, and candidate score.
- **Inline Keyboard:**
  - `[✅ Approve & Publish]` (Callback Data: `clip_approve:<job_id>`)
  - `[❌ Reject]` (Callback Data: `clip_reject:<job_id>`)

### Callback Query Handler (`/api/v1/webhooks/telegram`)
- Parses incoming `callback_query`.
- Verifies user authorization against a whitelist of admin Telegram User IDs (`ADMIN_TELEGRAM_IDS`).
- Updates the job status in the SQLite/SQLAlchemy database (`PUBLISHED` or `REJECTED`).
- Edits the Telegram message to indicate decision status (e.g., *"Approved by @user"*).
