from __future__ import annotations

import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from space_invaders.core import Action, ShmupEngine
from space_invaders.features import (
    ACTION_SCHEMA,
    VECTOR_FEATURE_COUNT,
    VECTOR_OBSERVATION_SCHEMA,
    vectorize_observation,
)
from space_invaders.learned import LINEAR_POLICY_SCHEMA, LinearPilot, load_linear_policy


class LearnedPolicyTests(unittest.TestCase):
    def _payload(self, *, active: tuple[str, ...] = ("fire",)) -> dict:
        outputs = {}
        for name in ("left", "right", "fire"):
            outputs[name] = {
                "weights": [0.0] * VECTOR_FEATURE_COUNT,
                "bias": 1.0 if name in active else -1.0,
                "threshold": 0.0,
            }
        return {
            "schema": LINEAR_POLICY_SCHEMA,
            "observation_schema": VECTOR_OBSERVATION_SCHEMA,
            "action_schema": ACTION_SCHEMA,
            "feature_count": VECTOR_FEATURE_COUNT,
            "outputs": outputs,
            "metadata": {
                "trainer": "fixture",
                "dataset_manifest_sha256": "0" * 64,
            },
        }

    def _observation(self) -> dict:
        engine = ShmupEngine()
        engine.reset(seed=3044, players=2)
        return engine.observation(2)

    def test_vector_helper_matches_engine_v1_projection(self) -> None:
        engine = ShmupEngine()
        engine.reset(seed=3044, players=2)
        structured = engine.observation(2)
        self.assertEqual(vectorize_observation(structured), engine.vector_observation(2))
        self.assertEqual(len(vectorize_observation(structured)), VECTOR_FEATURE_COUNT)
        self.assertEqual(VECTOR_FEATURE_COUNT, 134)

    def test_checkpoint_can_activate_exact_action_bits(self) -> None:
        pilot = LinearPilot.from_payload(self._payload(active=("left", "fire")))
        action = pilot.act(self._observation())
        self.assertEqual(action, Action.LEFT | Action.FIRE)
        self.assertEqual(int(action) & ~int(Action.LEFT | Action.RIGHT | Action.FIRE), 0)

    def test_checkpoint_inference_is_deterministic(self) -> None:
        pilot = LinearPilot.from_payload(self._payload(active=("right",)))
        observation = self._observation()
        self.assertEqual(pilot.act(observation), pilot.act(observation))

    def test_wrong_schema_is_rejected(self) -> None:
        payload = self._payload()
        payload["schema"] = "kilocore.shmup-linear-policy.v999"
        with self.assertRaisesRegex(ValueError, "checkpoint schema"):
            LinearPilot.from_payload(payload)

    def test_wrong_feature_width_is_rejected(self) -> None:
        payload = self._payload()
        payload["outputs"]["left"]["weights"].pop()
        with self.assertRaisesRegex(ValueError, "exactly 134"):
            LinearPilot.from_payload(payload)

    def test_nonfinite_parameter_is_rejected(self) -> None:
        payload = self._payload()
        payload["outputs"]["fire"]["weights"][7] = math.inf
        with self.assertRaisesRegex(ValueError, "finite number"):
            LinearPilot.from_payload(payload)

    def test_missing_or_unknown_output_head_is_rejected(self) -> None:
        payload = self._payload()
        payload["outputs"]["bomb"] = payload["outputs"].pop("fire")
        with self.assertRaisesRegex(ValueError, "outputs must contain exactly"):
            LinearPilot.from_payload(payload)

    def test_file_loader_records_exact_checkpoint_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pilot.json"
            raw = json.dumps(self._payload(), sort_keys=True).encode("utf-8")
            path.write_bytes(raw)
            pilot = load_linear_policy(path)
            self.assertEqual(pilot.checkpoint_sha256, hashlib.sha256(raw).hexdigest())
            self.assertEqual(pilot.act(self._observation()), Action.FIRE)

    def test_structured_observation_schema_is_enforced(self) -> None:
        pilot = LinearPilot.from_payload(self._payload())
        observation = self._observation()
        observation["schema"] = "wrong"
        with self.assertRaisesRegex(ValueError, "observation schema"):
            pilot.act(observation)


if __name__ == "__main__":
    unittest.main()
