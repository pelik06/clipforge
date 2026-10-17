# ClipForge

Streamer-first short-form clipping automation system with smart reframing, word-level captions, and human approval gates.

> **Architecture Note:** ClipForge studies proven open-source implementations (such as **OpenShorts** and **ai-clips-maker**) for algorithms and patterns (MediaPipe/YOLO tracking, Whisper alignment, ASS karaoke captions), while maintaining its own modular service implementation and independent runtime.

## Target Architecture

```text
Streamer VOD / YouTube URL / GDrive
   ↓
Ingest & Validation
   ↓
Transcription (faster-whisper / whisperX word-level)
   ↓
Signal & Scene Detection (PySceneDetect + Audio energy)
   ↓
Candidate Windows & LLM Virality Scoring
   ↓
Smart 9:16 Reframing (TRACK / SPLIT / GENERAL + EMA Tripod)
   ↓
Dynamic Captions (Programmatic .ass karaoke style)
   ↓
FFmpeg Rendering & QC
   ↓
Human Approval Gate (Telegram / Discord)
   ↓
Publishing / Campaign Adapters (Direct social or Clippo.id bounty flow)
```

## Repository layout

```text
clipforge/
├── apps/
│   ├── api/              # HTTP API / job entry point
│   └── worker/           # background processing
├── services/
│   ├── ingest/           # VOD ingestion + validation
│   ├── transcription/   # Whisper-compatible transcription
│   ├── detection/       # audio/scene/visual signals
│   ├── scoring/         # streamer moment ranking
│   ├── clipping/        # FFmpeg clip generation
│   ├── captions/        # caption generation/rendering
│   ├── reframing/       # vertical composition
│   ├── qc/              # quality checks
│   └── publishing/      # isolated platform adapters
├── core/
│   ├── models/          # shared data models
│   ├── config/          # configuration
│   └── utils/           # shared utilities
├── workflows/
│   ├── n8n/             # orchestration workflows
│   └── telegram/        # approval workflow definitions
├── data/
│   ├── input/           # source VODs
│   ├── work/            # temporary processing files
│   ├── output/          # final clips
│   └── archive/         # optional retained artifacts
├── tests/
├── docs/
├── scripts/
└── constitution.md
```

## Development philosophy

Do not implement everything at once.

Start with Phase 1:

1. local video input
2. transcription
3. candidate detection
4. scoring
5. FFmpeg rendering
6. manifest output

Then validate against real streamer VODs before adding automation.

## OpenShorts reference

The architecture can be informed by studying OpenShorts, but ClipForge should maintain its own interfaces and implementation.

Do not add OpenShorts as a dependency simply to avoid implementing a component.


## LLM Viral Hooks (9Router)

ClipForge generates viral Indonesian hook banners and social captions using 9Router (OpenAI-compatible router endpoint):

```bash
NINEROUTER_API_KEY=your_key_here
NINEROUTER_BASE_URL=https://api.9router.com/v1
NINEROUTER_MODEL=openai/gpt-4o-mini
```

If no key provided or request fails/times out, system falls back deterministically to local dialogue keyword extraction without crashing pipeline.
## Security

Never commit:
- API keys
- cookies
- OAuth tokens
- platform credentials
- private VOD URLs
- `.env` files containing secrets

See `constitution.md` for project rules.
