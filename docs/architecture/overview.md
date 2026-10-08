# Architecture Overview

## Boundary

n8n is an external orchestrator.

ClipForge owns the media intelligence pipeline.

## Processing flow

1. Ingest
2. Validate
3. Transcribe
4. Detect signals
5. Build candidate windows
6. Score candidates
7. Render clips
8. Caption/reframe
9. QC
10. Human approval
11. Publish

## Design rule

Each stage should have a clear input/output contract so components can be replaced independently.
