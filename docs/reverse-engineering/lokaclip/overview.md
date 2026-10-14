# LokaClip.pro — Architecture & System Overview

## 1. Product Summary
LokaClip (`https://lokaclip.pro/`) is an Indonesian-origin desktop video clipping software tailored for content creators and YouTubers.

- **Core Value Proposition:** "AI Clipper Desktop Teringan — Sekali bayar, render unlimited langsung di laptop."
- **Core Architectural Thesis:** **"Dua fase yang terpisah tegas"** (Strict separation of thinking vs rendering):
  1. **Fase 1: Berpikir (AI Highlight Analysis):** Requires cloud/internet. Whisper + LLM (Gemini / Groq) scans transcripts to score viral moments (Hook, Emosi, Payoff). Paid via cloud AI tokens or free via Bring-Your-Own-Key (BYOK).
  2. **Fase 2: Merender (Local Processing):** Runs 100% locally on the user's laptop using native **Rust + FFmpeg**. Video never leaves the machine, rendering is zero-cloud-cost, unwatermarked, and accelerated by local hardware encoders (NVENC, Apple VideoToolbox, Intel QSV).

---

## 2. Ingestion & Pipeline Topology
```text
Video Ingest (Local File Drag & Drop OR YouTube URL)
  │
  ▼
4-Layer Escalating Transcript Ingestion
  ├─ Layer 1: Direct YouTube manual caption API
  ├─ Layer 2: YouTube automatic caption API
  ├─ Layer 3: On-Device local Whisper transcription (no audio leaves machine)
  └─ Layer 4: Fallback / Cookies manual injection for bot prevention
  │
  ▼
Fase 1: Cloud/BYOK AI Analysis (Berpikir)
  ├─ Cloud LLM / Local User API Key (Gemini, Groq)
  ├─ Quality threshold per genre (Relaxed for Gaming, strict for Educational/Podcast)
  ├─ Moment scoring: Hook, Emosi, Payoff (Composite 1–10 viral potential score)
  └─ Selects candidate set: 3, 5, or 7 clips (target duration: 45–60s, 60–90s, or 90–120s)
  │
  ▼
Fase 2: 6-Stage Local Native Rendering (Rust + FFmpeg)
  ├─ Stage 1: Unduh (YouTube download via yt-dlp/native; skips if local file)
  ├─ Stage 2: Potong (Precise boundary trimming at nearest word/scene mark)
  ├─ Stage 3: Framing (9:16 SmartCrop: Face detection, Voice activity, Lip sync matching, Split-screen)
  ├─ Stage 4: Subtitle (Word-synced dynamic captions: TikTok Viral, Classic Karaoke, Minimalist, Word Pop)
  ├─ Stage 5: Watermark (Intro hook text in first 0–3s, user logo watermark)
  └─ Stage 6: Finalisasi (Hardware-accelerated encode via NVENC/VideoToolbox/QSV to 1080x1920 MP4)
```

---

## 3. Desktop vs Cloud Distinction
- **LokaClip Desktop (Current Active Product):**
  - Downloadable native client for Windows 10/11 and macOS 12+ (Universal / Apple Silicon Neural Engine accelerated).
  - Software license: One-time payment (Rp 250.000 Plus / Rp 350.000 Pro).
  - Rendering: 100% offline, local FFmpeg, unlimited minutes, zero watermark.
- **LokaClip Cloud (Roadmap / Future):**
  - Explicitly marked under roadmap as "Sedang dikerjakan / Belum tersedia hari ini" along with Smart Trim and Enhance Audio.
