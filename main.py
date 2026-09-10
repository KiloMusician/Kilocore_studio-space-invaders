from __future__ import annotations

import argparse
from pathlib import Path

from space_invaders.app import PygameApp
from space_invaders.learned import load_linear_policy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KiloCore Space Invaders 3044")
    parser.add_argument(
        "--mode",
        choices=("solo", "ai-coop", "local-coop"),
        default="ai-coop",
        help=(
            "solo = one human pilot; ai-coop = human P1 + Player Two policy; "
            "local-coop = two human pilots"
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=3044,
        help="Deterministic simulation seed for this deployment.",
    )
    parser.add_argument(
        "--p2-checkpoint",
        type=Path,
        help=(
            "Optional kilocore.shmup-linear-policy.v1 JSON checkpoint for P2. "
            "Only valid with --mode ai-coop; the heuristic remains the default."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.p2_checkpoint is not None and args.mode != "ai-coop":
        parser.error("--p2-checkpoint requires --mode ai-coop")

    app = PygameApp(mode=args.mode, seed=args.seed)
    if args.p2_checkpoint is not None:
        app.p2 = load_linear_policy(args.p2_checkpoint, config=app.config)
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
