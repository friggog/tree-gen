bl_info = {
    "name": "TreeGen",
    "category": "Object",
}

import bpy
from . import gui


def register():
    bpy.utils.register_class(gui.TreeGen)
    bpy.utils.register_class(gui.TreeGenPanel)
    bpy.utils.register_class(gui.TreeGenSaveFile)
    bpy.utils.register_class(gui.TreeGenLoadParams)

def unregister():
    # Reversing order is best-practice
    bpy.utils.unregister_class(gui.TreeGenLoadParams)
    bpy.utils.unregister_class(gui.TreeGenSaveFile)
    bpy.utils.unregister_class(gui.TreeGenPanel)
    bpy.utils.unregister_class(gui.TreeGen)


if __name__ == "__main__":
    register()
