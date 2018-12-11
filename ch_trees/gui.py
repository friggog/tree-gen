import bpy

import traceback
import threading
import random
import imp
import sys
import os
import pprint
from copy import deepcopy

from ch_trees import parametric
from ch_trees import lsystems


def _get_addon_path_details():
    addon_path_parts = __file__.split(os.path.sep)[:-1]
    addon_name = addon_path_parts[-1]
    addon_path = os.path.sep.join(addon_path_parts)

    return addon_path_parts, addon_name, addon_path


def _get_tree_types(self=None, context=None):
    # Scan the the ch_trees addon folder for parameters and definitions,
    # then return two EnumProperty objects for use as the drop-down tree selector
    # (one for parametric, one for L-system)

    addon_path_parts, addon_name, addon_path = _get_addon_path_details()

    module_path_parts = [['parametric', 'tree_params'], ['lsystems', 'sys_defs']]

    # Build the drop-down menus
    enum_options = []
    for modparts in module_path_parts:
        path = os.path.join(addon_path, *modparts)
        files = [f.split('.')[0] for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

        # ex: ['ch_trees.parametric.tree_params.quaking_aspen', ...]
        modules = ['{}.{}.{}'.format(addon_name, '.'.join(modparts), f) for f in files]

        # ex: 'Quaking Aspen'
        titles = [f.replace('_', ' ').title() for f in files]

        enum_options.append([(module, title, title) for module, title in zip(modules, titles)])

    # Add 'Custom' menu option to parametric mode
    enum_options[0].append(('custom', 'Custom', 'Custom parameters'))

    enum_options[0] = [tuple(option) for option in enum_options[0]]
    enum_options[1] = [tuple(option) for option in enum_options[1]]

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

    # Item format: (internal value, label, hover-text)
    _gen_methods = (('parametric', 'Parametric', 'Parametric mode'),
                    ('lsystems', 'L-System', 'L-System mode'))
    _scene.tree_gen_method_input = _props.EnumProperty(name="", items=_gen_methods, default='parametric')

    # Drop-downs containing tree options for each generation method
    # These are switched between by TreeGenPanel.draw() based on the state of tree_gen_method_input
    parametric_items, lsystems_items = _get_tree_types()
    _scene.parametric_tree_type_input = _props.EnumProperty(name="", items=parametric_items)
    _scene.lsystem_tree_type_input = _props.EnumProperty(name="", items=lsystems_items)

    # Nothing exciting here. Seed, leaf toggle, and simplify geometry toggle.
    _scene.seed_input = _props.IntProperty(name="", default=0, min=0, max=9999999)
    _scene.generate_leaves_input = _props.BoolProperty(name="Generate leaves", default=True)
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
        ('5', 'Flame', 'Flame'), ('6', 'Inverse Conical', 'Inverse Conical'), ('7', 'Tend Flame', 'Tend Flame'),
        ('8', 'Custom', 'Custom')
    )
    _scene.tree_shape_input = _props.EnumProperty(name="", items=tree_shape_options, default='0')

    _scene.tree_prune_ratio_input = _props.FloatProperty(name="", default=0, min=0, max=1)
    _scene.tree_prune_width_input = _props.FloatProperty(name="", default=.5, min=.000001, max=200)
    _scene.tree_prune_width_peak_input = _props.FloatProperty(name="", default=.5, min=0, max=200)
    _scene.tree_prune_power_low_input = _props.FloatProperty(name="", default=.5, min=-200,
                                                                         max=200)  # <1 convex, >1 concave
    _scene.tree_prune_power_high_input = _props.FloatProperty(name="", default=.5, min=-200,
                                                                          max=200)  # <1 convex, >1 concave

    # Size of base
    _scene.tree_base_size_input = _props.FloatVectorProperty(name="", default=(0.3, 0.02, 0.02, 0.02), size=4, min=.001)

    # Floor split count
    _scene.tree_floor_splits_input = _props.IntProperty(name="", default=0, min=0, max=500)

    # Base split count
    _scene.tree_base_splits_randomize_input = _props.BoolProperty(name="Randomize split count", default=False)
    _scene.tree_base_splits_limit_input = _props.IntProperty(name="", default=0, min=0, max=10)

    # Overall tree scale and scale variation
    _scene.tree_g_scale_input = _props.FloatProperty(name="", default=13, min=.000001, max=150)
    _scene.tree_g_scale_v_input = _props.FloatProperty(name="", default=3, min=0, max=149.99)

    # Level count
    _scene.tree_levels_input = _props.IntProperty(name="", default=3, min=1, max=6)

    # Ratio and ratio power
    _scene.tree_ratio_input = _props.FloatProperty(name="", default=.015, min=.000001, max=1)
    _scene.tree_ratio_power_input = _props.FloatProperty(name="", default=1.2, min=0, max=5)

    # Flare
    _scene.tree_flare_input = _props.FloatProperty(name="", default=.6, min=0, max=10)

    # Branch appearance
    _scene.tree_branches_input = _props.FloatVectorProperty(name="", default=(-0, 50, 30, 10), size=4, min=-0, max=360)

    _scene.tree_length_input = _props.FloatVectorProperty(name="", default=(1, 0.3, 0.6, 0), size=4, min=-0, max=1)
    _scene.tree_length_v_input = _props.FloatVectorProperty(name="", default=(0, 0, 0, 0), size=4, min=-0, max=1)

    _scene.tree_branch_dist_input = _props.FloatVectorProperty(name="", default=(-0, 0, 0, 0), size=4, min=-0, max=1)

    _scene.tree_taper_input = _props.FloatVectorProperty(name="", default=(1, 1, 1, 1), size=4, min=-0, max=1)
    _scene.tree_radius_mod_input = _props.FloatVectorProperty(name="", default=(1, 1, 1, 1), size=4, min=0, max=1)

    _scene.tree_bend_v_input = _props.FloatVectorProperty(name="", default=(-0, 50, 0, 0), size=4, min=-0, max=360)

    _scene.tree_curve_res_input = _props.FloatVectorProperty(name="", default=(5, 5, 3, 1), size=4, min=1, max=10)
    _scene.tree_curve_input = _props.FloatVectorProperty(name="", default=(0, -40, -40, 0), size=4, min=-360, max=360)
    _scene.tree_curve_v_input = _props.FloatVectorProperty(name="", default=(20, 50, 75, 0), size=4, min=0, max=360)
    _scene.tree_curve_back_input = _props.FloatVectorProperty(name="", default=(0, 0, 0, 0), size=4, min=0, max=1)

    # "the turning of all or part of an organism in a particular direction in response to an external stimulus"
    _scene.tree_tropism_input = _props.FloatVectorProperty(name="", default=(0, 0, 0.5), size=3, min=0, max=1)

    _scene.tree_down_angle_input = _props.FloatVectorProperty(name="", default=(-0, 140, 140, 77), size=4, min=-0, max=360)
    _scene.tree_down_angle_v_input = _props.FloatVectorProperty(name="", default=(-0, -50, 10, 10), size=4, min=-0, max=360)

    _scene.tree_rotate_input = _props.FloatVectorProperty(name="", default=(-0, 140, 140, 77), size=4, min=-0, max=360)
    _scene.tree_rotate_v_input = _props.FloatVectorProperty(name="", default=(-0, 0, 0, 0), size=4, min=-0)


    # ----
    # Cumulative count of leaves and blossoms on each of the deepest level of branches
    _scene.tree_leaf_blos_num_input = _props.IntProperty(name="", default=40, min=0, max=3000)

    # Leaf shape
    leaf_shape_options = (
        ('1', 'Ovate', 'Ovate'), ('2', 'Linear', 'Linear'), ('3', 'Cordate', 'Cordate'), ('4', 'Maple', 'Maple'),
        ('5', 'Palmate', 'Palmate'), ('6', 'Spiky Oak', 'Spiky Oak'), ('7', 'Rounded Oak', 'Rounded Oak'),
        ('8', 'Elliptic', 'Elliptic'), ('9', 'Rectangle', 'Rectangle'), ('10', 'Triangle', 'Triangle')
    )
    _scene.tree_leaf_shape_input = _props.EnumProperty(name="", items=leaf_shape_options, default='1')

    # Leaf scale
    _scene.tree_leaf_scale = _props.FloatProperty(name="", default=.17, min=.0001, max=1000)

    # Leaf scale in x-direction
    _scene.tree_leaf_scale_x = _props.FloatProperty(name="", default=1, min=.0001, max=1000)

    # Amount of leaf bend towards sunlight
    _scene.tree_leaf_bend_input = _props.FloatProperty(name="", default=.6, min=0, max=1)

    # ----
    # Blossom configuration
    _scene.tree_generate_blossoms_input = _props.BoolProperty(name="Generate blossoms", default=False)

    blossom_shape_options = (('1', 'Cherry', 'Cherry'), ('2', 'Orange', 'Orange'), ('3', 'Magnolia', 'Magnolia'))
    _scene.tree_blossom_shape_input = _props.EnumProperty(name="", items=blossom_shape_options, default='1')

    # Blossom scale
    _scene.tree_blossom_scale_input = _props.FloatProperty(name="", default=1, min=.0001, max=1000)

    # Rate at which blossoms occur relative to leaves
    _scene.tree_blossom_rate_input = _props.FloatProperty(name="", default=0, min=0, max=1)

    # Save location for custom tree params
    _scene.custom_tree_save_overwrite_input = _props.BoolProperty(name="Overwrite if file exists", default=False)
    tree_save_location = os.path.sep.join((_get_addon_path_details()[2], 'parametric', 'tree_params', 'my_custom_tree.py'))
    _scene.custom_tree_save_location_input = _props.StringProperty(name="", default=tree_save_location)

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
        mod_name = scene.parametric_tree_type_input if scene.tree_gen_method_input == 'parametric' else scene.lsystem_tree_type_input

        try:
            if mod_name.startswith('custom'):
                parametric.gen.construct(params, scene.seed_input, scene.render_input, scene.render_output_path_input,
                                         scene.generate_leaves_input)

            elif mod_name.startswith('ch_trees.parametric'):
                mod = __import__(mod_name, fromlist=[''])
                imp.reload(mod)
                parametric.gen.construct(mod.params, scene.seed_input, scene.render_input, scene.render_output_path_input,
                                         scene.generate_leaves_input)

            else:
                lsystems.gen.construct(mod_name, scene.generate_leaves_input)

            if scene.simplify_geometry_input:
                from . import utilities

                sys.stdout.write('Simplifying tree branch geometry. Blender will appear to crash; be patient.\n')
                sys.stdout.flush()

                # Catch exceptions and print them as strings
                # This will hopefully reduce random crashes
                try:
                    utilities.simplify_branch_geometry(context)

                except Exception:
                    sys.stdout.write('\n{}\n'.format(traceback.format_exc()))
                    sys.stdout.write('Geometry simplification failed\n\n')
                    sys.stdout.flush()

        # Reduce chance of Blender crashing when generation fails or the user does something ill-advised
        except Exception:
            sys.stdout.write('\n{}\n'.format(traceback.format_exc()))
            sys.stdout.write('Tree generation failed\n\n')
            sys.stdout.flush()

    # ----
    @staticmethod
    def get_params_from_customizer(context):
        scene = context.scene

        tree_base_splits = scene.tree_base_splits_limit_input
        if scene.tree_base_splits_randomize_input:
            tree_base_splits = random.randrange(0, tree_base_splits)

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
                pass
                # print('"{}" missing in customizer data, using default'.format(name))

        params['base_splits'] = tree_base_splits

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

        parametric_items, _ = _get_tree_types()
        bpy.types.Scene.parametric_tree_type_input = bpy.props.EnumProperty(name="", items=parametric_items)
        context.scene.parametric_tree_type_input = 'custom'

        return {'FINISHED'}


