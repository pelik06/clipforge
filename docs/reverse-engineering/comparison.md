# Multi-Product Architecture Comparison & Gap Analysis
### AutoClip.dev vs LokaClip.pro vs OpenShorts vs ClipForge

---

## 1. Feature Comparison Matrix

| Feature | AutoClip.dev | LokaClip.pro | OpenShorts (Ref) | ClipForge (Current) |
|---|---|---|---|---|
| **Deployment Model** | 100% Cloud SaaS | Desktop App (Rust + FFmpeg) + Cloud/BYOK AI | Local Python CLI / WebUI | Local FastAPI + Next.js + Python Workers |
| **Full Video Analysis** | Yes (Cloud worker) | Yes (Local extract + Cloud LLM) | Yes (Local Python) | Yes (`NonLLMMomentDetector` full timeline scan) |
| **Transcription Engine** | Production Cloud ASR | 4-Tier: YouTube API -> Local Whisper | `faster-whisper` / `whisperX` | `faster-whisper` (16kHz float32 FFmpeg decode) |
| **Word Timestamps** | Yes (`{w, s, e}` array) | Yes (Whisper / YouTube ASR) | Yes (Whisper word alignment) | Yes (`Word(text, start, end)`) |
| **Moment Detection** | Two-pass Multimodal AI + YAMNet Audio | Whisper transcript + LLM (Gemini/Groq) | Acoustic envelope + Transcript LLM | Non-LLM Multi-Signal (RMS energy, peak, motion, face, regex hooks) + LLM selector |
| **Multi-Moment Extraction** | Yes (Top highlights scanned across video) | Yes (3, 5, or 7 clips per video) | Yes (Prompt specifies $N$ viral moments) | Yes (NMS deduplication, finds all peaks above threshold) |
| **Clip Count** | 6 (Starter) to 10 (Pro/Scale) | 3, 5, or 7 (User option) | Variable ($N$ in prompt, default 3–5) | Dynamic (0 to $N$, configurable max_clips=15) |
| **Moment Scoring** | 5 Criteria (100 pts max): Hook, Emotion, Info, Share, Replay | 3 Narrative Pillars (1–10 / 100 pts): Hook, Emosi, Payoff | Viral Score 0–100 via LLM prompt | 0.0–1.0 Composite Score (RMS, peak, motion, scenes, face, completeness, hook regex) |
| **Scene Detection** | Yes (Scene-cut boundary snapping) | Yes (Angle-change snap in framing) | PySceneDetect (HSV histogram) | HSV luminance/color histogram difference (`scene.py`) |
| **Audio Scoring** | YAMNet (Laughter/Applause), RMS energy, Speech rate | VAD (Voice Activity Detection vs Noise) | RMS volume energy curve | Continuous RMS volume + Peak audio array |
| **Face Tracking** | AI Face & Object Tracking (Cloud) | Face Detection + Persistent "Seating" (~12 MB ONNX) | MediaPipe Face Detection | OpenCV YuNet ONNX (`cv2.FaceDetectorYN`) at 4 fps |
| **Active Speaker Detection** | Spatial tracking / Centering | Audio VAD + Mouth/Lip Movement Correlation | General Face Following / Tracker Mode | In development (`active_speaker_available=False`, falls back to primary face persistence) |
| **Object Tracking** | Yes (Object tracker for sports/gaming) | No (Focus on human faces/speakers) | YOLOv8 fallback for subjects | No (Face-only currently) |
| **9:16 Reframe** | SmartReframe (Fill, Split, 4:5, 1:1) | SmartCrop (9:16 Fill, 9:16 Smart, Fit Black, Fit Blur) | 9:16 Crop with EMA camera smoothing | 9:16 Crop with EMA smoothing + downsampled FFmpeg filter |
| **Multi-Speaker Layout** | Auto Split Layout (Top/Bottom) | Auto Stacked Split-Screen (when speakers far apart) | Multi-Mode (`TRACK`, `SPLIT`, `GENERAL`) | Single primary speaker tracking only (No split-screen yet) |
| **Caption Styles** | 6 Presets (`karaoke`, `beasty`, `deep_diver`, `pod_p`, `youshaei`, `mozi`) | 4 Presets (`TikTok Viral`, `Classic Karaoke`, `Minimalist`, `Word Pop`) | ASS Karaoke with `\k` tags | ASS Karaoke with `{\c&H...&}` word-level highlight |
| **Caption Reveal Modes** | 4-word chunked CSS animation / hardsub | 4 Modes: Per Kata, Karaoke Sweep, Kumulatif, Statis | Karaoke timing sweep | Word-level highlight sweep (active word colored, base text colored) |
| **Caption Burn-in** | FFmpeg Hardsub | FFmpeg libass local burn-in | FFmpeg libass filter | FFmpeg libass filter (`-vf ass=...`) |
| **Rendering Backend** | Cloud FFmpeg workers | Local Rust + FFmpeg with 5 Hardware Encoders | Local Python + FFmpeg | Local Python + FFmpeg CLI subprocess |

