from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .core import Action, GameConfig
from .features import (
    ACTION_SCHEMA,
    VECTOR_FEATURE_COUNT,
    VECTOR_OBSERVATION_SCHEMA,
    vectorize_observation,
)

LINEAR_POLICY_SCHEMA = "kilocore.shmup-linear-policy.v1"
_OUTPUT_ACTIONS = {
    "left": Action.LEFT,
    "right": Action.RIGHT,
    "fire": Action.FIRE,
}


@dataclass(frozen=True)
class LinearHead:
    weights: tuple[float, ...]
    bias: float
    threshold: float = 0.0

    def active(self, features: list[float]) -> bool:
        score = self.bias + sum(weight * value for weight, value in zip(self.weights, features))
        return score >= self.threshold


@dataclass
class LinearPilot:
    """Portable learned P2 policy with no ML-runtime dependency.

    Player Two or another trainer may produce this checkpoint, but the game owns
    strict loading and inference against its versioned observation/action
    contract. Loading a checkpoint never grants that trainer source access or
    runtime authority inside the game.
    """

    heads: dict[str, LinearHead]
    config: GameConfig = GameConfig()
    metadata: dict[str, Any] | None = None
    checkpoint_sha256: str | None = None

    def act(self, observation: dict) -> Action:
        features = vectorize_observation(observation, self.config)
        if len(features) != VECTOR_FEATURE_COUNT:
            raise ValueError(
                f"feature width {len(features)} does not match checkpoint contract "
                f"{VECTOR_FEATURE_COUNT}"
            )
        action = Action.NONE
        for name, bit in _OUTPUT_ACTIONS.items():
            if self.heads[name].active(features):
                action |= bit
        return action

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        config: GameConfig | None = None,
        checkpoint_sha256: str | None = None,
    ) -> "LinearPilot":
        if not isinstance(payload, dict):
            raise ValueError("checkpoint must be a JSON object")
        if payload.get("schema") != LINEAR_POLICY_SCHEMA:
            raise ValueError(f"checkpoint schema must be {LINEAR_POLICY_SCHEMA!r}")
        if payload.get("observation_schema") != VECTOR_OBSERVATION_SCHEMA:
            raise ValueError(
                f"observation_schema must be {VECTOR_OBSERVATION_SCHEMA!r}"
            )
        if payload.get("action_schema") != ACTION_SCHEMA:
            raise ValueError(f"action_schema must be {ACTION_SCHEMA!r}")
        if payload.get("feature_count") != VECTOR_FEATURE_COUNT:
            raise ValueError(
                f"feature_count must be {VECTOR_FEATURE_COUNT}, got "
                f"{payload.get('feature_count')!r}"
            )

        outputs = payload.get("outputs")
        if not isinstance(outputs, dict):
            raise ValueError("outputs must be an object")
        if set(outputs) != set(_OUTPUT_ACTIONS):
            raise ValueError(
                f"outputs must contain exactly {sorted(_OUTPUT_ACTIONS)}, got "
                f"{sorted(outputs) if isinstance(outputs, dict) else outputs!r}"
            )

        heads: dict[str, LinearHead] = {}
        for name in _OUTPUT_ACTIONS:
            raw = outputs[name]
            if not isinstance(raw, dict):
                raise ValueError(f"outputs.{name} must be an object")
            weights = raw.get("weights")
            if not isinstance(weights, list) or len(weights) != VECTOR_FEATURE_COUNT:
                actual = len(weights) if isinstance(weights, list) else "non-list"
                raise ValueError(
                    f"outputs.{name}.weights must contain exactly "
                    f"{VECTOR_FEATURE_COUNT} values, got {actual}"
                )
            normalized_weights = tuple(
                _finite_number(value, f"outputs.{name}.weights[{index}]")
                for index, value in enumerate(weights)
            )
            bias = _finite_number(raw.get("bias", 0.0), f"outputs.{name}.bias")
            threshold = _finite_number(
                raw.get("threshold", 0.0), f"outputs.{name}.threshold"
            )
            heads[name] = LinearHead(
                weights=normalized_weights,
                bias=bias,
                threshold=threshold,
            )

        metadata = payload.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError("metadata must be an object when present")

        return cls(
            heads=heads,
            config=config or GameConfig(),
            metadata=dict(metadata or {}),
            checkpoint_sha256=checkpoint_sha256,
        )


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{label} must be a finite number")
    return normalized


def load_linear_policy(
    path: str | Path,
    *,
    config: GameConfig | None = None,
) -> LinearPilot:
    source = Path(path)
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read checkpoint {source}: {exc}") from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid checkpoint JSON in {source}: {exc}") from exc

    digest = hashlib.sha256(raw).hexdigest()
    return LinearPilot.from_payload(
        payload,
        config=config,
        checkpoint_sha256=digest,
    )
