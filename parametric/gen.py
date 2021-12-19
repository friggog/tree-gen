""" Parametric tree generation system for Blender based on the paper by Weber and Penn """

# standard imports
from collections import namedtuple
from copy import copy
from math import ceil, sqrt, degrees, radians, tan, sin, cos, pow, pi
import time

# Import random functions into a closer namespace to alleviate some lookup costs
import random
from random import random as random_random
from random import getstate as random_getstate
from random import setstate as random_setstate
from random import uniform as random_uniform

# blender imports
import bpy
from enum import Enum
from mathutils import Quaternion

from .. import utilities
from ..chturtle import Vector, CHTurtle
from ..leaf import Leaf
from .tree_params.tree_param import TreeParam

__console_logging__ = True

# ----- GENERAL FUNCTIONS ----- #

update_log = utilities.get_logger(__console_logging__)


def rand_in_range(lower, upper):
    """Generate random number between lower and upper"""

    return (random_random() * (upper - lower)) + lower


def calc_point_on_bezier(offset, start_point, end_point):
    """Evaluate Bezier curve at offset between bezier_spline_points start_point and end_point"""
    if offset < 0 or offset > 1:
        raise Exception('Offset out of range: %s not between 0 and 1' % offset)

    one_minus_offset = 1 - offset

    res = one_minus_offset ** 3 * start_point.co + 3 * one_minus_offset ** 2 * offset * start_point.handle_right + 3 *\
        one_minus_offset * offset ** 2 * end_point.handle_left + offset ** 3 * end_point.co

    # initialize new vector to add subclassed methods
    return Vector(res)


def calc_tangent_to_bezier(offset, start_point, end_point):
    """Calculate tangent to Bezier curve at offset between bezier_spline_points start_point and end_point"""
    if offset < 0 or offset > 1:
        raise Exception('Offset out of range: %s not between 0 and 1' % offset)

    one_minus_offset = 1 - offset

    start_handle_right = start_point.handle_right
    end_handle_left = end_point.handle_left

    res = 3 * one_minus_offset ** 2 * (start_handle_right - start_point.co) + 6 * one_minus_offset * offset *\
        (end_handle_left - start_handle_right) + 3 * offset ** 2 * (end_point.co - end_handle_left)

    # initialize new vector to add subclassed methods
    return Vector(res)


def calc_helix_points(turtle, rad, pitch):
    """ calculates required points to produce helix bezier curve with given radius and pitch in direction of turtle"""
    # alpha = radians(90)
    # pit = pitch/(2*pi)
    # a_x = rad*cos(alpha)
    # a_y = rad*sin(alpha)
    # a = pit*alpha*(rad - a_x)*(3*rad - a_x)/(a_y*(4*rad - a_x)*tan(alpha))
    # b_0 = Vector([a_x, -a_y, -alpha*pit])
    # b_1 = Vector([(4*rad - a_x)/3, -(rad - a_x)*(3*rad - a_x)/(3*a_y), -a])
    # b_2 = Vector([(4*rad - a_x)/3, (rad - a_x)*(3*rad - a_x)/(3*a_y), a])
    # b_3 = Vector([a_x, a_y, alpha*pit])
    # axis = Vector([0, 0, 1])

    # simplifies greatly for case inc_angle = 90
    points = [Vector([0, -rad, -pitch / 4]),
              Vector([(4 * rad) / 3, -rad, 0]),
              Vector([(4 * rad) / 3, rad, 0]),
              Vector([0, rad, pitch / 4])]

    # align helix points to turtle direction and randomize rotation around axis
    trf = turtle.dir.to_track_quat('Z', 'Y')
    spin_ang = rand_in_range(0, 2 * pi)
    rot_quat = Quaternion(Vector([0, 0, 1]), spin_ang)

    for p in points:
        p.rotate(rot_quat)
        p.rotate(trf)

    return points[1] - points[0], points[2] - points[0], points[3] - points[0], turtle.dir.copy()


def point_in_cube(point):
    size = 2
    return abs(point.x) < size and abs(point.y) < size and abs(point.z - size) < size


# ----- MAIN CLASSES ----- #

class BranchMode(Enum):
    """Enum to refer to branching modes"""
    alt_opp = 1
    whorled = 2
    fan = 3


class Stem(object):
    """Class to store data for each stem (branch) in the system, primarily to
    be accessed by its children in calculating their own parameters"""

    __slots__ = (
        'depth', 'curve', 'parent', 'offset', 'radius_limit', 'children', 'length', 'radius',
        'length_child_max'
    )

    def __init__(self, depth, curve, parent=None, offset=0, radius_limit=-1):
        """Init with at depth with curve, possibly parent and offset (for depth > 0)"""

        self.depth = depth
        self.curve = curve
        self.parent = parent
        self.offset = offset
        self.radius_limit = radius_limit

        self.children = []
        self.length = 0
        self.radius = 0
        self.length_child_max = 0

    def copy(self):
        """Copy method for stems"""
        new_stem = Stem(self.depth, self.curve, self.parent, self.offset, self.radius_limit)
        new_stem.length = self.length
        new_stem.radius = self.radius
        new_stem.length_child_max = self.length_child_max
        return new_stem

    def __str__(self):
        return '%s %s %s' % (self.length, self.offset, self.radius)


