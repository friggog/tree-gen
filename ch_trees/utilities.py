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


def auto_dissolve_limit(scene, parent, br_bmesh, angle_limit=1.5, new_mesh_container_name='Branches', new_mesh_name='branches'):
    # Perform a limited dissolve
    bmesh.ops.dissolve_limit(br_bmesh, verts=br_bmesh.verts, edges=br_bmesh.edges, angle_limit=radians(angle_limit))

    # Create a new mesh and container object
    new_branches = bpy.data.objects.new(new_mesh_container_name, bpy.data.meshes.new(new_mesh_name))
    br_bmesh.to_mesh(new_branches.data)

    # Purge bmesh from memory
    br_bmesh.free()

    # Make the mesh active in the scene, then associate it with the tree
    scene.objects.link(new_branches)
    new_branches.matrix_world = parent.matrix_world
    new_branches.parent = parent


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
            break

    if original is None:
        raise Exception('No branches found while attempting to generate LODs')

    # Convert the branches curve to a mesh, then get an editable copy
    original_mesh = original.to_mesh(scene, False, 'RENDER')

    dissolve_limits = [.5, 1.0, 1.6]
    for level in range(level_count):
        br_bmesh = bmesh.new()
        br_bmesh.from_mesh(original_mesh)

        lod_level_name = '_LOD' + str(level + 1)
        auto_dissolve_limit(scene, tree, br_bmesh, dissolve_limits[level], new_mesh_container_name=base_name + lod_level_name, new_mesh_name='branches' + lod_level_name)

        update_log('\rLOD level ' + str(level + 1) + '/' + str(level_count) + ' generated')

    update_log('\n')

