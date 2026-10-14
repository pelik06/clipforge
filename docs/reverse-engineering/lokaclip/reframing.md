# LokaClip.pro — Reframing & Speaker Tracking Architecture

## 1. 9:16 SmartCrop Architecture
LokaClip brands its speaker-following framing engine as **9:16 SmartCrop**.
The documentation reveals an **on-device model of ~12 MB** downloaded once upon initial setup and accelerated via macOS Apple Neural Engine or Windows GPU/DirectML/ONNX.

---

## 2. 5-Step Speaker Following Pipeline

```text
[Video Frames] ──► Step 1: Face Detection & Spatial Seating
                         │
[Audio Track]  ──► Step 2: Voice Activity Detection (VAD)
                         │
                         ▼
                   Step 3: Lip Movement Correlation (Active Speaker Detection)
                         │
                         ▼
                   Step 4: Angle Change & Scene-Cut Snapping
                         │
                         ▼
                   Step 5: Layout Selection (9:16 Smart Pan vs Split-Screen)
```

### Step 1: Face Detection & Spatial Seating ("Kursi")
- Detects all human faces in each sampled video frame.
- Clusters detected faces across the video timeline into stable persistent "seats" (e.g., Seat 1 = left chair, Seat 2 = right chair).
- Prevents identity hopping and spurious bounding box drift.

### Step 2: Voice Activity Detection (VAD)
- Separates audio intervals containing human speech from background music, room noise, or game sound effects.

### Step 3: Lip Movement Correlation (Active Speaker)
- Measures facial landmark displacements around the mouth/lips across frames.
- Correlates lip motion against speech audio bursts to determine which seated subject is actively talking at any given second.

### Step 4: Angle Changes & Scene-Cut Snapping
- Integrates scene cut detection.
- When the video cuts to a different camera angle, the 9:16 crop window snaps abruptly at the exact cut frame rather than slowly panning across irrelevant pixels.

### Step 5: Split-Screen Automatic Fallback
- If two speakers are seated too far apart to fit inside a single 9:16 crop window (e.g., left 30% and right 70% of 16:9 frame), LokaClip automatically engages a **Stacked Split-Screen Layout** (top pane = Host, bottom pane = Guest) instead of cropping one person out.

---

## 3. Four Framing Layout Presets
1. **9:16 Fill:** Center-crop filling the vertical frame (fast, for single-speaker videos).
2. **9:16 Smart:** Active speaker following with multi-speaker split-screen capability.
3. **16:9 Fit (Black):** Full landscape video preserved with black letterboxing top and bottom.
4. **16:9 Fit (Blur):** Full landscape video preserved with blurred enlarged background.