class Tree(object):
    """Class to store data for the tree"""

    __slots__ = (
        'param', 'generate_leaves', 'leaves_array', 'stem_index', 'tree_scale', 'branch_curves',
        'base_length', 'split_num_error', 'tree_obj', 'trunk_length'
    )

    def __init__(self, param, generate_leaves=True):
        """initialize tree with specified parameters"""

        self.param = param
        self.generate_leaves = generate_leaves
        self.leaves_array = []

        self.stem_index = 0
        self.tree_scale = 0
        self.branch_curves = []
        self.base_length = 0
        self.split_num_error = [0, 0, 0, 0, 0, 0, 0]
        self.tree_obj = None
        self.trunk_length = 0

        # Disable leaf generation
        if not generate_leaves:
            self.param.leaf_blos_num = 0

    def make(self):
        """make the tree"""

        # create parent object
        self.tree_obj = bpy.data.objects.new('Tree', None)
        bpy.context.collection.objects.link(self.tree_obj)
        bpy.context.view_layer.objects.active = self.tree_obj

        # create branches
        self.create_branches()

        # Create leaf mesh if needed and enabled
        if self.generate_leaves:
            self.create_leaf_mesh()

    def points_for_floor_split(self):
        """Calculate Poissonly distributed points for stem start points"""
        array = []

        # calculate approx spacing radius for dummy stem
        self.tree_scale = self.param.g_scale + self.param.g_scale_v
        stem = Stem(0, None)
        stem.length = self.calc_stem_length(stem)
        rad = 2.5 * self.calc_stem_radius(stem)

        # generate points
        for _ in range(self.param.branches[0]):
            point_ok = False
            while not point_ok:
                # distance from center proportional for number of splits, tree scale and stem radius
                dis = sqrt(random_random() * self.param.branches[0] / 2.5 * self.param.g_scale * self.param.ratio)
                # angle random in circle
                theta = rand_in_range(0, 2 * pi)
                pos = Vector([dis * cos(theta), dis * sin(theta), 0])
                # test point against those already in array to ensure it will not intersect
                point_m_ok = True
                for point in array:
                    if (point[0] - pos).magnitude < rad:
                        point_m_ok = False
                        break
                if point_m_ok:
                    point_ok = True
                    array.append((pos, theta))
        return array

    def create_branches(self):
        """Create branches for tree"""

        update_log('\nMaking Stems\n')
        start_time = time.time()

        # Set up container objects and curves for each level
        for level_depth, level_name in enumerate(['Trunk'] + ['Branches' + str(_) for _ in range(1, self.param.levels)]):
            level_curve = bpy.data.curves.new(level_name.lower(), type='CURVE')
            level_curve.dimensions = '3D'
            level_curve.resolution_u = self.param.curve_res[level_depth]
            level_curve.fill_mode = 'FULL'
            level_curve.bevel_depth = 1
            level_curve.bevel_resolution = self.param.bevel_res[level_depth]

            # Removed in Blender 2.82+
            if hasattr(level_curve, 'use_uv_as_generated'):
                level_curve.use_uv_as_generated = True

            level_obj = bpy.data.objects.new(level_name, level_curve)
            bpy.context.collection.objects.link(level_obj)
            level_obj.parent = self.tree_obj

            self.branch_curves.append(level_curve)

        # actually make the branches
        if self.param.branches[0] > 0:
            points = self.points_for_floor_split()

        for ind in range(self.param.branches[0]):
            self.tree_scale = self.param.g_scale + random_uniform(-1, 1) * self.param.g_scale_v
            turtle = CHTurtle()
            turtle.pos = Vector([0, 0, 0])
            turtle.dir = Vector([0, 0, 1])
            turtle.right = Vector([1, 0, 0])

            if self.param.branches[0] > 1:
                # position randomly at base and rotate to face out
                point = points[ind]
                turtle.roll_right(degrees(point[1] - 90))
                turtle.pos = point[0]
            else:
                # start at random rotation
                turtle.roll_right(rand_in_range(0, 360))

            trunk = self.branch_curves[0].splines.new('BEZIER')
            trunk.radius_interpolation = 'CARDINAL'
            trunk.resolution_u = self.param.curve_res[0]

            self.make_stem(turtle, Stem(0, trunk))

        b_time = time.time() - start_time
        update_log('\nStems made: %i in %f seconds\n' % (self.stem_index, b_time))

        curve_points = 0
        for branch_level in self.branch_curves:
            for spline in branch_level.splines:
                curve_points += len(spline.bezier_points)

        update_log('Curve points: %i\n' % curve_points)

        return b_time

    def create_leaf_mesh(self):
        """Create leaf mesh for tree"""

        if len(self.leaves_array) <= 0:
            return

        update_log('\nMaking Leaves\n')
        start_time = time.time()

        # Start loading spinner
        windman = bpy.context.window_manager
        windman.progress_begin(0, len(self.leaves_array))

        # go through global leaf array populated in branch making phase and add polygons to mesh
        base_leaf_shape = Leaf.get_shape(self.param.leaf_shape, self.tree_scale / self.param.g_scale,
                                         self.param.leaf_scale, self.param.leaf_scale_x)

        base_blossom_shape = Leaf.get_shape(-self.param.blossom_shape, self.tree_scale / self.param.g_scale,
                                            self.param.blossom_scale, 1)
        leaf_verts = []
        leaf_faces = []
        leaf_index = 0
        blossom_verts = []
        blossom_faces = []
        blossom_index = 0

        counter = 0
        for leaf in self.leaves_array:
            # Update loading spinner periodically
            if counter % 500 == 0:
                windman.progress_update(counter / 100)
                update_log('\r-> {} leaves made, {} blossoms made'.format(leaf_index, blossom_index))
            if self.param.blossom_rate and random_random() < self.param.blossom_rate:
                verts, faces = leaf.get_mesh(self.param.leaf_bend, base_blossom_shape, blossom_index)
                blossom_verts.extend(verts)
                blossom_faces.extend(faces)
                blossom_index += 1
            else:
                verts, faces = leaf.get_mesh(self.param.leaf_bend, base_leaf_shape, leaf_index)
                leaf_verts.extend(verts)
                leaf_faces.extend(faces)
                leaf_index += 1
            counter += 1

        # set up mesh object
        if leaf_index > 0:
            leaves = bpy.data.meshes.new('leaves')
            leaves_obj = bpy.data.objects.new('Leaves', leaves)
            bpy.context.collection.objects.link(leaves_obj)
            leaves_obj.parent = self.tree_obj
            leaves.from_pydata(leaf_verts, (), leaf_faces)
            # set up UVs for leaf polygons
            leaf_uv = base_leaf_shape[2]

            if leaf_uv:
                leaves.uv_layers.new(name="leavesUV")
                uv_layer = leaves.uv_layers.active.data

                for seg_ind in range(int(len(leaf_faces) / len(base_leaf_shape[1]))):
                    vert_ind = 0
                    for vert in leaf_uv:
                        uv_layer[seg_ind * len(leaf_uv) + vert_ind].uv = vert
                        vert_ind += 1
                        # leaves.validate()

        if blossom_index > 0:
            blossom = bpy.data.meshes.new('blossom')
            blossom_obj = bpy.data.objects.new('Blossom', blossom)
            bpy.context.collection.objects.link(blossom_obj)
            blossom_obj.parent = self.tree_obj
            blossom.from_pydata(blossom_verts, (), blossom_faces)
            # blossom.validate()

        l_time = time.time() - start_time
        update_log('\nMade %i leaves and %i blossoms in %f seconds\n' % (leaf_index, blossom_index, l_time))
        windman.progress_end()

    def make_leaf(self, leaf, base_leaf_shape, index, verts_array, faces_array):
        """get vertices and faces for leaf and append to appropriate arrays"""
        verts, faces = leaf.get_mesh(self.param.leaf_bend, base_leaf_shape, index)
        verts_array.extend(verts)
        faces_array.extend(faces)

    def make_stem(self, turtle, stem, start=0, split_corr_angle=0, num_branches_factor=1, clone_prob=1,
                  pos_corr_turtle=None, cloned_turtle=None):
        """Generate stem given parameters, as well as all children (branches, splits and leaves) via
        recursion"""

        # if the stem is so thin as to be invisible then don't bother to make it
        if 0 <= stem.radius_limit < 0.0001:
            return

        if self.stem_index % 100 == 0:
            update_log('\r-> {} stems made'.format(self.stem_index))

        # use level 3 parameters for any depth greater than this
        depth = stem.depth
        d_plus_1 = depth + 1
        if d_plus_1 > 3:
            d_plus_1 = 3

        # calc length and radius for this stem (only applies for non clones)
        if start == 0:
            stem.length_child_max = self.param.length[d_plus_1] + random_uniform(-1, 1) * self.param.length_v[d_plus_1]
            stem.length = self.calc_stem_length(stem)
            stem.radius = self.calc_stem_radius(stem)
            if depth == 0:
                self.base_length = stem.length * self.param.base_size[0]

        # if the branch origin needs to be repositioned so bevel doesnt sit outside parent
        if pos_corr_turtle:
            # pos_corr_turtle currently positioned on circumference so subtract this branch radius
            # to ensure open ends are never visible
            pos_corr_turtle.move(-min(stem.radius, stem.radius_limit))
            turtle.pos = pos_corr_turtle.pos

        # apply pruning, not required if is a clone, as this will have been tested already
        if cloned_turtle is None and self.param.prune_ratio > 0:
            # save start length and random state
            start_length = stem.length
            r_state = random_getstate()
            split_err_state = copy(self.split_num_error)

            # iteratively scale length by 0.9 until it fits, or remove entirely if we get to 80%
            # reduction
            in_pruning_envelope = self.test_stem(CHTurtle(turtle), stem, start, split_corr_angle, clone_prob)
            while not in_pruning_envelope:
                stem.length *= 0.9
                if stem.length < 0.15 * start_length:
                    # too short to look good so remove allow for semi prune with 0 length
                    if self.param.prune_ratio < 1:
                        stem.length = 0
                        break
                    else:
                        return

                random_setstate(r_state)
                self.split_num_error = split_err_state
                in_pruning_envelope = self.test_stem(CHTurtle(turtle), stem, start, split_corr_angle, clone_prob)

            fitting_length = stem.length
            # apply reduction scaled by prune ratio
            stem.length = start_length * (1 - self.param.prune_ratio) + fitting_length * self.param.prune_ratio
            # recalculate stem radius for new length
            stem.radius = self.calc_stem_radius(stem)
            # restore random state
            random_setstate(r_state)
            self.split_num_error = split_err_state

        # get parameters
        curve_res = int(self.param.curve_res[depth])
        seg_splits = self.param.seg_splits[depth]
        seg_length = stem.length / curve_res

        # calc base segment
        base_seg_ind = ceil(self.param.base_size[0] * int(self.param.curve_res[0]))

        leaf_count = 0
        branch_count = 0
        if depth == self.param.levels - 1 and depth > 0 and self.param.leaf_blos_num != 0:
            # calc base leaf count
            leaf_count = self.calc_leaf_count(stem)
            # correct leaf count for start position along stem
            leaf_count *= 1 - start / curve_res
            # divide by curve_res to get no per seg
            f_leaves_on_seg = leaf_count / curve_res

        else:
            # calc base branch count
            branch_count = self.calc_branch_count(stem)
            # correct branch Count for start position along stem
            branch_count *= 1 - start / curve_res
            # correct for reduced number on clone branches
            branch_count *= num_branches_factor
            # divide by curve_res to get no per seg
            f_branches_on_seg = branch_count / curve_res

        # higher point resolution for flared based
        max_points_per_seg = ceil(max(1.0, 100 / curve_res))

        # set up FS error values
        branch_num_error = 0
        leaf_num_error = 0

        # decide on start rotation for branches/leaves
        # use array to allow other methods to modify the value (otherwise passed by value)
        prev_rotation_angle = [0]
        if self.param.rotate[d_plus_1] >= 0:
            # start at random rotation
            prev_rotation_angle[0] = rand_in_range(0, 360)
        else:
            # on this case prev_rotation_angle used as multiplier to alternate side of branch
            prev_rotation_angle[0] = 1

        # calc helix parameters if needed
        hel_p_0 = hel_p_1 = hel_p_2 = hel_axis = None
        if self.param.curve_v[depth] < 0:
            tan_ang = tan(radians(90 - abs(self.param.curve_v[depth])))
            hel_pitch = 2 * stem.length / curve_res * rand_in_range(0.8, 1.2)
            hel_radius = 3 * hel_pitch / (16 * tan_ang) * rand_in_range(0.8, 1.2)

            # apply full tropism if not trunk/main branch and horizontal tropism if is
            if depth > 1:
                apply_tropism(turtle, self.param.tropism)
            else:
                apply_tropism(turtle, Vector([self.param.tropism[0], self.param.tropism[1], 0]))

            hel_p_0, hel_p_1, hel_p_2, hel_axis = calc_helix_points(turtle, hel_radius, hel_pitch)

        # point resolution for this seg, max_points_per_seg if base, 1 otherwise
        if depth == 0 or self.param.taper[depth] > 1:
            points_per_seg = max_points_per_seg
        else:
            points_per_seg = 2

        for seg_ind in range(start, curve_res + 1):
            remaining_segs = curve_res + 1 - seg_ind

            # set up next bezier point
            if self.param.curve_v[depth] < 0:
                # negative curve_v so helix branch
                pos = turtle.pos
                if seg_ind == 0:
                    new_point = stem.curve.bezier_points[0]
                    new_point.co = pos.copy()
                    new_point.handle_right = hel_p_0 + pos
                    new_point.handle_left = pos.copy()

                else:
                    stem.curve.bezier_points.add(1)
                    new_point = stem.curve.bezier_points[-1]

                    if seg_ind == 1:
                        new_point.co = hel_p_2 + pos
                        new_point.handle_left = hel_p_1 + pos
                        new_point.handle_right = 2 * new_point.co - new_point.handle_left

                    else:
                        prev_point = stem.curve.bezier_points[-2]
                        new_point.co = hel_p_2.rotated(Quaternion(hel_axis, (seg_ind - 1) * pi))
                        new_point.co += prev_point.co
                        dif_p = (hel_p_2 - hel_p_1).rotated(Quaternion(hel_axis, (seg_ind - 1) * pi))
                        new_point.handle_left = new_point.co - dif_p
                        new_point.handle_right = 2 * new_point.co - new_point.handle_left

                turtle.pos = new_point.co.copy()
                turtle.dir = new_point.handle_right.copy().normalized()

            else:
                # normal curved branch
                # get/make new point to be modified
                if seg_ind == start:
                    new_point = stem.curve.bezier_points[0]
                else:
                    turtle.move(seg_length)
                    stem.curve.bezier_points.add(1)
                    new_point = stem.curve.bezier_points[-1]

                # set position and handles of new point
                # if this is a clone then correct initial direction to match original to make
                # split smoother
                new_point.co = turtle.pos.copy()
                if cloned_turtle and seg_ind == start:
                    new_point.handle_left = turtle.pos - cloned_turtle.dir * (stem.length / (curve_res * 3))
                    new_point.handle_right = turtle.pos + cloned_turtle.dir * (stem.length / (curve_res * 3))
                else:
                    new_point.handle_left = turtle.pos - turtle.dir * stem.length / (curve_res * 3)
                    new_point.handle_right = turtle.pos + turtle.dir * stem.length / (curve_res * 3)

            # set radius of new point
            actual_radius = self.radius_at_offset(stem, seg_ind / curve_res)
            new_point.radius = actual_radius

            if seg_ind > start:
                # calc number of splits at this seg (N/A for helix)
                if self.param.curve_v[depth] >= 0:
                    num_of_splits = 0

                    if self.param.base_splits > 0 and depth == 0 and seg_ind == base_seg_ind:
                        # if base_seg_ind and has base splits then override with base split number
                        # take random number of splits up to max of base_splits if negative
                        if self.param.base_splits < 0:
                            num_of_splits = int(random_random() * (abs(self.param.base_splits) + 0.5))
                        else:
                            num_of_splits = int(self.param.base_splits)
                    elif seg_splits > 0 and seg_ind < curve_res and (depth > 0 or seg_ind > base_seg_ind):
                        # otherwise get number of splits from seg_splits and use floyd-steinberg to
                        # fix non-integer values only clone with probability clone_prob
                        if random_random() <= clone_prob:
                            num_of_splits = int(seg_splits + self.split_num_error[depth])
                            self.split_num_error[depth] -= num_of_splits - seg_splits

                            # reduce clone/branch propensity
                            clone_prob /= num_of_splits + 1
                            num_branches_factor /= num_of_splits + 1
                            num_branches_factor = max(0.8, num_branches_factor)

                            # TODO do this better?
                            # if depth != self.param.levels - 1:
                            branch_count *= num_branches_factor
                            f_branches_on_seg = branch_count / curve_res

                # add branches/leaves for this seg
                # if below max level of recursion then draw branches, otherwise draw leaves
                r_state = random_getstate()
                if abs(branch_count) > 0 and depth < self.param.levels - 1:
                    if branch_count < 0:
                        # fan branches
                        if seg_ind == curve_res:
                            branches_on_seg = int(branch_count)
                        else:
                            branches_on_seg = 0

                    else:
                        # get FS corrected branch number
                        branches_on_seg = int(f_branches_on_seg + branch_num_error)
                        branch_num_error -= branches_on_seg - f_branches_on_seg

                    # add branches
                    if abs(branches_on_seg) > 0:
                        self.make_branches(turtle, stem, seg_ind, branches_on_seg, prev_rotation_angle)

                elif abs(leaf_count) > 0 and depth > 0:
                    if leaf_count < 0:
                        # fan leaves
                        if seg_ind == curve_res:
                            leaves_on_seg = leaf_count
                        else:
                            leaves_on_seg = 0
                    else:
                        # get FS corrected number of leaves
                        leaves_on_seg = int(f_leaves_on_seg + leaf_num_error)
                        leaf_num_error -= leaves_on_seg - f_leaves_on_seg

                    # add leaves
                    if abs(leaves_on_seg) > 0:
                        self.make_leaves(turtle, stem, seg_ind, leaves_on_seg, prev_rotation_angle)

                random_setstate(r_state)

                # perform cloning if needed, not allowed for helix (also don't curve/apply tropism as irrelevant)
                if self.param.curve_v[depth] >= 0:
                    if num_of_splits > 0:
                        # calc angles for split
                        is_base_split = (self.param.base_splits > 0 and depth == 0 and seg_ind == base_seg_ind)
                        using_direct_split = self.param.split_angle[depth] < 0

                        if using_direct_split:
                            spr_angle = abs(self.param.split_angle[depth]) + random_uniform(-1, 1) * \
                                self.param.split_angle_v[depth]
                            spl_angle = 0
                            split_corr_angle = 0
                        else:
                            declination = turtle.dir.declination()
                            spl_angle = self.param.split_angle[depth] + random_uniform(-1, 1) * self.param.split_angle_v[
                                depth] - declination
                            spl_angle = max(0, spl_angle)
                            split_corr_angle = spl_angle / remaining_segs
                            spr_angle = - (20 + 0.75 * (30 + abs(declination - 90) * random_random() ** 2))

                        # make clone branches
                        r_state = random_getstate()
                        self.make_clones(turtle, seg_ind, split_corr_angle, num_branches_factor, clone_prob, stem,
                                         num_of_splits, spl_angle, spr_angle, is_base_split)
                        random_setstate(r_state)

                        # apply split to base stem
                        turtle.pitch_down(spl_angle / 2)

                        # apply spread if splitting to 2 and not base split
                        if not is_base_split and num_of_splits == 1:
                            if using_direct_split:
                                turtle.turn_right(spr_angle / 2)
                            else:
                                turtle.dir.rotate(Quaternion(Vector([0, 0, 1]), radians(-spr_angle / 2)))
                                turtle.dir.normalize()
                                turtle.right.rotate(Quaternion(Vector([0, 0, 1]), radians(-spr_angle / 2)))
                                turtle.right.normalize()
                    else:
                        # just apply curve and split correction
                        turtle.turn_left(random_uniform(-1, 1) * self.param.bend_v[depth] / curve_res)
                        curve_angle = self.calc_curve_angle(depth, seg_ind)
                        turtle.pitch_down(curve_angle - split_corr_angle)

                    # apply full tropism if not trunk/main branch and horizontal tropism if is
                    if depth > 1:
                        apply_tropism(turtle, Vector(self.param.tropism))
                    else:
                        apply_tropism(turtle, Vector([self.param.tropism[0], self.param.tropism[1], 0]))

                # increase point resolution at base of trunk and apply flaring effect
                if points_per_seg > 2:
                    self.increase_bezier_point_res(stem, seg_ind, points_per_seg)

        # scale down bezier point handles for flared base of trunk
        if points_per_seg > 2:
            scale_bezier_handles_for_flare(stem, max_points_per_seg)

        self.stem_index += 1

    def test_stem(self, turtle, stem, start=0, split_corr_angle=0, clone_prob=1):
        """Test if stem is inside pruning envelope"""
        # use level 3 parameters for any depth greater than this
        depth = stem.depth
        d_plus_1 = depth + 1
        if d_plus_1 > 3:
            d_plus_1 = 3

        # get parameters
        curve_res = int(self.param.curve_res[depth])
        seg_splits = self.param.seg_splits[depth]
        seg_length = stem.length / curve_res

        # calc base segment
        base_seg_ind = ceil(self.param.base_size[0] * int(self.param.curve_res[0]))

        # decide on start rotation for branches/leaves
        # use array to allow other methods to modify the value (otherwise passed by value)
        prev_rotation_angle = [0]
        if self.param.rotate[d_plus_1] >= 0:
            # start at random rotation
            prev_rotation_angle[0] = rand_in_range(0, 360)
        else:
            # on this case prev_rotation_angle used as multiplier to alternate side of branch
            prev_rotation_angle[0] = 1

        # calc helix parameters if needed
        hel_p_2 = hel_axis = previous_helix_point = None
        if self.param.curve_v[depth] < 0:
            tan_ang = tan(radians(90 - abs(self.param.curve_v[depth])))
            hel_pitch = 2 * stem.length / curve_res * rand_in_range(0.8, 1.2)
            hel_radius = 3 * hel_pitch / (16 * tan_ang) * rand_in_range(0.8, 1.2)
            # apply full tropism if not trunk/main branch and horizontal tropism if is
            if depth > 1:
                apply_tropism(turtle, self.param.tropism)
            else:
                apply_tropism(turtle, Vector([self.param.tropism[0], self.param.tropism[1], 0]))
            _, _, hel_p_2, hel_axis = calc_helix_points(turtle, hel_radius, hel_pitch)

        for seg_ind in range(start, curve_res + 1):
            remaining_segs = curve_res + 1 - seg_ind

            # set up next bezier point
            if self.param.curve_v[depth] < 0:
                # negative curve_v so helix branch
                pos = turtle.pos.copy()
                if seg_ind == 0:
                    turtle.pos = pos
                else:
                    if seg_ind == 1:
                        turtle.pos = hel_p_2 + pos
                    else:
                        hel_p_2.rotate(Quaternion(hel_axis, (seg_ind - 1) * pi))
                        turtle.pos = hel_p_2 + previous_helix_point
                previous_helix_point = turtle.pos.copy()
            else:
                # normal curved branch
                # move turtle
                if seg_ind != start:
                    turtle.move(seg_length)
                    if not (stem.depth == 0 and start < base_seg_ind) and not self.point_inside(turtle.pos):
                        return False

            if seg_ind > start:
                # calc number of splits at this seg (N/A for helix)
                if self.param.curve_v[depth] >= 0:
                    num_of_splits = 0
                    if self.param.base_splits > 0 and depth == 0 and seg_ind == base_seg_ind:
                        # if base_seg_ind and has base splits then override with base split number
                        # take random number of splits up to max of base_splits
                        num_of_splits = int(random_random() * (self.param.base_splits + 0.5))
                    elif seg_splits > 0 and seg_ind < curve_res and (depth > 0 or seg_ind > base_seg_ind):
                        # otherwise get number of splits from seg_splits and use Floyd-Steinberg to
                        # fix non-integer values only clone with probability clone_prob
                        if random_random() <= clone_prob:
                            num_of_splits = int(seg_splits + self.split_num_error[depth])
                            self.split_num_error[depth] -= num_of_splits - seg_splits
                            # reduce clone/branch propensity
                            clone_prob /= num_of_splits + 1

                    # perform cloning if needed, not allowed for helix (also don't curve/apply tropism as irrelevant)
                    if num_of_splits > 0:
                        # calc angles for split
                        is_base_split = (self.param.base_splits > 0 and depth == 0 and seg_ind == base_seg_ind)
                        using_direct_split = self.param.split_angle[depth] < 0
                        if using_direct_split:
                            spr_angle = abs(self.param.split_angle[depth]) + random_uniform(-1, 1) * \
                                self.param.split_angle_v[depth]
                            spl_angle = 0
                            split_corr_angle = 0
                        else:
                            declination = turtle.dir.declination()
                            spl_angle = self.param.split_angle[depth] + random_uniform(-1, 1) * self.param.split_angle_v[
                                depth] - declination
                            spl_angle = max(0, spl_angle)
                            split_corr_angle = spl_angle / remaining_segs
                            spr_angle = - (20 + 0.75 * (30 + abs(declination - 90) * random_random() ** 2))

                        # apply split to base stem
                        turtle.pitch_down(spl_angle / 2)
                        # apply spread if splitting to 2 and not base split
                        if not is_base_split and num_of_splits == 1:
                            if using_direct_split:
                                turtle.turn_left(spr_angle / 2)
                            else:
                                turtle.dir.rotate(Quaternion(Vector([0, 0, 1]), radians(-spr_angle / 2)))
                                turtle.dir.normalize()
                                turtle.right.rotate(Quaternion(Vector([0, 0, 1]), radians(-spr_angle / 2)))
                                turtle.right.normalize()
                    else:
                        # just apply curve and split correction
                        turtle.turn_left(random_uniform(-1, 1) * self.param.bend_v[depth] / curve_res)
                        curve_angle = self.calc_curve_angle(depth, seg_ind)
                        turtle.pitch_down(curve_angle - split_corr_angle)

                    # apply full tropism if not trunk/main branch and horizontal tropism if is
                    if depth > 1:
                        apply_tropism(turtle, Vector(self.param.tropism))
                    else:
                        apply_tropism(turtle, Vector([self.param.tropism[0], self.param.tropism[1], 0]))

        return self.point_inside(turtle.pos)

    def make_clones(self, turtle, seg_ind, split_corr_angle, num_branches_factor, clone_prob,
                    stem, num_of_splits, spl_angle, spr_angle, is_base_split):
        """make clones of branch used if seg_splits or base_splits > 0"""

        using_direct_split = self.param.split_angle[stem.depth] < 0
        stem_depth = self.param.split_angle_v[stem.depth]

        if not is_base_split and num_of_splits > 2 and using_direct_split:
            raise Exception('Only splitting up to 3 branches is supported')

        for split_index in range(num_of_splits):
            # copy turtle for new branch
            n_turtle = CHTurtle(turtle)
            # tip branch down away from axis of stem
            n_turtle.pitch_down(spl_angle / 2)

            # spread out clones
            if is_base_split and not using_direct_split:
                eff_spr_angle = (split_index + 1) * (360 / (num_of_splits + 1)) + random_uniform(-1, 1) * stem_depth

            else:
                if split_index == 0:
                    eff_spr_angle = spr_angle / 2
                else:
                    eff_spr_angle = -spr_angle / 2

            if using_direct_split:
                n_turtle.turn_left(eff_spr_angle)

            else:
                quat = Quaternion(Vector([0, 0, 1]), radians(eff_spr_angle))

                n_turtle.dir.rotate(quat)
                turtle.dir.normalize()
                n_turtle.right.rotate(quat)
                turtle.right.normalize()

            # create new clone branch and set up then recurse
            split_stem = self.branch_curves[stem.depth].splines.new('BEZIER')
            split_stem.resolution_u = stem.curve.resolution_u
            split_stem.radius_interpolation = 'CARDINAL'
            new_stem = stem.copy()
            new_stem.curve = split_stem

            if self.param.split_angle_v[stem.depth] >= 0:
                cloned = turtle
            else:
                cloned = None

            self.make_stem(n_turtle, new_stem, seg_ind, split_corr_angle, num_branches_factor, clone_prob,
                           cloned_turtle=cloned)

    def make_branches(self, turtle, stem, seg_ind, branches_on_seg, prev_rotation_angle, is_leaves=False):
        """Make the required branches for a segment of the stem"""
        start_point = stem.curve.bezier_points[-2]
        end_point = stem.curve.bezier_points[-1]
        branches_array = []
        d_plus_1 = min(3, stem.depth + 1)

        if branches_on_seg < 0:  # fan branches
            for branch_ind in range(abs(int(branches_on_seg))):
                stem_offset = 1
                branches_array.append(self.set_up_branch(turtle, stem, BranchMode.fan, 1, start_point, end_point, stem_offset,
                                                         branch_ind, prev_rotation_angle, abs(branches_on_seg)))
        else:
            base_length = stem.length * self.param.base_size[stem.depth]
            branch_dist = self.param.branch_dist[d_plus_1]
            curve_res = int(self.param.curve_res[stem.depth])

            if branch_dist > 1:  # whorled branches
                # calc number of whorls, will result in a rounded number of branches rather than the
                # exact amount specified by branches_on_seg
                num_of_whorls = int(branches_on_seg / (branch_dist + 1))
                branches_per_whorl = branch_dist + 1
                branch_whorl_error = 0

                for whorl_num in range(num_of_whorls):
                    # calc whorl offset in segment and on stem
                    offset = min(max(0.0, whorl_num / num_of_whorls), 1.0)
                    stem_offset = (((seg_ind - 1) + offset) / curve_res) * stem.length

                    # if not in base area then make the branches
                    if stem_offset > base_length:
                        # calc FS corrected num of branches this whorl
                        branches_this_whorl = int(branches_per_whorl + branch_whorl_error)
                        branch_whorl_error -= branches_this_whorl - branches_per_whorl

                        # set up these branches
                        for branch_ind in range(branches_this_whorl):
                            branches_array.append(self.set_up_branch(turtle, stem, BranchMode.whorled, offset, start_point,
                                                                     end_point, stem_offset, branch_ind, prev_rotation_angle,
                                                                     branches_this_whorl))

                    # rotate start angle for next whorl
                    prev_rotation_angle[0] += self.param.rotate[d_plus_1]
            else:  # alternating or opposite branches
                # ensure even number of branches on segment if near opposite
                for branch_ind in range(branches_on_seg):
                    #  calc offset in segment and on stem
                    if branch_ind % 2 == 0:
                        offset = min(max(0, branch_ind / branches_on_seg), 1)
                    else:
                        offset = min(max(0, (branch_ind - branch_dist) / branches_on_seg), 1)

                    stem_offset = (((seg_ind - 1) + offset) / curve_res) * stem.length
                    # if not in base area then set up the branch
                    if stem_offset > base_length:
                        branches_array.append(self.set_up_branch(turtle, stem, BranchMode.alt_opp, offset,
                                                                 start_point, end_point, stem_offset, branch_ind,
                                                                 prev_rotation_angle))

        # make all new branches from branches_array, passing pos_corr_turtle which will be used to
        # set the position of branch_turtle in this call
        if is_leaves:
            for pos_tur, dir_tur, _, _ in branches_array:
                self.leaves_array.append(Leaf(pos_tur.pos, dir_tur.dir, dir_tur.right))
        else:
            for pos_tur, dir_tur, rad, b_offset in branches_array:
                new_spline = self.branch_curves[d_plus_1].splines.new('BEZIER')
                new_spline.resolution_u = self.param.curve_res[d_plus_1]
                new_spline.radius_interpolation = 'CARDINAL'
                self.make_stem(dir_tur, Stem(d_plus_1, new_spline, stem, b_offset, rad), pos_corr_turtle=pos_tur)

    def make_leaves(self, turtle, stem, seg_ind, leaves_on_seg, prev_rotation_angle):
        """Make the required leaves for a segment of the stem"""
        self.make_branches(turtle, stem, seg_ind, leaves_on_seg,
                           prev_rotation_angle, True)

    def set_up_branch(self, turtle, stem, branch_mode, offset, start_point,
                      end_point, stem_offset, branch_ind, prev_rot_ang, branches_in_group=0):
        """Set up a new branch, creating the new direction and position turtle and orienting them
        correctly and adding the required info to the list of branches to be made"""

        d_plus_1 = min(3, stem.depth + 1)

        # make branch direction turtle
        branch_dir_turtle = make_branch_dir_turtle(turtle, self.param.curve_v[stem.depth] < 0, offset, start_point,
                                                   end_point)

        # calc rotation angle
        if branch_mode is BranchMode.fan:
            if branches_in_group == 1:
                t_angle = 0
            else:
                t_angle = (self.param.rotate[d_plus_1] * (
                    (branch_ind / (branches_in_group - 1)) - 1 / 2)) + random_uniform(-1, 1) * self.param.rotate_v[
                    d_plus_1]
            branch_dir_turtle.turn_right(t_angle)
            radius_limit = 0
        else:
            if branch_mode is BranchMode.whorled:
                r_angle = prev_rot_ang[0] + (360 * branch_ind / branches_in_group) + random_uniform(-1, 1) * \
                    self.param.rotate_v[d_plus_1]
            else:
                r_angle = self.calc_rotate_angle(d_plus_1, prev_rot_ang[0])
                if self.param.rotate[d_plus_1] >= 0:
                    prev_rot_ang[0] = r_angle
                else:
                    prev_rot_ang[0] = -prev_rot_ang[0]

            # orient direction turtle to correct rotation
            branch_dir_turtle.roll_right(r_angle)
            radius_limit = self.radius_at_offset(stem, stem_offset / stem.length)

        # make branch position turtle in appropriate position on circumference
        branch_pos_turtle = make_branch_pos_turtle(branch_dir_turtle, offset, start_point,
                                                   end_point, radius_limit)

        # calc down angle
        d_angle = self.calc_down_angle(stem, stem_offset)

        # orient direction turtle to correct declination
        branch_dir_turtle.pitch_down(d_angle)

        # return branch info
        return branch_pos_turtle, branch_dir_turtle, radius_limit, stem_offset

    def calc_stem_length(self, stem):
        """Calculate length of this stem as defined in paper"""
        if stem.depth == 0:  # trunk
            result = self.tree_scale * (self.param.length[0] + random_uniform(-1, 1) * self.param.length_v[0])
            self.trunk_length = result
        elif stem.depth == 1:  # first level
            result = stem.parent.length * stem.parent.length_child_max * self.shape_ratio(
                self.param.shape, (stem.parent.length - stem.offset) / (
                    stem.parent.length - self.base_length))
        else:  # other
            result = stem.parent.length_child_max * (stem.parent.length - 0.7 * stem.offset)
        return max(0, result)

    def calc_stem_radius(self, stem):
        """Calculate radius of this stem as defined in paper"""
        if stem.depth == 0:  # trunk
            result = stem.length * self.param.ratio * self.param.radius_mod[0]
        else:  # other
            result = self.param.radius_mod[stem.depth] * stem.parent.radius * pow((
                stem.length / stem.parent.length), self.param.ratio_power)
            result = max(0.005, result)
            result = min(stem.radius_limit, result)
        return result

    def calc_curve_angle(self, depth, seg_ind):
        """Calculate curve angle for segment number seg_ind on a stem"""
        curve = self.param.curve[depth]
        curve_v = self.param.curve_v[depth]
        curve_back = self.param.curve_back[depth]
        curve_res = int(self.param.curve_res[depth])
        if curve_back == 0:
            curve_angle = curve / curve_res
        else:
            if seg_ind < curve_res / 2.0:
                curve_angle = curve / (curve_res / 2.0)
            else:
                curve_angle = curve_back / (curve_res / 2.0)
        curve_angle += random_uniform(-1, 1) * (curve_v / curve_res)
        return curve_angle

    def calc_down_angle(self, stem, stem_offset):
        """calc down angle as defined in paper"""
        d_plus_1 = min(stem.depth + 1, 3)
        if self.param.down_angle_v[d_plus_1] >= 0:
            d_angle = self.param.down_angle[d_plus_1] + random_uniform(-1, 1) * self.param.down_angle_v[d_plus_1]
        else:
            d_angle = self.param.down_angle[d_plus_1] + (self.param.down_angle_v[d_plus_1] * (
                1 - 2 * self.shape_ratio(0, (stem.length - stem_offset) / (stem.length * (
                    1 - self.param.base_size[stem.depth])))))
            # introduce some variance to improve visual result
            d_angle += random_uniform(-1, 1) * abs(d_angle * 0.1)
        return d_angle

    def calc_rotate_angle(self, depth, prev_angle):
        """calc rotate angle as defined in paper, limit to 0-360"""
        if self.param.rotate[depth] >= 0:
            r_angle = (prev_angle + self.param.rotate[depth] + random_uniform(-1, 1) * self.param.rotate_v[depth]) % 360
        else:
            r_angle = prev_angle * (180 + self.param.rotate[depth] + random_uniform(-1, 1) * self.param.rotate_v[depth])
        return r_angle

    def calc_leaf_count(self, stem):
        """Calculate leaf count of this stem as defined in paper"""
        if self.param.leaf_blos_num >= 0:
            # scale number of leaves to match global scale and taper
            leaves = self.param.leaf_blos_num * self.tree_scale / self.param.g_scale
            result = leaves * (stem.length / (stem.parent.length_child_max * stem.parent.length))
        else:  # fan leaves
            return self.param.leaf_blos_num
        return result

    def calc_branch_count(self, stem):
        """Calculate branch count of this stem as defined in paper"""
        d_p_1 = min(stem.depth + 1, 3)
        if stem.depth == 0:
            result = self.param.branches[d_p_1] * (random_random() * 0.2 + 0.9)
        else:
            if self.param.branches[d_p_1] < 0:
                result = self.param.branches[d_p_1]
            elif stem.depth == 1:
                result = self.param.branches[d_p_1] * (0.2 + 0.8 * (
                    stem.length / stem.parent.length) / stem.parent.length_child_max)
            else:
                result = self.param.branches[d_p_1] * (1.0 - 0.5 * stem.offset / stem.parent.length)
        return result / (1 - self.param.base_size[stem.depth])

    def shape_ratio(self, shape, ratio):
        """Calculate shape ratio as defined in paper"""
        if shape == 1:  # spherical
            result = 0.2 + 0.8 * sin(pi * ratio)
        elif shape == 2:  # hemispherical
            result = 0.2 + 0.8 * sin(0.5 * pi * ratio)
        elif shape == 3:  # cylindrical
            result = 1.0
        elif shape == 4:  # tapered cylindrical
            result = 0.5 + 0.5 * ratio
        elif shape == 5:  # flame
            if ratio <= 0.7:
                result = ratio / 0.7
            else:
                result = (1.0 - ratio) / 0.3
        elif shape == 6:  # inverse conical
            result = 1.0 - 0.8 * ratio
        elif shape == 7:  # tend flame
            if ratio <= 0.7:
                result = 0.5 + 0.5 * ratio / 0.7
            else:
                result = 0.5 + 0.5 * (1.0 - ratio) / 0.3
        elif shape == 8:  # envelope
            if ratio < 0 or ratio > 1:
                result = 0.0
            elif ratio < 1 - self.param.prune_width_peak:
                result = pow(ratio / (1 - self.param.prune_width_peak),
                             self.param.prune_power_high)
            else:
                result = pow((1 - ratio) / (1 - self.param.prune_width_peak),
                             self.param.prune_power_low)
        else:  # conical (0)
            result = 0.2 + 0.8 * ratio
        return result

    def radius_at_offset(self, stem, z_1):
        """ calculate radius of stem at offset z_1 along it """
        n_taper = self.param.taper[stem.depth]

        if n_taper < 1:
            unit_taper = n_taper
        elif n_taper < 2:
            unit_taper = 2 - n_taper
        else:
            unit_taper = 0
        taper = stem.radius * (1 - unit_taper * z_1)

        if n_taper < 1:
            radius = taper
        else:
            z_2 = (1 - z_1) * stem.length
            if n_taper < 2 or z_2 < taper:
                depth = 1
            else:
                depth = n_taper - 2
            if n_taper < 2:
                z_3 = z_2
            else:
                z_3 = abs(z_2 - 2 * taper * int(z_2 / (2 * taper) + 0.5))
            if n_taper < 2 and z_3 >= taper:
                radius = taper
            else:
                radius = (1 - depth) * taper + depth * sqrt(pow(taper, 2) - pow((z_3 - taper), 2))
        if stem.depth == 0:
            y_val = max(0, 1 - 8 * z_1)
            flare = self.param.flare * ((pow(100, y_val) - 1) / 100) + 1
            radius *= flare
        return radius

    def increase_bezier_point_res(self, stem, seg_ind, points_per_seg):
        """add in new points in appropriate positions along curve and modify radius for flare"""
        # need a copy of the end point as it is moved during the process, but also used for
        # calculations throughout
        curve_res = int(self.param.curve_res[stem.depth])
        seg_end_point = stem.curve.bezier_points[-1]
        FakeSplinePoint = namedtuple('FakeSplinePoint', ['co', 'handle_left', 'handle_right'])
        end_point = FakeSplinePoint(seg_end_point.co.copy(),
                                    seg_end_point.handle_left.copy(),
                                    seg_end_point.handle_right.copy())
        seg_start_point = stem.curve.bezier_points[-2]
        start_point = FakeSplinePoint(seg_start_point.co.copy(),
                                      seg_start_point.handle_left.copy(),
                                      seg_start_point.handle_right.copy())
        for k in range(0, points_per_seg):
            # add new point and position
            # at this point the normals are left over-sized in order to allow for evaluation of the
            # original curve in later steps
            # once the stem is entirely built we then go back and scale the handles
            offset = k / (points_per_seg - 1)
            if k == 0:
                curr_point = seg_start_point
            else:
                if k == 1:
                    curr_point = seg_end_point
                else:
                    stem.curve.bezier_points.add(1)
                    curr_point = stem.curve.bezier_points[-1]
                if k == points_per_seg - 1:
                    curr_point.co = end_point.co
                    curr_point.handle_left = end_point.handle_left
                    curr_point.handle_right = end_point.handle_right
                else:
                    curr_point.co = calc_point_on_bezier(offset, start_point, end_point)
                    # set handle to match direction of curve
                    tangent = calc_tangent_to_bezier(offset, start_point, end_point).normalized()
                    # and set the magnitude to match other control points
                    dir_vec_mag = (end_point.handle_left - end_point.co).magnitude
                    curr_point.handle_left = curr_point.co - tangent * dir_vec_mag
                    curr_point.handle_right = curr_point.co + tangent * dir_vec_mag

            curr_point.radius = self.radius_at_offset(stem, (offset + seg_ind - 1) / curve_res)

    def point_inside(self, point):
        """Check if point == inside pruning envelope, from WP 4.6"""
        # return point_in_cube(Vector([point.x, point.y, point.z - self.base_length]))
        dist = sqrt(point.x ** 2 + point.y ** 2)
        ratio = (self.tree_scale - point.z) / (self.tree_scale * (1 - self.param.base_size[0]))
        inside = (dist / self.tree_scale) < (self.param.prune_width * self.shape_ratio(8, ratio))
        # inside = inside and (point.x > -0.7 or point.z > 5.3)
        return inside


