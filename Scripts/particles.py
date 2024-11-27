import math
import pygame
from typing import Callable, Hashable, Sequence, Iterable, Optional

import Scripts.CONFIG as CFG


class ImageCache:
    def __init__(self, make_image_func: Callable[[Hashable], pygame.Surface]):
        self.cache: dict[Hashable, pygame.Surface] = {}
        self.misses = 0
        self.make_image = make_image_func

    def get_image(self, item: Hashable) -> pygame.Surface:
        if item not in self.cache:
            self.misses += 1
            self.cache[item] = self.make_image(item)
        return self.cache[item]


class Particle:
    def update(self, dt: float, *args, **kwargs) -> bool:
        """Return False when particle should be removed."""
        return True

    def draw_pos(self, image: pygame.Surface) -> Sequence[float]:
        raise NotImplementedError

    def cache_lookup(self) -> Hashable:
        raise NotImplementedError


class ParticleGroup:
    def __init__(self, blend: int = pygame.BLENDMODE_NONE, particles: Optional[list[Particle]] = None):
        self.particles: list[Particle] = particles if particles is not None else []
        self.blend = blend

    def __len__(self):
        return len(self.particles)

    def clear(self) -> None:
        self.particles.clear()

    def add(self, particles: Particle | Iterable[Particle]):
        if isinstance(particles, Particle):
            self.particles.append(particles)
        else:
            self.particles.extend(particles)

    def update(self, dt: float, *args, **kwargs):
        self.particles = [p for p in self.particles if p.update(dt, *args, **kwargs)]

    def _get_render_tuple(self, p: Particle, offset=(0, 0)) -> tuple[pygame.Surface, Sequence[float]]:
        pos = p.draw_pos()
        return (CFG.am.get(p.cache_lookup()), (pos[0]-offset[0], pos[1]-offset[1]))

    def render(self, screen: pygame.Surface, offset=(0, 0), blend: int = pygame.BLENDMODE_NONE):
        screen.fblits([self._get_render_tuple(p, offset) for p in self.particles], blend if blend else self.blend)


class AnimationParticle(Particle):
    def __init__(self, pos: tuple, vel: tuple, type: str, state: str) -> None:
        self.base_type = type
        self.type = type
        self.animation_state = state
        self.pos = pos
        self.vel = vel
        self.max_frames = CFG.am.get_animation_number_of_frames(f"particles-{self.base_type}", self.animation_state) - 1
        self.animation_frame = 0
        self.animation_frame_timer = 0.0

    def update(self, dt: float, *args, **kwargs) -> bool:
        self.pos = (self.pos[0] + self.vel[0] * dt, self.pos[1] + self.vel[1] * dt)
        if self.update_animation_state(dt):
            return False
        return True

    def draw_pos(self) -> Sequence[float]: return self.pos
    def cache_lookup(self) -> str: return self.type

    def update_animation_state(self, dt: float) -> bool:
        # returnt True sobald Animation fertig ist.
        end = False
        self.animation_frame_timer += dt
        if self.animation_frame_timer >= CFG.am.get_animation_frame_data(f"particles-{self.base_type}", self.animation_state)[self.animation_frame]:
            self.animation_frame += 1
            if self.animation_frame > self.max_frames:
                end = True
            self.animation_frame = min(self.animation_frame, self.max_frames)
            self.animation_frame_timer = 0.0
        self.type = f"ANIMATIONS/particles-{self.base_type}/{self.animation_state}/{int(self.animation_frame)}"
        return end


class LeafParticle(Particle):
    def __init__(self, pos: tuple, vel: tuple, max_imgs: int, type: str = "leaf") -> None:
        self.type = type
        self.pos = pos
        self.vel = vel
        self.max_ints = max_imgs
        self.state = 0  # which img to use right now?

    def update(self, dt: float, *args, **kwargs) -> bool:
        self.pos = (self.pos[0] + self.vel[0] * dt, self.pos[1] + self.vel[1] * dt)
        self.state += dt * 10
        if self.state > self.max_ints - 1:
            return False
        return True

    def draw_pos(self, image: pygame.Surface) -> Sequence[float]:
        # img benötigt um zu centern, falls gewollt
        return self.pos

    def cache_lookup(self) -> Hashable:
        s = str(int(self.state))
        if len(s) < 2:
            s = "0" + s
        return f"assets/particles/{self.type}/{s}.png"


class Spark:
    def __init__(self, pos: tuple, angle: float, speed: float, decay_speed: float = 1.0):
        self.pos = list(pos)
        self.angle = angle
        self.speed = speed
        self.decay_speed = decay_speed

    def update(self, dt: float):
        # return True
        self.pos[0] += math.cos(self.angle) * self.speed * dt
        self.pos[1] += math.sin(self.angle) * self.speed * dt

        self.speed = max(0, self.speed - 50 * dt * self.decay_speed)
        return self.speed > 0

    def render(self, surf: pygame.Surface, offset=(0, 0)):
        render_points = [
            (self.pos[0] + math.cos(self.angle) * self.speed * 1 - offset[0], self.pos[1] + math.sin(self.angle) * self.speed * 3 - offset[1]),
            (self.pos[0] + math.cos(self.angle + math.pi * 0.5) * self.speed * 0.3 - offset[0], self.pos[1] + math.sin(self.angle + math.pi * 0.5) * self.speed * 0.3 - offset[1]),
            (self.pos[0] + math.cos(self.angle + math.pi) * self.speed * 3 - offset[0], self.pos[1] + math.sin(self.angle + math.pi) * self.speed * 3 - offset[1]),
            (self.pos[0] + math.cos(self.angle - math.pi * 0.5) * self.speed * 0.3 - offset[0], self.pos[1] + math.sin(self.angle - math.pi * 0.5) * self.speed * 0.3 - offset[1]),
        ]

        pygame.draw.polygon(surf, (255, 255, 255), render_points)
