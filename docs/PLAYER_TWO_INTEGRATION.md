# Player Two Integration

## Relationship

KiloCore Space Invaders is a **testbed/provider**. Player-Two is a **pilot/training system**.

They must remain independently runnable.

Do not add a source-tree dependency such as:

```text
sys.path += ../Player-Two
import playertwo...
```

Instead meet at a narrow controller/training contract.

## Shared idea with the existing Player-Two harness

Player-Two's emulator work already separates:

```text
in-process reflex/controller
from
out-of-process learning/directing
```

This Pygame testbed makes the same boundary cheaper because we own the simulation state directly:

```text
ShmupEngine
    -> observation
policy/controller
    -> action
ShmupEngine
    -> reward + next observation + events
recorder
    -> transition artifact
```

No framebuffer inference or RAM archaeology is required for this game, although those remain essential for emulated games where source state is unavailable.

## Action contract v1

Bitmask:

```text
NONE  = 0
LEFT  = 1
RIGHT = 2
FIRE  = 4
```

Opposing LEFT+RIGHT is legal input but produces zero horizontal movement. This keeps input validation deterministic and lets trainers discover/avoid useless actions without hidden coercion.

## Structured observation v1

Schema: `kilocore.shmup-observation.v1`

Contains:

```text
tick
wave
score
player_id
self {x, y, lives, active, cooldown, invulnerable}
allies[]
enemies[] {id, x, y, hp, kind, points}
hostile_projectiles[] {x, y, vx, vy}
```

This is the preferred semantic interchange surface.

## Vector observation v1

A fixed 134-float projection is available for compact ML policies:

```text
6 self/global features
16 enemies * 3
20 projectiles * 4
```

Entities are deterministically sorted before truncation/padding.

A model checkpoint must record the exact observation/action schema version and game revision used for training.

## Episode and transition artifacts

Episode result schema:

```text
kilocore.shmup-episode.v1
```

Transition schema:

```text
kilocore.shmup-transition.v1
```

JSONL transitions contain:

```text
observation
action
reward
next_observation
terminated
info
```

This is intentionally boring and portable. Player-Two can ingest an artifact without importing the game package.

## First training ladder

Do not jump directly to PPO because the word "AI" appears in the mission.

Use escalating baselines:

```text
B0 random action policy
B1 always-fire/stationary policy
B2 deterministic HeuristicPilot
B3 tuned heuristic / evolutionary parameter search
B4 behavior cloning from human or strong heuristic trajectories
B5 compact supervised policy / tree / MLP as appropriate
B6 RL only when evaluation shows the simpler lanes have saturated
```

Every stage should run against a fixed evaluation seed set plus held-out seeds.

## Metrics

Record separately:

```text
score
waves survived
lives remaining
deaths/damage
kills
shots fired
accuracy
ally survival
joint team score
wall-clock simulation throughput
policy inference time
```

Do not collapse all qualities into reward. In co-op, a selfish policy may score well while making an awful wingman.

Future cooperation metrics can include:

```text
lane interference
threat interception
coverage complementarity
ally rescue events
shared target efficiency
human preference / fun rating
```

## Determinism/evaluation rule

A policy comparison should publish:

```text
game commit
policy/checkpoint identity
observation schema
action schema
reward definition
seed set
number of episodes
summary distribution, not only best run
```

Training seeds and evaluation seeds should not be identical forever.

## Human + AI mode

The playable default is `ai-coop`:

```text
P1 human: A/D + Space/S
P2 AI: HeuristicPilot initially
```

The important achievement is not that the heuristic is brilliant. It is that the **P2 slot is now an explicit policy injection point**. A future Player-Two adapter can replace the heuristic without rewriting collision, rendering or input code.

## Cross-game harvest

What should graduate into Player-Two or GameArchaeologyLab only after it proves reusable:

- action/observation schema versioning;
- deterministic episode receipts;
- JSONL transition tooling;
- baseline/evaluation protocol;
- co-op partner metrics;
- replay-to-training conversion.

Game-specific formation rules, sprites and campaign content stay here.
