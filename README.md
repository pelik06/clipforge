# ClipForge

Streamer-first short-form clipping automation.

> **Important:** ClipForge is its own implementation. OpenShorts is treated as a reference for architecture/ideas, not as a runtime dependency.

## Current target

Build the smallest useful loop:

```text
Streamer VOD
   ↓
Ingest
   ↓
Transcription
   ↓
Signal Detection
   ↓
Candidate Windows
   ↓
Interestingness Scoring
   ↓
Clip Rendering
   ↓
QC
   ↓
Output + Manifest
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

## Security

Never commit:
- API keys
- cookies
- OAuth tokens
- platform credentials
- private VOD URLs
- `.env` files containing secrets

See `constitution.md` for project rules.
