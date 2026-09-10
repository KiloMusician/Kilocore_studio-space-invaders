from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntFlag
import math
import random
from typing import Mapping


class Action(IntFlag):
    NONE = 0
    LEFT = 1
    RIGHT = 2
    FIRE = 4


@dataclass(frozen=True)
class GameConfig:
    width: int = 800
    height: int = 600
    tick_hz: int = 60
    player_speed: float = 300.0
    player_width: float = 44.0
    player_height: float = 28.0
    player_lives: int = 3
    player_fire_cooldown: float = 0.18
    player_bullet_speed: float = 560.0
    player_invulnerability: float = 1.25
    enemy_width: float = 30.0
    enemy_height: float = 24.0
    enemy_bullet_speed: float = 210.0
    enemy_base_speed: float = 52.0
    enemy_drop_step: float = 16.0
    enemy_fire_rate: float = 0.18
    wave_break_seconds: float = 0.75
    max_enemy_projectiles: int = 36

    @property
    def dt(self) -> float:
        return 1.0 / self.tick_hz


@dataclass
class PlayerState:
    player_id: int
    x: float
    y: float
    width: float
    height: float
    lives: int
    cooldown: float = 0.0
    invulnerable: float = 0.0
    active: bool = True
    shots_fired: int = 0
    hits: int = 0
    damage_taken: int = 0


@dataclass
class EnemyState:
    enemy_id: int
    x: float
    y: float
    width: float
    height: float
    hp: int
    points: int
    kind: str
    column: int
    row: int


@dataclass
class ProjectileState:
    projectile_id: int
    owner: str
    owner_id: int
    x: float
    y: float
    vx: float
    vy: float
    width: float = 5.0
    height: float = 12.0


@dataclass
class StepEvents:
    kills: list[tuple[int, int]] = field(default_factory=list)
    player_hits: list[int] = field(default_factory=list)
    player_deaths: list[int] = field(default_factory=list)
    wave_started: int | None = None
    game_over: bool = False


@dataclass
class GameState:
    tick: int
    elapsed: float
    seed: int
    wave: int
    score: int
    players: dict[int, PlayerState]
    enemies: list[EnemyState]
    projectiles: list[ProjectileState]
    formation_direction: int
    wave_cooldown: float
    game_over: bool
    next_enemy_id: int
    next_projectile_id: int
    last_events: StepEvents = field(default_factory=StepEvents)


