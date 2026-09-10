from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ai import HeuristicPilot
from .training import run_episode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run headless deterministic shmup episodes")
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--seed", type=int, default=3044)
    parser.add_argument("--max-ticks", type=int, default=60 * 180)
    parser.add_argument("--record-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.episodes < 1:
        raise SystemExit("--episodes must be >= 1")
    pilot = HeuristicPilot()
    results = []
    for episode in range(args.episodes):
        seed = args.seed + episode
        record_path = args.record_dir / f"episode-{seed}.jsonl" if args.record_dir else None
        results.append(
            run_episode(
                pilot,
                seed=seed,
                max_ticks=args.max_ticks,
                teammate_policy=pilot,
                record_path=record_path,
            )
        )
    print(json.dumps({"episodes": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
