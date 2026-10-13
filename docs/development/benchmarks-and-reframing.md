# ClipForge Phase 1: Algorithm Benchmarks & Memory Footprint Specs

This document outlines the reference algorithm specifications, performance benchmarks, and strict resource/memory regression thresholds for Phase 1 of **ClipForge**.

---

## 1. Transcription & Alignment (`faster-whisper` / `whisperX`)

### Algorithm & Invariants
- **Engine:** `faster-whisper` (CTranslate2 backend) utilizing `large-v3` or `medium.en` models.
- **Word-level Timestamps:** Computed via attention weight projection and Viterbi alignment / cross-entropy alignment.
- **Precision:** FP16 on GPU (CUDA) or INT8 on CPU.

### Performance & Memory Footprint Specs (Regression Thresholds)
| Model Size | RAM/VRAM Footprint (Idle / Active) | Processing Speed (1hr 1080p60 VOD) | Target Word Alignment Drift |
| :--- | :--- | :--- | :--- |
| **`medium.en` (INT8)** | ~1.2 GB / ~1.8 GB | ~4.5x realtime | < 50ms |
| **`large-v3` (FP16)** | ~3.0 GB / ~4.8 GB | ~1.8x realtime | < 25ms |

- **Hard Regression Threshold:** Maximum peak VRAM/RAM allocation during inference must not exceed **5.5 GB** for `large-v3` (FP16). Subprocess workers exceeding this are terminated by supervisor guardrails.

---

## 2. Visual Detection & Reframing (`MediaPipe` + EMA Tripod Logic)

### Algorithm & Invariants
- **Scene Detection:** PySceneDetect (ContentDetector) with adaptive thresholding (`threshold=27.0`).
- **Face / Object Tracking:** MediaPipe Tasks Vision (Face Detector / BlazeFace or Objectron) running at 30 FPS subsampled from 60 FPS input.
- **Smoothing / Reframing:** Exponential Moving Average (EMA) tripod smoothing to eliminate jitter during rapid pan/zoom adjustments (smoothing factor $\alpha = 0.15$).

### Performance & Memory Footprint Specs (Regression Thresholds)
| Component | RAM Footprint | CPU/GPU Utilization | Latency per Frame |
| :--- | :--- | :--- | :--- |
| **PySceneDetect** | ~150 MB - 300 MB | Single core bound (~80% on 1 core) | < 5ms / frame |
| **MediaPipe Tracking** | ~400 MB - 600 MB | GPU/CPU hybrid (~25% GPU) | < 18ms / frame |

- **Hard Regression Threshold:** Combined detection and MediaPipe tracking memory footprint must remain under **1.0 GB** per worker process. EMA tripod smoothing latency overhead must stay under **2ms** per frame.

---

## 3. Candidate Window Scoring & Audio Energy
- **Audio Energy VAD:** RMS energy computation using 50ms sliding windows.
- **Scoring Weights:**
  - Audio Energy Peak: 40%
  - Scene Change Proximity: 30%
  - Transcript Keyword Density / LLM Salience: 30%
