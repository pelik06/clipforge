# ClipForge Phase 4: Web Dashboard & Clippo.id Integration Specs

This document outlines the architecture, frontend dashboard design, and external task synchronization specifications for **ClipForge Phase 4**.

---

## 1. Web Dashboard & In-Browser Review Workflow

### Architecture
- **Static Hosting:** FastAPI serves static HTML/JS from `apps/api/static/` at the root `/` endpoint.
- **UI Framework:** Tailwind CSS & Lucide icons via CDN for a modern, responsive operator panel.
- **Workflow:**
  1. Operator submits a VOD download link or YouTube URL via the dashboard input form (`POST /api/v4/jobs`).
  2. Live job status and progress are polled via `GET /api/v4/jobs`.
  3. Completed clips render in an interactive review grid with embedded video players and `Approve`/`Reject` action buttons (`POST /api/v4/jobs/{id}/decision`).

---

## 2. Clippo.id Integration & Automated Sync

### Endpoint Specification
- **Endpoint:** `POST /api/v4/clippo/sync`
- **Behavior:** Polls or receives webhooks from `https://clippo.id/` to discover requested streamer clipping tasks. Automatically provisions and queues job processing in ClipForge.
