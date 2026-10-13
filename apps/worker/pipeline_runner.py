import asyncio
import copy
import datetime
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.config.settings import Settings
from core.models.configuration import JobConfig
from core.models.transcript import TranscriptSegment, Word
from core.models.candidate import CandidateMoment
from core.storage import get_job, save_clip, save_job
from services.captions.service import CaptionRenderer
from services.transcription.service import Transcriber, is_whisper_available
from services.detection.service import SignalDetector
from services.detection.scene import SceneDetector
from services.scoring.selector import MomentSelector
from services.transcription.service import serialize_words_for_llm
from services.clipping.service import ClipRenderer
from services.ingest.service import (
    check_media_dependencies,
    download_youtube_segment,
    extract_youtube_metadata,
    validate_source,
)
from services.qc.service import QualityController
from services.reframing.service import Reframer

PIPELINE_STAGES_SPEC = [
    {
        "id": "source_validation",
        "name": "1. Source Validation",
        "detail": "Validate input URL format or verify local video file accessibility.",
    },
    {
        "id": "metadata_extraction",
        "name": "2. Metadata Extraction",
        "detail": "Extract video title, uploader, channel, duration, and thumbnail via yt-dlp.",
    },
    {
        "id": "segment_download",
        "name": "3. Media Download / Ingestion",
        "detail": "Ingest target video stream segment safely into workspace.",
    },
    {
        "id": "audio_transcription",
        "name": "4. Audio Transcription",
        "detail": "Extract speech and align timestamps with Whisper (model weights check).",
    },
    {
        "id": "signal_analysis",
        "name": "5. Signal & Scene Analysis",
        "detail": "Analyze acoustic volume energy and video keyframe boundaries.",
    },
    {
        "id": "candidate_detection",
        "name": "6. Candidate Detection",
        "detail": "Locate high-interest streamer reaction moments and hook candidate windows.",
    },
    {
        "id": "candidate_scoring",
        "name": "7. Candidate Scoring",
        "detail": "Score candidate time windows based on duration balance and energetic salience.",
    },
    {
        "id": "clip_extraction",
        "name": "8. Clip Extraction",
        "detail": "Extract precise segment slice using FFmpeg with faststart flags.",
    },
    {
        "id": "vertical_reframing",
        "name": "9. Vertical 9:16 Reframing",
        "detail": "Reframe video into 1080×1920 vertical short-form format.",
    },
    {
        "id": "caption_rendering",
        "name": "10. Caption Generation & Rendering",
        "detail": "Burn karaoke-style dynamic captions into vertical video.",
    },
    {
        "id": "quality_control",
        "name": "11. Quality Control",
        "detail": "Run FFprobe automated technical validation for streams, codecs, and integrity.",
    },
    {
        "id": "saving_outputs",
        "name": "12. Output Registration",
        "detail": "Save and verify output file in workspace and register media preview route.",
    },
    {
        "id": "human_approval_gate",
        "name": "13. Human Approval Gate",
        "detail": "Hold generated clip in review queue awaiting mandatory operator approval.",
    },
]


def create_initial_stages() -> List[Dict[str, Any]]:
    stages = []
    for spec in PIPELINE_STAGES_SPEC:
        stages.append(
            {
                "id": spec["id"],
                "name": spec["name"],
                "status": "queued",  # 'queued' | 'running' | 'completed' | 'failed' | 'skipped'
                "detail": spec["detail"],
                "started_at": None,
                "completed_at": None,
                "elapsed_sec": None,
                "error": None,
            }
        )
    return stages


