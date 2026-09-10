from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .core import Action, GameConfig


class Policy(Protocol):
    def act(self, observation: dict) -> Action: ...


@dataclass
class HeuristicPilot:
    """Deterministic baseline pilot for Player Two and regression tests.

    It is deliberately understandable rather than 'smart': dodge imminent shots,
    otherwise align under the most useful target, and fire when approximately
    lined up. Future learned policies can replace this object without changing
    the simulation or Pygame frontend.
    """

    config: GameConfig = GameConfig()
    dodge_radius: float = 58.0
    alignment_tolerance: float = 15.0
    deadband: float = 5.0

    def act(self, observation: dict) -> Action:
        me = observation["self"]
        if not me["active"]:
            return Action.NONE

        center_x = me["x"] + self.config.player_width / 2
        action = Action.NONE

        threat_direction = self._dodge_direction(center_x, me["y"], observation)
        if threat_direction < 0:
            action |= Action.LEFT
        elif threat_direction > 0:
            action |= Action.RIGHT
        else:
            target_x = self._target_x(center_x, observation)
            if target_x is not None:
                if target_x < center_x - self.deadband:
                    action |= Action.LEFT
                elif target_x > center_x + self.deadband:
                    action |= Action.RIGHT
                if abs(target_x - center_x) <= self.alignment_tolerance:
                    action |= Action.FIRE

        return action

    def _dodge_direction(self, x: float, y: float, observation: dict) -> int:
        candidates = []
        for shot in observation["hostile_projectiles"]:
            if shot["vy"] <= 0:
                continue
            dy = y - shot["y"]
            if dy < 0 or dy > 150:
                continue
            time_to_y = dy / max(shot["vy"], 1e-6)
            predicted_x = shot["x"] + shot["vx"] * time_to_y
            distance = predicted_x - x
            if abs(distance) <= self.dodge_radius:
                candidates.append((time_to_y, distance))
        if not candidates:
            return 0
        _time, distance = min(candidates)
        return 1 if distance <= 0 else -1

    @staticmethod
    def _target_x(x: float, observation: dict) -> float | None:
        enemies = observation["enemies"]
        if not enemies:
            return None
        target = min(
            enemies,
            key=lambda enemy: abs(enemy["x"] - x) * 0.7 - enemy["y"] * 0.3,
        )
        return target["x"] + 15.0
