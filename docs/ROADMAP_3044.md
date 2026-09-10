# Roadmap 3044

The project should grow along two synchronized tracks:

```text
PLAYABLE GAME
    fun / feel / content / co-op / presentation

RESEARCH TESTBED
    determinism / telemetry / policies / evaluation / replay
```

Neither track is allowed to eat the other.

## R0: control specimen

Preserve the original Neural Lab fork on `main` as historical/control evidence.

Measure before claiming improvements: startup, basic controls, original progression, obvious defects and packaging behavior.

## R1: deterministic foundation

Current 3044 foundation:

- renderer-free fixed-step simulation;
- seeded randomness;
- first-class 1P/2P state;
- human and AI controller seam;
- local co-op and AI co-op frontend modes;
- formation waves and enemy fire;
- headless simulation CLI;
- structured/vector observations;
- JSONL transitions;
- portable high-score storage;
- pure-core tests and CI.

Exit gate: exact-head tests plus real Pygame smoke/playtest.

## R2: shmup vocabulary

Build depth before sheer asset count:

```text
enemy archetypes
aimed / radial / sweeping / lane patterns
elite formations
powerups and weapon choices
bomb/defensive mechanic
combo/risk scoring
mini-bosses and bosses
stage phases
telegraphed hazards
```

Prefer data-driven definitions over giant `if wave == ...` blocks.

## R3: campaign and replay

Add:

- mission/stage definitions;
- deterministic replay files;
- ghost playback;
- seeded daily challenge;
- run summary/heatmap telemetry;
- difficulty profiles;
- accessibility settings;
- save/settings separation.

A replay should contain game/version identity, seed and action stream rather than video frames.

## R4: Player Two academy

Benchmark policies in order of increasing complexity:

```text
random
static/simple scripted
HeuristicPilot
tuned/evolutionary heuristic
behavior cloning
small supervised models
RL where justified
```

Evaluate both solo competence and co-op usefulness.

The first learned model is not automatically the new default P2. It must beat simpler baselines on held-out evaluation and survive human co-op testing.

## R5: ShmupLab extraction

Only after at least two games consume the same contract, consider extracting reusable infrastructure into Player-Two/GameArchaeologyLab/a dedicated small package:

```text
controller protocol
transition/replay schema
episode evaluator
seed suites
co-op metrics
policy adapters
training report format
```

Do not prematurely turn one game's internals into a colony-wide framework.

## R6: content evolution

Potential 3044 directions:

```text
1979 homage mode
vector/neon 3044 campaign
branching bosses
adaptive but bounded director
2P human + AI wingman personality profiles
co-op synergy abilities
local tournament/evaluation lab
procedural challenge seeds
boss pattern editor
spectator/telemetry observatory
```

The director may tune content selection from measured performance, but difficulty adaptation must be visible/optional rather than secretly invalidating scores.

## R7: harvest into other projects

Reusable lessons, not copied source trees:

- deterministic gameplay architecture -> future small games and prototypes;
- controller injection -> Player-Two;
- telemetry/evidence semantics -> KiloCore Studio;
- replay/version provenance -> GameArchaeologyLab;
- modular content definitions -> larger Godot games such as Ash & Anvil where structurally relevant;
- development workflow/quality gates -> Dev-Mentor curriculum.

## North star

3044 is successful when it is simultaneously:

```text
a genuinely better game,
a tiny reproducible game-engine laboratory,
a useful co-op AI benchmark,
and a clean example another developer can understand without the colony attached.
```
