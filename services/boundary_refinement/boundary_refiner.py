from typing import List, Optional

from core.models.transcript import Word
from services.boundary_refinement.models import RefinedBoundary
from services.boundary_refinement.pause_boundary import PauseBoundaryAnalyzer
from services.boundary_refinement.sentence_boundary import (
    DANGLING_END_REGEX,
    DANGLING_START_REGEX,
    SentenceBoundaryAnalyzer,
)
from services.boundary_refinement.thought_boundary import ThoughtBoundaryMatcher
from services.detection.thought_detector import SentenceWindow


class SmartBoundaryRefiner:
    """Refines candidate moment start and end timestamps into human-editor quality cuts.
    
    Principles:
      - Purge dangling start words ('dan...', 'terus...', 'karena...')
      - Prevent cutting sentences mid-clause or mid-word
      - Snap into acoustic pause valleys (silence valleys)
      - Enforce max expansions: MAX_START_EXPANSION = 2.0s, MAX_END_EXPANSION = 3.0s
    """

    def __init__(
        self,
        max_start_expansion: float = 3.0,
        max_end_expansion: float = 8.0,
    ):
        self.max_start_expansion = max_start_expansion
        self.max_end_expansion = max_end_expansion
        self.sentence_analyzer = SentenceBoundaryAnalyzer()
        self.pause_analyzer = PauseBoundaryAnalyzer()
        self.thought_matcher = ThoughtBoundaryMatcher(
            max_start_expansion=max_start_expansion,
            max_end_expansion=max_end_expansion,
        )

    def refine(
        self,
        candidate_start: float,
        candidate_end: float,
        words: Optional[List[Word]] = None,
        sentences: Optional[List[SentenceWindow]] = None,
        text: Optional[str] = None,
        min_duration: float = 15.0,
        max_duration: float = 90.0,
    ) -> RefinedBoundary:
        all_reasons = []
        flags = []
        words = words or []
        sentences = sentences or []

        cur_start = float(candidate_start)
        cur_end = float(candidate_end)

        # 1. Thought / Sentence Boundary Expansion
        if sentences:
            m_start, m_end, t_reasons = self.thought_matcher.match_boundaries(
                cur_start, cur_end, sentences
            )
            # Enforce max expansion constraints
            if (cur_start - m_start) <= self.max_start_expansion:
                cur_start = max(0.0, m_start)
            if (m_end - cur_end) <= self.max_end_expansion:
                cur_end = m_end
            all_reasons.extend(t_reasons)

        # 2. Dangling Word Checks & Start Truncation
        clip_words = [w for w in words if w.end > cur_start and w.start < cur_end]
        if clip_words:
            first_w = clip_words[0].text.strip().lower()
            if DANGLING_START_REGEX.search(first_w) and len(clip_words) >= 2:
                # Snap start to the second word to discard dangling opening conjunction
                cur_start = clip_words[1].start
                all_reasons.append(f"Trimmed leading dangling conjunction '{first_w}'")
                flags.append("TRIMMED_DANGLING_START")

            last_w = clip_words[-1].text.strip().lower()
            if DANGLING_END_REGEX.search(last_w) and len(clip_words) >= 2:
                # Trim trailing dangling conjunction
                cur_end = clip_words[-2].end
                all_reasons.append(f"Trimmed trailing dangling word '{last_w}'")
                flags.append("TRIMMED_DANGLING_END")

        # 3. Acoustic Pause Alignment (Silence Valley Snapping)
        if words:
            aligned_start = self.pause_analyzer.align_timestamp_to_pause(
                cur_start, words, is_start=True, max_shift=1.2
            )
            if abs(aligned_start - cur_start) > 0.05:
                all_reasons.append(f"Snapped start to silence valley ({cur_start:.2f}s -> {aligned_start:.2f}s)")
                cur_start = aligned_start

            aligned_end = self.pause_analyzer.align_timestamp_to_pause(
                cur_end, words, is_start=False, max_shift=2.0
            )
            if abs(aligned_end - cur_end) > 0.05:
                all_reasons.append(f"Snapped end to silence valley ({cur_end:.2f}s -> {aligned_end:.2f}s)")
                cur_end = aligned_end
        # Duration bounds safety clamp
        cur_start = max(0.0, round(cur_start, 2))
        cur_end = round(max(cur_start + min_duration, cur_end), 2)
        if (cur_end - cur_start) > max_duration:
            cur_end = round(cur_start + max_duration, 2)

        duration = round(cur_end - cur_start, 2)
        start_adj = round(cur_start - candidate_start, 2)
        end_adj = round(cur_end - candidate_end, 2)

        return RefinedBoundary(
            original_start=candidate_start,
            original_end=candidate_end,
            refined_start=cur_start,
            refined_end=cur_end,
            duration=duration,
            start_adjustment=start_adj,
            end_adjustment=end_adj,
            reasons=all_reasons,
            boundary_flags=flags,
        )
