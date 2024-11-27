import collections
import collections.abc
import pygame
from pygame import FRect, Rect, Surface
import enum
from typing import Literal

from Scripts.utils_math import clamp

pygame.init()
pygame.font.init()


class WidgetStates(enum.Enum):
    HOVER_ENTER = enum.auto()
    HOVER = enum.auto()
    HOVER_EXIT = enum.auto()
    NO_HOVERED = enum.auto()


STATES_CONSIDERED_HOVERED = {WidgetStates.HOVER_ENTER, WidgetStates.HOVER}


class Widget:
    # default_font = pygame.font.SysFont("arial", 16)
    default_font = pygame.font.Font("assets/fonts/Retro Gaming.ttf", 11)
    _total_id = 0

    def __init__(self, parent: "Widget", pos: tuple, size: tuple) -> None:
        self._parent: Container | Widget | None = parent
        if self._parent:
            self._parent.add(self)
        self._selected = False

        self.pos = pos
        self.size = size
        self._state = WidgetStates.NO_HOVERED
        self._last_state = self._state = WidgetStates.NO_HOVERED

        self._id = Widget._total_id
        Widget._total_id = Widget._total_id + 1

        print("__init__", type(self), self.pos, self.size)

    @property
    def rect(self) -> Rect:
        return Rect(*self.pos, *self.size)

    @property
    def abs_rect(self) -> Rect:
        if self._parent:
            return Rect(self.pos[0] + self._parent.abs_rect.x,
                        self.pos[1] + self._parent.abs_rect.y,
                        *self.size)
        else:
            return self.rect

    @property
    def draw_rect(self):
        if self._parent and not isinstance(self._parent, Container):
            return Rect(self.pos[0] + self._parent.draw_rect.x,
                        self.pos[1] + self._parent.draw_rect.y,
                        *self.size)
        else:
            return self.rect

    @property
    def hovered(self):
        return True if self._state in STATES_CONSIDERED_HOVERED else False

    def select(self):
        self._selected = True

    def deselect(self):
        self._selected = False

    def select_toggle(self):
        self._selected = not self._selected

    def render(self, surf: Surface, debug=False):
        raise NotImplementedError

    def _render_debug(self, surf):
        pygame.draw.rect(surf, (255, 255, 0), self.draw_rect, 1)

    def on_click(self, **kwargs): raise NotImplementedError
    def on_release(self, **kwargs): raise NotImplementedError
    def on_hold(self, **kwargs): raise NotImplementedError

    def _mouse_collides_rect(self, mouse_pos: tuple):
        if type(self._parent) == Container:
            return self.abs_rect.collidepoint(mouse_pos[0] * self._parent._scale, mouse_pos[1] * self._parent._scale)
        return self.abs_rect.collidepoint(*mouse_pos)

    def update(self, mouse_pos: tuple, dt: float, **kwargs):
        self._last_state = self._state
        if self._mouse_collides_rect(mouse_pos):
            if self._state == WidgetStates.NO_HOVERED:
                self._state = WidgetStates.HOVER_ENTER
            elif self._state == WidgetStates.HOVER_ENTER or self._state == WidgetStates.HOVER:
                self._state = WidgetStates.HOVER
        else:
            if self._state == WidgetStates.HOVER or self._state == WidgetStates.HOVER_ENTER:
                self._state = WidgetStates.HOVER_EXIT
            else:
                self._state = WidgetStates.NO_HOVERED

        mb_just_pressed = pygame.mouse.get_just_pressed()
        mb_just_released = pygame.mouse.get_just_released()
        mb_pressed = pygame.mouse.get_pressed()
        if mb_just_pressed[0]:
            self.on_click(**kwargs)
        elif mb_pressed[0]:
            self.on_hold(**kwargs)
        elif mb_just_released[0]:
            self.on_release(**kwargs)


