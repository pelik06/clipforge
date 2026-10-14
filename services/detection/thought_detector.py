import numpy as np
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.models.candidate import CandidateMoment
from core.models.transcript import SentenceWindow, ThoughtWindow, TranscriptSegment, Word
from services.detection.analyzer import MultiSignalAnalyzer, HOOK_PATTERN_REGEX

DANGLING_START_REGEX = re.compile(
    r"^(?:and|so|but|or|because|which|that|dan|lalu|karena|tapi|sehingga|bahwa|tetapi)\b",
    re.IGNORECASE,
)
DANGLING_END_REGEX = re.compile(
    r"(?:and|so|but|or|because|which|that|dan|lalu|karena|tapi|sehingga|bahwa|tetapi|the|a|an|to|of|with|in|on|at|for|by|from)\s*$",
    re.IGNORECASE,
)
BUMPER_TEXT_REGEX = re.compile(
    r"(?:please visit|subscribe|copyright|sponsored by|stanford\.edu|click the link|all rights reserved)",
    re.IGNORECASE,
)
HOOK_OPENERS_REGEX = re.compile(
    r"(?:truth be told|i am honored|i'm honored|today i want|let me tell you|the secret|here is why|here's why|most people|have you ever|what if|imagine if|rahasia|ternyata|tahukah kamu|sebenarnya|masalah terbesar)",
    re.IGNORECASE,
)
PAYOFF_ENDERS_REGEX = re.compile(
    r"(?:that's it|just three stories|graduation|ever gotten|thank you|in the world|it changed everything|that is why|itulah kenapa|akhirnya|selesai|berhasil)[.!?]?$",
    re.IGNORECASE,
)


def extract_sentences(
    transcript_segments: List[TranscriptSegment],
) -> List[SentenceWindow]:
    """Parse transcript segments and word timestamps into discrete, complete SentenceWindows."""
    if not transcript_segments:
        return []

    # Flatten all words with sentence-end markers
    sentences: List[SentenceWindow] = []
    current_words: List[Word] = []
    current_text_parts: List[str] = []

    for seg in transcript_segments:
        words = seg.words if seg.words else []
        if not words:
            # Synthesize words from text
            tokens = seg.text.split()
            dur = max(0.1, seg.end - seg.start)
            step = dur / max(1, len(tokens))
            words = [
                Word(
                    text=tok,
                    start=round(seg.start + i * step, 3),
                    end=round(min(seg.end, seg.start + (i + 1) * step), 3),
                )
                for i, tok in enumerate(tokens)
            ]

        for w in words:
            current_words.append(w)
            current_text_parts.append(w.text)

            # Check for sentence end punctuation: '.', '?', '!'
            text_clean = w.text.strip()
            is_terminal = any(text_clean.endswith(punct) for punct in [".", "?", "!"])

            if is_terminal and len(current_words) >= 2:
                s_start = current_words[0].start
                s_end = current_words[-1].end
                s_text = " ".join(current_text_parts).strip()
                sentences.append(
                    SentenceWindow(
                        start=round(s_start, 3),
                        end=round(s_end, 3),
                        text=s_text,
                        words=list(current_words),
                    )
                )
                current_words = []
                current_text_parts = []

    # If any trailing words remain
    if current_words:
        s_start = current_words[0].start
        s_end = current_words[-1].end
        s_text = " ".join(current_text_parts).strip()
        sentences.append(
            SentenceWindow(
                start=round(s_start, 3),
                end=round(s_end, 3),
                text=s_text,
                words=list(current_words),
            )
        )

    return sentences


