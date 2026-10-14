# LokaClip.pro — Network & API Flow Analysis

## 1. Web Portal Network Scope
The web application hosted at `https://lokaclip.pro/` is **not a web-based video processing SaaS**. The web frontend functions purely as an account dashboard, license purchase portal, installer distribution system, and AI Token quota manager.

### Discovered Web API Routes:
```text
/api/auth/me                -> Session user identity
/api/auth/login             -> User authentication
/api/auth/register          -> User registration
/api/auth/verify-otp        -> Email verification OTP
/api/auth/resend-otp        -> Resend verification OTP
/api/auth/forgot-password   -> Password reset flow
/api/auth/verify-reset-otp  -> Password reset OTP verification
/api/auth/reset-password    -> Set new password
/api/auth/logout            -> Terminate web session
/api/pricing                -> Pricing plans & currency rates
/api/pricing/me             -> Current user license status
/api/stats                  -> Aggregated platform metrics
```

---

## 2. Desktop Application Network Patterns

The desktop application operates under a split-network model:

```text
[LokaClip Desktop App]
   │
   ├─► [Licensing / Update API]: https://lokaclip.pro/api/...
   │     - Validates license code on initial setup
   │     - Verifies AI Token quota balance
   │     - Fetches auto-update binaries
   │
   ├─► [YouTube API / Ingest]:
   │     - Fetches YouTube captions (if URL source)
   │     - Uses manual cookies if bot check triggered
   │
   ├─► [AI Highlight API (Fase 1)]:
   │     - Mode A: LokaClip Cloud AI Server (consumes 1 Token per analyzed video)
   │     - Mode B: Direct BYOK (User supplies own Google Gemini or Groq API Key)
   │       * Sends timestamped transcript text only
   │       * Video/audio media is NEVER transmitted to AI endpoint
   │       * Returns JSON with selected moment boundaries and scores
   │
   └─► [Fase 2: Rendering]:
         - 100% OFFLINE (ZERO network traffic during rendering)
```

---

## 3. Security & Privacy Findings
- **Zero Video Egress:** Video files (often 1–5 GB) never upload to LokaClip servers during local desktop processing.
- **BYOK Credential Security:** Confirmed by official docs: user API keys (Gemini / Groq) are stored locally in the desktop app configuration and never proxied through LokaClip servers.
- **Installer Safety & Code Signing:** Windows installer executable is digitally signed; Windows Defender SmartScreen warning guidance is documented in `/download` and `/faq`.
