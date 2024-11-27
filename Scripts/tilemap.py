import collections
from typing import Any
import math
import functools
import json

import pygame
import random

import Scripts.CONFIG as CFG
from Scripts.utils_math import clamp_number_to_range_steps, dist, sign
from Scripts.timer import Timer


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Scripts.ecs_components_systems import Transform

t = (0, -1)
l = (-1, 0)
r = (1, 0)
b = (0, 1)
tl = (-1, -1)
tr = (1, -1)
bl = (-1, 1)
br = (1, 1)
AUTOTILE_MAP = {
    tuple(sorted([r, b])): (1, 0),
    tuple(sorted([r, b, l])): (2, 0),
    tuple(sorted([l, b])): (3, 0),
    tuple(sorted([l, t, b])): (3, 1),
    tuple(sorted([l, t])): (3, 2),
    tuple(sorted([l, t, r])): (2, 2),
    tuple(sorted([r, t])): (1, 2),
    tuple(sorted([r, t, b])): (1, 1),
    tuple(sorted([r, l, b, t])): (2, 1),
}

NEIGHBOR_OFFSETS = [(-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0), (0, 0), (-1, 1), (0, 1), (1, 1)]
PHYSICS_TILES = {"sides", "blocker", "stone"}
AUTOTILE_TYPES = {"dirt", "stone"}
FALLTRHOGH_TILES = {}
DONT_RENDER = {"blocker"}
MAX_PLADES_PER_PATCH = 3
BLADES_STIFFNESS = 360
MAKE_RANDOM_VARIANTS_TYPES = {"grass"}


class GrassTile:
    __slots__ = ("pos", "blades", "padding", "world_pos")
    game: object = None

    def __init__(self, pos) -> None:
        self.pos = pos  # tilepos
        self.blades = []  # sind in world pos
        # blade = list[pos, variant, angle, ob-blade-zurück-schwingt]
        self.padding = 7  # muss man eigentlich dynamisch je nach imgs berechnen.

        self.world_pos = (pos[0] * CFG.TILESIZE, pos[1] * CFG.TILESIZE)

    def add_blade(self, pos, variant):
        self.blades.append([pos, variant, 0.0, 0.0])

    def remove_blade(self, pos):
        raise NotImplementedError

    def create_blades(self):
        offsets = [
            # Aus irgendeinem grund ist (0,0), die untere linke ecke und (tilesize, -tilesize) die obere rechte.
            (0, 0), (4, 0), (8, 0),
            (0, -4), (4, -4), (8, -4),
            (0, -8), (4, -8), (8, -8),
        ]
        random.seed(hash(self.pos))
        for offset in offsets:
            if random.random() >= 3/9:
                continue
            pos = (
                self.pos[0] * CFG.TILESIZE + offset[0],
                self.pos[1] * CFG.TILESIZE + offset[1]
            )
            variant = random.randint(0, 5)
            self.add_blade(pos, variant)
        random.seed(0)

    def sim_wind(self, rot_func):
        for blade in self.blades:
            blade[2] += clamp_number_to_range_steps(rot_func(*blade[0]), -90, 90, 180 / MAX_GRASS_STEPS) / 180

    def render(self, surf: pygame.Surface, shadow_radius=5, offset=(0, 0)):
        shadow_surfs = []
        blades_surfs = []
        for blade in self.blades:
            variant = blade[1]
            angle = blade[2]
            pos = blade[0]
            img, rect, shadow, s_pos = make_rot(variant, angle, pos, radius=shadow_radius)
            blades_surfs.append((img, (rect.x - offset[0], rect.y - offset[1])))
            shadow_surfs.append((shadow, (s_pos[0] - offset[0], s_pos[1] - offset[1])))
        shadow_surfs = sorted(shadow_surfs, key=lambda x: x[1][1])
        surf.fblits(shadow_surfs)
        surf.fblits(blades_surfs)

    def __len__(self): return len(self.blades)


def lerp(val, amt, target):
    if val > target + amt:
        val -= amt
    elif val < target - amt:
        val += amt
    else:
        val = target
    return val


def close_enough(val, target, diff=1.0) -> bool:
    # print(val, target, diff, abs(val - target) <= diff, abs(val - target))
    return abs(val - target) <= diff


