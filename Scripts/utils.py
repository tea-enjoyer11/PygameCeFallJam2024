import numpy as np
from pygame import Vector2, Surface, Color
import pygame
import os
import pickle
import gzip
import random
from typing import List, Tuple, Literal

BASE_SOUND_PATH = ""

if not pygame.mixer.get_init():
    pygame.mixer.init()
if not pygame.font.get_init():
    pygame.font.init()


def load_image(path: str, flip_x: bool = False, flip_y: bool = False, colorkey: Tuple = (0, 0, 0)) -> Surface:
    i = pygame.image.load(path).convert()
    i = pygame.transform.flip(i, flip_x=flip_x, flip_y=flip_y)
    i.set_colorkey(colorkey)
    return i


def load_images(path: str, colorkey: Tuple = (0, 0, 0), imgnames_are_ints: bool = False) -> List[Surface]:
    images = []
    file_names = sorted(int(x.split(".")[0]) if imgnames_are_ints else x for x in os.listdir(path))
    # print(path, file_names)
    for img_name in file_names:
        if not imgnames_are_ints and not img_name.endswith(".png"):
            continue
        images.append(load_image(path + '/' + f"{img_name}{'.png' if imgnames_are_ints else ''}", colorkey=colorkey))
    return images


def props(cls):
    return [i for i in cls.__dict__.keys() if i[:1] != '_']


def random_color(step=1):
    return (random.randrange(0, 255, step), random.randrange(0, 255, step), random.randrange(0, 255, step))


sysFont = pygame.font.SysFont("arial", 24)
_circle_cache = {}


def _circlepoints(r):
    r = int(round(r))
    if r in _circle_cache:
        return _circle_cache[r]
    x, y, e = r, 0, 1 - r
    _circle_cache[r] = points = []
    while x >= y:
        points.append((x, y))
        y += 1
        if e < 0:
            e += 2 * y - 1
        else:
            x -= 1
            e += 2 * (y - x) - 1
    points += [(y, x) for x, y in points if x > y]
    points += [(-x, y) for x, y in points if x]
    points += [(x, -y) for x, y in points if y]
    points.sort()
    return points


def draw_text(screen: pygame.Surface, text: str, pos: tuple, font: pygame.Font = None,
              antialias: bool = True, color: Color = Color(255, 255, 255), background_color: Color | None = None,
              outline_color: Color | None = None, outline_thickness: float = 1.0):
    # outline code from https://stackoverflow.com/questions/54363047/how-to-draw-outline-on-the-fontpygame
    if not font:
        font = sysFont

    textsurface = font.render(text, antialias, color, background_color)

    if outline_color:
        w = textsurface.get_width() + 2 * outline_thickness
        h = font.get_height()

        osurf = pygame.Surface((w, h + 2 * outline_thickness)).convert_alpha()
        osurf.fill((0, 0, 0, 0))

        surf = osurf.copy()

        osurf.blit(font.render(text, True, outline_color).convert_alpha(), (0, 0))

        for dx, dy in _circlepoints(outline_thickness):
            surf.blit(osurf, (dx + outline_thickness, dy + outline_thickness))

        surf.blit(textsurface, (outline_thickness, outline_thickness))
        screen.blit(surf, pos)
    else:
        screen.blit(textsurface, pos)


def hide_mouse() -> None: pygame.mouse.set_visible(False)
def show_mouse() -> None: pygame.mouse.set_visible(True)
def set_mouse_visibility(val: bool) -> None: pygame.mouse.set_visible(val)


def make_surface(size: Tuple, color: Tuple = (0, 0, 0), color_key: Tuple = (0, 0, 0)) -> pygame.Surface:
    s = pygame.Surface(size)
    s.fill(color)
    s.set_colorkey(color_key)
    return s


def loadSound(path, volume=1):
    s = pygame.mixer.Sound(BASE_SOUND_PATH + path)
    s.set_volume(volume)
    return s


def loadSounds(path):
    sounds = []
    for soundName in sorted(os.listdir(BASE_SOUND_PATH + path)):
        sounds.append(loadSound(path + "/" + soundName))
    return sounds


def combineImages(images: List[Surface], pathToOverLayImage: str):
    overLayImage = load_image(pathToOverLayImage).convert_alpha()
    newImages = []
    for img in images:
        newImg = img.copy()
        newImg.blit(overLayImage, (0, 0))
        newImages.append(newImg)

    return newImages