class Container(Widget):
    def __init__(self, parent: "Widget", pos: tuple, size: tuple, scale: float = 1.) -> None:
        super().__init__(parent, pos, size)

        self._elements: list[Widget] = []

        self._area = Surface(size)
        self._scale = scale

        self._render_img = make_9slice("assets/ui/9slice-button-pressed.png", self.size, (7, 7))

    def add(self, element: Widget):
        element._parent = self
        self._elements.append(element)

    def on_click(self, **kwargs): return
    def on_hold(self, **kwargs): return
    def on_release(self, **kwargs): return

    def update(self, mouse_pos, dt, **kwargs):
        super().update(mouse_pos, dt, **kwargs)
        for e in self._elements:
            e.update(mouse_pos, dt, keys=get_keys(), mouse_data=get_mouse(), ** kwargs)

    def render(self, surf: Surface, debug=False):
        self._area.fill((0, 0, 0))
        self._area.blit(self._render_img, (0, 0))
        for e in self._elements:
            e.render(self._area, debug=False)
        surf.blit(self._area, self.pos)
        if debug:
            self._render_debug(surf)


class Button(Widget):
    def __init__(self, parent: "Widget", pos, size, text: str = None, on_click_func: collections.abc.Callable = None):
        super().__init__(parent, pos, size)

        self._on_click_func = on_click_func if on_click_func else None

        self._img_default = make_9slice("assets/ui/9slice-button-default.png", (self.size), (7, 7))
        self._img_pressed = make_9slice("assets/ui/9slice-button-pressed.png", (self.size), (7, 7))
        self._img_focused = make_9slice("assets/ui/9slice-button-focused.png", (self.size), (7, 7))
        self._render_img = self._img_default

        self._held_down = False

        self.text = text if text else "None"

    def on_click(self, **kwargs):
        if not self.hovered:
            return
        if self._on_click_func:
            self._on_click_func()
        self.select()
        print("button clicked.")

    def on_hold(self, **kwargs):
        if not self.hovered and not self._selected:
            return

        self._held_down = True
        self._render_img = self._img_pressed

    def on_release(self, **kwargs):
        self.deselect()

    def update(self, mouse_pos, dt, **kwargs):
        self._held_down = False
        self._render_img = self._img_default
        super().update(mouse_pos, dt, **kwargs)

    def render(self, surf: Surface, debug=False):
        # pygame.draw.rect(surf, (50, 50, 50), self.draw_rect)
        surf.blit(self._render_img, self.draw_rect)

        fs = Widget.default_font.render(self.text, False, (255, 255, 255))
        r = self.draw_rect
        p = (
            r.centerx - fs.width / 2,
            r.centery - fs.height / 2 - (-0 if self._held_down else 2)
        )
        surf.blit(fs, p)
        if debug:
            self._render_debug(surf)
        # print("render", type(self))


class CheckBox(Widget):
    def __init__(self, pos, size):
        super().__init__(pos, size)

        self._ticked = False

    def _tick(self): self._ticked = not self._ticked

    def on_click(self, **kwargs):
        if self.hovered:
            self._tick()

    def on_hold(self, **kwargs): return
    def on_release(self, **kwargs): return

    def render(self, surf: Surface):
        if self._ticked:
            pygame.draw.rect(surf, [0, 255, 0], self.draw_rect)
        else:
            pygame.draw.rect(surf, [255, 0, 0], self.draw_rect)
        self._render_debug(surf)


class Label(Widget):
    def __init__(self, parent: "Widget", pos: tuple, size: tuple, text: str = "None", font: pygame.Font = None, text_callable: collections.abc.Callable = None) -> None:
        super().__init__(parent, pos, size)
        self._text = text

        self.font = font if font else self.default_font
        self._text_callable = text_callable

        print(self._text)
        self.font_surf = self.font.render(self._text, False, (255, 255, 255))
        self._max_counter = 0
        if self.font_surf.width > self.size[0]:
            self._max_counter = self.font_surf.width - self.size[0] + 50
        self._counter = 0.

        self._img_default = make_9slice("assets/ui/9slice-button-default.png", (self.size), (7, 7))
        self._render_img = self._img_default

    @property
    def text(self): return self._text

    @text.setter
    def text(self, text: str):
        self._text = str(text)
        self.font_surf = self.font.render(self.text, False, (255, 255, 255))
        self._max_counter = 0
        if self.font_surf.width > self.size[0]:
            self._max_counter = self.font_surf.width - self.size[0] + 50
        self._counter = 0.

    def on_click(self, **kwargs): return
    def on_hold(self, **kwargs): return
    def on_release(self, **kwargs): return

    def update(self, mouse_pos, dt, **kwargs):
        super().update(mouse_pos, dt, **kwargs)
        if self.hovered and self._max_counter:
            self._counter += 25 * dt
            if self._counter > self._max_counter:
                self._counter = 0.
        else:
            self._counter = 0.

        if self._text_callable:
            self.text = self._text_callable()
        # print(self._text)

    def render(self, surf: Surface, debug=False):

        # pygame.draw.rect(surf, (50, 50, 50), self.draw_rect)
        surf.blit(self._render_img, self.draw_rect)
        temp_surf = pygame.Surface(self.size)
        temp_surf.set_colorkey((0, 0, 0))
        temp_surf.blit(self.font_surf, (-self._counter, 0))
        surf.blit(temp_surf, self.draw_rect)

        if debug:
            self._render_debug(surf)


