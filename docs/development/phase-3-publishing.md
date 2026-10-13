# ClipForge Phase 3: Publishing & Campaign Adapters Specs

This document outlines the architecture and security controls for Phase 3 publishing adapters in **ClipForge**, including YouTube Shorts, TikTok, and Instagram Reels integration.

## 1. Publishing Isolation & Adapters
- Publishing adapters connect approved clips to target platforms (e.g., YouTube Shorts, TikTok, Instagram Reels, or Clippo.id bounty program).
- Each adapter runs in an isolated subprocess with restricted network permissions and dedicated credential mounts, featuring exponential backoff rate limiting.

## 2. Security & Compliance
- **No plaintext secrets:** API keys and OAuth tokens are injected via secure vault/env variables at runtime.
- **Explicit Human Approval Required:** Zero auto-publishing without prior sign-off from the Telegram approval gate.
