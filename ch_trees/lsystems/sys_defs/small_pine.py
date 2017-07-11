"""L-system definition for fir tree"""

from random import random

from ch_trees.chturtle import Vector
from ch_trees.lsystems.lsystem import LSystem, LSymbol

__length_r__ = 0.8
__width_r__ = 0.8
__branch_length_r__ = 0.93
__sec_branch_ang__ = 80
__sec_branch_ang_v__ = 30
__n_leaves__ = 300


def q_prod(sym):
    """Production rule for Q"""
    ret = [LSymbol("!", {"w": sym.parameters["w"]}),
           LSymbol("&", {"a": 90}),
           LSymbol("+", {"a": random() * 360}),
           LSymbol("!", {"w": sym.parameters["bw"]})]
    b_count = int(random() * 2) + 5
    for _ in range(b_count):
        rand = random() * 130 / b_count
        ret.extend([LSymbol("+", {"a": rand}),
                    LSymbol("["),
                    LSymbol("^", {"a": 5 / max(sym.parameters["bl"] * sym.parameters["bl"], 0.05
                                               ) - 30 * (random() * 0.2 + 0.9)}),
                    LSymbol("A", {"l": sym.parameters["bl"], "w": sym.parameters["bw"]}),
                    LSymbol("]"),
                    LSymbol("+", {"a": (360 / b_count) - rand})])
    ret.extend([LSymbol("!", {"w": sym.parameters["w"]}),
                LSymbol("$"),
                LSymbol("F", {"l": sym.parameters["l"],
                              "leaves": int(sym.parameters["l"] * __n_leaves__ / 3),
                              "leaf_d_ang": 20,
                              "leaf_r_ang": 140}),
                LSymbol("Q", {"w": sym.parameters["w"] - 0.2 / 15,
                              "l": sym.parameters["l"] * 0.95,
                              "bw": sym.parameters["bw"] * __width_r__,
                              "bl": sym.parameters["bl"] * __branch_length_r__}),
                LSymbol("%")])
    return ret


def a_prod(sym):
    """Production rule for A"""
    if random() < sym.parameters["l"]:
        ang = random() * __sec_branch_ang_v__ + __sec_branch_ang__
        return [LSymbol("!", {"w": sym.parameters["w"]}),
                LSymbol("^", {"a": random() * 15 - 5}),
                LSymbol("F", {"l": sym.parameters["l"],
                              "leaves": int(sym.parameters["l"] * __n_leaves__),
                              "leaf_d_ang": 40,
                              "leaf_r_ang": 140}),
                LSymbol("-", {"a": ang / 2}),
                LSymbol("["),
                LSymbol("A", {"l": sym.parameters["l"] * __length_r__,
                              "w": sym.parameters["w"] * __width_r__}),
                LSymbol("]"),
                LSymbol("+", {"a": ang}),
                LSymbol("["),
                LSymbol("A", {"l": sym.parameters["l"] * __length_r__,
                              "w": sym.parameters["w"] * __width_r__}),
                LSymbol("]"),
                LSymbol("-", {"a": ang / 2}),
                LSymbol("A", {"l": sym.parameters["l"] * __length_r__,
                              "w": sym.parameters["w"] * __width_r__})]
    else:
        return [LSymbol("!", {"w": sym.parameters["w"]}),
                LSymbol("^", {"a": random() * 15 - 5}),
                LSymbol("F", {"l": sym.parameters["l"],
                              "leaves": int(sym.parameters["l"] * __n_leaves__),
                              "leaf_d_ang": 40,
                              "leaf_r_ang": 140}),
                LSymbol("A", {"l": sym.parameters["l"] * __length_r__,
                              "w": sym.parameters["w"] * __width_r__})]


def system():
    """initialize and iterate the system as appropriate"""
    l_sys = LSystem(axiom=[LSymbol("!", {"w": 0.2}),
                           LSymbol("F", {"l": 0.6}),
                           LSymbol("Q", {"w": 0.2, "bw": 0.05, "l": 0.5, "bl": 0.4})],
                    rules={"Q": q_prod, "A": a_prod},
                    tropism=Vector([0, 0, 0]),
                    thickness=0.5,
                    bendiness=0.5,
                    leaf_shape=2,
                    leaf_scale=0.15,
                    leaf_scale_x=0.3,
                    leaf_bend=0)
    l_sys.iterate_n(15)
    return l_sys
