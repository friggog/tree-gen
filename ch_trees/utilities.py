import bpy
import bmesh

from math import radians

import sys
import threading
from queue import Queue


class _LogThread(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)

        self.queue = queue
        self.daemon = True
        self.running = False

    def run(self):
        self.running = True

        while True:
            msg = self.queue.get()

            if msg == 'kill_thread':
                break

            sys.stdout.write(msg)
            sys.stdout.flush()

        self.running = False


thread_queue = None
log_thread = None
def get_logger(logging):
    global log_thread, thread_queue

    if logging:
        thread_queue = Queue()
        log_thread = _LogThread(thread_queue)
        log_thread.start()

        def update_log(msg):
            global log_thread
            if not log_thread.running:
                log_thread = _LogThread(thread_queue)
                log_thread.start()

            thread_queue.put(msg)

        return update_log

    return lambda _: None


def object_deleted(o):
    try:
        return bpy.data.objects.get(o.name, None) is not None
    except ReferenceError:  # o is deleted, so accessing name raises an error
        return True


def convert_to_mesh(context):  #, angle_limit=1.5):
    """
    Converts tree branches from curve to mesh, then runs a limited dissolve
    to reduce their geometric complexity with minimal quality loss.

    [float] angle_limit :: Radian value in float form that provides the angle
                           limit for the limited dissolve. Default is 1.5
    """

    scene = context.scene

    try:
        tree = scene.objects.active
    except AttributeError:
        raise Exception('Could not find tree while attempting to convert to mesh')

    old_branches = None
    for child in tree.children:
        if child.name.startswith('Branches'):
            old_branches = child
            break

    if old_branches is None:
        raise Exception('No branches found while converting to mesh')

    # Convert the branches curve to a mesh, then get an editable copy
    old_branch_mesh = old_branches.to_mesh(scene, False, 'RENDER')
    br_bmesh = bmesh.new()
    br_bmesh.from_mesh(old_branch_mesh)

    # Purge old branch data from memory
    bpy.data.meshes.remove(old_branch_mesh)
    del old_branch_mesh

    bpy.data.curves.remove(old_branches.data)

    if not object_deleted(old_branches):
        bpy.data.objects.remove(old_branches, True)

    del old_branches

    # Create a new mesh and container object
    new_branches = bpy.data.objects.new('Branches', bpy.data.meshes.new('branches'))
    br_bmesh.to_mesh(new_branches.data)

    # Purge bmesh from memory
    br_bmesh.free()

    # Make the mesh active in the scene, then associate it with the tree
    scene.objects.link(new_branches)
    new_branches.matrix_world = tree.matrix_world
    new_branches.parent = tree


def generate_lods(context, level_count=3):
    from ch_trees import parametric
    update_log = parametric.gen.update_log

    scene = context.scene

    try:
        tree = scene.objects.active
    except AttributeError:
        raise Exception('Could not find tree while attempting to generate LODs')

    original = None
    for child in tree.children:
        if child.name.startswith('Branches'):
            base_name = child.name
            child.name = child.name + '_LOD0'
            original = child
            parent = child.parent
            break

    if original is None:
        raise Exception('No branches found while attempting to generate LODs')

    # Create a mesh data container for use/reuse with mesh generation
    curve_bmesh = bmesh.new()

    resolutions = [3, 2, 1]
    dissolve_ratios = [.9, .7, .5]
    for level in range(0, level_count):
        lod_level_name = '_LOD' + str(level + 1)

        # Create copy of curve
        new_curve = original.copy()

        # Set the resolution of the new curve and convert to mesh
        new_curve.data.resolution_u = resolutions[level]
        curve_bmesh.from_mesh(new_curve.to_mesh(scene, settings='RENDER', apply_modifiers=False))
        new_branches = bpy.data.objects.new(base_name + lod_level_name, bpy.data.meshes.new('branches' + lod_level_name))
        curve_bmesh.to_mesh(new_branches.data)  # Copy data from curve_bmesh into new_branches
        curve_bmesh.clear()

        # Decimate
        modifier = new_branches.modifiers.new('TreeDecimateMod', 'DECIMATE')
        modifier.ratio = dissolve_ratios[level]

        # Make the mesh active in the scene, then associate it with the tree
        scene.objects.link(new_branches)
        new_branches.matrix_world = parent.matrix_world
        new_branches.parent = parent

        # Switch to object mode and apply modifier
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.scene.objects.active = new_branches
        bpy.ops.object.modifier_apply(modifier='TreeDecimateMod')

        update_log('\rLOD level ' + str(level + 1) + '/' + str(level_count) + ' generated')

    curve_bmesh.free()

    update_log('\n')