class Section(Label):
    def __init__(self, pos: tuple, size: tuple, text: str, font: pygame.Font = None, widgets: list[Widget] = [], collapsed=False) -> None:
        super().__init__(pos, size, text, font)

        self._elements: list[Widget] = []
        for w in widgets:
            self.add(w)

        self._collapsed = collapsed

    def add(self, *widgets):
        for w in widgets:
            w._parent = self
            self._elements.append(w)

    def _collapse(self):
        if self.hovered:
            self._collapsed = not self._collapsed

    def on_click(self, **kwargs): self._collapse()
    def on_hold(self, **kwargs): return
    def on_release(self, **kwargs): return

    def render(self, surf: Surface):
        super().render(surf)
        if not self._collapsed:
            for e in self._elements:
                e.render(surf)
        self._render_debug(surf)

    def update(self, mouse_pos, dt, **kwargs):
        super().update(mouse_pos, dt, **kwargs)
        if not self._collapsed:
            for e in self._elements:
                e.update(mouse_pos, dt, **kwargs)


class InputField(Widget):
    def __init__(self, pos: tuple, size: tuple, hint_text: str = "Hint text here", font: pygame.Font = None) -> None:
        super().__init__(pos, size)

        self.font = font if font else self.default_font

        self._hint_text = hint_text
        self._text = ""
        self._cursor_pos = 0

        self._selected = False

    def select(self):
        self._selected = not self._selected

    def on_click(self, **kwargs):
        if self.hovered:
            self.select()
        elif not self.hovered and self._selected:
            self.deselect()

    def on_hold(self, **kwargs): return
    def on_release(self, **kwargs): return

    def update(self, mouse_pos: tuple, dt: float, **kwargs):
        super().update(mouse_pos, dt, **kwargs)

        if self._selected:
            keys_pressed = kwargs["keys"]["just_pressed"]
            mods = kwargs["keys"]["mods"]
            keyerror = False
            for key in latin_keys_navigation:
                if keys_pressed[key]:
                    print(key)
                    if key == pygame.K_LEFT:
                        self._cursor_pos = max(0, self._cursor_pos - 1)
                    elif key == pygame.K_RIGHT:
                        self._cursor_pos = min(len(self._text), self._cursor_pos + 1)
                    elif key == pygame.K_UP:
                        self._cursor_pos = len(self._text)
                    elif key == pygame.K_DOWN:
                        self._cursor_pos = 0
            for key in latin_keys:
                if not keys_pressed[key]:
                    continue
                str_key = None
                if shift_pressed(mods):
                    try:
                        str_key = keys_with_shift[key]
                    except KeyError:
                        keyerror = True
                elif ctrl_pressed(mods):
                    continue
                elif alt_gr_pressed(mods):
                    try:
                        str_key = keys_with_altgr[key]
                    except KeyError:
                        keyerror = True
                else:
                    str_key = keys_without_mod[key]
                if not keyerror:
                    self._text = self._text[:self._cursor_pos] + str_key + self._text[self._cursor_pos:]
                    self._cursor_pos += 1
            for key in latin_keys_functional:
                if keys_pressed[key]:
                    if key == pygame.K_BACKSPACE:
                        self._text = self._text[:self._cursor_pos - 1] + self._text[self._cursor_pos:]
                        self._cursor_pos = max(0, self._cursor_pos - 1)
                    elif key == pygame.K_SPACE:
                        self._text += " "
                        self._cursor_pos += 1
                    elif key == pygame.K_DELETE:
                        # S = S[:Index] + S[Index + 1:]
                        self._text = self._text[:self._cursor_pos] + self._text[self._cursor_pos + 1:]
        # print(self._text, self._cursor_pos, pygame.key.get_mods())

    def render(self, surf: Surface):

        hint_surf = self.font.render(self._hint_text, False, (200, 200, 200))
        text_surf = self.font.render(self._text, False, (255, 255, 255))

        pygame.draw.rect(surf, (51, 92, 108), self.draw_rect)
        if not self._text:
            surf.blit(hint_surf, self.draw_rect)
        if self._selected:
            r = self.draw_rect
            clipped_text_surf = self.font.render(self._text[:self._cursor_pos], False, (255, 255, 255))
            pygame.draw.rect(surf, (200, 20, 20), [r.x + clipped_text_surf.width, r.y, 2, self.size[1]])
        surf.blit(text_surf, self.draw_rect)

        self._render_debug(surf)