def recolorImages(imgList: Surface, oldColor: Color, newColor: Color, blackKey: bool = False) -> List[Surface]:
    """Only recolors one color at a time! removes any previous .set_colorkey() calls"""
    recoloredImages = []
    for img in imgList:
        imgCopy = img.copy()
        imgCopy.fill(newColor)
        img.set_colorkey(oldColor)
        imgCopy.blit(img, (0, 0))
        if blackKey:
            imgCopy.set_colorkey((0, 0, 0))
        recoloredImages.append(imgCopy)

    return recoloredImages


def fillImgWithColor(surface: Surface, color: Color) -> Surface:
    """Fill all pixels of the surface with color, preserve transparency."""
    r, g, b = color
    pixel_array = pygame.PixelArray(surface)
    for x in range(surface.get_width()):
        for y in range(surface.get_height()):
            a = surface.get_at((x, y)).a  # Get the alpha value
            pixel_array[x, y] = (r, g, b, a)
    return pixel_array.make_surface()


def recolorSurface(img: Surface, newColor: Color) -> Surface:
    """Recolors all colors except black!"""
    img_copy = img.copy()
    pixel_array = pygame.PixelArray(img_copy)
    new_color_mapped = img_copy.map_rgb(newColor)

    # Iterate over pixels
    for x in range(img_copy.get_width()):
        for y in range(img_copy.get_height()):
            # Only change color if it's not black
            if pixel_array[x, y] != img_copy.map_rgb((0, 0, 0)):
                pixel_array[x, y] = new_color_mapped

    img_copy.set_colorkey((0, 0, 0))
    return img_copy


def palette_sawp(image: Surface, org_pallet: List[Color], new_pallet: List[Color]) -> Surface:
    """
    Swapes color `n` from `org_pallet` with color `m` from `new_pallet`.
    """
    ret = image.copy()
    for o_color, n_color in zip(org_pallet, new_pallet):
        ret_copy = ret.copy()
        ret_copy.fill(n_color)
        ret.set_colorkey(o_color)
        ret_copy.blit(ret, (0, 0))
        ret_copy.set_colorkey((0, 0, 0))
        ret = ret_copy
    return ret


def pallete_swap_dir(images: List[Surface], org_pallet: List[Color], new_pallet: List[Color]) -> Surface:
    """
    Swapes color `n` from `org_pallet` with color `m` from `new_pallet`.
    """
    l = []
    for image in images:
        ret = image.copy()
        for o_color, n_color in zip(org_pallet, new_pallet):
            ret_copy = ret.copy()
            ret_copy.fill(n_color)
            ret.set_colorkey(o_color)
            ret_copy.blit(ret, (0, 0))
            ret_copy.set_colorkey((0, 0, 0))
            ret = ret_copy
        l.append(ret)
    return l


def circle_surf(radius: float, color: Color) -> Surface:
    surf = pygame.Surface((radius * 2, radius * 2))
    pygame.draw.circle(surf, color, (radius, radius), radius)
    surf.set_colorkey((0, 0, 0))
    return surf


def save_pickle(obj: object) -> bytes:
    return pickle.dumps(obj)


def load_pickle(obj: bytes) -> object:
    return pickle.loads(obj)


def save_compressed_pickle(obj: object, compresslevel: int = 9) -> bytes:
    return gzip.compress(pickle.dumps(obj), compresslevel=compresslevel)


def load_compressed_pickle(obj: bytes) -> object:
    return pickle.loads(gzip.decompress(obj))


def surf_is_black(surf: Surface) -> bool:
    surf.lock()
    pixel_array = pygame.surfarray.array3d(surf)
    surf.unlock()
    return np.all(pixel_array == 0)


def hex_to_rgb(hex_color: str) -> Tuple:
    hex_color = hex_color.lstrip('#')  # Remove the hash symbol if present
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str, alpha: Literal[0, 255]) -> Tuple:
    hex_color = hex_color.lstrip('#')  # Remove the hash symbol if present
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def draw_rect_alpha(surface: Surface, color: tuple, rect: pygame.Rect, alpha: Literal[0, 255]) -> None:
    surf = Surface(pygame.Rect(rect).size)
    surf.fill(color)
    surf.set_alpha(alpha)
    surface.blit(surf, rect)