# ------ RELATED FUNCTIONS ------ #

def make_branch_pos_turtle(dir_turtle, offset, start_point, end_point, radius_limit):
    """Create and setup the turtle for the position of a new branch, also returning the radius
    of the parent to use as a limit for the child"""

    dir_turtle.pos = calc_point_on_bezier(offset, start_point, end_point)
    branch_pos_turtle = CHTurtle(dir_turtle)
    branch_pos_turtle.pitch_down(90)
    branch_pos_turtle.move(radius_limit)

    return branch_pos_turtle


def make_branch_dir_turtle(turtle, helix, offset, start_point, end_point):
    """Create and setup the turtle for the direction of a new branch"""

    branch_dir_turtle = CHTurtle()
    tangent = calc_tangent_to_bezier(offset, start_point, end_point)
    tangent.normalize()
    branch_dir_turtle.dir = tangent

    if helix:
        # approximation to actual normal to preserve for helix
        tan_d = calc_tangent_to_bezier(offset + 0.0001, start_point, end_point).normalized()
        branch_dir_turtle.right = branch_dir_turtle.dir.cross(tan_d)
    else:
        # generally curve lines in plane define by turtle.right, so is fair approximation to take new right as being
        # parallel to this, ie find the turtle up vector (in the plane) and cross with tangent (assumed in the plane)
        # to get the new direction - this doesn't hold for the helix
        branch_dir_turtle.right = turtle.dir.cross(turtle.right).cross(branch_dir_turtle.dir)

    return branch_dir_turtle


