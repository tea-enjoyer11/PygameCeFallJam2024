import pygame
import math
import numpy as np

from Scripts.utils import load_image


class IkArm:
    def update(self, target_pos: tuple) -> None: return
    def render(self, surface: pygame.Surface, c1=(0, 0, 255), c2=(255, 0, 0)) -> None: return
    def set_base_pos(self, pos: tuple) -> None: return


class IkArmLawOfCosines:
    def __init__(self, pos: tuple, arm1_len: float, arm2_len: float) -> None:
        self.pos = pos
        self.arm1_len = arm1_len
        self.arm2_len = arm2_len

        self.angle1 = 0.0
        self.angle2 = 0.0

    def set_base_pos(self, pos: tuple) -> None:
        self.pos = pos

    def _calculate_angles(self, target_x, target_y):
        d = math.sqrt(target_x ** 2 + target_y ** 2)

        # Clamp the distance to the maximum reach of the arm
        if d > (self.arm1_len + self.arm2_len):
            d = self.arm1_len + self.arm2_len

        # Calculate angle2 using the law of cosines
        angle2 = math.acos(min(max((d**2 - self.arm1_len**2 - self.arm2_len**2) / (2 * self.arm1_len * self.arm2_len), -1), 1))

        base_angle = math.atan2(target_y, target_x)  # Calculate the base angle

        # Calculate angle1
        angle1 = base_angle - math.atan2(self.arm2_len * math.sin(angle2), self.arm1_len + self.arm2_len * math.cos(angle2))

        self.angle1 = angle1
        self.angle2 = angle2

    def convert_to_local_space(self, pos: tuple) -> tuple:
        return (pos[0] - self.pos[0], pos[1] - self.pos[1])

    def solve(self, target_pos: tuple) -> None:
        target_pos = self.convert_to_local_space(target_pos)
        self._calculate_angles(target_pos[0], target_pos[1])

    def render(self, surface: pygame.Surface, c1=(0, 0, 255), c2=(255, 0, 0), upperarm_width=5, lowerarm_width=3, offset=(0, 0)) -> None:
        joint1_x = self.arm1_len * math.cos(self.angle1)
        joint1_y = self.arm1_len * math.sin(self.angle1)

        end_x = joint1_x + self.arm2_len * math.cos(self.angle1 + self.angle2)
        end_y = joint1_y + self.arm2_len * math.sin(self.angle1 + self.angle2)

        pos = self.pos

        # Draw the arm
        # uppper arm
        # pygame.draw.line(surface, c1, pos, (joint1_x + pos[0], joint1_y + pos[1]), 5)
        # lower arm
        # pygame.draw.line(surface, c2, (joint1_x + pos[0], joint1_y + pos[1]), (end_x + pos[0], end_y + pos[1]), 3)
        pygame.draw.line(
            surface,
            c1,
            (
                pos[0] - offset[0],
                pos[1] - offset[1],
            ),
            (
                joint1_x + pos[0] - offset[0],
                joint1_y + pos[1] - offset[1],
            ),
            upperarm_width
        )
        pygame.draw.line(
            surface,
            c2,
            (
                joint1_x + pos[0] - offset[0],
                joint1_y + pos[1] - offset[1],
            ),
            (
                end_x + pos[0] - offset[0],
                end_y + pos[1] - offset[1],
            ),
            lowerarm_width
        )
        # pygame.draw.circle(surface, (0, 255, 0), (int(end_x + self.pos[0]), int(end_y + self.pos[1])), 3)


