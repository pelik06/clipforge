"""HyperFrames Composition Structural & Semantic Validator.

Ensures that layer bounds, timings, asset references, and canvas dimensions
comply with the HyperFrames authoring contract before triggering rendering.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from services.render.hyperframes_models import HyperframesComposition, LayerType


@dataclass
class CompositionValidationResult:
    valid: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class HyperframesValidator:
    """Pre-render validation gate checking structural and timing invariants."""

    def validate(self, composition: HyperframesComposition) -> CompositionValidationResult:
        issues: List[str] = []
        warnings: List[str] = []

        # 1. Canvas Dimensions
        if composition.width != 1080 or composition.height != 1920:
            warnings.append(f"Non-standard canvas dimensions: {composition.width}x{composition.height} (expected 1080x1920)")

        # 2. Total Duration
        if composition.duration <= 0.0:
            issues.append(f"Invalid composition duration: {composition.duration}s (must be > 0.0s)")

        # 3. Base Video Layer
        video_layers = [l for l in composition.layers if l.type == LayerType.VIDEO]
        if not video_layers:
            issues.append("Missing required base VIDEO layer in composition")
        else:
            v_layer = video_layers[0]
            if v_layer.duration <= 0.0:
                issues.append(f"Base video layer duration must be > 0.0s, got {v_layer.duration}s")
            src = v_layer.data.get("src", "")
            if not src:
                issues.append("Base video layer missing 'src' data path")

        # 4. Visible Visual Layers
        visible_layers = [l for l in composition.layers if l.visible]
        if len(visible_layers) < 2:
            warnings.append(f"Only {len(visible_layers)} visible layer(s) declared; expected at least video + overlays")

        # 5. Layer Bounds & Timings
        for l in composition.layers:
            if l.start < 0.0:
                issues.append(f"Layer '{l.id}' has negative start time: {l.start}s")
            if l.end > (composition.duration + 0.5):
                warnings.append(f"Layer '{l.id}' end time ({l.end}s) exceeds composition duration ({composition.duration}s)")
            if l.start >= l.end and l.duration == 0.0:
                issues.append(f"Layer '{l.id}' has zero or negative duration: {l.start}s -> {l.end}s")
            if l.scale <= 0.0:
                issues.append(f"Layer '{l.id}' scale must be positive, got {l.scale}")
            if not (0.0 <= l.opacity <= 1.0):
                issues.append(f"Layer '{l.id}' opacity must be between 0.0 and 1.0, got {l.opacity}")

        # 6. Captions
        if composition.captions:
            for idx, c in enumerate(composition.captions):
                c_start = float(c.get("start", 0.0))
                c_end = float(c.get("end", 0.0))
                if c_start < 0.0:
                    issues.append(f"Caption #{idx} has negative start time: {c_start}s")
                if c_end <= c_start:
                    issues.append(f"Caption #{idx} start ({c_start}s) >= end ({c_end}s)")

        return CompositionValidationResult(
            valid=len(issues) == 0,
            issues=issues,
            warnings=warnings,
        )
