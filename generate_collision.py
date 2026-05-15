"""
generate_collision.py — Generate simplified collision mesh for game engine export.

Run AFTER baking textures (optional) but BEFORE exporting to FBX/glTF.

What it does:
  1. Finds the joined single mesh in the scene (e.g., "RacingEnvironment_SingleMesh")
  2. Duplicates it
  3. Applies aggressive decimation for collision-level detail
  4. Removes all materials (collision meshes don't need them)
  5. Names it "{original}_Collision"
  6. Exports both visual + collision meshes as separate objects in the same FBX

Usage:
  - Run this after environment generation (and optionally after bake_textures.py)
  - The collision mesh will be added to the scene alongside the visual mesh
  - Both will be visible and ready for FBX/glTF export
"""

import bpy

# ============================================================
# CONFIGURATION
# ============================================================
COLLISION_DECIMATE_RATIO = 0.08   # ~92% reduction — very low poly
COLLISION_SUFFIX = "_Collision"
FULL_MESH_NAMES = [
    "RacingEnvironment_SingleMesh",
    "JapanRacing_SingleMesh",
]

# ============================================================
# HELPERS
# ============================================================

def find_visual_mesh():
    """Find the full-detail environment mesh by known name patterns."""
    for name in FULL_MESH_NAMES:
        obj = bpy.data.objects.get(name)
        if obj and obj.type == 'MESH':
            return obj

    # Fallback: find the largest mesh by face count
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_get()]
    if not meshes:
        return None
    return max(meshes, key=lambda o: len(o.data.polygons))


def generate_collision(visual_obj):
    """Create a simplified collision mesh from the visual mesh."""
    name = visual_obj.name
    col_name = f"{name}{COLLISION_SUFFIX}"

    # Remove existing collision mesh if present
    existing = bpy.data.objects.get(col_name)
    if existing:
        bpy.data.objects.remove(existing, do_unlink=True)
        if existing.data:
            bpy.data.meshes.remove(existing.data)

    # Duplicate visual mesh
    bpy.context.view_layer.objects.active = visual_obj
    visual_obj.select_set(True)

    bpy.ops.object.duplicate()
    col_obj = bpy.context.active_object
    col_obj.name = col_name
    col_obj.data.name = f"{col_name}_mesh"

    # Remove all materials from collision mesh
    col_obj.data.materials.clear()

    # Add and apply decimate modifier
    mod = col_obj.modifiers.new('CollisionDecimate', 'DECIMATE')
    mod.ratio = COLLISION_DECIMATE_RATIO
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = col_obj
    col_obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier='CollisionDecimate')

    # Remove vertex colors / UV layers (not needed for collision)
    mesh = col_obj.data
    mesh.uv_layers.clear()

    # Set origin to geometry
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    # Deselect
    col_obj.select_set(False)
    visual_obj.select_set(False)

    return col_obj


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 50)
    print("Collision Mesh Generator")
    print("=" * 50)

    visual_obj = find_visual_mesh()
    if not visual_obj:
        print("ERROR: No environment mesh found in the scene.")
        print("  Expected one of:", FULL_MESH_NAMES)
        print("  Run racing_environment.py or japanese_environment.py first.")
        return

    print(f"Visual mesh: '{visual_obj.name}'")
    print(f"  Verts: {len(visual_obj.data.vertices)}")
    print(f"  Faces: {len(visual_obj.data.polygons)}")

    col_obj = generate_collision(visual_obj)

    print(f"\nCollision mesh: '{col_obj.name}'")
    print(f"  Verts: {len(col_obj.data.vertices)}")
    print(f"  Faces: {len(col_obj.data.polygons)}")
    print(f"  Decimate ratio: {COLLISION_DECIMATE_RATIO}")

    print(f"\n{'=' * 50}")
    print(f"Done! Both meshes are in the scene:")
    print(f"  Visual: '{visual_obj.name}'")
    print(f"  Collision: '{col_obj.name}'")
    print(f"Export both as separate objects in the same FBX.")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
