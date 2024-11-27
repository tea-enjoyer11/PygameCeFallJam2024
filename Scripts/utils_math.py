from pygame import Vector2
import math
from typing import Sequence


def skalar(v1, v2):
    # v1.n * v2.n + ... + v1.m + v2.m
    return sum(v1[i] * v2[i] for i in range(len(v1)))


def magnitude(v):
    return math.sqrt(sum([x**2 for x in v]))


def normalize(vector, rounddigits: int = 0) -> tuple:
    mag = magnitude(vector)
    if mag == 0:
        # raise ValueError("Cannot normalize the zero vector")
        return tuple([0] * len(vector))
    if rounddigits:
        return tuple([round(x / mag, rounddigits) for x in vector])
    return tuple([x / mag for x in vector])


def lerp(start: float, end: float, time: float) -> float:
    return start + (end - start) * time


def Vector2Lerp(start: Vector2, end: Vector2, time: float) -> Vector2:
    return start + (end - start) * time


def dist(p1: Sequence[float | int], p2: Sequence[float | int]) -> float:
    # return ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1])) ** 0.5
    # return math.sqrt(math.pow(p2[0] - p1[0], 2) + math.pow(p2[1] - p1[1], 2))
    return math.sqrt(sum([math.pow(x1 - x0, 2) for x0, x1 in zip(p1, p2)]))


def clamp(minimum, x, maximum):
    return max(minimum, min(x, maximum))


def clamp_bottom(minimun, x):
    return max(minimun, x)


def clamp_top(maximun, x):
    return min(maximun, x)


def cycle_sequence(arr: list | tuple) -> list | tuple:
    first = arr[0]
    arr[0] = arr[-1]
    arr[-1] = first
    return arr


def flatten_list(l: list):
    l_ = []
    if not isinstance(l, list | tuple):
        return []
    else:
        for i in l:
            if isinstance(i, list | tuple):  # Check if element is a list
                l_ += flatten_list(i)  # Recursively flatten nested list
            else:
                l_.append(i)
    return l_


def reverseInts(list_: list) -> list:
    listCopy = []
    for pos in list_:
        if pos > 0:
            listCopy.append(-pos)
        else:
            listCopy.append(pos * -1)

    return listCopy


def clamp_number_to_range_steps(n, start, end, step) -> float:
    n = clamp(start, n, end)
    return round(n / step) * step


def sign(n, zero_error_return=1):
    if n != 0:
        return n / abs(n)
    return zero_error_return


def angle_from_vector2d(vec: tuple[float, float]) -> float:
    """
    Returns angle in `radians`
    """
    return math.atan2(vec[1], vec[0])


def vector2d_from_angle(angle: float) -> tuple[float, float]:
    """
    !!!!!!!!!!!!!!!! Angle is in `degrees` !!!!!!!!!!!!!!!!
    """
    return (math.cos(angle), math.sin(angle))


def rotate_vector2d(vec: tuple[float, float], angle: float) -> tuple[float, float]:
    # https://en.wikipedia.org/wiki/Rotation_matrix
    return (
        vec[0] * math.cos(angle) - vec[1] * math.sin(angle),
        vec[0] * math.sin(angle) + vec[1] * math.cos(angle),
    )


def sign_vector2d(vec: tuple[float, float], zero_error_return=1) -> tuple[float, float]:
    return (
        sign(vec[0], zero_error_return=zero_error_return),
        sign(vec[1], zero_error_return=zero_error_return),
    )


def vector2d_add(vec1: tuple, vec2: tuple) -> tuple:
    return (
        vec1[0] + vec2[0],
        vec1[1] + vec2[1]
    )


def vector2d_sub(vec1: tuple, vec2: tuple) -> tuple:
    return (
        vec1[0] - vec2[0],
        vec1[1] - vec2[1]
    )


def vector2d_mult(vec1: tuple, a: float) -> tuple:
    return (
        vec1[0] * a,
        vec1[1] * a
    )