def apply_tropism(turtle, tropism_vector):
    """Apply tropism_vector to turtle direction"""
    h_cross_t = turtle.dir.cross(tropism_vector)
    # calc angle to rotate by (from ABoP) multiply to achieve accurate results from WP attractionUp param
    alpha = 10 * h_cross_t.magnitude
    h_cross_t.normalize()
    # rotate by angle about axis perpendicular to turtle direction and tropism vector
    turtle.dir.rotate(Quaternion(h_cross_t, radians(alpha)))
    turtle.dir.normalize()
    turtle.right.rotate(Quaternion(h_cross_t, radians(alpha)))
    turtle.right.normalize()


def scale_bezier_handles_for_flare(stem, max_points_per_seg):
    """Reduce length of bezier handles to account for increased density of points on curve for
    flared base of trunk"""
    for point in stem.curve.bezier_points:
        point.handle_left = point.co + (point.handle_left - point.co) / max_points_per_seg
        point.handle_right = point.co + (point.handle_right - point.co) / max_points_per_seg


def construct(params, seed=0, generate_leaves=True):
    """Construct the tree"""

    if seed == 0:
        seed = int(random_random() * 9999999)
        bpy.context.scene.last_seed = seed

    update_log('\nUsing seed: {}\n'.format(seed))

    random.seed(seed)

    t = Tree(TreeParam(params), generate_leaves)
    t.make()

    ret_obj = t.tree_obj

    # Try to get unneeded data out of memory ASAP
    del t.leaves_array
    del t.branch_curves
    del t

    return ret_obj
