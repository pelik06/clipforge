# Architecture Overview

## Boundary

n8n is an external orchestrator.

ClipForge owns the media intelligence pipeline.

## Reference Patterns & Technology Stack

ClipForge adopts proven architectural patterns from open-source references (**OpenShorts** and **ai-clips-maker**):
- **Reframing:** MediaPipe / YOLOv8 face tracking with Exponential Moving Average (EMA) camera stabilization (`TRACK`, `SPLIT`, `GENERAL` modes).
- **Transcription:** `faster-whisper` / `whisperX` with word-level timestamps.
- **Captions:** Programmatic Advanced SubStation Alpha (`.ass`) karaoke-style dynamic subtitles burned via FFmpeg.
- **Intelligence:** Hybrid scoring combining acoustic/visual signals with LLM hook/retention extraction.

## Processing flow

1. Ingest (Local VOD, YouTube URL, GDrive)
2. Validate
3. Transcribe (faster-whisper word-level)
4. Detect signals & scenes (PySceneDetect + Audio energy)
5. Build candidate windows & LLM scoring
6. Smart 9:16 reframing & layout selection (`TRACK`, `SPLIT`, `GENERAL`)
7. Burn-in dynamic ASS captions (karaoke style)
8. FFmpeg render & automated QC
9. Human approval gate (Telegram / Discord)
10. Publish / Bounty submission (Direct social or Clippo.id flow)

## Design rule

Each stage should have a clear input/output contract so components can be replaced independently.
