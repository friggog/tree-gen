"""3D Turtle implementation for use in tree generation module, also extends
Blender Vector class with some useful methods"""

from math import radians, degrees, atan2, sqrt
from random import random as random_random

import mathutils
from mathutils import Quaternion


class Vector(mathutils.Vector):
    """Extension of the standard Vector class with some useful methods"""

    @staticmethod
    def random():
        """Normalised vector containing random entries in all dimensions"""
        vec = Vector([random_random(), random_random(), random_random()])
        vec.normalize()
        return vec

    def rotated(self, rotation):
        vec = self.copy()
        vec.rotate(rotation)
        return vec

    def declination(self):
        """Calculate declination of vector in degrees"""
        return degrees(atan2(sqrt(self.x ** 2 + self.y ** 2), self.z))


class CHTurtle(object):
    """3D turtle implementation for use in both L-Systems and Parametric tree
    generation schemes"""
    dir = Vector([0.0, 0.0, 1.0])
    pos = Vector([0.0, 0.0, 0.0])
    right = Vector([1.0, 0.0, 0.0])
    width = 0.0

    def __init__(self, other=None):
        """Copy Constructor"""
        if other is not None:
            self.dir = other.dir.copy()
            self.pos = other.pos.copy()
            self.right = other.right.copy()
            self.width = other.width

    def __str__(self):
        return 'Turtle at %s, direction %s, right %s' % (self.pos, self.dir, self.right)

    def turn_right(self, angle):
        """Turn the turtle right about the axis perpendicular to the direction
        it is facing"""

        axis = (self.dir.cross(self.right))
        axis.normalize()

        rot_quat = Quaternion(axis, radians(angle))

        self.dir.rotate(rot_quat)
        self.dir.normalize()
        self.right.rotate(rot_quat)
        self.right.normalize()

    def turn_left(self, angle):
        """Turn the turtle left about the axis perpendicular to the direction it
        is facing"""

        axis = (self.dir.cross(self.right))
        axis.normalize()

        rot_quat = Quaternion(axis, radians(-angle))

        self.dir.rotate(rot_quat)
        self.dir.normalize()
        self.right.rotate(rot_quat)
        self.right.normalize()

    def pitch_up(self, angle):
        """Pitch the turtle up about the right axis"""
        self.dir.rotate(Quaternion(self.right, radians(angle)))
        self.dir.normalize()

    def pitch_down(self, angle):
        """Pitch the turtle down about the right axis"""
        self.dir.rotate(Quaternion(self.right, radians(-angle)))
        self.dir.normalize()

    def roll_right(self, angle):
        """Roll the turtle right about the direction it is facing"""
        self.right.rotate(Quaternion(self.dir, radians(angle)))
        self.right.normalize()

    def roll_left(self, angle):
        """Roll the turtle left about the direction it is facing"""
        self.right.rotate(Quaternion(self.dir, radians(-angle)))
        self.right.normalize()

    def move(self, distance):
        """Move the turtle in the direction it is facing by specified distance"""
        self.pos += self.dir * distance

    def set_width(self, width):
        """Set the width stored by the turtle"""
        self.width = width
