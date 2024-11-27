from typing import Callable, Any
import time


class TimerManager:
    timers: list["Timer"] = []

    @staticmethod
    def update() -> None:
        [t.update() for t in TimerManager.timers]

    @staticmethod
    def add(timer: "Timer") -> None:
        TimerManager.timers.append(timer)

    @staticmethod
    def extend(timers: list["Timer"]) -> None:
        TimerManager.timers.extend(timers)

    @staticmethod
    def remove(timer: "Timer") -> None:
        if timer in TimerManager.timers:
            TimerManager.timers.remove(timer)


class Timer:
    def __init__(self, duration: float, autostart=False, start_on_end=False) -> None:
        self.duration = duration
        self.start_time = .0
        self.paused = .0
        self.ended = False
        self.just_ended = False

        if autostart:
            self.start()
        if start_on_end:
            self.ended = True
            self.just_ended = True

        TimerManager.add(self)

    def update(self):
        self.just_ended = False
        if self.start_time and not self.paused:
            if time.perf_counter() - self.start_time >= self.duration:
                self._end()

    def reset(self):
        self.start_time = time.perf_counter()

    def start(self):
        if self.start_time:
            return
        self.start_time = time.perf_counter()
        self.ended = False

    def stop(self):
        pass

    def _end(self):
        self.start_time = .0
        self.ended = True
        self.just_ended = True

    def pause(self):
        if self.paused:
            return
        self.paused = time.perf_counter()

    def resume(self):
        self.start_time = time.perf_counter() - (self.paused - self.start_time)
        self.paused = .0

    def remaining(self):
        if self.paused:
            return self.duration - (self.paused - self.start_time)
        elif not self.start_time:
            return 0.0
        else:
            return self.duration - (time.perf_counter() - self.start_time)


# class Timer:
#     __slots__ = ("duration", "repeat", "start_time", "active", "_start_hooks", "_end_hooks", "_hit_end")

#     def __init__(self, duration: float, repeat: bool = None, autostart: bool = False) -> None:
#         self.duration = duration
#         self.repeat = repeat
#         self.start_time = 0
#         self.active = False
#         self._start_hooks: list[Callable[..., Any]] = []
#         self._end_hooks: list[Callable[..., Any]] = []
#         # Eine Queue hier könnte scheclt sein, falls der timer auf autostart ist. Queue habe ich nur genommen für FIFO (First in, First out). Sonst Liste Nehmen

#         self._hit_end = False

#         if autostart:
#             self.activate()

#         TimerManager.add(self)

#     def execute(self) -> bool:
#         return self._hit_end

#     def remove(self) -> None:
#         TimerManager.remove(self)

#     def activate(self):
#         self.active = True
#         self.start_time = time.time()
#         self._execute_hooks(self._start_hooks)
#         self._hit_end = False

#     def end(self) -> None:
#         self._execute_hooks(self._end_hooks)
#         self._hit_end = True

#     def deactivate(self):
#         self.active = False
#         self.start_time = 0
#         if self.repeat:
#             self.activate()

#     def update(self, /):
#         if time.time() - self.start_time >= self.duration:
#             if self.start_time != 0:
#                 self.end()
#             self.deactivate()
#         # print(f"updateded timer: {self}, {time.time() - self.start_time}")

#     def add_start_hook(self, hook: Callable):
#         self._start_hooks.append(hook)
#         # print("Added start hook:", hook.__name__)

#     def add_end_hook(self, hook: Callable):
#         self._end_hooks.append(hook)
#         # print("Added end hook:", hook.__name__)

#     def _execute_hooks(self, hooks: list[Callable[..., Any]]) -> None:
#         for hook in hooks:
#             hook()


# def call_on_timer_start(timer: Timer):
#     def decorator(func: Callable):
#         timer.add_start_hook(func)
#         return func
#     return decorator


# def call_on_timer_end(timer: Timer):
#     def decorator(func: Callable):
#         timer.add_end_hook(func)
#         return func
#     return decorator


# if __name__ == "__main__":
#     import pygame
#     pygame.init()

#     timermanager = TimerManager()
#     timer = Timer(2000)

#     @call_on_timer_start(timer)
#     def test1():
#         print("test1 called")

#     @call_on_timer_end(timer)
#     def test2():
#         print("test2 called")

#     screen = pygame.display.set_mode((100, 100))
#     clock = pygame.time.Clock()
#     timer.activate()
#     while True:
#         dt = clock.tick(60) * 0.001
#         for event in pygame.event.get():
#             if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
#                 exit()
#         timermanager.update()
