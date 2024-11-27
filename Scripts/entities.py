import Scripts.InverseKinematics as ik
from typing import assert_type
import random
import math
import Scripts.CONFIG as CFG
import pygame
from pygame import FRect, Rect, Surface
from Scripts.tilemap import TileMap, EntityMap
import collections
from Scripts.utils_math import dist, normalize, vector2d_from_angle, rotate_vector2d, sign_vector2d, vector2d_mult, vector2d_sub, clamp
import json
from Scripts.utils import load_image, load_images, draw_rect_alpha
import time
import dataclasses
import abc
from Scripts.timer import Timer


class FrozenDict(collections.abc.Mapping):  # https://stackoverflow.com/questions/2703599/what-would-a-frozen-dict-be
    """Don't forget the docstrings!!"""

    def __init__(self, *args, **kwargs):
        self._d = dict(*args, **kwargs)
        self._hash = None

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __hash__(self):
        # It would have been simpler and maybe more obvious to
        # use hash(tuple(sorted(self._d.iteritems()))) from this discussion
        # so far, but this solution is O(n). I don't know what kind of
        # n we are going to run into, but sometimes it's hard to resist the
        # urge to optimize when it will gain improved algorithmic performance.
        if self._hash is None:
            hash_ = 0
            for pair in self.items():
                if isinstance(pair[1], list):
                    hash_ ^= hash((pair[0], tuple(pair[1])))
                else:
                    hash_ ^= hash(pair)
            self._hash = hash_
        return self._hash


