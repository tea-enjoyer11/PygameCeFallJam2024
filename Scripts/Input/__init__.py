import typing
import pygame
import dataclasses

import Scripts.CONFIG as CFG


class ButtonInput:
    def match(self, event: pygame.Event) -> bool:
        raise NotImplementedError

    def pressed(self, event: pygame.Event) -> bool:
        raise NotImplementedError


@dataclasses.dataclass(frozen=True, slots=True)
class KeyPress(ButtonInput):
    key: int
    just_down: bool = False

    def match(self, event):
        return event.type in (pygame.KEYDOWN, pygame.KEYUP) and event.key == self.key

    def pressed(self, event):
        return event.type == pygame.KEYDOWN

    def __hash__(self):
        return self.key

    def __repr__(self):
        return f"KeyPress {self.key}"


@dataclasses.dataclass(frozen=True, slots=True)
class JoyButtonPress(ButtonInput):
    button: int
    joy_id: int

    def match(self, event):
        # TODO aus irgendeinem Grund, der mir schleierhaft ist, funktioniert das nicht, obwohl joy_id mit event.joy, button mit event.button übereinstimmen.....
        # print(event, event.type, self.button, self.joy_id, pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP)
        # return (
        #     event in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP)
        #     and event.joy == self.joy_id
        #     and event.button == self.button
        # )
        if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONDOWN):
            # print(1)
            # print(self.button == event.button and self.joy_id == event.joy, self.button, event.button, type(self.button), type(event.button), self.joy_id, event.joy, type(self.joy_id), type(event.joy))
            if self.button == event.button and self.joy_id == event.joy:
                # print(2)
                return True
        # print(3)
        return False

    def pressed(self, event):
        return event.type == pygame.JOYBUTTONDOWN

    def __hash__(self):
        return (self.joy_id, self.button).__hash__()


@dataclasses.dataclass(frozen=True, slots=True)
class JoyAxis:
    axis: int
    joy_id: int
    reversed: bool = False
    deadzone: int = 0.1  # Jeder Wert unter, der diesen unterschreitet wird ignoriert.
    sensibility: float = 1.0  # Nützlich, wenn der Joystick nicht ganz zu +/-1 geht.

    def match(self, event: pygame.Event):
        return (
            event.type == pygame.JOYAXISMOTION
            and event.joy == self.joy_id
            and event.axis == self.axis
        )

    def value(self, event: pygame.Event):
        if abs(event.value) < self.deadzone:
            return 0
        scaled = min(event.value * self.sensibility, 1)
        if self.reversed:
            return -scaled
        return scaled


@dataclasses.dataclass(frozen=True, slots=True)
class MouseTrigger(ButtonInput):

    button: int

    def match(self, event) -> bool:
        return event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and event.button == self.button

    def pressed(self, event) -> bool:
        return event.type == pygame.MOUSEBUTTONDOWN

    def __hash__(self):
        return self.button


@dataclasses.dataclass(frozen=True, slots=True)
class JoyAxisTrigger(ButtonInput):
    """
    Für die trigger Dinger am Controller
    """

    axis: int
    threshold: float = -0.5
    above: bool = True  # Ob der Button gedrückt ist, wenn der Wert unter oder über threshold ist
    joy_id: int = 0

    def match(self, event) -> bool:
        return (
            event.type == pygame.JOYAXISMOTION
            and event.joy == self.joy_id
            and event.axis == self.axis
        )

    def pressed(self, event) -> bool:
        print(event.value)
        return self.above == (event.value > self.threshold)

    def __hash__(self):
        return (self.joy_id, self.axis).__hash__()


class Button:
    def __init__(self, *keys, toggle=False, just_down=False) -> None:
        self._keys: set[ButtonInput] = {KeyPress(key) if isinstance(key, int) else key for key in keys}

        self._pressed = dict()
        self._toggle = toggle
        self._toggled_state = False

        self._just_down = just_down
        self._just_pressed = False

    def actualize(self, events: list[pygame.Event]) -> None:
        # print(1, events)
        self._just_pressed = False
        old_pressed = sum(self._pressed.values()) > 0
        for event in events:
            for key in self._keys:
                if key.match(event):
                    if self._toggle:
                        if key.pressed(event):
                            self._toggled_state = not self._toggled_state
                        self._pressed[key] = self._toggled_state
                    else:
                        self._pressed[key] = key.pressed(event)
                elif isinstance(key, JoyButtonPress):
                    self._pressed[key] = False

        # print(sum(self._pressed.values()) > 0)
        if self._just_down and not old_pressed:
            if sum(self._pressed.values()) > 0:
                # print(1)
                self._just_pressed = True

    def __bool__(self) -> bool:
        # print(self._pressed)
        if self._just_down:
            return self._just_pressed
        else:
            return sum(self._pressed.values()) > 0

    def pressed(self) -> bool:
        # print(self.__bool__())
        return self.__bool__()


