import uuid
import json
from pathlib import Path
from apps.worker.pipeline_runner import execute_job_pipeline_sync
from core.storage import save_job, list_clips

job_id = f"job_sheila_{uuid.uuid4().hex[:6]}"
cfg = {
    "framing_mode": "track",
    "caption_preset": "creator_bold",
    "caption_words_per_group": 4,
    "max_clips": 2,
    "min_clip_duration": 15.0,
    "max_clip_duration": 35.0,
    "moment_threshold": 0.50,
}

save_job({
    "id": job_id,
    "vod_url": "https://youtu.be/KQK7hMCazFY",
    "kind": "youtube",
    "status": "created",
    "metadata": {},
    **cfg,
})

print(f"Starting job {job_id} on https://youtu.be/KQK7hMCazFY...")
final_job = execute_job_pipeline_sync(job_id, "https://youtu.be/KQK7hMCazFY", "youtube", config=cfg)
print(f"Job Status: {final_job['status']}")
print(f"Job Stage: {final_job['stage']}")

clips = list_clips(job_id=job_id)
print(f"\nTotal clips generated: {len(clips)}")
for c in clips:
    print(f"  Clip ID: {c['id']}")
    print(f"  Title: {c['title']}")
    print(f"  Duration: {c['duration']}")
    print(f"  Score: {c['score']}")
    print(f"  Media URL: {c['media_url']}")
    print("  ---")
