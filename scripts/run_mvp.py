from apps.worker.pipeline import run_mvp
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: python scripts/run_mvp.py <path-to-vod>")

result = run_mvp(sys.argv[1])
print(result)
