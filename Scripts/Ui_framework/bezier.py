import numpy as np


def bezier_point(control_points, t):
    """
    De Casteljau's algorithm.
    """
    control_points = np.array(control_points)

    while len(control_points) > 1:
        # Linear interpolation between points
        control_points = [(1 - t) * p0 + t * p1 for p0, p1 in zip(control_points[:-1], control_points[1:])]

    return control_points[0]


if __name__ == "__main__":
    import time
    control_pts = [(0, 0), (0, .5), (1, 0), (1, 1)]
    t_value = 0.5  # Zwischen 0 - 1
    t0 = time.perf_counter()
    point_on_curve = bezier_point(control_pts, t_value)
    print(f"Took {time.perf_counter() - t0} seconds to calculate: {point_on_curve}")
