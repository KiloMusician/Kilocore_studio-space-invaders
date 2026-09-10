from __future__ import annotations

import math

from .core import GameConfig

STRUCTURED_OBSERVATION_SCHEMA = "kilocore.shmup-observation.v1"
VECTOR_OBSERVATION_SCHEMA = "kilocore.shmup-vector-observation.v1"
ACTION_SCHEMA = "kilocore.shmup-action.v1"
MAX_VECTOR_ENEMIES = 16
MAX_VECTOR_PROJECTILES = 20
VECTOR_FEATURE_COUNT = 6 + MAX_VECTOR_ENEMIES * 3 + MAX_VECTOR_PROJECTILES * 4


def vectorize_observation(
    observation: dict,
    config: GameConfig | None = None,
    *,
    max_enemies: int = MAX_VECTOR_ENEMIES,
    max_projectiles: int = MAX_VECTOR_PROJECTILES,
) -> list[float]:
    """Compile a structured observation into the stable v1 ML feature vector.

    The deterministic engine introduced the original v1 projection. This pure
    helper makes that representation available to checkpoint inference without
    requiring an engine object. Contract tests pin parity with
    ``ShmupEngine.vector_observation`` so the compatibility seam cannot drift
    silently while ownership is consolidated in a later refactor.
    """

    if observation.get("schema") != STRUCTURED_OBSERVATION_SCHEMA:
        raise ValueError(
            f"observation schema must be {STRUCTURED_OBSERVATION_SCHEMA!r}"
        )
    if max_enemies < 0 or max_projectiles < 0:
        raise ValueError("entity limits must be non-negative")

    cfg = config or GameConfig()
    me = observation["self"]
    vector = [
        float(me["x"]) / cfg.width,
        float(me["y"]) / cfg.height,
        float(me["lives"]) / max(1, cfg.player_lives),
        float(bool(me["active"])),
        min(float(me["cooldown"]) / max(cfg.player_fire_cooldown, 1e-9), 1.0),
        min(float(observation["wave"]) / 50.0, 1.0),
    ]

    enemies = sorted(
        observation["enemies"],
        key=lambda enemy: (
            abs((float(enemy["x"]) + cfg.enemy_width / 2) - float(me["x"])),
            -float(enemy["y"]),
        ),
    )[:max_enemies]
    for enemy in enemies:
        vector.extend(
            [
                float(enemy["x"]) / cfg.width,
                float(enemy["y"]) / cfg.height,
                min(float(enemy["hp"]) / 3.0, 1.0),
            ]
        )
    vector.extend([0.0] * (max_enemies - len(enemies)) * 3)

    projectiles = sorted(
        observation["hostile_projectiles"],
        key=lambda projectile: math.hypot(
            float(projectile["x"]) - float(me["x"]),
            float(projectile["y"]) - float(me["y"]),
        ),
    )[:max_projectiles]
    for projectile in projectiles:
        vector.extend(
            [
                float(projectile["x"]) / cfg.width,
                float(projectile["y"]) / cfg.height,
                max(-1.0, min(1.0, float(projectile["vx"]) / 400.0)),
                max(-1.0, min(1.0, float(projectile["vy"]) / 400.0)),
            ]
        )
    vector.extend([0.0] * (max_projectiles - len(projectiles)) * 4)

    if max_enemies == MAX_VECTOR_ENEMIES and max_projectiles == MAX_VECTOR_PROJECTILES:
        if len(vector) != VECTOR_FEATURE_COUNT:
            raise AssertionError(
                f"v1 vector width drifted: {len(vector)} != {VECTOR_FEATURE_COUNT}"
            )
    return vector
