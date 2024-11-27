import json
import pygame
from pygame import Surface, FRect, Rect, Surface
import Scripts.CONFIG as CFG
from Scripts.tilemap import TileMap, EntityMap
from Scripts.utils import load_image, load_images, draw_rect_alpha
from Scripts.utils_math import vector2d_from_angle, vector2d_add, vector2d_mult, sign, dist, vector2d_sub
from Scripts.particles import Spark
from Scripts.timer import TimerManager, Timer
from Scripts.entities import (
    ItemABC, Gun, ItemStats, Medkit,
    Player, Zombie, SucideZombie, LootDrop, Decal,
    Bullet, BulletCasing,
    handle_collision, handle_pickup, handle_drop, update_held_items, handle_item_outlines, handle_bullet_collision
)
import math
import random
import time
import Scripts.Input as Input
from Scripts.particles import AnimationParticle, ParticleGroup


PROJECTILE_DECAY_TIME = 5  # in sekunden.

font = pygame.font.SysFont("arial", 14)


class Game:
    __last_tick = time.perf_counter()
    __fps = 0  # how many frames have I drawn, per second
    __fps_timer = .0
    __frames_drawn = 0

    def __init__(self) -> None:
        # random.seed(0)
        # , flags=pygame.DOUBLEBUF | pygame.OPENGL)
        self.master_screen = pygame.display.set_mode(CFG.ORG_RES)
        self.screen = Surface(CFG.RES)
        self.clock = pygame.time.Clock()
        assets = {
            "blocker": [load_image("assets/tiles/blocker.png")],
            "sides": [load_image("assets/tiles/grass/side.png"), load_image("assets/tiles/stone/side.png"), load_image("assets/tiles/dirt/side.png")],
            "grass": [load_image(f"assets/tiles/grass/top{i}.png") for i in range(9)],
            # "dirt": [load_image("assets/tiles/dirt/top.png")],
            "dirt": CFG.parse_tileset("assets/tiles/dirt/tilemap.png", as_array=True),
            "stone": CFG.parse_tileset("assets/tiles/stone/tilemap.png", as_array=True),
            "shadow": CFG.parse_tileset("assets/tiles/shadow/tilemap.png", as_array=True, colorkey=(255, 0, 0), alpha=125),
            "spawners": load_images("assets/tiles/spawners", imgnames_are_ints=True),
            "blades_cover": [load_image("assets/tiles/blades_cover.png")],
            "grass_blades": load_images("assets/tiles/grass_blades"),
            "player_head": load_image("assets/entities/player/head.png"),
            "player_portrait": load_image("assets/entities/player/player_portrait.png"),
            "zombie_head": load_image("assets/entities/enemies/zombie/head.png"),
            "zombie_portrait": load_image("assets/entities/enemies/zombie/zombie_portrait.png"),
            "zombie_suicide_head": load_image("assets/entities/enemies/zombie_suicide/head.png"),
            "zombie_suicide_portrait": load_image("assets/entities/enemies/zombie_suicide/zombie_portrait.png"),
            "creates": load_images("assets/entities/create"),
            "deco": load_images("assets/tiles/deco"),
            "items": {
                "apple": load_image("assets/items/apple.png"),
                "apple_lt": load_image("assets/items/apple_lt.png"),
                "grenade": load_image("assets/items/grenade.png"),
                "grenade_lt": load_image("assets/items/grenade_lt.png"),
                "cluster_grenade": load_image("assets/items/cluster_grenade.png"),
                "cluster_grenade_lt": load_image("assets/items/cluster_grenade_lt.png"),
                "medkit": load_image("assets/items/medkit.png"),
                "medkit_lt": load_image("assets/items/medkit_lt.png"),
                "ammo": load_image("assets/items/ammo.png"),
                "ammo_lt": load_image("assets/items/ammo_lt.png"),
                "planks": load_images("assets/items/planks", imgnames_are_ints=True),
                "guns": {
                    "ring": load_image("assets/items/guns/ring.png"),
                    "rifle": load_image("assets/items/guns/rifle.png"),
                    "pistol": load_image("assets/items/guns/pistol.png"),
                    "pistol_silenced": load_image("assets/items/guns/pistol_silenced.png"),
                    "shotgun": load_image("assets/items/guns/shotgun.png"),
                    "rocketlauncher": load_image("assets/items/guns/rocketlauncher.png"),
                    "projectile": load_image("assets/items/guns/projectile.png"),
                    "kriss_vector": load_image("assets/items/guns/kriss_vector.png"),
                    "m60": load_image("assets/items/guns/m60.png"),
                    # gun lts
                    "ring_lt": load_image("assets/items/guns/ring_lt.png"),
                    "rifle_lt": load_image("assets/items/guns/rifle_lt.png"),
                    "pistol_lt": load_image("assets/items/guns/pistol_lt.png"),
                    "pistol_silenced_lt": load_image("assets/items/guns/pistol_silenced_lt.png"),
                    "shotgun_lt": load_image("assets/items/guns/shotgun_lt.png"),
                    "rocketlauncher_lt": load_image("assets/items/guns/rocketlauncher_lt.png"),
                    "kriss_vector_lt": load_image("assets/items/guns/kriss_vector_lt.png"),
                    "m60_lt": load_image("assets/items/guns/m60_lt.png"),
                }
            },
            "ANIMATIONS": {},
        }
        CFG.am.assets = assets

        CFG.am.load_animation("assets/entities/player/config.json")
        CFG.am.load_animation("assets/entities/enemies/zombie/config.json")
        CFG.am.load_animation("assets/entities/enemies/zombie_suicide/config.json")
        CFG.am.load_animation("assets/particles/config-blood.json")
        CFG.am.load_animation("assets/particles/config-heal.json")

        # print(CFG.am.assets)

        # region AssetManager tests
        # print(len(CFG.am.get("spawners")))
        # print(CFG.am.get("blocker/0"))
        # print(CFG.am.get("items/apple"))
        # print(CFG.am.get("items/guns/rifle"))
        # print(CFG.am.get("grass_blades"))
        # print(CFG.am.get("grass_blades/0"))
        # print(CFG.am.get("grass_blades/1"))
        # print(CFG.am.get("grass_blades/3"))
        # endregion

        self.entitymap = EntityMap()
        self.projectilemap = EntityMap()

        # entities / lists for objects in the game
        # self.player: ecs.Entity = None  # type: ignore
        # self.enemies: list[ecs.Entity] = list()
        # self.items: list[ecs.Entity] = list()
        # self.projectiles: list[ecs.Entity] = list()
        self.sparks: set[Spark] = set()
        self.entities: dict[str, list] = {
            "player": [],
            "enemies": [],
            "items": [],
            "items_pickedup": [],
            "projectiles": [],
            "bullet_casings": [],
            "objects": [],
            "floating_texts": [],
            "decals": []
        }
        self.particles: dict[str, list] = {
            "circle": [],  # particle = [pos: list, vel: tuple, color: tuple, alive: float, alive_time: float, size: float]
            "sparks": list(),
        }
        self.animation_particle_group = ParticleGroup()

        # misc
        self.timer_manager = TimerManager()
        self.running = True

        # map
        self.zombie_spawn_poses = []
        self.tilemap = TileMap(self)
        self.parse_level()

        # print(self.zombie_spawn_poses)

    def parse_level(self):
        def get_spawner_pos(spawner: dict, ignore_int=False):
            if ignore_int:
                return spawner["pos"]
            return (int(spawner["pos"][0]), int(spawner["pos"][1]))
        self.tilemap.load("map.json")
        self.tilemap.make_walls()
        self.tilemap.make_random_variations()
        self.tilemap.init_grass()
        self.tilemap.make_shadow()

        _ids = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
        _extract_list = [("spawners", _id) for _id in _ids]
        for spawner in self.tilemap.extract(_extract_list, keep=False):
            # print(spawner)
            if spawner["variant"] == 0:  # player
                p = Player(FRect(*get_spawner_pos(spawner), 9, 7))
                self.entities["player"].append(p)
            elif spawner["variant"] in {1, 15}:  # enemy
                r = FRect(*get_spawner_pos(spawner), 9, 7)
                if spawner["variant"] == 1:
                    enemy = Zombie(r)
                    _size = CFG.am.get("items/guns/pistol").size
                    item = Gun(FRect(enemy.x, enemy.y, *_size), "items/guns/pistol")
                    item.pickup(enemy)
                    self.entities["items_pickedup"].append(item)
                else:
                    enemy = SucideZombie(r)
                self.entities["enemies"].append(enemy)
            elif spawner["variant"] in {6}:  # items
                lt = {
                    6: ("apple", (5, 6))
                }
                item = UsableItem(
                    FRect(*get_spawner_pos(spawner), *lt[spawner['variant']][1]),
                    ItemStats(name=lt[spawner['variant']][0],
                              type=f"items/{lt[spawner['variant']][0]}")
                )
                self.entities["items"].append(item)
            elif spawner["variant"] in {2, 3, 4, 5, 10, 11, 12, 13}:  # items (guns)
                lt = {
                    2: "rifle",
                    3: "pistol",
                    4: "shotgun",
                    5: "rocketlauncher",
                    10: "pistol_silenced",
                    11: "kriss_vector",
                    12: "m60",
                    13: "ring",
                }
                size = CFG.am.get(f"items/guns/{lt[spawner["variant"]]}").size
                gun = Gun(
                    FRect(*get_spawner_pos(spawner), *size),
                    f"items/guns/{lt[spawner['variant']]}"
                )
                self.entities["items"].append(gun)
            elif spawner["variant"] in {8}:  # kisten
                create = LootDrop(FRect(*get_spawner_pos(spawner), 16, 16))
                self.entities["objects"].append(create)
            elif spawner["variant"] in {14}:  # decal (gravestone)
                lt = {
                    18: "deco/0",
                }
                size = CFG.am.get(lt[spawner["variant"]]).size
                decal = Decal(FRect(*get_spawner_pos(spawner), *size), lt[spawner["variant"]])
                self.entities["decals"].append(decal)
            elif spawner["variant"] in {16}:
                self.zombie_spawn_poses.append(get_spawner_pos(spawner))

    def get_fps(self) -> float:
        return self.__fps

    def get_entities(self, ent_type: set[str] = {}, ignore: set[str] = {}) -> list:
        if ent_type:
            l = []
            for type_ in ent_type:
                l += self.entities[type_]
            return l
        else:
            l = []
            for type_, entities in self.entities.items():
                if type_ in ignore:
                    continue
                l += entities
            return l

    def make_explosion_particles(self, pos: tuple, n: int, colors: list[tuple]) -> list[list]:
        ret = []
        for i in range(n):
            vel = (
                (random.random() * math.pi * 16 - 8*math.pi) * (random.random() * 2),
                (random.random() * math.pi * 16 - 8*math.pi) * (random.random() * 2)
            )
            ret.append([
                # [pos: list, vel: tuple, color: tuple, alive: float, alive_time: float]
                list(pos),
                vel,
                random.choice(colors),
                0.0,
                random.randint(4, 12)
            ])
        return ret

    def render_all_ents(self, scroll, render_scroll) -> None:
        # alle entities (außer: Player, gehaltene Items)
        for ent in sorted(self.get_entities(ignore={"player", "items_pickedup", "bullet_casings", "enemies"}), key=lambda x: x.y):
            p = (ent.x - scroll[0], ent.frect.y - ent.z_offset - scroll[1])
            if ent.outlined:
                self.screen.blit(CFG.am.get_outlined(ent.type, angle=ent.angle_degrees, outline_color=(255, 255, 255)), (p[0]-1, p[1]-1))  # -1, -1, wegen der outline.
            else:
                self.screen.blit(CFG.am.get(ent.type, angle=ent.angle_degrees, flip_x=ent.render_fliped), p)
            # pygame.draw.rect(self.screen, (0, 255, 255), [ent.x - scroll[0], ent.y - scroll[1], *ent.frect.size], 1)

        # player und Zombies
        for ent in sorted(self.get_entities({"player", "enemies"}), key=lambda x: x.pos[1]-x.z_offset):
            ent.render(self.screen, scroll, draw_rect=False)

        for bullet_casing in self.get_entities({"bullet_casings"}):
            p1 = bullet_casing.p1
            p2 = bullet_casing.p2
            pygame.draw.line(
                self.screen,
                bullet_casing.color,
                (
                    p1[0] - scroll[0],
                    p1[1] - scroll[1],
                ),
                (
                    p2[0] - scroll[0],
                    p2[1] - scroll[1],
                ),
                width=2
            )
            # pygame.draw.circle(self.screen, (125, 125, 125), (bullet_casing.x-scroll[0], bullet_casing.y-scroll[1]), 1)
        for circle_particle in self.particles["circle"]:
            pygame.draw.circle(
                self.screen,
                circle_particle[2],
                (
                    circle_particle[0][0] - scroll[0],
                    circle_particle[0][1] - scroll[1],
                ),
                circle_particle[4] - circle_particle[3]
            )
        for spark in self.particles["sparks"]:
            spark.render(self.screen, scroll)

    def update_particles(self, dt: float) -> None:
        to_remove = []
        for circle_particle in self.particles["circle"]:
            # [pos: list, vel: tuple, color: tuple, alive: float, alive_time: float]
            circle_particle[0][0] += circle_particle[1][0] * dt
            circle_particle[0][1] += circle_particle[1][1] * dt
            circle_particle[3] += dt * 5
            if circle_particle[3] > circle_particle[4]:
                to_remove.append(circle_particle)

        for p in to_remove:
            self.particles["circle"].remove(p)

        self.particles["sparks"] = [p for p in self.particles["sparks"] if p.update(dt)]

    def run(self):
        master_time = 0
        speed = 75
        screen_shake = [0, 0]
        sh_amp = 7

        input_manager = Input.InputManager()
        input_manager["hmove"] = Input.Axis(
            (pygame.K_a,),
            (pygame.K_d,),
            Input.JoyAxis(0, 0)
        )
        input_manager["vmove"] = Input.Axis(
            (pygame.K_w,),
            (pygame.K_s,),
            Input.JoyAxis(1, 0)
        )
        input_manager["interact"] = Input.Button(pygame.K_e, Input.JoyButtonPress(pygame.CONTROLLER_BUTTON_X, 0), just_down=True)
        input_manager["drop"] = Input.Button(pygame.K_q, Input.JoyButtonPress(pygame.CONTROLLER_BUTTON_Y, 0), toggle=False, just_down=True)
        input_manager["boost"] = Input.Button(pygame.K_LCTRL)
        input_manager["reload"] = Input.Button(pygame.K_r, Input.JoyButtonPress(pygame.CONTROLLER_BUTTON_A, 0))
        input_manager["noclip"] = Input.Button(pygame.K_TAB)
        input_manager["fire"] = Input.Button(Input.MouseTrigger(1), Input.JoyAxisTrigger(5))
        input_manager["scroll"] = Input.ScrollAxis()
        joysticks = {}

        def zombie_spawn_func(x: float) -> float: return 0.035*math.pow(x, 2)

        n_zombies_spawned = 0
        zombie_size = (9, 7)
        n_zombies_killed = 0

        global_timer = Timer(64, True)

        lost = False
        won = False

        while self.running:
            self.screen.fill((0, 150, 200))
            dt = self.clock.tick(0) * 0.001
            dt = time.perf_counter() - self.__last_tick
            self.__last_tick = time.perf_counter()
            self.__fps_timer += dt
            master_time += dt * 100

            # region calc scroll
            # _mx, _my = CFG.get_mouse_pos(s=CFG.DOWNSCALE_FACTOR)
            _mx, _my = input_manager.get_pos(downscale_factor=CFG.DOWNSCALE_FACTOR)
            _look_factor = 3.5
            _look_factor_scaled = _look_factor * 2
            _mx, _my = _mx / _look_factor, _my / _look_factor
            scroll = (
                self.entities["player"][0].frect.x - CFG.RES[0] / 2 + (_mx - CFG.RES[0]/_look_factor_scaled),
                self.entities["player"][0].frect.y - CFG.RES[1] / 2 + (_my - CFG.RES[1]/_look_factor_scaled),
            )
            render_scroll = (int(scroll[0]), int(scroll[1]))
            # endregion
            viewport = pygame.Rect(render_scroll[0], render_scroll[1], CFG.RES[0], CFG.RES[1])  # * später hier WIDTH & HEIGHT als variablen passen, damit man das Fenster resizen kann
            self.timer_manager.update()

            # self.tilemap.shadows.clear()
            # self.tilemap.make_shadow(shadow_dir=(math.sin(master_time/100), math.cos(master_time/100)))

            def rot_function(x, y) -> int: return int(math.sin(master_time / 60 + x / 100 + y / 250 + x / (y * 2 + .001)) * 25)
            # def rot_function(x, y): return random.random() * 180 - 90
            all_entity_rects = [ent.frect for ent in self.get_entities()]
            self.tilemap.update_grass(all_entity_rects, 1.5, 7, dt)
            self.tilemap.rotate_grass(rot_function=rot_function)

            if lost or won:
                dt = 0.0
                global_timer.pause()

            if global_timer.ended:
                if n_zombies_killed >= 64:
                    won = True
                else:
                    lost = True

            # region events
            events = pygame.event.get()
            input_manager.update(events)

            reload = input_manager["reload"]
            boost = input_manager["boost"]
            movement = [input_manager["hmove"].value * speed, input_manager["vmove"].value * speed]
            pickup = input_manager["interact"].pressed()
            drop = input_manager["drop"].pressed()

            for event in events:
                # Handle hotplugging
                if event.type == pygame.JOYDEVICEADDED:
                    # This event will be generated when the program starts for every
                    # joystick, filling up the list without needing to create them manually.
                    joy = pygame.joystick.Joystick(event.device_index)
                    joysticks[joy.get_instance_id()] = joy
                    print(f"Joystick {joy.get_instance_id()} connencted")

                if event.type == pygame.JOYDEVICEREMOVED:
                    del joysticks[event.instance_id]
                    print(f"Joystick {event.instance_id} disconnected")
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_z:
                        self.entities["player"].pos = (200, 100)
            # endregion

            # region player update
            self.entities["player"][0].update(dt, movement, input_manager["scroll"].value, boost=False)
            if self.entities["player"][0].health <= 0:
                lost = True
            # endregion

            handle_collision(dt, self.get_entities(ent_type={"player", "enemies"}), self.tilemap)

            explosion_poses: set[tuple] = set()

            # region crate update
            for create in self.get_entities({"objects"}):
                create_ret = create.update(dt)
                if not create_ret["alive"]:
                    for dropped_item in create_ret["items"]:
                        self.entities["items"].append(dropped_item)
                        print(dropped_item.pos, dropped_item.type)
                    self.entities["objects"].remove(create)
                else:
                    for plank_data in create_ret["planks"]:
                        d = Decal(FRect(*plank_data[0], 6, 2), type="items/planks", vel=plank_data[1])
                        d.type = f"{d.base_type}/{plank_data[2]}"
                        self.entities["decals"].append(d)
            # endregion

            # region Bullets colls
            for bullet_to_remove, effect_data, killed in handle_bullet_collision(self.get_entities({"player", "enemies", "objects"}), self.projectilemap, self.tilemap):
                try:
                    self.entities["projectiles"].remove(bullet_to_remove)
                except ValueError:  # eigentlich nicht gut, das so zu machen, aber bei gamejam ist ok
                    pass
                for i in range(-2, 2+1):
                    new_angle = -effect_data[1] + i * 0.2
                    self.particles["sparks"].append(Spark(
                        effect_data[0], new_angle, 7, decay_speed=2
                    ))
                if effect_data[2]:  # bool ob mit ents collided -> blood partikel spawnen
                    for i in range(-2, 2+1):
                        new_angle = -effect_data[1] + i * 0.4 * random.random() * 3
                        p = AnimationParticle(effect_data[0], vector2d_mult(vector2d_from_angle(new_angle), 50), "blood", "blood")
                        self.animation_particle_group.add(p)
                if killed:  # bool ob einen kill gemacht
                    n_zombies_killed += 1
            # endregion

            # region items update
            if (pickedup_item := handle_pickup(self.entities["player"][0], self.get_entities({"items"}), pickup, ignore_items=self.get_entities({"items_pickedup", }))):
                print("pickedup:", pickedup_item)
                self.entities["items"].remove(pickedup_item)
                self.entities["items_pickedup"].append(pickedup_item)
                pickedup_item.outlined = False
            if (dropped_item := handle_drop(self.entities["player"][0], self.entitymap, drop)):
                print("dropped:", dropped_item)
                self.entities["items_pickedup"].remove(dropped_item)
                self.entities["items"].append(dropped_item)
            handle_item_outlines(self.entities["player"][0], self.get_entities({"items"}))
            item_update_ret = update_held_items(self.get_entities({"items_pickedup"}), dt, reload_input=reload, scroll=scroll, shoot_input=input_manager["fire"], mPos=input_manager.get_pos())
            for item, data in item_update_ret.items():
                if isinstance(item, Gun):
                    bullets_to_spawn = data["use"]
                    bullet_spawn_pos = item.get_bullet_spawn_pos()
                    for bullet in bullets_to_spawn:
                        surf = CFG.am.get("items/guns/projectile", angle=bullet["angle"])
                        radius = surf.get_frect(center=bullet_spawn_pos)
                        b = Bullet(pygame.FRect(radius.x, radius.y, 5, 5), bullet["angle"], bullet["dmg"], owner=item.owner, speed=bullet["speed"])
                        self.entities["projectiles"].append(b)
                        bc_maxfall = 15
                        bc = BulletCasing(pygame.FRect(*item.bulletcasing_pos, 1, 1), 3, bc_maxfall, bullet["angle"], speed=-200)
                        self.entities["bullet_casings"].append(bc)
                        self.particles["circle"].append([
                            # [pos: list, vel: tuple, color: tuple, alive: float, alive_time: float]
                            list(item.get_bullet_spawn_pos()),
                            (item.direction[0] * 15 + random.random() * 10, item.direction[1] * 10 - 30 - random.random() * 10),
                            random.choice([(70, 70, 70), (100, 100, 100), (150, 150, 150)]),
                            0.0,
                            2.0
                        ])
                        screen_shake[0] = item.stats.screen_shake_duration
                        screen_shake[1] = item.stats.screen_shake_duration

                        _a = bullet["angle"]
                        for i in range(-2, 2):
                            s = Spark(vector2d_add(bullet_spawn_pos, vector2d_mult(vector2d_from_angle(_a), 7.0)), _a + i * 0.3, 4.0, decay_speed=2.0)
                            self.particles["sparks"].append(s)
                elif isinstance(item, Medkit):
                    healamount = data["use"]
                    if healamount:
                        item.owner.heal(healamount)
                        for i in range(-2, 2+1):
                            new_angle = random.choice((-1, 1)) * random.random() * math.pi
                            p = AnimationParticle(effect_data[0], vector2d_mult(vector2d_from_angle(new_angle), 50), "heal", "heal")
                            self.animation_particle_group.add(p)

            # endregion

            # region gegner update
            for zombie in self.get_entities({"enemies"}):
                zombie_update_ret = zombie.update(dt, self.entities["player"][0].pos, self.entitymap)
                if zombie_update_ret["type"] == "zombie":
                    for item in zombie_update_ret["pickedup_items"]:
                        # print(item)
                        try:
                            self.entities["items"].remove(item)
                            self.entities["items_pickedup"].append(item)
                        except ValueError:
                            pass
                    for item in zombie_update_ret["dropped_items"]:
                        # print(item)
                        try:
                            self.entities["items_pickedup"].remove(item)
                            self.entities["items"].append(item)
                        except ValueError:
                            pass
                        # item.outlined = False
                elif zombie_update_ret["type"] == "zombie_suicide":
                    if zombie_update_ret["explode"]:
                        self.particles["circle"].extend(self.make_explosion_particles(zombie.center, int(zombie_update_ret["radius"]*3), [(80, 80, 80), (100, 100, 100), (175, 175, 175), (40, 40, 40)]))
                        zombie.kill()
                        sh_amp = 32
                        screen_shake[0] = 0.9
                        screen_shake[1] = 0.9
                        explosion_poses.add((zombie.center, zombie_update_ret["radius"]))
            # endregion

            # region decals update
            _decals_to_remove = []
            for decal in self.get_entities({"decals"}):
                if decal.base_type != "items/planks":
                    continue

                decal.update(dt)
                decal.x += decal.velocity[0] * dt
                decal.y += decal.velocity[1] * dt

                if decal.alive > 1.5:
                    _decals_to_remove.append(decal)
            for decal in _decals_to_remove:
                self.entities["decals"].remove(decal)
            # endregion

            self.update_entitymaps()

            # region explosion damage
            for ex_pos, radius in explosion_poses:
                tl = (ex_pos[0] - radius, ex_pos[1] - radius)
                r2 = radius * radius
                size = (int(r2), int(r2))

                # print(ex_pos, radius, tl, size)

                for entity_to_dmg_data in self.entitymap.query(tl, size=size):
                    entity_to_dmg = entity_to_dmg_data[1]["ent"]
                    if not entity_to_dmg.damageable:
                        continue
                    # print(entity_to_dmg)
                    if (dist_from_ex := dist(entity_to_dmg.frect.center, ex_pos)) < radius:
                        entity_to_dmg.damage((radius / (dist_from_ex+1)) * radius*3.5, vector2d_sub(ex_pos, entity_to_dmg.frect.center))
            # endregion

            if (n_to_spawn := int(zombie_spawn_func(master_time / 100)) - n_zombies_spawned):
                # print(n_to_spawn, Player.head_pos_cache_per_type)
                for n in range(n_to_spawn):
                    pos = random.choice(self.zombie_spawn_poses)
                    if random.randint(0, 100) <= 25:
                        zombie = SucideZombie(FRect(pos[0], pos[1], *zombie_size))
                    else:
                        zombie = Zombie(FRect(pos[0], pos[1], *zombie_size))
                    n_zombies_spawned += 1
                    zombie.set_animation_state("spawn")
                    self.entities["enemies"].append(zombie)

            self.update_particles(dt)
            self.animation_particle_group.update(dt)

            self.tilemap.render(self.screen, offset=render_scroll, render_offgrid=True, main_layer=None, render_layer=[0])

            self.render_all_ents(scroll, render_scroll)
            self.animation_particle_group.render(self.screen, offset=scroll)

            # ? debug_draw_entitymap
            # s = self.entitymap.entity_hashmap.cell_size
            # for cell_data in self.entitymap.get_cells():
            #     pygame.draw.rect(self.screen, (255, 255, 0), [cell_data[0][0] - scroll[0], cell_data[0][1]-scroll[1], s, s], 1)

            self.tilemap.render(self.screen, offset=render_scroll, render_offgrid=False, main_layer=None, render_layer=[1])

            # region rerender head for human entities
            for human_ent in self.get_entities({"player", "enemies"}):
                rerender_head = False
                p0 = (
                    int((human_ent.frect.x + sign(human_ent.velocity[0]) * CFG.TILESIZE) // CFG.TILESIZE),
                    int((human_ent.frect.y - CFG.TILESIZE) // CFG.TILESIZE)
                )
                p1 = (
                    int((human_ent.frect.x) // CFG.TILESIZE),
                    int((human_ent.frect.y - CFG.TILESIZE*2) // CFG.TILESIZE)
                )
                p11 = (
                    int((human_ent.frect.x + sign(human_ent.velocity[0]) * CFG.TILESIZE) // CFG.TILESIZE),
                    int((human_ent.frect.y - CFG.TILESIZE*2) // CFG.TILESIZE)
                )
                tile_above = self.tilemap.get_tile(p1, layer=1)
                if tile_above:
                    rerender_head = True
                tile_above2 = self.tilemap.get_tile(p11, layer=1)
                if tile_above2:
                    rerender_head = True
                tile_right = self.tilemap.get_tile(p0, layer=1)
                if tile_right and tile_right["type"] == "sides":
                    rerender_head = True
                # pygame.draw.rect(self.screen, (255, 255, 0), [p0[0]*CFG.TILESIZE - scroll[0], p0[1]*CFG.TILESIZE - scroll[1], CFG.TILESIZE, CFG.TILESIZE], 1)
                # pygame.draw.rect(self.screen, (255, 255, 0), [p1[0]*CFG.TILESIZE - scroll[0], p1[1]*CFG.TILESIZE - scroll[1], CFG.TILESIZE, CFG.TILESIZE], 1)

                if rerender_head:
                    human_ent.render_head(self.screen, scroll)
            # endregion

            self.tilemap.render_shadows(self.screen, offset=render_scroll)

            self.entities["player"][0].render_hud(self.screen)

            # for ent in self.get_entities({"items"}):
            #     r = 30
            #     pygame.draw.circle(self.screen, (0, 255, 255), (ent.center[0] - scroll[0], ent.center[1] - scroll[1]), r, 1)

            self.entities["projectiles"] = [b for b in self.get_entities({"projectiles"}) if b.update(dt)]
            self.entities["bullet_casings"] = [bc for bc in self.get_entities({"bullet_casings"}) if bc.update(dt)]

            screen_shake[0] = max(screen_shake[0] - dt, 0)
            screen_shake[1] = max(screen_shake[1] - dt, 0)
            sh_amp = max(sh_amp - dt * 25, 7)

            pygame.draw.circle(self.screen, (255, 255, 255), input_manager.get_pos(CFG.DOWNSCALE_FACTOR), 4)

            # self.screen.blit(font.render(f"FPS: {self.get_fps():.0f}, {self.clock.get_fps():.0f} pos: {self.entities["player"][0].tile_pos} {self.entities["player"][0].render_fliped} {self.entities["player"][0].type}", False, (255, 255, 255), (0, 0, 0)), (0, 0))
            self.screen.blit(font.render(f"FPS: {self.get_fps():.0f}\nTIME: {global_timer.remaining():.0f}\nZOMBIES: {n_zombies_spawned-n_zombies_killed}\nKILLS: {n_zombies_killed}", False, (255, 255, 255)), (5, 20))
            if lost:
                s = font.render("You Lost", False, (255, 255, 255))
                self.screen.blit(s, (self.screen.width//2 - s.width//2, self.screen.height//2 - s.height//2))
            elif won:
                s = font.render("You Won", False, (255, 255, 255))
                self.screen.blit(s, (self.screen.width//2 - s.width//2, self.screen.height//2 - s.height//2))

            r = [5, 5, self.screen.width - 10, 10]
            pygame.draw.rect(self.screen, (255, 255, 255), r, 1)
            r = [6, 6, max(1, (self.screen.width - 12) * global_timer.remaining() / global_timer.duration), 8]
            draw_rect_alpha(self.screen, (255, 255, 255), r, 125)

            render_offset = (
                random.random() * sh_amp - sh_amp/2 if screen_shake[0] else 0,
                random.random() * sh_amp - sh_amp/2 if screen_shake[1] else 0
            )

            self.master_screen.blit(
                pygame.transform.scale(self.screen, CFG.ORG_RES), render_offset)
            pygame.display.flip()

            if self.__fps_timer > 1.0:
                self.__fps = self.__frames_drawn
                self.__frames_drawn = 0
                self.__fps_timer = .0
            self.__frames_drawn += 1

    def update_entitymaps(self) -> None:
        self.entitymap.clear()
        self.projectilemap.clear()
        for ent in self.get_entities(ignore={"items_pickedup", "projectiles", "floating_texts"}):
            self.entitymap.add_entity(ent.pos, data={"ent": ent})
        [self.projectilemap.add_entity(ent.pos, data={"ent": ent}) for ent in self.get_entities(ent_type={"projectiles"})]


if __name__ == "__main__":
    pygame.init()
    pygame.joystick.init()

    DEBUG = False
    if DEBUG:
        import os
        from profiling import run_profiling, end_profiling
        run_profiling()
        Game().run()
        end_profiling()
        # das lässt das programm laufen, bis der tab geschlossen ist. nicht so gut..
        os.system("profile_stats.html")
    else:
        Game().run()
