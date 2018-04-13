"""L System class definition for L-system based tree gen system"""

import sys
from math import radians
from random import random
from time import time

import bpy
from ch_trees.chturtle import CHTurtle, Vector
from ch_trees.leaf import Leaf
from mathutils import Quaternion


__console_logging__ = True
windman = bpy.context.window_manager

# ----- GENERAL FUNCTIONS ----- #


def update_log(msg):
    if __console_logging__:
        sys.stdout.write(msg)
        sys.stdout.flush()


def rand_in_range(lower, upper):
    """Generate random number between lower and upper"""
    return (random() * (upper - lower)) + lower


def calc_point_on_bezier(offset, start_point, end_point):
    """Evaluate Bezier curve at offset between bezier_spline_points start_point and end_point"""
    if offset < 0 or offset > 1:
        raise Exception('Offset out of range: %s not between 0 and 1' % offset)
    res = (1 - offset) ** 3 * start_point.co + 3 * (1 - offset) ** 2 * offset * start_point.handle_right + 3 * (
        1 - offset) * offset ** 2 * end_point.handle_left + offset ** 3 * end_point.co
    # initialize new vector to add subclassed methods
    return Vector([res.x, res.y, res.z])


def calc_radius_on_bezier(offset, start_point, end_point):
    """Calculate interpolated radius between bezier_spline_points start_point and end_point"""
    if offset < 0 or offset > 1:
        raise Exception('Offset out of range: %s not between 0 and 1' % offset)
    return offset * end_point.radius + (1 - offset) * start_point.radius


def calc_tangent_to_bezier(offset, start_point, end_point):
    """Calculate tangent to Bezier curve at offset between bezier_spline_points start_point and
    end_point"""
    if offset < 0 or offset > 1:
        raise Exception('Offset out of range: %s not between 0 and 1' % offset)
    res = 3 * (1 - offset) ** 2 * (start_point.handle_right - start_point.co) + 6 * (
        1 - offset) * offset * (end_point.handle_left - start_point.handle_right) + 3 * offset ** 2 * (
        end_point.co - end_point.handle_left)
    # initialize new vector to add subclassed methods
    return Vector([res.x, res.y, res.z])


class LSymbol(object):
    """L-System Symbol"""
    letter = ""
    parameters = {}

    def __init__(self, letter, param=None):
        """Initialise L-symbol with given arguments"""
        self.letter = letter
        self.parameters = param

    def __str__(self):
        """return string representation of l-symbol"""
        if not self.parameters:
            return self.letter
        else:
            return self.letter + str(self.parameters)


