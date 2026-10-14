import pytest
from core.models.candidate import CandidateMoment
from core.models.configuration import JobConfig
from core.models.transcript import SentenceWindow, ThoughtWindow, TranscriptSegment, Word
from services.captions.service import (
    CaptionRenderer,
    adjust_segments_for_clip,
    build_word_chunks_from_segment,
    group_words_into_chunks,
    validate_ass_file,
)
from services.detection.moment_pipeline import NonLLMMomentDetector
from services.detection.thought_detector import ThoughtDetector, extract_sentences
from services.reframing.service import (
    Detection,
    Reframer,
    ReframingAnalysis,
    TrajectoryPoint,
    compute_center_similarity,
    compute_iou,
)


# =====================================================================
# 1. Thought Windowing & Sentence Boundary Tests
# =====================================================================

def test_thought_window_grouping():
    """Verify multiple adjacent sentences group into a coherent thought window with hook and payoff."""
    s1 = SentenceWindow(start=10.0, end=14.0, text="Truth be told, this is the hardest problem in AI.", words=[
        Word("Truth", 10.0, 10.5), Word("be", 10.5, 11.0), Word("told,", 11.0, 11.5),
        Word("this", 11.5, 12.0), Word("is", 12.0, 12.3), Word("the", 12.3, 12.5),
        Word("hardest", 12.5, 13.0), Word("problem", 13.0, 13.5), Word("in", 13.5, 13.7), Word("AI.", 13.7, 14.0),
    ])
    s2 = SentenceWindow(start=14.5, end=20.0, text="Most people think it is the algorithm itself.", words=[
        Word("Most", 14.5, 15.0), Word("people", 15.0, 15.5), Word("think", 15.5, 16.0),
        Word("it", 16.0, 16.3), Word("is", 16.3, 16.6), Word("the", 16.6, 17.0),
        Word("algorithm", 17.0, 18.0), Word("itself.", 18.0, 20.0),
    ])
    s3 = SentenceWindow(start=20.5, end=27.0, text="In reality, it is completely about data quality and nothing else.", words=[
        Word("In", 20.5, 21.0), Word("reality,", 21.0, 22.0), Word("it", 22.0, 22.3),
        Word("is", 22.3, 22.6), Word("about", 22.6, 23.0), Word("data", 23.0, 24.0),
        Word("quality.", 24.0, 27.0),
    ])

    td = ThoughtDetector(min_clip_duration=15.0, max_clip_duration=60.0)
    thoughts = td.identify_thought_windows([s1, s2, s3], total_duration=35.0)

    assert len(thoughts) >= 1
    t = thoughts[0]
    assert t.duration >= 15.0
    assert t.has_hook is True  # "Truth be told"
    assert t.has_payoff is True  # Terminal punctuation and resolution
    assert "Truth be told" in t.text
    assert "data quality" in t.text


def test_sentence_boundary_preserved():
    """Verify that sentence extraction preserves exact word boundaries without mid-sentence truncations."""
    segs = [
        TranscriptSegment(
            text="First sentence ends here. Second sentence continues right now.",
            start=1.0,
            end=10.0,
            words=[
                Word("First", 1.0, 1.5), Word("sentence", 1.5, 2.0), Word("ends", 2.0, 2.5), Word("here.", 2.5, 3.0),
                Word("Second", 4.0, 4.5), Word("sentence", 4.5, 5.0), Word("continues", 5.0, 5.5),
                Word("right", 5.5, 6.0), Word("now.", 6.0, 6.5),
            ],
        )
    ]
    sentences = extract_sentences(segs)
    assert len(sentences) == 2
    assert sentences[0].text == "First sentence ends here."
    assert sentences[0].start == 1.0
    assert sentences[0].end == 3.0
    assert sentences[1].text == "Second sentence continues right now."
    assert sentences[1].start == 4.0
    assert sentences[1].end == 6.5


# =====================================================================
# 2. Strict Duration Enforcement Tests
# =====================================================================

def test_min_duration_enforced():
    """Verify that candidate moments < 15.0 seconds are strictly rejected."""
    # A short thought of only 7 seconds
    s_short = SentenceWindow(start=5.0, end=12.0, text="A very brief comment here.", words=[
        Word("A", 5.0, 5.5), Word("very", 5.5, 6.0), Word("brief", 6.0, 7.0),
        Word("comment", 7.0, 8.0), Word("here.", 8.0, 12.0),
    ])
    td = ThoughtDetector(min_clip_duration=15.0, max_clip_duration=60.0)
    thoughts = td.identify_thought_windows([s_short], total_duration=20.0)
    # Cannot expand to 15s because no other sentences exist
    assert len(thoughts) == 0, f"Expected 0 thoughts < 15s, got {len(thoughts)}"


