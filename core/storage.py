import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
import datetime

DEFAULT_DB_PATH = Path("data/clipforge.db")


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target = db_path or DEFAULT_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as conn:
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
                media_url, start_time, end_time, resolution, qc_json, created_at, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                reviewed_at = excluded.reviewed_at,
                render_status = excluded.render_status,
                render_notice = excluded.render_notice,
                media_url = excluded.media_url,
                qc_json = excluded.qc_json;
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
    }
