import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from apps.api.main import app, validate_vod_input
from core.storage import save_job, get_job, list_clips
from services.ingest.service import check_media_dependencies, extract_youtube_metadata
from apps.worker.pipeline_runner import execute_job_pipeline_sync


@pytest.fixture
def client():
    return TestClient(app)


def test_validate_vod_input():
    # Valid YouTube URLs
    assert validate_vod_input("https://www.youtube.com/watch?v=dQw4w9WgXcQ")[0] is True
    assert validate_vod_input("https://youtu.be/dQw4w9WgXcQ")[0] is True
    assert validate_vod_input("https://youtube.com/shorts/dQw4w9WgXcQ")[0] is True

    # Valid local files
    assert validate_vod_input("C:/Videos/stream.mp4")[0] is True
    assert validate_vod_input("data/input/vod.mkv")[0] is True

    # Invalid inputs
    assert validate_vod_input("")[0] is False
    assert validate_vod_input("ftp://badurl")[0] is False
    assert validate_vod_input("https://example.com/not-youtube")[0] is False


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_system_status(client):
    res = client.get("/api/v4/system")
    assert res.status_code == 200
    data = res.json()
    assert "dependencies" in data
    assert "ytdlp_available" in data["dependencies"]
    assert data["dependencies"]["ytdlp_available"] is True


def test_check_media_dependencies():
    deps = check_media_dependencies()
    assert isinstance(deps, dict)
    assert "ffmpeg_available" in deps
    assert "ytdlp_available" in deps
    assert deps["ffmpeg_available"] is True
    assert deps["ytdlp_available"] is True


def test_create_job_invalid_url(client):
    res = client.post("/api/v4/jobs", json={"vod_url": "invalid_url_string"})
    assert res.status_code == 400
    assert "Invalid video URL" in res.json()["detail"]


def test_create_job_and_get_single_job(client):
    res = client.post("/api/v4/jobs", json={"vod_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
    assert res.status_code == 200
    data = res.json()
    job_id = data["job"]["id"]

    # Fetch single job by ID
    single_res = client.get(f"/api/v4/jobs/{job_id}")
    assert single_res.status_code == 200
    s_data = single_res.json()
    assert s_data["job"]["id"] == job_id
    assert "stages" in s_data["job"]
    assert len(s_data["job"]["stages"]) == 13

    # Nonexistent job
    missing_res = client.get("/api/v4/jobs/nonexistent_job_999")
    assert missing_res.status_code == 404


def test_decision_endpoint_validation(client):
    # Nonexistent clip
    res = client.post("/api/v4/jobs/nonexistent_clip/decision", json={"decision": "approve"})
    assert res.status_code == 404

    # Invalid decision string
    res = client.post("/api/v4/jobs/fixture_001/decision", json={"decision": "auto_publish"})
    assert res.status_code == 400
    assert "Decision must be 'approve' or 'reject'" in res.json()["detail"]

    # Valid decision: approve
    res = client.post("/api/v4/jobs/fixture_001/decision", json={"decision": "approve"})
    assert res.status_code == 200
    assert res.json()["decision"] == "APPROVED"

    # Valid decision: reject
    res = client.post("/api/v4/jobs/fixture_002/decision", json={"decision": "reject"})
    assert res.status_code == 200
    assert res.json()["decision"] == "REJECTED"


def test_pipeline_runner_failure_handling(tmp_path):
    # Passing an unreadable/invalid file path should mark stage failed and record error
    job_id = "test_fail_job_001"
    bad_source = tmp_path / "corrupt.mp4"
    # File doesn't exist
    job = execute_job_pipeline_sync(job_id, str(bad_source), kind="local")
    assert job["status"] == "failed"
    assert job["stages"][0]["status"] == "failed"
    assert job["error"] is not None
