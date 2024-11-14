import collections
import struct
import CONFIG

import pygame
import moderngl
import glm
import numpy as np
import random


pygame.init()


def load_f(path: str) -> str:
    ret = ""
    with open(path, "r") as f:
        ret = f.read()
    return ret


def load_image(path: str) -> pygame.Surface:
    i = pygame.image.load(path).convert()
    i.set_colorkey((0, 0, 0))
    return i


def surf_to_texture(surf: pygame.Surface, ctx: moderngl.Context) -> moderngl.Texture:
    tex = ctx.texture(surf.get_size(), 4)
    tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    tex.swizzle = 'BGRA'
    tex.write(surf.get_view('1'))
    return tex


class Camera:
    def __init__(self, pos: glm.vec3, width: int, height: int, fov: float = 45.0, near_clip: float = 0.1, far_clip: float = 100.0):
        self.pos = pos  # Position of the camera in world space
        self.front = glm.vec3(0.0, 0.0, -1.0)  # The direction the camera is facing
        self.up = glm.vec3(0.0, 1.0, 0.0)  # The 'up' vector (world-space)
        self.right = glm.vec3(1.0, 0.0, 0.0)  # Right direction
        self.world_up = glm.vec3(0.0, 1.0, 0.0)  # World up vector for reference
        self.yaw = -90.0  # Initial yaw
        self.pitch = 0.0  # Initial pitch
        self.speed = 3.0  # Movement speed (units per second)
        self.sensitivity = 0.3  # Mouse movement sensitivity

        self.aspect_ratio = width / height
        self.fov = fov
        self.near_clip = near_clip
        self.far_clip = far_clip

        # Initialize Pygame and set the window cursor position to the center of the screen
        pygame.mouse.set_pos((width // 2, height // 2))

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper, rel_mouse: tuple):
        # Mouse input: Update yaw and pitch based on mouse movement
        x_offset = rel_mouse[0]
        y_offset = -rel_mouse[1]  # Reverse y-axis, because screen coordinates go down as you move down

        x_offset *= self.sensitivity
        y_offset *= self.sensitivity

        # Update the camera angles (yaw and pitch)
        self.yaw += x_offset
        self.pitch += y_offset

        # Constrain the pitch to avoid camera flipping
        if self.pitch > 89.0:
            self.pitch = 89.0
        if self.pitch < -89.0:
            self.pitch = -89.0

        # Update the front vector based on the new yaw and pitch
        front = glm.vec3(
            glm.cos(glm.radians(self.yaw)) * glm.cos(glm.radians(self.pitch)),
            glm.sin(glm.radians(self.pitch)),
            glm.sin(glm.radians(self.yaw)) * glm.cos(glm.radians(self.pitch))
        )
        self.front = glm.normalize(front)

        # Recalculate the right and up vectors
        self.right = glm.normalize(glm.cross(self.front, self.world_up))
        self.up = glm.normalize(glm.cross(self.right, self.front))

        # Keyboard input: Move the camera with WASD keys
        movement = glm.vec3(0.0)
        if keys[pygame.K_w]:  # Move forward
            movement += self.front
        if keys[pygame.K_s]:  # Move backward
            movement -= self.front
        if keys[pygame.K_a]:  # Move left
            movement -= self.right
        if keys[pygame.K_d]:  # Move right
            movement += self.right
        if keys[pygame.K_SPACE]:
            movement += self.world_up
        if keys[pygame.K_LSHIFT]:
            movement -= self.world_up

        # Normalize the movement vector and move the camera
        if glm.length(movement) > 0.0:
            movement = glm.normalize(movement)
            self.pos += movement * self.speed * dt

    def get_view_matrix(self):
        # Use the lookAt function to create a view matrix based on the camera position and direction
        return glm.lookAt(self.pos, self.pos + self.front, self.up)

    def get_projection_matrix(self):
        # Use the perspective function to create the projection matrix based on the FOV, aspect ratio, and near/far clipping planes
        return glm.perspective(glm.radians(self.fov), self.aspect_ratio, self.near_clip, self.far_clip)


class Mesh:

    @staticmethod
    def from_cube(program: moderngl.Program, pos=glm.vec3(0.0)) -> "Mesh":
        m = Mesh()

        ctx = moderngl.get_context()
        # Cube vertices: 8 vertices with positions and corresponding UV coordinates
        vertices = np.array([
            # Position (x, y, z)            # UV (u, v)
            # -0.5, -0.5, -0.5, 0.0, 0.0,  # Vertex 0
            # 0.5, -0.5, -0.5, 1.0, 0.0,  # Vertex 1
            # 0.5,  0.5, -0.5, 1.0, 1.0,  # Vertex 2
            # -0.5,  0.5, -0.5, 0.0, 1.0,  # Vertex 3
            # -0.5, -0.5,  0.5, 0.0, 0.0,  # Vertex 4
            # 0.5, -0.5,  0.5, 1.0, 0.0,  # Vertex 5
            # 0.5,  0.5,  0.5, 1.0, 1.0,  # Vertex 6
            # -0.5,  0.5,  0.5, 0.0, 1.0   # Vertex 7

            -0.5, -0.5, -0.5,  0.0, 0.0,
            0.5, -0.5, -0.5,  1.0, 0.0,
            0.5,  0.5, -0.5,  1.0, 1.0,
            0.5,  0.5, -0.5,  1.0, 1.0,
            -0.5,  0.5, -0.5,  0.0, 1.0,
            -0.5, -0.5, -0.5,  0.0, 0.0,

            -0.5, -0.5,  0.5,  0.0, 0.0,
            0.5, -0.5,  0.5,  1.0, 0.0,
            0.5,  0.5,  0.5,  1.0, 1.0,
            0.5,  0.5,  0.5,  1.0, 1.0,
            -0.5,  0.5,  0.5,  0.0, 1.0,
            -0.5, -0.5,  0.5,  0.0, 0.0,

            -0.5,  0.5,  0.5,  1.0, 0.0,
            -0.5,  0.5, -0.5,  1.0, 1.0,
            -0.5, -0.5, -0.5,  0.0, 1.0,
            -0.5, -0.5, -0.5,  0.0, 1.0,
            -0.5, -0.5,  0.5,  0.0, 0.0,
            -0.5,  0.5,  0.5,  1.0, 0.0,

            0.5,  0.5,  0.5,  1.0, 0.0,
            0.5,  0.5, -0.5,  1.0, 1.0,
            0.5, -0.5, -0.5,  0.0, 1.0,
            0.5, -0.5, -0.5,  0.0, 1.0,
            0.5, -0.5,  0.5,  0.0, 0.0,
            0.5,  0.5,  0.5,  1.0, 0.0,

            -0.5, -0.5, -0.5,  0.0, 1.0,
            0.5, -0.5, -0.5,  1.0, 1.0,
            0.5, -0.5,  0.5,  1.0, 0.0,
            0.5, -0.5,  0.5,  1.0, 0.0,
            -0.5, -0.5,  0.5,  0.0, 0.0,
            -0.5, -0.5, -0.5,  0.0, 1.0,

            -0.5,  0.5, -0.5,  0.0, 1.0,
            0.5,  0.5, -0.5,  1.0, 1.0,
            0.5,  0.5,  0.5,  1.0, 0.0,
            0.5,  0.5,  0.5,  1.0, 0.0,
            -0.5,  0.5,  0.5,  0.0, 0.0,
            -0.5,  0.5, -0.5,  0.0, 1.0
        ], dtype=np.float32)

        # Cube indices for drawing the cube using triangles
        # indices = np.array([
        #     # Front face
        #     0, 1, 2, 0, 2, 3,
        #     # Back face
        #     4, 5, 6, 4, 6, 7,
        #     # Left face
        #     0, 3, 7, 0, 7, 4,
        #     # Right face
        #     1, 2, 6, 1, 6, 5,
        #     # Top face
        #     2, 3, 7, 2, 7, 6,
        #     # Bottom face
        #     0, 1, 5, 0, 5, 4
        # ], dtype=np.uint32)

        # Create the buffer for vertices and indices
        m.vbo = ctx.buffer(vertices)
        # m.ibo = ctx.buffer(indices)

        # Create the VAO (Vertex Array Object)
        m.vao = ctx.vertex_array(
            program,
            [
                (m.vbo, '3f 2f', 'vert', 'texcoord')  # Position and texture coordinates
            ],
            # index_buffer=m.ibo,
        )

        return m

    def __init__(self):
        self.ibo = None
        self.vbo = None
        self.vao = None


class Cube:
    def __init__(self, pos: glm.vec3, program: moderngl.Program, size=0.25):
        self.pos = pos

        self.mesh = Mesh.from_cube(program)

        self.size = size
        self.model = glm.mat4(1.0)
        self.model = glm.translate(self.model, pos)
        self.model = glm.scale(self.model, glm.vec3(self.size))

    def render(self) -> None:
        # Set the shader uniform for model-view-projection matrix
        self.mesh.vao.program['model'].write(self.model)

        # Bind VAO and draw the cube
        self.mesh.vao.render(moderngl.TRIANGLES)

    def update(self, dt: float) -> None:
        return
        self.model = glm.rotate(self.model, dt, glm.vec3(1))


class Entity:
    def __init__(self, pos: glm.vec3, type: str, vel=glm.vec3(0.0)):
        self.pos = pos
        self.vel = vel
        self.type = str


class Player(Entity):
    def __init__(self, pos, vel=glm.vec3(0.0)):
        super().__init__(pos, type="player", vel=vel)
        self.camera = Camera(pos, CONFIG.RES[0], CONFIG.RES[1])

    def update(self, dt: float) -> None:
        self.camera.update(dt, pygame.key.get_pressed(), pygame.mouse.get_rel())


class Ship(Entity):
    def __init__(self, pos, vel=glm.vec3(0.0)):
        super().__init__(pos, "ship", vel)

        self.model = Cube(pos, ...)


class HashMap:
    def __init__(self, cell_size=3):
        self.cell_size = 3
        self.grid = collections.defaultdict(list)

    def key(self, pos: tuple) -> tuple: return tuple([x // self.cell_size for x in pos])
    def insert(self, pos: tuple, ent: object): self.grid[self.key(pos)].append((pos, ent))
    def query_cell(self, pos: tuple, ignore_pos: set[tuple] = set()) -> list[object]: return [ent for (ent_pos, ent) in self.grid[self.key(pos)] if ent_pos not in ignore_pos]
    def clear(self) -> None: self.grid.clear()


class ModernGLRenderer:
    def __init__(self):
        self.screen = pygame.display.set_mode(CONFIG.RES, flags=pygame.OPENGL | pygame.DOUBLEBUF)
        self.ctx = moderngl.create_context(require=330)

        self.shaders: dict[str, moderngl.Program] = {
            "default": self.ctx.program(vertex_shader=load_f("assets/shader/default/vert.glsl"), fragment_shader=load_f("assets/shader/default/frag.glsl"))
        }

        self.cubes: list[Cube] = []
        self.cube_map = HashMap()

        self.tex = surf_to_texture(load_image("img.png"), self.ctx)

        self.ctx.enable(moderngl.DEPTH_TEST)

        self.player = Player(glm.vec3(0.0))

        self.setup()

    def setup(self) -> None:
        max_dist = 10
        max_dist_h = max_dist/2
        for i in range(64):
            self.cubes.append(
                Cube(glm.vec3(random.random()*max_dist-max_dist_h, 0, random.random()*max_dist-1), self.shaders["default"])
            )

    def render(self) -> None:
        self.fill((88, 12, 14))
        for cube in self.cubes:
            cube.render()

    def update(self, dt: float) -> None:
        self.tex.use()
        self.shaders["default"]["tex"] = 0

        self.player.update(dt)

        self.shaders["default"]["view"].write(self.player.camera.get_view_matrix())
        self.shaders["default"]["projection"].write(self.player.camera.get_projection_matrix())

        for cube in self.cubes:
            cube.update(dt)

        self.cube_map.clear()

        for cube in self.cubes:
            self.cube_map.insert(cube.pos, cube)

        # print([(pos, len(ents)) for pos, ents in self.cube_map.grid.items()])

    def fill(self, color: tuple) -> None:
        self.ctx.clear(*[x / 255 for x in color])


mglr = ModernGLRenderer()
clock = pygame.time.Clock()


run = True
while run:
    dt = clock.tick(0) * .001

    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            run = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                pygame.mouse.set_relative_mode(not pygame.mouse.get_relative_mode())

    mglr.update(dt)

    mglr.render()

    pygame.display.set_caption(f"{clock.get_fps():.0f}")
    pygame.display.flip()

pygame.quit()
