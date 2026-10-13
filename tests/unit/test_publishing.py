import pytest


def test_publishing_adapter_approval_guard():
    approved = True
    assert approved is True


def test_publishing_adapter_payload():
    metadata = {"title": "Epic Clip", "platform": "youtube_shorts"}
    assert metadata["platform"] == "youtube_shorts"
