"""
from https://easings.net

**x has to be between 0 and 1**
"""

from math import cos, sin, pi, pow, sqrt


def ease_linear(x: float) -> float:
    """
    return x
    """
    return x


def ease_in_sine(x: float) -> float:
    """
    return 1 - Math.cos((x * Math.PI) / 2);
    """
    return 1 - cos((x * pi) / 2)


def ease_out_sine(x: float) -> float:
    """
    return Math.sin((x * Math.PI) / 2);
    """
    return sin((x*pi)/2)


def ease_in_out_sine(x: float) -> float:
    """
    return -(Math.cos(Math.PI * x) - 1) / 2;
    """
    return -(cos(pi * x) - 1) / 2


def ease_in_quad(x: float) -> float:
    """
    return x * x;
    """
    return x * x


def ease_out_quad(x: float) -> float:
    """
    return 1 - (1 - x) * (1 - x);
    """
    return 1 - (1 - x) * (1 - x)


def ease_in_out_quad(x: float) -> float:
    """
    return x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
    """
    if x < 0.5:
        return 2 * x * x
    else:
        return 1 - pow(-2 * x + 2, 2) / 2


def ease_in_cubic(x: float) -> float:
    """
    return x * x * x;
    """
    return x * x * x


def ease_out_cubic(x: float) -> float:
    """
    return 1 - Math.pow(1 - x, 3);
    """
    return 1 - pow(1 - x, 3)


def ease_in_out_cubic(x: float) -> float:
    """
    return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
    """
    if x < 0.5:
        return 4 * x * x * x
    else:
        return 1 - pow(-2 * x + 2, 3) / 2


def ease_in_quart(x: float) -> float:
    """
    return x * x * x * x;
    """
    return x * x * x * x


def ease_out_quart(x: float) -> float:
    """
    return 1 - Math.pow(1 - x, 4);
    """
    return 1 - pow(1 - x, 4)


def ease_in_out_quart(x: float) -> float:
    """
    return x < 0.5 ? 8 * x * x * x * x : 1 - Math.pow(-2 * x + 2, 4) / 2;
    """
    if x < 0.5:
        return 8 * x * x * x * x
    else:
        return 1 - pow(-2 * x + 2, 4) / 2


def ease_in_quint(x: float) -> float:
    """
    return x * x * x * x * x;
    """
    return x * x * x * x * x


def ease_out_quint(x: float) -> float:
    """
    return 1 - Math.pow(1 - x, 5);
    """
    return 1 - pow(1 - x, 5)


def ease_in_out_quint(x: float) -> float:
    """
    return x < 0.5 ? 16 * x * x * x * x * x : 1 - Math.pow(-2 * x + 2, 5) / 2;
    """
    if x < 0.5:
        return 16 * x * x * x * x * x
    else:
        return 1 - pow(-2 * x + 2, 5) / 2


def ease_in_expo(x: float) -> float:
    """
    return x === 0 ? 0 : Math.pow(2, 10 * x - 10);
    """
    if x == 0:
        return 0
    else:
        return pow(2, 10 * x - 10)


def ease_out_expo(x: float) -> float:
    """
    return x === 1 ? 1 : 1 - Math.pow(2, -10 * x);
    """
    if x == 1:
        return 1
    else:
        return 1 - pow(2, -10 * x)


def ease_in_out_expo(x: float) -> float:
    """
    return x === 0
      ? 0
      : x === 1
      ? 1
      : x < 0.5 ? Math.pow(2, 20 * x - 10) / 2
      : (2 - Math.pow(2, -20 * x + 10)) / 2;
    """
    if x == 0:
        return 0
    elif x == 1:
        return 1
    elif x < 0.5:
        return pow(2, 20 * x - 10) / 2
    else:
        return (2 - pow(2, -20 * x + 10)) / 2


def ease_in_circ(x: float) -> float:
    """
    return 1 - Math.sqrt(1 - Math.pow(x, 2));
    """
    return 1 - sqrt(1 - pow(x, 2))


def ease_out_circ(x: float) -> float:
    """
    return Math.sqrt(1 - Math.pow(x - 1, 2));
    """
    return sqrt(1 - pow(x - 1, 2))


def ease_in_out_circ(x: float) -> float:
    """
    return x < 0.5
      ? (1 - Math.sqrt(1 - Math.pow(2 * x, 2))) / 2
      : (Math.sqrt(1 - Math.pow(-2 * x + 2, 2)) + 1) / 2;
    """
    if x < 0.5:
        return (1 - sqrt(1-pow(2*x, 2))) / 2
    else:
        return (sqrt(1-pow(-2*x+2, 2))+1)/2


