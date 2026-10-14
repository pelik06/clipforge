# LokaClip.pro — Caption Reverse Engineering

## 1. Caption Generation & Multi-Tier Ingestion
To maintain zero cloud cost and resilience against missing captions, LokaClip employs **4 escalating transcript layers**:

1. **Layer 1:** Direct YouTube official manual captions (fastest, lossless punctuation).
2. **Layer 2:** YouTube automated captions (fallback if manual subtitles missing).
3. **Layer 3:** **On-Device Whisper AI transcription** running locally on user's machine (CPU / GPU / Apple Neural Engine; zero external data transmission).
4. **Layer 4:** Manual cookie header injection (to bypass YouTube bot verification on protected videos).

---

## 2. Word-Level Timing & Reveal Modes
LokaClip supports word-level synchronized timing extracted either from Whisper word timestamps (`word_timestamps=True`) or YouTube ASR word offsets.

It provides **4 Reveal Modes (Mode Kemunculan):**
1. **Per Kata (Word-by-word):** Only the active word appears on screen at its exact timestamp.
2. **Karaoke Sweep (Word-level Highlight):** The full phrase is visible in dim/base color; as each word is spoken, it highlights into active color with scale/pop animation.
3. **Kumulatif (Cumulative):** Words accumulate sequentially across the line as spoken until the phrase completes.
4. **Statis per Kalimat (Static sentence):** Entire sentence stays on screen during its time interval without kinetic animation.

---

## 3. Presets & Styling Capabilities

LokaClip ships with **4 Built-in Presets:**
1. **TikTok Viral:** Bold display typography, accent yellow/green background tag (`bg-accent text-accent-fg`), kinetic scale (1.06x), and slight rotation (-1.5 deg).
2. **Classic Karaoke:** High-contrast outlined text with active word sweep highlighting.
3. **Minimalist:** Clean sans-serif font, subtle lower-third positioning, minimal glow/stroke.
4. **Word Pop:** Kinetic pop animation on word arrival with bouncy cubic-bezier transition.

### Customization Dimensions:
- **Font:** User can choose local system fonts or included styles.
- **Color & Alpha:** Primary text color, outline color, highlight accent color.
- **Dimensions & Box:** Outline stroke thickness, text box width, line height.
- **Position & Safe Zones:** Free-drag positioning on the 9:16 canvas with safe zone margins protecting UI overlays (TikTok like/comment buttons).
- **Timing Adjustment:** Micro-nudge slider allowing users to advance or delay subtitle synchronization if audio has latency.

---

## 4. Local Rendering Implementation
Subtitles are rendered locally on the user's laptop using **FFmpeg libass subtitle filter** (`-vf ass=...`).
- Advanced SubStation Alpha (`.ass`) files are compiled on the fly by the Rust backend.
- Word timestamps are mapped directly to ASS dialogue events with override tags (`{\k...}` or color tags `{\c&H...&}`).
- Hardware encoders (NVENC / VideoToolbox) burn the subtitles without requiring CPU-bound frame dumping.