class ShmupEngine:
    """Deterministic, renderer-free fixed-timestep Space Invaders simulation.

    The engine owns game rules only. It never reads keyboard state, loads assets,
    touches the filesystem, or imports pygame. That separation is the seam used
    by the human frontend, Player Two controllers, tests, and training tools.
    """

    def __init__(self, config: GameConfig | None = None) -> None:
        self.config = config or GameConfig()
        self._rng = random.Random()
        self.state = self.reset(seed=0, players=1)

    def reset(self, seed: int = 0, players: int = 1) -> GameState:
        if players not in (1, 2):
            raise ValueError("players must be 1 or 2")
        self._rng.seed(seed)
        cfg = self.config
        player_states: dict[int, PlayerState] = {}
        starts = (cfg.width * 0.5,) if players == 1 else (cfg.width * 0.42, cfg.width * 0.58)
        for idx, center_x in enumerate(starts, start=1):
            player_states[idx] = PlayerState(
                player_id=idx,
                x=center_x - cfg.player_width / 2,
                y=cfg.height - cfg.player_height - 22,
                width=cfg.player_width,
                height=cfg.player_height,
                lives=cfg.player_lives,
            )

        self.state = GameState(
            tick=0,
            elapsed=0.0,
            seed=seed,
            wave=0,
            score=0,
            players=player_states,
            enemies=[],
            projectiles=[],
            formation_direction=1,
            wave_cooldown=0.0,
            game_over=False,
            next_enemy_id=1,
            next_projectile_id=1,
        )
        self._begin_next_wave()
        return self.state

    def step(self, actions: Mapping[int, Action | int] | None = None) -> StepEvents:
        state = self.state
        if state.game_over:
            return state.last_events

        cfg = self.config
        dt = cfg.dt
        state.tick += 1
        state.elapsed += dt
        events = StepEvents()
        state.last_events = events
        normalized = {pid: Action(value) for pid, value in (actions or {}).items()}

        self._update_players(normalized, dt)
        self._update_formation(dt)
        self._update_projectiles(dt)
        self._resolve_collisions(events)
        self._remove_expired_projectiles()
        self._resolve_breaches(events)
        self._maybe_enemy_fire(dt)
        self._advance_wave(dt, events)

        if not any(player.active for player in state.players.values()):
            state.game_over = True
            events.game_over = True
        return events

    def snapshot(self) -> dict:
        state = self.state
        return {
            "tick": state.tick,
            "elapsed": round(state.elapsed, 6),
            "seed": state.seed,
            "wave": state.wave,
            "score": state.score,
            "game_over": state.game_over,
            "players": {
                pid: {
                    "x": round(p.x, 6),
                    "y": round(p.y, 6),
                    "lives": p.lives,
                    "active": p.active,
                    "shots_fired": p.shots_fired,
                    "hits": p.hits,
                    "damage_taken": p.damage_taken,
                }
                for pid, p in sorted(state.players.items())
            },
            "enemies": [
                {"id": e.enemy_id, "x": round(e.x, 6), "y": round(e.y, 6), "hp": e.hp, "kind": e.kind}
                for e in state.enemies
            ],
            "projectiles": [
                {
                    "id": p.projectile_id,
                    "owner": p.owner,
                    "owner_id": p.owner_id,
                    "x": round(p.x, 6),
                    "y": round(p.y, 6),
                    "vx": round(p.vx, 6),
                    "vy": round(p.vy, 6),
                }
                for p in state.projectiles
            ],
        }

    def observation(self, player_id: int) -> dict:
        state = self.state
        if player_id not in state.players:
            raise KeyError(f"unknown player_id {player_id}")
        player = state.players[player_id]
        hostile = [p for p in state.projectiles if p.owner == "enemy"]
        return {
            "schema": "kilocore.shmup-observation.v1",
            "tick": state.tick,
            "wave": state.wave,
            "score": state.score,
            "player_id": player_id,
            "self": {
                "x": player.x,
                "y": player.y,
                "lives": player.lives,
                "active": player.active,
                "cooldown": player.cooldown,
                "invulnerable": player.invulnerable,
            },
            "allies": [
                {"player_id": p.player_id, "x": p.x, "y": p.y, "lives": p.lives, "active": p.active}
                for pid, p in sorted(state.players.items())
                if pid != player_id
            ],
            "enemies": [
                {"id": e.enemy_id, "x": e.x, "y": e.y, "hp": e.hp, "kind": e.kind, "points": e.points}
                for e in state.enemies
            ],
            "hostile_projectiles": [
                {"x": p.x, "y": p.y, "vx": p.vx, "vy": p.vy} for p in hostile
            ],
        }

    def vector_observation(self, player_id: int, *, max_enemies: int = 16, max_projectiles: int = 20) -> list[float]:
        """Fixed-size normalized vector suitable for lightweight ML baselines."""
        cfg = self.config
        obs = self.observation(player_id)
        me = obs["self"]
        vector = [
            me["x"] / cfg.width,
            me["y"] / cfg.height,
            me["lives"] / max(1, cfg.player_lives),
            float(me["active"]),
            min(me["cooldown"] / max(cfg.player_fire_cooldown, 1e-9), 1.0),
            min(obs["wave"] / 50.0, 1.0),
        ]
        enemies = sorted(
            obs["enemies"],
            key=lambda e: (abs((e["x"] + cfg.enemy_width / 2) - me["x"]), -e["y"]),
        )[:max_enemies]
        for enemy in enemies:
            vector.extend([enemy["x"] / cfg.width, enemy["y"] / cfg.height, min(enemy["hp"] / 3.0, 1.0)])
        vector.extend([0.0] * (max_enemies - len(enemies)) * 3)

        shots = sorted(
            obs["hostile_projectiles"],
            key=lambda p: math.hypot(p["x"] - me["x"], p["y"] - me["y"]),
        )[:max_projectiles]
        for shot in shots:
            vector.extend(
                [
                    shot["x"] / cfg.width,
                    shot["y"] / cfg.height,
                    max(-1.0, min(1.0, shot["vx"] / 400.0)),
                    max(-1.0, min(1.0, shot["vy"] / 400.0)),
                ]
            )
        vector.extend([0.0] * (max_projectiles - len(shots)) * 4)
        return vector

    def _update_players(self, actions: Mapping[int, Action], dt: float) -> None:
        cfg = self.config
        for pid, player in self.state.players.items():
            if not player.active:
                continue
            action = actions.get(pid, Action.NONE)
            direction = int(bool(action & Action.RIGHT)) - int(bool(action & Action.LEFT))
            player.x += direction * cfg.player_speed * dt
            player.x = max(0.0, min(cfg.width - player.width, player.x))
            player.cooldown = max(0.0, player.cooldown - dt)
            player.invulnerable = max(0.0, player.invulnerable - dt)
            if action & Action.FIRE and player.cooldown <= 0.0:
                self._spawn_player_projectile(player)
                player.cooldown = cfg.player_fire_cooldown
                player.shots_fired += 1

    def _spawn_player_projectile(self, player: PlayerState) -> None:
        state = self.state
        cfg = self.config
        state.projectiles.append(
            ProjectileState(
                projectile_id=state.next_projectile_id,
                owner="player",
                owner_id=player.player_id,
                x=player.x + player.width / 2 - 2.5,
                y=player.y - 12.0,
                vx=0.0,
                vy=-cfg.player_bullet_speed,
            )
        )
        state.next_projectile_id += 1

    def _update_formation(self, dt: float) -> None:
        enemies = self.state.enemies
        if not enemies:
            return
        cfg = self.config
        speed = cfg.enemy_base_speed * (1.0 + min(self.state.wave - 1, 20) * 0.055)
        dx = self.state.formation_direction * speed * dt
        min_x = min(e.x for e in enemies)
        max_x = max(e.x + e.width for e in enemies)
        hits_edge = (dx < 0 and min_x + dx <= 10.0) or (dx > 0 and max_x + dx >= cfg.width - 10.0)
        if hits_edge:
            self.state.formation_direction *= -1
            drop = cfg.enemy_drop_step + min(self.state.wave, 12) * 0.65
            for enemy in enemies:
                enemy.y += drop
        else:
            for enemy in enemies:
                enemy.x += dx

    def _update_projectiles(self, dt: float) -> None:
        for projectile in self.state.projectiles:
            projectile.x += projectile.vx * dt
            projectile.y += projectile.vy * dt

    @staticmethod
    def _overlap(a_x: float, a_y: float, a_w: float, a_h: float, b_x: float, b_y: float, b_w: float, b_h: float) -> bool:
        return a_x < b_x + b_w and a_x + a_w > b_x and a_y < b_y + b_h and a_y + a_h > b_y

    def _resolve_collisions(self, events: StepEvents) -> None:
        state = self.state
        removed_projectiles: set[int] = set()
        removed_enemies: set[int] = set()
        for projectile in tuple(state.projectiles):
            if projectile.owner != "player" or projectile.projectile_id in removed_projectiles:
                continue
            for enemy in tuple(state.enemies):
                if enemy.enemy_id in removed_enemies:
                    continue
                if not self._overlap(projectile.x, projectile.y, projectile.width, projectile.height, enemy.x, enemy.y, enemy.width, enemy.height):
                    continue
                removed_projectiles.add(projectile.projectile_id)
                enemy.hp -= 1
                if enemy.hp <= 0:
                    removed_enemies.add(enemy.enemy_id)
                    state.score += enemy.points
                    shooter = state.players.get(projectile.owner_id)
                    if shooter:
                        shooter.hits += 1
                    events.kills.append((projectile.owner_id, enemy.enemy_id))
                break

        for projectile in tuple(state.projectiles):
            if projectile.owner != "enemy" or projectile.projectile_id in removed_projectiles:
                continue
            for player in state.players.values():
                if not player.active or player.invulnerable > 0.0:
                    continue
                if not self._overlap(projectile.x, projectile.y, projectile.width, projectile.height, player.x, player.y, player.width, player.height):
                    continue
                removed_projectiles.add(projectile.projectile_id)
                self._damage_player(player, events)
                break

        if removed_projectiles:
            state.projectiles = [p for p in state.projectiles if p.projectile_id not in removed_projectiles]
        if removed_enemies:
            state.enemies = [e for e in state.enemies if e.enemy_id not in removed_enemies]

    def _damage_player(self, player: PlayerState, events: StepEvents) -> None:
        cfg = self.config
        player.damage_taken += 1
        player.lives -= 1
        events.player_hits.append(player.player_id)
        if player.lives <= 0:
            player.lives = 0
            player.active = False
            events.player_deaths.append(player.player_id)
            return
        player.invulnerable = cfg.player_invulnerability
        if len(self.state.players) > 1:
            center = cfg.width * (0.42 if player.player_id == 1 else 0.58)
        else:
            center = cfg.width * 0.5
        player.x = center - player.width / 2

    def _remove_expired_projectiles(self) -> None:
        cfg = self.config
        self.state.projectiles = [
            p for p in self.state.projectiles
            if -40.0 <= p.y <= cfg.height + 40.0 and -40.0 <= p.x <= cfg.width + 40.0
        ]

    def _resolve_breaches(self, events: StepEvents) -> None:
        if not self.state.enemies:
            return
        cfg = self.config
        breach_y = cfg.height - cfg.player_height - 36.0
        if max(enemy.y + enemy.height for enemy in self.state.enemies) < breach_y:
            return
        for player in self.state.players.values():
            if player.active:
                self._damage_player(player, events)
        self.state.enemies.clear()
        self.state.projectiles = [p for p in self.state.projectiles if p.owner == "player"]

    def _maybe_enemy_fire(self, dt: float) -> None:
        state = self.state
        cfg = self.config
        if not state.enemies or state.game_over:
            return
        if sum(1 for p in state.projectiles if p.owner == "enemy") >= cfg.max_enemy_projectiles:
            return
        difficulty = 1.0 + min(state.wave - 1, 20) * 0.06
        expected = cfg.enemy_fire_rate * difficulty * dt * max(1, len(state.enemies) / 6)
        if self._rng.random() >= min(expected, 0.35):
            return

        bottom_by_column: dict[int, EnemyState] = {}
        for enemy in state.enemies:
            incumbent = bottom_by_column.get(enemy.column)
            if incumbent is None or enemy.y > incumbent.y:
                bottom_by_column[enemy.column] = enemy
        shooter = self._rng.choice(list(bottom_by_column.values()))
        target = self._nearest_active_player(shooter.x + shooter.width / 2)
        if target is None:
            return
        center_x = shooter.x + shooter.width / 2
        center_y = shooter.y + shooter.height
        target_x = target.x + target.width / 2
        horizontal = max(-110.0, min(110.0, (target_x - center_x) * 0.22))
        state.projectiles.append(
            ProjectileState(
                projectile_id=state.next_projectile_id,
                owner="enemy",
                owner_id=shooter.enemy_id,
                x=center_x - 2.5,
                y=center_y,
                vx=horizontal,
                vy=cfg.enemy_bullet_speed * difficulty,
            )
        )
        state.next_projectile_id += 1

    def _nearest_active_player(self, x: float) -> PlayerState | None:
        active = [p for p in self.state.players.values() if p.active]
        if not active:
            return None
        return min(active, key=lambda p: abs((p.x + p.width / 2) - x))

    def _advance_wave(self, dt: float, events: StepEvents) -> None:
        state = self.state
        if state.game_over:
            return
        if state.enemies:
            state.wave_cooldown = 0.0
            return
        state.wave_cooldown += dt
        if state.wave_cooldown >= self.config.wave_break_seconds:
            self._begin_next_wave()
            events.wave_started = state.wave

    def _begin_next_wave(self) -> None:
        state = self.state
        cfg = self.config
        state.wave += 1
        state.wave_cooldown = 0.0
        state.formation_direction = 1 if state.wave % 2 else -1
        columns = min(10, 5 + (state.wave - 1) // 2)
        rows = min(5, 2 + (state.wave - 1) // 4)
        spacing_x = cfg.enemy_width + 18.0
        spacing_y = cfg.enemy_height + 16.0
        formation_width = columns * cfg.enemy_width + (columns - 1) * 18.0
        start_x = (cfg.width - formation_width) / 2
        start_y = 70.0
        tank_every = 5 if state.wave >= 4 else 999
        for row in range(rows):
            for column in range(columns):
                kind = "tank" if (row * columns + column + 1) % tank_every == 0 else "invader"
                hp = 2 if kind == "tank" else 1
                points = 3 if kind == "tank" else 1
                state.enemies.append(
                    EnemyState(
                        enemy_id=state.next_enemy_id,
                        x=start_x + column * spacing_x,
                        y=start_y + row * spacing_y,
                        width=cfg.enemy_width,
                        height=cfg.enemy_height,
                        hp=hp,
                        points=points,
                        kind=kind,
                        column=column,
                        row=row,
                    )
                )
                state.next_enemy_id += 1


def actions_from_bools(*, left: bool = False, right: bool = False, fire: bool = False) -> Action:
    value = Action.NONE
    if left:
        value |= Action.LEFT
    if right:
        value |= Action.RIGHT
    if fire:
        value |= Action.FIRE
    return value