class TileMap:
    def __init__(self, game):
        self.game = game
        self.tilemap: collections.defaultdict[int, collections.defaultdict[str, dict]] = {0: {}}  # dict[layer_idx, tilemap]
        self.offgrid_tiles = []
        self.shadows = {}
        self.grass_tiles: dict[tuple, GrassTile] = {}

        GrassTile.game = game

    def place_tile(self, pos: tuple, tile: Any, layer=0) -> None:
        if layer not in self.tilemap:
            self.tilemap[layer] = {}
        str_pos = str(pos[0]) + ';' + str(pos[1])
        # print(self.tilemap[layer])
        self.tilemap[layer][str_pos] = tile

    def remove_tile(self, pos: tuple, layer=0) -> None:
        if layer in self.tilemap:
            str_pos = str(pos[0]) + ';' + str(pos[1])
            if str_pos in self.tilemap[layer]:
                del self.tilemap[layer][str_pos]

    def make_random_variations(self, layer=0):
        for str_pos, tile in self.tilemap[layer].items():
            if tile["type"] in MAKE_RANDOM_VARIANTS_TYPES:
                if random.randint(0, 100) > 80:
                    tile["variant"] = random.randint(1, len(CFG.am.get(tile["type"])) - 1)
                else:
                    tile["variant"] = 0

    def extract(self, id_pairs, keep=False):
        matches = []
        for tile in self.offgrid_tiles.copy():
            if (tile['type'], tile['variant']) in id_pairs:
                matches.append(tile.copy())
                if not keep:
                    self.offgrid_tiles.remove(tile)

        for layer in self.tilemap:
            for loc in self.tilemap[layer]:
                tile = self.tilemap[layer][loc]
                if (tile['type'], tile['variant']) in id_pairs:
                    matches.append(tile.copy())
                    matches[-1]['pos'] = matches[-1]['pos'].copy()
                    matches[-1]['pos'][0] *= CFG.TILESIZE
                    matches[-1]['pos'][1] *= CFG.TILESIZE
                    if not keep:
                        del self.tilemap[layer][loc]

        return matches

    def remove_grass_tile(self, location):
        tile_loc = (
            (location[0] // CFG.TILESIZE),
            (location[1] // CFG.TILESIZE)
        )
        tile_loc_str = f"{int(tile_loc[0])};{int(tile_loc[1])}"
        print(tile_loc)
        if tile_loc_str not in self.grass_tiles:
            return
        del self.grass_tiles[tile_loc_str]

    def place_grass_tile(self, location):
        tile_loc = (
            (location[0] // CFG.TILESIZE),
            (location[1] // CFG.TILESIZE)
        )
        print(tile_loc)
        tile_loc_str = f"{int(tile_loc[0])};{int(tile_loc[1])}"
        if tile_loc_str not in self.grass_tiles:
            self.grass_tiles[tile_loc_str] = GrassTile(tile_loc)

    def init_grass(self):
        for tile in self.grass_tiles.values():
            tile.create_blades()

    def update_grass(self, entity_rects: list[pygame.Rect], force_radius, force_dropoff, dt):
        # TODO
        # einzelne blades müssen zusammen gepackt werden, damit lookup times nicht durch die Decke gehen.
        # Am besten alle blades in einem Tile gruppieren.
        # Dann vllt auch die mögliche state vom tile cachen??
        # ----------------------------------------------------
        # move blades back to base pos
        for t in self.grass_tiles.values():
            for blade in t.blades:
                blade[2] = lerp(blade[2], BLADES_STIFFNESS * dt, 0)

        # for tile in self.grass_tiles.values():
        #     ents = entitymap.query_circle(tile.world_pos, force_dropoff*2)
        #     for ent_pos, ent_data in ents:
        #         ent_rect: pygame.Rect = ent_data["rect"]
        #         ent_pos_center = (ent_rect.centerx, ent_rect.bottom)
        #         for blade in tile.blades:
        #             org_rot = blade[2]
        #             dis = abs(dist((blade[0][0], blade[0][1]+12), ent_pos_center))
        #             # print(ent_data, blade[0], dis)
        #             if dis < force_radius:
        #                 force = 2
        #             else:
        #                 dis = max(0, dis - force_radius)
        #                 force = 1 - min(dis / force_dropoff, 1)
        #             # print(333333333, dis, force)
        #             dir = -1 if ent_pos_center[0] < blade[0][0] else 1
        #             # dont update unless force is stronger
        #             if abs(blade[2]) < force * 90:  # bending because entity collides
        #                 blade[2] = min(max(dir * force * 90 + org_rot * 0.5, -90), 90)
        #                 blade[2] = clamp_number_to_range_steps(blade[2], -90, 90, 180 / MAX_GRASS_STEPS)
        #                 # if dis < 5:
        #                 #     hit_blades.append(blade)
        #                 blade[3] = 0
        #             else:  # if abs(blade[2]) - abs(org_rot) < abs(force) * 90:
        #                 blade[3] = 1
        #             # print(abs(blade[2]) - abs(org_rot), abs(force)*90, abs(blade[2]) < abs(force) * 90)

        processed: set[tuple] = set()
        for rect in entity_rects:
            pos = (rect.centerx, rect.bottom)
            tile_loc = (int(pos[0] // CFG.TILESIZE), int(pos[1] // CFG.TILESIZE))
            tile_loc2 = str(tile_loc[0]) + ';' + str(tile_loc[1])
            if tile_loc in processed or tile_loc2 not in self.grass_tiles:
                continue
            processed.add(tile_loc)
            blades: list[list] = []
            for offset in NEIGHBOR_OFFSETS:
                check_loc = str(tile_loc[0] + offset[0]) + ';' + str(tile_loc[1] + offset[1])
                if check_loc in self.grass_tiles:
                    blades.extend(self.grass_tiles[check_loc].blades)

            for blade in blades:
                org_rot = blade[2]
                dis = abs(dist((blade[0][0], blade[0][1] + 12), pos))
                if dis < force_radius:
                    force = 2
                else:
                    dis = max(0, dis - force_radius)
                    force = 1 - min(dis / force_dropoff, 1)
                dir = -1 if pos[0] < blade[0][0] else 1
                # dont update unless force is stronger
                if abs(blade[2]) < force * 90:  # bending because entity "collides"
                    blade[2] = min(max(dir * force * 90 + org_rot * 0.5, -90), 90)
                    blade[2] = clamp_number_to_range_steps(blade[2], -90, 90, 180 / MAX_GRASS_STEPS)

    def caculate_tile_span(self, size: int):
        if size <= CFG.TILESIZE:
            return 0
        return (size + CFG.TILESIZE - 1) // CFG.TILESIZE - 1

    def get_around(self, pos, size=(CFG.TILESIZE, CFG.TILESIZE), ignore_types: set[str] = set(), layer=None, types: set[str] = set()):
        if not layer:
            layer = 0
        if layer not in self.tilemap:
            return []
        tiles = []
        topleft_tile = (
            int(pos[0] // CFG.TILESIZE),
            int(pos[1] // CFG.TILESIZE)
        )
        bottomright_tile = (
            int(pos[0] // CFG.TILESIZE) + self.caculate_tile_span(size[0]),
            int(pos[1] // CFG.TILESIZE) + self.caculate_tile_span(size[1])
        )
        for x in range(topleft_tile[0], bottomright_tile[0] + 1):
            for y in range(topleft_tile[1], bottomright_tile[1] + 1):
                for offset in NEIGHBOR_OFFSETS:
                    check_loc = str(x + offset[0]) + ';' + str(y + offset[1])
                    if check_loc in self.tilemap[layer]:
                        t = self.tilemap[layer][check_loc]
                        if types:
                            if t["type"] in types and t not in tiles:
                                tiles.append(t)
                        elif t["type"] not in ignore_types and t not in tiles:
                            tiles.append(t)
        return tiles

    def get_tile(self, pos, convert_to_tilespace=False, layer=0):
        if convert_to_tilespace:
            tile_loc = (int(pos[0] // CFG.TILESIZE), int(pos[1] // CFG.TILESIZE))
        else:
            tile_loc = pos
        check_loc = str(tile_loc[0]) + ';' + str(tile_loc[1])
        if layer in self.tilemap:
            if check_loc in self.tilemap[layer]:
                return self.tilemap[layer][check_loc]
        return None

    def save(self, path):
        blades = {}
        for pos, t in self.grass_tiles.items():
            arr = []
            for blade in t.blades:
                arr.append((blade[0], blade[1]))
            blades[pos] = arr
        f = open(path, 'w')
        tilemap = {str(key): value for key, value in self.tilemap.items()}
        json.dump({'tilemap': tilemap,
                   'tile_size': CFG.TILESIZE,
                   'offgrid': self.offgrid_tiles,
                   "blades": blades}, f)
        f.close()

    def load(self, path):
        f = open(path, 'r')
        map_data = json.load(f)
        f.close()

        self.tilemap = {int(key): value for key, value in map_data['tilemap'].items()}
        CFG.TILESIZE = map_data['tile_size']
        self.offgrid_tiles = map_data['offgrid']
        for pos, data in map_data["blades"].items():
            # print(data)
            t = GrassTile((int(pos.split(";")[0]), int(pos.split(";")[1])))
            self.grass_tiles[pos] = t

    def solid_check(self, pos):
        tile_loc = str(int(pos[0] // CFG.TILESIZE)) + ';' + str(int(pos[1] // CFG.TILESIZE))
        if tile_loc in self.tilemap:
            if self.tilemap[tile_loc]['type'] in PHYSICS_TILES:
                return self.tilemap[tile_loc]

    def physics_rects_around(self, pos, size=(16, 16)):
        rects = []
        for tile in self.get_around(pos, size=size):
            if tile["type"] in PHYSICS_TILES:
                rects.append(pygame.FRect(tile['pos'][0] * CFG.TILESIZE, tile['pos'][1] * CFG.TILESIZE, CFG.TILESIZE, CFG.TILESIZE))
        return rects

    def make_rect_from_tile(self, tile) -> pygame.FRect:
        return pygame.FRect(tile['pos'][0] * CFG.TILESIZE, tile['pos'][1] * CFG.TILESIZE, CFG.TILESIZE, CFG.TILESIZE)

    def rotate_grass(self, rot_function):
        for t in self.grass_tiles.values():
            t.sim_wind(rot_function)

    def render_shadows(self, surf: pygame.Surface, offset=(0, 0)) -> None:
        # shadows
        fblits = []
        for _, tile in self.shadows.items():
            fblits.append((
                tile,
                (_[0] * CFG.TILESIZE - offset[0], _[1] * CFG.TILESIZE - offset[1])
            ))
        surf.fblits(fblits)

    def render(
        self,
        surf: pygame.Surface, offset=(0, 0),
        debug_render_grass_tiles=False,
        render_dont_render=False,
        render_offgrid=True,
        main_layer=None,
        render_layer: list[int] = [0]
    ):
        fblits = []
        for layer in range(render_layer[0], render_layer[-1]+1):
            if layer not in self.tilemap:
                continue
            for x in range(int(offset[0] // CFG.TILESIZE), int((offset[0] + surf.get_width()) // CFG.TILESIZE + 1)):
                for y in range(int(offset[1] // CFG.TILESIZE), int((offset[1] + surf.get_height()) // CFG.TILESIZE + 1)):
                    loc = str(x) + ';' + str(y)
                    if loc in self.tilemap[layer]:
                        tile = self.tilemap[layer][loc]
                        if render_dont_render or tile["type"] not in DONT_RENDER:
                            # surf.blit(CFG.am.get(f"{tile["type"]}/{tile["variant"]}"), (tile['pos'][0] * CFG.TILESIZE - offset[0], tile['pos'][1] * CFG.TILESIZE - offset[1]))
                            a = 125 if main_layer != None and main_layer != layer else 255
                            # print(tile["pos"], f"{tile["type"]}/{tile["variant"]}", a, type(CFG.am.get(f"{tile["type"]}/{tile["variant"]}", alpha=a)))
                            fblits.append((
                                CFG.am.get(f"{tile["type"]}/{tile["variant"]}", alpha=a),
                                (tile['pos'][0] * CFG.TILESIZE - offset[0], tile['pos'][1] * CFG.TILESIZE - offset[1])
                            ))
        surf.fblits(fblits)
        fblits.clear()
        if render_offgrid:
            for tile in self.offgrid_tiles:
                # surf.blit(CFG.am.get(f"{tile["type"]}/{tile["variant"]}"), (tile['pos'][0] - offset[0], tile['pos'][1] - offset[1]))
                fblits.append((
                    CFG.am.get(f"{tile["type"]}/{tile["variant"]}"),
                    (tile['pos'][0] - offset[0], tile['pos'][1] - offset[1])
                ))
        surf.fblits(fblits)
        fblits.clear()
        if 0 in render_layer:  # grass zählt zu tile_layer 0
            for x in range(int(offset[0] // CFG.TILESIZE), int((offset[0] + surf.get_width()) // CFG.TILESIZE + 1)):
                for y in range(int(offset[1] // CFG.TILESIZE), int((offset[1] + surf.get_height()) // CFG.TILESIZE + 1)):
                    loc = str(x) + ';' + str(y)
                    if loc in self.grass_tiles:
                        self.grass_tiles[loc].render(surf, offset=offset)  # fblits benutzen?
                        # self.grass_tiles[loc].render_debug(surf, offset=offset)  # fblits benutzen?

        if debug_render_grass_tiles:
            for tile in self.grass_tiles.values():
                r = pygame.Rect(tile.pos[0] * CFG.TILESIZE - offset[0], tile.pos[1] * CFG.TILESIZE-offset[1], CFG.TILESIZE, CFG.TILESIZE)
                pygame.draw.rect(surf, (0, 100, 0), r, 1)

    def autotile(self, layer=0):
        for loc, tile in self.tilemap[layer].items():
            neighbors = set()
            for shift in [(1, 0), (-1, 0), (0, -1), (0, 1)]:
                check_loc = str(tile['pos'][0] + shift[0]) + ';' + str(tile['pos'][1] + shift[1])
                if check_loc in self.tilemap[layer]:
                    if self.tilemap[layer][check_loc]['type'] == tile['type']:
                        neighbors.add(shift)
            neighbors = tuple(sorted(neighbors))
            if (tile['type'] in AUTOTILE_TYPES) and (neighbors in AUTOTILE_MAP):
                tile['variant'] = atlas_coords_to_1d_array(AUTOTILE_MAP[neighbors], 4)

    def make_shadow2(self, shadow_length=CFG.TILESIZE, shadow_dir=(-1, 1)):
        # ! Für vllt besseres rendering kann man die final surface in chunks unterteilen und nur die dann rendern. Müsste man testen
        shadow_making_tiles: list[dict] = []
        layer = 0

        def is_shadow_making_tile(pos: tuple) -> bool:
            str_pos = f"{pos[0]};{pos[1]}"
            if str_pos in self.tilemap[layer]:
                tile = self.tilemap[layer][str_pos]
                if tile["type"] == "sides":
                    above_pos = f"{pos[0]};{pos[1]-1}"
                    if above_pos in self.tilemap[layer]:
                        if self.tilemap[layer][above_pos]["type"] == "stone":
                            return True
                return tile["type"] == "stone"
            return False

        def fill_img(img: pygame.Surface, color=(255, 255, 0)) -> pygame.Surface:
            img_copy = img.copy()
            img_copy.fill(color)
            return img_copy

        for tile in self.tilemap[layer].values():
            if is_shadow_making_tile(tile["pos"]):
                shadow_making_tiles.append(tile)

        tl, br = (1000, 1000), (-1000, -1000)
        for tile in shadow_making_tiles:
            pos = tile["pos"]
            if pos[0] < tl[0]:
                tl = (pos[0], tl[1])
            if pos[1] < tl[1]:
                tl = (tl[0], pos[1])
            if pos[0] > br[0]:
                br = (pos[0], br[1])
            if pos[1] > br[1]:
                br = (br[0], pos[1])

        shadow_color = (255, 255, 0)
        width, height = (br[0]-tl[0]+1)*CFG.TILESIZE, (br[1]-tl[1]+1)*CFG.TILESIZE
        shadow_surf = pygame.Surface((width, height))
        shadow_surf.fill((255, 0, 0))
        shadow_surf.set_colorkey((255, 0, 0))
        for tile in shadow_making_tiles:
            yoffset = abs(tl[1])
            pos = ((tile["pos"][0]-1)*CFG.TILESIZE, (tile["pos"][1]+yoffset)*CFG.TILESIZE)
            shadow_surf.blit(fill_img(CFG.am.get(f"{tile["type"]}/{tile["variant"]}"), color=shadow_color), pos)

        offset = (
            shadow_dir[0] * shadow_length,
            shadow_dir[1] * shadow_length
        )
        final_shadow_surf = pygame.Surface((
            width + abs(offset[0]),
            height + abs(offset[1])
        ))
        final_shadow_surf.fill((255, 0, 0))

        for i in range(shadow_length + 1):  # * könnte für polish bei starken steps zwischen blits machen, damit die kanten Glatt sind. (Bei shadow_dir von (-4, 5) z.B:)
            pos = [
                -shadow_dir[0]*i,
                -shadow_dir[1]*i,
            ]
            if shadow_dir[0] > 0:
                pos[0] += offset[0]
            if shadow_dir[1] > 0:
                pos[1] += offset[1]
            final_shadow_surf.blit(shadow_surf, pos)

        for tile in shadow_making_tiles:
            yoffset = abs(tl[1])
            pos = [(tile["pos"][0]-1)*CFG.TILESIZE, (tile["pos"][1]+yoffset)*CFG.TILESIZE]
            if shadow_dir[0] < 0:
                pos[0] += abs(shadow_dir[0]) * CFG.TILESIZE
            if shadow_dir[1] < 1:
                pos[1] += abs(shadow_dir[1]) * CFG.TILESIZE
            final_shadow_surf.blit(fill_img(CFG.am.get(f"{tile["type"]}/{tile["variant"]}"), color=(255, 0, 0)), pos)

        pos = list(tl)
        if shadow_dir[0] < 0:
            pos[0] += offset[0] / CFG.TILESIZE * 2
        if shadow_dir[1] < 0:
            pos[1] += offset[1] / CFG.TILESIZE
        final_shadow_surf.set_alpha(125)
        # final_shadow_surf.set_colorkey((255, 0, 0))
        self.shadows[tuple(pos)] = final_shadow_surf

    def make_shadow(self, shadow_length=19, shadow_dir=(-0.781, 1.125)) -> None:
        layer = 0
        # region Schlagschatten
        shadow_making_tiles: list[dict] = []
        shadow_covering_tiles: list[dict] = []

        def is_shadow_making_tile(pos: tuple) -> bool:
            str_pos = f"{pos[0]};{pos[1]}"
            if str_pos in self.tilemap[layer]:
                tile = self.tilemap[layer][str_pos]
                if tile["type"] == "sides":
                    above_pos = f"{pos[0]};{pos[1]-1}"
                    if above_pos in self.tilemap[layer]:
                        if self.tilemap[layer][above_pos]["type"] == "stone":
                            return True
                return tile["type"] == "stone"
            return False

        for tile in self.tilemap[layer].values():
            if is_shadow_making_tile(tile["pos"]):
                shadow_making_tiles.append(tile)
        for tile in self.tilemap[layer+1].values():
            if tile["type"] in {"stone", "sides"}:
                shadow_covering_tiles.append(tile)

        tl, br = (1000, 1000), (-1000, -1000)
        for tile in shadow_making_tiles:
            pos = tile["pos"]
            if pos[0] < tl[0]:
                tl = (pos[0], tl[1])
            if pos[1] < tl[1]:
                tl = (tl[0], pos[1])
            if pos[0] > br[0]:
                br = (pos[0], br[1])
            if pos[1] > br[1]:
                br = (br[0], pos[1])

        extra_size = (
            (abs(shadow_dir[0]) * shadow_length) // CFG.TILESIZE + 2,
            (abs(shadow_dir[1]) * shadow_length) // CFG.TILESIZE + 2
        )
        size = (
            (br[0]-tl[0])*CFG.TILESIZE + abs(extra_size[0])*CFG.TILESIZE,
            (br[1]-tl[1])*CFG.TILESIZE + abs(extra_size[1])*CFG.TILESIZE
        )  # in CFG.TILESIZE größe
        offset = (
            ((shadow_dir[0] * CFG.TILESIZE - CFG.TILESIZE) // CFG.TILESIZE) * CFG.TILESIZE if shadow_dir[0] < 0 else 0,
            ((shadow_dir[1] * CFG.TILESIZE - CFG.TILESIZE) // CFG.TILESIZE) * CFG.TILESIZE if shadow_dir[1] < 0 else 0
        )
        offset = (
            offset[0] + CFG.TILESIZE if 0 > shadow_dir[0] > -1.5 else offset[0],  # 0 & -1.5 sind Werte die ich durch testen gefunden habe!
            offset[1] + CFG.TILESIZE if 0 > shadow_dir[1] > -1.5 else offset[1]  # 0 & -1.5 sind Werte die ich durch testen gefunden habe!
        )
        print(size, extra_size, offset)
        SHADOW_COLOR = (1, 0, 0)
        SHADOW_COLORKEY_COLOR = (255, 0, 0)
        SHADOW_SURF = pygame.Surface(size)
        SHADOW_SURF.fill(SHADOW_COLORKEY_COLOR)
        SHADOW_SURF.set_colorkey(SHADOW_COLORKEY_COLOR)

        TEMP_SURF = pygame.Surface((size[0]-CFG.TILESIZE, size[1]-CFG.TILESIZE))
        TEMP_SURF.set_colorkey((0, 0, 0))
        for tile in shadow_making_tiles:
            local_pos = (tile["pos"][0] - tl[0], tile["pos"][1] - tl[1])
            pygame.draw.rect(TEMP_SURF, SHADOW_COLOR, [local_pos[0]*CFG.TILESIZE, local_pos[1]*CFG.TILESIZE, CFG.TILESIZE, CFG.TILESIZE])

        for i in range(shadow_length):
            local_pos = (
                abs(offset[0]) + shadow_dir[0] * i,
                abs(offset[1]) + shadow_dir[1] * i
            )
            SHADOW_SURF.blit(TEMP_SURF, local_pos)
        for tile in shadow_making_tiles + shadow_covering_tiles:
            local_pos = (tile["pos"][0] - tl[0], tile["pos"][1] - tl[1])
            pygame.draw.rect(SHADOW_SURF, (255, 0, 0),  [
                local_pos[0]*CFG.TILESIZE + abs(offset[0]),
                local_pos[1]*CFG.TILESIZE + abs(offset[1]),
                CFG.TILESIZE,
                CFG.TILESIZE]
            )

        SHADOW_SURF.set_alpha(125)
        self.shadows[(
            tl[0] + (offset[0] // CFG.TILESIZE),
            tl[1] + (offset[1] // CFG.TILESIZE)
        )] = SHADOW_SURF
        # endregion

        # region Schatten an der Wand
        if shadow_dir[1] < 0:  # nach oben, dann muss kein Schatten erstellt werden.
            return

        def is_shadow_recieving(tile) -> bool:
            ret = False
            if tile["type"] == "sides" and tile["variant"] == 1:
                ret = True
            elif tile["type"] == "stone":
                if layer+1 in self.tilemap:
                    # print(1)
                    pos = f"{tile["pos"][0]};{tile["pos"][1]}"
                    if pos in self.tilemap[layer+1]:
                        above_tile = self.tilemap[layer+1][pos]
                        # print(above_tile)
                        if above_tile["type"] == "sides":
                            ret = True
            return ret

        shadow_recieving_tiles: list[dict] = []
        for tile in self.tilemap[layer].values():
            # print(tile["type"], is_shadow_recieving(tile))
            if is_shadow_recieving(tile):
                shadow_recieving_tiles.append(tile)

        tl, br = (1000, 1000), (-1000, -1000)
        for tile in shadow_making_tiles:
            pos = tile["pos"]
            if pos[0] < tl[0]:
                tl = (pos[0], tl[1])
            if pos[1] < tl[1]:
                tl = (tl[0], pos[1])
            if pos[0] > br[0]:
                br = (pos[0], br[1])
            if pos[1] > br[1]:
                br = (br[0], pos[1])

        size = ((br[0]-tl[0])*CFG.TILESIZE, (br[1]-tl[1])*CFG.TILESIZE)
        SHADOW_SURF_2 = pygame.Surface((size[0]+CFG.TILESIZE, size[1]+CFG.TILESIZE))
        SHADOW_SURF_2.fill(SHADOW_COLORKEY_COLOR)
        SHADOW_SURF_2.set_colorkey(SHADOW_COLORKEY_COLOR)
        for tile in shadow_recieving_tiles:
            local_pos = (tile["pos"][0] - tl[0], tile["pos"][1] - tl[1])
            pygame.draw.rect(SHADOW_SURF_2, SHADOW_COLOR, [local_pos[0]*CFG.TILESIZE, local_pos[1]*CFG.TILESIZE, CFG.TILESIZE, CFG.TILESIZE])

        SHADOW_SURF_2.set_alpha(125)
        self.shadows[tl] = SHADOW_SURF_2
        # endregion

    def make_walls(self, layer=0) -> None:
        def make_stone_walls(layer):
            wall_height = 2  # in tiles
            for i in range(0, wall_height):
                for str_pos, tile in sorted(self.tilemap[layer+i].copy().items(), key=lambda x: x[1]["pos"][1], reverse=True):
                    if tile["type"] != "stone":  # Wände sind nur für steine
                        continue
                    # print(tile)
                    pos_above_str = pos_to_str([tile["pos"][0], tile["pos"][1]-2])
                    self.place_tile(
                        str_pos_to_list(pos_above_str),
                        {
                            "type": "stone",
                            "variant": 0,
                            "pos": str_pos_to_list(pos_above_str)
                        },
                        layer=layer+1
                    )
                    tile["type"] = "sides"
                    tile["variant"] = 1

                    # damit man, falls man hinter die Wände kommt nur maximal einen tile "runter" gehen kann.
                    if i == 0:
                        self.place_tile(
                            str_pos_to_list(pos_above_str),
                            {
                                "type": "stone",
                                "variant": 0,
                                "pos": str_pos_to_list(pos_above_str)
                            },
                            layer=layer
                        )

        def make_island_walls():
            layer = 0
            lt = {
                "grass": 0,
                "dirt": 2,
                "sides": 0,
                # "stone": 0,
            }
            for str_pos, tile in self.tilemap[layer].copy().items():
                pos = [int(x) for x in str_pos.split(";")]
                pos_below = f"{pos[0]};{pos[1]+1}"
                if pos_below not in self.tilemap[layer]:
                    self.tilemap[layer][pos_below] = {"type": "sides", "variant": lt[tile["type"]], "pos": [pos[0], pos[1] + 1]}
        make_stone_walls(layer)
        make_island_walls()


def pos_to_str(pos: tuple) -> str:
    return f"{pos[0]};{pos[1]+1}"


def str_pos_to_list(pos: str) -> list:
    return [int(x) for x in pos.split(";")]


def atlas_coords_to_1d_array(pos: tuple, n_rows: int) -> int:
    return pos[1] + n_rows * pos[0]


MAX_GRASS_STEPS = 25


def make_rot(variant, angle, b_pos, radius=6) -> tuple[pygame.Surface, pygame.FRect, pygame.Surface, pygame.FRect]:
    # org_image: pygame.Surface = game.assets["grass_blades"][variant]
    org_image: pygame.Surface = CFG.am.get(f"grass_blades/{variant}")
    org_rect = org_image.get_frect()
    org_rect.topleft = b_pos
    rot_image = make_rot_image(variant, angle)
    rot_rect = rot_image.get_frect(center=org_rect.center)
    shadow = make_shadow(r=radius)
    shadow_pos = (b_pos[0]-radius+2, b_pos[1]+radius*2-1)

    # print(make_rot_image.cache_info(), make_shadow.cache_info())

    return (rot_image, rot_rect, shadow, shadow_pos)


@ functools.lru_cache(maxsize=2048)
def make_rot_image(variant, angle) -> pygame.Surface:
    # org_image: pygame.Surface = game.assets["grass_blades"][variant]
    org_image: pygame.Surface = CFG.am.get(f"grass_blades/{variant}")
    rot_image = pygame.transform.rotate(org_image, angle)
    return rot_image


@ functools.lru_cache(maxsize=2048)
def make_shadow(r=6, alpha=60) -> pygame.Surface:
    s = pygame.Surface((r * 2, r * 2))
    s.fill((255, 0, 0))
    pygame.draw.circle(s, (0, 0, 0), (r, r), r)
    s.set_colorkey((255, 0, 0))
    s.set_alpha(alpha)
    return s


class HashMap(object):
    """
    Hashmap is a a spatial index which can be used for a broad-phase
    collision detection strategy.
    """

    @ staticmethod
    def from_points(cell_size, points, data=None) -> "HashMap":
        hm = HashMap(cell_size)
        if not data:
            data = [{}] * len(points)
        [hm.insert(p, d) for p, d in zip(points, data)]
        return hm

    def __init__(self, cell_size):
        self.cell_size = cell_size
        self.grid = collections.defaultdict(list)

    def key(self, point) -> object:
        cell_size = self.cell_size
        return (
            int((math.floor(point[0]/cell_size))*cell_size),
            int((math.floor(point[1]/cell_size))*cell_size)
        )
        # return tuple([int((math.floor(p/cell_size))*cell_size) for p in point])

    def insert(self, point, data: dict = {}) -> None:
        """
        Insert point into the hashmap.
        """
        rect: pygame.Rect = data["ent"].frect
        left = int(rect.x // self.cell_size)
        right = int((rect.x + rect.width) // self.cell_size)
        top = int(rect.y // self.cell_size)
        bottom = int((rect.y + rect.height) // self.cell_size)

        for x in range(left, right + 1):
            for y in range(top, bottom + 1):
                cell_key = (x * self.cell_size, y * self.cell_size)
                # cell_key = self.key((x, y))
                # print(data)
                # self.grid.setdefault(cell_key, []).append((point, data))
                self.grid[cell_key].append((point, data))

    def query_quad(self, point: tuple[float, float], size: tuple[float, float] = (0.0, 0.0), ignore_points: set[tuple[float, float]] = set()) -> list[tuple[tuple, Any]]:  # list[tuple[key, data]]
        l = []
        x_start, y_start = self.key(point)
        x_end, y_end = self.key((point[0] + size[0], point[1] + size[1]))

        # Iterate over the cells within the bounds (from point to point + size)
        # Each step will cover one cell in the grid.
        x = x_start
        while x < x_end:
            y = y_start
            while y < y_end:
                # Generate the key for the current cell
                key = self.key((x, y))

                # Query the grid for the current cell
                output = self.grid.get(key, [])

                # Add objects to the result list, ensuring no duplicates
                for o in output:
                    if o[0] not in ignore_points and o not in l:
                        l.append(o)

                # Move to the next y coordinate (step to next row)
                y += self.cell_size

            # Move to the next x coordinate (step to next column)
            x += self.cell_size

        return l

    def query(self, point: tuple[float, float], size: tuple[float, float] = (0.0, 0.0), ignore_points: set[tuple[float, float]] = set()) -> list[tuple[tuple, Any]]:  # list[tuple[key, data]]
        """
        Return all objects in the cell specified by point.
        """
        if size[0] // self.cell_size > 1.0 or size[1] // self.cell_size > 1:
            return self.query_quad(point, size, ignore_points=ignore_points)
        l = []
        keys = {
            self.key(point),
            self.key((point[0] + size[0], point[1])),
            self.key((point[0], point[1] + size[1])),
            self.key((point[0] + size[0], point[1] + size[1])),
        }  # Drauf achten, dass keys nicht doppelt vorkommen!! -> deshalb set!
        for key in keys:
            output = self.grid[key]
            for o in output:
                if o[0] not in ignore_points and o not in l:
                    l.append(o)
            # for output in self.grid.setdefault(key, []):
            #     if output not in l:
            #         l.append(output)

        # print(l)
        return l
        # return self.grid.setdefault(self.key(point), [])

    def clear(self) -> None:
        self.grid.clear()

    def get_all(self) -> list[tuple[tuple, Any]]:
        l = []
        found_already = set()
        keys = set(self.grid.keys())

        for key in keys:
            output = self.grid[key]
            for o in output:
                if o[0] not in found_already:
                    l.append(o)
                    found_already.add(o[0])

        return l


class EntityMap:
    def __init__(self, cell_size=32) -> None:
        self.entity_hashmap = HashMap(cell_size)

    def clear(self) -> None:
        self.entity_hashmap.clear()

    def get_cells(self) -> list[tuple]: return [(k, v) for k, v in self.entity_hashmap.grid.items()]

    def add_entity(self, entity_pos: tuple, data: dict = {}) -> None:
        self.entity_hashmap.insert(point=entity_pos, data=data)

    def query(self, position: tuple, size: tuple = (0, 0), ignore_points: set[tuple] = set()) -> list:
        return self.entity_hashmap.query(position, size=size, ignore_points=ignore_points)

    def query_circle(self, position: tuple, radius: float) -> list:
        cell_size = self.entity_hashmap.cell_size
        found = []

        min_cell_x = int((position[0] - radius) // cell_size)
        max_cell_x = int((position[0] + radius) // cell_size)
        min_cell_y = int((position[1] - radius) // cell_size)
        max_cell_y = int((position[1] + radius) // cell_size)

        for x in range(min_cell_x, max_cell_x+1):
            for y in range(min_cell_y, max_cell_y+1):
                data = self.entity_hashmap.query((x*cell_size, y*cell_size))
                found.extend(
                    [(pos, entity) for (pos, entity) in data
                     if dist(pos, position) <= radius]
                )
        return found

    def get_all(self) -> ...: return self.entity_hashmap.get_all()

    def debug_render(self, surf: pygame.Surface, offset: tuple = (0, 0)) -> None:
        for tile_pos in self.entity_hashmap.grid:
            pygame.draw.rect(surf, (255, 255, 0), [tile_pos[0] - offset[0], tile_pos[1] - offset[1], self.entity_hashmap.cell_size, self.entity_hashmap.cell_size], 1)
