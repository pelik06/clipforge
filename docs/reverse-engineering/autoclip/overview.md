# AutoClip.dev — Architecture & System Overview

## 1. Product Summary
AutoClip (`https://autoclip.dev/`) is a cloud-based SaaS platform engineered for automated long-form to short-form video generation and social media distribution (TikTok, Instagram Reels, YouTube Shorts).

- **Core Proposition:** "Paste a link, get 10 viral clips, auto-posted."
- **Stack & Architecture:**
  - **Frontend:** Next.js (Turbopack, App Router, React Server Components Flight protocol).
  - **Auth & Session:** Clerk (`clerk.autoclip.dev`) with JWT session cookies and client handoff tokens (`autoclip:clip-handoff`).
  - **Analytics & Telemetry:** PostHog (`homepage_url_submitted`, `homepage_upload_clicked`, etc.) and Sentry (`sentry-environment=production`).
  - **Backend Operations:** Next.js Server Actions (`x-action-redirect`, `Accept: text/x-component`) bridging into backend video processing microservices and Whop billing integration.
  - **Processing Topology:** 100% Cloud-rendered pipeline (users submit URLs or files; clips render remotely on cloud workers in ~2 minutes per clip).

## 2. Ingestion & Pipeline Topology
```text
Source URL / Upload (YouTube, Vimeo, Rumble, Loom, Twitch, Kick, MP4/MOV)
  │
  ▼
Client Handoff Validation (base64url payload with platform, intent, source)
  │
  ▼
Cloud Ingestion Worker
  ├─ Stream VODs: Pre-filters broadcast, extracts top highlight segments (1 credit per 20 min)
  └─ Standard VODs: 1 credit per source minute
  │
  ▼
Two-Pass Multimodal Analysis & Acoustic Profiling (ViralScan)
  ├─ Pass 1: Audio Signal Extraction (YAMNet reactions, RMS peaks, speech pace, music transitions)
  └─ Pass 2: Multimodal Text/Vision Alignment & 5-Factor Virality Scoring
  │
  ▼
Moment Selection & Variant Generation
  ├─ Tight Cut (high retention, hook-focused)
  └─ Extended Cut (wider explanatory context)
  │
  ▼
SmartReframe 9:16 Pipeline
  ├─ Subject centering via AI Face & Object Tracking
  └─ Multi-speaker scene auto-split layout
  │
  ▼
Caption Synthesis & Burn-in
  ├─ Production-grade Speech-to-Text transcription
  ├─ Word-level timestamp synchronization
  ├─ Web Editor Preview: Dynamic CSS @keyframes DOM injection on 4-word spans
  └─ Server Export: Hardsubbed FFmpeg video burn-in
  │
  ▼
Distribution & Auto-Posting (TikTok, IG Reels, YouTube Shorts, Content Calendar)
```

## 3. High-Level Characteristics
- **Multi-Clip Output:** Produces 6 to 10 clips per video (Starter plan caps at 6 clips/video, Pro/Scale produce up to 10 clips/video).
- **Processing Time:** ~2 minutes per clip on cloud infrastructure.
- **Billing Metric:** Source-minute credits (1 credit = 1 source minute; Twitch/Kick streams discounted via pre-filtering heuristic).
