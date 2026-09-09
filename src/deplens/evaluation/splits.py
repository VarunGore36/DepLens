from __future__ import annotations


def temporal_split(dates: list[str], train_fraction: float = 0.7) -> tuple[list[int], list[int]]:
    if not 0.0 < train_fraction < 1.0:
        raise ValueError(f"train_fraction must be in (0, 1), got {train_fraction}")
    ordered = sorted(range(len(dates)), key=lambda i: (dates[i], i))
    cutoff = int(len(ordered) * train_fraction)
    if cutoff == 0 or cutoff == len(ordered):
        raise ValueError(f"train_fraction {train_fraction} leaves an empty split for {len(dates)} items")
    return ordered[:cutoff], ordered[cutoff:]
