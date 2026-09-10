from __future__ import annotations

import unittest

from space_invaders.core import Action, ProjectileState, ShmupEngine


class ShmupCoreTests(unittest.TestCase):
    def test_same_seed_and_actions_produce_same_snapshot(self) -> None:
        first = ShmupEngine()
        second = ShmupEngine()
        first.reset(seed=3044, players=2)
        second.reset(seed=3044, players=2)

        for tick in range(600):
            action = Action.FIRE | (Action.LEFT if (tick // 45) % 2 else Action.RIGHT)
            actions = {1: action, 2: Action.FIRE}
            first.step(actions)
            second.step(actions)

        self.assertEqual(first.snapshot(), second.snapshot())

    def test_two_players_are_first_class_state(self) -> None:
        engine = ShmupEngine()
        state = engine.reset(seed=7, players=2)
        self.assertEqual(set(state.players), {1, 2})
        self.assertTrue(state.players[1].active)
        self.assertTrue(state.players[2].active)

    def test_player_actions_work_without_pygame(self) -> None:
        engine = ShmupEngine()
        engine.reset(seed=7, players=1)
        x_before = engine.state.players[1].x
        engine.step({1: Action.LEFT | Action.FIRE})
        player = engine.state.players[1]
        self.assertLess(player.x, x_before)
        self.assertEqual(player.shots_fired, 1)
        self.assertTrue(any(p.owner == "player" for p in engine.state.projectiles))

    def test_enemy_collision_removal_does_not_skip_neighbor(self) -> None:
        engine = ShmupEngine()
        engine.reset(seed=2, players=1)
        first, second = engine.state.enemies[:2]
        first.x = 100.0
        first.y = 200.0
        second.x = 140.0
        second.y = 200.0
        engine.state.enemies = [first, second]
        engine.state.projectiles = [
            ProjectileState(1, "player", 1, first.x, first.y, 0, 0, first.width, first.height),
            ProjectileState(2, "player", 1, second.x, second.y, 0, 0, second.width, second.height),
        ]
        engine.state.next_projectile_id = 3

        events = engine.step({})
        self.assertEqual(engine.state.enemies, [])
        self.assertEqual(len(events.kills), 2)

    def test_vector_observation_has_stable_shape(self) -> None:
        engine = ShmupEngine()
        engine.reset(seed=8, players=2)
        vector = engine.vector_observation(2)
        self.assertEqual(len(vector), 6 + 16 * 3 + 20 * 4)
        self.assertTrue(all(isinstance(value, float) for value in vector))

    def test_game_over_requires_all_players_to_be_out(self) -> None:
        engine = ShmupEngine()
        engine.reset(seed=8, players=2)
        engine.state.players[1].lives = 0
        engine.state.players[1].active = False
        engine.step({2: Action.NONE})
        self.assertFalse(engine.state.game_over)

        engine.state.players[2].lives = 0
        engine.state.players[2].active = False
        engine.step({})
        self.assertTrue(engine.state.game_over)


if __name__ == "__main__":
    unittest.main()