class Slider(Widget):
    def __init__(self, parent: "Widget", pos, size, bounds: tuple, initial_percentage=0.5):
        super().__init__(parent, pos, size)

        self._percentage = initial_percentage
        self._bounds = bounds

        self._is_horizontal = True  # wenn nicht, dann ist der slider Vertikal
        if size[0] < size[1]:
            self._is_horizontal = False

        self._img_default = make_9slice("assets/ui/9slice-button-default.png", (self.size), (7, 7))
        self._img_pressed = make_9slice("assets/ui/9slice-button-pressed.png", (self.size), (7, 7))
        self._img_focused = make_9slice("assets/ui/9slice-button-focused.png", (self.size), (7, 7))
        self._render_img = self._img_default

        self.cursor_width = 10
        self._cursorimg_default = make_9slice("assets/ui/9slice-slidercursor-default.png", (self.cursor_width, self.size[1]), (5, 7))
        self._cursorimg_pressed = make_9slice("assets/ui/9slice-slidercursor-pressed.png", (self.cursor_width, self.size[1]), (5, 7))
        self._cursorimg_focused = make_9slice("assets/ui/9slice-slidercursor-focused.png", (self.cursor_width, self.size[1]), (5, 7))
        self._cursor_img = self._cursorimg_default

        self._held_down = False

    @property
    def min(self): return self._bounds[0]
    @property
    def max(self): return self._bounds[1]
    @property
    def val(self): return clamp(self.min, self.min + (abs(self.max) + abs(self.min)) * self._percentage, self.max)
    @property
    def val_inverse(self): return clamp(self.min, self.min + (abs(self.max) + abs(self.min)) * (1 - self._percentage), self.max)

    def update(self, mouse_pos, dt, **kwargs):
        self._held_down = False
        self._render_img = self._img_default
        self._cursor_img = self._cursorimg_default
        super().update(mouse_pos, dt, **kwargs)

    def _move_val(self, mouse_pos):
        mx, my = mouse_pos
        if self._parent:
            mx = int(mx * self._parent._scale)
            my = int(my * self._parent._scale)
        if self._is_horizontal:
            relx = mx - self.abs_rect.left
            self._percentage = relx / self.size[0]
        else:
            rely = my - self.abs_rect.top
            self._percentage = rely / self.size[1]

    def on_click(self, **kwargs):
        if self.hovered:
            self._move_val(kwargs["mouse_data"]["pos"])
            self.select()

    def on_hold(self, **kwargs):
        if self.hovered and self._selected:
            self._move_val(kwargs["mouse_data"]["pos"])
            self._held_down = True
            self._render_img = self._img_pressed
            self._cursor_img = self._cursorimg_pressed
        elif self._selected:
            self._move_val(kwargs["mouse_data"]["pos"])
            self._held_down = True
            self._render_img = self._img_pressed
            self._cursor_img = self._cursorimg_pressed

    def on_release(self, **kwargs):
        self.deselect()

    def render(self, surf: Surface, debug=False):
        # pygame.draw.rect(surf, (50, 50, 50), self.draw_rect)
        surf.blit(self._render_img, self.draw_rect)
        if self._is_horizontal:
            # pygame.draw.rect(surf, (255, 0, 255), [
            #     clamp(self.draw_rect.x, self.draw_rect.x + self.size[0] * self._percentage, self.draw_rect.x + self.size[0] - self.cursor_width),
            #     self.draw_rect.y,
            #     self.cursor_width,
            #     self.size[1]], 1)
            surf.blit(self._cursor_img, [
                clamp(self.draw_rect.x, self.draw_rect.x + self.size[0] * self._percentage, self.draw_rect.x + self.size[0] - self.cursor_width),
                self.draw_rect.y,
                self.cursor_width,
                self.size[1]])
        else:
            pygame.draw.rect(surf, (255, 0, 255), [
                self.draw_rect.x,
                clamp(self.draw_rect.y, self.draw_rect.y + self.size[1] * self._percentage, self.draw_rect.y + self.size[1] - self.cursor_width),
                self.size[0],
                self.cursor_width], 1)
        if debug:
            self._render_debug(surf)


