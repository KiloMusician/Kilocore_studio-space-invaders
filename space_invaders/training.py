from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .ai import Policy
from .core import Action, GameConfig, ShmupEngine
from .features import ACTION_SCHEMA, VECTOR_FEATURE_COUNT, VECTOR_OBSERVATION_SCHEMA


@dataclass(frozen=True)
class Transition:
    observation: list[float]
    action: int
    reward: float
    next_observation: list[float]
    terminated: bool
    info: dict


class ShmupEnv:
    """Small Gym-like adapter with no gym dependency.

    The API is intentionally serializable so Player Two, local ML experiments,
    evolutionary search, behavior cloning, or a future Gymnasium wrapper can all
    consume it without importing pygame.
    """

    def __init__(
        self,
        *,
        controlled_player: int = 2,
        players: int = 2,
        config: GameConfig | None = None,
    ) -> None:
        if controlled_player < 1 or controlled_player > players:
            raise ValueError("controlled_player must exist in the configured player count")
        self.engine = ShmupEngine(config)
        self.controlled_player = controlled_player
        self.players = players
        self._previous_score = 0
        self._previous_lives = 0
        self._previous_wave = 0

    def reset(self, seed: int = 0) -> list[float]:
        state = self.engine.reset(seed=seed, players=self.players)
        controlled = state.players[self.controlled_player]
        self._previous_score = state.score
        self._previous_lives = controlled.lives
        self._previous_wave = state.wave
        return self.engine.vector_observation(self.controlled_player)

    def step(
        self,
        action: Action | int,
        *,
        teammate_action: Action | int = Action.NONE,
    ) -> tuple[list[float], float, bool, dict]:
        actions = {self.controlled_player: Action(action)}
        for pid in self.engine.state.players:
            if pid != self.controlled_player:
                actions[pid] = Action(teammate_action)
        events = self.engine.step(actions)
        player = self.engine.state.players[self.controlled_player]

        score_delta = self.engine.state.score - self._previous_score
        lives_delta = player.lives - self._previous_lives
        wave_delta = self.engine.state.wave - self._previous_wave
        personal_kills = sum(1 for killer, _enemy_id in events.kills if killer == self.controlled_player)

        reward = (
            score_delta * 1.0
            + personal_kills * 0.75
            + wave_delta * 8.0
            + lives_delta * 20.0
            + (0.002 if player.active else 0.0)
        )
        self._previous_score = self.engine.state.score
        self._previous_lives = player.lives
        self._previous_wave = self.engine.state.wave

        terminated = self.engine.state.game_over
        info = {
            "tick": self.engine.state.tick,
            "wave": self.engine.state.wave,
            "score": self.engine.state.score,
            "lives": player.lives,
            "personal_kills": personal_kills,
            "events": {
                "kills": events.kills,
                "player_hits": events.player_hits,
                "player_deaths": events.player_deaths,
                "wave_started": events.wave_started,
            },
        }
        return self.engine.vector_observation(self.controlled_player), reward, terminated, info


def run_episode(
    policy: Policy,
    *,
    seed: int,
    max_ticks: int = 60 * 180,
    teammate_policy: Policy | None = None,
    record_path: str | Path | None = None,
) -> dict:
    env = ShmupEnv(controlled_player=2, players=2)
    observation = env.reset(seed)
    recorder = TransitionRecorder(record_path) if record_path else None
    total_reward = 0.0

    for _ in range(max_ticks):
        p2_action = policy.act(env.engine.observation(2))
        p1_action = teammate_policy.act(env.engine.observation(1)) if teammate_policy is not None else Action.NONE
        next_observation, reward, terminated, info = env.step(p2_action, teammate_action=p1_action)
        if recorder is not None:
            recorder.write(
                Transition(
                    observation=observation,
                    action=int(p2_action),
                    reward=reward,
                    next_observation=next_observation,
                    terminated=terminated,
                    info=info,
                )
            )
        observation = next_observation
        total_reward += reward
        if terminated:
            break

    return {
        "schema": "kilocore.shmup-episode.v1",
        "observation_schema": VECTOR_OBSERVATION_SCHEMA,
        "action_schema": ACTION_SCHEMA,
        "feature_count": VECTOR_FEATURE_COUNT,
        "seed": seed,
        "ticks": env.engine.state.tick,
        "wave": env.engine.state.wave,
        "score": env.engine.state.score,
        "total_reward": total_reward,
        "players": {
            pid: {
                "lives": player.lives,
                "shots_fired": player.shots_fired,
                "hits": player.hits,
                "damage_taken": player.damage_taken,
            }
            for pid, player in sorted(env.engine.state.players.items())
        },
        "terminated": env.engine.state.game_over,
    }


class TransitionRecorder:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, transition: Transition) -> None:
        payload = {
            "schema": "kilocore.shmup-transition.v1",
            "observation_schema": VECTOR_OBSERVATION_SCHEMA,
            "action_schema": ACTION_SCHEMA,
            "feature_count": VECTOR_FEATURE_COUNT,
            "observation": transition.observation,
            "action": transition.action,
            "reward": transition.reward,
            "next_observation": transition.next_observation,
            "terminated": transition.terminated,
            "info": transition.info,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