---

## 2. In-Depth Architectural Mechanics

### A. Moment Detection
- **AutoClip:** Relies on **multimodal and acoustic signal analysis**. By using YAMNet for laughter and applause detection alongside RMS audio intensity and speech velocity, it can detect high-engagement moments in gaming and sports where dialogue is sparse.
- **LokaClip:** Relies heavily on **linguistic/narrative analysis via LLM** (Gemini / Groq) over the transcript. It evaluates three pillars: Hook (arresting opening), Emosi (intensity of discussion), and Payoff (conclusive resolution).
- **ClipForge:** Uses a **non-LLM multi-signal analyzer** (RMS audio energy, peak audio, frame difference motion, face detection activity, regex hook patterns, sentence completeness) that outputs continuous sliding window signals, with an optional LLM selector prompt.

### B. Multi-Clip Count Determination
- **AutoClip:** Plan-governed ceiling (6 clips on Starter, 10 clips on Pro/Scale). It finds all high-scoring moments, ranks them descending, and selects the top clips up to the plan limit.
- **LokaClip:** Explicit user parameter (3, 5, or 7 clips). It instructs the LLM prompt to select exactly $N$ moments meeting the duration constraints.
- **ClipForge:** Dynamic non-LLM detection extracts all peaks exceeding the `moment_threshold` (e.g. 0.65), capped at `max_clips` (default 15).

### C. Clip Boundary Alignment
- **AutoClip:** Generates **two variants per moment** (Tight Cut for fast feed retention, Extended Cut for broader context). Snaps boundaries to word start/end and scene cuts.
- **LokaClip:** Prompts the LLM for target duration ranges (45–60s, 60–90s, 90–120s), and snaps boundaries to nearest sentence/word timestamps and scene cut transitions.
- **ClipForge:** Expands around peak windows (context -> development -> payoff), snaps start/end to nearest Whisper word boundaries, and aligns with adjacent scene cuts and silence intervals.

### D. Caption Generation & Timing
- **AutoClip:** Chunks word arrays into fixed **4-word segments**. Browser preview uses dynamic CSS `@keyframes` on `<span>` tags; server export burns hardsubs via FFmpeg.
- **LokaClip:** Supports 4 distinct reveal paradigms (Per kata, Karaoke sweep, Kumulatif, Statis) compiled into Advanced SubStation Alpha (`.ass`) and burned locally via FFmpeg.
- **ClipForge:** Generates `.ass` subtitles with word-level highlight color overrides (`{\c&H00highlight&}word{\c&H00text&}`), adjusting relative timestamps for trimmed clips.

### E. 9:16 Reframing & Speaker Selection
- **AutoClip:** AI face and object tracking with automatic split-screen layout for multi-speaker scenes.
- **LokaClip:** 5-step pipeline: (1) Persistent face seating, (2) Voice activity detection, (3) Mouth/lip movement correlation, (4) Angle-cut snapping, (5) Stacked split-screen if subjects are far apart.
- **ClipForge:** OpenCV YuNet ONNX face detector sampled at 4 fps, single primary track ID selected by bounding box area and persistence, EMA smoothing, downsampled to $\le 24$ keypoints to avoid FFmpeg parser recursion overflow (error -22). No lip-sync or split-screen layout yet.

### F. Ranking & Scoring
- **AutoClip:** 100-point composite score: Hook (20) + Emotion (20) + Info Density (20) + Shareability (20) + Replay Value (20).
- **LokaClip:** 1–10 viral potential score based on Hook, Emosi, and Payoff completeness.
- **ClipForge:** Normalized weighted sum of 10 acoustic, visual, and linguistic feature signals.

### G. Deduplication
- **AutoClip:** Suppresses duplicate clips across overlapping time intervals; offers Tight and Extended variants for the top moments.
- **LokaClip:** Prompt-based non-overlap constraints with minimum temporal gap between selected clips.
- **ClipForge:** Temporal Non-Maximum Suppression (NMS) with `max_overlap_ratio=0.35`.

---

## 3. Gap Analysis for ClipForge

### What AutoClip Has That ClipForge Lacks:
1. **Audio Reaction Classifier (YAMNet):** AutoClip classifies audience laughter and applause via YAMNet, which drastically improves highlight detection in podcasts and gaming streams.
2. **Dual-Variant Output (Tight vs Extended Cut):** Generating both a 30s punchy cut and a 60s full-context cut for top highlights gives creators platform flexibility.
3. **Multi-Speaker Split Layout:** When two speakers are visible across a wide frame, AutoClip stacks them top-and-bottom.
4. **4-Word Caption Chunking:** AutoClip groups captions into neat 4-word lines rather than full sentences, keeping captions centered and readable on vertical video.