class IKArmFABRIK:
    def __init__(self, pos: tuple, arm1_len: float, arm2_len: float) -> None:
        self.fixed_base_pos = pos
        self.joints: list[np.array] = [
            np.array(pos),
            np.array([pos[0] + arm1_len, pos[1]]),
            np.array([pos[0] + arm1_len + arm2_len, pos[1]]),
        ]
        self.joint_lengths: list[float] = [arm1_len, arm2_len]

        self.diff = 1
        self.last_diff = 1
        self.just_switched = False

    def set_base_pos(self, pos: tuple) -> None:
        self.fixed_base_pos = pos

    def solve(self, target: tuple, focus_direction: tuple[int, int] = (0, 0)):
        target = np.array(target)

        self.joints[1][0] += 100 * focus_direction[0]  # damit der Ellbogen richtig positioniert ist
        self.joints[1][1] += 100 * focus_direction[1]  # damit der Ellbogen richtig positioniert ist

        # Step 1: Forward reaching
        self.joints[-1] = target.copy()  # Set the end effector to the target
        for i in range(len(self.joints) - 2, -1, -1):
            # print(i)
            direction = self.joints[i + 1] - self.joints[i]
            distance = np.linalg.norm(direction)
            if distance > 0:
                direction = direction / distance  # Normalize direction
            self.joints[i] = self.joints[i + 1] - direction * self.joint_lengths[i-1]

        # Step 2: Backward reaching
        self.joints[0] = np.array(self.fixed_base_pos)  # Fixed base position
        for i in range(1, len(self.joints)):
            direction = self.joints[i] - self.joints[i - 1]
            distance = np.linalg.norm(direction)
            if distance > 0:
                direction = direction / distance  # Normalize direction
            self.joints[i] = self.joints[i - 1] + direction * self.joint_lengths[i-2]

    def update(self, target: tuple) -> None:
        self.solve(np.array(target))

    def render(self, surface: pygame.Surface, c1=(0, 0, 255), c2=(255, 0, 0), upperarm_width=5, lowerarm_width=3, offset: tuple = (0, 0)) -> None:
        # print(self.joints)
        pygame.draw.line(
            surface,
            c1,
            (
                self.joints[0][0] - offset[0],
                self.joints[0][1] - offset[1],
            ),
            (
                self.joints[1][0] - offset[0],
                self.joints[1][1] - offset[1],
            ),
            upperarm_width
        )
        pygame.draw.line(
            surface,
            c2,
            (
                self.joints[1][0] - offset[0],
                self.joints[1][1] - offset[1],
            ),
            (
                self.joints[2][0] - offset[0],
                self.joints[2][1] - offset[1],
            ),
            lowerarm_width
        )
        # pygame.draw.circle(surface, (0, 255, 0), self.joints[2], 3)


# RES = (600, 600)


# def rotate_around_pos(img: pygame.Surface, pos: tuple, angle: float) -> dict:
#     ret = {"surf": None, "rect": None}
#     org_image = img.copy()
#     if angle >= 0:
#         org_image = pygame.transform.flip(org_image, False, True)
#     # org_rect = org_image.get_frect()
#     rot_image = pygame.transform.rotate(org_image, math.degrees(angle)+90)

#     ret["surf"] = rot_image
#     ret["rect"] = rot_image.get_rect(center=pos)
#     return ret


# class Game:
#     def __init__(self):
#         self.master_screen = pygame.display.set_mode(RES)
#         self.screen = pygame.Surface((100, 100))
#         self.clock = pygame.time.Clock()

#         self.gun_image = load_image("test-gun.png")
#         self.gun_angle = 0.0

#         self.shoulder1_pos = (50, 50)
#         self.shoulder2_pos = (40, 50)
#         # self.arm1 = IkArmLawOfCosines(self.shoulder1_pos, 12, 12)
#         # self.arm2 = IkArmLawOfCosines(self.shoulder2_pos, 12, 12)
#         self.arm1 = IKArmFABRIK(self.shoulder1_pos, 12, 12)
#         self.arm2 = IKArmFABRIK(self.shoulder2_pos, 12, 12)

#         self.counter = 0  # recoil beim schießen
#         self.flip_offset = 7  # wenn geflippt, dann muss alles um dieses hier verschoben werden.

#         self.font = pygame.font.SysFont("arial", 21)

#     def update_gun_angle(self, mouse_pos) -> None:
#         mouse_offset = (self.shoulder1_pos[0] - mouse_pos[1], self.shoulder1_pos[1] - mouse_pos[0])
#         self.gun_angle = math.atan2(mouse_offset[1], mouse_offset[0])

