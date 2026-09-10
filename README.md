# KiloCore Space Invaders // 3044

A downstream evolution of Neural Lab's compact Pygame Space Invaders project into a **deterministic co-op shmup and AI training testbed**.

The original project remains the lineage/control specimen. The 3044 branch adds a renderer-independent game core, human/AI controller injection, local co-op, an AI wingman, headless simulation, transition recording, tests and a staged path toward richer shmup content and Player Two learning.

## Lineage and license

This repository is a fork of `theneurallab/tiktok-space-invaders`, originally made by Neural Lab. The upstream project and assets are distributed under the MIT License; see `LICENSE` and preserve its copyright/permission notice when redistributing substantial portions.

3044 does not erase the upstream history. It builds on it.

## Current modes

```bash
python main.py --mode ai-coop     # default: P1 human + P2 heuristic wingman
python main.py --mode solo        # one human player
python main.py --mode local-coop  # two human players
```

Optional deterministic seed:

```bash
python main.py --mode ai-coop --seed 3044
```

### Controls

**Player 1**

- A / D: move
- Space or S: fire

**Player 2 in local co-op**

- Left / Right: move
- Enter or Right Ctrl: fire

**Global**

- P: pause
- M: mute
- R: restart after game over
- Q or Esc: quit

In `ai-coop`, Player 2 is currently a transparent deterministic heuristic pilot. It is deliberately **not** described as machine learning or reinforcement learning. The point of this stage is to establish the clean policy seam and measurable baseline that learned pilots must later beat.

## Headless AI / testing lane

The simulation does not require Pygame:

```bash
python -m space_invaders.simulate --episodes 10 --seed 3044
```

Record JSONL transitions:

```bash
python -m space_invaders.simulate \
  --episodes 10 \
  --seed 3044 \
  --record-dir runs/baseline
```

This produces deterministic episodes from a renderer-free fixed-timestep engine suitable for regression testing, scripted policies, behavior cloning datasets, evolutionary tuning and later learned policies.

## Architecture

```text
human input ─────┐
AI policy ───────┼─> Action map
replay / fuzzer ─┘       │
                         ▼
                deterministic core
                state -> step -> events
                  │              │
                  ▼              ├─> telemetry/training
              Pygame UI          └─> tests/replays
```

Key files:

```text
space_invaders/core.py      game rules, seeded state, fixed-step simulation
space_invaders/app.py       Pygame renderer/input/audio adapter
space_invaders/ai.py        transparent Player Two baseline policy
space_invaders/training.py  reset/step/reward + JSONL transition contract
space_invaders/storage.py   user-local atomic high-score persistence
space_invaders/simulate.py  headless episode CLI
tests/                      renderer-free deterministic proof
```

See:

- `docs/ARCHITECTURE_3044.md`
- `docs/PLAYER_TWO_INTEGRATION.md`
- `docs/ROADMAP_3044.md`
- `AGENTS.md`

## Gameplay changes in the foundation

3044 begins moving the game from a falling-enemy loop toward a fuller shmup vocabulary:

- classic horizontal formations with edge drops;
- multi-wave difficulty growth;
- enemy projectiles;
- limited aimed fire pressure;
- tougher multi-hit invaders after early waves;
- first-class two-player lives/state;
- team game-over only after both pilots are out;
- deterministic wave generation suitable for replays and policy evaluation.

This is foundation work, not the final content pass. Bosses, richer bullet patterns, weapon/powerup choices, stage data, replays, procedural challenges and deeper scoring belong to later reviewable waves.

## Development setup

```bash
python -m venv .venv
# activate the environment for your platform
pip install -r requirements.txt
python main.py
```

Renderer-free tests do not require Pygame:

```bash
python -m unittest discover -s tests -v
python -m space_invaders.simulate --episodes 2 --seed 3044 --max-ticks 600
```

## Why this game is useful to the wider colony

Because the project is small, we can completely instrument it without hiding complexity behind an emulator or a giant engine. It gives Player Two a cheap laboratory for policy interfaces and co-op metrics, gives Game Archaeology Lab a controlled counterpart to black-box arcade instrumentation, and gives the wider development platform a clean specimen for testing architecture, CI, telemetry, agent handoffs and game-development practice.

The transfer rule is **harvest contracts and lessons, not copied sibling source trees**.

## Original upstream feature set

The Neural Lab version provided Pygame rendering, sound effects, scoring/high-score persistence, progressive levels, pause/resume, audio mute controls and the original art/audio assets. Those foundations made this experiment possible.
