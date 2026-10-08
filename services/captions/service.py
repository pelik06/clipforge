class CaptionRenderer:
    """Generate and/or burn timed captions."""

    def render(self, transcript, video_path: str, output_path: str) -> str:
        raise NotImplementedError
