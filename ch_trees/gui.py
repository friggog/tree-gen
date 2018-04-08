import bpy
import addon_utils

import threading
import imp
import sys
import os

from ch_trees import parametric
from ch_trees import lsystems

# ------
def _get_tree_types():
    # Scan the the ch_trees addon folder for parameters and definitions,
    # then return two EnumProperty objects for use as the drop-down tree selector
    # (one for parametric, one for L-system)
    
    addon_path = None
    
    for path in addon_utils.paths():
        if 'ch_trees' in os.listdir(path):
            addon_path = path
            break
    
    if addon_path is None:
        sys.stdout.write('TreeGen :: WARNING: Could not find addon installation folder\n')
        sys.stdout.flush()
        return None, None
    
    root_path_parts = [['ch_trees', 'parametric', 'tree_params'],
                       ['ch_trees', 'lsystems', 'sys_defs']]
    
    enums = []
    for rpparts in root_path_parts:
        path  = os.path.join(addon_path, *rpparts)
        files = [f.split('.')[0] for f in os.listdir(path) if os.path.isfile(path + '/' + f)]
        
        modules  = ['{}.{}'.format('.'.join(rpparts), f) for f in files]
        titles   = [f.replace('_', ' ').title() for f in files]
        
        quaking_aspen = modules[0]
        options = []
        for module, title in zip(modules, titles):
            # Use quaking aspen as the default for the drop-down
            if title == 'Quaking Aspen':
               quaking_aspen = module
               
            options.append((module, title, title))
        
        enums.append(bpy.props.EnumProperty(name="", items=tuple(options), default=quaking_aspen))
    
    return enums

# ---
class TreeGen(bpy.types.Operator):
    """Generate a tree"""
    
    bl_idname   = "object.tree_gen"
    bl_category = "TreeGen"
    bl_label    = "Generate Tree"
    bl_options  = {'REGISTER', 'UNDO'}
    
    # Empty names remove labels from input boxes
    bpy.types.Scene.seed_input              = bpy.props.IntProperty(name="", default=0, min=0, max=9999999)
    bpy.types.Scene.simplify_geometry_input = bpy.props.BoolProperty(name="Simplify branch geometry", default=False)
    bpy.types.Scene.render_input            = bpy.props.BoolProperty(name="Render", default=False)
    bpy.types.Scene.out_path_input          = bpy.props.StringProperty(name="", default=os.path.sep.join((os.path.expanduser('~'), 'treegen_render.png')))
    
    _gen_methods = (('parametric', 'Parametric', 'Parametric mode'),
                    ('lsystem', 'L-System', 'L-System mode'))
    bpy.types.Scene.tree_gen_method_input = bpy.props.EnumProperty(name="", items=_gen_methods, default='parametric')
    bpy.types.Scene.para_tree_type_input, bpy.types.Scene.lsys_tree_type_input = _get_tree_types()

    # ---
    def execute(self, context):
        # "Generate Tree" button callback
        
        thread = threading.Thread(target=self._construct, kwargs={'context': context})
        thread.start()
        
        return {'FINISHED'}

    # ---
    def _construct(self, context):
        # The generator's main thread. Also handles conditional logic for generation method selection.
        
        scene = context.scene
        mod_name = scene.para_tree_type_input if scene.tree_gen_method_input == 'parametric' else scene.lsys_tree_type_input
        
        if mod_name.startswith('ch_trees.parametric'):
            mod = __import__(mod_name, fromlist=[''])
            imp.reload(mod)
            parametric.gen.construct(mod.params, scene.seed_input, scene.render_input, scene.out_path_input)
            
        else:
            lsystems.gen.construct(mod_name)
            
        if scene.simplify_geometry_input:
            from . import utilities
            
            sys.stdout.write('Simplifying tree branch geometry. Blender will appear to crash; be patient.\n')
            sys.stdout.flush()
            
            utilities.simplify_branch_geometry(context)
            
            sys.stdout.write('Geometry simplification complete\n\n')
            sys.stdout.flush()

    
# ------
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
        scene  = context.scene
        
        def label_row(label, prop, separator=True, one_row=False):
            # Helper method to shorten the UI code
            row = layout.row()
            
            if one_row or not label:
                row.prop(scene, prop)
                if label: row.label(label)
                
            else:
                row.label(label)
                row = layout.row()
                row.prop(scene, prop)
                
            if separator: layout.separator()
        
        
        label_row('Method:', 'tree_gen_method_input')

        mode = scene.tree_gen_method_input
        label_row('Tree Type:', 'para_tree_type_input' if mode == 'parametric' else 'lsys_tree_type_input')
            
        if mode == 'parametric': 
            label_row('Seed:', 'seed_input')

            label_row('', 'render_input', False, True)
            if scene.render_input:
                label_row('Render output path:', 'out_path_input')
        
        label_row('', 'simplify_geometry_input', True, True)
            
        layout.separator()
        row = layout.row()
        layout.operator(TreeGen.bl_idname)
