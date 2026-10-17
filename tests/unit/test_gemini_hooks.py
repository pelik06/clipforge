"""Unit tests for Gemini AI Studio Hook & Social Post Generator."""

import json
from unittest.mock import patch, MagicMock
from core.models.transcript import TranscriptSegment
from services.hooks.gemini_hook_generator import GeminiHookGenerator
from services.render.hyperframes_templates import generate_initial_composition


def test_gemini_hook_fallback_without_api_key():
    """Without an API key, generator must use local dialogue keyword extraction without raising errors."""
    gen = GeminiHookGenerator(api_key="")
    assert not gen.is_enabled

    clip = {
        "id": "clip_test_1",
        "title": "Highlight #1: Rahasia Cuan Miliar Dari Kripto [0.0s-30.0s]",
        "start_time": 0.0,
        "end_time": 30.0,
        "duration": "30.0s",
        "vod": "https://youtu.be/dummy",
    }
    segs = [
        TranscriptSegment(text="halo semua selamat datang", start=0.0, end=3.0),
        TranscriptSegment(text="ini kayak palsu gitu padahal untung 4 miliar", start=3.5, end=8.0),
        TranscriptSegment(text="gara-gara beli meme coin fresh wallet", start=8.5, end=14.0),
    ]

    res = gen.generate_hook_and_post(clip, transcript_segments=segs)
    assert isinstance(res, dict)
    assert "top_tag" in res
    assert "badge_tag" in res
    assert "highlight_text" in res
    assert "sub_text" in res
    assert "punchline" in res
    assert "social_post_caption" in res
    assert isinstance(res["hashtags"], list)
    assert len(res["hashtags"]) >= 3
    assert res["intro_blur_grayscale"] is True


def test_gemini_hook_with_mock_response():
    """When Gemini returns structured JSON, it must parse all fields cleanly."""
    mock_payload = {
        "top_tag": "TIMOTHY",
        "badge_tag": "DI RECALL RECALL",
        "highlight_text": "DEPAN MUKA",
        "sub_text": "SAMPE DIUSIR",
        "punchline": "SECURITY!",
        "social_post_caption": "Gak nyangka bisa terjadi hal segila ini di depan mata! Tonton sampai habis biar paham kronologinya.",
        "hashtags": ["#viral", "#timothy", "#security", "#fyp", "#shorts"],
    }

    gen = GeminiHookGenerator(api_key="fake-test-key")
    assert gen.is_enabled

    with patch.object(gen, "_call_gemini_api", return_value=json.dumps(mock_payload)):
        clip = {"id": "clip_test_2", "start_time": 0.0, "end_time": 20.0, "duration": "20.0s"}
        res = gen.generate_hook_and_post(clip, transcript_segments=[])
        assert res["top_tag"] == "TIMOTHY"
        assert res["badge_tag"] == "DI RECALL RECALL"
        assert res["highlight_text"] == "DEPAN MUKA"
        assert res["sub_text"] == "SAMPE DIUSIR"
        assert res["punchline"] == "SECURITY!"
        assert "Gak nyangka" in res["social_post_caption"]
        assert "#viral" in res["hashtags"]


def test_gemini_hook_with_malformed_json_fallback():
    """When Gemini returns unparseable or error response, it must fallback safely."""
    gen = GeminiHookGenerator(api_key="fake-test-key")
    with patch.object(gen, "_call_gemini_api", return_value="Invalid non-json response"):
        clip = {
            "id": "clip_test_3",
            "title": "Highlight: Taktik Catur Paling Gila",
            "start_time": 0.0,
            "end_time": 15.0,
            "duration": "15.0s",
        }
        res = gen.generate_hook_and_post(clip, transcript_segments=[])
        assert isinstance(res, dict)
        assert res["highlight_text"] != ""
        assert res["punchline"] != ""


def test_gemini_hook_integration_with_hyperframes_templates():
    """Initial composition generation must embed hook and social post data into hook layer."""
    clip = {
        "id": "clip_test_4",
        "title": "Investasi Cuan Miliar Dari Kripto",
        "start_time": 0.0,
        "end_time": 25.0,
        "duration": "25.0s",
        "vod": "https://youtu.be/dummy",
    }
    segs = [
        TranscriptSegment(text="kita verify secara onchain fresh wallet", start=1.0, end=6.0),
    ]

    comp = generate_initial_composition(clip, transcript_segments=segs)
    hook_layer = comp.get_layer("layer_hook_title")
    assert hook_layer is not None
    assert "top_tag" in hook_layer.data
    assert "highlight_text" in hook_layer.data
    assert "social_post_caption" in hook_layer.data
    assert "hashtags" in hook_layer.data
