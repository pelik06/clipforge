class Publisher:
    """Platform-specific publishing interface.

    Publishing must remain separate from the clipping engine and require
    explicit approval.
    """

    def publish(self, video_path: str, metadata: dict) -> str:
        raise NotImplementedError
