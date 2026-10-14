# AutoClip.dev — Reframing & Tracking Architecture

## 1. Feature Specifications: SmartReframe
AutoClip brands its vertical reframing pipeline as **SmartReframe**:
- **Target Aspect Ratios:** 9:16 (primary vertical), 4:5 (Instagram portrait feed), 1:1 (square).
- **Core Promise:** "Resize any video for any platform and keep the moving subject centered with AI face and object tracking. Multi-speaker scenes get split layouts automatically."

---

## 2. Tracking & Subject Centering Pipeline

### Face & Object Detection:
- Detects the primary human subject or tracked object in landscape footage.
- Maintains the subject within the center horizontal 9:16 crop window across the duration of the cut.
- **Model Inferences:**
  - Fast single-shot face/person detector (e.g., YOLOv8-pose or MediaPipe Face/BlazeFace equivalent running in cloud worker GPU/CPU).
  - Subject persistence tracking assigns consistent track IDs to prevent rapid switching between background figures and the primary subject.

### Camera Movement & Smoothing:
- Applies trajectory smoothing (EMA or spline dampening) to eliminate frame jitter when speakers tilt their heads or lean.
- When an abrupt scene cut occurs in the source video, the camera cuts immediately without panning across irrelevant pixels.

---

## 3. Multi-Speaker & Split Layouts

### Auto-Split Detection:
In podcast, interview, or multi-subject footage where speakers are seated too far apart to fit in a single 9:16 vertical crop:
1. Detects two concurrent spatial clusters of faces/subjects.
2. Automatically engages a **Split Layout**:
   - Top frame: Speaker A (upper half)
   - Bottom frame: Speaker B (lower half)
3. Preserves aspect ratio with letterboxing/cropping tailored per split pane.

### Manual Override:
The web dashboard provides a tracker manual takeover control allowing users to specify:
- Layout mode: `Fill` vs `Split`
- Track state: `Track: ON` vs manual fixed crop anchor.
