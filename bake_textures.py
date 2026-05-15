"""
bake_textures.py — Bake procedural materials to image textures for game engine export.

Run AFTER generating an environment (racing_environment.py or japanese_environment.py).

What it does:
  1. Finds the joined single mesh in the scene
  2. Identifies materials with procedural texture nodes (noise, voronoi, brick)
  3. For each procedural material:
     - Bakes Albedo (diffuse color without lighting) -> {name}_Diffuse.png
     - Bakes Normal map (tangent space)         -> {name}_Normal.png
     - Bakes Ambient Occlusion                    -> {name}_AO.png
     - Creates a replacement material with baked image textures
  4. Assigns baked materials to the mesh

Output: ./baked_textures/ folder next to the .blend file (or project root)
"""

import bpy
import os

BAKE_RES = 1024          # Output texture resolution
BAKE_SAMPLES = 64        # Cycles samples for baking
OUTPUT_DIR = "baked_textures"  # Relative to .blend file or project root

# Materials with flat colors or simple emissive that don't need baking
# (they export fine as-is to game engines)
BAKE_BLACKLIST = [
    "WhiteMark", "YellowMark",
    "Tunnel_Light", "LightHead", "Lantern_Glow", "Neon",
    "Vend_Glow", "Sign_BG",
    "Yellow_Line", "White_Line", "Sign_",
    "Overpass_", "Torii_", "Sakura_", "Bridge_",
    "JP_Wall", "Stone",
]

# ============================================================
# HELPERS
# ============================================================

