from deplens.prediction.baselines import (
    BASELINES,
    Prediction,
    UpdateCase,
    api_change_heuristic,
    coerce_version,
    depth_heuristic,
    direct_dependency_heuristic,
    major_version_heuristic,
    run_baselines,
    semver_change,
)

__all__ = [
    "BASELINES",
    "Prediction",
    "UpdateCase",
    "api_change_heuristic",
    "coerce_version",
    "depth_heuristic",
    "direct_dependency_heuristic",
    "major_version_heuristic",
    "run_baselines",
    "semver_change",
]
