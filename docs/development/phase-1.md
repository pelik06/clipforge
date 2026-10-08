# Phase 1 Development

## Goal

Process one local streamer VOD and produce ranked clip candidates plus rendered clips.

## Milestones

- [ ] Verify FFmpeg / FFprobe
- [ ] Implement media metadata extraction
- [ ] Implement timestamped transcription
- [ ] Implement transcript candidate windows
- [ ] Implement audio signal detector
- [ ] Implement scene-change detector
- [ ] Implement candidate merger
- [ ] Implement initial scoring
- [ ] Implement FFmpeg clip rendering
- [ ] Implement manifest JSON
- [ ] Add tests
- [ ] Run against real VOD
- [ ] Inspect false positives/negatives
- [ ] Tune scoring

## Explicitly out of scope

- automatic publishing
- Telegram approval
- n8n automation
- multi-platform publishing
- sophisticated face tracking

Those come after the core clipping loop works.