class BaseEntityABC(abc.ABC):
    counter = 0
    __slots__ = ("_r", "base_type", "type", "z_offset", "_vel", "render_fliped", "outlined", "_id", "angle", "dead", "damageable")

    def __init__(self, r: FRect, type: str, vel: tuple[float, float, float] = (0.0, 0.0, 0.0), angle=0.0):
        self._r = r
        self.type = type
        self.base_type = self.type
        self.z_offset = 0.0
        self._vel = vel
        self.angle = angle  # in radians
        self.render_fliped = False

        self.outlined = False
        self.dead = False
        self.damageable = False

        self._id = BaseEntityABC.counter
        BaseEntityABC.counter += 1

    # region Properties
    # rect stuff (pos, size)
    @property
    def frect(self) -> FRect: return self._r
    @property
    def area(self) -> float: return self._r.w * self._r.h

    @property
    def pos(self) -> tuple[float, float]: return self._r.topleft
    @pos.setter
    def pos(self, val: tuple[float, float]) -> None: self._r.topleft = val

    @property
    def x(self) -> float: return self._r.x
    @x.setter
    def x(self, val: float) -> None: self._r.x = val
    @property
    def y(self) -> float: return self._r.y
    @y.setter
    def y(self, val: float) -> None: self._r.y = val
    @property
    def centerx(self) -> float: return self._r.centerx
    @centerx.setter
    def centerx(self, val: float) -> None: self._r.centerx = val
    @property
    def centery(self) -> float: return self._r.centery
    @centery.setter
    def centery(self, val: float) -> None: self._r.centery = val

    @property
    def tile_pos(self) -> tuple[int, int]: return (int(self._r.x // CFG.TILESIZE), int(self._r.y // CFG.TILESIZE))

    @property
    def center(self) -> tuple[float, float]: return self._r.center
    @center.setter
    def center(self, val: tuple[float, float]) -> None: self._r.center = val

    @property
    def size(self) -> tuple[float, float]: return self._r.size
    @property
    def size_int(self) -> tuple[int, int]: return int(self._r.w), int(self._r.h)

    @property
    def angle_degrees(self) -> float: return math.degrees(self.angle)

    @property
    def direction(self) -> tuple[float, float]: return vector2d_from_angle(-self.angle)

    # velocity stuff
    @property
    def velocity(self) -> tuple[float, float, float]: return self._vel
    @velocity.setter
    def velocity(self, val: tuple[float, float, float]) -> None: self._vel = val
    @property
    def normalized_velocity(self) -> tuple[float, float, float]: return normalize(self._vel)
    # endregion

    @abc.abstractmethod
    def update(self, dt: float) -> ...: return

    def __hash__(self): return self._id
    def __repr__(self): return f"BaseEntity{self._id}  {self.__class__.__name__}  {self.type}"


class Animation:
    def __init__(self, config_file_path: str, loaded_already=None) -> None:
        super().__init__()
        self.states: dict[str, list[Surface]] = {}
        self.states_looping: dict[str, bool] = {}
        self.states_frame_times: dict[str, bool] = {}
        self.states_offset: dict[str, tuple] = {}
        self.default: str = ""  # default state from config

        self.__state: str = None
        self.index: float = 0.0
        self._last_img: Surface = None
        self.offset = [0, 0]

        self.flip = False
        self.last_index_update: float = .0

        self.__parse_config(config_file_path, loaded_already)

        # print(self.states)
        # print(self.states_frame_times)
        # print(self.states_looping)

    def __parse_config(self, path: str, loaded_already) -> None:
        with open(path, "r") as f:
            data = json.load(f)

            colorkey = data["colorkey"]
            default_path = data["file_path"]
            same_dir = data["samedir"]
            for state, state_data in data["animations"].items():
                if loaded_already:
                    self.states[state] = loaded_already
                elif same_dir:
                    self.states[state] = load_images(default_path, colorkey=colorkey)
                else:
                    self.states[state] = load_images(f"{default_path}/{state}", colorkey=colorkey)
                self.states_looping[state] = state_data["loop"]
                self.states_frame_times[state] = state_data["frames"]
                self.states_offset[state] = state_data["offset"]

            self.state = data["default"]
            self.offset = data["offset"]

            self.default = data["default"]

    @property
    def state(self) -> str: return self.__state

    @state.setter
    def state(self, state: str) -> None:
        if state != self.__state:
            self.__state = state
            self.index = 0
            self.last_index_update = time.time()

    @property
    def over(self) -> bool:
        if self.states_looping[self.__state]:  # looping
            return False
        return self.index == len(self.states[self.__state]) - 1

    def add_state(self, state: str, surfs: list[Surface], looping: bool, frame_times: list[float]) -> None:
        if state not in self.states:
            self.states[state] = surfs
            self.states_looping[state] = looping
            self.states_frame_times[state] = frame_times

    def img(self) -> Surface:
        return pygame.transform.flip(self.states[self.__state][int(self.index)], self.flip, False)

    def new_img(self) -> bool:
        return self.__last_img != self.img()

    def get_offset(self) -> tuple:
        state_offset = self.states_offset[self.state]
        return (self.offset[0] + state_offset[0], self.offset[1] + state_offset[1])


def find_first_occurance_of_pixel_with_color_X(surf: Surface, color: tuple) -> tuple[int, int]:
    color = pygame.Color(*color)
    for x in range(surf.width):
        for y in range(surf.height):
            if surf.get_at((x, y)) == color:
                return (x, y)
    return None


class Player(BaseEntityABC):
    head_pos_cache_per_type = {}

    def __init__(self, r: FRect, vel=(0, 0, 0), type="player", hitbox_size=(9, 25)):
        super().__init__(r, type, vel)
        self.hitbox_size = hitbox_size

        # self.held_item: ItemABC = None
        self.z_offset = 30
        self.x_offset = 5

        upperarm_len = 3
        lowerarm_len = 5
        self.right_arm = ik.IKArmFABRIK(self.shoulder_right_pos, lowerarm_len, upperarm_len)
        self.left_arm = ik.IKArmFABRIK(self.shoulder_left_pos, lowerarm_len, upperarm_len)
        self.animation_frame = 0
        self.animation_frame_timer = 0.
        self.animation_type = "idle"
        self.head_angle = 0.0  # radians

        if self.base_type not in Player.head_pos_cache_per_type:
            Player.head_pos_cache_per_type[self.base_type] = self._parse_headdata("assets/entities/enemies/zombie/head_offsets/config.json")  # müsste eigentlich players headoffsets sein, aber dann gehen die Zombies headoffsets nicht mehr. Da gamejam = egal
        self.head_position_cache = Player.head_pos_cache_per_type[self.base_type]
        # print(self.head_position_cache)

        self.damageable = True
        self.max_health = 200
        self.health = self.max_health

        self.inventory = []
        self.inventory_idx = 0

    def _parse_headdata(self, path: str) -> None:
        offsets = {}
        with open(path, "r") as f:
            data = json.load(f)
            colorkey = data["colorkey"]
            default_path = data["file_path"]
            id = data["id"]

            for animation_state, state_data in data["animations"].items():
                state_offsets = [(0, 0)] * state_data["len"]
                imgs = load_images(f"{default_path}/{animation_state}", colorkey=colorkey)
                for i, img in enumerate(imgs):
                    state_offsets[i] = find_first_occurance_of_pixel_with_color_X(img, state_data["pixel_color"])
                offsets[animation_state] = state_offsets

        return offsets

    @property
    def hitbox(self) -> FRect:
        return FRect(
            self._r.x,
            self._r.y - self.hitbox_size[1] + self._r.h,
            self._r.w + self._r.w - self.hitbox_size[0],
            self.hitbox_size[1]
        )

    @property
    def head_pos(self) -> tuple:  # relative to self._r.topleft
        p = self.head_position_cache[self.animation_type][int(self.animation_frame)]
        head_offset = (-2, 0) if self.render_fliped else (0, 0)
        return (self.x+p[0]-head_offset[0], self.y+p[1]-self.z_offset-head_offset[1])

    @property
    def head_angle_degrees(self) -> float: return math.degrees(self.head_angle)

    @property
    def shoulder_left_pos(self) -> tuple:
        if self.render_fliped:
            return (self.x+1, self.y-self.z_offset+22)
        return (self.x+8, self.y-self.z_offset+22)

    @property
    def shoulder_right_pos(self) -> tuple:
        if self.render_fliped:
            return (self.x+8, self.y-self.z_offset+22)
        return (self.x+1, self.y-self.z_offset+22)

    @property
    def gun_docking_pos(self) -> tuple:
        if self.render_fliped:
            return (self.x+5, self.y-self.z_offset+23)
        return (self.x+4, self.y-self.z_offset+23)

    def set_type(self, type: str) -> None:
        self.type = type

    def reset_animation_timer(self) -> None:
        self.animation_frame = 0
        self.animation_frame_timer = 0.0

    def update_animation_state(self, dt: float):
        self.animation_frame_timer += dt
        if self.animation_frame_timer >= CFG.am.get_animation_frame_data(self.base_type, self.animation_type)[self.animation_frame]:
            self.animation_frame += 1
            if CFG.am.get_animation_looping(self.base_type, self.animation_type):
                self.animation_frame %= CFG.am.get_animation_number_of_frames(self.base_type, self.animation_type)
                # self.animation_frame = (self.animation_frame + 1) % CFG.am.get_animation_number_of_frames(self.base_type, self.animation_type)
            else:
                self.animation_frame = min(self.animation_frame, CFG.am.get_animation_number_of_frames(self.base_type, self.animation_type) - 1)
            self.animation_frame_timer = 0.0
        self.type = f"ANIMATIONS/{self.base_type}/{self.animation_type}/{int(self.animation_frame)}"

    def set_animation_state(self, type: str) -> None:
        if self.animation_type != type:
            self.animation_type = type
            self.reset_animation_timer()

    def update_arms(self) -> None:
        self.right_arm.set_base_pos(self.shoulder_right_pos)
        self.left_arm.set_base_pos(self.shoulder_left_pos)

        if self.held_item:
            self.right_arm.solve(self.held_item.right_hand_pos, focus_direction=sign_vector2d(self.held_item.direction))
            self.left_arm.solve(self.held_item.left_hand_pos, focus_direction=sign_vector2d(self.held_item.direction))

    def update_angle(self, x_movement) -> None:
        self.render_fliped = x_movement < 0
        self.head_angle = math.pi if x_movement < 0 else 0.0
        if self.held_item:
            self.render_fliped = math.pi/2 < self.held_item.angle < 1.5*math.pi
            self.head_angle = self.held_item.angle

    @property
    def held_item(self) -> "ItemABC":
        if len(self.inventory):
            return self.inventory[self.inventory_idx]
        return None

    def update_inventory(self, cycle_direction: int):
        if len(self.inventory):
            self.inventory_idx = (self.inventory_idx + cycle_direction) % (len(self.inventory))
            # print(cycle_direction, self.inventory_idx)

    def update(self, dt: float, movement: list, inventory_cycle_direction: int, boost=False) -> None:

        self.update_inventory(inventory_cycle_direction)

        if boost:
            self._vel = (movement[0] * 4, movement[1] * 4, 0)
        else:
            self._vel = (movement[0], movement[1], 0)

        self.update_arms()

        # self.x += movement[0] * dt
        # self.y += movement[1] * dt

        # animation
        if self._vel[0] or self._vel[1]:
            # walking
            self.set_animation_state("run")
        else:
            # idle
            self.set_animation_state("idle")
        self.update_animation_state(dt)
        self.update_angle(self._vel[0])

    def pickup(self, item: "ItemABC") -> None:
        # if self.held_item:
        #     return
        # self.held_item = item
        # print(1)
        self.inventory.append(item)

    def drop(self) -> "ItemABC":
        # item = self.held_item
        # self.held_item = None
        item = self.inventory[self.inventory_idx]
        self.inventory.remove(item)
        item.drop()

        self.inventory_idx = clamp(0, self.inventory_idx-1, len(self.inventory))

        return item

    def has_equiped(self, item: "ItemABC") -> bool:
        return item == self.inventory[self.inventory_idx]

    def draw_arm_behind(self, surface: Surface, offset: tuple) -> None:
        if not self.held_item:
            return
        if self.render_fliped:
            self.left_arm.render(surface, c1=(0, 0, 255), c2=(0, 0, 125), offset=offset, lowerarm_width=2, upperarm_width=3)
        else:
            self.left_arm.render(surface, c1=(255, 0, 0), c2=(125, 0, 0), offset=offset, lowerarm_width=2, upperarm_width=3)

    def draw_arm_infront(self, surface: Surface, offset: tuple) -> None:
        if not self.held_item:
            return
        if self.render_fliped:
            self.right_arm.render(surface, c1=(255, 0, 0), c2=(125, 0, 0), offset=offset, lowerarm_width=2, upperarm_width=3)
        else:
            self.right_arm.render(surface, c1=(0, 0, 255), c2=(0, 0, 125), offset=offset, lowerarm_width=2, upperarm_width=3)

    def draw_arms(self, surface: Surface, offset: tuple) -> None:
        if not self.held_item:
            return
        self.right_arm.render(surface, c1=(255, 0, 0), c2=(125, 0, 0), offset=offset, lowerarm_width=2, upperarm_width=3)
        self.left_arm.render(surface, c1=(0, 0, 255), c2=(0, 0, 125), offset=offset, lowerarm_width=2, upperarm_width=3)

    def render_hud(self, surface: Surface) -> None:
        bl = (0, surface.height)
        healthbar_size = (95, 10)
        padding = (5, 5)
        portrait_size = (30, 20)

        fblits = []

        # region healthbar
        r = [bl[0]+padding[0], bl[1]-padding[1]-healthbar_size[1], healthbar_size[0], healthbar_size[1]]
        pygame.draw.rect(surface, (25, 100, 0), r)
        r = [bl[0]+padding[0], bl[1]-padding[1]-healthbar_size[1], healthbar_size[0] * (self.health / self.max_health), healthbar_size[1]]
        pygame.draw.rect(surface, (80, 210, 10), r)
        r = [bl[0]+padding[0], bl[1]-padding[1]-healthbar_size[1], healthbar_size[0], healthbar_size[1]]
        pygame.draw.rect(surface, (255, 255, 255), r, 1)
        # endregion

        # region player portrait
        r = [bl[0]+padding[0], bl[1]-padding[1]-portrait_size[1] - healthbar_size[1]-padding[1], *portrait_size]
        draw_rect_alpha(surface, (255, 255, 255), r, 125)
        pygame.draw.rect(surface, (255, 255, 255), r, 1)
        s = CFG.am.get_outlined("player_portrait", outline_color=(255, 255, 255))
        fblits.append((
            s,
            s.get_rect(center=((bl[0]+padding[0]+portrait_size[0]//2, bl[1]-padding[1]-portrait_size[1]//2 - healthbar_size[1]-padding[1])))
        ))
        surface.fblits(fblits)
        # endregion

        padding = (5, 5)
        icon_image_size = (30, 20)
        inv_pos = (surface.width - icon_image_size[0]*2, surface.height)
        equipped_item = None
        inv = []
        for item in self.inventory:
            if self.has_equiped(item):
                equipped_item = item
            else:
                inv.append(item)

        l = len(inv)
        for i, item in enumerate(inv):
            r = [
                inv_pos[0] - (padding[0] + icon_image_size[0]) * (l-i),
                inv_pos[1]-padding[1]-icon_image_size[1],
                *icon_image_size
            ]
            draw_rect_alpha(surface, (180, 180, 180), r, 125)
            pygame.draw.rect(surface, (180, 180, 180), r, 1)
            s = CFG.am.get_outlined(item.type, outline_color=(180, 180, 180))
            fblits.append((
                s,
                s.get_rect(center=((
                    inv_pos[0] - (padding[0] + icon_image_size[0]) * (l-i) + icon_image_size[0]//2,
                    inv_pos[1]-padding[1]-icon_image_size[1] + icon_image_size[1]//2
                )))
            ))
        surface.fblits(fblits)

        if equipped_item:
            equipped_item.render_hud(surface)

    def render_body(self, surface: Surface, scroll=(0, 0), draw_rect=False) -> None:
        p = (self.x - scroll[0] - self.x_offset, self.y - self.z_offset - scroll[1])
        # print(self)
        surface.blit(CFG.am.get(self.type, angle=self.angle_degrees, flip_x=self.render_fliped), p)
        if draw_rect:
            r = self.frect
            pygame.draw.rect(surface, (0, 255, 255), [r.x - scroll[0], r.y - scroll[1], *r.size], 1)
            r = self.hitbox
            pygame.draw.rect(surface, (0, 255, 0), [r.x - scroll[0], r.y - scroll[1], *r.size], 1)

    def render_head(self, surface: Surface, scroll=(0, 0)) -> None:
        head_surf = CFG.am.get(f"{self.base_type}_head", angle=self.head_angle_degrees)
        p = head_surf.get_frect(center=self.head_pos)
        surface.blit(head_surf, (p[0] - scroll[0] - self.x_offset, p[1] - scroll[1]))

    def render(self, surface: Surface, scroll=(0, 0), draw_rect=False) -> None:
        self.render_body(surface, scroll, draw_rect)
        self.draw_arm_behind(surface, scroll)
        if self.render_fliped:
            self.render_head(surface, scroll)
        self.draw_item(surface, scroll)
        self.draw_arm_infront(surface, scroll)
        if not self.render_fliped:
            self.render_head(surface, scroll)

    def draw_item(self, surface: Surface, scroll=(0, 0)) -> None:
        if not self.held_item:
            return
        ent = self.held_item
        surf = CFG.am.get(ent.type, angle=ent.angle_degrees)
        center_pos = (
            ent.centerx - ent.direction[0] * ent.stats.holding_offset - ent.direction[0] * ent.recoil,
            ent.centery - ent.direction[1] * ent.stats.holding_offset - ent.direction[1] * ent.recoil
        )
        p = surf.get_frect(center=center_pos).topleft
        p = (p[0]-scroll[0], p[1] - scroll[1] - ent.z_offset)
        surface.blit(surf, p)

    def damage(self, amount: int, direction: tuple) -> None:
        self.health -= amount
        self.dead = self.health <= 0

    def heal(self, amount: int) -> None:
        self.health += amount


class ZombieBase(Player):
    player_last_seen_map: dict["ZombieBase", tuple] = {}

    def __init__(self, r, vel=(0, 0, 0), type="zombie"):
        super().__init__(r, vel, type=type)
        self.damageable = True

    def rule1(self, target_pos: tuple) -> tuple:
        return (
            (target_pos[0] - self.pos[0]) * 0.2,
            (target_pos[1] - self.pos[1]) * 0.2
        )

    def rule2(self, entity_map: EntityMap) -> tuple:
        c = (0, 0)
        for zombie_pos, zombie_data in entity_map.query(self.pos):
            if dist(self.pos, zombie_pos) < 25:
                c = (c[0] + (self.pos[0] - zombie_pos[0]), c[1] + (self.pos[1] - zombie_pos[1]))
        c = (
            c[0] * 0.6,
            c[1] * 0.6,
        )
        return c

    def kill(self):
        self.health = 0
        self.dead = True
        self.set_animation_state("death")

    def damage(self, amount, direction):
        if self.dead:
            return
        super().damage(amount, direction)

        if self.health <= 0:
            self.set_animation_state("death")
            self.dead = True
            self.render_fliped = not self.render_fliped  # weil die death animation falsch rum ist.


class Zombie(ZombieBase):
    def __init__(self, r: FRect, vel=(0, 0, 0), type="zombie"):
        super().__init__(r, vel, type=type)
        self.z_offset = 30

        self._reload_input = False
        self._shoot_input = False
        self.speed = 25
        self.see_dist = 125
        self.time_between_reload = 0.0
        self.no_target_sight_time = 0.0

        ZombieBase.player_last_seen_map[self] = None

        self.target_point = (0, 0)

        if self.base_type not in Player.head_pos_cache_per_type:
            Player.head_pos_cache_per_type[self.base_type] = self._parse_headdata("assets/entities/enemies/zombie/head_offsets/config.json")
        self.head_position_cache = Player.head_pos_cache_per_type[self.base_type]

        self.update_animation_state(0.0)

    def update(self, dt, player_pos: tuple, entity_map: EntityMap):
        if self.animation_type == "spawn":
            self.update_animation_state(dt)
            if self.animation_frame == CFG.am.get_animation_number_of_frames(self.base_type, self.animation_type) - 1:
                self.set_animation_state("idle")
            return {"type": self.base_type, "pickedup_items": [], "dropped_items": []}

        if self.dead:
            self.update_animation_state(dt)
            dropped_items = []
            if self.held_item:
                dropped_items = [self.drop()]
            return {"type": self.base_type, "pickedup_items": [], "dropped_items": dropped_items}

        target_pos = (0, 0)
        can_shoot = False
        do_reload = False

        if self.held_item and self.held_item.ammo != self.held_item.stats.ammo:
            self.time_between_reload += dt

        if self.held_item and self.time_between_reload > self.held_item.ammo * 2 and self.held_item.ammo != self.held_item.stats.ammo:
            do_reload = True

        if dist(player_pos, self.pos) > self.see_dist:
            # get average of last seen poses.
            last_seen_pos = self.pos
            c = 1
            for zombie_pos, zombie_data in entity_map.query(self.pos):
                if not isinstance(zombie_data["ent"], ZombieBase):
                    continue
                if (_pos := ZombieBase.player_last_seen_map[zombie_data["ent"]]):
                    last_seen_pos = (
                        last_seen_pos[0] + _pos[0],
                        last_seen_pos[1] + _pos[1]
                    )
                    c += 1
            last_seen_pos = (
                last_seen_pos[0] // c,
                last_seen_pos[1] // c
            )
            target_pos = last_seen_pos
            self.no_target_sight_time += dt
        else:
            target_pos = player_pos
            ZombieBase.player_last_seen_map[self] = target_pos
            can_shoot = bool(self.held_item) and self.held_item.ammo
            self.no_target_sight_time = 0.0
        v = (0, 0)
        if do_reload or not can_shoot:
            v1 = self.rule1(target_pos)
            v2 = self.rule2(entity_map)

            v = (v1[0] + v2[0], v1[1] + v2[1])
            v = vector2d_mult(normalize(v), self.speed)
            self.velocity = (*v, 0)
            # self.pos = (self.pos[0] + v[0], self.pos[1] + v[1])
        self.target_point = vector2d_mult(target_pos, 1)

        # animation
        if v[0] or v[1]:
            # walking
            self.set_animation_state("run")
        else:
            # idle
            self.set_animation_state("idle")
        self.update_animation_state(dt)

        self.update_arms()
        self.update_angle(v[0])

        self._shoot_input = can_shoot
        self._reload_input = do_reload

        # query for items on the ground:
        pickedup_items = []
        if not self.held_item:
            for ent_pos, ent_data in entity_map.query(self.pos, size=self.size_int):
                if not isinstance(ent_data["ent"], Gun):
                    continue
                if ent_data["ent"].frect.colliderect(self.frect):
                    ent_data["ent"].pickup(self)
                    pickedup_items.append(ent_data["ent"])
                    break

        return {"type": self.base_type, "pickedup_items": pickedup_items, "dropped_items": []}

    def render(self, surface: Surface, scroll=(0, 0), draw_rect=False) -> None:
        super().render(surface, scroll, draw_rect)

        if self.dead:
            return

        # region healthbar
        pos = (self.frect.centerx, self.y - self.z_offset+6)
        healthbar_size = 0
        healthbar_size = (15, 4)
        r = [pos[0] - scroll[0]-healthbar_size[0]//2, pos[1] - scroll[1], healthbar_size[0], healthbar_size[1]]
        pygame.draw.rect(surface, (25, 100, 0), r)
        r = [pos[0] - scroll[0]-healthbar_size[0]//2, pos[1] - scroll[1], healthbar_size[0] * (self.health / self.max_health), healthbar_size[1]]
        pygame.draw.rect(surface, (80, 210, 10), r)
        r = [pos[0] - scroll[0]-healthbar_size[0]//2, pos[1] - scroll[1], healthbar_size[0], healthbar_size[1]]
        pygame.draw.rect(surface, (255, 255, 255), r, 1)
        # endregion

        if draw_rect:
            pygame.draw.circle(surface, (255, 0, 255), vector2d_sub(self.target_point, scroll), 3)
            pygame.draw.line(surface, (255, 0, 255), vector2d_sub(self.pos, scroll), vector2d_sub(self.target_point, scroll), 1)

    @property
    def reload_input(self) -> bool: return self._reload_input
    @property
    def shoot_input(self) -> bool: return self._shoot_input


class SucideZombie(ZombieBase):
    def __init__(self, r: FRect, vel=(0, 0, 0)):
        super().__init__(r, vel, type="zombie_suicide")

        self.speed = 15
        self.boost = 2.5
        self.time_dead = 0.0
        self.explode_range = 30.0
        self.did_explode = False

        self.target_point = (0, 0)
        ZombieBase.player_last_seen_map[self] = (0, 0)  # gegen crash

        if self.base_type not in Player.head_pos_cache_per_type:
            Player.head_pos_cache_per_type[self.base_type] = self._parse_headdata("assets/entities/enemies/zombie_suicide/head_offsets/config.json")
        self.head_position_cache = Player.head_pos_cache_per_type[self.base_type]

        self.update_animation_state(0.0)

    def update(self, dt, player_pos: tuple, entity_map: EntityMap):
        explode = False

        if self.animation_type == "spawn":
            self.update_animation_state(dt)
            if self.animation_frame == CFG.am.get_animation_number_of_frames(self.base_type, self.animation_type) - 1:
                self.set_animation_state("idle")
            return {"type": self.base_type, "explode": explode, "radius": self.explode_range}

        if self.dead:
            self.time_dead += dt
            self.update_animation_state(dt)

            if not self.did_explode and self.time_dead > 2.1:  # wann die Weste verzögert nacht dem Tod explodiert
                explode = True
                self.did_explode = True

            return {"type": self.base_type, "explode": explode, "radius": self.explode_range}

        target_pos = (0, 0)

        target_pos = player_pos
        ZombieBase.player_last_seen_map[self] = target_pos

        explode = dist(target_pos, self.pos) < self.explode_range
        if explode and not self.did_explode:
            self.did_explode = True

        v = (0, 0)
        v1 = self.rule1(target_pos)
        v2 = self.rule2(entity_map)

        v = (v1[0] + v2[0], v1[1] + v2[1])
        v = vector2d_mult(normalize(v), self.speed)
        self.velocity = (*v, 0)
        # self.pos = (self.pos[0] + v[0], self.pos[1] + v[1])
        self.target_point = vector2d_mult(target_pos, 1)

        # animation
        if v[0] or v[1]:  # walking
            self.set_animation_state("run")
        else:            # idle
            self.set_animation_state("idle")
        self.update_animation_state(dt)

        return {"type": self.base_type, "explode": explode, "radius": self.explode_range}

    def render(self, surface, scroll=(0, 0), draw_rect=False):
        super().render(surface, scroll, draw_rect)

        if self.dead:
            return

        # region healthbar
        pos = (self.frect.centerx, self.y - self.z_offset+6)
        healthbar_size = 0
        healthbar_size = (15, 4)
        r = [pos[0] - scroll[0]-healthbar_size[0]//2, pos[1] - scroll[1], healthbar_size[0], healthbar_size[1]]
        pygame.draw.rect(surface, (25, 100, 0), r)
        r = [pos[0] - scroll[0]-healthbar_size[0]//2, pos[1] - scroll[1], healthbar_size[0] * (self.health / self.max_health), healthbar_size[1]]
        pygame.draw.rect(surface, (80, 210, 10), r)
        r = [pos[0] - scroll[0]-healthbar_size[0]//2, pos[1] - scroll[1], healthbar_size[0], healthbar_size[1]]
        pygame.draw.rect(surface, (255, 255, 255), r, 1)
        # endregion

        if draw_rect:
            pygame.draw.circle(surface, (255, 0, 255), vector2d_sub(self.target_point, scroll), 3)
            pygame.draw.line(surface, (255, 0, 255), vector2d_sub(self.pos, scroll), vector2d_sub(self.target_point, scroll), 1)


@dataclasses.dataclass(kw_only=True)
class ItemStats:
    name: str
    type: str
    angle: float = dataclasses.field(default=0.0)
    owner: BaseEntityABC = dataclasses.field(default=None)
    ignore_physics: bool = dataclasses.field(default=False)


@dataclasses.dataclass(kw_only=True)
class GunStats(ItemStats):
    firerate: float  # wie viele ms zwischen den Schüssen
    damage: float
    ammo: int
    reloadtime: float
    gun_length: float  # in px
    shoulder_pivot_point_offset: tuple[int, int]  # von (0,0) auf dem img # um diesen Punkt wird das Bild rotiert!
    bullets: int = 1
    bullet_speed: float = 150
    spread: float = 0.06
    holding_offset: float = 0.0
    recoil: float = 3.0
    recoil_resetrate: float = 12.0
    screen_shake_duration: float = 0.2


GUN_STATS = {
    "items/guns/rifle": GunStats(
        name="Rifle",
        type="items/guns/rifle",
        angle=.0,
        firerate=0.15,
        damage=15,
        ammo=31,
        reloadtime=1.7,
        gun_length=19,
        shoulder_pivot_point_offset=(0, 2)
    ),
    "items/guns/pistol": GunStats(
        name="Pistol",
        type="items/guns/pistol",
        firerate=0.4,
        damage=33,
        ammo=6,
        reloadtime=1.4,
        gun_length=10,
        shoulder_pivot_point_offset=(0, 0),
        holding_offset=-3,
    ),
    "items/guns/pistol_silenced": GunStats(
        name="Silenced Pistol",
        type="items/guns/pistol_silenced",
        firerate=0.3,
        damage=21,
        ammo=8,
        reloadtime=1.6,
        gun_length=17,
        shoulder_pivot_point_offset=(0, 0),
        holding_offset=-3,
    ),
    "items/guns/shotgun": GunStats(
        name="Shotgun",
        type="items/guns/shotgun",
        firerate=0.25,  # 0.04,
        damage=9,
        ammo=8,
        reloadtime=2,
        bullets=11,
        gun_length=19,
        shoulder_pivot_point_offset=(1, 2),
        recoil=4.0,
        recoil_resetrate=9,
        screen_shake_duration=0.3
    ),
    "items/guns/rocketlauncher": GunStats(
        name="Rocketlauncher",
        type="items/guns/rocketlauncher",
        firerate=0.001,
        damage=100,
        ammo=1,
        reloadtime=3,
        bullet_speed=250,
        gun_length=23,
        shoulder_pivot_point_offset=(3, 4),
        holding_offset=7,
        recoil_resetrate=6,
    ),
    "items/guns/kriss_vector": GunStats(
        name="Vector",
        type="items/guns/kriss_vector",
        firerate=0.1,
        damage=5,
        ammo=33,
        reloadtime=1.6,
        gun_length=17,
        shoulder_pivot_point_offset=(1, 3)
    ),
    "items/guns/m60": GunStats(
        name="M60",
        type="items/guns/m60",
        firerate=0.23,
        damage=20,
        ammo=45,
        bullets=2,
        reloadtime=3.5,
        gun_length=23,
        shoulder_pivot_point_offset=(3, 4)
    ),
    "items/guns/ring": GunStats(
        name="Ring",
        type="items/guns/ring",
        firerate=0.1,
        damage=13,
        ammo=100,
        bullets=36,
        reloadtime=6.0,
        gun_length=10.0,
        shoulder_pivot_point_offset=(5, 5)
    )
}


class ItemABC(BaseEntityABC):
    def __init__(self, r, stats: ItemStats):
        self.stats = stats
        super().__init__(r, self.stats.type)
        self.owner: Player = None

        # region handle-points & barreltip point offsets
        self.handle_pos_offset = find_first_occurance_of_pixel_with_color_X(CFG.am.get(f"{self.type}_lt"), (255, 0, 0))
        self.handle_pos2_offset = find_first_occurance_of_pixel_with_color_X(CFG.am.get(f"{self.type}_lt"), (0, 255, 0))
        self.barrel_pos_offset = find_first_occurance_of_pixel_with_color_X(CFG.am.get(f"{self.type}_lt"), (0, 0, 255))
        self.bulletcasing_pos_offset = find_first_occurance_of_pixel_with_color_X(CFG.am.get(f"{self.type}_lt"), (255, 255, 0))
        # offset to "centerline" of rect
        self.handle_pos_offset = (self.handle_pos_offset[0], self.handle_pos_offset[1] - self._r.h/2)
        self.handle_pos2_offset = (self.handle_pos2_offset[0], self.handle_pos2_offset[1] - self._r.h/2)
        self.barrel_pos_offset = (self.barrel_pos_offset[0], self.barrel_pos_offset[1] - self._r.h/2)
        self.bulletcasing_pos_offset = (self.bulletcasing_pos_offset[0], self.bulletcasing_pos_offset[1] - self._r.h/2)

        # für self.render_flipped
        self.handle_pos_offset_flipped = find_first_occurance_of_pixel_with_color_X(pygame.transform.flip(CFG.am.get(f"{self.type}_lt"), False, True), (255, 0, 0))
        self.handle_pos2_offset_flipped = find_first_occurance_of_pixel_with_color_X(pygame.transform.flip(CFG.am.get(f"{self.type}_lt"), False, True), (0, 255, 0))
        self.barrel_pos_offset_flipped = find_first_occurance_of_pixel_with_color_X(pygame.transform.flip(CFG.am.get(f"{self.type}_lt"), False, True), (0, 0, 255))
        self.bulletcasing_pos_offset_flipped = find_first_occurance_of_pixel_with_color_X(pygame.transform.flip(CFG.am.get(f"{self.type}_lt"), False, True), (255, 255, 0))
        # offset to "centerline" of rect
        self.handle_pos_offset_flipped = (self.handle_pos_offset_flipped[0], self.handle_pos_offset_flipped[1] - self._r.h/2)
        self.handle_pos2_offset_flipped = (self.handle_pos2_offset_flipped[0], self.handle_pos2_offset_flipped[1] - self._r.h/2)
        self.barrel_pos_offset_flipped = (self.barrel_pos_offset_flipped[0], self.barrel_pos_offset_flipped[1] - self._r.h/2)
        self.bulletcasing_pos_offset_flipped = (self.bulletcasing_pos_offset_flipped[0], self.bulletcasing_pos_offset_flipped[1] - self._r.h/2)

        self.recoil = 0.0

    def _gp(self, vec: tuple[float, float]) -> tuple[float, float]:  # gp = get point
        dir_vec = self.direction
        return (
            self.owner.gun_docking_pos[0] + rotate_vector2d(vec, -self.angle)[0] - (dir_vec[0] * self.stats.holding_offset) - (dir_vec[0] * self.recoil),
            self.owner.gun_docking_pos[1] + rotate_vector2d(vec, -self.angle)[1] - (dir_vec[1] * self.stats.holding_offset) - (dir_vec[1] * self.recoil)
        )

    @property
    def right_hand_pos(self) -> tuple[float, float]:
        if self.owner.render_fliped:
            return self._gp(self.handle_pos_offset_flipped)
            # return (
            #     self.owner.gun_docking_pos[0] + rotate_vector2d(self.handle_pos_offset_flipped, -self.angle)[0] - dir_vec[0] * self.stats.holding_offset,
            #     self.owner.gun_docking_pos[1] + rotate_vector2d(self.handle_pos_offset_flipped, -self.angle)[1] - dir_vec[1] * self.stats.holding_offset,
            # )
        return self._gp(self.handle_pos_offset)
        # return (
        #     self.owner.gun_docking_pos[0] + rotate_vector2d(self.handle_pos_offset, -self.angle)[0] - dir_vec[0] * self.stats.holding_offset,
        #     self.owner.gun_docking_pos[1] + rotate_vector2d(self.handle_pos_offset, -self.angle)[1] - dir_vec[1] * self.stats.holding_offset,
        # )

    @property
    def left_hand_pos(self) -> tuple[float, float]:
        if self.owner.render_fliped:
            return self._gp(self.handle_pos2_offset_flipped)
            # return (
            #     self.owner.gun_docking_pos[0] + rotate_vector2d(self.handle_pos2_offset_flipped, -self.angle)[0] - dir_vec[0] * self.stats.holding_offset,
            #     self.owner.gun_docking_pos[1] + rotate_vector2d(self.handle_pos2_offset_flipped, -self.angle)[1] - dir_vec[1] * self.stats.holding_offset
            # )
        return self._gp(self.handle_pos2_offset)
        # return (
        #     self.owner.gun_docking_pos[0] + rotate_vector2d(self.handle_pos2_offset, -self.angle)[0] - dir_vec[0] * self.stats.holding_offset,
        #     self.owner.gun_docking_pos[1] + rotate_vector2d(self.handle_pos2_offset, -self.angle)[1] - dir_vec[1] * self.stats.holding_offset
        # )

    @property
    def bulletcasing_pos(self) -> tuple[float, float]:
        if self.owner.render_fliped:
            return self._gp(self.bulletcasing_pos_offset_flipped)
        return self._gp(self.bulletcasing_pos_offset)

    def get_bullet_spawn_pos(self) -> tuple:
        if self.owner.render_fliped:
            return self._gp(self.barrel_pos_offset_flipped)
            # return (
            #     self.owner.gun_docking_pos[0] + rotate_vector2d(self.barrel_pos_offset_flipped, -self.angle)[0] - dir_vec[0] * self.stats.holding_offset,
            #     self.owner.gun_docking_pos[1] + rotate_vector2d(self.barrel_pos_offset_flipped, -self.angle)[1] - dir_vec[1] * self.stats.holding_offset
            # )
        return self._gp(self.barrel_pos_offset)
        # return (
        #     self.owner.gun_docking_pos[0] + rotate_vector2d(self.barrel_pos_offset, -self.angle)[0] - dir_vec[0] * self.stats.holding_offset,
        #     self.owner.gun_docking_pos[1] + rotate_vector2d(self.barrel_pos_offset, -self.angle)[1] - dir_vec[1] * self.stats.holding_offset
        # )

    def pickup(self, owner: Player):
        self.owner = owner
        self.owner.pickup(self)
        self.ignore_physics = True

    def drop(self):
        self.owner = None
        self.ignore_physics = False

    @abc.abstractmethod
    def use(self, **kwargs): return NotImplemented
    @abc.abstractmethod
    def update(self, dt: float, **kwargs): return NotImplemented

    @property
    def is_held(self) -> bool:
        return bool(self.owner)

    def update_pos_angle(self, scroll: tuple, lookpoint: tuple) -> None:
        return NotImplemented


class Bullet(BaseEntityABC):
    def __init__(self, r, angle, dmg, owner, speed=700):
        vel = vector2d_from_angle(angle)  # speed einbauen
        vel = (vel[0] * speed, vel[1] * speed, 0)
        super().__init__(r, "items/guns/projectile", vel, angle=-angle)
        self.dmg = dmg
        self.owner = owner
        self.alive = 0.0
        self.timer = 1.5

    def update(self, dt: float):
        self.alive += dt
        self.x += self._vel[0] * dt
        self.y += self._vel[1] * dt

        return self.alive < self.timer


class BulletCasing(BaseEntityABC):
    color = (218, 165, 32)

    def __init__(self, r, length: int, max_fall: float, angle=0, speed=10):
        a = angle
        if -(math.pi * 3/2) < angle < -(math.pi * 4/3):
            angle = -(math.pi+math.pi/3.2)
        elif 0.98 < angle < 1.6:
            angle = 0.97
        # print(a, angle)
        vel = vector2d_from_angle(angle)
        vel = (vel[0] * speed, vel[1] * speed, random.random()*50-25)
        super().__init__(r, "bullet_casing", vel, angle)
        self.length = length
        self.speed = speed
        self.max_fall = max_fall + random.random() * 5
        self.org_y = self.y
        self.alive = 0.0

    @property
    def p1(self) -> tuple[float, float]:
        dir = self.direction()
        return (
            self.x - dir[0] * self.length/2,
            self.y - self.direction()[1] * self.length/2
        )

    @property
    def p2(self) -> tuple[float, float]:
        dir = self.direction()
        return (
            self.x + dir[0] * self.length/2,
            self.y + dir[1] * self.length/2
        )

    def direction(self) -> tuple[float, float]:
        return rotate_vector2d(self.normalized_velocity, self.angle)

    def update(self, dt: float, **kwargs) -> bool:
        self.x += self._vel[0] * dt
        self.y += self._vel[1] * dt
        self.alive += dt
        self.angle += self.velocity[2] * dt

        self._vel = (self._vel[0] * 0.98, self._vel[1] + 10*CFG.GRAVITY * dt, self._vel[2])
        if abs(self.y - self.org_y) > self.max_fall:
            self._vel = (self._vel[0] * 0.98, -50, self._vel[2])  # nicht so ganz happy. eigentlich sollte, die Hülse aufm Boden Springen.

        return self.alive < 1.2  # dann noch am leben.


class Gun(ItemABC):
    def __init__(self, r, gun_type: str):
        stats = GUN_STATS[gun_type]
        super().__init__(r, stats)

        # print(self.type, self.barrel_pos_offset, self.barrel_pos_offset_flipped)
        self.shoottimer = Timer(self.stats.firerate, start_on_end=True)
        # endregion
        self.reloadtimer = Timer(self.stats.reloadtime, start_on_end=True)
        self.ammo = self.stats.ammo

    def pickup(self, owner):
        super().pickup(owner)

    def drop(self):
        super().drop()

    def use(self):
        if self.shoottimer.ended and self.ammo > 0 and self.reloadtimer.ended:
            ret = []
            # print(self.angle, math.radians(self.angle), -math.pi, math.pi)
            if self.stats.bullets % 2 != 0:  # ungerade anzahl an bullets.
                x = (self.stats.bullets-1)//2
                for i in range(-x, x+1, 1):
                    new_angle = -self.angle + i*self.stats.spread
                    ret.append({"angle": new_angle,
                                "speed": self.stats.bullet_speed,
                                "dmg": self.stats.damage
                                })
            else:  # gerade anzahl an bullets
                x = self.stats.bullets//2
                for i in range(-x, x):
                    new_angle = -self.angle + i*self.stats.spread
                    ret.append({"angle": new_angle,
                                "speed": self.stats.bullet_speed,
                                "dmg": self.stats.damage
                                })
            self.shoottimer.start()
            self.ammo -= 1
            self.recoil = self.stats.recoil
            return ret
        else:
            return []

    def update(self, dt: float, **kwargs):
        d = {"use": []}
        if not self.owner:
            return d
        elif not self.owner.has_equiped(self):
            return d

        scroll = kwargs["scroll"]
        reload_input = kwargs["reload_input"]
        shoot_input = kwargs["shoot_input"]
        lookpoint = kwargs["mPos"]

        if isinstance(self.owner, ZombieBase):
            scroll = kwargs["scroll"]
            reload_input = self.owner.reload_input
            shoot_input = self.owner.shoot_input
            lookpoint = vector2d_sub(self.owner.target_point, scroll)  # weil targetpoint in worldspace ist. Der Punkt muss erst zu screenspace umgewandelt werden.

        if reload_input or (self.ammo == 0 and shoot_input and not self.reloadtimer.just_ended):
            self.reloadtimer.start()
        elif shoot_input:
            d["use"] = self.use()

        self.update_pos_angle(scroll, lookpoint)

        if self.reloadtimer.just_ended:
            self.ammo = self.stats.ammo

            self.recoil = max(self.recoil - dt * self.stats.recoil_resetrate, 0.0)
        return d

    def render_hud(self, surface: Surface) -> None:
        br = surface.size
        icon_image_size = (30, 20)
        padding = (5, 5)
        reload_bar_item_size = (7, 4)
        padding_reloadbar = (0, 1)
        reloadbar_rect_padding = (1, 1)

        r = [br[0]-padding[0]-reload_bar_item_size[0]-padding[0]-icon_image_size[0], br[1]-padding[1]-icon_image_size[1], *icon_image_size]
        draw_rect_alpha(surface, (255, 255, 255), r, 125)
        pygame.draw.rect(surface, (255, 255, 255), r, 1)

        fblits = []
        proj_surf = CFG.am.get("items/guns/projectile")

        if not self.reloadtimer.ended and self.reloadtimer.remaining():
            counter = int((self.reloadtimer.duration - self.reloadtimer.remaining()) / self.reloadtimer.duration * self.stats.ammo)
        else:
            counter = self.ammo

        r = [
            br[0]-padding[0]-reload_bar_item_size[0] - reloadbar_rect_padding[0],
            max(0, br[1]-padding[1]-(reload_bar_item_size[1]+padding_reloadbar[1])*self.stats.ammo-reloadbar_rect_padding[1]),
            reload_bar_item_size[0]+reloadbar_rect_padding[0]*2,
            min(surface.height-padding[1], (reload_bar_item_size[1]+padding_reloadbar[1])*self.stats.ammo + reloadbar_rect_padding[1])
        ]  # min, max sind dazu da aus rects wie [x, y, -10000, 10104], [x, y, 0, 104] zu machen. (weniger Lag!!)
        draw_rect_alpha(surface, (255, 255, 255), r, 125)
        pygame.draw.rect(surface, (255, 255, 255), r, 1)

        for i in range(min(counter, int(br[1]/(reload_bar_item_size[1]+padding_reloadbar[1])))):
            r = [
                br[0]-padding[0]-reload_bar_item_size[0],
                br[1]-padding[1]-reload_bar_item_size[1] - (reload_bar_item_size[1]+padding_reloadbar[1])*i - reloadbar_rect_padding[1],
                *reload_bar_item_size
            ]
            # pygame.draw.rect(surface, (125, 125, 125), r)
            # pygame.draw.rect(surface, (255, 255, 255), r, 1)
            fblits.append((
                proj_surf,
                r
            ))
        s = CFG.am.get_outlined(self.type, outline_color=(255, 255, 255))
        fblits.append((
            s,
            s.get_rect(center=(br[0]-padding[0]-reload_bar_item_size[0]-padding[0]-icon_image_size[0]/2, br[1]-padding[1]-icon_image_size[1]/2))
        ))
        surface.fblits(fblits)

    def update_pos_angle(self, scroll: tuple, lookpoint: tuple) -> None:
        mouse_offset = (self.y - scroll[1] - lookpoint[1], self.x - scroll[0] - lookpoint[0])
        self.angle = math.atan2(mouse_offset[1], mouse_offset[0]) + math.pi/2
        # print(self.angle, mouse_offset)

        dir_vec = self.direction
        self.center = (
            self.owner.gun_docking_pos[0] + dir_vec[0] * self.stats.gun_length / 2,
            self.owner.gun_docking_pos[1] + dir_vec[1] * self.stats.gun_length / 2
        )


@dataclasses.dataclass(kw_only=True)
class HealStats(ItemStats):
    heal_amount: int
    uses: int
    cooldown: float = 15.0
    holding_offset: int = 0


class Consumable(ItemABC):
    def __init__(self, r, stats):
        super().__init__(r, stats)

    def use(self, **kwargs):
        return
        return super().use(**kwargs)

    def update(self, dt, **kwargs):
        return
        return super().update(dt, **kwargs)

    def render_hud(self, surface: pygame.Surface):
        return

    def update_pos_angle(self, scroll: tuple, lookpoint: tuple) -> None:
        mouse_offset = (self.y - scroll[1] - lookpoint[1], self.x - scroll[0] - lookpoint[0])
        self.angle = math.atan2(mouse_offset[1], mouse_offset[0]) + math.pi/2
        # print(self.angle, mouse_offset)

        dir_vec = self.direction
        self.center = (
            self.owner.gun_docking_pos[0] + dir_vec[0],
            self.owner.gun_docking_pos[1] + dir_vec[1]
        )


class Medkit(Consumable):
    def __init__(self, r, stats):
        super().__init__(r, stats)

        self.uses = self.stats.uses

    def use(self, **kwargs):
        self.uses -= 1
        return self.stats.heal_amount

    def update(self,  dt, **kwargs):
        d = {"use": []}
        if not self.owner:
            return d
        elif not self.owner.has_equiped(self):
            return d
        elif self.uses <= 0:
            return d

        scroll = kwargs["scroll"]
        shoot_input = kwargs["shoot_input"]
        lookpoint = kwargs["mPos"]

        if isinstance(self.owner, ZombieBase):
            scroll = kwargs["scroll"]
            lookpoint = vector2d_sub(self.owner.target_point, scroll)  # weil targetpoint in worldspace ist. Der Punkt muss erst zu screenspace umgewandelt werden.

        elif shoot_input:
            d["use"] = self.use()

        self.update_pos_angle(scroll, lookpoint)

        return d

    def render_hud(self, surface):
        br = surface.size
        icon_image_size = (30, 20)
        padding = (5, 5)
        reload_bar_item_size = (7, 4)
        padding_reloadbar = (0, 1)
        reloadbar_rect_padding = (1, 1)

        r = [br[0]-padding[0]-reload_bar_item_size[0]-padding[0]-icon_image_size[0], br[1]-padding[1]-icon_image_size[1], *icon_image_size]
        draw_rect_alpha(surface, (255, 255, 255), r, 125)
        pygame.draw.rect(surface, (255, 255, 255), r, 1)

        fblits = []
        proj_surf = CFG.am.get("items/guns/projectile")

        counter = self.uses

        r = [
            br[0]-padding[0]-reload_bar_item_size[0] - reloadbar_rect_padding[0],
            max(0, br[1]-padding[1]-(reload_bar_item_size[1]+padding_reloadbar[1])*self.stats.uses-reloadbar_rect_padding[1]),
            reload_bar_item_size[0]+reloadbar_rect_padding[0]*2,
            min(surface.height-padding[1], (reload_bar_item_size[1]+padding_reloadbar[1])*self.stats.uses + reloadbar_rect_padding[1])
        ]  # min, max sind dazu da aus rects wie [x, y, -10000, 10104], [x, y, 0, 104] zu machen. (weniger Lag!!)
        draw_rect_alpha(surface, (255, 255, 255), r, 125)
        pygame.draw.rect(surface, (255, 255, 255), r, 1)

        for i in range(min(counter, int(br[1]/(reload_bar_item_size[1]+padding_reloadbar[1])))):
            r = [
                br[0]-padding[0]-reload_bar_item_size[0],
                br[1]-padding[1]-reload_bar_item_size[1] - (reload_bar_item_size[1]+padding_reloadbar[1])*i - reloadbar_rect_padding[1],
                *reload_bar_item_size
            ]
            # pygame.draw.rect(surface, (125, 125, 125), r)
            # pygame.draw.rect(surface, (255, 255, 255), r, 1)
            fblits.append((
                proj_surf,
                r
            ))

        s = CFG.am.get_outlined(self.type, outline_color=(255, 255, 255))
        fblits.append((
            s,
            s.get_rect(center=(br[0]-padding[0]-reload_bar_item_size[0]-padding[0]-icon_image_size[0]/2, br[1]-padding[1]-icon_image_size[1]/2))
        ))
        surface.fblits(fblits)


@dataclasses.dataclass(kw_only=True)
class AmmoStats(ItemStats):
    amount: int
    holding_offset: int = 0


class LootDrop(BaseEntityABC):
    def __init__(self, r, vel=(0, 0, 0), angle=0):
        super().__init__(r, "creates", vel, angle)

        self.contained_items = []
        self.make_items(random.randint(1, 4))

        self.max_health = 150
        self.health = self.max_health
        self.num_damage_stages = 3

        self.hitbox_size = (16, 16)

        # print(self.contained_items)

        self.planks_to_spawn: set[tuple] = set()

    @property
    def hitbox(self) -> FRect:
        return FRect(
            self._r.x,
            self._r.y - self.hitbox_size[1] + self._r.h,
            self._r.w + self._r.w - self.hitbox_size[0],
            self.hitbox_size[1]
        )

    def make_items(self, n: int) -> None:
        for _ in range(n):
            item = None
            p = random.randint(0, 100)
            if p <= 50:  # gun
                p2 = random.randint(0, 100)
                type = "gun_to_be_chosen"
                if p2 <= 5:  # ring
                    type = "ring"
                elif p2 <= 15:  # m60 or vector
                    type = random.choice(["m60", "kriss_vector"])
                elif p2 <= 25:  # rocketlauncher
                    type = "rocketlauncher"
                elif p2 <= 35:  # shotgun
                    type = "shotgun"
                else:  # rest (pistol, rifle)
                    type = random.choice(["pistol", "pistol_silenced", "rifle"])
                size = CFG.am.get(f"items/guns/{type}").size
                item = Gun(FRect(self.x, self.y, *size), f"items/guns/{type}")

            elif p <= 100:  # heal
                if random.randint(0, 100) <= 50:
                    continue
                size = CFG.am.get(f"items/medkit").size
                item = Medkit(FRect(self.x, self.y, *size), HealStats(name="Medkit", type="items/medkit", heal_amount=50, uses=1))

            self.contained_items.append(item)

    def damage(self, amount: int, direction: tuple) -> None:
        self.health -= amount

        # spawn plank and damage itself
        self.planks_to_spawn.add((
            self.frect.center,
            (
                (random.random() * math.pi * 16 - 8*math.pi) * (random.random() * 2),
                (random.random() * math.pi * 16 - 8*math.pi) * (random.random() * 2)
                # direction[0] * 14,
                # direction[1] * 14,
            ),
            random.randint(0, 2)  # welcher typ von plank
        ))

    def update(self, dt):
        super().update(dt)

        idx = 0
        if self.health <= 100:
            idx = 1
        if self.health <= 50:
            idx = 2

        self.type = f"{self.base_type}/{idx}"

        if self.health <= 0:
            return {"alive": False, "items": self.contained_items}

        ret = {"alive": True, "planks": self.planks_to_spawn.copy()}
        self.planks_to_spawn.clear()

        return ret


class Decal(BaseEntityABC):
    def __init__(self, r, type, vel=(0, 0, 0), angle=0):
        super().__init__(r, type, vel, angle)

        self.alive = 0.0

    def update(self, dt):
        self.alive += dt


def handle_collision(dt: float, human_entities: list[BaseEntityABC], tilemap: TileMap) -> None:
    def collision_test(rect: FRect, tiles: list[dict]) -> list[FRect]:
        return [tilemap.make_rect_from_tile(tile) for tile in tiles if rect.colliderect(tilemap.make_rect_from_tile(tile))]
    for entity in human_entities:
        if entity.dead:
            continue
        tiles = tilemap.get_around(entity.pos, size=entity.size_int, layer=0, types={"sides", "stone"})
        # print(tiles)

        entity.x += entity.velocity[0] * dt
        tile_hit_list = collision_test(entity.frect, tiles)
        for t in tile_hit_list:
            if entity.velocity[0] > 0:
                entity.frect.right = t.left
                # entity._collision_types['right'] = True
            elif entity.velocity[0] < 0:
                entity.frect.left = t.right
                # self._collision_types['left'] = True

        entity.y += entity.velocity[1] * dt
        tile_hit_list = collision_test(entity.frect, tiles)
        for t in tile_hit_list:
            if entity.velocity[1] > 0:
                entity.frect.bottom = t.top
                # entity._collision_types['bottom'] = True
            elif entity.velocity[1] < 0:
                entity.frect.top = t.bottom
                # entity._collision_types['top'] = True
            # entity.pos[1] = entity.rect.y


def handle_item_outlines(player: Player, items: list[ItemABC]) -> list[ItemABC]:
    outlined_items = []

    for ent in items:
        ent.outlined = False
        if dist(ent.center, player.center) <= 30:
            outlined_items.append(ent)
            ent.outlined = True

    return outlined_items


def handle_pickup(player: Player, items: list[ItemABC], pickup_input: bool, ignore_items: set[ItemABC] = set()) -> ItemABC | None:
    item: ItemABC = None
    item_d = math.inf

    if not pickup_input:
        return None
    # if player.held_item:
    #     return None

    possible_to_pickup: list[tuple[ItemABC, float]] = []

    for ent in items:
        if ent in ignore_items:
            continue
        if ent.type.split("/")[0] != "items":
            continue
        _d = dist(ent.center, player.center)
        if _d <= 30:
            possible_to_pickup.append((ent, _d))

    for p_item, p_item_d in possible_to_pickup:
        if p_item_d < item_d:
            item = p_item
            item_d = p_item_d

    if item:
        item.pickup(player)
    return item


def handle_drop(player: Player, entity_map: EntityMap, drop_input: bool) -> None | ItemABC:
    if not drop_input:
        return None
    if not player.held_item:
        return None

    item = player.held_item
    player.drop()

    entity_map.add_entity(item.pos, {"ent": item})

    return item


def update_held_items(items: list[ItemABC], dt: float, **kwargs) -> None:
    d: dict[int, dict] = dict()
    for held_item in items:
        d[held_item] = held_item.update(dt, **kwargs)
    return d


def handle_bullet_collision(entities: list[BaseEntityABC], projectilemap: EntityMap, tilemap: TileMap):
    # TODO
    to_remove = set()
    poses = set()
    kills = set()
    projs_calcd = set()
    for entity in entities:
        killed = False
        if entity.dead:
            continue
        for proj_pos, projectile_data in projectilemap.query(entity.pos, size=entity.hitbox_size):
            if projectile_data["ent"].owner == entity:
                continue
            if projectile_data["ent"].frect.colliderect(entity.hitbox):
                entity.damage(projectile_data["ent"].dmg, vector2d_from_angle(-projectile_data["ent"].angle))
                if entity.dead:
                    killed = True
                to_remove.add(projectile_data["ent"])
                poses.add((
                    projectile_data["ent"].pos,
                    projectile_data["ent"].angle,
                    entity.base_type != "creates",  # ob mit entities collided, False = mit der Wand
                ))
            # check for coll with tilemap
            if tilemap.get_tile(projectile_data["ent"].tile_pos, layer=1):
                to_remove.add(projectile_data["ent"])
                poses.add((
                    projectile_data["ent"].pos,
                    projectile_data["ent"].angle,
                    False,  # ob mit entities collided, False = mit der Wand
                ))
                projs_calcd.add(proj_pos)
        kills.add(killed)

    for proj_pos, projectile_data in projectilemap.get_all():
        if proj_pos in projs_calcd:
            continue
        if tilemap.get_tile(projectile_data["ent"].tile_pos, layer=1):
            to_remove.add(projectile_data["ent"])
            poses.add((
                projectile_data["ent"].pos,
                projectile_data["ent"].angle,
                False,  # ob mit entities collided, False = mit der Wand
            ))
    return zip(to_remove, poses, kills)

# TODO:
# - Items
#     - updating -> shooting, reloading, animation, ...
#     - rendering
#     - welche?
#           - Granate
#           - Medkit
#           - Cluster Bombe
#
# - Physics
#     - Player vs Enemies
#     - All entities vs all entities (items vs player, ...)
# - decay
#     - so zeugs zum rum schieben wie in die Bücher in "enter the gungeon"
#     - Holzsplitter von einer zersörten Kiste.
# - Partikel
#     - physics und non-physics partikel
#     - updaten
#     - rendern