def get_mouse_buttons() -> tuple: return pygame.mouse.get_pressed()


latin_keys = [
    # Latin alphabet (a-z)
    pygame.K_a, pygame.K_b, pygame.K_c, pygame.K_d, pygame.K_e, pygame.K_f, pygame.K_g,
    pygame.K_h, pygame.K_i, pygame.K_j, pygame.K_k, pygame.K_l, pygame.K_m, pygame.K_n,
    pygame.K_o, pygame.K_p, pygame.K_q, pygame.K_r, pygame.K_s, pygame.K_t, pygame.K_u,
    pygame.K_v, pygame.K_w, pygame.K_x, pygame.K_y, pygame.K_z,

    # Numbers (0-9)
    pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
    pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9,

    # Special symbols
    pygame.K_PLUS,  # +
    pygame.K_MINUS,  # -
    pygame.K_COMMA,  # ,
    pygame.K_PERIOD,  # .
    pygame.K_LESS,  # <
]
latin_keys_navigation = [
    pygame.K_UP,
    pygame.K_RIGHT,
    pygame.K_LEFT,
    pygame.K_DOWN,
]
latin_keys_functional = [
    pygame.K_BACKSPACE,
    pygame.K_SPACE,
    pygame.K_DELETE
]

keys_without_mod = {
    pygame.K_a: 'a',
    pygame.K_b: 'b',
    pygame.K_c: 'c',
    pygame.K_d: 'd',
    pygame.K_e: 'e',
    pygame.K_f: 'f',
    pygame.K_g: 'g',
    pygame.K_h: 'h',
    pygame.K_i: 'i',
    pygame.K_j: 'j',
    pygame.K_k: 'k',
    pygame.K_l: 'l',
    pygame.K_m: 'm',
    pygame.K_n: 'n',
    pygame.K_o: 'o',
    pygame.K_p: 'p',
    pygame.K_q: 'q',
    pygame.K_r: 'r',
    pygame.K_s: 's',
    pygame.K_t: 't',
    pygame.K_u: 'u',
    pygame.K_v: 'v',
    pygame.K_w: 'w',
    pygame.K_x: 'x',
    pygame.K_y: 'y',
    pygame.K_z: 'z',

    pygame.K_0: '0',
    pygame.K_1: '1',
    pygame.K_2: '2',
    pygame.K_3: '3',
    pygame.K_4: '4',
    pygame.K_5: '5',
    pygame.K_6: '6',
    pygame.K_7: '7',
    pygame.K_8: '8',
    pygame.K_9: '9',

    pygame.K_MINUS: '-',
    pygame.K_PLUS: '+',
    pygame.K_COMMA: ',',
    pygame.K_PERIOD: '.',
    pygame.K_LESS: '<',
}
keys_with_shift = {
    pygame.K_1: '!',
    pygame.K_2: '"',
    pygame.K_3: '§',
    pygame.K_4: '$',
    pygame.K_5: '%',
    pygame.K_6: '&',
    pygame.K_7: '/',
    pygame.K_8: '(',
    pygame.K_9: ')',
    pygame.K_0: '=',

    pygame.K_a: 'A',
    pygame.K_b: 'B',
    pygame.K_c: 'C',
    pygame.K_d: 'D',
    pygame.K_e: 'E',
    pygame.K_f: 'F',
    pygame.K_g: 'G',
    pygame.K_h: 'H',
    pygame.K_i: 'I',
    pygame.K_j: 'J',
    pygame.K_k: 'K',
    pygame.K_l: 'L',
    pygame.K_m: 'M',
    pygame.K_n: 'N',
    pygame.K_o: 'O',
    pygame.K_p: 'P',
    pygame.K_q: 'Q',
    pygame.K_r: 'R',
    pygame.K_s: 'S',
    pygame.K_t: 'T',
    pygame.K_u: 'U',
    pygame.K_v: 'V',
    pygame.K_w: 'W',
    pygame.K_x: 'X',
    pygame.K_y: 'Y',
    pygame.K_z: 'Z',

    pygame.K_PLUS: '*',  # Shift + +
    pygame.K_MINUS: '_',  # Shift + -
    pygame.K_COMMA: ';',  # Shift + ,
    pygame.K_PERIOD: ':',  # Shift + .
    pygame.K_LESS: '>',  # Shift + <
}
keys_with_altgr = {
    pygame.K_q: '@',  # Alt-gr + Q
    pygame.K_e: '€',  # Alt-gr + E (Euro symbol)
    pygame.K_8: '[',  # Alt-gr + 8
    pygame.K_9: ']',  # Alt-gr + 9
    pygame.K_7: '{',  # Alt-gr + 7
    pygame.K_0: '}',  # Alt-gr + 0
    pygame.K_LESS: '|'  # Alt-gr + \
}


