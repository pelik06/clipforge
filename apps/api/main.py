import asyncio
import datetime
import json
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
    get_connection,
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
from services.render import RenderJobManager, get_preset_config
from services.editor import (
    EditorOperations,
    EditorState,
    EditorStateManager,
    StudioRenderBridge,
)
from core.storage import (
    delete_export_artifact,
    list_export_artifacts,
)
from services.ingest.service import check_media_dependencies

render_manager = RenderJobManager()
editor_state_manager = EditorStateManager()
render_bridge = StudioRenderBridge(render_manager=render_manager)
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
    framing_mode: Optional[str] = "auto_follow_speaker"
    caption_preset: Optional[str] = "clean"
    caption_language: Optional[str] = "auto"
    caption_size: Optional[str] = "large"
    caption_position: Optional[str] = "bottom_safe"
    caption_text_color: Optional[str] = "#FFFFFF"
    caption_highlight_color: Optional[str] = "#FFFF00"
    caption_word_highlight: Optional[bool] = False
    moment_detection_mode: Optional[str] = "heuristic"
    moment_detection_provider: Optional[str] = "heuristic"
    max_clips: Optional[int] = 5
    min_clip_duration: Optional[float] = 45.0
    max_clip_duration: Optional[float] = 120.0
    enable_scene_detection: Optional[bool] = True
    moment_threshold: Optional[float] = 0.45

class DecisionRequest(BaseModel):
    decision: str  # 'approve' or 'reject'


class ClippoSyncRequest(BaseModel):
    clippo_job_id: str
    vod_url: str

class RenderSubmitRequest(BaseModel):
    clip_id: str
    preset: str = "tiktok"
    render_type: str = "final"
    priority: int = 10
    config: Optional[dict] = None


class BatchRenderRequest(BaseModel):
    clip_ids: list[str]
    preset: str = "tiktok"
    render_type: str = "final"
    priority: int = 10


class EditorOperationRequest(BaseModel):
    op: str
    params: dict = {}


class EditorRenderRequest(BaseModel):
    preset: str = "tiktok"


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
    """Return all jobs and clips from persistent storage, filtering out synthetic test runs."""
    all_jobs = list_jobs()
    all_clips = list_clips()
    jobs = [
        j for j in all_jobs
        if not str(j.get("id", "")).startswith("job_test_")
        and "synthetic" not in str(j.get("vod_url", ""))
        and "dQw4w9WgX" not in str(j.get("vod_url", ""))
    ]
    clips = [
        c for c in all_clips
        if not str(c.get("job_id", "")).startswith("job_test_")
    ]
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
        framing_mode=req.framing_mode or "auto_follow_speaker",
        caption_preset=req.caption_preset or "clean",
        caption_language=req.caption_language or "auto",
        caption_size=req.caption_size or "large",
        caption_position=req.caption_position or "bottom_safe",
        caption_text_color=req.caption_text_color or "#FFFFFF",
        caption_highlight_color=req.caption_highlight_color or "#FFFF00",
        caption_word_highlight=bool(req.caption_word_highlight),
        moment_detection_mode=req.moment_detection_mode or "heuristic",
        moment_detection_provider=req.moment_detection_provider or "heuristic",
        max_clips=int(req.max_clips or 5),
        min_clip_duration=float(req.min_clip_duration or 45.0),
        max_clip_duration=float(req.max_clip_duration or 120.0),
        moment_threshold=float(req.moment_threshold or 0.45),
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

