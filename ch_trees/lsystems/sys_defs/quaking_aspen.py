"""L System definition for basic tree"""

from math import sqrt
from random import random

from ch_trees.chturtle import Vector
from ch_trees.lsystems.lsystem import LSystem, LSymbol

__base_width__ = 0.3
__base_length__ = 4


def q_prod(sym):
    """Production rule for Q"""
    ret = []
    prev_ang = 0
    n = int(random() * 2 + 7)
    for ind in range(8):
        offset = 1 - (__base_width__ - sym.parameters["w"]) / __base_width__
        offset += ind / 8 / 12
        dang = 30 + 85 * offset
        if offset <= 0.7:
            b_len = 0.4 + 0.6 * offset / 0.7
        else:
            b_len = 0.4 + 0.6 * (1.0 - offset) / 0.3
        ret.extend([LSymbol("/", {"a": prev_ang + 75 + random() * 10}),
                    LSymbol("&", {"a": dang}),
                    LSymbol("!", {"w": sym.parameters["w"] * 0.08 * b_len}),
                    LSymbol("["),
                    LSymbol("F", {"l": sym.parameters["w"] / 2}),
                    LSymbol("A", {"w": 0.08 * b_len,
                                  "l": 0.6 * b_len}),
                    LSymbol("]"),
                    LSymbol("!", {"w": sym.parameters["w"]}),
                    LSymbol("^", {"a": dang}),
                    LSymbol("F", {"l": sym.parameters["l"]})])
    ret.append(LSymbol("Q", {"w": max(0, sym.parameters["w"] - __base_width__ / 11),
                             "l": sym.parameters["l"]}))
    return ret


def a_prod(sym):
    """Production rule for A"""
    ret = []
    w_d = sym.parameters["w"] / 14
    prev_rot = 0
    n = int(random() * 3 + 15.5)
    for ind in range(n):
        wid = sym.parameters["w"] - ind * w_d
        l_count = int((sqrt(n - ind) + 2) * 4 * sym.parameters["l"])
        ret.extend([LSymbol("!", {"w": wid}),
                    LSymbol("F", {"l": sym.parameters["l"] / 3}),
                    LSymbol("/", {"a": prev_rot + 140}),
                    LSymbol("&", {"a": 60}),
                    LSymbol("!", {"w": wid * 0.4}),
                    LSymbol("["),
                    LSymbol("F", {"l": sqrt(n - ind) * sym.parameters["l"] / 3,
                                  "leaves": l_count,
                                  "leaf_d_ang": 40,
                                  "leaf_r_ang": 140}),
                    LSymbol("^", {"a": random() * 30 + 30}),
                    LSymbol("F", {"l": sqrt(n - ind) * sym.parameters["l"] / 4,
                                  "leaves": l_count,
                                  "leaf_d_ang": 40,
                                  "leaf_r_ang": 140}),
                    LSymbol("%"),
                    LSymbol("]"),
                    LSymbol("!", {"w": wid}),
                    LSymbol("^", {"a": 60}),
                    LSymbol("\\", {"a": prev_rot + 140}),
                    LSymbol("+", {"a": -5 + random() * 10}),
                    LSymbol("^", {"a": -7.5 + random() * 15})])
        prev_rot += 140
    ret.append(LSymbol("F", {"l": sym.parameters["l"] / 2}))
    return ret


def system():
    """initialize and iterate the system as appropriate"""
    axiom = []
    con = int(__base_length__ / 0.1)
    s = random() * 0.2 + 0.9
    for ind in range(con):
        axiom.append(LSymbol("!", {"w": s * (__base_width__ + ((con - ind) / con) ** 6 * 0.2)}))
        axiom.append(LSymbol("F", {"l": s * 0.1}))
    axiom.append(LSymbol("Q", {"w": s * __base_width__, "l": s * 0.1}))
    l_sys = LSystem(axiom=axiom,
                    rules={"Q": q_prod, "A": a_prod},
                    tropism=Vector([0, 0, 0.2]),
                    thickness=0.5,
                    bendiness=0,
                    leaf_shape=3,
                    leaf_scale=0.17,
                    leaf_bend=0.2)
    l_sys.iterate_n(12)
    return l_sys
