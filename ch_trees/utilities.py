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


def simplify_branch_geometry(context, angle_limit=1.5):
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
        raise Exception('Could not find tree while attempting to simplify branch geometry')

    try:
        old_branches = [child for child in tree.children if 'Branches' in child.name][0]
    except IndexError:
        raise Exception('No branches found while simplifying branch geometry')

    # Convert the branches curve to a mesh, then get an editable copy
    br_bmesh = bmesh.new()
    br_bmesh.from_mesh(old_branches.to_mesh(scene, False, 'RENDER'))

    # Remove the old branches from the scene and purge them from memory
    bpy.data.curves.remove(old_branches.data, True)
    bpy.data.objects.remove(old_branches, True)

    # Perform a limited dissolve
    bmesh.ops.dissolve_limit(br_bmesh, verts=br_bmesh.verts, edges=br_bmesh.edges, angle_limit=radians(angle_limit))

    # Create a new mesh and container object
    new_branches = bpy.data.objects.new('Branches', bpy.data.meshes.new('branches'))
    br_bmesh.to_mesh(new_branches.data)

    # Purge bmesh from memory
    br_bmesh.free()

    # Make the mesh active in the scene, then associate it with the tree
    scene.objects.link(new_branches)
    new_branches.matrix_world = tree.matrix_world
    new_branches.parent = tree
