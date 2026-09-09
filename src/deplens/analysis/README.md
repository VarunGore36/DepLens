# `analysis` — Status: `in progress` (Phase 2)

AST import parsing (`imports.py`), directory collection, stdlib filtering and import→dependency linking with alias table (`linking.py`), qualified API usage tracking with per-dependency filtering (`usage.py`). Scope-limited (no scope/shadowing analysis, relative imports skipped) — see module docstrings.
