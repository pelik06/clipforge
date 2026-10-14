# LokaClip.pro — Moment Detection & Multi-Clip Strategy

## 1. Technical Claims vs Observed Implementation
LokaClip implements a two-stage hybrid approach:
- Stage 1: Fast multi-layered transcription (YouTube API fallback to on-device Whisper).
- Stage 2: Large Language Model (LLM) reasoning over the timestamped transcript.

### LLM Backends Revealed:
As confirmed in the settings documentation, LokaClip supports:
- **Google Gemini API**
- **Groq API** (Llama-3-70b / Mixtral for ultra-low latency transcript analysis)
- **LokaClip Cloud AI Server** (default hosted fallback for non-technical users, billed at ~1 token per video)

---

## 2. Moment Detection & Scoring Taxonomy
LokaClip structures moment evaluation around three primary narrative factors:

1. **HOOK (Opening 0–3s):**
   - Did the speaker begin with an intriguing premise, shocking fact, or polarizing statement that arrests viewer scrolling?
2. **EMOSI (Emotional Arc & Intensity):**
   - Does the segment contain an energetic debate, laughter, passion, or revelation?
3. **PAYOFF (Resolution & Value):**
   - Does the segment conclude with a punchline, lesson, conclusion, or satisfying finish rather than ending mid-sentence?

### Composite Score:
- Evaluated on a **1 to 10 viral potential score** (scaled to 0–100 in dashboard showcase badges, e.g., Hook: 92, Emosi: 88, Payoff: 84).
- The prompt instructs the model to preserve complete thought boundaries (hook, development, payoff).

---

## 3. Multi-Clip Parameters & Boundaries

LokaClip exposes explicit user-configurable clipping controls:

### 1. Clip Count:
- **Options:** **3, 5, or 7 clips** from a single source video.
- The user chooses how many top-ranking highlights to extract.

### 2. Target Duration:
- **Options:**
  - `45–60 detik` (Short, rapid retention)
  - `60–90 detik` (Standard short-form)
  - `90–120 detik` (Long-form explainer / TikTok 2-minute format)
- Duration constraints are enforced on the LLM prompt and adjusted against nearest sentence/word boundaries.

### 3. Content Type Presets:
- `Umum` (General)
- `Podcast` (Interview dialogue focus)
- `Gaming` (Relaxed transcript density thresholds, acoustic reaction focus)
- `Edukasi` (Informational density and clear explanation structure)

### 4. Deduplication & Non-Overlap:
- LLM prompt enforces temporal non-overlap between candidate moments.
- Minimum gap ensures distinct highlights across the video timeline rather than clustering around a single scene.
