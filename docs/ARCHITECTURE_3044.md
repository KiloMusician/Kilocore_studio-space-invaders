# Architecture 3044

## Control specimen

The fork begins as Neural Lab's compact Pygame shooter: one `main.py` owns assets, input, movement, collisions, levels, rendering, audio and persistence.

That is valuable as a control specimen, but it makes automated testing, co-op, replay and AI training unnecessarily entangled with the display loop.

3044 evolves by **extraction, not erasure**.

## Runtime shape

```text
human keyboard ─┐
Player Two AI ──┼─> controller Action map
replay/fuzzer ──┘          │
                           ▼
                 deterministic ShmupEngine
                  state -> step -> events
                    │             │
                    │             ├─> telemetry / reward / replay
                    │             └─> deterministic tests
                    ▼
                 Pygame renderer
              audio / HUD / effects
```

The game core has no dependency on Pygame. Pygame has no authority over game rules.

## Why fixed-step matters

The simulation advances at a configured 60 ticks per second. Rendering can run faster without making ships faster, fire cooldowns shorter or enemy behavior hardware-dependent.

Given:

```text
same version
same GameConfig
same seed
same initial state
same action stream
```

the expected simulation state is identical.

That property gives us:

- reliable regression tests;
- reproducible bug reports;
- replay/ghost support;
- accelerated headless evaluation;
- fair policy comparison;
- deterministic procedural-wave debugging.

## Two-player model

Two-player is not a separate game mode inside the rules engine. The engine owns a `players` mapping and accepts an action per player.

Frontends decide who supplies those actions:

```text
solo        P1 human
ai-coop     P1 human + P2 policy
local-coop  P1 human + P2 human
future      human + remote/network/controller/replay/learned policy
```

Team game-over occurs only when no player remains active.

## Difficulty and duration

The original falling-enemy stream becomes a formation/wave model:

- horizontal formation movement with edge drops;
- increasing columns and rows;
- enemy projectile pressure;
- basic target leading;
- tougher tank invaders after early waves;
- short deterministic wave breaks;
- bounded projectile count.

This is only the first content layer. The engine is deliberately data-friendly so future archetypes, patterns, bosses and campaign rules can be added without returning to a monolith.

## AI seam

`observation(player_id)` exposes structured state for explainable/scripted agents.

`vector_observation(player_id)` exposes a fixed-length normalized vector for lightweight ML baselines.

Current vector layout:

```text
self: 6
nearest 16 enemies: 16 * 3
nearest 20 hostile projectiles: 20 * 4
TOTAL: 134 floats
```

The vector schema is a convenience projection. The structured observation remains easier to evolve safely.

## Training seam

`ShmupEnv` provides a minimal dependency-free interface:

```python
obs = env.reset(seed=3044)
next_obs, reward, terminated, info = env.step(action)
```

This is intentionally Gym-like rather than Gym-dependent. A future Gymnasium wrapper can adapt it without forcing the playable game to carry a scientific Python stack.

Transitions can be written as JSONL using `kilocore.shmup-transition.v1`.

## Reward doctrine

Reward is currently a declared engineering baseline, not proof of an ideal objective:

```text
team score delta
+ personal kill credit
+ wave progression
- life loss
+ tiny living reward
```

Every future learned-policy experiment should publish its reward definition and compare against the deterministic heuristic baseline. "Higher reward" and "more fun co-op partner" are not automatically equivalent.

## Persistence

High-score state no longer belongs inside the source/package tree. It resolves through environment configuration or a user-local state path and is written atomically.

The bundled `data.json` is treated only as a legacy/default seed value.

## Provenance boundary

Neural Lab owns the original implementation and assets under the repository's MIT license. KiloCore 3044 changes are a downstream evolution of that work. Preserve attribution and license headers/history when packaging or redistributing.

## Architecture invariant

> A human, a heuristic, and a learned policy should be interchangeable at the controller seam without the game engine knowing which one is flying.
