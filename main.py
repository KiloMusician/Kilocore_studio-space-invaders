from __future__ import annotations

import argparse

from space_invaders.app import PygameApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KiloCore Space Invaders 3044")
    parser.add_argument(
        "--mode",
        choices=("solo", "ai-coop", "local-coop"),
        default="ai-coop",
        help=(
            "solo = one human pilot; ai-coop = human P1 + Player Two baseline; "
            "local-coop = two human pilots"
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=3044,
        help="Deterministic simulation seed for this deployment.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return PygameApp(mode=args.mode, seed=args.seed).run()


if __name__ == "__main__":
    raise SystemExit(main())