class ThoughtDetector:
    """Transcript-driven conversational thought segmentation and full-window quality scoring."""

    def __init__(
        self,
        min_clip_duration: float = 15.0,
        max_clip_duration: float = 60.0,
        max_overlap_ratio: float = 0.35,
        max_containment_ratio: float = 0.50,
    ):
        self.min_clip_duration = min_clip_duration
        self.max_clip_duration = max_clip_duration
        self.max_overlap_ratio = max_overlap_ratio
        self.max_containment_ratio = max_containment_ratio
        self.analyzer = MultiSignalAnalyzer()

    def identify_thought_windows(
        self,
        sentences: List[SentenceWindow],
        total_duration: float,
        silences: Optional[List[Tuple[float, float]]] = None,
        scenes: Optional[List[Dict[str, float]]] = None,
    ) -> List[ThoughtWindow]:
        """Cluster adjacent sentences into complete conversational thoughts [15s - 60s]."""
        if not sentences:
            return []

        thoughts: List[ThoughtWindow] = []
        n_sent = len(sentences)

        for i in range(n_sent):
            anchor = sentences[i]

            # Reject anchor if it's purely a website bumper or disclaimer
            if BUMPER_TEXT_REGEX.search(anchor.text):
                continue

            # Start clustering from anchor sentence
            curr_sentences = [anchor]
            curr_start = anchor.start
            curr_end = anchor.end
            curr_words = list(anchor.words)

            # Look forward to build complete thought
            for j in range(i + 1, n_sent):
                next_s = sentences[j]
                if BUMPER_TEXT_REGEX.search(next_s.text):
                    break

                potential_dur = next_s.end - curr_start
                if potential_dur > self.max_clip_duration:
                    break

                # Check pause between sentences
                pause = next_s.start - curr_end
                # If natural continuation (pause < 4.0s)
                if pause < 4.0:
                    curr_sentences.append(next_s)
                    curr_end = next_s.end
                    curr_words.extend(next_s.words)

                    dur = curr_end - curr_start
                    if dur >= self.min_clip_duration:
                        # Check if last sentence has terminal payoff
                        has_payoff = bool(
                            re.search(r"[.!?]$", next_s.text.strip())
                            or PAYOFF_ENDERS_REGEX.search(next_s.text.strip())
                        )
                        if has_payoff:
                            break

            dur = curr_end - curr_start

            # If duration < min_clip_duration, attempt backward expansion to include preceding setup sentence
            if dur < self.min_clip_duration and i > 0:
                prev_s = sentences[i - 1]
                if not BUMPER_TEXT_REGEX.search(prev_s.text):
                    pause_prev = curr_start - prev_s.end
                    if pause_prev < 4.0 and (curr_end - prev_s.start) <= self.max_clip_duration:
                        curr_sentences.insert(0, prev_s)
                        curr_start = prev_s.start
                        curr_words = list(prev_s.words) + curr_words
                        dur = curr_end - curr_start

            # Strict duration filter: must meet min_clip_duration (15s) and max_clip_duration (60s)
            if dur < self.min_clip_duration or dur > self.max_clip_duration:
                continue

            combined_text = " ".join([s.text for s in curr_sentences]).strip()

            # Analyze hook in opening sentence
            first_text = curr_sentences[0].text
            has_hook = bool(HOOK_OPENERS_REGEX.search(first_text) or HOOK_PATTERN_REGEX.search(first_text))

            # Analyze payoff in final sentence
            last_text = curr_sentences[-1].text
            has_payoff = bool(PAYOFF_ENDERS_REGEX.search(last_text) or re.search(r"[.!?]$", last_text))

            tw = ThoughtWindow(
                sentences=curr_sentences,
                start=round(curr_start, 3),
                end=round(curr_end, 3),
                text=combined_text,
                words=curr_words,
                hook_text=first_text,
                payoff_text=last_text,
                has_hook=has_hook,
                has_payoff=has_payoff,
            )
            thoughts.append(tw)

        return thoughts

    def score_thought_window(
        self,
        thought: ThoughtWindow,
        energy_arr: Optional[np.ndarray] = None,
        peak_arr: Optional[np.ndarray] = None,
        motion_profile: Optional[List[Tuple[float, float]]] = None,
        face_profile: Optional[List[Tuple[float, float, int]]] = None,
        scenes: Optional[List[Dict[str, float]]] = None,
        silences: Optional[List[Tuple[float, float]]] = None,
        total_duration: float = 300.0,
        audio_reactions: Optional[List[Any]] = None,
    ) -> float:
        """Compute holistic full-window quality score evaluating all 9 criteria plus penalties."""
        scenes = scenes or []
        silences = silences or []
        motion_profile = motion_profile or []
        face_profile = face_profile or []
        energy_arr = energy_arr if energy_arr is not None else np.array([])
        peak_arr = peak_arr if peak_arr is not None else np.array([])
        t0 = thought.start
        t1 = thought.end
        dur = max(0.1, t1 - t0)

        # 1. Speech Density across full candidate window
        spoken_dur = sum([w.end - w.start for w in thought.words]) if thought.words else dur * 0.7
        speech_density = min(1.0, max(0.0, spoken_dur / dur))

        # 2. Audio Energy & Peak across full window
        i0 = max(0, int(t0 / 0.5))
        i1 = min(len(energy_arr), int(t1 / 0.5) + 1)
        if i0 < i1 and len(energy_arr) > 0:
            sub_e = energy_arr[i0:i1]
            sub_p = peak_arr[i0:i1]
            audio_energy = float(np.mean(sub_e))
            audio_peak = float(np.max(sub_p))
        else:
            audio_energy = 0.5
            audio_peak = 0.5

        # 3. Sentence Completeness
        has_start_punct = not DANGLING_START_REGEX.search(thought.text)
        has_end_punct = bool(re.search(r"[.!?]$", thought.text.strip()))
        sentence_completeness = 1.0 if (has_start_punct and has_end_punct) else 0.5

        # 4. Thought Completeness (Hook + Context + Payoff)
        if thought.has_hook and thought.has_payoff and len(thought.sentences) >= 2:
            thought_completeness = 1.0
        elif thought.has_payoff or thought.has_hook:
            thought_completeness = 0.75
        else:
            thought_completeness = 0.50

        # 5. Hook Strength
        hook_strength = 1.0 if thought.has_hook else 0.35

        # 6. Payoff Strength
        payoff_strength = 1.0 if thought.has_payoff else 0.35

        # 7. Boundary Quality (silence / pause alignment)
        boundary_quality = 0.3
        for s_start, s_end in silences:
            if abs(t0 - s_end) <= 1.2 or abs(t1 - s_start) <= 1.2:
                boundary_quality = 1.0
                break

        # 8. Scene Stability & Boundary
        scene_quality = 0.5
        for sc in scenes:
            if abs(t0 - sc["start"]) <= 1.5 or abs(t1 - sc["end"]) <= 1.5:
                scene_quality = 1.0
                break

        # Weighted baseline score
        base_score = (
            0.15 * speech_density
            + 0.10 * audio_energy
            + 0.10 * audio_peak
            + 0.15 * sentence_completeness
            + 0.20 * thought_completeness
            + 0.10 * hook_strength
            + 0.10 * payoff_strength
            + 0.05 * boundary_quality
            + 0.05 * scene_quality
        )
        score_100 = base_score * 100.0

        # Audio Reaction Boost (up to 10% maximum contribution)
        if audio_reactions:
            for r in audio_reactions:
                r_start = getattr(r, "start", 0.0) if hasattr(r, "start") else r.get("start", 0.0)
                r_end = getattr(r, "end", 0.0) if hasattr(r, "end") else r.get("end", 0.0)
                r_conf = getattr(r, "confidence", 0.7) if hasattr(r, "confidence") else r.get("confidence", 0.7)
                if max(t0, r_start) < min(t1, r_end):
                    boost = min(10.0, r_conf * 10.0)
                    score_100 += boost
                    break
        # PENALTIES
        # Incomplete start penalty: e.g. starts with "and", "so", "because", "dan" without setup
        if DANGLING_START_REGEX.search(thought.text):
            score_100 -= 25.0

        # Incomplete end penalty: trailing conjunction or no terminal punctuation
        if DANGLING_END_REGEX.search(thought.text) or not has_end_punct:
            score_100 -= 25.0

        # Zero-start penalty: penalize starting at 0.0 unless strong genuine conversational hook
        if thought.start < 1.0:
            if BUMPER_TEXT_REGEX.search(thought.text) or not thought.has_hook:
                score_100 -= 35.0

        return round(max(0.0, min(99.0, score_100)), 1)

    def deduplicate_thoughts(
        self,
        candidates: List[CandidateMoment],
        max_clips: int = 10,
    ) -> List[CandidateMoment]:
        """Strict deduplication enforcing both IoU <= 0.35 AND containment <= 0.50."""
        candidates.sort(key=lambda c: c.score, reverse=True)
        unique: List[CandidateMoment] = []

        for cand in candidates:
            is_dup = False
            for prev in unique:
                overlap_start = max(cand.start, prev.start)
                overlap_end = min(cand.end, prev.end)
                if overlap_end > overlap_start:
                    overlap_dur = overlap_end - overlap_start
                    union_dur = (cand.end - cand.start) + (prev.end - prev.start) - overlap_dur
                    iou = overlap_dur / max(0.01, union_dur)
                    containment = overlap_dur / max(0.01, min(cand.duration, prev.duration))

                    # Reject if IoU > 0.35 OR containment > 0.50
                    if iou > self.max_overlap_ratio or containment > self.max_containment_ratio:
                        is_dup = True
                        break

            if not is_dup:
                cand.rank = len(unique) + 1
                cand.moment_id = f"mom_{cand.rank:03d}"
                unique.append(cand)
                if len(unique) >= max_clips:
                    break
        return unique

    def generate_variants_for_top_moments(
        self,
        top_moments: List[CandidateMoment],
        sentences: List[SentenceWindow],
        top_n: int = 3,
    ) -> List[CandidateMoment]:
        """Generate tight (20-35s) and extended (40-65s) variants for top N moments based on sentence boundaries."""
        if not sentences or not top_moments:
            return top_moments

        expanded_moments: List[CandidateMoment] = []

        for idx, mom in enumerate(top_moments):
            if idx >= top_n:
                expanded_moments.append(mom)
                continue

            moment_sentences = [
                s for s in sentences if s.start >= (mom.start - 0.5) and s.end <= (mom.end + 0.5)
            ]

            if len(moment_sentences) < 2:
                expanded_moments.append(mom)
                continue

            # 1. Tight Variant: Hook + core punchline (20-35s)
            tight_moment = None
            for p in range(len(moment_sentences)):
                sub_end = moment_sentences[p].end
                sub_dur = sub_end - moment_sentences[0].start
                if 20.0 <= sub_dur <= 35.0:
                    if re.search(r"[.!?]$", moment_sentences[p].text.strip()):
                        tight_moment = CandidateMoment(
                            start=round(moment_sentences[0].start, 2),
                            end=round(sub_end, 2),
                            score=round(mom.score + 0.5, 1),
                            reasons=mom.reasons + [f"Tight punchy variant ({sub_dur:.1f}s)"],
                            signals=dict(mom.signals),
                            variant="tight",
                            parent_moment_id=mom.moment_id,
                        )
                        break

            # 2. Extended Variant: Context setup + payoff resolution (40-65s)
            ext_moment = None
            first_idx = sentences.index(moment_sentences[0]) if moment_sentences[0] in sentences else -1
            last_idx = sentences.index(moment_sentences[-1]) if moment_sentences[-1] in sentences else -1

            if first_idx >= 0 and last_idx >= 0:
                e_start_idx = first_idx
                e_end_idx = last_idx

                if first_idx > 0:
                    prev_s = sentences[first_idx - 1]
                    if (moment_sentences[0].start - prev_s.end) < 2.5 and not BUMPER_TEXT_REGEX.search(prev_s.text):
                        e_start_idx = first_idx - 1

                while e_end_idx < (len(sentences) - 1):
                    nxt_s = sentences[e_end_idx + 1]
                    total_dur = nxt_s.end - sentences[e_start_idx].start
                    if total_dur > 65.0 or (nxt_s.start - sentences[e_end_idx].end) > 3.0:
                        break
                    e_end_idx += 1
                    if total_dur >= 40.0 and re.search(r"[.!?]$", nxt_s.text.strip()):
                        break

                ext_dur = sentences[e_end_idx].end - sentences[e_start_idx].start
                if ext_dur > mom.duration + 4.0 and ext_dur <= 70.0:
                    ext_moment = CandidateMoment(
                        start=round(sentences[e_start_idx].start, 2),
                        end=round(sentences[e_end_idx].end, 2),
                        score=round(mom.score, 1),
                        reasons=mom.reasons + [f"Extended context variant ({ext_dur:.1f}s)"],
                        signals=dict(mom.signals),
                        variant="extended",
                        parent_moment_id=mom.moment_id,
                    )

            if tight_moment and ext_moment:
                expanded_moments.extend([tight_moment, ext_moment])
            elif tight_moment:
                expanded_moments.extend([tight_moment, mom])
            elif ext_moment:
                expanded_moments.extend([mom, ext_moment])
            else:
                expanded_moments.append(mom)

        return expanded_moments
