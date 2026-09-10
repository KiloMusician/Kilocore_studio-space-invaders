from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Literal

from .ai import HeuristicPilot
from .core import Action, GameConfig, ShmupEngine, actions_from_bools
from .storage import load_high_score, save_high_score


Mode = Literal["solo", "ai-coop", "local-coop"]


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / "assets" / Path(*parts)


@dataclass
class AudioBank:
    shoot: object | None = None
    kill: object | None = None
    hit: object | None = None
    muted: bool = False

    def set_muted(self, muted: bool) -> None:
        self.muted = muted
        volume = 0.0 if muted else 0.65
        for sound in (self.shoot, self.kill, self.hit):
            if sound is not None:
                sound.set_volume(volume)

    def play(self, name: str) -> None:
        if self.muted:
            return
        sound = getattr(self, name, None)
        if sound is not None:
            sound.play()


class PygameApp:
    """Thin Pygame adapter over the deterministic simulation core."""

    def __init__(self, *, mode: Mode = "ai-coop", seed: int = 3044) -> None:
        import pygame

        self.pg = pygame
        self.mode = mode
        self.seed = seed
        self.config = GameConfig()
        self.engine = ShmupEngine(self.config)
        self.engine.reset(seed=seed, players=1 if mode == "solo" else 2)
        self.p2 = HeuristicPilot(self.config)
        self.paused = False
        self.started = False
        self.running = True
        self.high_score = load_high_score(bundled_default=self._bundled_high_score())

        pygame.init()
        pygame.font.init()
        try:
            pygame.mixer.init()
            mixer_ok = True
        except pygame.error:
            mixer_ok = False

        self.screen = pygame.display.set_mode((self.config.width, self.config.height))
        pygame.display.set_caption("KiloCore Space Invaders 3044")
        self.clock = pygame.time.Clock()
        self.fonts: dict[int, object] = {}

        self.background = self._load_image(
            "images", "background.png", size=(self.config.width, self.config.height)
        )
        self.ship_image = self._load_image("images", "UFO.png")
        self.enemy_image = self._load_image(
            "images",
            "enemy.png",
            size=(int(self.config.enemy_width), int(self.config.enemy_height)),
        )
        self.bullet_image = self._load_image("images", "bullet.png", size=(8, 16))
        icon_path = resource_path("images", "icon.png")
        if icon_path.exists():
            pygame.display.set_icon(pygame.image.load(str(icon_path)))

        if mixer_ok:
            self.audio = AudioBank(
                shoot=self._load_sound("audios", "BulletFired.wav"),
                kill=self._load_sound("audios", "EnemyKilled.wav"),
                hit=self._load_sound("audios", "PlayerDied.wav"),
            )
            self.audio.set_muted(False)
        else:
            self.audio = AudioBank()

    def _bundled_high_score(self) -> int:
        import json

        source = Path(__file__).resolve().parents[1] / "data.json"
        try:
            return int(json.loads(source.read_text(encoding="utf-8")).get("HighScore", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 0

    def _load_image(self, *parts: str, size: tuple[int, int] | None = None):
        image = self.pg.image.load(str(resource_path(*parts))).convert_alpha()
        if size is not None:
            image = self.pg.transform.scale(image, size)
        return image

    def _load_sound(self, *parts: str):
        path = resource_path(*parts)
        return self.pg.mixer.Sound(str(path)) if path.exists() else None

    def _font(self, size: int):
        if size not in self.fonts:
            self.fonts[size] = self.pg.font.SysFont("consolas", size)
        return self.fonts[size]

    def run(self) -> int:
        accumulator = 0.0
        while self.running:
            frame_seconds = min(self.clock.tick(120) / 1000.0, 0.25)
            accumulator += frame_seconds
            self._events()
            actions = self._actions()

            if self.started and not self.paused and not self.engine.state.game_over:
                while accumulator >= self.config.dt:
                    before_shots = sum(
                        p.shots_fired for p in self.engine.state.players.values()
                    )
                    events = self.engine.step(actions)
                    after_shots = sum(
                        p.shots_fired for p in self.engine.state.players.values()
                    )
                    if after_shots > before_shots:
                        self.audio.play("shoot")
                    if events.kills:
                        self.audio.play("kill")
                    if events.player_hits:
                        self.audio.play("hit")
                    accumulator -= self.config.dt
            else:
                accumulator = min(accumulator, self.config.dt)

            self._draw()

        self._persist_high_score()
        self.pg.quit()
        return 0

    def _events(self) -> None:
        for event in self.pg.event.get():
            if event.type == self.pg.QUIT:
                self.running = False
            elif event.type == self.pg.KEYDOWN:
                if not self.started:
                    self.started = True
                if event.key == self.pg.K_p and self.started:
                    self.paused = not self.paused
                elif event.key == self.pg.K_m:
                    self.audio.set_muted(not self.audio.muted)
                elif event.key == self.pg.K_r and self.engine.state.game_over:
                    self._persist_high_score()
                    self.seed += 1
                    self.engine.reset(
                        seed=self.seed, players=1 if self.mode == "solo" else 2
                    )
                    self.paused = False
                    self.started = True
                elif event.key in (self.pg.K_q, self.pg.K_ESCAPE):
                    self.running = False

    def _actions(self) -> dict[int, Action]:
        keys = self.pg.key.get_pressed()
        actions = {
            1: actions_from_bools(
                left=keys[self.pg.K_a],
                right=keys[self.pg.K_d],
                fire=keys[self.pg.K_SPACE] or keys[self.pg.K_s],
            )
        }
        if self.mode == "ai-coop":
            actions[2] = self.p2.act(self.engine.observation(2))
        elif self.mode == "local-coop":
            actions[2] = actions_from_bools(
                left=keys[self.pg.K_LEFT],
                right=keys[self.pg.K_RIGHT],
                fire=keys[self.pg.K_RETURN] or keys[self.pg.K_RCTRL],
            )
        return actions

    def _draw(self) -> None:
        pg = self.pg
        self.screen.blit(self.background, (0, 0))

        for enemy in self.engine.state.enemies:
            rect = pg.Rect(
                int(enemy.x), int(enemy.y), int(enemy.width), int(enemy.height)
            )
            self.screen.blit(self.enemy_image, rect)
            if enemy.kind == "tank":
                pg.draw.rect(self.screen, (255, 185, 70), rect, width=2)

        for projectile in self.engine.state.projectiles:
            rect = pg.Rect(
                int(projectile.x),
                int(projectile.y),
                int(projectile.width),
                int(projectile.height),
            )
            if projectile.owner == "player":
                self.screen.blit(self.bullet_image, rect)
            else:
                pg.draw.rect(self.screen, (255, 88, 118), rect, border_radius=2)

        for pid, player in sorted(self.engine.state.players.items()):
            if not player.active:
                continue
            rect = pg.Rect(
                int(player.x), int(player.y), int(player.width), int(player.height)
            )
            image = pg.transform.scale(self.ship_image, rect.size)
            if player.invulnerable <= 0.0 or (self.engine.state.tick // 4) % 2 == 0:
                self.screen.blit(image, rect)
            border = (94, 220, 255) if pid == 2 else (255, 255, 255)
            pg.draw.rect(
                self.screen, border, rect.inflate(4, 4), width=2, border_radius=4
            )

        self._hud()
        if not self.started:
            self._center_text("SPACE INVADERS // 3044", 48, self.config.height // 2 - 60)
            self._center_text(
                "Press any key to deploy", 24, self.config.height // 2 + 8
            )
            label = (
                "P1: A/D + Space    P2: AI wingman"
                if self.mode == "ai-coop"
                else "P1: A/D + Space"
            )
            self._center_text(label, 18, self.config.height // 2 + 48)
        elif self.paused:
            self._center_text("PAUSED", 52, self.config.height // 2)
        elif self.engine.state.game_over:
            self._center_text("MISSION LOST", 56, self.config.height // 2 - 28)
            self._center_text(
                "R: redeploy    Q/Esc: quit", 22, self.config.height // 2 + 34
            )
        pg.display.flip()

    def _hud(self) -> None:
        state = self.engine.state
        self.high_score = max(self.high_score, state.score)
        lines = [
            f"SCORE {state.score:06d}   HIGH {self.high_score:06d}   WAVE {state.wave:02d}",
            "   ".join(
                f"P{pid} {'AI' if pid == 2 and self.mode == 'ai-coop' else 'HUM'} LIVES {player.lives}"
                for pid, player in sorted(state.players.items())
            ),
        ]
        for idx, text in enumerate(lines):
            surface = self._font(18).render(text, True, (235, 242, 255))
            self.screen.blit(surface, (12, 10 + idx * 24))

    def _center_text(self, text: str, size: int, y: int) -> None:
        surface = self._font(size).render(text, True, (242, 245, 255))
        self.screen.blit(
            surface, ((self.config.width - surface.get_width()) // 2, y)
        )

    def _persist_high_score(self) -> None:
        if self.high_score > 0:
            save_high_score(self.high_score)
