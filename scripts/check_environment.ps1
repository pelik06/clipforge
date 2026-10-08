Write-Host "Checking ClipForge environment..."

if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "FFmpeg: OK"
} else {
    Write-Host "FFmpeg: MISSING"
}

if (Get-Command ffprobe -ErrorAction SilentlyContinue) {
    Write-Host "FFprobe: OK"
} else {
    Write-Host "FFprobe: MISSING"
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    python --version
} else {
    Write-Host "Python: MISSING"
}
