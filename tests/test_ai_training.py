from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from space_invaders.ai import HeuristicPilot
from space_invaders.core import Action
from space_invaders.training import ShmupEnv, Transition, TransitionRecorder


class PilotAndTrainingTests(unittest.TestCase):
    def test_heuristic_returns_action(self) -> None:
        env = ShmupEnv(controlled_player=2, players=2)
        env.reset(seed=3044)
        action = HeuristicPilot().act(env.engine.observation(2))
        self.assertIsInstance(action, Action)

    def test_projected_shot_causes_dodge(self) -> None:
        pilot = HeuristicPilot()
        observation = {
            "self": {"x": 380.0, "y": 540.0, "active": True},
            "enemies": [],
            "hostile_projectiles": [
                {"x": 400.0, "y": 480.0, "vx": 0.0, "vy": 210.0}
            ],
        }
        action = pilot.act(observation)
        self.assertTrue(action & (Action.LEFT | Action.RIGHT))

    def test_life_loss_produces_negative_reward(self) -> None:
        env = ShmupEnv(controlled_player=2, players=2)
        env.reset(seed=12)
        player = env.engine.state.players[2]
        player.lives -= 1
        _obs, reward, _done, info = env.step(Action.NONE)
        self.assertLess(reward, 0)
        self.assertEqual(info["lives"], player.lives)

    def test_transition_recorder_writes_jsonl_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "episode.jsonl"
            recorder = TransitionRecorder(path)
            recorder.write(
                Transition(
                    observation=[0.0, 1.0],
                    action=int(Action.FIRE),
                    reward=1.25,
                    next_observation=[0.1, 0.9],
                    terminated=False,
                    info={"tick": 4},
                )
            )
            payload = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["schema"], "kilocore.shmup-transition.v1")
            self.assertEqual(payload["action"], int(Action.FIRE))
            self.assertEqual(payload["info"]["tick"], 4)


if __name__ == "__main__":
    unittest.main()
