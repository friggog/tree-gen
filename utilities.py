import bpy
import bmesh
import mathutils

import random
import sys
import threading
import time
from queue import Queue


class _LogThread(threading.Thread):
    # Set to run as a daemon, so this thread kills itself at program termination

    def __init__(self, queue):
        threading.Thread.__init__(self)

        self.queue = queue
        self.daemon = True
        self.running = False

    def run(self):
        self.running = True

        while True:
            msg = self.queue.get()
            sys.stdout.write(str(msg))
            sys.stdout.flush()


thread_queue = None
log_thread = None


def get_logger(logging):
    global log_thread, thread_queue

    if logging:
        if log_thread is None:
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

    def update_log(msg):
        pass

    return lambda _: None


def object_deleted(o):
    try:
        return bpy.data.objects.get(o.name, None) is not None
    except ReferenceError:  # o is deleted, so accessing name raises an error
        return True


def convert_to_mesh(context):
    """
    Converts tree branches from curve to mesh
    """

    from . import parametric
    update_log = parametric.gen.update_log

    try:
        tree = context.object
    except AttributeError:
        raise Exception('Could not find tree while attempting to convert to mesh')

    old_branches = None
    for child in tree.children:
        if child.name.startswith('Branches'):
            old_branches = child
            break

    if old_branches is None:
        raise Exception('No branches found while converting to mesh')

    old_branch_name = old_branches.name
    old_mesh_name = old_branches.data.name

    # Convert the branches curve to a mesh, then get an editable copy
    old_branch_mesh = old_branches.to_mesh()
    br_bmesh = bmesh.new()
    br_bmesh.from_mesh(old_branch_mesh)

    # Purge old branch data from memory
    old_branches.to_mesh_clear()

    bpy.data.curves.remove(old_branches.data)

    if not object_deleted(old_branches):
        bpy.data.objects.remove(old_branches, True)

    # Create a new mesh and container object
    new_branches = bpy.data.objects.new(old_branch_name, bpy.data.meshes.new(old_mesh_name))
    br_bmesh.to_mesh(new_branches.data)

    # Purge bmesh from memory
    br_bmesh.free()

    # Make the mesh active in the scene, then associate it with the tree
    context.collection.objects.link(new_branches)
    new_branches.matrix_world = tree.matrix_world
    new_branches.parent = tree

    if context.scene.tree_gen_merge_verts_by_distance:
        update_log('Merging duplicate vertices; this will take a bit for complex trees.\n')

        context.view_layer.objects.active = new_branches
        bpy.ops.object.mode_set(mode='EDIT', toggle=True)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0001)


def generate_lods(context, level_count=3):
    from . import parametric
    update_log = parametric.gen.update_log

    try:
        tree = context.object
    except AttributeError:
        raise Exception('Could not find tree while attempting to generate LODs')

    original = None
    for child in tree.children:
        if child.name.startswith('Branches'):
            base_name = child.name
            child.name = child.name + '_LOD0'
            child.data.name = child.data.name + '_LOD0'
            original = child
            parent = child.parent
            break

    if original is None:
        raise Exception('No branches found while attempting to generate LODs')

    resolutions = [3, 2, 1]
    dissolve_ratios = [.9, .7, .5]
    for level in range(level_count):
        lod_level_name = '_LOD' + str(level + 1)

        # Create copy of curve
        new_curve = original.copy()
        new_curve.data = original.data.copy()
        curve_bmesh = bmesh.new()  # Create a modifiable mesh data container

        # Set the resolution of the new curve and convert to mesh
        new_curve.data.resolution_u = resolutions[level]
        temp_mesh = new_curve.to_mesh()
        curve_bmesh.from_mesh(temp_mesh)
        new_curve.to_mesh_clear()

        # Create a new object, copy data from curve_bmesh into it, and purge bmesh from memory
        new_branches = bpy.data.objects.new(base_name + lod_level_name, bpy.data.meshes.new('branches' + lod_level_name))
        curve_bmesh.to_mesh(new_branches.data)
        curve_bmesh.free()

        # Decimate
        modifier = new_branches.modifiers.new('TreeDecimateMod', 'DECIMATE')
        modifier.ratio = dissolve_ratios[level]

        # Make the mesh active in the scene, then associate it with the tree
        context.collection.objects.link(new_branches)
        new_branches.matrix_world = parent.matrix_world
        new_branches.parent = parent

        # Select new branches and make them the active object
        bpy.ops.object.select_all(action='DESELECT')
        new_branches.select_set(True)
        context.view_layer.objects.active = new_branches

        bpy.ops.object.modifier_apply(modifier='TreeDecimateMod')
        new_branches.select_set(True)
        new_branches.hide_set(True)

        # Purge old data from memory
        bpy.data.curves.remove(new_curve.data)
        if not object_deleted(new_curve):
            bpy.data.objects.remove(new_curve, True)

        context.view_layer.objects.active = tree

        update_log('\rBranch LOD level ' + str(level + 1) + '/' + str(level_count) + ' generated')

    update_log('\n')

    _generate_leaf_lods(context, level_count)

    context.view_layer.update()

    update_log('\n')