class Axis:
    """
    Stellt movement auf einer Achse dar.
    Zum Beispiel:
    Axis(
        (pygame.K_a, pygame.K_LEFT),
        (pygame.K_d, pygame.K_RIGHT),
        JoyAxis(1)
    )
    (pygame.K_a, pygame.K_LEFT) ist dann -1.
    (pygame.K_d, pygame.K_RIGHT) ist dann 1.
    JoyAxis(1) geht natürlich von -1 zu 1.
    """

    def __init__(self, negative, positive, *axes: typing.Sequence[JoyAxis]):
        """
        :param negative: keycode or list of keycodes
        :param positive: keycode or list of keycodes
        """
        self._axes: set[JoyAxis] = set(axes)

        self._negative = {(KeyPress(n) if isinstance(n, int) else n): False for n in negative}
        self._positive = {(KeyPress(p) if isinstance(p, int) else p): False for p in positive}

        self._key_value = 0
        self._axis_value = 0

    def actualize(self, events: list[pygame.Event]) -> None:
        axis_value = 0
        any_axis = False
        for event in events:
            for pos in self._positive:
                if pos.match(event):
                    self._positive[pos] = pos.pressed(event)
            for neg in self._negative:
                if neg.match(event):
                    self._negative[neg] = neg.pressed(event)
            for axis in self._axes:
                if axis.match(event):
                    val = axis.value(event)
                    if abs(val) > abs(axis_value):
                        axis_value = val
                    any_axis = True

        self._key_value = sum(self._positive.values()) - sum(self._negative.values())
        if any_axis:
            self._axis_value = axis_value

    @ property
    def value(self) -> int:
        return max(-1, min(self._key_value + self._axis_value, 1))

    @ property
    def value_key(self) -> int:
        return max(-1, min(self._key_value, 1))

    @ property
    def value_axis(self) -> int:
        return max(-1, min(self._axis_value, 1))

    def __bool__(self) -> bool:
        return bool(self._key_value + self._axis_value)


@ dataclasses.dataclass(slots=True)
class MouseLook:
    joy_id: int = 0
    sensitivity: float = 5.0
    deadzone: float = 0.1
    _x: int = CFG.RES[0]//2
    _y: int = CFG.RES[1]//2

    _cx: int = _x
    _cy: int = _y

    axis_x = Axis([], [], JoyAxis(2, joy_id=joy_id))
    axis_y = Axis([], [], JoyAxis(3, joy_id=joy_id))

    def update_from_mouse(self) -> None:
        r = pygame.mouse.get_rel()
        if r[0] or r[1]:
            self._x, self._y = pygame.mouse.get_pos()

    def update_from_joystick(self, events: list[pygame.Event]):
        self.axis_x.actualize(events)
        self.axis_y.actualize(events)

        x = self.axis_x.value * self.sensitivity
        y = self.axis_y.value * self.sensitivity

        set_mpos = False
        if abs(x) > self.deadzone:
            set_mpos = True
            self._x += x
        if abs(y) > self.deadzone:
            set_mpos = True
            self._y += y

        if set_mpos:
            pygame.mouse.set_pos(self.get_pos())

    def get_pos(self) -> tuple[int, int]:
        self._x = max(1, min(self._x, CFG.ORG_RES[0]-1))
        self._y = max(1, min(self._y, CFG.ORG_RES[1]-1))
        return (self._x, self._y)


@ dataclasses.dataclass(slots=True)
class MouseScroll:
    dir: int

    def match(self, event) -> bool:
        return event.type == pygame.MOUSEWHEEL

    def pressed(self, event) -> bool:
        if self.dir < 0:
            return event.y < 0
        if self.dir > 0:
            return event.y > 0

    def __hash__(self):
        return self.dir


class ScrollAxis:
    def __init__(self):
        self._value = 0

    @ property
    def value(self) -> int: return self._value

    def actualize(self, events: list[pygame.Event]):
        self._value = 0
        for event in events:
            if event.type == pygame.MOUSEWHEEL:
                self._value = event.y


class InputManager(dict):
    def __init__(self) -> None:
        self.mouse_look = MouseLook()

    def update(self, events: list[pygame.Event]) -> None:
        self.mouse_look.update_from_mouse()
        for inp in self.values():
            inp.actualize(events)
        self.mouse_look.update_from_joystick(events)

    def get_pos(self, downscale_factor=None) -> tuple[int, int]:
        if not downscale_factor:
            downscale_factor = CFG.DOWNSCALE_FACTOR
        return (self.mouse_look.get_pos()[0] / downscale_factor, self.mouse_look.get_pos()[1] / downscale_factor)


if __name__ == "__main__":
    pygame.init()
    pygame.joystick.init()

    input_manager = InputManager()

    input_manager["hmove"] = Axis((KeyPress(pygame.K_a), pygame.K_LEFT), (pygame.K_d, pygame.K_RIGHT), JoyAxis(2, 0))
    print(input_manager["hmove"].__dict__)

    scr = pygame.display.set_mode((600, 600))
    clock = pygame.time.Clock()

    pos = [300, 300]
    speed = 2

    joysticks = {}
    run = True
    while run:
        dt = clock.tick(30) * .001
        events = pygame.event.get()
        input_manager.update(events)
        for event in events:
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                run = False

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

        print(bool(input_manager["hmove"]), input_manager["hmove"].value)

        pygame.draw.circle(scr, "red", pos, 15)

        pygame.display.flip()
    pygame.quit()
