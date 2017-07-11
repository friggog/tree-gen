"""L System definition for lombardy poplar"""

from math import sqrt
from random import random

from ch_trees.chturtle import Vector
from ch_trees.lsystems.lsystem import LSystem, LSymbol

__iterations__ = 10.0
__base_width__ = 0.7


def q_prod(sym):
    """Production rule for Q"""
    ret = []
    prev_ang = 0
    for _ in range(int(random() * 2 + 3)):
        ang = random() * 10 + 30
        ret.extend([LSymbol("/", {"a": prev_ang + 75 + random() * 10}),
                    LSymbol("&", {"a": ang}),
                    LSymbol("!", {"w": sym.parameters["w"] * 0.2}),
                    LSymbol("["),
                    LSymbol("A", {"w": sym.parameters["w"] * 0.3,
                                  "l": 1.5 * sqrt(sym.parameters["w"]) * (random() * 0.2 + 0.9)}),
                    LSymbol("]"),
                    LSymbol("!", {"w": sym.parameters["w"]}),
                    LSymbol("^", {"a": ang}),
                    LSymbol("F", {"l": sym.parameters["l"]})])
    ret.append(LSymbol("Q", {"w": max(0, sym.parameters["w"] - __base_width__ / 14),
                             "l": sym.parameters["l"]}))
    return ret


def a_prod(sym):
    """Production rule for A"""
    ret = []
    n = int(random() * 5 + 22.5)
    w_d = sym.parameters["w"] / (n - 1)
    prev_rot = 0
    for ind in range(n):
        wid = sym.parameters["w"] - ind * w_d
        ang = random() * 10 + 25
        ret.extend([LSymbol("!", {"w": wid}),
                    LSymbol("F", {"l": sym.parameters["l"] / 3}),
                    LSymbol("/", {"a": prev_rot + 140}),
                    LSymbol("&", {"a": ang}),
                    LSymbol("!", {"w": wid * 0.3}),
                    LSymbol("["),
                    LSymbol("F", {"l": 0.75 * sqrt(n - ind) * sym.parameters["l"] / 3,
                                  "leaves": 25,
                                  "leaf_d_ang": 40,
                                  "leaf_r_ang": 140}),
                    LSymbol("^", {"a": 20}),
                    LSymbol("F", {"l": 0.75 * sqrt(n - ind) * sym.parameters["l"] / 3,
                                  "leaves": 25,
                                  "leaf_d_ang": 40,
                                  "leaf_r_ang": 140}),
                    LSymbol("%"),
                    LSymbol("]"),
                    LSymbol("!", {"w": wid}),
                    LSymbol("^", {"a": ang}),
                    LSymbol("\\", {"a": prev_rot + 140}),
                    LSymbol("^", {"a": 1.2})])
        prev_rot += 140
    return ret


def system():
    """initialize and iterate the system as appropriate"""
    l_sys = LSystem(axiom=[LSymbol("!", {"w": __base_width__}),
                           LSymbol("/", {"a": 45}),
                           LSymbol("Q", {"w": __base_width__, "l": 0.5})],
                    rules={"Q": q_prod, "A": a_prod},
                    tropism=Vector([0, 0, 0]),
                    thickness=0.5,
                    bendiness=0,
                    leaf_shape=0,
                    leaf_scale=0.3,
                    leaf_bend=0.7)
    l_sys.iterate_n(15)
    return l_sys
