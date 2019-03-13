import bpy

import traceback
import threading
import sys
import os
import time
import pprint
from copy import deepcopy

from ch_trees import parametric
from ch_trees.parametric.tree_params import tree_param


update_log = parametric.gen.update_log


def _get_addon_path_details():
    addon_path_parts = __file__.split(os.path.sep)[:-1]
    addon_name = addon_path_parts[-1]
    addon_path = os.path.sep.join(addon_path_parts)
    return addon_path_parts, addon_name, addon_path


def _get_tree_types(self=None, context=None):
    # Scan the the ch_trees addon folder for parameters and definitions,
    # then return two EnumProperty objects for use as the drop-down tree selector
    addon_path_parts, addon_name, addon_path = _get_addon_path_details()
    module_parts = ['parametric', 'tree_params']
    # Build the drop-down menus
    path = os.path.join(addon_path, *module_parts)
    files = [f.split('.')[0] for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    files.remove('tree_param')
    # ex: ['ch_trees.parametric.tree_params.quaking_aspen', ...]
    modules = ['{}.{}.{}'.format(addon_name, '.'.join(module_parts), f) for f in files]
    # ex: 'Quaking Aspen'
    titles = [f.replace('_', ' ').title() for f in files]
    enum_options = [(module, title, title) for module, title in zip(modules, titles)]
    return enum_options


class TreeGen(bpy.types.Operator):
    """Generate a tree"""

    bl_idname = "object.tree_gen"
    bl_category = "TreeGen"
    bl_label = "Generate Tree"
    bl_options = {'REGISTER'}

    # ---
    # Note: an empty-string 'name' parameter removes the default label from inputs

    _scene = bpy.types.Scene
    _props = bpy.props

    # Drop-downs containing tree options for each generation method
    # These are switched between by TreeGenPanel.draw() based on the state of tree_gen_method_input
    parametric_items = _get_tree_types()

    # Nothing exciting here. Seed, leaf toggle, and simplify geometry toggle.
    _scene.seed_input = _props.IntProperty(name="", default=1, min=0, max=9999999)
    _scene.generate_leaves_input = _props.BoolProperty(name="Generate Leaves/Blossom", default=True)
    _scene.simplify_geometry_input = _props.BoolProperty(name="Simplify Branch Geometry", default=False)

    # Render inputs; auto-fill path input with user's home directory
    _scene.render_input = _props.BoolProperty(name="Render", default=False)
    render_output_path = os.path.sep.join((os.path.expanduser('~'), 'treegen_render.png'))
    _scene.render_output_path_input = _props.StringProperty(name="", default=render_output_path)

    # ======================
    # Tree customizer inputs

    # Tree Shape
    tree_shape_options = (
        ('0', 'Conical', 'Conical'), ('1', 'Spherical', 'Spherical'), ('2', 'Hemispherical', 'Hemispherical'),
        ('3', 'Cylindrical', 'Cylindrical'), ('4', 'Tapered Cylindrical', 'Tapered Cylindrical'),
        ('5', 'Flame', 'Flame'), ('6', 'Inverse Conical', 'Inverse Conical'), ('7', 'Tend Flame', 'Tend Flame'), ('8', 'Custom', 'Custom')
    )
    _scene.tree_shape_input = _props.EnumProperty(name="", description="Controls shape of the tree by altering the first level branch length. Custom uses the envelope defined by the pruning parameters to control the tree shape directly rather than through pruning", items=tree_shape_options, default='7')

    _scene.tree_prune_ratio_input = _props.FloatProperty(name="", description="Fractional amount by which the effect of pruning is applied", default=0, min=0, max=1)
    _scene.tree_prune_width_input = _props.FloatProperty(name="", description="Width of the pruning envelope as a fraction of its height (the maximum height of the tree)", default=.5, min=.000001, max=200)
    _scene.tree_prune_width_peak_input = _props.FloatProperty(name="", description="The fractional distance from the bottom of the pruning up at which the peak width occurs", default=.5, min=0, max=200)
    _scene.tree_prune_power_low_input = _props.FloatProperty(name="", description="The curvature of the lower section of the pruning envelope. < 1 results in a convex shape, > 1 in concave", default=.5, min=-200, max=200)  # <1 convex, >1 concave
    _scene.tree_prune_power_high_input = _props.FloatProperty(name="", description="The curvature of the upper section of the pruning envelope. < 1 results in a convex shape, > 1 in concave", default=.5, min=-200, max=200)  # <1 convex, >1 concave

    # Size of base
    _scene.tree_base_size_input = _props.FloatVectorProperty(name="", description="Proportion of branch on which no child branches/leaves are spawned", default=(0.3, 0.02, 0.02, 0.02), size=4, min=.001)

    # Base split count
    _scene.tree_base_splits_input = _props.IntProperty(name="", description="Number of splits at base height on trunk, if negative then the number of splits will be randomly chosen up to a maximum of |base splits|", default=0, min=-5, max=5)

    # Overall tree scale and scale variation
    _scene.tree_g_scale_input = _props.FloatProperty(name="", description="Scale of the entire tree", default=13, min=.000001, max=150)
    _scene.tree_g_scale_v_input = _props.FloatProperty(name="", description="Maximum variation in size of the entire tree", default=3, min=0, max=149.99)

    # Level count
    _scene.tree_levels_input = _props.IntProperty(name="", description="Number of levels of branching, typically 3 or 4", default=3, min=1, max=4)

    # Ratio and ratio power
    _scene.tree_ratio_input = _props.FloatProperty(name="", description="Ratio of the stem length to radius", default=.015, min=.000001, max=1)
    _scene.tree_ratio_power_input = _props.FloatProperty(name="", description="How drastically the branch radius is reduced between branching levels", default=1.2, min=0, max=5)

    # Flare
    _scene.tree_flare_input = _props.FloatProperty(name="", description="How much the radius at the base of the trunk increases", default=.6, min=0, max=10)

    # Branch appearance
    _scene.tree_branches_input = _props.IntVectorProperty(name="", description="The maximum number of child branches at a given level on each parent branch. The first level parameter indicates the number of trunks coming from the floor, positioned in a rough circle facing outwards (see bamboo)", default=(1, 50, 30, 1), size=4, min=1, max=500)

    _scene.tree_length_input = _props.FloatVectorProperty(name="", description="The length of branches at a given level as a fraction of their parent branch’s length", default=(1, 0.3, 0.6, 0), size=4, min=0, max=1)
    _scene.tree_length_v_input = _props.FloatVectorProperty(name="", description="Maximum variation in branch length", default=(0, 0, 0, 0), size=4, min=-0, max=1)

    _scene.tree_branch_dist_input = _props.FloatVectorProperty(name="", description="Controls the distribution of branches along their parent stem. 0 indicates fully alternate branching, interpolating to fully opposite branching at 1. Values > 1 indicate whorled branching (as on fir trees) with n + 1 branches in each whorl. Fractional values result in a rounded integer number of branches in each whorl", default=(0, 0, 0, 0), size=4, min=0, max=1)

    _scene.tree_taper_input = _props.FloatVectorProperty(name="", description="Controls the tapering of the radius of each branch along its length. If < 1 then the branch tapers to that fraction of its base radius at its end, so a value 1 results in conical tapering. If =2 the radius remains uniform until the end of the stem where the branch is rounded off in a hemisphere, fractional values between 1 and 2 interpolate between conical tapering and this rounded end. Values > 2 result in periodic tapering with a maximum variation in radius equal to the value − 2 of the base radius - so a value of 3 results in a series of adjacent spheres (see palm trunk)", default=(1, 1, 1, 1), size=4, min=-0, max=3)
    _scene.tree_radius_mod_input = _props.FloatVectorProperty(name="", description="", default=(1, 1, 1, 1), size=4, min=0, max=1)

    _scene.tree_bend_v_input = _props.FloatVectorProperty(name="", description="Maximum angle by which the direction of the branch may change from start to end, rotating about the branch’s local y-axis. Applied randomly at each segment", default=(0, 50, 0, 0), size=4, min=0, max=360)

    _scene.tree_curve_res_input = _props.FloatVectorProperty(name="", description="Number of segments in each branch", default=(5, 5, 3, 1), size=4, min=1, max=10)
    _scene.tree_curve_input = _props.FloatVectorProperty(name="", description="Angle by which the direction of the branch will change from start to end, rotating about the branch’s local x-axis", default=(0, -40, -40, 0), size=4, min=-360, max=360)
    _scene.tree_curve_v_input = _props.FloatVectorProperty(name="", description="Maximum variation in curve angle of a branch. Applied randomly at each segment", default=(20, 50, 75, 0), size=4, min=-360, max=360)
    _scene.tree_curve_back_input = _props.FloatVectorProperty(name="", description="Angle in the opposite direction to the curve that the branch will curve back from half way along, creating S shaped branches", default=(0, 0, 0, 0), size=4, min=-360, max=360)

    _scene.tree_seg_splits_input = _props.FloatVectorProperty(name="", description="Maximum number of dichotomous branches (splits) at each segment of a branch, fractional values are distributed along the branches semi-randomly", default=(0, 0, 0, 0), size=4, min=0, max=2)
    _scene.tree_split_angle_input = _props.FloatVectorProperty(name="", description="Angle between dichotomous branches", default=(40, 0, 0, 0), size=4, min=0, max=360)
    _scene.tree_split_angle_v_input = _props.FloatVectorProperty(name="", description="Maximum variation in angle between dichotomous branches", default=(5, 0, 0, 0), size=4, min=0, max=360)

    # "the turning of all or part of an organism in a particular direction in response to an external stimulus"
    _scene.tree_tropism_input = _props.FloatVectorProperty(name="", description="Influence upon the growth direction of the tree in the x, y and z directions, the z element only applies to branches in the second level and above. Useful for simulating the effects of gravity, sunlight and wind", default=(0, 0, 0.5), size=3, min=-10, max=10)

    _scene.tree_down_angle_input = _props.FloatVectorProperty(name="", description="Controls the angle of the direction of a child branch away from that of its parent", default=(0, 60, 45, 45), size=4, min=0, max=360)
    _scene.tree_down_angle_v_input = _props.FloatVectorProperty(name="", description="Maximum variation in down angle, if < 0 then the value of down angle is distributed along the parent stem", default=(0, -50, 10, 10), size=4, min=-360, max=360)

    _scene.tree_rotate_input = _props.FloatVectorProperty(name="", description="Angle around the parent branch between each child branch. If < 0 then child branches are directed this many degrees away from the downward direction in their parent's local basis (see palm leaves). For fanned branches, the fan will spread by this angle and for whorled branches, each whorl will rotate by this angle", default=(0, 140, 140, 77), size=4, min=-360, max=360)
    _scene.tree_rotate_v_input = _props.FloatVectorProperty(name="", description="Maximum variation in angle between branches. For fanned and whorled branches, each branch will vary in angle by this much", default=(0, 0, 0, 0), size=4, min=0)

    # ----
    # Cumulative count of leaves and blossoms on each of the deepest level of branches
    _scene.tree_leaf_blos_num_input = _props.IntProperty(name="", description="Number of leaves or blossom on each of the deepest level of branches", default=40, min=-1000, max=3000)

    # Leaf shape
    leaf_shape_options = (
        ('1', 'Ovate', 'Ovate'), ('2', 'Linear', 'Linear'), ('3', 'Cordate', 'Cordate'), ('4', 'Maple', 'Maple'),
        ('5', 'Palmate', 'Palmate'), ('6', 'Spiky Oak', 'Spiky Oak'), ('7', 'Rounded Oak', 'Rounded Oak'),
        ('8', 'Elliptic', 'Elliptic'), ('9', 'Rectangle', 'Rectangle'), ('10', 'Triangle', 'Triangle')
    )
    _scene.tree_leaf_shape_input = _props.EnumProperty(name="", description="Predefined leaf shapes, rectangle is easiest if wishing to use an image texture", items=leaf_shape_options, default='3')

    # Leaf scale
    _scene.tree_leaf_scale_input = _props.FloatProperty(name="", description="Overall leaf scale", default=.17, min=.0001, max=1000)

    # Leaf scale in x-direction
    _scene.tree_leaf_scale_x_input = _props.FloatProperty(name="", description="Leaf scale in the x-direction (width)", default=1, min=.0001, max=1000)

    # Amount of leaf bend towards sunlight
    _scene.tree_leaf_bend_input = _props.FloatProperty(name="", description="Fractional amount by which leaves are reoriented to face the light (upwards and outwards)", default=.6, min=0, max=1)

    # ----
    # Blossom configuration
    # _scene.tree_generate_blossoms_input = _props.BoolProperty(name="Generate blossoms", default=False)

    blossom_shape_options = (('1', 'Cherry', 'Cherry'), ('2', 'Orange', 'Orange'), ('3', 'Magnolia', 'Magnolia'))
    _scene.tree_blossom_shape_input = _props.EnumProperty(name="", description="Predefined blossom shapes", items=blossom_shape_options, default='1')

    # Blossom scale
    _scene.tree_blossom_scale_input = _props.FloatProperty(name="", description="Overall blossom scale", default=0.1, min=.0001, max=1)

    # Rate at which blossoms occur relative to leaves
    _scene.tree_blossom_rate_input = _props.FloatProperty(name="", description="Fractional rate at which blossom occurs relative to leaves", default=0, min=0, max=1)

    # Save location for custom tree params
    _scene.custom_tree_save_overwrite_input = _props.BoolProperty(name="Overwrite if File Exists", default=False)
    tree_save_location = os.path.sep.join((_get_addon_path_details()[2], 'parametric', 'tree_params', 'my_custom_tree.py'))
    _scene.custom_tree_save_location_input = _props.StringProperty(name="", default=tree_save_location)

    # Load custom params
    _scene.custom_tree_load_params_input = _props.EnumProperty(name="", default="ch_trees.parametric.tree_params.quaking_aspen", items=parametric_items)

    # ---
    def execute(self, context):
        # "Generate Tree" button callback
        params = TreeGen.get_params_from_customizer(context)
        threading.Thread(daemon=True, target=self._construct, kwargs={'context': context, 'params': params}).start()
        return {'FINISHED'}

    # ---
    def _construct(self, context, params):
        # The generator's main thread.
        # Handles conditional logic for generation method selection.
        scene = context.scene
        update_log('\n** Generating Tree **\n')
        try:
            start_time = time.time()
            parametric.gen.construct(params, scene.seed_input, scene.render_input, scene.render_output_path_input,
                                     scene.generate_leaves_input)

            if scene.simplify_geometry_input:
                from . import utilities
                # update_log doesn't get a chance to print before Blender locks up, so a direct print is necessary
                sys.stdout.write('Simplifying tree branch geometry. Blender will appear to crash; be patient.\n')
                sys.stdout.flush()

                # Catch exceptions and print them as strings
                # This will hopefully reduce random crashes
                try:
                    utilities.simplify_branch_geometry(context)
                    update_log('Geometry simplification complete\n\n')

                except Exception:
                    update_log('\n{}\n'.format(traceback.format_exc()))
                    update_log('Geometry simplification failed\n\n')

            update_log('Tree generated in {:.6f} seconds\n\n'.format(time.time() - start_time))

        # Reduce chance of Blender crashing when generation fails or the user does something ill-advised
        except Exception:
            sys.stdout.write('\n{}\n'.format(traceback.format_exc()))
            sys.stdout.write('Tree generation failed\n\n')
            sys.stdout.flush()

    # ----
    @staticmethod
    def get_params_from_customizer(context):
        scene = context.scene

        param_names = ['shape', 'g_scale', 'g_scale_v', 'levels', 'ratio', 'flare', 'ratio_power',
                       'base_size', 'down_angle', 'down_angle_v', 'rotate', 'rotate_v', 'branches',
                       'length', 'length_v', 'taper', 'seg_splits', 'split_angle', 'split_angle_v', 'curve_res',
                       'curve', 'curve_back', 'curve_v', 'bend_v', 'branch_dist', 'radius_mod', 'leaf_blos_num',
                       'leaf_shape', 'leaf_scale', 'leaf_scale_x', 'leaf_bend', 'blossom_shape', 'blossom_scale',
                       'blossom_rate', 'tropism', 'prune_ratio', 'prune_width', 'prune_width_peak',
                       'prune_power_low', 'prune_power_high', 'base_splits']

        params = {}
        for name in param_names:
            try:
                p = getattr(scene, 'tree_{}_input'.format(name))
                if str(type(p)) == "<class 'bpy_prop_array'>":
                    p = list(p)
                if p is not None:
                    params[name] = deepcopy(p)
                else:
                    print('Error while parsing input: {} = {}'.format(name, p))
            except AttributeError:
                pass  # Skip missing attributes, reverting to default

        return params


class TreeGenSaveFile(bpy.types.Operator):
    """Button to save custom tree parameters"""

    bl_idname = "object.tree_gen_custom_save"
    bl_category = "TreeGen"
    bl_label = "Save Custom Tree"
    bl_options = {'REGISTER'}

    def execute(self, context):
        save_location = context.scene.custom_tree_save_location_input
        params = TreeGen.get_params_from_customizer(context)

        if not context.scene.custom_tree_save_overwrite_input:
            counter = 0
            save_location_no_ext = save_location[:-3]
            while os.path.isfile(save_location):
                save_location = '{}_{}.py'.format(save_location_no_ext, counter)
                counter += 1

        with open(save_location, 'w') as output_file:
            print('params = ' + pprint.pformat(params), file=output_file)

        parametric_items = _get_tree_types()
        bpy.types.Scene.custom_tree_load_params_input = bpy.props.EnumProperty(name="", items=parametric_items)

        return {'FINISHED'}


class TreeGenLoadParams(bpy.types.Operator):
    """Button to load custom tree parameters"""

    bl_idname = "object.tree_gen_custom_load"
    bl_category = "TreeGen"
    bl_label = "Load Tree Parameters"
    bl_options = {'REGISTER'}

    def execute(self, context):
        mod_name = context.scene.custom_tree_load_params_input
        mod = __import__(mod_name, fromlist=[''])

        params = tree_param.TreeParam(mod.params).params

        scene = context.scene
        for name, value in params.items():
            if name in ['leaf_shape', 'shape', 'blossom_shape']:
                if value == 0 and name == 'leaf_shape':
                    value = 8  # default
                value = str(value)
            try:
                setattr(scene, 'tree_{}_input'.format(name), value)
            except TypeError as ex:
                exception = str(ex).replace('TypeError: bpy_struct: item.attr = val: ', '')
                print('TreeGen :: Error while loading preset "{}": {}'.format(name, exception))

        return {'FINISHED'}


class TreeGenCustomisePanel(bpy.types.Panel):
    """Provides the main user interface for TreeGen"""

    bl_label = "TreeGen Customisation"
    bl_idname = "OBJECT_PT_treegen_c"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'TreeGen'
    bl_context = (("objectmode"))
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        def label_row(label, prop, checkbox=False, dropdown=False, container=None):
            # Helper method to shorten the UI code
            if container is None:
                container = layout
            if dropdown:
                col = container.column()
                cont = col.split(percentage=.5, align=True)
                cont.label(text=label + ':')
            else:
                cont = container.row()

            if checkbox or dropdown:
                cont.prop(scene, prop)
            else:
                cont.prop(scene, prop, text=label)

        row = layout.row()
        row.label('Leaf Parameters:')
        box = layout.box()
        box.row()
        label_row('', 'generate_leaves_input', checkbox=True, container=box)
        if scene.generate_leaves_input:
            label_row('Leaf Shape', 'tree_leaf_shape_input', dropdown=True, container=box)
            label_row('Leaf Count', 'tree_leaf_blos_num_input', container=box)
            label_row('Leaf Scale', 'tree_leaf_scale_input', container=box)
            label_row('Leaf Width', 'tree_leaf_scale_x_input', container=box)
            label_row('Leaf Bend', 'tree_leaf_bend_input', container=box)
            box.separator()
            label_row('Blossom Shape', 'tree_blossom_shape_input', dropdown=True, container=box)
            label_row('Blossom Rate', 'tree_blossom_rate_input', container=box)
            label_row('Blossom Scale', 'tree_blossom_scale_input', container=box)
        box.row()

        layout.separator()
        row = layout.row()
        row.label('Tree Parameters:')
        box = layout.box()
        box.row()
        label_row('Tree Shape', 'tree_shape_input', dropdown=True, container=box)
        box.separator()
        label_row('Level Count', 'tree_levels_input', container=box)
        box.separator()
        label_row('Prune Ratio', 'tree_prune_ratio_input', container=box)
        label_row('Prune Width', 'tree_prune_width_input', container=box)
        label_row('Prune Width Peak', 'tree_prune_width_peak_input', container=box)
        label_row('Prune Power (low)', 'tree_prune_power_low_input', container=box)
        label_row('Prune Power (high)', 'tree_prune_power_high_input', container=box)
        box.separator()
        label_row('Trunk Splits', 'tree_base_splits_input', container=box)
        label_row('Trunk Flare', 'tree_flare_input', container=box)
        box.separator()
        label_row('Height', 'tree_g_scale_input', container=box)
        label_row('Height Variation', 'tree_g_scale_v_input', container=box)
        box.separator()
        label_row('Tropism', 'tree_tropism_input', container=box)
        box.separator()
        label_row('Branch Thickness Ratio', 'tree_ratio_input', container=box)
        label_row('Branch Thickness Ratio Power', 'tree_ratio_power_input', container=box)
        box.row()

        layout.separator()
        row = layout.row()
        row.label('Branch Parameters:')
        box = layout.box()
        box.row()
        label_row('Number', 'tree_branches_input', container=box)
        label_row('Length', 'tree_length_input', container=box)
        label_row('Length Variation', 'tree_length_v_input', container=box)
        label_row('Base Size', 'tree_base_size_input', container=box)
        label_row('Distribution', 'tree_branch_dist_input', container=box)
        label_row('Taper', 'tree_taper_input', container=box)
        label_row('Radius Modifier', 'tree_radius_mod_input', container=box)
        box.separator()
        label_row('Curve Resolution', 'tree_curve_res_input', container=box)
        label_row('Curve', 'tree_curve_input', container=box)
        label_row('Curve Variation', 'tree_curve_v_input', container=box)
        label_row('Curve Back', 'tree_curve_back_input', container=box)
        box.separator()
        label_row('Segment Splits', 'tree_seg_splits_input', container=box)
        label_row('Split Angle', 'tree_split_angle_input', container=box)
        label_row('Split Angle Variation', 'tree_split_angle_v_input', container=box)
        box.separator()
        label_row('Bend Variation', 'tree_bend_v_input', container=box)
        box.separator()
        label_row('Down Angle', 'tree_down_angle_input', container=box)
        label_row('Down Angle Variation', 'tree_down_angle_v_input', container=box)
        box.separator()
        label_row('Rotation', 'tree_rotate_input', container=box)
        label_row('Rotation Variation', 'tree_rotate_v_input', container=box)
        box.row()

        layout.separator()
        box = layout.box()
        box.row()
        label_row('Save Location', 'custom_tree_save_location_input', container=box)
        label_row('Overwrite if Exists', 'custom_tree_save_overwrite_input', checkbox=True, container=box)
        box.row()
        box.operator(TreeGenSaveFile.bl_idname)
        box.row()


class TreeGenPanel(bpy.types.Panel):
    """Provides the main user interface for TreeGen"""

    bl_label = "TreeGen"
    bl_idname = "OBJECT_PT_treegen"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'TreeGen'
    bl_context = (("objectmode"))

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        def label_row(label, prop, checkbox=False, dropdown=False, container=None):
            # Helper method to shorten the UI code

            if container is None:
                container = layout

            if dropdown:
                col = container.column()
                cont = col.split(percentage=.5, align=True)
                cont.label(text=label)
            else:
                cont = container.row()

            if checkbox or dropdown:
                cont.prop(scene, prop)
            else:
                cont.prop(scene, prop, text=label)

        box = layout.box()
        box.row()
        label_row('Load from file', 'custom_tree_load_params_input', container=box)
        box.row()
        box.operator(TreeGenLoadParams.bl_idname)
        box.row()

        layout.separator()
        box = layout.box()
        box.row()
        label_row('', 'render_input', checkbox=True, container=box)
        if scene.render_input:
            label_row('Filepath:', 'render_output_path_input', container=box)
        box.separator()
        label_row('', 'simplify_geometry_input', checkbox=True, container=box)
        box.separator()
        label_row('Seed', 'seed_input', container=box)
        box.row()

        layout.separator()
        layout.operator(TreeGen.bl_idname)
        layout.separator()