# =====================================================================
# 3. Deduplication & Distinct Thoughts Tests
# =====================================================================

def test_distinct_thought_deduplication():
    """Verify that semantic duplicates (containment > 50% or IoU > 35%) are eliminated."""
    td = ThoughtDetector(max_overlap_ratio=0.35, max_containment_ratio=0.50)
    candidates = [
        # Candidate 1: Full thought [10.0 - 28.0] (18s)
        CandidateMoment(start=10.0, end=28.0, score=92.0),
        # Candidate 2: Sub-slice of Candidate 1 [12.0 - 27.0] (15s) -> Containment = 15/15 = 100% -> MUST DROP!
        CandidateMoment(start=12.0, end=27.0, score=85.0),
        # Candidate 3: Distinct thought [32.0 - 50.0] (18s) -> Keep!
        CandidateMoment(start=32.0, end=50.0, score=88.0),
    ]
    unique = td.deduplicate_thoughts(candidates, max_clips=5)
    assert len(unique) == 2
    assert unique[0].start == 10.0 and unique[0].end == 28.0
    assert unique[1].start == 32.0 and unique[1].end == 50.0


# =====================================================================
# 4. Zero-Start Fallback Eradication Tests
# =====================================================================

def test_no_first_seconds_fallback():
    """Verify that detector does not inject an arbitrary [0, 10] or [0, 15] fallback when criteria are not met."""
    detector = NonLLMMomentDetector(moment_threshold=0.99)
    # When threshold is unreachable, must return strictly []
    moments = detector.detect_moments(
        media_path="non_existent.mp4",
        min_clip_duration=15.0,
    )
    assert moments == []


# =====================================================================
# 5. Caption Transcript & Timestamp Alignment Tests
# =====================================================================

def test_caption_content_matches_clip_transcript():
    """Verify that words outside [clip_start, clip_end] are stripped and caption text is reconstructed."""
    clip_start = 20.0
    clip_end = 35.0  # Duration = 15.0s

    segments = [
        TranscriptSegment(
            text="Halo ini adalah contoh kalimat pembuka yang sangat panjang sekali.",
            start=18.0,
            end=38.0,
            words=[
                Word("Halo", 18.0, 19.0),        # OUTSIDE (< 20.0) -> DROP
                Word("ini", 19.2, 19.8),         # OUTSIDE (< 20.0) -> DROP
                Word("adalah", 20.5, 21.0),      # INSIDE -> KEEP
                Word("contoh", 21.2, 22.0),      # INSIDE -> KEEP
                Word("kalimat", 22.2, 23.0),     # INSIDE -> KEEP
                Word("pembuka", 23.5, 24.5),     # INSIDE -> KEEP
                Word("yang", 25.0, 25.5),        # INSIDE -> KEEP
                Word("sangat", 26.0, 27.0),      # INSIDE -> KEEP
                Word("panjang", 27.5, 28.5),     # INSIDE -> KEEP
                Word("sekali.", 36.0, 37.0),     # OUTSIDE (> 35.0) -> DROP
            ],
        )
    ]

    adjusted = adjust_segments_for_clip(segments, clip_start=clip_start, clip_end=clip_end)
    assert len(adjusted) == 1
    seg = adjusted[0]

    # Dropped words "Halo", "ini", "sekali." must not appear!
    assert "Halo" not in seg.text
    assert "ini" not in seg.text
    assert "sekali" not in seg.text

    # Inside words must appear
    assert seg.text == "adalah contoh kalimat pembuka yang sangat panjang"
    assert seg.start == 0.5  # 20.5 - 20.0
    assert seg.end == 8.5    # 28.5 - 20.0
    assert len(seg.words) == 7


def test_caption_timestamp_relative_to_clip():
    """Verify relative timestamps start at 0.0 and clamp to clip duration."""
    clip_start = 10.0
    clip_end = 25.0  # 15s clip

    segments = [
        TranscriptSegment(
            text="Speech inside clip interval.",
            start=12.0,
            end=22.0,
            words=[
                Word("Speech", 12.0, 14.0),
                Word("inside", 14.0, 16.0),
                Word("clip", 16.0, 18.0),
                Word("interval.", 18.0, 22.0),
            ],
        )
    ]
    adjusted = adjust_segments_for_clip(segments, clip_start=clip_start, clip_end=clip_end)
    assert len(adjusted) == 1
    assert adjusted[0].start == 2.0   # 12.0 - 10.0
    assert adjusted[0].end == 12.0   # 22.0 - 10.0
    assert adjusted[0].words[0].start == 2.0
    assert adjusted[0].words[-1].end == 12.0


# =====================================================================
# 6. Caption 4-Word Grouping Tests
# =====================================================================

