# Agent Contract

This repository is a forked game and an AI/game-development testbed. Preserve both facts.

## Ownership map

```text
main.py
  tiny executable entrypoint only

space_invaders/core.py
  deterministic game rules and state transitions
  no pygame, filesystem, network, controller polling, or Player-Two import

space_invaders/app.py
  Pygame input/audio/rendering adapter
  presentation may consume core state but must not own game rules

space_invaders/ai.py
  transparent baseline policies
  do not call a heuristic "ML" or "RL"

space_invaders/training.py
  observation/action/reward/transition contract
  no pygame dependency

space_invaders/storage.py
  mutable local persistence

tests/
  deterministic rules and contract proof
```

## Development doctrine

1. Preserve Neural Lab attribution and the MIT license.
2. Do not rewrite the original history. `main` is the control specimen; evolution happens in reviewable branches/PRs.
3. A gameplay-rule change belongs in `core.py` and requires a deterministic test.
4. A renderer/input/audio change belongs in `app.py` and requires a real Pygame playtest before claiming it works visually.
5. Keep simulation time fixed-step. Rendering rate must not change game rules.
6. Seed randomness. A recorded seed + action stream should reproduce the same simulation state.
7. Keep Player Two contract-coupled, not source-tree-coupled. This repo must run without a Player-Two checkout.
8. Missing telemetry is unknown, not zero. Do not manufacture reward/scalar values to make a trainer happy.
9. Keep heuristic, behavior-cloned, evolutionary, supervised, and reinforcement-learning policies explicitly classified.
10. Optimize the game for humans first. Training speed and instrumentation are additional surfaces, not excuses to damage game feel.

## Controller boundary

Controllers produce only `Action` values. The current action bits are:

```text
LEFT  = 1
RIGHT = 2
FIRE  = 4
```

Human keyboard, scripted replay, heuristic P2, learned P2, network co-op, and fuzz tests should all enter through this boundary.

## Evidence ladder

Do not compress these into "works":

```text
source compiles
pure core tests pass
headless episode runs
Pygame imports
window launches
input/audio/rendering verified
co-op played by two humans
AI wingman observed in real play
training data recorded
learned policy beats a named baseline under a fixed evaluation suite
```

State the highest rung actually proven.

## Cross-repo rule

Player-Two and GameArchaeologyLab are consumers/research relatives, not runtime source dependencies. Prefer a small versioned observation/action/episode contract, JSONL artifacts, or a future package/API boundary. Never add `../Player-Two` to `sys.path`.

## Before a substantial change

Record:

```text
BASE SHA:
BRANCH:
BEHAVIOR OWNER:
CONTROL SPECIMEN BEHAVIOR:
CHANGE:
DETERMINISTIC PROOF:
VISUAL/RUNTIME PROOF:
UNKNOWN:
```

The goal is a better game and a better laboratory, with neither pretending to be the other.
