# ClipForge Constitution

**Version:** 2.1
**Status:** Active
**Project:** ClipForge

## 1. Mission

ClipForge is a streamer-first short-form clipping system.

Its primary job is:

> Take a streamer VOD or livestream recording, identify genuinely interesting moments, turn them into vertical short-form clips, run quality checks, request human approval, and publish approved clips.

ClipForge is **not** a generic AI video generator.

The core value is finding and packaging moments that are worth watching.

---

## 2. Core Principles

### P1 — Streamer clipping comes first
Every major feature must improve one of:
- finding interesting streamer moments
- preserving context
- producing watchable clips
- reducing manual clipping work

Features unrelated to streamer clipping are secondary.

### P2 — Build our own implementation
ClipForge may study proven open-source projects such as OpenShorts for architecture, algorithms, and engineering ideas.

However:
- ClipForge does not depend on the OpenShorts repository at runtime.
- ClipForge owns its implementation.
- Code is implemented independently unless explicitly licensed and intentionally reused.
- OpenShorts is a reference, not a required dependency.

### P3 — n8n orchestrates; ClipForge thinks
n8n may coordinate jobs, schedules, notifications, and external services.

The actual clipping intelligence belongs inside ClipForge.

### P4 — Human approval remains the safety gate
Automatic generation does not mean automatic publication.

A clip should reach publishing only after passing:
1. technical QC
2. rights/source checks
3. human approval

### P5 — Keep the first version simple
Do not build the complete system before validating the core loop.

The first useful loop is:

`VOD → transcript/signals → candidate moments → ranking → clip → QC → output`

### P6 — Prefer measurable signals
Interestingness should be based on observable evidence rather than arbitrary LLM guesses.

Signals may include:
- transcript semantics
- emotional/reaction language
- audio intensity
- silence/speech boundaries
- scene changes
- visual activity
- streamer reactions
- gameplay/event changes
- context completeness

### P7 — Preserve context
A clip that starts at the funniest sentence but removes the setup may be worse than a slightly longer clip.

Candidate selection must consider:
- lead-in context
- complete sentences
- reaction payoff
- natural ending

### P8 — Platform quality matters
Target output:
- 9:16 vertical video
- 1080×1920 when source/output budget permits
- readable captions
- safe-zone-aware text
- normalized audio
- no accidental black bars
- no third-party watermarks

### P9 — Rights before scale
Only process sources that ClipForge is authorized to process and publish.

Do not use copyrighted streamer content without the required permission/license.

### P10 — Fail safely
Repeated QC failures, malformed jobs, missing inputs, or unsafe states should stop the job rather than silently publish bad output.

---

## 3. Hard Rules

### R1 — Rights verification
Every source must have a known rights status before publishing.

### R2 — Human approval
Publishing requires explicit approval unless a future policy explicitly changes this rule.

### R3 — Secrets
API keys, tokens, cookies, and publishing credentials must never be committed to Git.

### R4 — No fake engagement
No fake views, likes, comments, follows, spam, or artificial engagement.

### R5 — No third-party watermark
Final clips must not contain watermarks belonging to unrelated clipping/generation platforms.

### R6 — QC failure stop
Two consecutive failures of the same required QC check should stop the job for investigation.

### R7 — Source diversity
When operating multiple channels, avoid over-relying on one creator/source unless explicitly authorized.

### R8 — Local media hygiene
Temporary media should be deleted according to the configured retention policy.

### R9 — Job traceability
Every processing job must have:
- job ID
- source
- creation timestamp
- current status
- stage
- errors
- output references

### R10 — No silent publishing
A technical success is not equivalent to approval.

### R11 — No unnecessary infrastructure
Do not introduce a paid service when a local/free implementation is sufficient for the current stage.

---

## 4. Architecture

```text
                    ┌──────────────────┐
                    │       n8n        │
                    │ orchestration    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   ClipForge API  │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
          Ingest        Transcription    Job/State
              │              │
              └──────┬───────┘
                     ▼
              Signal Detection
                     │
                     ▼
              Candidate Builder
                     │
                     ▼
              Interestingness
                 Scoring
                     │
                     ▼
                Clip Engine
                     │
            ┌────────┴────────┐
            ▼                 ▼
        Captions          Reframing
            │                 │
            └────────┬────────┘
                     ▼
                    QC
                     │
                     ▼
              Human Approval
                     │
                     ▼
                 Publishing
```