#     def update(self):
#         mouse_pos = pygame.mouse.get_pos()
#         mouse_pos = (mouse_pos[0] / 6, mouse_pos[1] / 6)

#         self.update_gun_angle(mouse_pos)

#         offset = self.counter
#         translation_offset = (0, 0)
#         if self.gun_angle < 0:
#             translation_offset = (self.flip_offset, 0)
#         self.gun_pos = (
#             self.shoulder1_pos[0] - math.sin(self.gun_angle) * (20 - offset),  # rote
#             self.shoulder1_pos[1] - math.cos(self.gun_angle) * (20 - offset),  # rote
#         )
#         self.gun_handgrip1 = (
#             self.shoulder1_pos[0] - math.sin(self.gun_angle) * (27 - offset) - translation_offset[0],  # grüne
#             self.shoulder1_pos[1] - math.cos(self.gun_angle) * (27 - offset) - translation_offset[1],  # grüne
#         )
#         self.gun_handgrip2 = (
#             self.shoulder1_pos[0] - math.sin(self.gun_angle) * (15 - offset) - translation_offset[0],  # blaue
#             self.shoulder1_pos[1] - math.cos(self.gun_angle) * (15 - offset) - translation_offset[1],  # blaue
#         )

#         # swich arm positions if flip
#         if self.gun_angle < 0:
#             self.arm1.set_base_pos(self.shoulder2_pos)
#             self.arm2.set_base_pos(self.shoulder1_pos)
#         else:
#             self.arm1.set_base_pos(self.shoulder1_pos)
#             self.arm2.set_base_pos(self.shoulder2_pos)

#         self.arm1.update(self.gun_handgrip2)
#         self.arm2.update(self.gun_handgrip1)

#         self.counter = max(0, self.counter - 0.35)
#         # recoil wenn schießen.
#         if pygame.mouse.get_pressed()[0] and not self.counter:
#             self.counter = 5

#     def render(self, debug=True):
#         data = rotate_around_pos(self.gun_image, self.gun_pos, self.gun_angle)
#         rect = data["rect"]
#         if self.gun_angle < 0:
#             rect.x -= self.flip_offset

#         self.arm2.render(self.screen, c1=(0, 125, 0), c2=(0, 200, 0))
#         self.screen.blit(data["surf"], rect)
#         self.arm1.render(self.screen, c1=(255, 0, 0), c2=(255, 125, 0))

#         if debug:
#             pygame.draw.rect(self.screen, (255, 255, 0), rect, 1)
#             pygame.draw.circle(self.screen, (255, 0, 0), self.gun_pos, 1)
#             pygame.draw.circle(self.screen, (0, 255, 0), self.gun_handgrip1, 1)
#             pygame.draw.circle(self.screen, (0, 0, 255), self.gun_handgrip2, 1)
#             pygame.draw.circle(self.screen, (255, 125, 255), self.shoulder1_pos, 1)
#             pygame.draw.circle(self.screen, (255, 125, 255), self.shoulder2_pos, 1)

#         self.master_screen.blit(self.screen)

#         self.master_screen.blit(pygame.transform.scale(self.screen, RES), (0, 0))

#         mouse_pos = pygame.mouse.get_pos()
#         mouse_pos = (mouse_pos[0] // 6, mouse_pos[1] // 6)
#         font_surf = self.font.render(f"angle: {self.gun_angle}\n\nmouse_pos: {mouse_pos}", True, (0, 0, 0))
#         self.master_screen.blit(font_surf, (10, 10))
#         pygame.display.flip()

#     def main(self):
#         running = True
#         debug = True
#         while running:
#             self.screen.fill((255, 255, 255))
#             for event in pygame.event.get():
#                 if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
#                     running = False
#                 if event.type == pygame.KEYDOWN and event.key == pygame.K_LSHIFT:
#                     debug = not debug

#             self.update()

#             self.render(debug=debug)

#             self.clock.tick(120)

#         pygame.quit()


# if __name__ == "__main__":
#     Game().main()
