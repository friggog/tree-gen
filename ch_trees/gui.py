import bpy
import addon_utils

import threading
import imp
import os

from ch_trees import parametric
from ch_trees import lsystems

# ------
def _get_tree_types():
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
    bpy.types.Scene.seed_input      = bpy.props.IntProperty(name="", default=0, min=0, max=9999999)
    bpy.types.Scene.render_input    = bpy.props.BoolProperty(name="", default=False)
    bpy.types.Scene.out_path_input  = bpy.props.StringProperty(name="", default=os.path.sep.join((os.path.expanduser('~'), 'treegen_render.png')))
    
    _tree_type_options = (('parametric', 'Parametric', 'Parametric mode'), ('lsystem', 'L-System', 'L-System mode'))
    bpy.types.Scene.tree_gen_mode_input = bpy.props.EnumProperty(name="", items=_tree_type_options, default='parametric')
    bpy.types.Scene.para_tree_type_input, bpy.types.Scene.lsys_tree_type_input = _get_tree_types()

    # ---
    def execute(self, context):
        scene = context.scene
        
        mod_name = scene.para_tree_type_input if scene.tree_gen_mode_input == 'parametric' else scene.lsys_tree_type_input
        
        params = {
            'seed':      scene.seed_input,
            'render':    scene.render_input,
            'out_path':  scene.out_path_input,
            'mod_name':  mod_name
        }
        
        thread = threading.Thread(target=self._construct, kwargs=params)
        thread.start()
        
        return {'FINISHED'}

    # ---
    def _construct(self, seed, render, out_path, mod_name):
        if mod_name.startswith('ch_trees.parametric'):
            mod = __import__(mod_name, fromlist=[''])
            imp.reload(mod)
            parametric.gen.construct(mod.params, seed, render, out_path)
            
        else:
            lsystems.gen.construct(mod_name)

# ------
class TreeGenPanel(bpy.types.Panel):
    
    bl_label = "TreeGen Configuration"
    bl_idname = "OBJECT_PT_treegen"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'TreeGen'
    bl_context = (("objectmode"))

    param_gen_rows = [
        ('Seed', 'seed_input'),
        ('Render', 'render_input'),
        ('Output path', 'out_path_input')
    ]
    
    messages = []
    
    # ---
    def draw(self, context):
        layout = self.layout
        scene  = context.scene
        
        def new_row():
            layout.separator()
            return layout.row()

        row = layout.row()
        row.label('Mode')
        row.prop(scene, 'tree_gen_mode_input')
        
        mode = scene.tree_gen_mode_input
        
        row = new_row()
        row.label('Tree type')
        row.prop(scene, 'para_tree_type_input' if mode == 'parametric' else 'lsys_tree_type_input')

        if mode == 'parametric':
            layout.separator()
            
            for label, name in self.param_gen_rows:
                row = layout.row()
                row.label(label)
                row.prop(scene, name)
        
        row = new_row()
        layout.operator(TreeGen.bl_idname)