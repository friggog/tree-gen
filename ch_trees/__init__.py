bl_info = {
    "name": "TreeGen",
    "category": "Object",
}

import bpy
from . import gui


def register():
    bpy.utils.register_class(gui.TreeGen)
    bpy.utils.register_class(gui.TreeGenPanel)
    bpy.utils.register_class(gui.TreeGenLogger)
    # bpy.types.Object.expanded = bpy.props.BoolProperty(default=True)

def unregister():
    # Reversing order is best-practice
    bpy.utils.unregister_class(gui.TreeGenLogger)
    bpy.utils.unregister_class(gui.TreeGenPanel)
    bpy.utils.unregister_class(gui.TreeGen)
    # del bpy.types.Object.expanded


if __name__ == "__main__":
    register()
