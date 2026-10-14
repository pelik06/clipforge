# AutoClip.dev — Network & API Flow Analysis

## 1. Network Topology & Request Patterns
AutoClip does not expose public legacy REST endpoints like `/api/v1/jobs` on the client bundle. Instead, it utilizes **Next.js App Router Server Actions** communicating over the React Server Component (RSC) Flight protocol, alongside Clerk Auth endpoints and PostHog analytics ingestion.

### Observed Network Architecture:
- **Client Framework:** Next.js with Turbopack bundler.
- **Protocol:** HTTP/2 over TLS with streaming RSC payloads (`Accept: text/x-component`).
- **Auth Provider:** Clerk JS CDN (`https://clerk.autoclip.dev/npm/@clerk/clerk-js@6/dist/clerk.browser.js`).
- **Telemetry Endpoints:** PostHog custom ingest (`capture('homepage_url_submitted')`).

---

## 2. Ingestion & Handoff Request Flow

### Step 1: URL Validation & Client Handoff Generation
When a user pastes a link into the hero input (`input[name="url"]`), client module `567848` executes regex-based hostname and protocol checks:
- **Supported Platforms:**
  - `youtube.com`, `youtu.be`, `music.youtube.com`, `m.youtube.com` (matching `/watch`, `/shorts`, `/live`, `/embed`)
  - `twitch.tv`, `m.twitch.tv`
  - `kick.com`
  - Direct video files (`.mp4`, `.mov`)
  - Vimeo, Loom, Rumble

### Step 2: Base64URL State Serialization
The client packages an intent payload:
```json
{
  "v": 1,
  "url": "https://www.youtube.com/watch?v=...",
  "platform": "youtube",
  "mode": "url",
  "source": "homepage-hero"
}
```
This JSON is encoded into URL-safe Base64 (`replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')`).

### Step 3: Local Storage & Routing
- If the user is unauthenticated:
  - Stores token into `localStorage.setItem("autoclip:clip-handoff", base64Payload)`.
  - Pushes route: `/sign-up?redirect_url=${encodeURIComponent('/dashboard/submit?handoff=' + base64Payload)}`.
- If user is authenticated:
  - Pushes route: `/dashboard/submit?handoff=${base64Payload}`.

---

## 3. Server Action Execution (Job Creation)

Upon entering the dashboard, the submission triggers a Next.js Server Action:
```http
POST /dashboard/submit HTTP/2
Host: autoclip.dev
Accept: text/x-component
Next-Action: <action_hash_id>
Next-Router-State-Tree: [...]
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...
Cookie: __session=<clerk_jwt>; ac_theme=...

[RSC Form Payload containing handoff token, platform, clip count target, and template preferences]
```

### Response Pattern:
```http
HTTP/2 200 OK
Content-Type: text/x-component
x-action-redirect: /dashboard/jobs/<jobId>;push

1:{"b":"$@2","c":"job_queued","jobId":"j97...","status":"processing"}
```
- **Job Status Tracking:** Utilizes Next.js RSC Flight streaming or polling at `/dashboard/jobs/<jobId>`.
- **Completion Response:** Delivers an array of generated clips with metadata:
  ```json
  {
    "clipId": "j97ah9yrzkn7srmhzhtfrv4rx58d2nhc",
    "slug": "1vmtorf2c0",
    "aspect": "9:16",
    "layout": "fill",
    "viralityScore": 89,
    "durationSec": 10,
    "sourceVideoId": "6ztvMAzFP24",
    "sourceTitle": "...",
    "sourceDurationSec": 1230,
    "words": [
      { "w": "god", "s": 0.0, "e": 0.32 },
      { "w": "this", "s": 0.34, "e": 0.58 }
    ]
  }
  ```

---

## 4. Render & Asset Endpoints
- **Video Streams / CDNs:** Previews stream `.mp4` slices and posters from cloud object storage (e.g., S3/Cloudflare R2 behind CDN).
- **Hardsubbed Rendering:** Done server-side during processing prior to delivering post-ready MP4 files for download or auto-posting to connected TikTok/Instagram/YouTube accounts.