def get_keys():
    return {
        "pressed": pygame.key.get_pressed(),
        "just_pressed": pygame.key.get_just_pressed(),
        "just_released": pygame.key.get_just_released(),
        "mods": pygame.key.get_mods()
    }


def get_mouse():
    return {
        "pos": pygame.mouse.get_pos(),
        "rel": pygame.mouse.get_rel(),
        "pressed": pygame.mouse.get_pressed(),
        "just_pressed": pygame.mouse.get_just_pressed(),
        "just_released": pygame.mouse.get_just_released(),
    }


def shift_pressed(mods: int) -> bool:
    return mods == pygame.KMOD_SHIFT or mods == pygame.KMOD_LSHIFT or mods == pygame.KMOD_RSHIFT


def ctrl_pressed(mods: int) -> bool:
    return mods == pygame.KMOD_CTRL or mods == pygame.KMOD_LCTRL or mods == pygame.KMOD_RCTRL


def alt_pressed(mods: int) -> bool:
    return mods == pygame.KMOD_ALT or mods == pygame.KMOD_LALT or mods == pygame.KMOD_RALT


def alt_gr_pressed(mods: int) -> bool:
    return mods == pygame.KMOD_RALT or mods == pygame.KMOD_MODE


def load_image(path):
    i = pygame.image.load(path)
    i.set_colorkey((0, 0, 0))
    return i


# @functools.lru_cache(max_size=16)
def make_9slice(path: str, size: tuple, slice_size: tuple, scale=0) -> Surface:
    base_img = load_image(path)
    surf = Surface(size)
    surf.set_colorkey((0, 0, 0))
    m_size = size[0] - slice_size[0] * 2, size[1] - slice_size[1] * 2

    print("make_9slice called", size, scale, slice_size, m_size, base_img.get_size())

    if slice_size[0] * 3 > size[0]:
        # nur die kanten, mitte auslassen.
        surf.blit(base_img.subsurface([0, 0, slice_size[0], slice_size[1]]), (0, 0))
        surf.blit(base_img.subsurface([slice_size[0], 0, slice_size[0], slice_size[1]]), (size[0] - slice_size[0], 0))
        surf.blit(base_img.subsurface([0, slice_size[1] * 2, slice_size[0], slice_size[1]]), (0, size[1] - slice_size[1]))
        surf.blit(base_img.subsurface([slice_size[0], slice_size[1] * 2, slice_size[0], slice_size[1]]), (size[0] - slice_size[0], size[1] - slice_size[1]))

        part_left = base_img.subsurface([0, slice_size[1], slice_size[0], slice_size[1]])
        part_right = base_img.subsurface([slice_size[0], slice_size[1], slice_size[0], slice_size[1]])

        surf.blit(pygame.transform.scale(part_left, (slice_size[0], m_size[1])), (0, slice_size[1]))
        surf.blit(pygame.transform.scale(part_right, (slice_size[0], m_size[1])), (size[0] - slice_size[0], slice_size[1]))

    else:
        surf.blit(base_img.subsurface([0, 0, slice_size[0], slice_size[1]]), (0, 0))
        surf.blit(base_img.subsurface([slice_size[0] * 2, 0, slice_size[0], slice_size[1]]), (size[0] - slice_size[0], 0))
        surf.blit(base_img.subsurface([0, slice_size[1] * 2, slice_size[0], slice_size[1]]), (0, size[1] - slice_size[1]))
        surf.blit(base_img.subsurface([slice_size[0] * 2, slice_size[1] * 2, slice_size[0], slice_size[1]]), (size[0] - slice_size[0], size[1] - slice_size[1]))

        part_top = base_img.subsurface([slice_size[0], 0, slice_size[0], slice_size[1]])
        part_bottom = base_img.subsurface([slice_size[0], slice_size[1] * 2, slice_size[0], slice_size[1]])
        part_middle = base_img.subsurface([slice_size[0], slice_size[1], slice_size[0], slice_size[1]])
        part_left = base_img.subsurface([0, slice_size[1], slice_size[0], slice_size[1]])
        part_right = base_img.subsurface([slice_size[0] * 2, slice_size[1], slice_size[0], slice_size[1]])

        surf.blit(pygame.transform.scale(part_top, (m_size[0], slice_size[1])), (slice_size[0], 0))
        surf.blit(pygame.transform.scale(part_bottom, (m_size[0], slice_size[1])), (slice_size[0], size[1] - slice_size[1]))
        surf.blit(pygame.transform.scale(part_left, (slice_size[0], m_size[1])), (0, slice_size[1]))
        surf.blit(pygame.transform.scale(part_right, (slice_size[0], m_size[1])), (size[0] - slice_size[0], slice_size[1]))
        surf.blit(pygame.transform.scale(part_middle, (m_size)), (slice_size[0], slice_size[1]))

    if scale:
        surf = pygame.transform.scale(surf, (surf.width * scale, surf.height * scale))
    return surf


