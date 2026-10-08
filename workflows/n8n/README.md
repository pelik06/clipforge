# n8n Workflows

n8n is the orchestration layer.

Potential future workflow:

Schedule/Webhook
→ create ClipForge job
→ wait for completion
→ send Telegram approval
→ if approved → publish
→ cleanup

Do not move moment-detection logic into n8n.