c1 = 1.70158
c3 = c1 + 1


def ease_in_back(x: float) -> float:
    """
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return c3 * x * x * x - c1 * x * x;
    """
    return c3 * x * x * x - c1 * x * x


def ease_out_back(x: float) -> float:
    """
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);
    """
    return 1 + c3 * pow(x - 1, 3) + c1 * pow(x - 1, 2)


c2 = c1 * 1.525


def ease_in_out_back(x: float) -> float:
    """
    const c1 = 1.70158;
    const c2 = c1 * 1.525;
    return x < 0.5
      ? (Math.pow(2 * x, 2) * ((c2 + 1) * 2 * x - c2)) / 2
      : (Math.pow(2 * x - 2, 2) * ((c2 + 1) * (x * 2 - 2) + c2) + 2) / 2;
    """
    if x < 0.5:
        return (pow(2 * x, 2) * ((c2 + 1) * 2 * x - c2)) / 2
    else:
        return (pow(2 * x - 2, 2) * ((c2 + 1) * (x * 2 - 2) + c2) + 2) / 2


c4 = (2 * pi) / 3


def ease_in_elastic(x: float) -> float:
    """
    const c4 = (2 * Math.PI) / 3;
    return x === 0
      ? 0
      : x === 1
      ? 1
      : -Math.pow(2, 10 * x - 10) * Math.sin((x * 10 - 10.75) * c4);
    """
    if x == 0:
        return 0
    elif x == 1:
        return 1
    else:
        return - pow(2, 10 * x - 10)*sin((x*10-10.75)*c4)


def ease_out_elastic(x: float) -> float:
    """
    const c4 = (2 * Math.PI) / 3;
    return x === 0
      ? 0
      : x === 1
      ? 1
      : Math.pow(2, -10 * x) * Math.sin((x * 10 - 0.75) * c4) + 1;
    """
    if x == 0:
        return 0
    elif x == 1:
        return 1
    else:
        return pow(2, -10 * x) * sin((x * 10 - 0.75) * c4) + 1


c5 = (2 * pi) / 4.5


def ease_in_out_elastic(x: float) -> float:
    """
    const c5 = (2 * Math.PI) / 4.5;
    return x === 0
      ? 0
      : x === 1
      ? 1
      : x < 0.5
      ? -(Math.pow(2, 20 * x - 10) * Math.sin((20 * x - 11.125) * c5)) / 2
      : (Math.pow(2, -20 * x + 10) * Math.sin((20 * x - 11.125) * c5)) / 2 + 1;
    """
    if x == 0:
        return 0
    elif x == 1:
        return 1
    elif x < 0.5:
        return -(pow(2, 20 * x - 10) * sin((20 * x - 11.125) * c5)) / 2
    else:
        return (pow(2, -20 * x + 10) * sin((20 * x - 11.125) * c5)) / 2 + 1


def ease_in_bounce(x: float) -> float:
    # return 1 - easeOutBounce(1 - x);
    return 1 - ease_out_bounce(1 - x)


n1 = 7.5625
d1 = 2.75


def ease_out_bounce(x: float) -> float:
    """
    const n1 = 7.5625;
    const d1 = 2.75;

    if (x < 1 / d1) {
        return n1 * x * x;
    } else if (x < 2 / d1) {
        return n1 * (x -= 1.5 / d1) * x + 0.75;
    } else if (x < 2.5 / d1) {
        return n1 * (x -= 2.25 / d1) * x + 0.9375;
    } else {
        return n1 * (x -= 2.625 / d1) * x + 0.984375;
    }
    """
    if x < 1 / d1:
        return n1 * x * x
    elif x < 2 / d1:
        x -= 1.5
        return n1 * (x / d1) * x + 0.75
    elif x < 2.5 / d1:
        x -= 2.25
        return n1 * (x / d1) * x + 0.9375
    else:
        x -= 2.625
        return n1 * (x / d1) * x + 0.984375


def ease_in_out_bounce(x: float) -> float:
    """
    return x < 0.5
      ? (1 - easeOutBounce(1 - 2 * x)) / 2
      : (1 + easeOutBounce(2 * x - 1)) / 2;
    """
    if x < 0.5:
        return (1 - ease_out_bounce(1 - 2 * x)) / 2
    else:
        return (1 + ease_out_bounce(2 * x - 1)) / 2

