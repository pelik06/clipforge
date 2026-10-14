import uuid
import sys
from apps.worker.pipeline_runner import execute_job_pipeline_sync
from core.storage import save_job, list_clips

job_id = f"job_karaoke_test_{uuid.uuid4().hex[:6]}"
cfg = {
    "framing_mode": "auto_follow_speaker",
    "caption_preset": "karaoke",
    "max_clips": 2,
    "min_clip_duration": 30.0,
    "max_clip_duration": 60.0,
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

print(f"Starting test job {job_id} with karaoke preset...")
final_job = execute_job_pipeline_sync(job_id, "https://youtu.be/KQK7hMCazFY", "youtube", config=cfg)
print(f"Job Status: {final_job['status']}")
print(f"Job Stage: {final_job['stage']}")

for s in final_job.get("stages", []):
    status_str = s.get("status")
    detail_str = s.get("detail", "")
    print(f"  {s.get('id')}: {status_str} - {detail_str}")
    if s.get("error"):
        print(f"    ERROR: {s['error']}")

clips = list_clips(job_id=job_id)
print(f"\nTotal clips generated: {len(clips)}")
for c in clips:
    print(f"  Clip: {c['id']} | {c['title']} | dur: {c['duration']} | score: {c['score']} | URL: {c['media_url']}")
