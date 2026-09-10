from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ai import HeuristicPilot
from .learned import load_linear_policy
from .training import run_episode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run headless deterministic shmup episodes")
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--seed", type=int, default=3044)
    parser.add_argument("--max-ticks", type=int, default=60 * 180)
    parser.add_argument("--record-dir", type=Path)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        help=(
            "Optional kilocore.shmup-linear-policy.v1 checkpoint. "
            "Without it the deterministic heuristic baseline is used."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.episodes < 1:
        raise SystemExit("--episodes must be >= 1")

    pilot = load_linear_policy(args.checkpoint) if args.checkpoint else HeuristicPilot()
    results = []
    for episode in range(args.episodes):
        seed = args.seed + episode
        record_path = args.record_dir / f"episode-{seed}.jsonl" if args.record_dir else None
        result = run_episode(
            pilot,
            seed=seed,
            max_ticks=args.max_ticks,
            teammate_policy=pilot,
            record_path=record_path,
        )
        if args.checkpoint:
            result["policy"] = {
                "kind": "linear_checkpoint",
                "checkpoint_sha256": pilot.checkpoint_sha256,
            }
        else:
            result["policy"] = {"kind": "heuristic"}
        results.append(result)

    print(json.dumps({"episodes": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
