# AutoClip.dev — Caption Reverse Engineering

## 1. Caption Data Format & Word Timing
AutoClip delivers word-level transcript data structured as an array of word objects with microsecond/centisecond precision:
```json
{
  "words": [
    { "w": "god", "s": 0.0, "e": 0.32 },
    { "w": "this", "s": 0.34, "e": 0.58 },
    { "w": "girl", "s": 0.60, "e": 0.88 },
    { "w": "shot", "s": 0.90, "e": 1.15 }
  ]
}
```
- `w`: Word string (verbatim token)
- `s`: Start time in seconds (relative to clip beginning)
- `e`: End time in seconds (relative to clip beginning)

---

## 2. Caption Grouping Heuristic
AutoClip chunks continuous word arrays into fixed groups of **4 words**:
```javascript
ey = ex ? function(words, chunkSize = 4) {
  if (words.length === 0) return [];
  if (chunkSize <= 0) return [words.slice()];
  let chunks = [];
  for (let i = 0; i < words.length; i += chunkSize) {
    chunks.push(words.slice(i, i + chunkSize));
  }
  return chunks;
}(clip.words, 4) : [];
```
This ensures captions on mobile vertical screens stay compact (typically 1–2 lines) and readable without crowding the 9:16 safe area.

---

## 3. Presets & Styling Architecture

From client bundle extraction (`eT` object in chunk `3lq2i3sgc_4c2.js`), AutoClip implements 6 core caption presets:

| Preset Key | Label | Font Family | Weight | Case | Mode | Styling Attributes |
|---|---|---|---|---|---|---|
| `none` | No captions | N/A | N/A | N/A | N/A | Disabled |
| `karaoke` | Karaoke | `'Montserrat', sans-serif` | 900 | UPPER | `fill` | `dimColor: rgba(255,255,255,0.4)`, `liveColor: rgb(255,255,255)`, `glow: 0 0 6px rgb(255,255,255)` |
| `beasty` | Beasty | `'Montserrat', sans-serif` | 900 | UPPER | `static` | `stroke: 1.5px rgb(0,0,0)`, bold white on black border |
| `deep_diver` | Deep Diver | `'Inter', sans-serif` | 400 | Normal | `static` | `dimColor: rgba(255,255,255,0.9)`, `glow: 0 2px 6px rgba(0,0,0,0.8)` |
| `pod_p` | Pod P | `'Inter', sans-serif` | 600 | Normal | `static` | `lowerThird: true`, clean interview typography |
| `youshaei` | Youshaei | `'Oswald', sans-serif` | 700 | UPPER | `alternate` | `highlightColor: rgb(34,211,238)` (cyan), `stroke: 1.5px black`, `glow: 0 0 6px rgba(34,211,238,0.7)` |
| `mozi` | Mozi | `'Poppins', sans-serif` | 700 | Normal | `sequential` | `liveColor: rgb(255,255,255)`, `glow: 0 2px 6px rgba(0,0,0,0.9)` |

---

## 4. Web Preview vs Server Export Rendering

### Web Preview (DOM + CSS Animation):
In the browser dashboard and homepage interactive previews, AutoClip **does not burn subtitles into video on the fly**. Instead:
1. It plays the clean MP4 video inside a `<video>` tag.
2. It generates dynamic CSS `@keyframes` rules with unique class names (`hdCapWordGroup_${id}_${idx}`, `hdCapWordFill_${id}_${idx}_${wIdx}`).
3. Words are wrapped in `<span>` tags, and CSS opacity/fill/scale transitions are executed natively by the browser GPU in sync with video playback.

### Server Export (Hardsub Burn-in):
During clip finalization and social auto-posting, AutoClip performs **FFmpeg hardsubbing (burn-in)**:
- Subtitles are rasterized directly onto the video frames.
- Rationale confirmed in technical documentation: Guarantees 100% platform consistency across TikTok, Instagram Reels, and Shorts feed autoplay where sound is muted by default.