### What LokaClip Has That ClipForge Lacks or Has Partially:
1. **Active Speaker Identification via Lip-Sync / Mouth Motion:** LokaClip measures lip movement and correlates with speech to know which seated face is speaking. ClipForge currently tracks only the largest/most persistent face.
2. **Persistent Face "Seating":** LokaClip maps subjects to fixed spatial seats across the video to avoid identity swapping.
3. **Scene-Cut Snapping in Reframing:** When camera angle cuts, LokaClip cuts the crop instantly rather than smoothing/panning across the transition.
4. **4 Subtitle Reveal Modes:** ClipForge has word highlight, but lacks cumulative, pure single-word pop, and static modes.
5. **BYOK (Bring Your Own Key) Support:** Allows users to input their own Gemini or Groq API key for zero-cost cloud LLM reasoning.

### What OpenShorts Has That ClipForge Implements Differently:
1. **MediaPipe / YOLOv8 Tracking:** OpenShorts uses MediaPipe / YOLO for pose and person tracking; ClipForge uses a ultra-lightweight ONNX YuNet model (`face_detection_yunet_2023mar.onnx`, ~232 KB) compiled natively into FFmpeg crop expressions.
2. **LLM-Centric vs Signal-Centric Detection:** OpenShorts relies primarily on sending full transcripts to LLMs; ClipForge features a dedicated non-LLM multi-signal engine that works 100% offline without requiring LLM tokens.

---

## 4. Implementation Priorities for ClipForge

```text
Priority Ranking:
├── P0 — Critical (Core Architecture Stability & Multiple Output Contract)
│   ├── 1. End-to-End Multi-Clip Orchestration (1 video -> N valid vertical MP4s with captions)
│   ├── 2. Robust Word-Level Caption Chunking (3–4 words per line, safe-zone positioning)
│   ├── 3. Subtitle Timeline Relative Offset Verification
│   ├── 4. Scene-Cut Aware Reframing (Instant cut on scene boundary, smooth EMA within scenes)
│   └── 5. Stable Face Track Persistence (Prevent identity swapping across frames)
│
├── P1 — High Value (Competitive Differentiation)
│   ├── 6. Active Speaker Detection (Correlate audio energy / VAD with mouth ROI movement)
│   ├── 7. Multi-Speaker Split Layout (Stack two speakers top/bottom for podcasts/interviews)
│   ├── 8. Audio Reaction Classifier (YAMNet laughter & applause detection)
│   ├── 9. Tight vs Extended Cut Variant Generation for Top Highlights
│   └── 10. Bring-Your-Own-Key (BYOK) Gemini / Groq Provider Support
│
└── P2 — Future Polish (Post-P0/P1)
    ├── 11. B-roll overlay insertion
    ├── 12. Audio enhancement (DeepFilterNet / noise suppression)
    ├── 13. Auto-posting social integrations
    └── 14. Silence / filler word removal (Smart Trim)
```

---

## 5. Architectural Recommendations for ClipForge

### Features to Adopt Immediately:
- **Scene-Cut Snapping in Reframing:** Inspect `scenes` list during trajectory computation. If frame $t$ crosses a scene cut, reset the crop window instantly to the new primary face instead of interpolating camera position across the cut.
- **4-Word Caption Chunking:** Update caption generator to split sentences into 3–4 word dialogue lines. This eliminates overflowing subtitles on 9:16 mobile displays.
- **End-to-End Multi-Clip Pipeline:** Wire `NonLLMMomentDetector` directly into `apps/worker/pipeline.py` so a single source video automatically renders all top $N$ candidate clips into separate vertical MP4s with burnt-in captions.

### Features to Avoid / Discard (YAGNI):
- **Cloud-Only Web Rendering:** Avoid AutoClip's server-side-only bottleneck. ClipForge's local FFmpeg approach (matching LokaClip and OpenShorts) eliminates massive cloud bandwidth and server rendering bills.
- **Overly Complex LLM Orchestration for Simple Videos:** Do not force LLM execution when ClipForge's `NonLLMMomentDetector` can extract high-energy moments offline in seconds. Keep LLM as an optional enhancer.

### Features Unproven / Requiring Further Validation:
- **Pure "Lip-Reading" Models:** Marketing claims often overstate active speaker accuracy. Correlating simple mouth bounding box variance with audio VAD is significantly lighter, more robust, and easier to maintain than full 3D lip-reading neural networks.
