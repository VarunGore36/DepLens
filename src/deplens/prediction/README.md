# `prediction` — Status: `in progress` (Phase 4)

`baselines.py` implements the four Phase 4 heuristics over `UpdateCase` (major-version, direct-dependency, API-change, dependency-depth) with `run_baselines` for joint scoring. `cases.py` builds measured cases from the dependency graph, import links, and API usage (`affected_imports`, `affected_apis`, depth, direct flag). Graph/ML/LLM methods (Phase 6) — `experimental / planned`.