controller_mapping = {
    "xbox": {
        "axis": {
            # -1 to 1. -1 nach links, 1 nach rechts
            0: "topleft-axis horizontal",
            1: "topleft-axis vertical",
            2: "bottomright-axis horizontal",
            3: "bottomright-axis vertical",
            4: "lt",
            5: "rt",
        },
        "buttons": {
            0: "a",
            1: "b",
            2: "x",
            3: "y",
            4: "lb",
            5: "rb",
            6: "unterm xbox symbol links",
            7: "unterm xbox symbol rechts",
            8: "topleft-axis drücken",
            9: "bottomright-axis drücken",
            10: "xbox symbol",
            11: "uterm xbox symbol mitte",
            12: "?",
            13: "?",
            14: "?",
            15: "?",
        },
        "hats": {
            0: "das kreuz zwischen den joysticks unten links."
        }
    }
}


def make_joystick_name(joystick: pygame.joystick.JoystickType) -> str:
    return joystick.get_name() + "////" + joystick.get_guid()


def save_joystickmapping(joystick: pygame.joystick.JoystickType, mapping: dict) -> None:
    import json
    JOYSTICK_MAPPING_SAVE_PATH = "data/joystick/saves.json"
    key = make_joystick_name(joystick)

    data = ""
    with open(JOYSTICK_MAPPING_SAVE_PATH, "r+")as f:
        data = json.loads(f)

    data[key] = mapping

    with open(JOYSTICK_MAPPING_SAVE_PATH, "w") as f:
        f.write(json.dumps(data))


