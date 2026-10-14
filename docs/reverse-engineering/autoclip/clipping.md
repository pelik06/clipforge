# AutoClip.dev — Moment Detection & Multi-Clip Strategy

## 1. Technical Claims vs Observed Implementation
AutoClip claims a proprietary **ViralScan** system utilizing a "two-pass multimodal AI model and audio-signal detection" to evaluate five engagement criteria.

### Revealed Acoustic Architecture:
As evidenced in AutoClip's technical FAQ, audio analysis explicitly uses:
1. **YAMNet (Audio Event Classification):** Google/TensorFlow YAMNet is utilized to detect audience reactions:
   - Laughter
   - Applause / Cheering
2. **Audio Energy Peaks:** Root Mean Square (RMS) volume and peak amplitude envelope analysis to locate emotional outbursts or gaming intensity.
3. **Speech Rate Changes:** Velocity of speech delivery (syllables/words per second) as an excitement proxy.
4. **Musical Transitions:** Detection of beat drops and musical crescendos.
5. **Pause Patterns:** Identification of strategic pauses immediately preceding punchlines or story payoffs.

---

## 2. Virality Scoring Structure
Each candidate moment is scored out of **100 total points**, comprised of **5 sub-criteria scored 0–20 points each**:

| Criterion | Max Points | Technical Basis |
|---|---|---|
| **Hook Strength** | 20 | First 0–3s opening sentence punchiness, pattern-interrupt words, audio energy |
| **Emotional Intensity** | 20 | YAMNet laughter/applause, vocal pitch/volume spikes, sentiment extremity |
| **Information Density** | 20 | Word rate, speech-to-silence ratio, conceptual payload |
| **Share-Worthiness** | 20 | Relatability score, polarizing statements, high social utility |
| **Replay Value** | 20 | Punchline delivery, looping suitability, unexpected payoffs |

**Total Virality Score = Hook (20) + Emotion (20) + Info Density (20) + Shareability (20) + Replay (20)**

Observed clip items in the showcase manifest exhibit scores ranging from **79 to 95** (e.g., Score 95, 92, 89, 88, 85, 82, 79).

---

## 3. Multi-Clip & Boundary Logic

### Clip Count Behavior:
- **Default / Maximum Clips:**
  - **Starter Plan:** Up to **6 clips** per video.
  - **Pro / Scale Plans:** Up to **10 clips** per video.
- **Dynamic Selection:** The system does not emit a static single slice. It scores candidate windows across the complete source timeline, ranks them descending by `viralityScore`, applies temporal deduplication, and selects the top $N$ non-overlapping moments.

### Dual-Variant Strategy (Tight vs Extended Cut):
Top-scoring moments automatically spawn **two variants**:
1. **Tight Cut:** Aggressively trimmed to maximize hook retention and eliminate non-essential lead-in/lead-out words (optimized for TikTok/Reels feed scrolling).
2. **Extended Cut:** Preserves wider context before the hook and after the payoff (optimized for deeper explanations or YouTube Shorts).

### Long Broadcast & VOD Handling (Twitch/Kick):
For multi-hour livestreams (e.g., 9-hour Twitch VODs):
- AutoClip applies an acoustic/chat pre-filtering heuristic that scans the entire timeline for high-density activity regions.
- Instead of transcribing and analyzing all 9 hours, it extracts only the top highlight candidate segments for full multimodal scoring.
- Billed at a fractional rate (1 credit per 20 minutes of broadcast) rather than 1:1 minute-for-minute pricing.