@app.post("/api/v4/renders")
async def submit_render(req: RenderSubmitRequest, background_tasks: BackgroundTasks):
    clips = list_clips()
    target_clip = next((c for c in clips if c["id"] == req.clip_id), None)
    if not target_clip:
        for f in FIXTURES_STORE:
            if f["id"] == req.clip_id:
                target_clip = f
                break

    if not target_clip:
        raise HTTPException(status_code=404, detail=f"Clip {req.clip_id} not found")

    # Determine source file
    source_path = target_clip.get("media_url")
    if source_path and source_path.startswith("/media/"):
        source_path = str(Path("data/output") / Path(source_path).name)
    elif not source_path:
        source_path = "data/input/real_talk_35s.mp4"

    cfg = req.config or {}
    if "start_time" not in cfg and target_clip.get("start_time") is not None:
        cfg["start_time"] = target_clip.get("start_time", 0.0)
    if "duration" not in cfg:
        dur_str = str(target_clip.get("duration", "30.0")).replace("s", "")
        try:
            cfg["duration"] = float(dur_str)
        except ValueError:
            cfg["duration"] = 30.0

    try:
        job = render_manager.submit_job(
            clip_id=req.clip_id,
            source_id=source_path,
            preset=req.preset,
            render_type=req.render_type,
            priority=req.priority,
            config=cfg,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

    background_tasks.add_task(render_manager.process_queue_sync, 1)
    return {"status": "queued", "job": job.to_dict()}


@app.get("/api/v4/renders")
def get_renders(status: Optional[str] = None):
    return {"renders": render_manager.list_jobs(status=status)}


@app.get("/api/v4/renders/{job_id}")
def get_render(job_id: str):
    job = render_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    return {"job": job}


@app.post("/api/v4/renders/{job_id}/cancel")
def cancel_render(job_id: str):
    ok = render_manager.cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Render job not found")
    return {"status": "cancelled", "job_id": job_id}


@app.post("/api/v4/renders/{job_id}/retry")
async def retry_render(job_id: str, background_tasks: BackgroundTasks):
    job = render_manager.retry_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found or not retryable")
    background_tasks.add_task(render_manager.process_queue_sync, 1)
    return {"status": "retrying", "job": job.to_dict()}


@app.post("/api/v4/renders/batch")
async def batch_render(req: BatchRenderRequest, background_tasks: BackgroundTasks):
    clips = list_clips()
    created_jobs = []
    for cid in req.clip_ids:
        target_clip = next((c for c in clips if c["id"] == cid), None)
        if not target_clip:
            continue
        source_path = target_clip.get("media_url")
        if source_path and source_path.startswith("/media/"):
            source_path = str(Path("data/output") / Path(source_path).name)
        elif not source_path:
            source_path = "data/input/real_talk_35s.mp4"
        cfg = {"duration": float(str(target_clip.get("duration", "30.0")).replace("s", ""))}
        job = render_manager.submit_job(
            clip_id=cid,
            source_id=source_path,
            preset=req.preset,
            render_type=req.render_type,
            priority=req.priority,
            config=cfg,
        )
        created_jobs.append(job.to_dict())

    background_tasks.add_task(render_manager.process_queue_sync, len(created_jobs))
    return {"status": "queued", "count": len(created_jobs), "jobs": created_jobs}


@app.get("/api/v4/editor/{clip_id}")
def get_editor_state_endpoint(clip_id: str):
    clips = list_clips()
    target_clip = next((c for c in clips if c["id"] == clip_id), None)
    if not target_clip:
        for f in FIXTURES_STORE:
            if f["id"] == clip_id:
                target_clip = f
                break
    if not target_clip:
        raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")

    state = editor_state_manager.load_or_initialize(target_clip)
    return {"status": "success", "state": state.to_dict()}


@app.put("/api/v4/editor/{clip_id}")
def save_editor_state_endpoint(clip_id: str, state_dict: dict):
    state_dict["clip_id"] = clip_id
    try:
        state = EditorState.from_dict(state_dict)
        saved = editor_state_manager.save(state)
        # Sync composition to clips table
        comp_to_sync = state.user_overrides.get("composition") or state.output.get("composition")
        if comp_to_sync:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE clips SET composition_json = ? WHERE id = ?",
                    (json.dumps(comp_to_sync), clip_id),
                )
                conn.commit()
        return {"status": "saved", "state": saved.to_dict()}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@app.post("/api/v4/editor/{clip_id}/operation")
def apply_editor_operation(clip_id: str, req: EditorOperationRequest):
    clips = list_clips()
    target_clip = next((c for c in clips if c["id"] == clip_id), None) or {"id": clip_id}
    state = editor_state_manager.load_or_initialize(target_clip)

    op = req.op.lower()
    p = req.params

    try:
        if op == "trim":
            new_state = EditorOperations.trim(state, float(p["start"]), float(p["end"]))
        elif op == "caption_text":
            new_state = EditorOperations.edit_caption_text(state, str(p["caption_id"]), str(p["text"]))
        elif op == "caption_timing":
            new_state = EditorOperations.edit_caption_timing(state, str(p["caption_id"]), float(p["start"]), float(p["end"]))
        elif op == "caption_add":
            new_state = EditorOperations.add_caption(state, float(p["start"]), float(p["end"]), str(p["text"]), style=p.get("style"), emphasis=bool(p.get("emphasis", False)))
        elif op == "caption_delete":
            new_state = EditorOperations.delete_caption(state, str(p["caption_id"]))
        elif op == "caption_split":
            new_state = EditorOperations.split_caption(state, str(p["caption_id"]), float(p["split_time"]))
        elif op == "caption_merge":
            new_state = EditorOperations.merge_captions(state, str(p["caption_id_1"]), str(p["caption_id_2"]))
        elif op == "crop":
            new_state = EditorOperations.set_crop(state, float(p.get("x", 0.0)), float(p.get("y", 0.0)), float(p.get("width", 1.0)), float(p.get("height", 1.0)), scale=float(p.get("scale", 1.0)), mode=str(p.get("mode", "manual")))
        elif op == "layout":
            new_state = EditorOperations.set_layout(state, str(p["layout"]))
        elif op == "audio":
            new_state = EditorOperations.set_audio(state, volume=float(p.get("volume", 1.0)), mute=bool(p.get("mute", False)), fade_in=float(p.get("fade_in", 0.0)), fade_out=float(p.get("fade_out", 0.0)))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported operation '{op}'")

        saved = editor_state_manager.save(new_state)
        return {"status": "success", "state": saved.to_dict()}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@app.post("/api/v4/editor/{clip_id}/gemini_hook")
