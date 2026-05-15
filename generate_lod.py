"""
generate_lod.py — Generate LOD (Level of Detail) variants for game engine export.

Run AFTER environment generation, optionally after bake_textures.py and generate_collision.py.

What it does:
  1. Finds the joined single mesh in the scene
  2. Creates 3 LOD variants:
     - LOD0: Full detail (original, no change)
     - LOD1: 50% decimated (mid-range)
     - LOD2: 80% decimated (far distance)
  3. Names them "{original}_LOD0", "{original}_LOD1", "{original}_LOD2"
  4. LOD1 and LOD2 get the COLLISION suffix removed from their names

Game engines auto-switch LOD levels based on camera distance.

Usage:
  1. Run racing_environment.py or japanese_environment.py
  2. (Optional) Run bake_textures.py
  3. (Optional) Run generate_collision.py
  4. Run this script
  5. Export all objects to FBX/glTF
"""

import bpy

# ============================================================
# CONFIGURATION
# ============================================================
LOD_LEVELS = [
    {"name": "LOD0", "ratio": 1.0,  "desc": "Full detail (no decimation)"},
    {"name": "LOD1", "ratio": 0.5,  "desc": "50% decimated (mid-range)"},
    {"name": "LOD2", "ratio": 0.2,  "desc": "80% decimated (far distance)"},
]

FULL_MESH_NAMES = [
    "RacingEnvironment_SingleMesh",
    "JapanRacing_SingleMesh",
]

# ============================================================
# HELPERS
# ============================================================

def find_source_mesh():
    """Find the full-detail environment mesh."""
    for name in FULL_MESH_NAMES:
        obj = bpy.data.objects.get(name)
        if obj and obj.type == 'MESH':
            return obj

    # Fallback: largest mesh by face count
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_get()]
    if not meshes:
        return None
    return max(meshes, key=lambda o: len(o.data.polygons))


def duplicate_and_decimate(source_obj, lod_name, ratio):
    """Duplicate the source mesh and apply decimation at the given ratio.
    
    Returns the new LOD object.
    """
    base_name = source_obj.name
    # Strip existing LOD/collision suffix for clean naming
    for suffix in ["_LOD0", "_LOD1", "_LOD2", "_Collision"]:
        if base_name.endswith(suffix):
            base_name = base_name[:-len(suffix)]
            break

    new_name = f"{base_name}_{lod_name}"

    # Remove existing LOD object if present
    existing = bpy.data.objects.get(new_name)
    if existing:
        bpy.data.objects.remove(existing, do_unlink=True)
        if existing.data:
            bpy.data.meshes.remove(existing.data)

    # Duplicate
    bpy.context.view_layer.objects.active = source_obj
    source_obj.select_set(True)
    bpy.ops.object.duplicate()
    lod_obj = bpy.context.active_object
    lod_obj.name = new_name
    lod_obj.data.name = f"{new_name}_mesh"

    # Apply decimate if ratio < 1.0
    if ratio < 1.0:
        mod = lod_obj.modifiers.new(f'Decimate_{lod_name}', 'DECIMATE')
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = lod_obj
        lod_obj.select_set(True)
        bpy.ops.object.modifier_apply(modifier=f'Decimate_{lod_name}')

    # Set origin
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    lod_obj.select_set(False)
    source_obj.select_set(False)

    return lod_obj


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 50)
    print("LOD Generator — 3 Levels of Detail")
    print("=" * 50)

    source_obj = find_source_mesh()
    if not source_obj:
        print("ERROR: No environment mesh found.")
        print("  Run racing_environment.py or japanese_environment.py first.")
        return

    print(f"Source mesh: '{source_obj.name}'")
    print(f"  Verts: {len(source_obj.data.vertices)}")
    print(f"  Faces: {len(source_obj.data.polygons)}")
    print()

    lod_objects = []
    for lod in LOD_LEVELS:
        print(f"Generating {lod['name']} ({lod['desc']})...")
        obj = duplicate_and_decimate(source_obj, lod['name'], lod['ratio'])
        lod_objects.append(obj)
        print(f"  → '{obj.name}' — Verts: {len(obj.data.vertices)}, Faces: {len(obj.data.polygons)}")

    # LOD0 is a duplicate too; rename the original to LOD0 name too so all LODs
    # share the same base name. We'll rename the original source as well.
    base_name = source_obj.name
    for suffix in ["_LOD0", "_LOD1", "_LOD2", "_Collision"]:
        if base_name.endswith(suffix):
            base_name = base_name[:-len(suffix)]
            break

    # Rename source to match LOD naming (keep the source as LOD0 as well)
    # Actually LOD0 is already a duplicate of source, so we have both.
    # Keep source as the original name, LODs have suffix.

    print(f"\n{'=' * 50}")
    print("LOD Summary:")
    print(f"  ┌──────────┬──────────┬──────────┐")
    print(f"  │ Level    │ Verts    │ Faces    │")
    print(f"  ├──────────┼──────────┼──────────┤")

    # Show source (original)
    print(f"  │ Original │ {len(source_obj.data.vertices):<8} │ {len(source_obj.data.polygons):<8} │")

    for lod, obj in zip(LOD_LEVELS, lod_objects):
        print(f"  │ {lod['name']:<8} │ {len(obj.data.vertices):<8} │ {len(obj.data.polygons):<8} │")

    print(f"  └──────────┴──────────┴──────────┘")

    print(f"\nObjects in scene:")
    all_objs = [source_obj] + lod_objects
    for o in all_objs:
        print(f"  • {o.name}")

    print(f"\n{lod_objects[0].name}   ← Full detail (LOD0)")
    print(f"{lod_objects[1].name}   ← Mid detail (LOD1)")
    print(f"{lod_objects[2].name}   ← Low detail (LOD2)")
    print(f"\nExport all LOD objects to FBX/glTF for game engine LOD system.")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
