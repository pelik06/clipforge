import importlib
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from core.config.settings import Settings
from core.models.transcript import TranscriptSegment, Word


def is_whisper_available() -> bool:
    """Check if faster-whisper or openai-whisper transcription engine is available."""
    for mod_name in ("faster_whisper", "whisper"):
        try:
            importlib.import_module(mod_name)
            return True
        except ImportError:
            pass
    return False


def decode_audio_with_ffmpeg(media_path: str, sample_rate: int = 16000) -> np.ndarray:
    """Decode audio track to float32 16kHz mono numpy array directly via FFmpeg."""
    s = Settings()
    cmd = [
        s.ffmpeg_bin,
        "-y",
        "-i", str(media_path),
        "-vn",
        "-f", "f32le",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0 or not proc.stdout:
        raise RuntimeError(f"FFmpeg audio decoding failed: {proc.stderr[-300:].decode(errors='ignore')}")
    return np.frombuffer(proc.stdout, dtype=np.float32)


class Transcriber:
    """Full-video timestamped speech-to-text implementation with word-level timestamps."""

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        self.model_size = model_size or os.getenv("WHISPER_MODEL", "tiny")
        self.device = device or os.getenv("WHISPER_DEVICE", "cpu")
        self.compute_type = compute_type or os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        self._available = is_whisper_available()
        self._model_instance = None

    @property
    def is_available(self) -> bool:
        return self._available

    def _get_model(self):
        if self._model_instance is None:
            from faster_whisper import WhisperModel  # type: ignore

            self._model_instance = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model_instance

    def transcribe(
        self,
        media_path: str,
        language: Optional[str] = None,
        cached_segments: Optional[List[TranscriptSegment]] = None,
    ) -> List[TranscriptSegment]:
        """Transcribe speech across entire video producing verified word-level timestamps."""
        if cached_segments is not None:
            return cached_segments

        if not self._available:
            raise RuntimeError(
                "Speech transcription model unavailable: faster-whisper is not installed on host."
            )

        try:
            # 1. Decode audio via FFmpeg to 16kHz float32 numpy array
            audio_array = decode_audio_with_ffmpeg(media_path, sample_rate=16000)

            # 2. Transcribe with faster-whisper word_timestamps=True
            model = self._get_model()
            lang_param = None if language in (None, "auto") else language
            segments, _ = model.transcribe(
                audio_array,
                language=lang_param,
                word_timestamps=True,
                vad_filter=True,
            )

            result: List[TranscriptSegment] = []
            for seg in segments:
                words: List[Word] = []
                if hasattr(seg, "words") and seg.words:
                    for w in seg.words:
                        cleaned_word = w.word.strip()
                        if cleaned_word:
                            words.append(Word(text=cleaned_word, start=round(w.start, 2), end=round(w.end, 2)))

                result.append(
                    TranscriptSegment(
                        text=seg.text.strip(),
                        start=round(seg.start, 2),
                        end=round(seg.end, 2),
                        words=words,
                    )
                )
            return result
        except Exception as exc:
            raise RuntimeError(f"Transcription failed: {str(exc)}")


def serialize_words_for_llm(segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
    """Format word timestamps into compact format matching OpenShorts WORDS_JSON schema."""
    words_data = []
    for s in segments:
        for w in (s.words or []):
            words_data.append({"w": str(w.text), "s": float(round(w.start, 2)), "e": float(round(w.end, 2))})
    return words_data
