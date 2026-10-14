from typing import Dict, List, Set

STAGE_DEPENDENCIES: Dict[str, Set[str]] = {
    "asr": {"transcript", "captions", "semantic_score", "moments", "renders"},
    "caption_preset": {"captions", "renders"},
    "framing_mode": {"reframing", "renders"},
    "quality_weights": {"ranking", "recommendation"},
    "scene_detection": {"scenes", "moments", "reframing", "renders"},
}


class IncrementalDependencyTracker:
    """Calculates granular stage invalidations to prevent redundant analysis computations."""

    @staticmethod
    def get_invalidated_artifacts(changed_configs: List[str]) -> Set[str]:
        invalidated: Set[str] = set()
        for change in changed_configs:
            deps = STAGE_DEPENDENCIES.get(change.lower())
            if deps:
                invalidated.update(deps)
            else:
                invalidated.add(change.lower())
        return invalidated

    @staticmethod
    def can_reuse_artifact(artifact_name: str, invalidated_artifacts: Set[str]) -> bool:
        return artifact_name.lower() not in invalidated_artifacts
