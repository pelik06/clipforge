import asyncio
import datetime
import os
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.models.configuration import JobConfig
from core.storage import (
    get_job,
    list_clips,
    list_jobs,
    save_job,
    update_clip_decision,
)
from apps.worker.pipeline_runner import (
    create_initial_stages,
    execute_job_pipeline_sync,
)
from services.ingest.service import check_media_dependencies

app = FastAPI(title="ClipForge API", version="0.4.0")

# Enable CORS for Next.js frontend (port 3000) and other dev origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Demo fixtures clearly marked and segregated from real generated clips
FIXTURES_STORE = [
    {
        "id": "fixture_001",
        "job_id": "job_fixture_stream_402",
        "title": "Epic 1v5 Clutch in Final Zone",
        "duration": "18.4s",
        "score": "94/100",
        "status": "WAITING_APPROVAL",
        "vod": "Stream VOD #402 (Demo)",
        "is_fixture": True,
        "is_real_media": False,
        "media_type": "fixture",
        "render_status": "demo_fixture",
        "render_notice": "Sample development fixture for testing operator review and approval flows.",
        "media_url": None,
        "start_time": 10.0,
        "end_time": 28.4,
        "resolution": "1080x1920",
        "qc_checks": {"container": True, "codec": "h264", "duration": 18.4},
        "created_at": "2026-10-12T10:00:00Z",
    },
    {
        "id": "fixture_002",
        "job_id": "job_fixture_stream_402",
        "title": "Hilarious Streamer Reaction to Jumpscare",
        "duration": "12.1s",
        "score": "88/100",
        "status": "WAITING_APPROVAL",
        "vod": "Stream VOD #402 (Demo)",
        "is_fixture": True,
        "is_real_media": False,
        "media_type": "fixture",
        "render_status": "demo_fixture",
        "render_notice": "Sample development fixture for testing operator review and approval flows.",
        "media_url": None,
        "start_time": 45.0,
        "end_time": 57.1,
        "resolution": "1080x1920",
        "qc_checks": {"container": True, "codec": "h264", "duration": 12.1},
        "created_at": "2026-10-12T10:05:00Z",
    },
]

# Validation patterns
YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/(watch\?.*v=|shorts/|live/)|youtu\.be/)[a-zA-Z0-9_-]{11}(.*)?$",
    re.IGNORECASE,
)
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".webm", ".avi", ".flv")


def validate_vod_input(url_or_path: str) -> tuple[bool, str, str]:
    """Validate input as supported YouTube URL or local video file."""
    clean = url_or_path.strip()
    if not clean:
        return False, "", "Video URL or file path cannot be empty."

    if YOUTUBE_REGEX.match(clean):
        return True, "youtube", ""

    path = Path(clean)
    if clean.lower().endswith(VIDEO_EXTENSIONS):
        return True, "local", ""
    if path.exists() and path.is_file():
        return True, "local", ""

    return (
        False,
        "",
        "Invalid video URL or file path. Please enter a valid public YouTube URL (e.g., https://www.youtube.com/watch?v=... or https://youtu.be/...) or a local video file (.mp4, .mkv, .mov).",
    )


class JobCreateRequest(BaseModel):
    vod_url: str
    framing_mode: Optional[str] = "center_crop"
    caption_preset: Optional[str] = "clean"
    caption_language: Optional[str] = "auto"
    caption_size: Optional[str] = "medium"
    caption_position: Optional[str] = "bottom_safe"
    caption_text_color: Optional[str] = "#FFFFFF"
    caption_highlight_color: Optional[str] = "#FFFF00"
    caption_word_highlight: Optional[bool] = False
    moment_detection_mode: Optional[str] = "heuristic"
    moment_detection_provider: Optional[str] = "gemini"
    max_clips: Optional[int] = 5
    min_clip_duration: Optional[float] = 12.0
    max_clip_duration: Optional[float] = 60.0
    enable_scene_detection: Optional[bool] = True

class DecisionRequest(BaseModel):
    decision: str  # 'approve' or 'reject'


class ClippoSyncRequest(BaseModel):
    clippo_job_id: str
    vod_url: str


async def run_pipeline_background(job_id: str, vod_url: str, kind: str, config: Optional[dict] = None):
    """Run the 13-stage pipeline in an async executor thread."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, execute_job_pipeline_sync, job_id, vod_url, kind, config)


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "0.4.0"}


@app.get("/api/v4/system")
def system_status():
    """Return media engine dependencies and system status."""
    deps = check_media_dependencies()
    jobs = list_jobs()
    clips = list_clips()
    return {
        "status": "healthy",
        "version": "0.4.0",
        "dependencies": deps,
        "counts": {
            "jobs": len(jobs),
            "clips": len(clips),
            "fixtures": len(FIXTURES_STORE),
        },
    }


@app.get("/api/v4/jobs")
def get_all_jobs(include_fixtures: bool = False):
    """Return all jobs and clips from persistent storage."""
    jobs = list_jobs()
    clips = list_clips()
    return {
        "jobs": jobs,
        "clips": clips,
        "fixtures": FIXTURES_STORE,
    }


@app.get("/api/v4/jobs/{job_id}")
def get_single_job(job_id: str):
    """Return detailed job record with all 13 stages and associated clips."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    clips = list_clips(job_id=job_id)
    return {
        "job": job,
        "clips": clips,
    }