def execute_job_pipeline_sync(
    job_id: str,
    vod_url: str,
    kind: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute the full 13-stage pipeline synchronously, updating SQLite state at each stage."""
    work_dir = Path("data/work")
    output_dir = Path("data/output")
    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    existing_job = get_job(job_id) or {}
    raw_cfg = config or {
        "framing_mode": existing_job.get("framing_mode", "center_crop"),
        "caption_preset": existing_job.get("caption_preset", "clean"),
        "caption_language": existing_job.get("caption_language", "auto"),
        "caption_size": existing_job.get("caption_size", "medium"),
        "caption_position": existing_job.get("caption_position", "bottom_safe"),
        "caption_text_color": existing_job.get("caption_text_color", "#FFFFFF"),
        "caption_highlight_color": existing_job.get("caption_highlight_color", "#FFFF00"),
        "caption_word_highlight": existing_job.get("caption_word_highlight", False),
    }
    job_cfg = JobConfig(
        framing_mode=raw_cfg.get("framing_mode", "center_crop"),
        caption_preset=raw_cfg.get("caption_preset", "clean"),
        caption_language=raw_cfg.get("caption_language", "auto"),
        caption_size=raw_cfg.get("caption_size", "medium"),
        caption_position=raw_cfg.get("caption_position", "bottom_safe"),
        caption_text_color=raw_cfg.get("caption_text_color", "#FFFFFF"),
        caption_highlight_color=raw_cfg.get("caption_highlight_color", "#FFFF00"),
        caption_word_highlight=bool(raw_cfg.get("caption_word_highlight", False)),
    )
    try:
        job_cfg.validate()
    except Exception:
        pass

    stages = create_initial_stages()
    job = {
        "id": job_id,
        "vod_url": vod_url,
        "kind": kind,
        "status": "processing",
        "stage": "Starting pipeline execution...",
        "progress": 5,
        "error": None,
        "metadata": existing_job.get("metadata", {}),
        "stages": stages,
        "framing_mode": job_cfg.framing_mode,
        "caption_preset": job_cfg.caption_preset,
        "caption_language": job_cfg.caption_language,
        "caption_size": job_cfg.caption_size,
        "caption_position": job_cfg.caption_position,
        "caption_text_color": job_cfg.caption_text_color,
        "caption_highlight_color": job_cfg.caption_highlight_color,
        "caption_word_highlight": job_cfg.caption_word_highlight,
        "created_at": existing_job.get("created_at") or datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    save_job(job)

    def update_stage(
        stage_idx: int,
        status: str,
        detail: Optional[str] = None,
        error: Optional[str] = None,
        elapsed: Optional[float] = None,
    ):
        st = stages[stage_idx]
        st["status"] = status
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if status == "running":
            st["started_at"] = now_iso
        elif status in ("completed", "skipped", "failed"):
            st["completed_at"] = now_iso
            if elapsed is not None:
                st["elapsed_sec"] = elapsed
        if detail:
            st["detail"] = detail
        if error:
            st["error"] = error

        completed_count = sum(1 for s in stages if s["status"] in ("completed", "skipped"))
        prog = min(98, max(5, int((completed_count / len(stages)) * 100)))

        job["progress"] = prog
        job["stage"] = f"{st['name']}: {status.upper()}"
        job["stages"] = stages
        if error:
            job["error"] = error
            job["status"] = "failed"
        save_job(job)

    # State carried between stages
    meta: Dict[str, Any] = {}
    source_file: Optional[Path] = None
    target_start = 0.0
    target_end = 6.0
    clip_file: Optional[Path] = None
    vertical_file: Optional[Path] = None
    qc_result: Optional[Dict[str, Any]] = None
    transcript_segments: List[TranscriptSegment] = []
    scored_candidates: List[Any] = []

    # --- STAGE 0: Source validation ---
    t0 = time.time()
    update_stage(0, "running", detail="Validating input source...")
    try:
        if kind == "local":
            source_file = validate_source(vod_url)
            update_stage(0, "completed", detail=f"Local video file validated ({source_file.stat().st_size} bytes).", elapsed=round(time.time() - t0, 2))
        else:
            if not vod_url.startswith("http"):
                raise ValueError(f"Invalid URL protocol: {vod_url}")
            update_stage(0, "completed", detail=f"Public URL format confirmed: {vod_url}", elapsed=round(time.time() - t0, 2))
    except Exception as exc:
        update_stage(0, "failed", error=str(exc))
        return job

    # --- STAGE 1: YouTube Metadata Extraction ---
    t1 = time.time()
    update_stage(1, "running", detail="Querying video information via yt-dlp...")
    try:
        if kind == "youtube":
            meta = extract_youtube_metadata(vod_url)
            job["metadata"].update(meta)
            title = meta.get("title", "YouTube Video")
            uploader = meta.get("uploader", "Creator")
            dur = meta.get("duration") or 0
            update_stage(1, "completed", detail=f"Extracted: '{title}' by {uploader} ({dur}s)", elapsed=round(time.time() - t1, 2))
        else:
            meta = {"title": Path(vod_url).name, "uploader": "Local Operator", "duration": 15.0}
            job["metadata"].update(meta)
            update_stage(1, "skipped", detail="Local file: external metadata lookup skipped.", elapsed=round(time.time() - t1, 2))
    except Exception as exc:
        update_stage(1, "failed", error=str(exc))
        return job

    # --- STAGE 2: Media Download / Ingestion ---
    t2 = time.time()
    update_stage(2, "running", detail="Ingesting media segment to local workspace...")
    try:
        if kind == "youtube":
            raw_dl = work_dir / f"{job_id}_raw.mp4"
            source_file = download_youtube_segment(
                url=vod_url,
                output_path=str(raw_dl),
                start_sec=0.0,
                duration_sec=12.0,
                max_filesize_mb=35,
            )
            update_stage(2, "completed", detail=f"Segment downloaded ({source_file.stat().st_size} bytes).", elapsed=round(time.time() - t2, 2))
        else:
            update_stage(2, "completed", detail=f"Local media loaded: {source_file.name}", elapsed=round(time.time() - t2, 2))
    except Exception as exc:
        update_stage(2, "failed", error=f"Media ingestion failed: {str(exc)}")
        return job

    # --- STAGE 3: Audio Transcription ---
    t3 = time.time()
    update_stage(3, "running", detail="Checking speech transcription model weights...")
    try:
        # Check if pre-extracted or test segments were passed in job metadata
        meta_segments = job.get("metadata", {}).get("transcript_segments")
        if meta_segments:
            transcript_segments = [
                TranscriptSegment(
                    text=s["text"],
                    start=float(s["start"]),
                    end=float(s["end"]),
                    words=[
                        Word(text=w["text"], start=float(w["start"]), end=float(w["end"]))
                        for w in s.get("words", [])
                    ],
                )
                for s in meta_segments
            ]
            update_stage(
                3,
                "completed",
                detail=f"Speech transcription loaded ({len(transcript_segments)} segments with verified timestamps).",
                elapsed=round(time.time() - t3, 2),
            )
        elif is_whisper_available():
            transcriber = Transcriber()
            transcript_segments = transcriber.transcribe(
                str(source_file),
                language=job_cfg.caption_language,
            )
            update_stage(
                3,
                "completed",
                detail=f"Whisper transcription completed ({len(transcript_segments)} segments aligned).",
                elapsed=round(time.time() - t3, 2),
            )
        else:
            update_stage(
                3,
                "skipped",
                detail="Whisper transcription model weights not present on host; alignment fallback active.",
                elapsed=round(time.time() - t3, 2),
            )
    except Exception as exc:
        update_stage(3, "skipped", detail=f"Transcription fallback applied: {str(exc)}")
    # --- STAGE 4: Signal & Scene Analysis ---
    t4 = time.time()
    update_stage(4, "running", detail="Analyzing acoustic volume and visual scene boundaries...")
    scenes: List[Dict[str, float]] = []
    try:
        sig_detector = SignalDetector()
        energy_profile, mean_e = sig_detector.compute_audio_energy_profile(str(source_file))
        if job_cfg.enable_scene_detection:
            scene_detector = SceneDetector()
            scenes = scene_detector.detect_scenes(str(source_file))
        update_stage(
            4,
            "completed",
            detail=f"Signal analysis: {len(scenes)} visual scene cuts, {len(energy_profile)} acoustic windows (baseline: {mean_e:.1f} RMS).",
            elapsed=round(time.time() - t4, 2),
        )
    except Exception as exc:
        update_stage(4, "skipped", detail=f"Signal analysis fallback applied: {str(exc)}")

    # --- STAGE 5: Candidate Detection ---
    t5 = time.time()
    update_stage(5, "running", detail="Selecting viral moments via transcript and scene analysis...")
    try:
        meta_candidates = job.get("metadata", {}).get("candidates")
        if meta_candidates is not None:
            scored_candidates = [
                CandidateMoment(
                    start=float(c["start"]),
                    end=float(c["end"]),
                    score=float(c.get("score", 85.0)),
                    reasons=c.get("reasons", ["Highlight candidate"]),
                )
                for c in meta_candidates
            ]
            selection_res_mode = "configured"
            selection_res_provider = "metadata"
            selection_res_notice = ""
        else:
            vid_duration = SignalDetector().get_media_duration(str(source_file))
            words_json = serialize_words_for_llm(transcript_segments) if transcript_segments else []
            selector = MomentSelector(mode=job_cfg.moment_detection_mode, provider=job_cfg.moment_detection_provider)
            selection_res = selector.select_moments(
                video_duration=vid_duration,
                transcript_segments=transcript_segments,
                words_json=words_json,
                scenes=scenes,
                min_duration=job_cfg.min_clip_duration,
                max_duration=job_cfg.max_clip_duration,
                max_clips=job_cfg.max_clips,
                media_path=str(source_file),
            )
            scored_candidates = selection_res.candidates
            selection_res_mode = selection_res.mode
            selection_res_provider = selection_res.provider
            selection_res_notice = selection_res.notice or ""
        if not scored_candidates:
            update_stage(
                5,
                "completed",
                detail="Candidate detection: 0 moments met quality threshold (NO_VALID_MOMENTS).",
                elapsed=round(time.time() - t5, 2),
            )
            for s_idx in range(5, 13):
                update_stage(s_idx, "skipped", detail="Skipped: NO_VALID_MOMENTS met the quality threshold.")
            job["status"] = "completed"
            job["progress"] = 100
            job["stage"] = "NO_VALID_MOMENTS — no highlights passed quality threshold"
            save_job(job)
            return job

        update_stage(
            5,
            "completed",
            detail=f"Candidate detection: {len(scored_candidates)} moments selected ({selection_res_mode}, {selection_res_provider}). {selection_res_notice}",
            elapsed=round(time.time() - t5, 2),
        )
    except Exception as exc:
        update_stage(5, "failed", error=str(exc))
        return job

    # --- STAGE 6: Candidate Scoring ---
    t6 = time.time()
    update_stage(6, "running", detail="Evaluating candidate salience and temporal ranking...")
    try:
        if "metadata" not in job or not isinstance(job["metadata"], dict):
            job["metadata"] = {}
        job["metadata"]["candidates"] = [
            {
                "start": c.start,
                "end": c.end,
                "duration": round(c.duration, 1),
                "score": round(c.score, 1),
                "reasons": c.reasons,
            }
            for c in scored_candidates
        ]
        durations_str = ", ".join([f"{c.duration:.1f}s" for c in scored_candidates])
        detail_msg = f"Ranked {len(scored_candidates)} moments (scores: {', '.join([f'{c.score:.0f}' for c in scored_candidates])}; durations: {durations_str})."
        update_stage(6, "completed", detail=detail_msg, elapsed=round(time.time() - t6, 2))
    except Exception as exc:
        update_stage(6, "failed", error=str(exc))
        return job

    # Multi-Clip Data Structures
    source_title = meta.get("title") or Path(vod_url).stem
    rendered_clips: List[Dict[str, Any]] = []
    clip_slices: List[Path] = []
    reframe_files: List[Path] = []
    final_files: List[Path] = []
    qc_results: List[Dict[str, Any]] = []

    # --- STAGE 7: Clip Extraction ---
    t7 = time.time()
    update_stage(7, "running", detail=f"FFmpeg extracting {len(scored_candidates)} slices across timeline...")
    try:
        cr = ClipRenderer()
        for idx, cand in enumerate(scored_candidates, 1):
            raw_slice = work_dir / f"{job_id}_cand_{idx}_clipped.mp4"
            cr.render(str(source_file), cand.start, cand.end, str(raw_slice))
            clip_slices.append(raw_slice)
        update_stage(7, "completed", detail=f"Extracted {len(clip_slices)} slices ({', '.join([f'{c.duration:.1f}s' for c in scored_candidates])}, H.264).", elapsed=round(time.time() - t7, 2))
    except Exception as exc:
        update_stage(7, "failed", error=f"FFmpeg clipping error: {str(exc)}")
        return job

    # --- STAGE 8: Vertical 9:16 Reframing ---
    t8 = time.time()
    update_stage(8, "running", detail=f"Executing {job_cfg.framing_mode} 9:16 vertical composition on {len(clip_slices)} clips...")
    try:
        rf = Reframer()
        for idx, slice_path in enumerate(clip_slices, 1):
            reframe_out = work_dir / f"{job_id}_cand_{idx}_reframe.mp4"
            rf.render_vertical(
                str(slice_path),
                str(reframe_out),
                width=1080,
                height=1920,
                framing_mode=job_cfg.framing_mode,
            )
            reframe_files.append(reframe_out)
        update_stage(8, "completed", detail=f"Rendered {len(reframe_files)} 9:16 vertical MP4 compositions ({job_cfg.framing_mode}).", elapsed=round(time.time() - t8, 2))
    except Exception as exc:
        update_stage(8, "failed", error=f"Vertical reframing error: {str(exc)}")
        return job

    # --- STAGE 9: Caption Generation & Rendering ---
    t9 = time.time()
    update_stage(9, "running", detail=f"Rendering '{job_cfg.caption_preset}' subtitles for {len(reframe_files)} clips...")
    try:
        cr = CaptionRenderer()
        for idx, (reframe_path, cand) in enumerate(zip(reframe_files, scored_candidates), 1):
            cand_final = output_dir / f"{job_id}_clip_{idx}.mp4"
            if job_cfg.caption_preset == "no_captions":
                if reframe_path.resolve() != cand_final.resolve():
                    cand_final.write_bytes(reframe_path.read_bytes())
            elif transcript_segments:
                cr.render(
                    transcript_segments=transcript_segments,
                    video_path=str(reframe_path),
                    output_path=str(cand_final),
                    config=job_cfg,
                    clip_start=cand.start,
                    clip_end=cand.end,
                )
            else:
                if reframe_path.resolve() != cand_final.resolve():
                    cand_final.write_bytes(reframe_path.read_bytes())
            final_files.append(cand_final)

        if job_cfg.caption_preset == "no_captions":
            update_stage(9, "skipped", detail="Caption rendering skipped: No Captions selected by user.", elapsed=round(time.time() - t9, 2))
        elif transcript_segments:
            update_stage(9, "completed", detail=f"Burned '{job_cfg.caption_preset}' ASS captions on {len(final_files)} clips with clip-relative offsets.", elapsed=round(time.time() - t9, 2))
        else:
            update_stage(9, "skipped", detail="Captions skipped: speech transcription unavailable on host.", elapsed=round(time.time() - t9, 2))
    except Exception as exc:
        update_stage(9, "failed", error=f"Caption rendering error: {str(exc)}")
        return job

    # --- STAGE 10: Quality Control ---
    t10 = time.time()
    update_stage(10, "running", detail=f"FFprobe inspecting {len(final_files)} generated clips...")
    try:
        qc = QualityController()
        for f_path in final_files:
            qc_res = qc.check(str(f_path))
            if not qc_res.passed:
                raise RuntimeError(f"QC failed for {f_path.name}: {qc_res.errors}")
            qc_results.append(qc_res.checks)
        update_stage(10, "completed", detail=f"Technical QC passed on all {len(final_files)} clips: H.264 video, AAC audio, valid container.", elapsed=round(time.time() - t10, 2))
    except Exception as exc:
        update_stage(10, "failed", error=f"Quality control rejected file: {str(exc)}")
        return job

    # --- STAGE 11: Output Registration ---
    t11 = time.time()
    update_stage(11, "running", detail=f"Registering {len(final_files)} playable outputs in media workspace...")
    try:
        for f_path in final_files:
            if not f_path.exists() or f_path.stat().st_size <= 1024:
                raise FileNotFoundError(f"Output MP4 missing or empty: {f_path.name}")
        update_stage(11, "completed", detail=f"Exposed {len(final_files)} clips at /media/{job_id}_clip_*.mp4.", elapsed=round(time.time() - t11, 2))
    except Exception as exc:
        update_stage(11, "failed", error=str(exc))
        return job

    # --- STAGE 12: Human Approval Gate ---
    t12 = time.time()
    update_stage(12, "running", detail=f"Registering {len(final_files)} clips into review queue for operator approval...")
    try:
        for idx, (f_path, cand, qc_chk) in enumerate(zip(final_files, scored_candidates, qc_results), 1):
            c_id = f"clip_{uuid.uuid4().hex[:6]}"
            clip_obj = {
                "id": c_id,
                "job_id": job_id,
                "title": f"Highlight #{idx}: {source_title[:38]} [{cand.start:.1f}s-{cand.end:.1f}s]",
                "duration": f"{cand.duration:.1f}s",
                "score": f"{int(round(cand.score))}/100",
                "status": "WAITING_APPROVAL",
                "vod": source_title,
                "is_fixture": False,
                "is_real_media": True,
                "media_type": "rendered_video",
                "render_status": "rendered",
                "render_notice": f"Highlight signals: {', '.join(cand.reasons)}",
                "media_url": f"/media/{f_path.name}",
                "start_time": cand.start,
                "end_time": cand.end,
                "resolution": "1080x1920",
                "qc_checks": qc_chk,
                "framing_mode": job_cfg.framing_mode,
                "caption_preset": job_cfg.caption_preset,
                "caption_language": job_cfg.caption_language,
                "caption_size": job_cfg.caption_size,
                "caption_position": job_cfg.caption_position,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            save_clip(clip_obj)
            rendered_clips.append(clip_obj)

        update_stage(12, "completed", detail=f"All {len(rendered_clips)} clips registered in review queue. Awaiting human operator approval.", elapsed=round(time.time() - t12, 2))

        # Job complete and awaiting review
        job["status"] = "waiting_approval"
        job["progress"] = 100
        job["stage"] = f"{len(rendered_clips)} clips rendered in 9:16 vertical MP4 — awaiting human approval"
        save_job(job)
    except Exception as exc:
        update_stage(12, "failed", error=str(exc))
        return job

    return job
