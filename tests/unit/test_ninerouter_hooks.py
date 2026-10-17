import io
import json
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch
import pytest

from services.llm.ninerouter_service import NineRouterService


class DummySegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


def test_fallback_without_api_key():
    service = NineRouterService(api_key="")
    assert not service.is_enabled

    clip = {
        "title": "Bongkar Rahasia Timothy Ronald Cuan Kripto",
        "vod": "vod_123",
        "start_time": 10.0,
        "end_time": 40.0,
        "duration": 30.0,
    }
    segments = [
        DummySegment(5.0, 9.5, "Halo selamat datang"),
        DummySegment(12.0, 18.0, "Gua bocorin rahasia cuan 4 miliar dari crypto"),
        DummySegment(20.0, 25.0, "Ini parah banget sih"),
        DummySegment(50.0, 55.0, "Jangan lupa subscribe"),
    ]

    hook = service.generate_clip_hook(clip, segments)
    assert hook["is_fallback"] is True
    assert "top_tag" in hook
    assert "badge_tag" in hook
    assert "highlight_text" in hook
    assert "sub_text" in hook
    assert "punchline" in hook
    assert "social_post_caption" in hook
    assert isinstance(hook["hashtags"], list)
    assert len(hook["hashtags"]) > 0


def test_mock_ninerouter_chat_completions_success():
    service = NineRouterService(api_key="test-9router-key", base_url="https://api.9router.com/v1")
    assert service.is_enabled

    clip = {
        "title": "Rahasia Timothy Ronald",
        "uploader": "Timothy Ronald",
        "start_time": 100.0,
        "end_time": 150.0,
        "duration": 50.0,
    }
    segments = [
        DummySegment(105.0, 115.0, "Gua beli coin ini terus langsung terbang to the moon modal 10 juta jadi 1 miliar"),
    ]

    mock_llm_content = {
        "top_tag": "TIMOTHY",
        "badge_tag": "BOCORIN RAHASIA",
        "highlight_text": "CUAN 1 MILIAR",
        "sub_text": "DARI MODAL 10 JUTA",
        "punchline": "TO THE MOON!",
        "social_post_caption": "Rahasia Timothy cuan 1 miliar dari coin receh! Simak penjelasannya sampai habis.",
        "hashtags": ["#crypto", "#timothyronald", "#cuan", "#investasi"],
    }

    mock_response_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(mock_llm_content),
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.read.return_value = json.dumps(mock_response_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        hook = service.generate_clip_hook(clip, segments)

        assert hook["is_fallback"] is False
        assert hook["top_tag"] == "TIMOTHY"
        assert hook["badge_tag"] == "BOCORIN RAHASIA"
        assert hook["highlight_text"] == "CUAN 1 MILIAR"
        assert hook["sub_text"] == "DARI MODAL 10 JUTA"
        assert hook["punchline"] == "TO THE MOON!"
        assert "Rahasia Timothy" in hook["social_post_caption"]
        assert "#crypto" in hook["hashtags"]

        # Verify request sent
        assert mock_urlopen.called
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") == "Bearer test-9router-key"
        assert req.get_header("Content-type") == "application/json"


def test_exact_timestamp_boundary_filtering():
    service = NineRouterService(api_key="")
    segments = [
        DummySegment(0.0, 10.0, "Too early seg 1"),
        DummySegment(9.9, 10.0, "Exact touch seg 2"),
        DummySegment(10.0, 15.0, "Inside seg 3"),
        DummySegment(18.0, 22.0, "Inside seg 4"),
        DummySegment(25.0, 35.0, "Overlap right seg 5"),
        DummySegment(35.0, 40.0, "Too late seg 6"),
    ]

    # Clip window: 10.0 to 30.0
    filtered = service.filter_clip_segments(segments, clip_start=10.0, clip_end=30.0)
    texts = [s.text for s in filtered]

    assert "Too early seg 1" not in texts
    assert "Exact touch seg 2" not in texts
    assert "Inside seg 3" in texts
    assert "Inside seg 4" in texts
    assert "Overlap right seg 5" in texts
    assert "Too late seg 6" not in texts


def test_provider_error_timeout_malformed_json_fallback():
    service = NineRouterService(api_key="test-key")
    clip = {"title": "Test Title", "start_time": 0.0, "end_time": 20.0, "duration": 20.0}
    segments = [DummySegment(1.0, 5.0, "Test dialogue")]

    # 1. Timeout / URLError
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection timed out")):
        hook1 = service.generate_clip_hook(clip, segments)
        assert hook1["is_fallback"] is True
        assert hook1["top_tag"]

    # 2. HTTP 500 error
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 500, "Server Error", {}, io.BytesIO(b""))):
        hook2 = service.generate_clip_hook(clip, segments)
        assert hook2["is_fallback"] is True

    # 3. Malformed JSON response body
    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.read.return_value = b"{bad json"
    mock_resp.__enter__.return_value = mock_resp
    with patch("urllib.request.urlopen", return_value=mock_resp):
        hook3 = service.generate_clip_hook(clip, segments)
        assert hook3["is_fallback"] is True

    # 4. Missing required keys in assistant content
    mock_resp2 = MagicMock()
    mock_resp2.getcode.return_value = 200
    mock_resp2.read.return_value = json.dumps({
        "choices": [{"message": {"content": json.dumps({"incomplete": "data"})}}]
    }).encode("utf-8")
    mock_resp2.__enter__.return_value = mock_resp2
    with patch("urllib.request.urlopen", return_value=mock_resp2):
        hook4 = service.generate_clip_hook(clip, segments)
        assert hook4["is_fallback"] is True
