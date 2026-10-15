import pytest
from pathlib import Path
from core.models.transcript import Word
from services.render.hyperframes_composition import HyperframesCompositionBuilder, HyperframesConfig


def test_hyperframes_composition_builder(tmp_path):
    output_dir = tmp_path / "hf_comp_test"
    dummy_video = tmp_path / "dummy_reframe.mp4"
    dummy_video.write_bytes(b"\x00" * 1024)

    words = [
        Word(text="Hello", start=0.5, end=0.9),
        Word(text="World", start=0.95, end=1.4),
        Word(text="HyperFrames", start=1.5, end=2.2),
    ]

    builder = HyperframesCompositionBuilder()
    res_dir = builder.build_composition(
        output_dir=output_dir,
        source_video_path=dummy_video,
        clip_duration=5.0,
        words=words,
        config=HyperframesConfig(title="TEST VIRAL HOOK"),
    )

    assert (res_dir / "index.html").exists()
    assert (res_dir / "hyperframes.json").exists()
    assert (res_dir / "meta.json").exists()
    assert (res_dir / "video.mp4").exists()

    html = (res_dir / "index.html").read_text(encoding="utf-8")
    assert "data-composition-id=\"main\"" in html
    assert "TEST VIRAL HOOK" in html
    assert "HyperFrames" in html
    assert "gsap.timeline" in html
