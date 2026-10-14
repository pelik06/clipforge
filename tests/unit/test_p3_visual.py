import pytest
from services.visual_quality import VisualCompositionAnalyzer


def test_headroom():
    analyzer = VisualCompositionAnalyzer(target_width=1080, target_height=1920)

    # Optimal headroom: face at y=350 (approx 18% of 1920)
    score1, _, _ = analyzer.evaluate_headroom(face_y=350, face_height=300)
    assert score1 >= 90.0

    # Cramped headroom: face at y=50 (approx 2.6% of 1920)
    score2, _, penalties2 = analyzer.evaluate_headroom(face_y=50, face_height=300)
    assert score2 <= 65.0
    assert any("headroom" in p.lower() for p in penalties2)


def test_face_size():
    analyzer = VisualCompositionAnalyzer(target_width=1080, target_height=1920)

    # Optimal face size: height = 350px (approx 18% of 1920)
    score1, _, _ = analyzer.evaluate_face_size(face_height=350)
    assert score1 >= 90.0

    # Distant / tiny face: height = 80px (approx 4% of 1920)
    score2, _, penalties2 = analyzer.evaluate_face_size(face_height=80)
    assert score2 <= 55.0
    assert any("small" in p.lower() for p in penalties2)


def test_caption_collision():
    analyzer = VisualCompositionAnalyzer(target_width=1080, target_height=1920)

    # Collision detected -> score penalized
    faces = [(400.0, 350.0, 280.0, 320.0)]
    res_clean = analyzer.evaluate(faces=faces, caption_face_collision=False)
    res_collided = analyzer.evaluate(faces=faces, caption_face_collision=True)

    assert res_clean.visual_quality_score > res_collided.visual_quality_score
    assert any("collides" in p.lower() for p in res_collided.penalties)