def _generate_leaf_lods(context, level_count=3):
    from . import parametric
    update_log = parametric.gen.update_log

    tree = context.object

    original = None
    for child in tree.children:
        if child.name.startswith('Leaves'):
            base_name = child.name
            child.name = child.name + '_LOD0'
            original = child
            parent = child.parent
            break

    if original is None:
        raise Exception('No leaves found while attempting to generate LODs')

    leaf_count = len(original.data.polygons)
    lod_reduce_amounts = [.9, .6, .4]
    lod_leaf_counts = [round(leaf_count * lod_reduce_amounts[0]),
                       round(leaf_count * lod_reduce_amounts[1]),
                       round(leaf_count * lod_reduce_amounts[2])]

    for level in range(level_count):
        new_leaf_data = bmesh.new()
        new_leaf_data.from_mesh(original.data)
        new_leaf_count = lod_leaf_counts[level]

        # Delete faces
        if new_leaf_count > 8:  # Prevent infinite loops
            amount_to_delete = leaf_count - new_leaf_count
            indexes_to_delete = set(random.randint(0, leaf_count - 1) for _ in range(amount_to_delete))
            while len(indexes_to_delete) < amount_to_delete:
                indexes_to_delete.add(random.randint(0, leaf_count - 1))

            new_leaf_data.faces.ensure_lookup_table()
            to_delete = [new_leaf_data.faces[i] for i in indexes_to_delete]

            bmesh.ops.delete(new_leaf_data, geom=list(to_delete), context='FACES')

        # Create new leaves object and copy the new leaves data into it
        lod_level_name = '_LOD' + str(level + 1)
        new_leaves = bpy.data.objects.new(base_name + lod_level_name, bpy.data.meshes.new('leaves' + lod_level_name))
        new_leaf_data.to_mesh(new_leaves.data)
        new_leaf_data.free()

        # Add new leaves object to the scene
        context.collection.objects.link(new_leaves)
        new_leaves.matrix_world = parent.matrix_world
        new_leaves.parent = parent
        new_leaves.hide_set(True)

        update_log('\rLeaf LOD level ' + str(level + 1) + '/' + str(level_count) + ' generated')

    context.view_layer.objects.active = tree

    update_log('\n')


def render_tree(output_path):
    from . import parametric
    update_log = parametric.gen.update_log

    update_log('\nRendering Scene\n')

    targets = None
    for obj in bpy.context.scene.objects:
        bpy.context.active_object.select_set(state=False)
        targets = [obj] + [child for child in obj.children] if obj.name.startswith('Tree') else targets

    if targets is None:
        print('Could not find a tree to render')
        return

    for target in targets:
        target.select_set(state=True)

    bpy.ops.view3d.camera_to_view_selected()

    time.sleep(.2)

    try:
        camera = bpy.context.scene.camera
    except KeyError:
        print('Could not find camera to capture with')
        return

    inv = camera.matrix_world.copy()
    inv.invert()

    vec = mathutils.Vector((0.0, 0, 1.0))  # move camera back a bit
    vec_rot = vec @ inv  # vec aligned to local axis
    camera.location = camera.location + vec_rot

    bpy.data.scenes['Scene'].render.filepath = output_path
    bpy.ops.render.render(write_still=True)