def generate_gemini_hook_endpoint(clip_id: str):
    from services.hooks.gemini_hook_generator import GeminiHookGenerator
    from services.editor.models import EditorState
    from core.models.transcript import TranscriptSegment

    clips = list_clips()
    target_clip = next((c for c in clips if c["id"] == clip_id), None)
    if not target_clip:
        for f in FIXTURES_STORE:
            if f["id"] == clip_id:
                target_clip = f
                break
    if not target_clip:
        raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")

    state = editor_state_manager.load_or_initialize(target_clip)
    comp_dict = state.user_overrides.get("composition") or state.output.get("composition") or target_clip.get("composition")
    if not comp_dict:
        from services.render.hyperframes_templates import generate_initial_composition
        comp_obj = generate_initial_composition(target_clip)
        comp_dict = comp_obj.to_dict()

    # Prepare segments from editor captions
    segs = []
    captions = state.captions or []
    for c in captions:
        segs.append(TranscriptSegment(text=c.text, start=c.start, end=c.end))

    generator = GeminiHookGenerator()
    hook_data = generator.generate_hook_and_post(target_clip, transcript_segments=segs)

    # Update hook layer and social post metadata
    layers = comp_dict.get("layers", [])
    hook_layer = next((l for l in layers if l.get("type") == "hook" or l.get("id") == "layer_hook_title"), None)
    if hook_layer:
        hook_layer["data"] = {
            **hook_layer.get("data", {}),
            **hook_data,
        }
    comp_dict["metadata"] = {
        **comp_dict.get("metadata", {}),
        "social_post_caption": hook_data.get("social_post_caption"),
        "hashtags": hook_data.get("hashtags"),
    }

    state.user_overrides["composition"] = comp_dict
    saved_state = editor_state_manager.save(state)

    # Persist in clips DB
    with get_connection() as conn:
        conn.execute(
            "UPDATE clips SET composition_json = ? WHERE id = ?",
            (json.dumps(comp_dict), clip_id),
        )
        conn.commit()

    return {
        "status": "success",
        "hook_data": hook_data,
        "composition": comp_dict,
        "state": saved_state.to_dict(),
    }


@app.post("/api/v4/editor/{clip_id}/preview")
async def render_editor_preview(clip_id: str, req: EditorRenderRequest, background_tasks: BackgroundTasks):
    clips = list_clips()
    target_clip = next((c for c in clips if c["id"] == clip_id), None) or {"id": clip_id}
    state = editor_state_manager.load_or_initialize(target_clip)

    job, snapshot = render_bridge.submit_render(state, preset="preview", render_type="preview", priority=20)
    background_tasks.add_task(render_manager.process_queue_sync, 1)
    return {"status": "queued", "job": job.to_dict(), "snapshot": snapshot.to_dict()}


@app.post("/api/v4/editor/{clip_id}/render")
async def render_editor_final(clip_id: str, req: EditorRenderRequest, background_tasks: BackgroundTasks):
    clips = list_clips()
    target_clip = next((c for c in clips if c["id"] == clip_id), None) or {"id": clip_id}
    state = editor_state_manager.load_or_initialize(target_clip)

    job, snapshot = render_bridge.submit_render(state, preset=req.preset, render_type="final", priority=25)
    background_tasks.add_task(render_manager.process_queue_sync, 1)
    return {"status": "queued", "job": job.to_dict(), "snapshot": snapshot.to_dict()}


@app.get("/api/v4/exports")
def get_export_library(clip_id: Optional[str] = None):
    return {"exports": list_export_artifacts(clip_id=clip_id)}


@app.delete("/api/v4/exports/{export_id}")
def delete_export(export_id: str):
    ok = delete_export_artifact(export_id)
    return {"status": "deleted" if ok else "not_found", "export_id": export_id}
# Mount generated media files directory
media_dir = Path(__file__).resolve().parent.parent.parent / "data" / "output"
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

final_renders_dir = Path(__file__).resolve().parent.parent.parent / "data" / "renders" / "final"
final_renders_dir.mkdir(parents=True, exist_ok=True)
app.mount("/renders", StaticFiles(directory=str(final_renders_dir)), name="renders")

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
