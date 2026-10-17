import asyncio
import copy
import datetime
import logging

logger = logging.getLogger("clipforge.runner")
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
    fetch_youtube_transcript,
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
        framing_mode=raw_cfg.get("framing_mode", "auto_follow_speaker"),
        caption_preset=raw_cfg.get("caption_preset", "clean"),
        caption_language=raw_cfg.get("caption_language", "auto"),
        caption_size=raw_cfg.get("caption_size", "large"),
        caption_position=raw_cfg.get("caption_position", "bottom_safe"),
        caption_text_color=raw_cfg.get("caption_text_color", "#FFFFFF"),
        caption_highlight_color=raw_cfg.get("caption_highlight_color", "#FFFF00"),
        caption_word_highlight=bool(raw_cfg.get("caption_word_highlight", False)),
        moment_detection_mode=raw_cfg.get("moment_detection_mode", "heuristic"),
        moment_detection_provider=raw_cfg.get("moment_detection_provider", "heuristic"),
        max_clips=int(raw_cfg.get("max_clips", 5)),
        min_clip_duration=float(raw_cfg.get("min_clip_duration", 45.0)),
        max_clip_duration=float(raw_cfg.get("max_clip_duration", 120.0)),
        enable_scene_detection=bool(raw_cfg.get("enable_scene_detection", True)),
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
    reframe_analyses: List[Any] = []
    detected_reactions: List[Any] = []
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
    update_stage(2, "running", detail="Ingesting media or fetching full transcript...")
    yt_full_transcript = []
    try:
        if kind == "youtube":
            yt_full_transcript = fetch_youtube_transcript(vod_url, cache_dir=work_dir)
            if yt_full_transcript:
                update_stage(2, "completed", detail=f"Fetched full YouTube transcript ({len(yt_full_transcript)} segments across {dur}s).", elapsed=round(time.time() - t2, 2))
            else:
                raw_dl = work_dir / f"{job_id}_raw.mp4"
                source_file = download_youtube_segment(
                    url=vod_url,
                    output_path=str(raw_dl),
                    start_sec=0.0,
                    duration_sec=min(float(dur or 300), 120.0),
                    max_filesize_mb=200,
                )
                update_stage(2, "completed", detail=f"Fallback video segment downloaded ({source_file.stat().st_size} bytes).", elapsed=round(time.time() - t2, 2))
        else:
            update_stage(2, "completed", detail=f"Local media loaded: {source_file.name}", elapsed=round(time.time() - t2, 2))
    except Exception as exc:
        update_stage(2, "failed", error=f"Media ingestion failed: {str(exc)}")
        return job

    # --- STAGE 3: Audio Transcription ---
    t3 = time.time()
    update_stage(3, "running", detail="Resolving speech transcription across video timeline...")
    try:
        if yt_full_transcript:
            transcript_segments = yt_full_transcript
            update_stage(
                3,
                "completed",
                detail=f"Full transcript loaded from YouTube ({len(transcript_segments)} segments aligned).",
                elapsed=round(time.time() - t3, 2),
            )
        else:
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
            elif is_whisper_available() and source_file:
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
        if source_file and Path(source_file).exists():
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
        else:
            update_stage(4, "skipped", detail="Direct YouTube stream: scene detection deferred to candidate slices.", elapsed=round(time.time() - t4, 2))
    except Exception as exc:
        update_stage(4, "skipped", detail=f"Signal analysis fallback applied: {str(exc)}")

    # --- STAGE 5: Candidate Detection ---
    t5 = time.time()
    update_stage(5, "running", detail="Selecting viral moments via transcript and scene analysis...")
    selection_res_mode = "heuristic"
    selection_res_provider = "heuristic"
    selection_res_notice = ""
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
            scored_candidates.sort(key=lambda c: getattr(c, "score", 0.0), reverse=True)
            selection_res_mode = "configured"
            selection_res_provider = "metadata"
            selection_res_notice = ""
        else:
            vid_duration = float(meta.get("duration") or (SignalDetector().get_media_duration(str(source_file)) if (source_file and Path(source_file).exists()) else 300.0))
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
                media_path=str(source_file) if source_file else None,
                youtube_heatmap=meta.get("heatmap") if meta else None,
            )
            scored_candidates = sorted(selection_res.candidates, key=lambda c: getattr(c, "score", 0.0), reverse=True)[:job_cfg.max_clips]
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
            c.to_dict() if hasattr(c, "to_dict") else {
                "moment_id": f"mom_{idx:03d}",
                "rank": idx,
                "source_start": round(c.start, 2),
                "source_end": round(c.end, 2),
                "start": round(c.start, 2),
                "end": round(c.end, 2),
                "duration": round(c.duration, 1),
                "score": round(c.score, 1),
                "reasons": c.reasons,
            }
            for idx, c in enumerate(scored_candidates, 1)
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
    candidates_to_render = sorted(scored_candidates, key=lambda c: getattr(c, "score", 0.0), reverse=True)[:job_cfg.max_clips]
    update_stage(7, "running", detail=f"FFmpeg extracting {len(candidates_to_render)} slices across timeline...")
    try:
        from services.boundary_refinement import SmartBoundaryRefiner
        refiner = SmartBoundaryRefiner(max_start_expansion=2.0, max_end_expansion=3.0)
        all_words = []
        for seg in transcript_segments:
            if seg.words:
                all_words.extend(seg.words)

        cr = ClipRenderer()
        successful_candidates = []
        for idx, cand in enumerate(candidates_to_render, 1):
            raw_slice = work_dir / f"{job_id}_cand_{idx}_clipped.mp4"
            b_res = refiner.refine(
                candidate_start=cand.start,
                candidate_end=cand.end,
                words=all_words,
                min_duration=job_cfg.min_clip_duration,
                max_duration=job_cfg.max_clip_duration,
            )
            cand.start = b_res.refined_start
            cand.end = b_res.refined_end
            setattr(cand, "boundary_adjustment", b_res.to_dict())
            try:
                if kind == "youtube":
                    actual_slice = download_youtube_segment(
                        url=vod_url,
                        output_path=str(raw_slice),
                        start_sec=cand.start,
                        duration_sec=cand.duration,
                        max_filesize_mb=200,
                    )
                else:
                    actual_slice = Path(cr.render(str(source_file), cand.start, cand.end, str(raw_slice)))
                clip_slices.append(actual_slice)
                successful_candidates.append(cand)
            except Exception as slice_err:
                logger.warning(f"Slice extraction error for candidate {idx}: {slice_err}")
                print(f"[Ingest] Slice error for candidate {idx} [{cand.start:.1f}s - {cand.end:.1f}s]: {slice_err}")

        if not clip_slices:
            raise RuntimeError("Zero candidate slices could be extracted.")

        scored_candidates = successful_candidates
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
            cand = scored_candidates[idx - 1]
            clip_scenes = [
                {"start": max(0.0, s.get("start", 0) - cand.start), "end": max(0.0, s.get("end", 0) - cand.start)}
                for s in scenes
                if s.get("end", 0) > cand.start and s.get("start", 0) < cand.end
            ]
            if not clip_scenes and job_cfg.enable_scene_detection:
                try:
                    from services.detection.scene import SceneDetector
                    clip_scenes = SceneDetector().detect_scenes(str(slice_path))
                except Exception:
                    clip_scenes = []
            reframe_out = work_dir / f"{job_id}_cand_{idx}_reframe.mp4"
            rf_res = rf.render_vertical(
                str(slice_path),
                str(reframe_out),
                width=1080,
                height=1920,
                framing_mode=job_cfg.framing_mode,
                scenes=clip_scenes,
            )
            reframe_files.append(reframe_out)
            reframe_analyses.append(getattr(rf_res, "analysis", None))
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
                hf_rendered = False
                try:
                    from services.render.hyperframes_templates import generate_initial_composition
                    from services.render.hyperframes_composition import HyperframesCompositionBuilder
                    from services.render.hyperframes_runner import HyperframesRunner

                    c_dict = {
                        "id": f"{job_id}_clip_{idx}",
                        "title": cand.reasons[0] if (hasattr(cand, "reasons") and cand.reasons) else "HIGHLIGHT MOMENT",
                        "duration": f"{cand.duration:.1f}s",
                        "start_time": cand.start,
                        "end_time": cand.end,
                        "layout_mode": getattr(cand, "layout_mode", "TRACK") or "TRACK",
                        "caption_preset": job_cfg.caption_preset,
                    }
                    c_segs = [s for s in transcript_segments if s.end > cand.start and s.start < cand.end]
                    hf_comp = generate_initial_composition(c_dict, transcript_segments=c_segs)
                    hf_comp.duration = cand.duration

                    hf_proj = work_dir / f"hf_{job_id}_{idx}"
                    builder = HyperframesCompositionBuilder()
                    builder.build_from_composition(hf_proj, reframe_path, hf_comp)
                    runner = HyperframesRunner(quality="draft", fps=30)
                    h_res = runner.render(hf_proj, cand_final, quality="draft")
                    if h_res.success and cand_final.exists() and cand_final.stat().st_size > 0:
                        hf_rendered = True
                except Exception as hf_err:
                    logger.warning(f"HyperFrames direct render failed for clip {idx}: {hf_err}")

                if not hf_rendered:
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
        from services.clip_quality import ClipQualityAnalyzer, HookPayoffClassifier
        from services.clustering import TopicClusterer
        from services.context import ContextCompletenessAnalyzer
        from services.recommendation import RecommendationEngine
        from services.visual_quality import VisualCompositionAnalyzer

        analyzer = ClipQualityAnalyzer()
        rec_engine = RecommendationEngine(default_top_k=job_cfg.max_clips or 5)
        hook_classifier = HookPayoffClassifier()
        context_analyzer = ContextCompletenessAnalyzer()
        visual_analyzer = VisualCompositionAnalyzer()
        topic_clusterer = TopicClusterer()
        raw_clip_objs = []
        quality_map = {}
        for idx, (f_path, cand, qc_chk) in enumerate(zip(final_files, scored_candidates, qc_results), 1):
            rf_analysis = reframe_analyses[idx - 1] if idx <= len(reframe_analyses) else None
            c_id = f"clip_{uuid.uuid4().hex[:6]}"
            clip_segs = [s for s in transcript_segments if s.end > cand.start and s.start < cand.end]
            clip_text = " ".join([s.text for s in clip_segs]) or "Conversational highlight moment"
            clip_sents = [s.text for s in clip_segs]

            q_feat = analyzer.analyze_clip(
                clip_id=c_id,
                text=clip_text,
                duration=cand.duration,
                sentences=clip_sents,
                audio_reactions=detected_reactions,
                clip_start=cand.start,
                clip_end=cand.end,
                active_speaker_confidence=0.88 if (rf_analysis and getattr(rf_analysis, "active_speaker_available", False)) else 0.5,
                face_detected=bool(rf_analysis and getattr(rf_analysis, "face_detection_available", True)),
                layout_mode=getattr(rf_analysis, "layout_mode", "TRACK") if rf_analysis else "TRACK",
            )
            quality_map[c_id] = q_feat

            clip_obj = {
                "id": c_id,
                "job_id": job_id,
                "title": f"Highlight #{idx}: {source_title[:38]} [{cand.start:.1f}s-{cand.end:.1f}s]",
                "duration": f"{cand.duration:.1f}s",
                "score": f"{int(round(q_feat.breakdown.total))}/100",
                "score_raw": q_feat.breakdown.total,
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
                "speaker_track_id": f"face_{rf_analysis.primary_track_id:02d}" if (rf_analysis and hasattr(rf_analysis, "primary_track_id") and rf_analysis.primary_track_id) else "face_01",
                "speaker_confidence": 0.88 if (rf_analysis and getattr(rf_analysis, "active_speaker_available", False)) else 0.5,
                "layout_mode": getattr(rf_analysis, "layout_mode", "TRACK") if rf_analysis else "TRACK",
                "audio_reaction": getattr(cand, "audio_reaction", None) or ("High Energy" if any("reaction" in r.lower() for r in cand.reasons) else "Speech"),
                "audio_reaction_confidence": 0.85 if any("reaction" in r.lower() for r in cand.reasons) else 0.0,
                "variant": getattr(cand, "variant", "normal"),
                "parent_moment_id": getattr(cand, "parent_moment_id", None),
                "text": clip_text,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

            # P3 Intelligence Analyses
            h_info = hook_classifier.classify_hook(clip_text)
            p_info = hook_classifier.classify_payoff(clip_text)
            ctx_info = context_analyzer.evaluate(clip_sents, full_text=clip_text)
            vis_faces = [(d.center_x, d.center_y, d.width, d.height) for d in rf_analysis.detections] if (rf_analysis and hasattr(rf_analysis, "detections") and rf_analysis.detections) else None
            vis_info = visual_analyzer.evaluate(faces=vis_faces, layout_mode=clip_obj["layout_mode"])

            clip_obj["hook_type"] = h_info.category.value
            clip_obj["payoff_type"] = p_info.category.value
            clip_obj["context_score"] = ctx_info.context_score
            clip_obj["bridge_score"] = round(ctx_info.bridge_count * 10.0, 1)
            clip_obj["context_completeness"] = ctx_info.context_completeness
            clip_obj["visual_quality_score"] = vis_info.visual_quality_score
            clip_obj["headroom_score"] = vis_info.headroom_score
            clip_obj["face_size_score"] = vis_info.face_size_score
            clip_obj["boundary_adjustment"] = getattr(cand, "boundary_adjustment", {})

            # P3 Quality Flags
            flags = []
            if q_feat.breakdown.hook >= 10.0 or h_info.category.value in {"QUESTION", "CURIOSITY_GAP", "NUMBER"}:
                flags.append("STRONG HOOK")
            if ctx_info.context_completeness >= 0.70:
                flags.append("COMPLETE THOUGHT")
            if q_feat.breakdown.information >= 6.5:
                flags.append("HIGH INFORMATION")
            if p_info.category.value in {"LESSON", "CONCLUSION", "RECOMMENDATION", "RESULT"}:
                flags.append("STRONG PAYOFF")
            if vis_info.visual_quality_score >= 80.0:
                flags.append("GREAT FRAMING")
            if not vis_info.caption_collision:
                flags.append("CAPTION SAFE")
            clip_obj["quality_flags"] = flags

            raw_clip_objs.append(clip_obj)

        # Topic family clustering & diversity
        topic_clusterer.cluster_clips(raw_clip_objs)
        recommended_clips = rec_engine.recommend_clips(raw_clip_objs, quality_map=quality_map)
        diversified_clips = topic_clusterer.enforce_family_diversity(recommended_clips)

        from services.render.hyperframes_templates import generate_initial_composition
        from services.editor.editor_state import EditorStateManager
        from core.storage import save_editor_state

        for clip_obj in diversified_clips:
            c_segs = [s for s in transcript_segments if s.end > clip_obj["start_time"] and s.start < clip_obj["end_time"]]
            hf_comp = generate_initial_composition(clip_obj, transcript_segments=c_segs)
            clip_obj["composition"] = hf_comp.to_dict()
            save_clip(clip_obj)

            # Persist in EditorState for Studio Editor
            ed_mgr = EditorStateManager()
            state = ed_mgr.load_or_initialize(clip_obj, transcript_segments=c_segs)
            state.user_overrides["composition"] = hf_comp.to_dict()
            ed_mgr.save(state)

            rendered_clips.append(clip_obj)
        update_stage(12, "completed", detail=f"All {len(rendered_clips)} clips registered in review queue. Awaiting human operator approval.", elapsed=round(time.time() - t12, 2))
        job["status"] = "waiting_approval"
        job["progress"] = 100
        job["stage"] = f"{len(rendered_clips)} clips rendered in 9:16 vertical MP4 — awaiting human approval"
        save_job(job)
    except Exception as exc:
        update_stage(12, "failed", error=str(exc))
        return job

    return job
