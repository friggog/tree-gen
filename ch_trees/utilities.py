import bpy
import bmesh

from math import radians


def simplify_branch_geometry(context, angle_limit=1.5):
    """
    Converts tree branches from curve to mesh, then runs a limited dissolve
    to reduce their geometric complexity with minimal quality loss.
    
    [float] angle_limit :: Radian value in float form that provides the angle
                           limit for the limited dissolve. Default is 1.5
    """
    
    scene = context.scene
    tree = scene.objects.active
    
    try:
        old_branches = [child for child in tree.children if 'Branches' in child.name][0]
    except IndexError:
        raise Exception('No branches found while simplifying tree geometry')

    # Convert the branches curve to a mesh, then create an object to contain it
    branches_mesh = old_branches.to_mesh(scene, False, 'RENDER')
    new_branches = bpy.data.objects.new('branches_mesh', branches_mesh)

    # Make the mesh active in the world, then associate it with the tree
    scene.objects.link(new_branches)
    new_branches.matrix_world = tree.matrix_world
    new_branches.parent = tree

    # Get an editable copy of the mesh, perform a limited dissolve, then replace the old mesh
    br_bmesh = bmesh.new()
    br_bmesh.from_mesh(new_branches.data)
    bmesh.ops.dissolve_limit(br_bmesh, verts=br_bmesh.verts, edges=br_bmesh.edges, angle_limit=radians(angle_limit))
    br_bmesh.to_mesh(new_branches.data)
    
    # Get bmesh out of memory ASAP
    br_bmesh.clear()
    br_bmesh.free()

    # Remove the old branches from the world and finalize the name
    scene.objects.unlink(old_branches)
    new_branches.name = 'Branches'
