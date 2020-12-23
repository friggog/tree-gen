"""Leaf module shared by L-System and Parametric tree generators"""

from math import atan2, pi

from ch_trees.chturtle import Vector
from mathutils import Quaternion

import ch_trees.leaf_shapes as leaf_geom


class Leaf(object):
    """Class to store data for each leaf in the system"""
    position = None
    direction = None
    right = None

    def __init__(self, pos, direction, right):
        """Init method for leaf with position, direction and relative x axis"""
        self.position = pos
        self.direction = direction
        self.right = right

    @classmethod
    def get_shape(cls, leaf_type, g_scale, scale, scale_x):
        """returns the base leaf shape mesh"""
        u_v = []

        if leaf_type < 0:  # blossom
            if leaf_type < -3:  # out of range
                leaf_type = -1
            shape = leaf_geom.blossom(abs(leaf_type + 1))

        else:  # leaf
            if leaf_type < 1 or leaf_type > 10:  # is out of range or explicitly default
                leaf_type = 8
            shape = leaf_geom.leaves(leaf_type - 1)

        verts = shape[0]
        faces = shape[1]
        if len(shape) == 3:
            u_v = shape[2]

        for vert in verts:
            vert *= scale * g_scale
            vert.x *= scale_x

        return verts, faces, u_v

    def get_mesh(self, bend, base_shape, index):
        """produce leaf mesh at position of this leaf given base mesh as input"""

        # calculate angles to transform mesh to align with desired direction
        trf = self.direction.to_track_quat('Z', 'Y')
        right_t = self.right.rotated(trf.inverted())
        spin_ang = pi - right_t.angle(Vector([1, 0, 0]))
        spin_ang_quat = Quaternion(Vector([0, 0, 1]), spin_ang)

        # calculate bend transform if needed
        if bend > 0:
            bend_trf_1, bend_trf_2 = self.calc_bend_trf(bend)
        else:
            bend_trf_1 = None

        vertices = []
        for vertex in base_shape[0]:
            # rotate to correct direction
            n_vertex = vertex.copy()
            n_vertex.rotate(spin_ang_quat)
            n_vertex.rotate(trf)

            # apply bend if needed
            if bend > 0:
                n_vertex.rotate(bend_trf_1)
                # n_vertex.rotate(bend_trf_2)

            # move to right position
            n_vertex += self.position

            # add to vertex array
            vertices.append(n_vertex)

        # set face to refer to vertices at correct offset in big vertex list
        index *= len(vertices)

        faces = [[elem + index for elem in face] for face in base_shape[1]]

        return vertices, faces

    def calc_bend_trf(self, bend):
        """calculate the transformations required to 'bend' the leaf out/up from WP"""
        normal = self.direction.cross(self.right)
        theta_pos = atan2(self.position.y, self.position.x)
        theta_bend = theta_pos - atan2(normal.y, normal.x)
        bend_trf_1 = Quaternion(Vector([0, 0, 1]), theta_bend * bend)

        # i think this is what the paper says but the second transform just looks stupid
        # so we just ignore it above

        self.direction.rotate(bend_trf_1)
        self.right.rotate(bend_trf_1)
        normal = self.direction.cross(self.right)
        phi_bend = normal.declination()

        if phi_bend > pi / 2:
            phi_bend = phi_bend - pi

        bend_trf_2 = Quaternion(self.right, phi_bend * bend)

        return bend_trf_1, bend_trf_2
