class ClipRenderer:
    """FFmpeg-backed renderer for final short-form clips."""

    def render(self, source_path: str, start: float, end: float, output_path: str) -> str:
        raise NotImplementedError
