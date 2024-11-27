from json import load
import sys

import pygame
import random

from Scripts.utils import load_image, load_images
from Scripts.tilemap import TileMap
import Scripts.CONFIG as CFG


RENDER_SCALE = 2.0


class Editor:
    def __init__(self):
        pygame.init()
        pygame.font.init()

        pygame.display.set_caption('editor')
        self.screen = pygame.display.set_mode((1200, 720))
        self.display = pygame.Surface((600, 360))

        self.font = pygame.font.SysFont("arial", 16)
        self.clock = pygame.time.Clock()

        assets = {
            "blocker": [load_image("assets/tiles/blocker.png")],
            "sides": [load_image("assets/tiles/grass/side.png"), load_image("assets/tiles/stone/side.png"), load_image("assets/tiles/dirt/side.png")],
            "grass": [load_image("assets/tiles/grass/top0.png")],
            # "dirt": [load_image("assets/tiles/dirt/top.png")],
            "dirt": CFG.parse_tileset("assets/tiles/dirt/tilemap.png", as_array=True),
            "stone": CFG.parse_tileset("assets/tiles/stone/tilemap.png", as_array=True),
            "spawners": load_images("assets/tiles/spawners", imgnames_are_ints=True),
            "blades_cover": [load_image("assets/tiles/blades_cover.png")],
            "grass_blades": load_images("assets/tiles/grass_blades"),
            "deco": load_images("assets/tiles/deco"),
            # "tilesets": {
            #     "grass-stone": load_images("assets/tiles/tileset/grass-stone", imgnames_are_ints=True),
            #     "dirt-grass": load_images("assets/tiles/tileset/dirt-grass", imgnames_are_ints=True),
            # },
        }
        CFG.am.assets = assets
        self.blade_cover_group = 6

        self.movement = [False, False, False, False]

        self.tilemap = TileMap(self)

        try:
            self.tilemap.load('map.json')
        except FileNotFoundError:
            pass

        self.scroll = [0, 0]

        self.tile_list = list(CFG.am)
        self.tile_group = 0
        self.tile_variant = 0

        self.clicking = False
        self.right_clicking = False
        self.shift = False
        self.ongrid = True
        self.toggle_view = False

        self.toggle_controls = True

        self.tile_layer = 0

    def run(self):
        boost = False
        while True:
            self.display.fill((0, 0, 0))

            self.scroll[0] += (self.movement[1] - self.movement[0]) * 2 * (4 if boost else 1)
            self.scroll[1] += (self.movement[3] - self.movement[2]) * 2 * (4 if boost else 1)
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            self.tilemap.render(self.display, offset=render_scroll, debug_render_grass_tiles=True, render_dont_render=True, render_offgrid=True, main_layer=self.tile_layer)
            # current_tile_img = self.assets[self.tile_list[self.tile_group]][self.tile_variant].copy()
            current_tile_img = CFG.am.get(f"{self.tile_list[self.tile_group]}/{self.tile_variant}").copy()
            current_tile_img.set_alpha(100)

            mpos = pygame.mouse.get_pos()
            mpos = (mpos[0] / RENDER_SCALE, mpos[1] / RENDER_SCALE)
            tile_pos = (int((mpos[0] + self.scroll[0]) // CFG.TILESIZE), int((mpos[1] + self.scroll[1]) // CFG.TILESIZE))

            if self.ongrid:
                self.display.blit(current_tile_img, (tile_pos[0] * CFG.TILESIZE - self.scroll[0], tile_pos[1] * CFG.TILESIZE - self.scroll[1]))
            else:
                self.display.blit(current_tile_img, mpos)

            if self.clicking and self.ongrid:
                if self.tile_group == self.blade_cover_group:
                    mx, my = CFG.get_mouse_pos(s=2)
                    self.tilemap.place_grass_tile(
                        (
                            int(mx + self.scroll[0]),
                            int(my + self.scroll[1])
                        )
                        # int(random.randint(0, len(self.assets["grass_blades"])-1)),
                    )
                else:
                    self.tilemap.place_tile(tile_pos, {'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': tile_pos}, self.tile_layer)
                    # self.tilemap.tilemap[self.tile_layer][str(tile_pos[0]) + ';' + str(tile_pos[1])] = {'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': tile_pos}
            if self.right_clicking:
                # tile_loc = str(tile_pos[0]) + ';' + str(tile_pos[1])
                if self.tile_group == self.blade_cover_group:
                    mx, my = CFG.get_mouse_pos(s=2)
                    self.tilemap.remove_grass_tile((
                        int(mx + self.scroll[0]),
                        int(my + self.scroll[1])
                    ))
                self.tilemap.remove_tile(tile_pos, self.tile_layer)
                for tile in self.tilemap.offgrid_tiles.copy():
                    # tile_img = self.assets[tile['type']][tile['variant']]
                    tile_img = CFG.am.get(f"{tile["type"]}/{tile["variant"]}")
                    tile_r = pygame.Rect(tile['pos'][0] - self.scroll[0], tile['pos'][1] - self.scroll[1], tile_img.get_width(), tile_img.get_height())
                    if tile_r.collidepoint(mpos):
                        self.tilemap.offgrid_tiles.remove(tile)

            self.display.blit(current_tile_img, (5, 5))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.clicking = True
                        if not self.ongrid:
                            self.tilemap.offgrid_tiles.append({'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': (mpos[0] + self.scroll[0], mpos[1] + self.scroll[1])})
                    if event.button == 3:
                        self.right_clicking = True
                    elif self.shift:
                        if event.button == 4:
                            self.tile_variant = (self.tile_variant - 1) % len(CFG.am.get(f"{self.tile_list[self.tile_group]}"))
                        elif event.button == 5:
                            self.tile_variant = (self.tile_variant + 1) % len(CFG.am.get(f"{self.tile_list[self.tile_group]}"))
                    else:
                        if event.button == 4:
                            self.tile_group = (self.tile_group - 1) % len(self.tile_list)
                            self.tile_variant = 0
                        elif event.button == 5:
                            self.tile_group = (self.tile_group + 1) % len(self.tile_list)
                            self.tile_variant = 0
                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.clicking = False
                    if event.button == 3:
                        self.right_clicking = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:
                        self.movement[0] = True
                    if event.key == pygame.K_d:
                        self.movement[1] = True
                    if event.key == pygame.K_w:
                        self.movement[2] = True
                    if event.key == pygame.K_s:
                        self.movement[3] = True
                    if event.key == pygame.K_g:
                        self.ongrid = not self.ongrid
                    if event.key == pygame.K_t:
                        self.tilemap.autotile()
                    if event.key == pygame.K_o:
                        self.tilemap.save('map.json')
                        print("saved tilemap")
                    if event.key == pygame.K_i:
                        try:
                            self.tilemap.load('map.json')
                            print("loaded tilemap")
                        except FileNotFoundError:
                            print("File map.json was not found1")
                    if event.key == pygame.K_LSHIFT:
                        self.shift = True
                    if event.key == pygame.K_LCTRL:
                        boost = True
                    if event.key == pygame.K_LALT:
                        self.shift_layer = True
                    if event.key == pygame.K_h:
                        self.toggle_view = not self.toggle_view
                    if event.key == pygame.K_z:
                        self.toggle_controls = not self.toggle_controls
                    if event.key == pygame.K_UP:
                        self.tile_layer += 1
                    if event.key == pygame.K_DOWN:
                        self.tile_layer -= 1
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_a:
                        self.movement[0] = False
                    if event.key == pygame.K_d:
                        self.movement[1] = False
                    if event.key == pygame.K_w:
                        self.movement[2] = False
                    if event.key == pygame.K_s:
                        self.movement[3] = False
                    if event.key == pygame.K_LSHIFT:
                        self.shift = False
                    if event.key == pygame.K_LCTRL:
                        boost = False
                    if event.key == pygame.K_LALT:
                        self.shift_layer = False

            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))

            if self.toggle_controls:
                s = self.font.render("--- Toggle Controls: Z ---\n\nmove: WASD\nboost: LCTRL\nplace/break: RMB/LMB\nchange tiles: MWHEEL\nchange tiles: MWHEEL + (LSHIFT)\nchange Layer: MWHEEL + (LALT)\nToggle view layer: H\nAutotile: T\ntoggle offgrid: G\nSave: O\nLoad: I", True, (0, 255, 0), (0, 0, 0))
            else:
                s = self.font.render("--- Toggle Controls: Z ---", True, (0, 255, 0), (0, 0, 0))
            self.screen.blit(s, (self.screen.width - s.width, self.screen.height - s.height))
            s = self.font.render(f"--- Tilelayer: {self.tile_layer} ---", True, (0, 255, 0), (0, 0, 0))
            self.screen.blit(s, (self.screen.width - s.width, 0))

            pygame.display.update()
            self.clock.tick(60)


if __name__ == "__main__":
    e = Editor()
    e.run()