def test_caption_grouping_7_words():
    """7 words must split into 4 + 3."""
    words = [Word(text=f"w{i}", start=float(i), end=float(i + 0.8)) for i in range(7)]
    chunks = group_words_into_chunks(words, words_per_group=4)
    assert len(chunks) == 2
    assert len(chunks[0]) == 4
    assert len(chunks[1]) == 3


def test_caption_grouping_8_words():
    """8 words must split into 4 + 4."""
    words = [Word(text=f"w{i}", start=float(i), end=float(i + 0.8)) for i in range(8)]
    chunks = group_words_into_chunks(words, words_per_group=4)
    assert len(chunks) == 2
    assert len(chunks[0]) == 4
    assert len(chunks[1]) == 4


def test_caption_grouping_9_words():
    """9 words must split into 4 + 4 + 1."""
    words = [Word(text=f"w{i}", start=float(i), end=float(i + 0.8)) for i in range(9)]
    chunks = group_words_into_chunks(words, words_per_group=4)
    assert len(chunks) == 3
    assert len(chunks[0]) == 4
    assert len(chunks[1]) == 4
    assert len(chunks[2]) == 1


# =====================================================================
# 7. Scene-Cut Snap Reframing Tests
# =====================================================================

def test_scene_cut_snap_in_filter():
    """At a scene cut, filter expression must snap instantly rather than interpolate."""
    reframer = Reframer()
    pts = [
        TrajectoryPoint(timestamp=0.0, target_x=500.0, target_y=300.0, crop_x=200.0, crop_y=0.0, is_scene_cut=False),
        TrajectoryPoint(timestamp=4.0, target_x=520.0, target_y=300.0, crop_x=220.0, crop_y=0.0, is_scene_cut=False),
        TrajectoryPoint(timestamp=8.0, target_x=900.0, target_y=300.0, crop_x=600.0, crop_y=0.0, is_scene_cut=True),
        TrajectoryPoint(timestamp=12.0, target_x=910.0, target_y=300.0, crop_x=610.0, crop_y=0.0, is_scene_cut=False),
    ]
    analysis = ReframingAnalysis(
        mode="speaker_aware_tracking",
        active_speaker_available=False,
        face_detection_available=True,
        fallback_applied=False,
        trajectory=pts,
    )
    filter_str = reframer.build_crop_filter(analysis, source_w=1920, source_h=1080)
    assert "if(lt(t,8.00),220.0" in filter_str
    assert "t-0.00" in filter_str

def test_caption_no_duplicate_words_and_zero_dialogue_overlap():
    """Verify that stutter/duplicate words are purged and no Dialogue events overlap in time."""
    cr = CaptionRenderer()
    segs = [
        TranscriptSegment(
            text="Halo halo dunia dunia",
            start=0.0,
            end=4.0,
            words=[
                Word("Halo", 0.0, 0.5),
                Word("halo", 0.3, 0.7),
                Word("dunia", 1.0, 1.8),
                Word("dunia", 1.2, 1.9),
                Word("indah", 2.0, 2.8),
                Word("sekali", 2.5, 3.5),
            ],
        )
    ]
    ass_content = cr.generate_ass_script(segs, JobConfig(caption_preset="creator_bold"))
    dialogues = [line for line in ass_content.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogues) >= 1
    for d in dialogues:
        text_part = d.split(",", 9)[-1]
        assert "Halo halo" not in text_part
        assert "dunia dunia" not in text_part

    from services.captions.service import parse_ass_time
    for i in range(len(dialogues) - 1):
        d1_end = parse_ass_time(dialogues[i].split(",")[2])
        d2_start = parse_ass_time(dialogues[i + 1].split(",")[1])
        assert d1_end <= d2_start + 0.01, f"Dialogue overlap detected: {d1_end} > {d2_start}"

def test_caption_centisecond_rounding_prevents_zero_duration():
    """Verify that words rounding to the same centisecond do not produce start >= end error."""
    cr = CaptionRenderer()
    segs = [
        TranscriptSegment(
            text="misalnya dengan ee",
            start=35.0,
            end=38.0,
            words=[
                Word("misalnya", 35.5, 36.2),
                Word("dengan", 36.2, 36.996),
                Word("ee", 37.000, 37.003),
            ],
        )
    ]
    ass_text = cr.generate_ass_script(segs, JobConfig(caption_preset="karaoke"))
    dialogues = [line for line in ass_text.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogues) == 3
    last_d = dialogues[-1]
    assert "0:00:37.00,0:00:37.08" in last_d or "0:00:37.00,0:00:37." in last_d
    from services.captions.service import parse_ass_time
    for d in dialogues:
        parts = d.split(",")
        t0 = parse_ass_time(parts[1])
        t1 = parse_ass_time(parts[2])
        assert t0 < t1, f"start >= end detected: {t0} >= {t1} in {d}"
