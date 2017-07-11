"""L System definition for acer"""

from random import random

from ch_trees.chturtle import Vector
from ch_trees.lsystems.lsystem import LSystem, LSymbol

__len_rat__ = 0.9
__n_leaves__ = 15
__width_d__ = 0.4 / 8
__len_d__ = 0.1


def d1_ang():
    """return random first split angle"""
    return random() * 40 + 60


def d2_ang():
    """return random second split angle"""
    return random() * 40 + 100


def branch_ang():
    """return random branch angle"""
    return random() * 15 + 10


def f_prod(sym):
    """Production rule for F"""
    return [LSymbol("F", {"l": sym.parameters["l"], "leaves": 0})]


def a_prod(sym):
    """Production rule for A"""
    rand = random() / (0.24 * sym.parameters["l"] ** 2.5)
    if sym.parameters["l"] == 2:
        rand += 0.5
    if rand < 0.4:
        return [LSymbol("["),
                LSymbol("F", {"l": sym.parameters["l"] / 2}),
                LSymbol("!", {"w": sym.parameters["w"]}),
                LSymbol("&", {"a": branch_ang()}),
                LSymbol("F", {"l": sym.parameters["l"] / 2,
                              "leaves": __n_leaves__,
                              "leaf_d_ang": 40,
                              "leaf_r_ang": 140}),
                LSymbol("A", {"w": sym.parameters["w"] - __width_d__,
                              "l": sym.parameters["l"] - __len_d__}),
                LSymbol("]")]
    elif rand < 0.8:
        return [LSymbol("["),
                LSymbol("F", {"l": sym.parameters["l"] / 2}),
                LSymbol("!", {"w": sym.parameters["w"]}),
                LSymbol("&", {"a": branch_ang()}),
                LSymbol("/", {"a": 90}),
                LSymbol("F", {"l": sym.parameters["l"] / 2,
                              "leaves": __n_leaves__,
                              "leaf_d_ang": 40,
                              "leaf_r_ang": 140}),
                LSymbol("A", {"w": sym.parameters["w"] - __width_d__,
                              "l": sym.parameters["l"] - __len_d__}),
                LSymbol("]"),
                LSymbol("["),
                LSymbol("!", {"w": sym.parameters["w"]}),
                LSymbol("^", {"a": branch_ang()}),
                LSymbol("\\", {"a": 90}),
                LSymbol("F", {"l": sym.parameters["l"] / 2,
                              "leaves": __n_leaves__,
                              "leaf_d_ang": 40,
                              "leaf_r_ang": 140}),
                LSymbol("A", {"w": sym.parameters["w"] - __width_d__,
                              "l": sym.parameters["l"] - __len_d__}),
                LSymbol("]")]
    else:
        return [LSymbol("["),
                LSymbol("F", {"l": sym.parameters["l"] / 2}),
                LSymbol("!", {"w": sym.parameters["w"]}),
                LSymbol("&", {"a": branch_ang()}),
                LSymbol("F", {"l": sym.parameters["l"] / 2,
                              "leaves": __n_leaves__,
                              "leaf_d_ang": 40,
                              "leaf_r_ang": 140}),
                LSymbol("A", {"w": sym.parameters["w"] - __width_d__,
                              "l": sym.parameters["l"] - __len_d__}),
                LSymbol("]"),
                LSymbol("/", {"a": d1_ang()}),
                LSymbol("["),
                LSymbol("!", {"w": sym.parameters["w"]}),
                LSymbol("&", {"a": branch_ang()}),
                LSymbol("F", {"l": sym.parameters["l"] / 2,
                              "leaves": __n_leaves__,
                              "leaf_d_ang": 40,
                              "leaf_r_ang": 140}),
                LSymbol("A", {"w": sym.parameters["w"] - __width_d__,
                              "l": sym.parameters["l"] - __len_d__}),
                LSymbol("]"),
                LSymbol("/", {"a": d2_ang()}),
                LSymbol("["),
                LSymbol("!", {"w": sym.parameters["w"]}),
                LSymbol("&", {"a": branch_ang()}),
                LSymbol("F", {"l": sym.parameters["l"] / 2,
                              "leaves": __n_leaves__,
                              "leaf_d_ang": 40,
                              "leaf_r_ang": 140}),
                LSymbol("A", {"w": sym.parameters["w"] - __width_d__,
                              "l": sym.parameters["l"] - __len_d__}),
                LSymbol("]")]


def system():
    """initialize and iterate the system as appropriate"""
    l_sys = LSystem(axiom=[LSymbol("!", {"w": 0.7}),
                           LSymbol("F", {"l": 0.5}),
                           LSymbol("/", {"a": 45}),
                           LSymbol("A", {"w": 0.4, "l": 2})],
                    rules={"A": a_prod, "F": f_prod},
                    tropism=Vector([0, 0, -1]),
                    thickness=0.5,
                    bendiness=2,
                    leaf_shape=5,
                    leaf_scale=0.2,
                    leaf_bend=0.2)
    l_sys.iterate_n(9)
    return l_sys
