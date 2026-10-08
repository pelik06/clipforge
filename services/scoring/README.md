# Interesting Moment Scoring

Streamer clipping is the core intelligence of ClipForge.

Candidate scores should eventually combine signals such as:

- transcript interest
- emotional/reaction language
- audio intensity
- visual activity
- scene/event change
- context completeness
- sentence completeness

Penalties:

- long silence
- starting mid-sentence
- ending mid-sentence
- duplicate/overlapping candidate
- insufficient context

Do not hard-code weights permanently before testing on real VODs.
