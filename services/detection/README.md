# Signal Detection

This service should eventually produce independent signals instead of one opaque "AI says this is interesting" result.

Planned detectors:

- `audio.py` — loudness/energy peaks, reaction spikes
- `silence.py` — speech boundaries and silence windows
- `scene.py` — scene/cut changes
- `visual.py` — motion/activity indicators
- `transcript.py` — semantic/event phrases from transcript

The detectors should emit normalized signals that the scoring layer can combine.