class Input:

    BUTTON_A = 0
    BUTTON_B = 1
    BUTTON_X = 2
    BUTTON_Y = 3
    BUTTON_LB = 4
    BUTTON_RB = 5
    BUTTON_LEFT_UNDER_XBOX_SYMBOL = 6
    BUTTON_RIGHT_UNDER_XBOX_SYMBOL = 7
    BUTTON_LEFT_JOYSTICK = 8
    BUTTON_RIGHT_JOYSTICK = 9
    BUTTON_XBOX_SYMBOL = 10
    BUTTON_MIDDLE_UNDER_XBOX_SYMBOL = 11

    DEFAULT_MAPPINGS = {
        "move_left": {
            "keyboard": [(pygame.KEYDOWN, pygame.K_a), (pygame.KEYDOWN, pygame.K_LEFT)],
            "controller": [(pygame.JOYAXISMOTION, 0, -1)]  # left joystick (axis 0, direction -1 -> left, negative)
        },
        "move_right": {
            "keyboard": [(pygame.KEYDOWN, pygame.K_d), (pygame.KEYDOWN, pygame.K_RIGHT)],
            "controller": [(pygame.JOYAXISMOTION, 0, 1)]  # left joystick (axis 0, direction 1 -> right, postive)
        },
        "move_up": {
            "keyboard": [(pygame.KEYDOWN, pygame.K_w), (pygame.KEYDOWN, pygame.K_UP)],
            "controller": [(pygame.JOYAXISMOTION, 1, -1)]  # left joystick (axis 1, direction -1 -> left, negative)
        },
        "move_down": {
            "keyboard": [(pygame.KEYDOWN, pygame.K_s), (pygame.KEYDOWN, pygame.K_DOWN)],
            "controller": [(pygame.JOYAXISMOTION, 1, 1)]  # left joystick (axis 1, direction 1 -> right, postive)
        },
        "select": {
            "keyboard": [(pygame.KEYDOWN, pygame.K_SPACE)],
            "controller": [(pygame.JOYBUTTONDOWN, BUTTON_X)]
        },
        "back": {
            "keyboard": [(pygame.KEYDOWN, pygame.K_ESCAPE)],
            "controller": [(pygame.JOYBUTTONDOWN, BUTTON_B)]
        }
    }

    INPUT_EVENTS = {pygame.KEYDOWN, pygame.KEYUP,
                    pygame.JOYAXISMOTION, pygame.JOYBUTTONDOWN}

    def __init__(self, mappings: dict = None, joystick_deadzone: float = 0.1):
        self.mappings = mappings if mappings else self.DEFAULT_MAPPINGS
        self._events = collections.defaultdict(list)

        self.joysticks = {}
        self.joystick_deadzone = joystick_deadzone

    def clear(self):
        """Clear the event buffer."""
        self._events.clear()
        # print(self._events == collections.defaultdict(list))

    def add_event(self, event: pygame.event.Event):
        # print(event)
        if event.type in self.INPUT_EVENTS:
            self._events[event.type].append(event)
        # Handle hotplugging
        elif event.type == pygame.JOYDEVICEADDED:
            # This event will be generated when the program starts for every
            # joystick, filling up the list without needing to create them manually.
            joy = pygame.joystick.Joystick(event.device_index)
            self.joysticks[joy.get_instance_id()] = joy
            print(f"Joystick {joy.get_instance_id()} connected")
        elif event.type == pygame.JOYDEVICEREMOVED:
            if event.instance_id in self.joysticks:
                del self.joysticks[event.instance_id]
                print(f"Joystick {event.instance_id} disconnected")
            else:
                print(
                    f"Tried to disconnect Joystick {event.instance_id}, "
                    "but couldn't find it in the joystick list"
                )

    def is_joystick_in_deadzone(self, value: float) -> bool:
        return abs(value) < self.joystick_deadzone

    def _check_input(self, input_list: list, press_type: str) -> dict:
        allowed_input_types = []
        if press_type == "down":
            allowed_input_types = [pygame.KEYDOWN, pygame.JOYBUTTONDOWN]
        elif press_type == "up":
            allowed_input_types = [pygame.KEYUP, pygame.JOYBUTTONUP]

        for input_tuple in input_list:
            if input_tuple[0] == pygame.JOYAXISMOTION and self._events.get(pygame.JOYAXISMOTION):
                for event in self._events[pygame.JOYAXISMOTION]:
                    if event.axis == input_tuple[1] and not self.is_joystick_in_deadzone(event.value) and \
                            ((input_tuple[2] < 0 and event.value < 0) or (input_tuple[2] > 0 and event.value > 0)):
                        return {"instance_id": event.instance_id, "joy": event.joy, "value": event.value}
            elif input_tuple[0] in allowed_input_types:
                if self._events.get(pygame.JOYBUTTONDOWN):
                    for event in self._events[pygame.JOYBUTTONDOWN]:
                        if event.button == input_tuple[1]:
                            return {"instance_id": event.instance_id, "joy": event.joy}
                elif self._events.get(pygame.KEYDOWN):
                    for event in self._events[pygame.KEYDOWN]:
                        if event.key == input_tuple[1]:
                            return {"key": event.key}
        return {}

    def event_occurred(self, event_type: str, press_type: Literal["down", "hold", "up"] = "down"):
        keyboard_inputs = self.mappings[event_type]["keyboard"]
        controller_inputs = self.mappings[event_type]["controller"]

        kb_result = self._check_input(keyboard_inputs, press_type)
        cb_result = self._check_input(controller_inputs, press_type)

        # print(event_type, press_type, kb_result, cb_result)
        if kb_result or cb_result:
            return {"keyboard": kb_result, "controller": cb_result}
        else:
            return {}
