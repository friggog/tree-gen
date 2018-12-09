import bpy

import traceback
import threading
import imp
import sys
import os
import time

from ch_trees import parametric, lsystems


update_log = parametric.gen.update_log


def _get_tree_types():
    # Scan the the ch_trees addon folder for parameters and definitions,
    # then return two EnumProperty objects for use as the drop-down tree selector
    # (one for parametric, one for L-system)

    addon_path_parts = __file__.split(os.path.sep)[:-1]
    addon_name = addon_path_parts[-1]
    addon_path = os.path.sep.join(addon_path_parts)

    module_path_parts = [['parametric', 'tree_params'], ['lsystems', 'sys_defs']]

    # Build the drop-down menus
    enums = []
    for modparts in module_path_parts:
        path = os.path.join(addon_path, *modparts)
        files = [f.split('.')[0] for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

        # ex: ['ch_trees.parametric.tree_params.quaking_aspen', ...]
        modules = ['{}.{}.{}'.format(addon_name, '.'.join(modparts), f) for f in files]

        # ex: 'Quaking Aspen'
        titles = [f.replace('_', ' ').title() for f in files]

        quaking_aspen = modules[0]
        options = []
        for module, title in zip(modules, titles):
            # Use quaking aspen as the default for the drop-down
            if title == 'Quaking Aspen':
                quaking_aspen = module

            # Item format: (internal value, label, hover-text)
            options.append((module, title, title))

        enums.append(bpy.props.EnumProperty(name="", items=tuple(options), default=quaking_aspen))

    return enums


class TreeGen(bpy.types.Operator):
    """Generate a tree"""

    bl_idname = "object.tree_gen"
    bl_category = "TreeGen"
    bl_label = "Generate Tree"
    bl_options = {'REGISTER', 'UNDO'}

    # ---
    # Note: an empty-string 'name' parameter removes the default label from inputs

    # Item format: (internal value, label, hover-text)
    _gen_methods = (('parametric', 'Parametric', 'Parametric mode'),
                    ('lsystem', 'L-System', 'L-System mode'))
    bpy.types.Scene.tree_gen_method_input = bpy.props.EnumProperty(name="", items=_gen_methods, default='parametric')

    # Drop-downs containing tree options for each generation method
    # These are switched between by TreeGenPanel.draw() based on the state of tree_gen_method_input
    bpy.types.Scene.para_tree_type_input, bpy.types.Scene.lsys_tree_type_input = _get_tree_types()

    # Nothing exciting here. Seed, leaf toggle, and simplify geometry toggle.
    bpy.types.Scene.seed_input = bpy.props.IntProperty(name="", default=0, min=0, max=9999999)
    bpy.types.Scene.generate_leaves_input = bpy.props.BoolProperty(name="Generate leaves", default=True)
    bpy.types.Scene.simplify_geometry_input = bpy.props.BoolProperty(name="Simplify branch geometry", default=False)

    # Render inputs; auto-fill path input with user's home directory
    bpy.types.Scene.render_input = bpy.props.BoolProperty(name="Render", default=False)
    render_output_path = os.path.sep.join((os.path.expanduser('~'), 'treegen_render.png'))
    bpy.types.Scene.render_output_path_input = bpy.props.StringProperty(name="", default=render_output_path)

    # ---
    def execute(self, context):
        # "Generate Tree" button callback

        threading.Thread(daemon=True, target=self._construct, kwargs={'context': context}).start()

        return {'FINISHED'}

    # ---
    def _construct(self, context):
        # The generator's main thread.
        # Handles conditional logic for generation method selection.

        scene = context.scene
        mod_name = scene.para_tree_type_input if scene.tree_gen_method_input == 'parametric' else scene.lsys_tree_type_input

        update_log('\n** Generating Tree **\n')

        if mod_name.startswith('ch_trees.parametric'):
            mod = __import__(mod_name, fromlist=[''])
            imp.reload(mod)

            start_time = time.time()
            parametric.gen.construct(mod.params, scene.seed_input, scene.render_input, scene.render_output_path_input, scene.generate_leaves_input)

        else:
            start_time = time.time()
            lsystems.gen.construct(mod_name, scene.generate_leaves_input)

        if scene.simplify_geometry_input:
            from . import utilities

            sys.stdout.write('Simplifying tree branch geometry. Blender will appear to crash; be patient.\n')
            sys.stdout.flush()

            # Catch exceptions and print them as strings
            # This will hopefully reduce random crashes
            try:
                utilities.simplify_branch_geometry(context)
                sys.stdout.write('Geometry simplification complete\n\n')

            except Exception as ex:
                sys.stdout.write('\n{}\n'.format(traceback.print_exc()))
                sys.stdout.write('Geometry simplification failed\n\n')

            sys.stdout.flush()

        update_log('\nTree generated in %f seconds\n\n'.format(time.time() - start_time))


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

        def label_row(label, prop, separator=True, one_row=False):
            # Helper method to shorten the UI code
            row = layout.row()

            if one_row or not label:
                row.prop(scene, prop)
                if label:
                    row.label(label)

            else:
                row.label(label)
                row = layout.row()
                row.prop(scene, prop)

            if separator:
                layout.separator()

        label_row('Method:', 'tree_gen_method_input')

        mode = scene.tree_gen_method_input
        label_row('Tree Type:', 'para_tree_type_input' if mode == 'parametric' else 'lsys_tree_type_input')

        if mode == 'parametric':
            label_row('Seed:', 'seed_input')

        label_row('', 'generate_leaves_input', False, True)

        label_row('', 'simplify_geometry_input', True, True)

        if mode == 'parametric':
            label_row('', 'render_input', False, True)
            if scene.render_input:
                label_row('Render output path:', 'render_output_path_input', False)
            layout.separator()

        layout.separator()
        layout.row()
        layout.operator(TreeGen.bl_idname)