class LSystem(object):
    """Simple L-System class"""
    rules = {}
    data = []
    iterations = 0
    tropism = Vector([0, -1, 0])
    thickness = 0.6
    bendiness = 0.5

    leaf_shape = 0
    leaf_bend = 0
    leaf_scale = 0.1
    leaf_scale_x = 1
    blossom_rate = 0
    blossom_shape = 0
    blossom_scale = 1

    tree_object = None

    def __init__(self,
                 axiom,
                 rules,
                 tropism=Vector([0, -1, 0]),
                 thickness=0.6,
                 bendiness=0.5,
                 leaf_shape=0,
                 leaf_bend=0,
                 leaf_scale=0.1,
                 leaf_scale_x=1,
                 blossom_rate=0,
                 blossom_shape=0,
                 blossom_scale=0):
        """initialise L-system with specified parameters"""
        self.data = axiom
        self.rules = rules
        self.tropism = tropism
        self.thickness = thickness
        self.bendiness = bendiness
        self.leaf_shape = leaf_shape
        self.leaf_bend = leaf_bend
        self.leaf_scale = leaf_scale
        self.leaf_scale_x = leaf_scale_x
        self.blossom_rate = blossom_rate
        self.blossom_shape = blossom_shape
        self.blossom_scale = blossom_scale

    def __str__(self):
        """return string representation of l-system"""
        return str(self.data)

    def iterate(self):
        """perform single iteration of l-system"""
        self.iterations += 1
        output = []
        for dat in self.data:
            if dat.letter in self.rules.keys():
                rule = self.rules.get(dat.letter)
                output.extend(rule(dat))
            else:
                output.append(dat)
        self.data = output
        update_log('\r-> {} iterations performed, {} symbols generated'.format(self.iterations, len(self.data)))

    def iterate_n(self, num):
        """perform n iterations of l-system"""
        start = time()
        if self.iterations == 0:
            update_log('\nIterating System\n')
        if num > 0:
            self.iterate()
            self.iterate_n(num - 1)
        else:
            update_log('\nMade %i symbols in %f seconds\n' % (len(self.data), time() - start))

    def parse(self, generate_leaves=True):
        """parse l-system and generate model"""

        try:
            self.tree_obj = bpy.data.objects.new('Tree', None)
        except AttributeError:
            raise Exception('TreeGen :: WARNING: lsystem generation was attempted before Blender was ready')

        bpy.context.scene.objects.link(self.tree_obj)
        bpy.context.scene.objects.active = self.tree_obj

        update_log('\nParsing System\n')

        start_time = time()

        # set up curve object
        curve = bpy.data.curves.new('branches', type='CURVE')
        curve.dimensions = '3D'
        curve.resolution_u = 4
        curve.fill_mode = 'FULL'
        curve.bevel_depth = self.thickness
        curve.bevel_resolution = 10
        curve.use_uv_as_generated = True
        branches_obj = bpy.data.objects.new('Branches', curve)
        bpy.context.scene.objects.link(branches_obj)
        branches_obj.parent = self.tree_obj

        # set up turtle etc.
        turtle = CHTurtle()
        # reset turtle pos/dir because blender keeps it for some reason
        turtle.dir = Vector([0, 0, 1])
        turtle.right = Vector([1, 0, 0])
        turtle.pos = Vector([0, 0, 0])
        trunk = curve.splines.new('BEZIER')
        active_branch = trunk
        active_branch.radius_interpolation = 'CARDINAL'
        active_branch.resolution_u = 2
        leaf_array = []
        stack = []  # keeps track of branches and turtle
        valid_branch = False  # keeps track of whether branch contains any F
        # at_end_of_inv_branch = False
        prev_leaf_ang = rand_in_range(0, 360)

        for ind, dat in enumerate(self.data):
            update_log('\r-> {} of {} symbols parsed'.format(ind + 1, len(self.data)))

            ltr = dat.letter
            if ltr == "!":
                # set width
                turtle.set_width(dat.parameters["w"])
            elif ltr == "F":
                # draw branch
                if not valid_branch:
                    valid_branch = True  # has an F so make branch valid
                old = turtle.pos.copy()
                # apply tropism force
                h_cross_t = turtle.dir.cross(self.tropism)
                alpha = h_cross_t.magnitude
                h_cross_t.normalize()
                turtle.dir.rotate(Quaternion(h_cross_t, radians(alpha)))
                # move turtle and extend spline
                turtle.move(dat.parameters["l"])
                self.add_points_to_bez(active_branch, old, turtle.pos, turtle.width, active_branch == trunk)

                if generate_leaves and "leaves" in dat.parameters and abs(dat.parameters["leaves"]) > 1:
                    prev_leaf_ang = self.add_leaves_to_seg(dat.parameters, active_branch, leaf_array, turtle,
                                                           prev_leaf_ang)

            elif ltr == "A" or ltr == "%":
                # at end of branch so taper width to 0
                if len(active_branch.bezier_points) > 0:
                    active_branch.bezier_points[-1].radius = 0
                # correct for end within invalid branch
                # at_end_of_inv_branch = not valid_branch
            elif ltr == "+":
                # turn left
                turtle.turn_left(dat.parameters["a"])
            elif ltr == "-":
                # turn right
                turtle.turn_right(dat.parameters["a"])
            elif ltr == "&":
                # pitch down
                turtle.pitch_down(dat.parameters["a"])
            elif ltr == "^":
                # pitch up
                turtle.pitch_up(dat.parameters["a"])
            elif ltr == "/":
                # roll right
                turtle.roll_right(dat.parameters["a"])
            elif ltr == "\\":
                # roll left
                turtle.roll_left(dat.parameters["a"])
            elif ltr == "L" and generate_leaves:
                # add a leaf
                leaf_turtle = CHTurtle(turtle)
                leaf_turtle.roll_left(dat.parameters["r_ang"])
                leaf_turtle.pitch_down(dat.parameters["d_ang"])
                leaf_array.append(Leaf(leaf_turtle.pos, leaf_turtle.dir, leaf_turtle.right))
            elif ltr == "[":
                # start branch
                stack.append((active_branch, valid_branch, prev_leaf_ang, CHTurtle(turtle)))
                valid_branch = False  # new branch not valid yet
                # set up new spline
                active_branch = curve.splines.new('BEZIER')
                active_branch.radius_interpolation = 'CARDINAL'
                active_branch.resolution_u = 4
                start_point = active_branch.bezier_points[-1]
                start_point.co = turtle.pos
                start_point.handle_left = turtle.pos - turtle.dir
                start_point.handle_right = turtle.pos + turtle.dir
                start_point.radius = turtle.width
            elif ltr == "]":
                # end branch
                # delete spline if not valid branch
                if not valid_branch:
                    curve.splines.remove(active_branch)
                # restore branch spline, validity, turtle
                if len(stack) > 0:
                    active_branch, valid_branch, prev_leaf_ang, turtle = stack.pop()
                else:
                    raise Exception("Invalid system input - unmatched end branch")
                # if at_end_of_inv_branch:
                #     if len(active_branch.bezier_points) > 0:
                #         active_branch.bezier_points[-1].radius = 0
                #     at_end_of_inv_branch = False
            elif ltr == "$":
                # set turtle to vertical
                turtle.dir = Vector([0, 0, 1])
                turtle.right = Vector([1, 0, 0])

        if active_branch != trunk:
            raise Exception("Invalid system input - missing end branch.")

        update_log('\nSystem parsed in %f seconds\n' % (time() - start_time))

        curve_points = 0
        for spline in curve.splines:
            curve_points += len(spline.bezier_points)

        # TODO do this better, could calc vertices by multiplying by bevel res and curve res?
        update_log('Curve points: %i\n' % curve_points)

        if generate_leaves:
            self.create_leaf_mesh(leaf_array)

    def add_points_to_bez(self, line, point1, point2, width, trunk=False):
        """add point to specific bezier spline"""
        direction = (point2 - point1)
        handle_f = 0.3

        # if exists get middle point in branch
        if len(line.bezier_points) > 1:
            start_point = line.bezier_points[-1]
            # linearly interpolate branch width between start and end of branch
            start_point.radius = line.bezier_points[-2].radius * 0.5 + width * 0.5
            # add bendiness to branch by rotating direction about random axis by random angle
            if self.bendiness > 0:
                acc_dir = direction.rotated(Quaternion(Vector.random(), radians(self.bendiness * (random() * 35 - 20))))
            else:
                acc_dir = direction
            start_point.handle_right = point1 + handle_f * acc_dir
            start_point.handle_left = point1 - handle_f * acc_dir
        else:
            # scale initial handle to match branch length
            start_point = line.bezier_points[-1]
            if trunk:
                # if trunk we also need to set the start width
                start_point.radius = width
                start_point.handle_right = start_point.co + Vector([0, 0, direction.magnitude * handle_f])
            else:
                start_point.handle_right = start_point.co + (start_point.handle_right -
                                                             start_point.co) * direction.magnitude * handle_f
                start_point.handle_left = start_point.co + (start_point.handle_left -
                                                            start_point.co) * direction.magnitude * handle_f

        # add new point to line and set position, direction and width
        line.bezier_points.add()
        end_point = line.bezier_points[-1]
        end_point.co = point2
        end_point.handle_right = point2 + handle_f * direction
        end_point.handle_left = point2 - handle_f * direction
        end_point.radius = width

    def add_leaves_to_seg(self, params, spline, leaf_array, base_turtle, prev_leaf_ang):
        """add leaves to branch segment 'F'"""
        n_leaves = abs(params["leaves"])
        for ind in range(n_leaves):
            offset = ind / (n_leaves - 1)
            leaf_dir_turtle = CHTurtle()
            leaf_dir_turtle.pos = calc_point_on_bezier(offset, spline.bezier_points[-2], spline.bezier_points[-1])
            leaf_dir_turtle.dir = calc_tangent_to_bezier(offset, spline.bezier_points[-2],
                                                         spline.bezier_points[-1]).normalized()
            if leaf_dir_turtle.dir.magnitude > 0:
                leaf_dir_turtle.right = leaf_dir_turtle.dir.cross(base_turtle.dir.cross(base_turtle.right)).normalized()
                prev_leaf_ang += params["leaf_r_ang"] * rand_in_range(0.9, 1.1)
                leaf_dir_turtle.roll_left(prev_leaf_ang)

                rad = calc_radius_on_bezier(offset, spline.bezier_points[-2], spline.bezier_points[-1])
                leaf_pos_turtle = CHTurtle(leaf_dir_turtle)
                leaf_pos_turtle.pitch_down(90)
                leaf_pos_turtle.move(rad * self.thickness)

                leaf_dir_turtle.pitch_down(params["leaf_d_ang"] * rand_in_range(0.9, 1.1))
                leaf_array.append(Leaf(leaf_pos_turtle.pos, leaf_dir_turtle.dir, leaf_dir_turtle.right))
        return prev_leaf_ang

    def create_leaf_mesh(self, leaves_array):
        """Create leaf mesh for tree"""

        if len(leaves_array) <= 0:
            return

        update_log('\nMaking Leaves\n')

        # Start loading spinner
        windman.progress_begin(0, len(leaves_array))

        start_time = time()

        # go through global leaf array populated in branch making phase and add polygons to mesh
        base_leaf_shape = Leaf.get_shape(self.leaf_shape, 1, self.leaf_scale, self.leaf_scale_x)
        base_blossom_shape = Leaf.get_shape(self.blossom_shape, 1, self.blossom_scale, 1)
        leaf_verts = []
        leaf_faces = []
        leaf_count = 0
        blossom_verts = []
        blossom_faces = []
        blossom_count = 0

        for ind, leaf in enumerate(leaves_array):
            if ind % 500 == 0:
                windman.progress_update(ind / 100)

            update_log('\r-> {} leaves made, {} blossoms made'.format(leaf_count, blossom_count))

            if random() < self.blossom_rate:
                self.make_leaf(leaf, base_blossom_shape, blossom_count, blossom_verts,
                               blossom_faces)
                blossom_count += 1
            else:
                self.make_leaf(leaf, base_leaf_shape, leaf_count, leaf_verts, leaf_faces)
                leaf_count += 1

        # set up mesh object
        if leaf_count > 0:
            leaves = bpy.data.meshes.new('leaves')
            leaves_obj = bpy.data.objects.new('Leaves', leaves)
            bpy.context.scene.objects.link(leaves_obj)
            leaves_obj.parent = self.tree_obj
            leaves.from_pydata(leaf_verts, (), leaf_faces)
            # set up UVs for leaf polygons
            leaf_uv = base_leaf_shape[2]
            if leaf_uv:
                leaves.uv_textures.new("leavesUV")
                uv_layer = leaves.uv_layers.active.data
                for seg_dat in range(int(len(leaf_faces) / len(base_leaf_shape[1]))):
                    for vert_dat, vert in enumerate(leaf_uv):
                        uv_layer[seg_dat * len(leaf_uv) + vert_dat].uv = vert
                        # leaves.validate()

        if blossom_count > 0:
            blossom = bpy.data.meshes.new('blossom')
            blossom_obj = bpy.data.objects.new('Blossom', blossom)
            bpy.context.scene.objects.link(blossom_obj)
            blossom.from_pydata(blossom_verts, (), blossom_faces)
            # blossom.validate()

        update_log('\nMade %i leaves and %i blossoms in %f seconds\n' % (leaf_count, blossom_count, time() - start_time))

        windman.progress_end()

    def make_leaf(self, leaf, base_leaf_shape, index, verts_array, faces_array):
        """get vertices and faces for leaf and append to appropriate arrays"""
        verts, faces = leaf.get_mesh(self.leaf_bend, base_leaf_shape, index)
        verts_array.extend(verts)
        faces_array.extend(faces)