---

## 5. Core Components

### 5.1 Ingest
Responsibilities:
- accept local VODs
- optionally accept supported URLs
- validate media
- normalize metadata
- create a job

### 5.2 Transcription
Responsibilities:
- generate transcript
- preserve timestamps
- expose word/sentence boundaries
- make transcript searchable by the scoring engine

Initial implementation target:
- Whisper-compatible transcription

### 5.3 Signal Detection
Detect independent evidence that a moment may be interesting.

Initial signals:
- audio peaks
- speech density
- silence boundaries
- scene changes
- visual activity
- transcript semantics

### 5.4 Candidate Builder
Convert signals into candidate time windows.

Candidates should:
- start before the important moment when context is useful
- end after the payoff/reaction
- avoid cutting through speech unnecessarily

### 5.5 Interestingness Scoring
Each candidate receives a score.

Example conceptual model:

```text
score =
    transcript_interest
  + reaction_signal
  + audio_energy
  + visual_activity
  + event_change
  + context_completeness
  - silence_penalty
  - incomplete_sentence_penalty
  - duplicate_penalty
```

The exact weights must be validated against real streamer VODs.

### 5.6 Clip Engine
Responsibilities:
- trim source media
- render vertical output
- preserve/normalize audio
- create final clip files

FFmpeg is the initial media-processing foundation.

### 5.7 Captions
Responsibilities:
- generate timed captions
- format captions for short-form viewing
- keep text inside platform-safe regions

### 5.8 Reframing
Initial version may use a fixed center crop.

Later versions may add:
- face tracking
- streamer/webcam detection
- gameplay-aware layouts
- dynamic crop selection

### 5.9 QC
Validate:
- duration
- resolution
- aspect ratio
- playable output
- audio presence
- caption presence
- safe zones
- no unintended watermark
- no obvious black bars

### 5.10 Publishing
Publishing adapters remain isolated from the clipping engine.

The clipping engine must not own platform credentials.

---

## 6. Development Phases

### Phase 1 — Core MVP
Implement:

`local VOD → transcription → candidates → scoring → FFmpeg clip → JSON manifest`

No publishing.

### Phase 2 — Better streamer intelligence
Add:
- audio reaction detection
- scene/event detection
- reaction-aware scoring
- context-aware windows
- duplicate candidate suppression

### Phase 3 — Vertical production
Add:
- 9:16 rendering
- captions
- configurable layouts
- basic reframing

### Phase 4 — QC and approval
Add:
- automated QC
- Telegram approval workflow
- job state persistence

### Phase 5 — Automation
Add:
- n8n workflows
- scheduled processing
- retry policies
- cleanup jobs

### Phase 6 — Publishing
Add isolated:
- YouTube adapter
- TikTok adapter
- publishing queue
- final approval enforcement

---

## 7. Tool Governance

Every external dependency must have a reason to exist.

Before adding a tool, evaluate:
1. Does it solve a real ClipForge problem?
2. Is it actively maintained?
3. Can it run locally?
4. What does it cost?
5. Does it add a watermark?
6. Does it require an account/API?
7. Can it be replaced later?
8. Does its license permit our intended use?

---

## 8. Kill Switches

Stop processing if:
- rights status is unknown
- required source media is corrupt
- QC repeatedly fails
- credentials are missing or invalid
- output contains unexpected watermarking
- job state becomes inconsistent
- publishing approval is absent

---

## 9. Definition of Done

A feature is not complete because the code runs.

A feature is complete when:
- it works on real streamer VOD data
- its failure modes are understood
- tests cover important behavior
- outputs are inspectable
- configuration is documented
- logs identify the job/stage
- it does not violate the constitution

---

## 10. Success Metric

The first success metric is not views.

The first success metric is:

> How reliably can ClipForge turn a long streamer VOD into a small set of genuinely good, context-complete, technically clean clips that a human would actually choose to publish?

Only after that works should optimization focus on publishing scale and channel performance.