def get_output_dir():
    """Resolve output directory relative to .blend file or project root."""
    blend_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else "."
    out_dir = os.path.join(blend_dir, OUTPUT_DIR)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def setup_bake_scene():
    """Configure render engine and bake settings."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = BAKE_SAMPLES
    scene.cycles.use_denoising = True
    scene.render.bake.margin = 8
    scene.render.bake.use_selected_to_active = False
    scene.render.bake.use_cage = False
    scene.render.bake.target = 'IMAGE_TEXTURES'


def is_procedural(mat):
    """Check if a material has procedural texture nodes that need baking."""
    if not mat or not mat.use_nodes:
        return False
    for name in BAKE_BLACKLIST:
        if name in mat.name:
            return False
    for node in mat.node_tree.nodes:
        if node.type in ('TEX_NOISE', 'TEX_VORONOI', 'TEX_BRICK', 'TEX_WAVE', 'TEX_MAGIC'):
            return True
    return False


def get_mesh_object():
    """Find the first visible mesh object (the joined single mesh)."""
    for o in bpy.data.objects:
        if o.type == 'MESH' and not o.hide_get():
            return o
    return None


def select_faces_by_material(obj, material_index):
    """Select polygon faces that use the given material index."""
    for poly in obj.data.polygons:
        poly.select = (poly.material_index == material_index)


def bake_image(obj, mat, img, bake_type, direct=True, indirect=True):
    """Add a temporary Image Texture node to the material and bake.
    
    Args:
        obj: Mesh object being baked
        mat: Material to add the bake target to
        img: Image datablock to bake into
        bake_type: 'DIFFUSE', 'NORMAL', 'AO', etc.
        direct: Include direct light pass
        indirect: Include indirect light pass
    """
    nodes = mat.node_tree.nodes
    tex_node = nodes.new('ShaderNodeTexImage')
    tex_node.image = img
    tex_node.location = (1000, 400)
    tex_node.select = True
    nodes.active = tex_node

    scene = bpy.context.scene
    scene.render.bake.type = bake_type

    if bake_type == 'DIFFUSE':
        # Albedo: no lighting, just base color
        scene.render.bake.use_pass_direct = False
        scene.render.bake.use_pass_indirect = False
    elif bake_type == 'NORMAL':
        scene.render.bake.use_pass_direct = False
        scene.render.bake.use_pass_indirect = False
        scene.render.bake.normal_space = 'TANGENT'
    elif bake_type == 'AO':
        scene.render.bake.use_pass_direct = False
        scene.render.bake.use_pass_indirect = False
    else:
        scene.render.bake.use_pass_direct = direct
        scene.render.bake.use_pass_indirect = indirect

    bpy.ops.object.bake()
    nodes.remove(tex_node)


def create_baked_material(orig_name, img_diff, img_norm, img_ao, out_dir):
    """Create a new material that uses baked image textures instead of procedural nodes.
    
    The material packs:
    - R channel of AO image -> Roughness input
    - G channel of AO image -> Metallic input  
    - B channel of AO image -> unused (for now)
    
    Returns the new material.
    """
    bake_mat = bpy.data.materials.new(f"{orig_name}_Baked")
    bake_mat.use_nodes = True
    nt = bake_mat.node_tree
    nodes = nt.nodes
    links = nt.links

    # Clear default nodes
    for n in list(nodes):
        nodes.remove(n)

    # --- Nodes ---
    tex_diff = nodes.new('ShaderNodeTexImage')
    tex_diff.image = img_diff
    tex_diff.location = (-800, 400)

    tex_norm = nodes.new('ShaderNodeTexImage')
    tex_norm.image = img_norm
    tex_norm.location = (-800, 100)

    tex_ao = nodes.new('ShaderNodeTexImage')
    tex_ao.image = img_ao
    tex_ao.location = (-800, -200)

    nmap = nodes.new('ShaderNodeNormalMap')
    nmap.location = (-600, 100)

    # Separate AO image into R (roughness) and G (metallic)
    separate = nodes.new('ShaderNodeSeparateColor')
    separate.location = (-600, -200)
    separate.mode = 'RGB'

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (-400, 200)

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (-100, 200)

    # --- Connections ---
    links.new(tex_diff.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(tex_diff.outputs['Alpha'], bsdf.inputs['Alpha'])
    links.new(tex_norm.outputs['Color'], nmap.inputs['Color'])
    links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
    links.new(tex_ao.outputs['Color'], separate.inputs['Color'])
    links.new(separate.outputs['R'], bsdf.inputs['Roughness'])
    links.new(separate.outputs['G'], bsdf.inputs['Metallic'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return bake_mat


# ============================================================
# MAIN
# ============================================================

def bake_all():
    """Main entry point — bake all procedural materials to image textures."""
    print("=" * 50)
    print("Texture Baker — Procedural → Image Textures")
    print("=" * 50)

    obj = get_mesh_object()
    if not obj:
        print("ERROR: No mesh objects found in the scene.")
        print("  Run racing_environment.py or japanese_environment.py first.")
        return

    out_dir = get_output_dir()
    setup_bake_scene()

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Find procedural materials and their slots
    mats_to_bake = []
    for i, slot in enumerate(obj.material_slots):
        mat = slot.material
        if mat and is_procedural(mat):
            mats_to_bake.append((mat, i))

    if not mats_to_bake:
        print("No procedural materials found to bake.")
        return

    print(f"Found {len(mats_to_bake)} procedural materials:")
    for mat, idx in mats_to_bake:
        print(f"  [{idx}] {mat.name}")

    # Store replacements: (slot_index, new_baked_material)
    replacements = []

    for mat, slot_idx in mats_to_bake:
        print(f"\n--- Baking '{mat.name}' (slot {slot_idx}) ---")

        # Select only faces using this material
        bpy.ops.mesh.select_all(action='DESELECT')
        select_faces_by_material(obj, slot_idx)

        face_count = sum(1 for p in obj.data.polygons if p.select)
        if face_count == 0:
            print(f"  Skipped: no faces with this material.")
            continue
        print(f"  Faces: {face_count}")

        # Create image datablocks
        img_diff = bpy.data.images.new(f"{mat.name}_Diffuse", BAKE_RES, BAKE_RES, alpha=True)
        img_norm = bpy.data.images.new(f"{mat.name}_Normal", BAKE_RES, BAKE_RES, alpha=False)
        img_ao = bpy.data.images.new(f"{mat.name}_AO", BAKE_RES, BAKE_RES, alpha=False)

        img_diff.colorspace_settings.name = 'sRGB'
        img_norm.colorspace_settings.name = 'Non-Color'
        img_ao.colorspace_settings.name = 'Non-Color'

        # --- Bake Albedo (Diffuse, no lighting) ---
        print("  Baking Albedo...")
        bake_image(obj, mat, img_diff, 'DIFFUSE')

        # --- Bake Normal Map ---
        print("  Baking Normal...")
        bake_image(obj, mat, img_norm, 'NORMAL')

        # --- Bake AO (stored for Roughness/Metallic packing) ---
        print("  Baking AO...")
        bake_image(obj, mat, img_ao, 'AO')

        # --- Save images to disk ---
        print("  Saving PNGs...")
        def save_image(img, filename):
            path = os.path.join(out_dir, filename)
            # Use save_render for sRGB images (applies color management),
            # use filepath_raw + save for Non-Color data
            if img.colorspace_settings.name == 'sRGB':
                img.save_render(filepath=path)
            else:
                img.filepath_raw = path
                img.save()

        save_image(img_diff, f"{mat.name}_Diffuse.png")
        save_image(img_norm, f"{mat.name}_Normal.png")
        save_image(img_ao, f"{mat.name}_AO.png")

        # Remove image datablocks from memory (they remain on disk as PNGs)
        # We keep them to assign to the baked material below

        print(f"  ✓ {mat.name}_Diffuse.png, _Normal.png, _AO.png")

        # Create replacement material
        bake_mat = create_baked_material(mat.name, img_diff, img_norm, img_ao, out_dir)
        replacements.append((slot_idx, bake_mat))

    # Assign baked materials
    if replacements:
        print(f"\n--- Assigning {len(replacements)} baked materials ---")
        for slot_idx, bake_mat in replacements:
            obj.data.materials[slot_idx] = bake_mat
            print(f"  Slot [{slot_idx}] ← {bake_mat.name}")

    bpy.ops.mesh.select_all(action='DESELECT')
    print(f"\n{'=' * 50}")
    print(f"Bake complete! Textures saved to: {out_dir}")
    print(f"Materials updated to use baked image textures.")
    print(f"Now export: File > Export > FBX or glTF")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    bake_all()
