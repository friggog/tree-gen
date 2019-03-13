bl_info = {
    "name": "TreeGen",
    "category": "Object",
    "description": "Generate high quality tree models",
    "author": "Charlie Hewitt and Luke Pflibsen-Jones",
    "version": (0, 0, 1),
    "wiki_url": "",
}


import bpy
from . import gui


def register():
    bpy.utils.register_class(gui.TreeGen)
    bpy.utils.register_class(gui.TreeGenPanel)
    bpy.utils.register_class(gui.TreeGenCustomisePanel)
    bpy.utils.register_class(gui.TreeGenSaveFile)
    bpy.utils.register_class(gui.TreeGenLoadParams)


def unregister():
    # Reversing order is best-practice
    bpy.utils.unregister_class(gui.TreeGenLoadParams)
    bpy.utils.unregister_class(gui.TreeGenSaveFile)
    bpy.utils.unregister_class(gui.TreeGenCustomisePanel)
    bpy.utils.unregister_class(gui.TreeGenPanel)
    bpy.utils.unregister_class(gui.TreeGen)


if __name__ == "__main__":
    register()
