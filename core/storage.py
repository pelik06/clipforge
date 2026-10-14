import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
import datetime

import os

def get_default_db_path() -> Path:
    data_dir = os.getenv("CLIPFORGE_DATA_DIR", "./data")
    return Path(data_dir) / "clipforge.db"

DEFAULT_DB_PATH = Path("data/clipforge.db")


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target = db_path or get_default_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                vod_url TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                current_stage TEXT,
                progress INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error TEXT,
                metadata_json TEXT,
                stages_json TEXT
            );

            CREATE TABLE IF NOT EXISTS clips (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                title TEXT NOT NULL,
                duration TEXT NOT NULL,
                score TEXT NOT NULL,
                status TEXT NOT NULL,
                vod TEXT NOT NULL,
                is_fixture INTEGER DEFAULT 0,
                is_real_media INTEGER DEFAULT 0,
                media_type TEXT NOT NULL,
                render_status TEXT,
                render_notice TEXT,
                media_url TEXT,
                start_time REAL,
                end_time REAL,
                resolution TEXT,
                qc_json TEXT,
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_clips_created ON clips(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_clips_job ON clips(job_id);

            CREATE TABLE IF NOT EXISTS render_jobs (
                id TEXT PRIMARY KEY,
                clip_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                progress REAL NOT NULL DEFAULT 0.0,
                preset TEXT NOT NULL DEFAULT 'tiktok',
                render_type TEXT NOT NULL DEFAULT 'final',
                output_path TEXT,
                output_sha256 TEXT,
                error_message TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                priority INTEGER NOT NULL DEFAULT 10,
                config_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_render_jobs_status ON render_jobs(status);
            CREATE INDEX IF NOT EXISTS idx_render_jobs_created ON render_jobs(created_at DESC);
            """
        )
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        existing_cols = {r["name"] for r in cursor.fetchall()}
        column_defs = {
            "framing_mode": "TEXT DEFAULT 'center_crop'",
            "caption_preset": "TEXT DEFAULT 'clean'",
            "caption_language": "TEXT DEFAULT 'auto'",
            "caption_size": "TEXT DEFAULT 'medium'",
            "caption_position": "TEXT DEFAULT 'bottom_safe'",
            "caption_text_color": "TEXT DEFAULT '#FFFFFF'",
            "caption_highlight_color": "TEXT DEFAULT '#FFFF00'",
            "caption_word_highlight": "INTEGER DEFAULT 0",
            "moment_detection_mode": "TEXT DEFAULT 'heuristic'",
            "moment_detection_provider": "TEXT DEFAULT 'gemini'",
            "max_clips": "INTEGER DEFAULT 5",
            "min_clip_duration": "REAL DEFAULT 12.0",
            "max_clip_duration": "REAL DEFAULT 60.0",
            "enable_scene_detection": "INTEGER DEFAULT 1",
        }
        for col_name, col_def in column_defs.items():
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_def}")

        cursor.execute("PRAGMA table_info(clips)")
        existing_clip_cols = {r["name"] for r in cursor.fetchall()}
        clip_column_defs = {
            "speaker_track_id": "TEXT DEFAULT NULL",
            "speaker_confidence": "REAL DEFAULT 0.0",
            "layout_mode": "TEXT DEFAULT 'TRACK'",
            "audio_reaction": "TEXT DEFAULT NULL",
            "audio_reaction_confidence": "REAL DEFAULT 0.0",
            "variant": "TEXT DEFAULT 'normal'",
            "parent_moment_id": "TEXT DEFAULT NULL",
            "ranking": "INTEGER DEFAULT NULL",
            "is_recommended": "INTEGER DEFAULT 0",
            "quality_breakdown": "TEXT DEFAULT '{}'",
            "why_this_clip": "TEXT DEFAULT '[]'",
            "recommendation_reasons": "TEXT DEFAULT '[]'",
            "context_score": "REAL DEFAULT NULL",
            "bridge_score": "REAL DEFAULT NULL",
            "hook_type": "TEXT DEFAULT NULL",
            "payoff_type": "TEXT DEFAULT NULL",
            "context_completeness": "REAL DEFAULT NULL",
            "topic_family": "TEXT DEFAULT NULL",
            "topic_label": "TEXT DEFAULT NULL",
            "visual_quality_score": "REAL DEFAULT NULL",
            "headroom_score": "REAL DEFAULT NULL",
            "face_size_score": "REAL DEFAULT NULL",
            "boundary_adjustment": "TEXT DEFAULT '{}'",
            "quality_flags": "TEXT DEFAULT '[]'",
        }
        for col_name, col_def in clip_column_defs.items():
            if col_name not in existing_clip_cols:
                conn.execute(f"ALTER TABLE clips ADD COLUMN {col_name} {col_def}")
        conn.commit()


def save_job(job: Dict[str, Any], db_path: Optional[Path] = None) -> Dict[str, Any]:
    init_db(db_path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    meta_str = json.dumps(job.get("metadata", {}))
    stages_str = json.dumps(job.get("stages", []))

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, vod_url, kind, status, current_stage, progress, created_at, updated_at, error,
                metadata_json, stages_json, framing_mode, caption_preset, caption_language,
                caption_size, caption_position, caption_text_color, caption_highlight_color,
                caption_word_highlight,
                moment_detection_mode, moment_detection_provider, max_clips,
                min_clip_duration, max_clip_duration, enable_scene_detection
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                current_stage = excluded.current_stage,
                progress = excluded.progress,
                updated_at = excluded.updated_at,
                error = excluded.error,
                metadata_json = excluded.metadata_json,
                stages_json = excluded.stages_json,
                framing_mode = COALESCE(excluded.framing_mode, jobs.framing_mode),
                caption_preset = COALESCE(excluded.caption_preset, jobs.caption_preset),
                caption_language = COALESCE(excluded.caption_language, jobs.caption_language),
                caption_size = COALESCE(excluded.caption_size, jobs.caption_size),
                caption_position = COALESCE(excluded.caption_position, jobs.caption_position),
                caption_text_color = COALESCE(excluded.caption_text_color, jobs.caption_text_color),
                caption_highlight_color = COALESCE(excluded.caption_highlight_color, jobs.caption_highlight_color),
                caption_word_highlight = COALESCE(excluded.caption_word_highlight, jobs.caption_word_highlight),
                moment_detection_mode = COALESCE(excluded.moment_detection_mode, jobs.moment_detection_mode),
                moment_detection_provider = COALESCE(excluded.moment_detection_provider, jobs.moment_detection_provider),
                max_clips = COALESCE(excluded.max_clips, jobs.max_clips),
                min_clip_duration = COALESCE(excluded.min_clip_duration, jobs.min_clip_duration),
                max_clip_duration = COALESCE(excluded.max_clip_duration, jobs.max_clip_duration),
                enable_scene_detection = COALESCE(excluded.enable_scene_detection, jobs.enable_scene_detection);
            """,
            (
                job["id"],
                job["vod_url"],
                job.get("kind", "youtube"),
                job.get("status", "created"),
                job.get("stage") or job.get("current_stage"),
                job.get("progress", 0),
                job.get("created_at", now),
                now,
                job.get("error"),
                meta_str,
                stages_str,
                job.get("framing_mode", "center_crop"),
                job.get("caption_preset", "clean"),
                job.get("caption_language", "auto"),
                job.get("caption_size", "medium"),
                job.get("caption_position", "bottom_safe"),
                job.get("caption_text_color", "#FFFFFF"),
                job.get("caption_highlight_color", "#FFFF00"),
                1 if job.get("caption_word_highlight") else 0,
                job.get("moment_detection_mode", "heuristic"),
                job.get("moment_detection_provider", "gemini"),
                int(job.get("max_clips", 5)),
                float(job.get("min_clip_duration", 12.0)),
                float(job.get("max_clip_duration", 60.0)),
                1 if job.get("enable_scene_detection", True) else 0,
            ),
        )
        conn.commit()
    return job


def get_job(job_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return _format_job_row(row)


def list_jobs(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [_format_job_row(r) for r in rows]


def save_clip(clip: Dict[str, Any], db_path: Optional[Path] = None) -> Dict[str, Any]:
    init_db(db_path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    qc_str = json.dumps(clip.get("qc_checks", {}))

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO clips (
                id, job_id, title, duration, score, status, vod,
                is_fixture, is_real_media, media_type, render_status, render_notice,
                media_url, start_time, end_time, resolution, qc_json, created_at, reviewed_at,
                speaker_track_id, speaker_confidence, layout_mode, audio_reaction, audio_reaction_confidence,
                variant, parent_moment_id, ranking, is_recommended, quality_breakdown, why_this_clip, recommendation_reasons,
                context_score, bridge_score, hook_type, payoff_type, context_completeness, topic_family, topic_label,
                visual_quality_score, headroom_score, face_size_score, boundary_adjustment, quality_flags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                reviewed_at = excluded.reviewed_at,
                render_status = excluded.render_status,
                render_notice = excluded.render_notice,
                media_url = excluded.media_url,
                qc_json = excluded.qc_json,
                speaker_track_id = COALESCE(excluded.speaker_track_id, clips.speaker_track_id),
                speaker_confidence = COALESCE(excluded.speaker_confidence, clips.speaker_confidence),
                layout_mode = COALESCE(excluded.layout_mode, clips.layout_mode),
                audio_reaction = COALESCE(excluded.audio_reaction, clips.audio_reaction),
                audio_reaction_confidence = COALESCE(excluded.audio_reaction_confidence, clips.audio_reaction_confidence),
                variant = COALESCE(excluded.variant, clips.variant),
                parent_moment_id = COALESCE(excluded.parent_moment_id, clips.parent_moment_id),
                ranking = COALESCE(excluded.ranking, clips.ranking),
                is_recommended = COALESCE(excluded.is_recommended, clips.is_recommended),
                quality_breakdown = COALESCE(excluded.quality_breakdown, clips.quality_breakdown),
                why_this_clip = COALESCE(excluded.why_this_clip, clips.why_this_clip),
                recommendation_reasons = COALESCE(excluded.recommendation_reasons, clips.recommendation_reasons),
                context_score = COALESCE(excluded.context_score, clips.context_score),
                bridge_score = COALESCE(excluded.bridge_score, clips.bridge_score),
                hook_type = COALESCE(excluded.hook_type, clips.hook_type),
                payoff_type = COALESCE(excluded.payoff_type, clips.payoff_type),
                context_completeness = COALESCE(excluded.context_completeness, clips.context_completeness),
                topic_family = COALESCE(excluded.topic_family, clips.topic_family),
                topic_label = COALESCE(excluded.topic_label, clips.topic_label),
                visual_quality_score = COALESCE(excluded.visual_quality_score, clips.visual_quality_score),
                headroom_score = COALESCE(excluded.headroom_score, clips.headroom_score),
                face_size_score = COALESCE(excluded.face_size_score, clips.face_size_score),
                boundary_adjustment = COALESCE(excluded.boundary_adjustment, clips.boundary_adjustment),
                quality_flags = COALESCE(excluded.quality_flags, clips.quality_flags);
            """,
            (
                clip["id"],
                clip["job_id"],
                clip["title"],
                clip["duration"],
                clip["score"],
                clip["status"],
                clip["vod"],
                1 if clip.get("is_fixture") else 0,
                1 if clip.get("is_real_media") else 0,
                clip.get("media_type", "candidate_metadata"),
                clip.get("render_status"),
                clip.get("render_notice"),
                clip.get("media_url"),
                clip.get("start_time"),
                clip.get("end_time"),
                clip.get("resolution", "1080x1920"),
                qc_str,
                clip.get("created_at", now),
                clip.get("reviewed_at"),
                clip.get("speaker_track_id"),
                float(clip.get("speaker_confidence") or 0.0),
                clip.get("layout_mode", "TRACK"),
                clip.get("audio_reaction"),
                float(clip.get("audio_reaction_confidence") or 0.0),
                clip.get("variant", "normal"),
                clip.get("parent_moment_id"),
                clip.get("ranking"),
                1 if clip.get("is_recommended") else 0,
                json.dumps(clip.get("quality_breakdown", {})),
                json.dumps(clip.get("why_this_clip", [])),
                json.dumps(clip.get("recommendation_reasons", [])),
                clip.get("context_score"),
                clip.get("bridge_score"),
                clip.get("hook_type"),
                clip.get("payoff_type"),
                clip.get("context_completeness"),
                clip.get("topic_family"),
                clip.get("topic_label"),
                clip.get("visual_quality_score"),
                clip.get("headroom_score"),
                clip.get("face_size_score"),
                json.dumps(clip.get("boundary_adjustment", {})),
                json.dumps(clip.get("quality_flags", [])),
            ),
        )
        conn.commit()
    return clip


def update_clip_decision(clip_id: str, decision_status: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE clips SET status = ?, reviewed_at = ? WHERE id = ?",
            (decision_status, now, clip_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM clips WHERE id = ?", (clip_id,)).fetchone()
        if not row:
            return None
        return _format_clip_row(row)


def list_clips(job_id: Optional[str] = None, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        if job_id:
            rows = conn.execute("SELECT * FROM clips WHERE job_id = ? ORDER BY created_at DESC", (job_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM clips ORDER BY created_at DESC").fetchall()
        return [_format_clip_row(r) for r in rows]

def save_render_job(job: Dict[str, Any], db_path: Optional[Path] = None) -> Dict[str, Any]:
    init_db(db_path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cfg_str = json.dumps(job.get("config", {}))

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO render_jobs (
                id, clip_id, source_id, status, stage, progress,
                preset, render_type, output_path, output_sha256, error_message,
                retry_count, priority, config_json, created_at, started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                stage = excluded.stage,
                progress = excluded.progress,
                output_path = excluded.output_path,
                output_sha256 = excluded.output_sha256,
                error_message = excluded.error_message,
                retry_count = excluded.retry_count,
                started_at = excluded.started_at,
                completed_at = excluded.completed_at;
            """,
            (
                job["id"],
                job["clip_id"],
                job.get("source_id", ""),
                job.get("status", "QUEUED"),
                job.get("stage", "Queued"),
                float(job.get("progress", 0.0)),
                job.get("preset", "tiktok"),
                job.get("render_type", "final"),
                job.get("output_path"),
                job.get("output_sha256"),
                job.get("error_message"),
                int(job.get("retry_count", 0)),
                int(job.get("priority", 10)),
                cfg_str,
                job.get("created_at", now),
                job.get("started_at"),
                job.get("completed_at"),
            ),
        )
        conn.commit()
    return job


def get_render_job(job_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM render_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return _format_render_job_row(row)


def list_render_jobs(status: Optional[str] = None, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        if status:
            rows = conn.execute("SELECT * FROM render_jobs WHERE status = ? ORDER BY priority DESC, created_at ASC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM render_jobs ORDER BY created_at DESC").fetchall()
        return [_format_render_job_row(r) for r in rows]


def delete_render_job(job_id: str, db_path: Optional[Path] = None) -> bool:
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM render_jobs WHERE id = ?", (job_id,))
        conn.commit()
    return True


def _format_render_job_row(row: sqlite3.Row) -> Dict[str, Any]:
    cfg = {}
    try:
        cfg = json.loads(row["config_json"]) if row["config_json"] else {}
    except Exception:
        pass
    return {
        "id": row["id"],
        "clip_id": row["clip_id"],
        "source_id": row["source_id"],
        "status": row["status"],
        "stage": row["stage"],
        "progress": float(row["progress"]),
        "preset": row["preset"],
        "render_type": row["render_type"],
        "output_path": row["output_path"],
        "output_sha256": row["output_sha256"],
        "error_message": row["error_message"],
        "retry_count": int(row["retry_count"]),
        "priority": int(row["priority"]),
        "config": cfg,
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
    }

def _format_job_row(row: sqlite3.Row) -> Dict[str, Any]:
    stages = []
    try:
        stages = json.loads(row["stages_json"]) if row["stages_json"] else []
    except Exception:
        pass

    meta = {}
    try:
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
    except Exception:
        pass

    keys = set(row.keys()) if hasattr(row, "keys") else set()
    return {
        "id": row["id"],
        "vod_url": row["vod_url"],
        "kind": row["kind"],
        "status": row["status"],
        "stage": row["current_stage"],
        "current_stage": row["current_stage"],
        "progress": row["progress"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "error": row["error"],
        "metadata": meta,
        "stages": stages,
        "framing_mode": row["framing_mode"] if "framing_mode" in keys and row["framing_mode"] else "center_crop",
        "caption_preset": row["caption_preset"] if "caption_preset" in keys and row["caption_preset"] else "clean",
        "caption_language": row["caption_language"] if "caption_language" in keys and row["caption_language"] else "auto",
        "caption_size": row["caption_size"] if "caption_size" in keys and row["caption_size"] else "medium",
        "caption_position": row["caption_position"] if "caption_position" in keys and row["caption_position"] else "bottom_safe",
        "caption_text_color": row["caption_text_color"] if "caption_text_color" in keys and row["caption_text_color"] else "#FFFFFF",
        "caption_highlight_color": row["caption_highlight_color"] if "caption_highlight_color" in keys and row["caption_highlight_color"] else "#FFFF00",
        "caption_word_highlight": bool(row["caption_word_highlight"]) if "caption_word_highlight" in keys and row["caption_word_highlight"] is not None else False,
        "moment_detection_mode": row["moment_detection_mode"] if "moment_detection_mode" in keys and row["moment_detection_mode"] else "heuristic",
        "moment_detection_provider": row["moment_detection_provider"] if "moment_detection_provider" in keys and row["moment_detection_provider"] else "gemini",
        "max_clips": int(row["max_clips"]) if "max_clips" in keys and row["max_clips"] is not None else 5,
        "min_clip_duration": float(row["min_clip_duration"]) if "min_clip_duration" in keys and row["min_clip_duration"] is not None else 12.0,
        "max_clip_duration": float(row["max_clip_duration"]) if "max_clip_duration" in keys and row["max_clip_duration"] is not None else 60.0,
        "enable_scene_detection": bool(row["enable_scene_detection"]) if "enable_scene_detection" in keys and row["enable_scene_detection"] is not None else True,
    }


def _format_clip_row(row: sqlite3.Row) -> Dict[str, Any]:
    qc_checks = {}
    try:
        qc_checks = json.loads(row["qc_json"]) if row["qc_json"] else {}
    except Exception:
        pass

    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "title": row["title"],
        "duration": row["duration"],
        "score": row["score"],
        "status": row["status"],
        "vod": row["vod"],
        "is_fixture": bool(row["is_fixture"]),
        "is_real_media": bool(row["is_real_media"]),
        "media_type": row["media_type"],
        "render_status": row["render_status"],
        "render_notice": row["render_notice"],
        "media_url": row["media_url"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "resolution": row["resolution"],
        "qc_checks": qc_checks,
        "created_at": row["created_at"],
        "reviewed_at": row["reviewed_at"],
        "speaker_track_id": row["speaker_track_id"] if "speaker_track_id" in row.keys() else None,
        "speaker_confidence": float(row["speaker_confidence"] or 0.0) if "speaker_confidence" in row.keys() else 0.0,
        "layout_mode": row["layout_mode"] if "layout_mode" in row.keys() and row["layout_mode"] else "TRACK",
        "audio_reaction": row["audio_reaction"] if "audio_reaction" in row.keys() else None,
        "audio_reaction_confidence": float(row["audio_reaction_confidence"] or 0.0) if "audio_reaction_confidence" in row.keys() else 0.0,
        "variant": row["variant"] if "variant" in row.keys() and row["variant"] else "normal",
        "parent_moment_id": row["parent_moment_id"] if "parent_moment_id" in row.keys() else None,
        "ranking": row["ranking"] if "ranking" in row.keys() else None,
        "is_recommended": bool(row["is_recommended"]) if "is_recommended" in row.keys() and row["is_recommended"] is not None else False,
        "quality_breakdown": json.loads(row["quality_breakdown"]) if "quality_breakdown" in row.keys() and row["quality_breakdown"] else {},
        "why_this_clip": json.loads(row["why_this_clip"]) if "why_this_clip" in row.keys() and row["why_this_clip"] else [],
        "recommendation_reasons": json.loads(row["recommendation_reasons"]) if "recommendation_reasons" in row.keys() and row["recommendation_reasons"] else [],
        "context_score": float(row["context_score"]) if "context_score" in row.keys() and row["context_score"] is not None else None,
        "bridge_score": float(row["bridge_score"]) if "bridge_score" in row.keys() and row["bridge_score"] is not None else None,
        "hook_type": row["hook_type"] if "hook_type" in row.keys() else None,
        "payoff_type": row["payoff_type"] if "payoff_type" in row.keys() else None,
        "context_completeness": float(row["context_completeness"]) if "context_completeness" in row.keys() and row["context_completeness"] is not None else None,
        "topic_family": row["topic_family"] if "topic_family" in row.keys() else None,
        "topic_label": row["topic_label"] if "topic_label" in row.keys() else None,
        "visual_quality_score": float(row["visual_quality_score"]) if "visual_quality_score" in row.keys() and row["visual_quality_score"] is not None else None,
        "headroom_score": float(row["headroom_score"]) if "headroom_score" in row.keys() and row["headroom_score"] is not None else None,
        "face_size_score": float(row["face_size_score"]) if "face_size_score" in row.keys() and row["face_size_score"] is not None else None,
        "boundary_adjustment": json.loads(row["boundary_adjustment"]) if "boundary_adjustment" in row.keys() and row["boundary_adjustment"] else {},
        "quality_flags": json.loads(row["quality_flags"]) if "quality_flags" in row.keys() and row["quality_flags"] else [],
    }
