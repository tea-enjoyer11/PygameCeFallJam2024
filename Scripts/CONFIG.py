from Scripts.utils_math import clamp_number_to_range_steps
import json
from Scripts.utils import load_images
import pygame

ORG_RES = (1080, 720)
DOWNSCALE_FACTOR = 3
RES = (ORG_RES[0] / DOWNSCALE_FACTOR, ORG_RES[1] / DOWNSCALE_FACTOR)
RES_VEC = pygame.Vector2(RES)
TILESIZE = 15

GRAVITY = 100


def get_mouse_pos(s=DOWNSCALE_FACTOR) -> tuple[float, float]:
    p = pygame.mouse.get_pos()
    return (p[0] / s, p[1] / s)


def parse_tileset(path: str, tilesize: tuple = None, as_array=False, colorkey=(0, 0, 0), alpha=255):
    if not tilesize:
        tilesize = (TILESIZE, TILESIZE)
    if alpha != 255:
        img = pygame.image.load(path).convert_alpha()
    else:
        img = pygame.image.load(path).convert()
    img.set_colorkey(colorkey)
    img.set_alpha(alpha)
    img_size = img.get_size()

    if as_array:
        ret = []
    else:
        ret = {}

    for x in range(0, img_size[0] // tilesize[0]):
        for y in range(0, img_size[1] // tilesize[1]):
            if as_array:
                ret.append(img.subsurface([x * tilesize[0], y * tilesize[1], tilesize[0], tilesize[1]]))
            else:
                ret[(x, y)] = img.subsurface([x * tilesize[0], y * tilesize[1], tilesize[0], tilesize[1]])

    return ret


class AssetManager:
    roation_steps = 360/32
    # könnte von ALLEN images die rotated vorgenerien ... :thinking:

    def premake_all_rotations(self) -> None:
        raise NotImplementedError

    def __init__(self, assets={}):
        self.assets = assets
        if "ANIMATIONS" not in self.assets:
            self.assets["ANIMATIONS"] = {}
        self.cache = {}
        self.rotated_cache = {}
        self.outline_cache = {}
        self.fonts = {
            "default": pygame.font.SysFont("arial", 12)
        }
        self.animation_data = {}

    def __len__(self) -> int: return len(self.assets)
    def __iter__(self): return iter(self.assets)

    def get(self, img_type: str, angle: float = 0.0, sep="/", clamp_angle_internally=True, flip_x=False, alpha=255) -> pygame.Surface:
        if clamp_angle_internally:
            angle = clamp_number_to_range_steps(angle, -90, 270, AssetManager.roation_steps)

        do_flip = 90 < angle < 270
        key = f"{angle}#{do_flip}#{alpha}#{img_type}"

        if key in self.cache:
            return self.cache[key]

        path_parts = img_type.split(sep)
        current_assets = self.assets

        for part in path_parts[:-1]:
            current_assets = current_assets[part]

        last_part = path_parts[-1]

        result: pygame.Surface = None
        result_list: list[pygame.Surface] = []
        if isinstance(current_assets, dict):
            _result = current_assets[last_part].copy()
            if isinstance(_result, dict):
                result = _result
            elif isinstance(_result, list):
                result_list = _result
            elif isinstance(_result, pygame.Surface):
                result = _result
        elif isinstance(current_assets, list):
            if last_part.isdigit():
                result = current_assets[int(last_part)].copy()
            else:
                result_list = current_assets
        else:
            raise ValueError(f"Asset type for '{img_type}' is not valid.")

        if result_list:
            if do_flip:
                result_list = [pygame.transform.flip(s, False, True) for s in result_list]
            result_list = [pygame.transform.flip(s, flip_x, False) for s in result_list]
            result_list = [pygame.transform.rotate(s, angle) for s in result_list]
            [s.set_alpha(alpha) for s in result_list]

            self.cache[key] = result_list
            return result_list
        else:
            if do_flip:
                result = pygame.transform.flip(result, False, True)
            result = pygame.transform.flip(result, flip_x, False)
            result = pygame.transform.rotate(result, angle)
            result.set_alpha(alpha)
            return result

    def get2(self, img_type: str, angle: float = 0.0, sep="/", clamp_angle_internally=True, flip=False, alpha=255) -> pygame.Surface:
        """
        !!!!!!!!!!!!!!!! Angle is in degrees !!!!!!!!!!!!!!!!
        """
        # if angle:
        if clamp_angle_internally:
            angle = clamp_number_to_range_steps(angle, -90, 270, AssetManager.roation_steps)

        do_flip = 90 < angle < 270
        key = f"{angle}#{do_flip}#{alpha}"
        if img_type in self.rotated_cache:
            if key in self.rotated_cache[img_type]:
                return self.rotated_cache[img_type][key]

        path_parts = img_type.split(sep)
        current_assets = self.assets

        for part in path_parts[:-1]:
            current_assets = current_assets[part]

        last_part = path_parts[-1]

        result = ""
        if isinstance(current_assets, dict):
            result = current_assets[last_part]
        elif isinstance(current_assets, list):
            if last_part.isdigit():
                index = int(last_part)
                result = current_assets[index]
            else:
                result = current_assets[0].copy()
        else:
            raise ValueError(f"Asset type for '{img_type}' is not valid.")

        if do_flip:
            result = pygame.transform.flip(result, False, True)
        result = pygame.transform.rotate(result, angle)
        result.set_alpha(alpha)
        if img_type not in self.rotated_cache:
            self.rotated_cache[img_type] = {}
        self.rotated_cache[img_type][key] = result
        return result
        # else:
        #     # Check if result is cached
        #     if img_type in self.cache:
        #         if flip:
        #             return pygame.transform.flip(self.cache[img_type], True, False)
        #         return self.cache[img_type]

        #     path_parts = img_type.split(sep)
        #     current_assets = self.assets

        #     for part in path_parts[:-1]:
        #         current_assets = current_assets[part]

        #     last_part = path_parts[-1]

        #     # print(path_parts, current_assets)

        #     result = ""
        #     if isinstance(current_assets, dict):
        #         result = current_assets[last_part]
        #     elif isinstance(current_assets, list):
        #         if last_part.isdigit():
        #             index = int(last_part)
        #             result = current_assets[index].copy()
        #         else:
        #             result = current_assets[0].copy()
        #     else:
        #         raise ValueError(f"Asset type for '{img_type}' is not valid.")

        #     result.set_alpha(alpha)
        #     self.cache[img_type] = result
        #     if flip:
        #         return pygame.transform.flip(self.cache[img_type], True, False)
        #     return result

    def add(self, img_type: str, image: pygame.Surface, sep="/") -> None:
        path_parts = img_type.split(sep)
        current_assets = self.assets

        for part in path_parts[:-1]:
            if part not in current_assets:
                current_assets[part] = {}
            current_assets = current_assets[part]

        last_part = path_parts[-1]

        current_assets[last_part] = image

    def add_font(self, path: str, size: int) -> None:
        f = pygame.font.Font(path, size)
        self.fonts[f"{path};{size}"] = f

    def render_text(self, text: str, color=(255, 255, 255), font_name: str = "default") -> pygame.Surface:
        return self.fonts[font_name].render(text, False, color)

    def get_outlined(self, type: str, angle=0, outline_color=(255, 0, 0), outline_only=False) -> pygame.Surface:
        """
        !!!!!!!!!!!!!!!! Angle is in degrees !!!!!!!!!!!!!!!!
        """
        surf = self.get(type, angle=angle)
        key = f"{type};;;{angle};;;OUTLINED;;;{outline_color};;;{outline_only}"
        if key in self.outline_cache:
            return self.outline_cache[key]

        convolution_mask = pygame.mask.Mask((3, 3), fill=True)
        mask = pygame.mask.from_surface(surf)

        surface_outline = mask.convolve(convolution_mask).to_surface(setcolor=outline_color, unsetcolor=surf.get_colorkey())

        if outline_only:
            mask_surface = mask.to_surface()
            mask_surface.set_colorkey((0, 0, 0))

            surface_outline.blit(mask_surface, (1, 1))
        else:
            surface_outline.blit(surf, (1, 1))
            surface_outline.set_colorkey((0, 0, 0))

        self.outline_cache[key] = surface_outline
        return surface_outline

    def _add_animation_states(self, states: dict[str, list[pygame.Surface]], animation_id: str) -> None:
        if animation_id not in self.assets["ANIMATIONS"]:
            self.assets["ANIMATIONS"][animation_id] = {}
        for state_name, state_images in states.items():
            self.assets["ANIMATIONS"][animation_id][state_name] = state_images

    def get_total_animation_data(self, id: str) -> dict:
        return self.animation_data[id]

    def get_animation_frame_data(self, id: str, state: str) -> list[float]:
        return self.animation_data[id]["states_speeds"][state]

    def get_animation_offset_data(self, id: str, state: str) -> list[tuple]:
        return self.animation_data[id]["states_offsets"][state]

    def get_animation_looping(self, id: str, state: str) -> bool:
        return self.animation_data[id]["states_looping"][state]

    def get_animation_number_of_frames(self, id: str, state: str) -> int:
        return len(self.animation_data[id]["states_speeds"][state])

    def load_animation(self, path: str) -> str:
        # Läd animation und gibt die default state zurück.
        states = {}
        states_speeds = {}
        states_looping = {}
        states_offsets = {}
        default_state = ""
        animation_id = ""

        with open(path, "r") as f:
            data = json.load(f)

            colorkey = data["colorkey"]
            default_path = data["file_path"]
            same_dir = data["samedir"]
            default_state = data["default"]
            animation_id = data["id"]

            for animation_state, state_data in data["animations"].items():
                if same_dir:
                    states[animation_state] = load_images(default_path, colorkey=colorkey)
                else:
                    states[animation_state] = load_images(f"{default_path}/{animation_state}", colorkey=colorkey)

                states_speeds[animation_state] = state_data["frames"]
                states_looping[animation_state] = state_data["loop"]
                states_offsets[animation_state] = state_data["offset"]

        self.animation_data[animation_id] = {
            "states_speeds":  states_speeds,
            "states_looping": states_looping,
            "states_offsets": states_offsets,
        }
        self._add_animation_states(states, animation_id)

        return default_state


am = AssetManager()
