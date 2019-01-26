import bpy

import traceback
import threading
# import random
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
    _scene.seed_input = _props.IntProperty(name="", default=0, min=0, max=9999999)
    _scene.generate_leaves_input = _props.BoolProperty(name="Generate leaves/blossom", default=True)
    _scene.simplify_geometry_input = _props.BoolProperty(name="Simplify branch geometry", default=False)

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
        ('5', 'Flame', 'Flame'), ('6', 'Inverse Conical', 'Inverse Conical'), ('7', 'Tend Flame', 'Tend Flame')
    )
    _scene.tree_shape_input = _props.EnumProperty(name="", items=tree_shape_options, default='0')

    _scene.tree_prune_ratio_input = _props.FloatProperty(name="", default=0, min=0, max=1)
    _scene.tree_prune_width_input = _props.FloatProperty(name="", default=.5, min=.000001, max=200)
    _scene.tree_prune_width_peak_input = _props.FloatProperty(name="", default=.5, min=0, max=200)
    _scene.tree_prune_power_low_input = _props.FloatProperty(name="", default=.5, min=-200, max=200)  # <1 convex, >1 concave
    _scene.tree_prune_power_high_input = _props.FloatProperty(name="", default=.5, min=-200, max=200)  # <1 convex, >1 concave

    # Size of base
    _scene.tree_base_size_input = _props.FloatVectorProperty(name="", default=(0.3, 0.02, 0.02, 0.02), size=4, min=.001)

    # Floor split count
    _scene.tree_floor_splits_input = _props.IntProperty(name="", default=0, min=0, max=500)

    # Base split count
    # _scene.tree_base_splits_randomize_input = _props.BoolProperty(name="Randomize base split count", default=False)
    _scene.tree_base_splits_input = _props.IntProperty(name="", default=0, min=-5, max=5)
    # _scene.tree_base_splits_limit_input = _props.IntProperty(name="", default=0, min=0, max=10)

    # Overall tree scale and scale variation
    _scene.tree_g_scale_input = _props.FloatProperty(name="", default=13, min=.000001, max=150)
    _scene.tree_g_scale_v_input = _props.FloatProperty(name="", default=3, min=0, max=149.99)

    # Level count
    _scene.tree_levels_input = _props.IntProperty(name="", default=3, min=1, max=4)

    # Ratio and ratio power
    _scene.tree_ratio_input = _props.FloatProperty(name="", default=.015, min=.000001, max=1)
    _scene.tree_ratio_power_input = _props.FloatProperty(name="", default=1.2, min=0, max=5)

    # Flare
    _scene.tree_flare_input = _props.FloatProperty(name="", default=.6, min=0, max=10)

    # Branch appearance
    _scene.tree_branches_input = _props.FloatVectorProperty(name="", default=(0, 50, 30, 10), size=4, min=0, max=360)

    _scene.tree_length_input = _props.FloatVectorProperty(name="", default=(1, 0.3, 0.6, 0), size=4, min=0, max=1)
    _scene.tree_length_v_input = _props.FloatVectorProperty(name="", default=(0, 0, 0, 0), size=4, min=-0, max=1)

    _scene.tree_branch_dist_input = _props.FloatVectorProperty(name="", default=(0, 0, 0, 0), size=4, min=0, max=1)

    _scene.tree_taper_input = _props.FloatVectorProperty(name="", default=(1, 1, 1, 1), size=4, min=-0, max=3)
    _scene.tree_radius_mod_input = _props.FloatVectorProperty(name="", default=(1, 1, 1, 1), size=4, min=0, max=1)

    _scene.tree_bend_v_input = _props.FloatVectorProperty(name="", default=(0, 50, 0, 0), size=4, min=0, max=360)

    _scene.tree_curve_res_input = _props.FloatVectorProperty(name="", default=(5, 5, 3, 1), size=4, min=1, max=10)
    _scene.tree_curve_input = _props.FloatVectorProperty(name="", default=(0, -40, -40, 0), size=4, min=-360, max=360)
    _scene.tree_curve_v_input = _props.FloatVectorProperty(name="", default=(20, 50, 75, 0), size=4, min=-360, max=360)
    _scene.tree_curve_back_input = _props.FloatVectorProperty(name="", default=(0, 0, 0, 0), size=4, min=0, max=1)

    _scene.tree_seg_splits_input = _props.FloatVectorProperty(name="", default=(1.5, 1.5, 0, 0), size=4, min=0, max=2)
    _scene.tree_split_angle_input = _props.FloatVectorProperty(name="", default=(50, 50, 0, 0), size=4, min=0, max=360)
    _scene.tree_split_angle_v_input = _props.FloatVectorProperty(name="", default=(5, 5, 0, 0), size=4, min=0, max=360)

    # "the turning of all or part of an organism in a particular direction in response to an external stimulus"
    _scene.tree_tropism_input = _props.FloatVectorProperty(name="", default=(0, 0, 0.5), size=3, min=-10, max=10)

    _scene.tree_down_angle_input = _props.FloatVectorProperty(name="", default=(0, 140, 140, 77), size=4, min=0, max=360)
    _scene.tree_down_angle_v_input = _props.FloatVectorProperty(name="", default=(0, -50, 10, 10), size=4, min=-360, max=360)

    _scene.tree_rotate_input = _props.FloatVectorProperty(name="", default=(0, 140, 140, 77), size=4, min=-360, max=360)
    _scene.tree_rotate_v_input = _props.FloatVectorProperty(name="", default=(0, 0, 0, 0), size=4, min=0)

    # ----
    # Cumulative count of leaves and blossoms on each of the deepest level of branches
    _scene.tree_leaf_blos_num_input = _props.IntProperty(name="", default=40, min=-1000, max=3000)

    # Leaf shape
    leaf_shape_options = (
        ('1', 'Ovate', 'Ovate'), ('2', 'Linear', 'Linear'), ('3', 'Cordate', 'Cordate'), ('4', 'Maple', 'Maple'),
        ('5', 'Palmate', 'Palmate'), ('6', 'Spiky Oak', 'Spiky Oak'), ('7', 'Rounded Oak', 'Rounded Oak'),
        ('8', 'Elliptic', 'Elliptic'), ('9', 'Rectangle', 'Rectangle'), ('10', 'Triangle', 'Triangle')
    )
    _scene.tree_leaf_shape_input = _props.EnumProperty(name="", items=leaf_shape_options, default='1')

    # Leaf scale
    _scene.tree_leaf_scale_input = _props.FloatProperty(name="", default=.17, min=.0001, max=1000)

    # Leaf scale in x-direction
    _scene.tree_leaf_scale_x_input = _props.FloatProperty(name="", default=1, min=.0001, max=1000)

    # Amount of leaf bend towards sunlight
    _scene.tree_leaf_bend_input = _props.FloatProperty(name="", default=.6, min=0, max=1)

    # ----
    # Blossom configuration
    # _scene.tree_generate_blossoms_input = _props.BoolProperty(name="Generate blossoms", default=False)

    blossom_shape_options = (('1', 'Cherry', 'Cherry'), ('2', 'Orange', 'Orange'), ('3', 'Magnolia', 'Magnolia'))
    _scene.tree_blossom_shape_input = _props.EnumProperty(name="", items=blossom_shape_options, default='1')

    # Blossom scale
    _scene.tree_blossom_scale_input = _props.FloatProperty(name="", default=0.1, min=.0001, max=1)

    # Rate at which blossoms occur relative to leaves
    _scene.tree_blossom_rate_input = _props.FloatProperty(name="", default=0, min=0, max=1)

    # Save location for custom tree params
    _scene.custom_tree_save_overwrite_input = _props.BoolProperty(name="Overwrite if file exists", default=False)
    tree_save_location = os.path.sep.join((_get_addon_path_details()[2], 'parametric', 'tree_params', 'my_custom_tree.py'))
    _scene.custom_tree_save_location_input = _props.StringProperty(name="", default=tree_save_location)

    # Load custom params
    _scene.custom_tree_load_params_input = _props.EnumProperty(name="", items=parametric_items)

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
        # mod_name = scene.parametric_tree_type_input if scene.tree_gen_method_input == 'parametric' else scene.lsystem_tree_type_input
        # mod_name = 'parametric'

        update_log('\n** Generating Tree **\n')
        try:
            # if mod_name.startswith('custom'):
            start_time = time.time()
            parametric.gen.construct(params, scene.seed_input, scene.render_input, scene.render_output_path_input,
                                     scene.generate_leaves_input)

            # elif mod_name.startswith('ch_trees.parametric'):
            #     mod = __import__(mod_name, fromlist=[''])
            #     imp.reload(mod)

            #     start_time = time.time()
            #     parametric.gen.construct(mod.params, scene.seed_input, scene.render_input, scene.render_output_path_input,
            #                              scene.generate_leaves_input)

            # else:
            #     start_time = time.time()
            #     lsystems.gen.construct(mod_name, scene.generate_leaves_input)

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

        # tree_base_splits = scene.tree_base_splits_limit_input
        # if scene.tree_base_splits_randomize_input:
        #     tree_base_splits = random.randrange(0, tree_base_splits)

        param_names = ['shape', 'g_scale', 'g_scale_v', 'levels', 'ratio', 'flare', 'ratio_power', 'floor_splits',
                       'base_size', 'down_angle', 'down_angle_v', 'rotate', 'rotate_v', 'branches',
                       'length', 'length_v', 'taper', 'seg_splits', 'split_angle', 'split_angle_v', 'curve_res',
                       'curve', 'curve_back', 'curve_v', 'bend_v', 'branch_dist', 'radius_mod', 'leaf_blos_num',
                       'leaf_shape', 'leaf_scale', 'leaf_scale_x', 'leaf_bend', 'blossom_shape', 'blossom_scale',
                       'blossom_rate', 'tropism', 'prune_ratio', 'prune_width', 'prune_width_peak',
                       'prune_power_low', 'prune_power_high']

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

        # params['base_splits'] = tree_base_splits

        return params