@app.post("/api/v4/jobs")
async def create_job(req: JobCreateRequest, background_tasks: BackgroundTasks):
    is_valid, kind, err_msg = validate_vod_input(req.vod_url)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err_msg)

    # Strict configuration validation
    cfg = JobConfig(
        framing_mode=req.framing_mode or "center_crop",
        caption_preset=req.caption_preset or "clean",
        caption_language=req.caption_language or "auto",
        caption_size=req.caption_size or "medium",
        caption_position=req.caption_position or "bottom_safe",
        caption_text_color=req.caption_text_color or "#FFFFFF",
        caption_highlight_color=req.caption_highlight_color or "#FFFF00",
        caption_word_highlight=bool(req.caption_word_highlight),
        moment_detection_mode=req.moment_detection_mode or "heuristic",
        moment_detection_provider=req.moment_detection_provider or "gemini",
        max_clips=int(req.max_clips or 5),
        min_clip_duration=float(req.min_clip_duration or 12.0),
        max_clip_duration=float(req.max_clip_duration or 60.0),
        enable_scene_detection=bool(req.enable_scene_detection if req.enable_scene_detection is not None else True),
    )
    try:
        cfg.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Configuration error: {str(exc)}")

    clean_url = req.vod_url.strip()
    existing_jobs = list_jobs()
    active_dupe = next(
        (j for j in existing_jobs if j["vod_url"] == clean_url and j["status"] == "processing"),
        None,
    )
    if active_dupe:
        return {
            "job": active_dupe,
            "message": "A job for this source is already actively processing.",
        }

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    initial_stages = create_initial_stages()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    config_dict = {
        "framing_mode": cfg.framing_mode,
        "caption_preset": cfg.caption_preset,
        "caption_language": cfg.caption_language,
        "caption_size": cfg.caption_size,
        "caption_position": cfg.caption_position,
        "caption_text_color": cfg.caption_text_color,
        "caption_highlight_color": cfg.caption_highlight_color,
        "caption_highlight_color": cfg.caption_highlight_color,
        "caption_word_highlight": cfg.caption_word_highlight,
        "moment_detection_mode": cfg.moment_detection_mode,
        "moment_detection_provider": cfg.moment_detection_provider,
        "max_clips": cfg.max_clips,
        "min_clip_duration": cfg.min_clip_duration,
        "max_clip_duration": cfg.max_clip_duration,
        "enable_scene_detection": cfg.enable_scene_detection,
    }

    new_job = {
        "id": job_id,
        "vod_url": clean_url,
        "kind": kind,
        "status": "created",
        "stage": "Job queued for pipeline execution",
        "progress": 5,
        "created_at": now_iso,
        "updated_at": now_iso,
        "error": None,
        "metadata": {},
        "stages": initial_stages,
        **config_dict,
    }
    save_job(new_job)

    background_tasks.add_task(run_pipeline_background, job_id, clean_url, kind, config_dict)

    return {
        "job": new_job,
        "message": "Clipping job successfully queued across 13 stages. Track live progress via /api/v4/jobs/{id}.",
    }


@app.post("/api/v4/jobs/{clip_id}/decision")
def clip_decision(clip_id: str, req: DecisionRequest):
    dec = req.decision.strip().lower()
    if dec not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")

    # Invariants P4 & R2: Human approval is mandatory before publishing
    decision_status = "APPROVED" if dec == "approve" else "REJECTED"

    updated_clip = update_clip_decision(clip_id, decision_status)
    if not updated_clip:
        for f in FIXTURES_STORE:
            if f["id"] == clip_id:
                f["status"] = decision_status
                f["reviewed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                updated_clip = f
                break

    if not updated_clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    return {
        "status": "success",
        "clip_id": clip_id,
        "decision": decision_status,
        "clip": updated_clip,
        "message": f"Clip {clip_id} successfully {decision_status.lower()} with human operator sign-off.",
    }


@app.post("/api/v4/clippo/sync")
async def sync_clippo_task(req: ClippoSyncRequest, background_tasks: BackgroundTasks):
    job_id = f"clippo_{req.clippo_job_id}"
    clean_url = req.vod_url.strip()
    initial_stages = create_initial_stages()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    new_job = {
        "id": job_id,
        "vod_url": clean_url,
        "kind": "clippo",
        "status": "processing",
        "stage": f"Synchronized from Clippo.id task {req.clippo_job_id}",
        "progress": 5,
        "created_at": now_iso,
        "updated_at": now_iso,
        "error": None,
        "metadata": {"clippo_job_id": req.clippo_job_id},
        "stages": initial_stages,
    }
    save_job(new_job)

    background_tasks.add_task(run_pipeline_background, job_id, clean_url, "clippo")

    return {
        "status": "queued",
        "clippo_job_id": req.clippo_job_id,
        "job": new_job,
        "message": "Successfully synchronized with clippo.id and queued 13-stage pipeline.",
    }


# Mount generated media files directory
media_dir = Path(__file__).resolve().parent.parent.parent / "data" / "output"
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

# Mount static Next.js export if present
out_dir = Path(__file__).resolve().parent.parent.parent / "apps" / "web" / "out"
if out_dir.exists():
    next_static_dir = out_dir / "_next"
    if next_static_dir.exists():
        app.mount("/_next", StaticFiles(directory=str(next_static_dir)), name="next_assets")

    @app.get("/", response_class=HTMLResponse)
    def serve_next_root():
        index_file = out_dir / "index.html"
        if index_file.exists():
            return index_file.read_text(encoding="utf-8")
        return "ClipForge Dashboard"


def main() -> None:
    import uvicorn
    uvicorn.run("apps.api.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