class TreeGenPanel(bpy.types.Panel):
    """Provides a user interface for TreeGen"""

    bl_label = "TreeGen Configuration"
    bl_idname = "OBJECT_PT_treegen"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'TreeGen'
    bl_context = (("objectmode"))

    # ---
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        def label_row(label, prop, separator=True, checkbox=False, dropdown=False):
            # Helper method to shorten the UI code

            if dropdown:
                col = layout.column()
                row = col.split(percentage=.5, align=True)
                row.label(text=label)
            else:
                row = layout.row()

            if checkbox or dropdown:
                row.prop(scene, prop)
            else:
                row.prop(scene, prop, text=label)

            if separator:
                layout.separator()

        label_row('Method', 'tree_gen_method_input', dropdown=True)

        mode = scene.tree_gen_method_input

        label_row('Tree Type',
                  'parametric_tree_type_input' if mode == 'parametric' else 'lsystem_tree_type_input',
                  dropdown=True)

        if mode == 'parametric':
            label_row('Seed', 'seed_input')

        if mode != 'parametric' or scene.parametric_tree_type_input != 'custom':
            label_row('', 'generate_leaves_input', False, True)

        label_row('', 'simplify_geometry_input', True, True)

        if mode == 'parametric':
            label_row('', 'render_input', False, True)
            if scene.render_input:
                label_row('Render output path:', 'render_output_path_input', False)
            layout.separator()

        # Show customizer
        if mode == 'parametric' and scene.parametric_tree_type_input == 'custom':
            layout.separator()

            label_row('Tree shape', 'tree_shape_input', dropdown=True)

            label_row('Level count', 'tree_levels_input')

            layout.separator()

            if scene.tree_shape_input == '8':
                label_row('Prune ratio', 'tree_prune_ratio_input', False)
                label_row('Prune width', 'tree_prune_width_input', False)
                label_row('Prune width peak', 'tree_prune_width_peak_input', False)
                label_row('Prune power (low)', 'tree_prune_power_low_input', False)
                label_row('Prune power (high)', 'tree_prune_power_high_input')

                label_row('Base size', 'tree_base_size_input')

                layout.separator()
                label_row('', 'tree_base_splits_randomize_input', False, True)
                if scene.tree_base_splits_randomize_input:
                    label_row('Base splits limit', 'tree_base_splits_limit_input')
                else:
                    label_row('Base splits count', 'tree_floor_splits_input')

                label_row('Floor splits', 'tree_floor_splits_input', False)

                layout.separator()
                label_row('G scale', 'tree_g_scale_input', False)
                label_row('G scale v', 'tree_g_scale_v_input')

                label_row('Ratio', 'tree_ratio_input', False)
                label_row('Ratio power', 'tree_ratio_power_input')

                label_row('Flare', 'tree_flare_input')

                layout.separator()
                label_row('', 'tree__input')
                label_row('', 'tree__input')


            layout.separator()
            label_row('', 'generate_leaves_input', False, True)
            if scene.generate_leaves_input:
                label_row('Leaf shape', 'tree_leaf_shape_input', True, dropdown=True)
                label_row('Leaf scale', 'tree_leaf_scale', False)
                label_row('Leaf scale x', 'tree_leaf_scale_x', False)
                label_row('Leaf bend', 'tree_leaf_bend_input')

            layout.separator()
            label_row('', 'tree_generate_blossoms_input', False, True)
            if scene.tree_generate_blossoms_input:
                label_row('Blossom shape', 'tree_blossom_shape_input', True, dropdown=True)
                label_row('Blossom count', 'tree_leaf_blos_num_input', False)
                label_row('Blossom rate', 'tree_blossom_rate_input', False)
                label_row('Blossom scale', 'tree_blossom_scale_input', False)

            layout.separator()
            layout.separator()
            label_row('Save location', 'custom_tree_save_location_input', False)
            label_row('Overwrite if exists', 'custom_tree_save_overwrite_input', True, True)
            layout.row()
            layout.operator(TreeGenSaveFile.bl_idname)

        layout.separator()
        layout.row()
        layout.separator()
        layout.operator(TreeGen.bl_idname)
        layout.separator()