class TreeGenSaveFile(bpy.types.Operator):
    """Button to save custom tree parameters"""

    bl_idname = "object.tree_gen_custom_save"
    bl_category = "TreeGen"
    bl_label = "Save custom tree"
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
        bpy.types.Scene.parametric_tree_type_input = bpy.props.EnumProperty(name="", items=parametric_items)

        return {'FINISHED'}


class TreeGenLoadParams(bpy.types.Operator):
    """Button to load custom tree parameters"""

    bl_idname = "object.tree_gen_custom_load"
    bl_category = "TreeGen"
    bl_label = "Load tree parameters"
    bl_options = {'REGISTER'}

    def execute(self, context):
        mod_name = context.scene.custom_tree_load_params_input
        mod = __import__(mod_name, fromlist=[''])

        params = tree_param.TreeParam(mod.params).params

        scene = context.scene
        for name, value in params.items():
            if name in ['leaf_shape', 'shape']:
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
                cont.label(text=label)
            else:
                cont = container.row()

            if checkbox or dropdown:
                cont.prop(scene, prop)
            else:
                cont.prop(scene, prop, text=label)

        box = layout.box()
        box.row()
        label_row('', 'generate_leaves_input', True, container=box)
        if scene.generate_leaves_input:
            label_row('Leaf shape', 'tree_leaf_shape_input', dropdown=True, container=box)
            label_row('Leaf Count', 'tree_leaf_blos_num_input', container=box)
            label_row('Length', 'tree_leaf_scale_input', container=box)
            label_row('Width', 'tree_leaf_scale_x_input', container=box)
            label_row('Bend', 'tree_leaf_bend_input', container=box)
            box.separator()
            label_row('Blossom shape', 'tree_blossom_shape_input', True, dropdown=True, container=box)
            label_row('Blossom rate', 'tree_blossom_rate_input', container=box)
            label_row('Blossom scale', 'tree_blossom_scale_input', container=box)
        box.row()

        layout.separator()
        box = layout.box()
        label_row('Tree shape', 'tree_shape_input', dropdown=True, container=box)
        box.separator()
        label_row('Level count', 'tree_levels_input', container=box)
        label_row('Trunk count', 'tree_floor_splits_input', container=box)
        box.separator()
        label_row('Prune ratio', 'tree_prune_ratio_input', container=box)
        label_row('Prune width', 'tree_prune_width_input', container=box)
        label_row('Prune width peak', 'tree_prune_width_peak_input', container=box)
        label_row('Prune power (low)', 'tree_prune_power_low_input', container=box)
        label_row('Prune power (high)', 'tree_prune_power_high_input', container=box)
        box.separator()
        label_row('Base splits', 'tree_base_splits_input', container=box)
        box.row()

        layout.separator()
        box = layout.box()
        box.row()
        label_row('Height scale', 'tree_g_scale_input', container=box)
        label_row('Height scale variation', 'tree_g_scale_v_input', container=box)
        box.separator()
        label_row('Tropism', 'tree_tropism_input', container=box)
        box.separator()
        label_row('Ratio', 'tree_ratio_input', container=box)
        label_row('Ratio power', 'tree_ratio_power_input', container=box)
        box.separator()
        label_row('Flare', 'tree_flare_input', container=box)
        box.row()

        layout.separator()
        box = layout.box()
        box.row()
        label_row('Branches', 'tree_branches_input', container=box)
        label_row('Length', 'tree_length_input', container=box)
        label_row('Length variation', 'tree_length_v_input', container=box)
        label_row('Base size', 'tree_base_size_input', container=box)
        label_row('Distance', 'tree_branch_dist_input', container=box)
        label_row('Taper', 'tree_taper_input', container=box)
        label_row('Radius modifier', 'tree_radius_mod_input', container=box)
        box.separator()
        label_row('Curve resolution', 'tree_curve_res_input', container=box)
        label_row('Curve', 'tree_curve_input', container=box)
        label_row('Curve variation', 'tree_curve_v_input', container=box)
        label_row('Curve back', 'tree_curve_back_input', container=box)
        box.separator()
        label_row('Segment splits', 'tree_seg_splits_input', container=box)
        label_row('Split angle', 'tree_split_angle_input', container=box)
        label_row('Split angle variation', 'tree_split_angle_v_input', container=box)
        box.separator()
        label_row('Bend variation', 'tree_bend_v_input', container=box)
        box.separator()
        label_row('Down angle', 'tree_down_angle_input', container=box)
        label_row('Down angle variation', 'tree_down_angle_v_input', container=box)
        box.separator()
        label_row('Rotation', 'tree_rotate_input', False, container=box)
        label_row('Rotation variation', 'tree_rotate_v_input', container=box)
        box.row()

        layout.separator()
        box = layout.box()
        box.row()
        label_row('Save location', 'custom_tree_save_location_input', container=box)
        label_row('Overwrite if exists', 'custom_tree_save_overwrite_input', True, container=box)
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
        label_row('', 'simplify_geometry_input', True)

        layout.separator()
        box = layout.box()
        box.row()
        label_row('', 'render_input', True, container=box)
        if scene.render_input:
            label_row('Filepath:', 'render_output_path_input', container=box)
        box.row()

        layout.separator()
        label_row('Seed', 'seed_input')

        layout.separator()
        layout.separator()
        layout.operator(TreeGen.bl_idname)
        layout.separator()
