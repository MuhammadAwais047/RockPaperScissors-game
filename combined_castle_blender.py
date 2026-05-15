"""
base_environment.py — Shared module for racing game environment generators.

Provides helpers, materials, road/terrain generation, and scene management.
Import in theme-specific scripts:
    from base_environment import *

P1 features included: sidewalks, road curbs, ground plane.
"""

import bpy, bmesh, math, random, sys, os
from mathutils import Vector

# ============================================================
# CONFIGURATION (overridable per theme)
# ============================================================
ROAD_LENGTH = 250
ROAD_WIDTH = 10
LANE_COUNT = 3
TERRAIN_WIDTH = 8
SIDEWALK_WIDTH = 2
DECIMATE_RATIO = 0.6
SEED = 42
# ============================================================
# ARTIST PROFILE INTEGRATION
# ============================================================

PROFILE_CONFIGS = {
    "NONE": {
        "label": "None",
        "decimate_ratio": 0.6,
        "export_format": "FBX",
        "export_suffix": ".fbx",
        "naming_prefix": "",
        "material_quality": "medium",
        "poly_budget": 100000,
        "scene_setup": "default",
    },
    "GAME_ASSET": {
        "label": "Game Asset Artist",
        "decimate_ratio": 0.35,
        "export_format": "FBX",
        "export_suffix": ".fbx",
        "naming_prefix": "SM_",
        "material_quality": "optimized",
        "poly_budget": 50000,
        "scene_setup": "game",
    },
    "FILM_VFX": {
        "label": "Film/VFX Artist",
        "decimate_ratio": 1.0,
        "export_format": "EXR",
        "export_suffix": ".exr",
        "naming_prefix": "",
        "material_quality": "cinematic",
        "poly_budget": 500000,
        "scene_setup": "film",
    },
    "ARCHVIZ": {
        "label": "Architectural Visualization",
        "decimate_ratio": 0.8,
        "export_format": "PNG",
        "export_suffix": ".png",
        "naming_prefix": "",
        "material_quality": "high",
        "poly_budget": 200000,
        "scene_setup": "archviz",
    },
    "ENVIRONMENT": {
        "label": "Environment Artist",
        "decimate_ratio": 0.5,
        "export_format": "FBX",
        "export_suffix": ".fbx",
        "naming_prefix": "SM_",
        "material_quality": "medium",
        "poly_budget": 100000,
        "scene_setup": "environment",
    },
    "AR_VR": {
        "label": "AR/VR/Metaverse Artist",
        "decimate_ratio": 0.2,
        "export_format": "GLB",
        "export_suffix": ".glb",
        "naming_prefix": "SM_",
        "material_quality": "optimized",
        "poly_budget": 15000,
        "scene_setup": "game",
    },
    "EDUCATIONAL": {
        "label": "Educational/Simulation Artist",
        "decimate_ratio": 0.5,
        "export_format": "GLB",
        "export_suffix": ".glb",
        "naming_prefix": "EQUIP_",
        "material_quality": "medium",
        "poly_budget": 50000,
        "scene_setup": "default",
    },
}


def get_artist_profile():
    """Read the selected artist profile from BlenderMCP panel.

    Returns:
        str: Profile key (e.g. GAME_ASSET, FILM_VFX, NONE)
             Returns NONE if the property is not registered or Blender is headless.
    """
    try:
        return bpy.context.scene.blendermcp_artist_profile
    except (AttributeError, KeyError, TypeError):
        return "NONE"


def get_profile_config(profile_key=None):
    """Get the configuration dict for a given artist profile.

    Args:
        profile_key: Profile key string. If None, reads from BlenderMCP panel.

    Returns:
        dict: Profile configuration with keys: decimate_ratio, export_format,
              naming_prefix, material_quality, poly_budget, scene_setup
    """
    if profile_key is None:
        profile_key = get_artist_profile()
    return PROFILE_CONFIGS.get(profile_key, PROFILE_CONFIGS["NONE"])


def apply_profile_config():
    """Apply the selected artist profile to the global module configuration.

    Modifies DECIMATE_RATIO based on the profile.
    Call this at the start of main() to adjust generation behavior.
    """
    global DECIMATE_RATIO
    cfg = get_profile_config()
    DECIMATE_RATIO = cfg["decimate_ratio"]
    profile_name = cfg["label"]
    print(f"  Artist Profile: {profile_name}")
    print(f"  Decimate Ratio: {DECIMATE_RATIO}")
    print(f"  Material Quality: {cfg['material_quality']}")
    print(f"  Export Format: {cfg['export_format']}")
    return cfg


def get_profile_naming(base_name, profile_key=None):
    """Apply naming convention from the artist profile.

    E.g. for Game Asset profile: Track -> SM_Track
         For Educational profile: Valve -> EQUIP_Valve

    Args:
        base_name: Original object name
        profile_key: Optional profile key. If None, reads current profile.
    Returns:
        str: Prefixed name per profile naming conventions
    """
    cfg = get_profile_config(profile_key)
    prefix = cfg["naming_prefix"]
    if prefix:
        return f"{prefix}{base_name}"
    return base_name


def get_profile_export_path(base_path, profile_key=None):
    """Get an export filepath with the correct extension for the current profile."""
    cfg = get_profile_config(profile_key)
    return f"{base_path}{cfg['export_suffix']}"


def get_profile_material_overrides(profile_key=None):
    """Get material quality overrides for the current artist profile.

    Returns a dict with keys: roughness_scale, metallic_scale, noise_detail_scale,
    bump_strength_scale, and emission_scale.
    """
    cfg = get_profile_config(profile_key)
    quality = cfg['material_quality']
    overrides = {
        'optimized': {
            'roughness_scale': 0.8,    # Slightly less rough to look better with fewer samples
            'metallic_scale': 0.9,     # Full metal response
            'noise_detail_scale': 0.5, # Simpler noise (faster, less GPU)
            'bump_strength_scale': 0.3,# Subtle bumps
            'emission_scale': 2.0,     # Brighter emission for AR/game
        },
        'medium': {
            'roughness_scale': 1.0,
            'metallic_scale': 1.0,
            'noise_detail_scale': 1.0,
            'bump_strength_scale': 1.0,
            'emission_scale': 1.0,
        },
        'high': {
            'roughness_scale': 1.2,    # More texture definition
            'metallic_scale': 1.0,
            'noise_detail_scale': 1.5, # More detailed noise
            'bump_strength_scale': 1.5,# Stronger bump mapping
            'emission_scale': 1.0,
        },
        'cinematic': {
            'roughness_scale': 0.6,    # Smoother surfaces for film
            'metallic_scale': 1.2,     # Enhanced metallic look
            'noise_detail_scale': 2.0, # Maximum detail
            'bump_strength_scale': 0.8,# Subtle but present
            'emission_scale': 0.5,     # More realistic emission
        },
    }
    return overrides.get(quality, overrides['medium'])


def adjust_material_for_profile(mat_name, base_roughness, base_metallic, profile_key=None):
    """Apply profile-based material quality adjustments to a material name string.

    Returns a suffix string to append to material names for profile-aware caching.
    Doesn't modify actual Blender materials (those are set per-object at creation time).
    """
    cfg = get_profile_config(profile_key)
    quality = cfg['material_quality']
    if quality == 'optimized':
        return f"_{quality}_r{base_roughness:.2f}_m{base_metallic:.2f}"
    elif quality == 'cinematic':
        return f"_{quality}_r{base_roughness:.2f}_m{base_metallic:.2f}"
    elif quality == 'high':
        return f"_{quality}_r{base_roughness:.2f}_m{base_metallic:.2f}"
    return ""


# ============================================================
# SCENE MANAGEMENT
# ============================================================

def clear_scene():
    """Remove all objects, meshes, and materials from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    for mat in list(bpy.data.materials): bpy.data.materials.remove(mat)

clear = clear_scene  # Japanese alias

# ============================================================
# MATERIAL HELPERS
# ============================================================

def mat(name, color, rough=0.8, metal=0.0, emit=0.0):
    """Create a simple Principled BSDF material with base color."""
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = color
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        b.inputs["Emission Strength"].default_value = emit
        if emit > 0:
            b.inputs["Emission Color"].default_value = color
    return m

mt = mat  # Japanese alias


def add_noise_texture(node_tree, bsdf, base_color, scale=5.0, detail=6.0, mix_fac=0.3):
    """Add noise texture mixed with base color for surface variation + bump."""
    nodes = node_tree.nodes; links = node_tree.links
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-800, 0)
    ns = nodes.new('ShaderNodeTexNoise'); ns.location = (-600, 0)
    ns.inputs['Scale'].default_value = scale; ns.inputs['Detail'].default_value = detail
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-400, 0)
    cr.color_ramp.elements[0].color = base_color
    c2 = (min(base_color[0]*1.3, 1), min(base_color[1]*1.3, 1), min(base_color[2]*1.3, 1), 1)
    cr.color_ramp.elements[1].color = c2
    mx = nodes.new('ShaderNodeMixRGB'); mx.location = (-200, 0)
    mx.inputs['Fac'].default_value = mix_fac
    mx.inputs['Color1'].default_value = base_color
    links.new(tc.outputs['Object'], ns.inputs['Vector'])
    links.new(ns.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], mx.inputs['Color2'])
    links.new(mx.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-200, -200)
    bp.inputs['Strength'].default_value = 0.15
    links.new(ns.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])

add_tex = add_noise_texture  # Japanese alias


# --- Procedural Material Creators ---

def make_asphalt():
    """Road asphalt with fine grain noise and cracks."""
    m = bpy.data.materials.new("Asphalt_Tex"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF"); bsdf.inputs['Roughness'].default_value = 0.92
    base = (0.04, 0.04, 0.05, 1)
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-900, 0)
    n1 = nodes.new('ShaderNodeTexNoise'); n1.location = (-700, 100)
    n1.inputs['Scale'].default_value = 50; n1.inputs['Detail'].default_value = 8
    n2 = nodes.new('ShaderNodeTexNoise'); n2.location = (-700, -100)
    n2.inputs['Scale'].default_value = 150; n2.inputs['Detail'].default_value = 4
    links.new(tc.outputs['Object'], n1.inputs['Vector'])
    links.new(tc.outputs['Object'], n2.inputs['Vector'])
    mx = nodes.new('ShaderNodeMixRGB'); mx.location = (-500, 0)
    mx.inputs['Fac'].default_value = 0.3
    mx.inputs['Color1'].default_value = base
    mx.inputs['Color2'].default_value = (0.02, 0.02, 0.025, 1)
    links.new(n1.outputs['Fac'], mx.inputs['Fac'])
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-300, 0)
    cr.color_ramp.elements[0].color = (0.03,0.03,0.035,1)
    cr.color_ramp.elements[1].color = (0.06,0.06,0.065,1)
    links.new(mx.outputs['Color'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-300, -200)
    bp.inputs['Strength'].default_value = 0.2
    links.new(n2.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m

mat_asphalt = make_asphalt
mt_asphalt = make_asphalt


def make_grass():
    """Grass terrain with noise + voronoi color variation."""
    m = bpy.data.materials.new("Grass_Tex"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF"); bsdf.inputs['Roughness'].default_value = 1.0
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-800, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-600, 0)
    n.inputs['Scale'].default_value = 8; n.inputs['Detail'].default_value = 10
    v = nodes.new('ShaderNodeTexVoronoi'); v.location = (-600, -200)
    v.inputs['Scale'].default_value = 15
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-400, 0)
    cr.color_ramp.elements[0].color = (0.03, 0.15, 0.02, 1)
    cr.color_ramp.elements[1].color = (0.08, 0.35, 0.05, 1)
    mx = nodes.new('ShaderNodeMixRGB'); mx.location = (-200, 0)
    mx.inputs['Fac'].default_value = 0.5
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(tc.outputs['Object'], v.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], mx.inputs['Color1'])
    mx.inputs['Color2'].default_value = (0.06, 0.25, 0.03, 1)
    links.new(v.outputs['Distance'], mx.inputs['Fac'])
    links.new(mx.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-200, -300)
    bp.inputs['Strength'].default_value = 0.4
    links.new(n.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m

mat_grass = make_grass
mt_grass = make_grass

def make_red_rock():
    """Red desert rock / adobe texture."""
    m = bpy.data.materials.new("RedRock_Tex"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.95
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-700, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-500, 0)
    n.inputs['Scale'].default_value = 15; n.inputs['Detail'].default_value = 6
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-300, 0)
    cr.color_ramp.elements[0].color = (0.55, 0.25, 0.1, 1)
    cr.color_ramp.elements[1].color = (0.7, 0.35, 0.15, 1)
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-100, -200)
    bp.inputs['Strength'].default_value = 0.4
    links.new(n.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m

mat_red_rock = make_red_rock
mt_red_rock = make_red_rock


def make_concrete():
    """Concrete/sidewalk texture."""
    m = bpy.data.materials.new("Concrete_Tex"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.95
    add_noise_texture(nt, bsdf, (0.5, 0.48, 0.45, 1), scale=20, detail=8, mix_fac=0.25)
    return m

mat_concrete = make_concrete


def make_metal_tex():
    """Scratched metal texture for barriers."""
    m = bpy.data.materials.new("Metal_Tex"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.4
    bsdf.inputs['Metallic'].default_value = 0.85
    add_noise_texture(nt, bsdf, (0.6, 0.6, 0.62, 1), scale=30, detail=4, mix_fac=0.15)
    return m

mat_metal_tex = make_metal_tex


def make_bark_tex():
    """Tree bark texture."""
    m = bpy.data.materials.new("Bark_Tex"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 1.0
    add_noise_texture(nt, bsdf, (0.22, 0.12, 0.04, 1), scale=15, detail=10, mix_fac=0.4)
    return m

mat_bark_tex = make_bark_tex


def make_leaf_tex(variant=0):
    """Tree leaf texture."""
    m = bpy.data.materials.new(f"Leaf_Tex_{variant}"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.9
    colors = [(0.04, 0.28, 0.03, 1), (0.06, 0.35, 0.05, 1)]
    add_noise_texture(nt, bsdf, colors[variant % 2], scale=6, detail=5, mix_fac=0.35)
    return m

mat_leaf_tex = make_leaf_tex


def make_brick():
    """Building brick/facade texture."""
    m = bpy.data.materials.new("Brick_Tex"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.85
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-700, 0)
    brick = nodes.new('ShaderNodeTexBrick'); brick.location = (-500, 0)
    brick.inputs['Scale'].default_value = 8
    brick.inputs['Color1'].default_value = (0.35, 0.18, 0.1, 1)
    brick.inputs['Color2'].default_value = (0.45, 0.22, 0.12, 1)
    brick.inputs['Mortar'].default_value = (0.6, 0.58, 0.55, 1)
    brick.inputs['Mortar Size'].default_value = 0.02
    links.new(tc.outputs['Object'], brick.inputs['Vector'])
    links.new(brick.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-300, -200)
    bp.inputs['Strength'].default_value = 0.3
    links.new(brick.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m

mat_brick = make_brick


def make_wood():
    """Dark wood texture (Japanese style)."""
    m = bpy.data.materials.new("JP_Wood"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.9
    add_noise_texture(nt, bsdf, (0.3, 0.18, 0.08, 1), scale=12, detail=8, mix_fac=0.4)
    return m

mt_wood = make_wood


def make_tile():
    """Stone tile texture (Japanese style)."""
    m = bpy.data.materials.new("JP_Tile"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.7
    add_noise_texture(nt, bsdf, (0.15, 0.15, 0.2, 1), scale=15, detail=5, mix_fac=0.2)
    return m

mt_tile = make_tile


def make_sand():
    """Desert sand terrain with wind-ripple noise."""
    m = bpy.data.materials.new("Sand_Tex"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 1.0
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-800, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-600, 0)
    n.inputs['Scale'].default_value = 10; n.inputs['Detail'].default_value = 8
    n2 = nodes.new('ShaderNodeTexNoise'); n2.location = (-600, -200)
    n2.inputs['Scale'].default_value = 80; n2.inputs['Detail'].default_value = 4
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-400, 0)
    cr.color_ramp.elements[0].color = (0.6, 0.48, 0.25, 1)
    cr.color_ramp.elements[1].color = (0.7, 0.55, 0.3, 1)
    mx = nodes.new('ShaderNodeMixRGB'); mx.location = (-200, 0)
    mx.inputs['Fac'].default_value = 0.3
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(tc.outputs['Object'], n2.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], mx.inputs['Color1'])
    mx.inputs['Color2'].default_value = (0.55, 0.42, 0.2, 1)
    links.new(n2.outputs['Fac'], mx.inputs['Fac'])
    links.new(mx.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-200, -300)
    bp.inputs['Strength'].default_value = 0.3
    links.new(n.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m

mat_sand = make_sand
mt_sand = make_sand


def make_dirt():
    """Dirt/gravel off-road path texture with small rock noise."""
    m = bpy.data.materials.new("Dirt_Tex"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 1.0
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-800, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-600, 0)
    n.inputs['Scale'].default_value = 20; n.inputs['Detail'].default_value = 8
    n2 = nodes.new('ShaderNodeTexNoise'); n2.location = (-600, -200)
    n2.inputs['Scale'].default_value = 100; n2.inputs['Detail'].default_value = 3
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-400, 0)
    cr.color_ramp.elements[0].color = (0.35, 0.28, 0.18, 1)
    cr.color_ramp.elements[1].color = (0.45, 0.35, 0.22, 1)
    mx = nodes.new('ShaderNodeMixRGB'); mx.location = (-200, 0)
    mx.inputs['Fac'].default_value = 0.35
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(tc.outputs['Object'], n2.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], mx.inputs['Color1'])
    mx.inputs['Color2'].default_value = (0.3, 0.22, 0.12, 1)
    links.new(n2.outputs['Fac'], mx.inputs['Fac'])
    links.new(mx.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-200, -300)
    bp.inputs['Strength'].default_value = 0.5
    links.new(n.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m

mat_dirt = make_dirt
mt_dirt = make_dirt


# Material cache
_mat_cache = {}
_mc = _mat_cache  # Japanese alias

def get_mat(key, creator):
    """Cache materials to avoid creating duplicates."""
    if key not in _mat_cache:
        _mat_cache[key] = creator()
    return _mat_cache[key]

gm = get_mat  # Japanese alias


# ============================================================
# PRIMITIVE HELPERS
# ============================================================

def apply_obj(o):
    """Apply transforms to an object (location, rotation, scale)."""
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.select_set(False)

ap = apply_obj  # Japanese alias


def cube(loc, scl, material):
    """Create a cube with size=2 (scale = half-dimensions), apply, assign material."""
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = scl; o.location = loc
    apply_obj(o)
    o.data.materials.append(material)
    return o

bx = cube  # Japanese alias


def cyl(loc, r, h, verts, material):
    """Create a cylinder (max 5 verts), apply, assign material."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=min(verts, 5), radius=r, depth=h)
    o = bpy.context.active_object
    o.location = loc
    apply_obj(o)
    o.data.materials.append(material)
    return o

cy = cyl  # Japanese alias


def cone(loc, r, h, verts, material):
    """Create a cone (max 5 verts), apply, assign material."""
    bpy.ops.mesh.primitive_cone_add(vertices=min(verts, 5), radius1=r, depth=h)
    o = bpy.context.active_object
    o.location = loc
    apply_obj(o)
    o.data.materials.append(material)
    return o

cn = cone  # Japanese alias


# ============================================================
# ROAD PATH
# ============================================================

def get_road_points(n=120):
    """Generate road center points with S-curves and bridge bump."""
    pts = []
    for i in range(n):
        t = i / (n - 1)
        y = -ROAD_LENGTH/2 + ROAD_LENGTH * t
        x = 12 * math.sin(t * math.pi * 2) * (0.3 + 0.7 * math.sin(t * math.pi))
        z = 5 * math.sin((t - 0.4) / 0.1 * math.pi) if 0.4 < t < 0.5 else 0
        pts.append(Vector((x, y, z)))
    return pts

road_pts = get_road_points  # Japanese alias


def get_road_frame(pts, i):
    """Get (fwd, right, up) vectors at point i along the road."""
    if i < len(pts) - 1:
        fwd = (pts[i+1] - pts[i]).normalized()
    else:
        fwd = (pts[i] - pts[i-1]).normalized()
    up = Vector((0, 0, 1))
    right = fwd.cross(up).normalized()
    if right.length < 0.01:
        right = Vector((1, 0, 0))
    up = right.cross(fwd).normalized()
    return fwd, right, up

rd_frame = get_road_frame  # Japanese alias


# ============================================================
# ROAD MESH
# ============================================================

def create_road_mesh(pts):
    """Create road surface mesh following curved path."""
    mesh = bpy.data.meshes.new("Road")
    bm = bmesh.new(); hw = ROAD_WIDTH / 2; rows = []
    for i, p in enumerate(pts):
        _, right, _ = get_road_frame(pts, i)
        rows.append((bm.verts.new(p - right * hw + Vector((0,0,0.01))),
                     bm.verts.new(p + right * hw + Vector((0,0,0.01)))))
    bm.verts.ensure_lookup_table()
    for i in range(len(rows)-1):
        bm.faces.new([rows[i][0], rows[i][1], rows[i+1][1], rows[i+1][0]])
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new("Road", mesh)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(get_mat('asphalt', make_asphalt))
    return o

make_road = create_road_mesh


# ============================================================
# LANE MARKINGS
# ============================================================

def create_curved_markings(pts, lane_count=3):
    """Create dashed lane markings along curved road."""
    objs = []
    lane_w = ROAD_WIDTH / (lane_count * 2)
    m_yellow = mat("Yellow_Line", (0.9,0.7,0.0,1))
    m_white = mat("White_Line", (0.95,0.95,0.95,1))
    for i in range(0, len(pts)-1, 6):
        if (i // 6) % 2 != 0: continue
        p = pts[i]; p2 = pts[min(i+3, len(pts)-1)]
        _, right, _ = get_road_frame(pts, i)
        mid = (p + p2) / 2; fwd_n = (p2 - p).normalized()
        ln = (p2 - p).length
        if ln < 0.1: continue
        angle = math.atan2(fwd_n.x, fwd_n.y)
        for off in [-0.15, 0.15]:
            o = cube(mid + right * off + Vector((0,0,0.02)), (0.06, ln/2, 0.004), m_yellow)
            o.rotation_euler.z = -angle; apply_obj(o)
            objs.append(o)
        for lane in range(1, lane_count):
            for side in [-1, 1]:
                o = cube(mid + right * side * lane * lane_w + Vector((0,0,0.02)),
                         (0.06, ln/2, 0.004), m_white)
                o.rotation_euler.z = -angle; apply_obj(o)
                objs.append(o)
    return objs

make_markings = create_curved_markings


# ============================================================
# TERRAIN
# ============================================================

def create_terrain_side(pts, side):
    """Create grass terrain strip on one side of the road."""
    hw = ROAD_WIDTH/2 + SIDEWALK_WIDTH
    mesh = bpy.data.meshes.new(f"Terrain_{side}")
    bm = bmesh.new(); rows = []
    for i, p in enumerate(pts):
        _, right, _ = get_road_frame(pts, i)
        base = p + right * side * hw; base.z = max(base.z, 0)
        edge = p + right * side * (hw + TERRAIN_WIDTH); edge.z = 0
        rows.append((bm.verts.new(base), bm.verts.new(edge)))
    bm.verts.ensure_lookup_table()
    for i in range(len(rows)-1):
        if side > 0:
            bm.faces.new([rows[i][0], rows[i][1], rows[i+1][1], rows[i+1][0]])
        else:
            bm.faces.new([rows[i][0], rows[i+1][0], rows[i+1][1], rows[i][1]])
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new(f"Terrain_{side}", mesh)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(get_mat('grass', make_grass))
    return o

make_terrain = create_terrain_side


# ============================================================
# SIDEWALKS (P1 item 4: ported from racing_environment.py)
# ============================================================

def create_sidewalk_side(pts, side):
    """Create sidewalk strip between road edge and terrain."""
    mesh = bpy.data.meshes.new(f"Sidewalk_{side}")
    bm = bmesh.new(); hw = ROAD_WIDTH/2; sw = SIDEWALK_WIDTH; rows = []
    for i, p in enumerate(pts):
        _, right, _ = get_road_frame(pts, i)
        rows.append((bm.verts.new(p + right * side * hw + Vector((0,0,0.02))),
                     bm.verts.new(p + right * side * (hw + sw) + Vector((0,0,0.15)))))
    bm.verts.ensure_lookup_table()
    for i in range(len(rows)-1):
        if side > 0:
            bm.faces.new([rows[i][0], rows[i][1], rows[i+1][1], rows[i+1][0]])
        else:
            bm.faces.new([rows[i][0], rows[i+1][0], rows[i+1][1], rows[i][1]])
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new(f"Sidewalk_{side}", mesh)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(get_mat('concrete', make_concrete))
    return o


# ============================================================
# ROAD CURBS (P1 item 5: new)
# ============================================================

def create_road_curbs(pts):
    """Add raised curb edges between road surface and sidewalk.
    
    Creates small raised strips (height ~0.12, width ~0.15) along
    both sides of the road, following the curved path.
    """
    objs = []
    m_curb = get_mat('concrete', make_concrete)
    hw = ROAD_WIDTH/2
    step = max(1, len(pts) // 60)

    for side in [-1, 1]:
        for i in range(0, len(pts)-step, step):
            p = pts[i]; p2 = pts[min(i+step, len(pts)-1)]
            _, right, _ = get_road_frame(pts, i)
            pos1 = p + right * side * hw
            pos2 = p2 + right * side * hw
            mid = (pos1 + pos2) / 2 + Vector((0, 0, 0.06))
            diff = pos2 - pos1; ln = diff.length
            if ln < 0.1: continue
            angle = math.atan2(diff.x, diff.y)

            # Bottom curb strip
            bpy.ops.mesh.primitive_cube_add(size=1)
            o = bpy.context.active_object
            o.scale = (0.06, ln/2, 0.06)
            o.location = mid; o.rotation_euler.z = -angle
            apply_obj(o); o.data.materials.append(m_curb); objs.append(o)

            # Top curb lip
            bpy.ops.mesh.primitive_cube_add(size=1)
            o2 = bpy.context.active_object
            o2.scale = (0.06, ln/2, 0.03)
            o2.location = mid + Vector((0, 0, 0.12))
            o2.rotation_euler.z = -angle
            apply_obj(o2); o2.data.materials.append(m_curb); objs.append(o2)

    return objs


# ============================================================
# GROUND PLANE (P1 item 6: new)
# ============================================================

def create_ground_plane(size=500):
    """Add a large flat plane at z=-0.05 as fallback ground.
    
    Prevents visible gaps from oblique camera angles where terrain
    strips don't fully cover the view. Single quad, grass material.
    """
    m_grass = get_mat('grass', make_grass)
    o = cube(Vector((0, 0, -0.05)), (size/2, size/2, 0.05), m_grass)
    o.name = "GroundPlane"
    return o


# ============================================================
# DIRT / OFF-ROAD PATH
# ============================================================

def create_dirt_path(main_pts, branch_idx, side, path_len=30, path_width=1.2, curve_angle=None):
    """Create a dirt/gravel off-road path branching from the main road.

    Generates a curved dirt path that starts at the main road edge and
    meanders away into the terrain. Handy for off-road sections.

    Args:
        main_pts: list of main road center points (Vector)
        branch_idx: index into main_pts where the path branches off
        side: -1 or 1 (which side of the road)
        path_len: total length of the dirt path
        path_width: half-width of the dirt strip
        curve_angle: optional override for the branch angle (radians)

    Returns:
        tuple (dirt_path_obj, end_pos) where end_pos is the far end of the path
    """
    m_dirt = get_mat('dirt', make_dirt)
    n_segments = 15
    dirt_pts = []

    # Starting point: at the road edge on the given side
    p0 = main_pts[min(branch_idx, len(main_pts) - 1)]
    _, right, _ = get_road_frame(main_pts, branch_idx)
    start_pos = p0 + right * side * (ROAD_WIDTH / 2 + SIDEWALK_WIDTH)
    start_pos.z = max(start_pos.z, 0)

    # Branch angle: perpendicular-ish away from road with slight randomness
    branch_angle = math.atan2(right.x, right.y)
    if side == 1:
        branch_angle += math.pi / 2 + random.uniform(-0.2, 0.2)
    else:
        branch_angle -= math.pi / 2 + random.uniform(-0.2, 0.2)
    if curve_angle is not None:
        branch_angle = curve_angle

    # Generate path points with gentle meander
    seg_len = path_len / n_segments
    for i in range(n_segments + 1):
        t = i / n_segments
        # Gentle S-curve meander
        meander = math.sin(t * math.pi * 2.5) * 1.5 * t
        angle_offset = branch_angle + meander * 0.1
        dx = math.cos(angle_offset) * seg_len * i
        dy = math.sin(angle_offset) * seg_len * i
        pt = Vector((start_pos.x + dx, start_pos.y + dy, 0.01))
        dirt_pts.append(pt)

    # Create the dirt mesh strip
    mesh = bpy.data.meshes.new("DirtPath")
    bm = bmesh.new()
    rows = []
    for i, p in enumerate(dirt_pts):
        # Compute local direction for this segment
        if i < len(dirt_pts) - 1:
            fwd = (dirt_pts[i + 1] - dirt_pts[i]).normalized()
        else:
            fwd = (dirt_pts[i] - dirt_pts[i - 1]).normalized()
        up = Vector((0, 0, 1))
        r = fwd.cross(up).normalized()
        if r.length < 0.01:
            r = Vector((1, 0, 0))
        rows.append((
            bm.verts.new(p - r * path_width),
            bm.verts.new(p + r * path_width)
        ))
    bm.verts.ensure_lookup_table()
    for i in range(len(rows) - 1):
        bm.faces.new([rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]])
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new("DirtPath", mesh)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(m_dirt)

    end_pos = dirt_pts[-1] if dirt_pts else start_pos
    return o, end_pos


# ============================================================
# JOIN ALL MESHES
# ============================================================

def join_all(mesh_name="Environment_SingleMesh"):
    """Join all mesh objects into a single mesh, clean, decimate."""
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    if not meshes: return None
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    result = bpy.context.active_object
    result.name = mesh_name

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.01)
    bpy.ops.mesh.dissolve_degenerate(threshold=0.01)
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.01)
    bpy.ops.object.mode_set(mode='OBJECT')

    if DECIMATE_RATIO < 1.0:
        mod = result.modifiers.new('Dec', 'DECIMATE')
        mod.ratio = DECIMATE_RATIO
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier='Dec')
        print(f"  Decimated to {DECIMATE_RATIO*100:.0f}% of original")

    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    return result


# ============================================================
# TRAFFIC PROPS (P2 item 8)
# ============================================================

# Car color palette
CAR_COLORS = [
    (0.85, 0.05, 0.05, 1),   # Red
    (0.1, 0.3, 0.8, 1),      # Blue
    (0.95, 0.95, 0.95, 1),   # White
    (0.15, 0.15, 0.15, 1),   # Black
    (0.6, 0.6, 0.6, 1),      # Silver
    (0.1, 0.6, 0.1, 1),      # Green
    (0.9, 0.6, 0.0, 1),      # Yellow
]

def create_car(pos, rot=0.0):
    """Create a low-poly car with body, cabin, and 4 wheels.
    
    Args:
        pos: Vector - ground-level center position
        rot: float - rotation around Z axis in radians
    Returns:
        list of objects
    """
    objs = []
    car_color = random.choice(CAR_COLORS)
    mc = mat("Car_Body", car_color, rough=0.4, metal=0.6)
    mw = mat("Car_Window", (0.2, 0.3, 0.5, 1), rough=0.1, metal=0.3)
    mt = mat("Car_Tire", (0.08, 0.08, 0.08, 1), rough=0.95)
    ml = mat("Car_Light", (0.95, 0.9, 0.7, 1), emit=1.0)

    cl = 2.2  # Car length half
    cw = 0.9  # Car width half
    ch = 0.25 # Body height

    # Car body (lower box)
    bpy.ops.mesh.primitive_cube_add(size=2)
    body = bpy.context.active_object
    body.scale = (cl, cw, ch)
    body.location = pos + Vector((0, 0, ch))
    body.rotation_euler.z = rot
    apply_obj(body)
    body.data.materials.append(mc)
    objs.append(body)

    # Cabin (upper box, narrower)
    bpy.ops.mesh.primitive_cube_add(size=2)
    cab = bpy.context.active_object
    cab_h = 0.2
    cab.scale = (cl*0.5, cw*0.7, cab_h)
    cab.location = pos + Vector((0, 0, ch*2 + cab_h))
    cab.rotation_euler.z = rot
    apply_obj(cab)
    cab.data.materials.append(mw)
    objs.append(cab)

    # 4 wheels
    for side in [-1, 1]:
        for ax in [-1, 1]:
            wh_pos = pos + Vector((ax * cl * 0.7, side * (cw + 0.15), ch * 0.3))
            objs.append(cyl(wh_pos, 0.12, 0.12, 5, mt))

    # Headlight rectangles
    bpy.ops.mesh.primitive_cube_add(size=2)
    hl = bpy.context.active_object
    hl.scale = (0.02, cw*0.4, ch*0.4)
    hl.location = pos + Vector((cl + 0.01, 0, ch))
    hl.rotation_euler.z = rot
    apply_obj(hl)
    hl.data.materials.append(ml)
    objs.append(hl)

    bpy.ops.mesh.primitive_cube_add(size=2)
    tl = bpy.context.active_object
    tl.scale = (0.02, cw*0.4, ch*0.4)
    tl.location = pos + Vector((-cl - 0.01, 0, ch))
    tl.rotation_euler.z = rot
    apply_obj(tl)
    tl.data.materials.append(mat("Car_Tail", (0.8, 0.1, 0.1, 1), emit=0.5))
    objs.append(tl)

    return objs


def create_traffic_cone(pos):
    """Create a traffic cone."""
    objs = []
    mo = mat("Cone_Orange", (0.95, 0.4, 0.05, 1), rough=0.7)
    mw = mat("Cone_White", (0.95, 0.95, 0.95, 1), rough=0.7)

    # Cone body
    objs.append(cone(pos + Vector((0, 0, 0.35)), 0.15, 0.6, 5, mo))

    # White reflective bands
    for h_off in [0.15, 0.35]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        o = bpy.context.active_object
        o.scale = (0.14, 0.14, 0.02)
        o.location = pos + Vector((0, 0, h_off))
        apply_obj(o)
        o.data.materials.append(mw)
        objs.append(o)

    # Square base
    objs.append(cube(pos + Vector((0, 0, 0.03)), (0.2, 0.2, 0.03), mo))

    return objs


def create_water_barrier(pos, rot=0.0):
    """Create a water/construction barrier block (orange/white)."""
    objs = []
    mo = mat("Barrier_Orange", (0.9, 0.35, 0.05, 1), rough=0.8)
    mw = mat("Barrier_White", (0.95, 0.95, 0.95, 1), rough=0.8)

    bw = 0.5  # half-width
    bd = 0.25 # half-depth
    bh = 0.4  # half-height

    # Main body
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (bw, bd, bh)
    o.location = pos + Vector((0, 0, bh))
    o.rotation_euler.z = rot
    apply_obj(o)
    o.data.materials.append(mo)
    objs.append(o)

    # White reflective stripes
    for x_off in [-0.3, 0.3]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        s = bpy.context.active_object
        s.scale = (0.06, bd+0.01, bh*0.5)
        s.location = pos + Vector((x_off, 0, bh))
        s.rotation_euler.z = rot
        apply_obj(s)
        s.data.materials.append(mw)
        objs.append(s)

    # Top fill hole detail
    objs.append(cube(pos + Vector((0, 0, bh*1.8)), (0.3, 0.15, 0.04), mo))

    return objs


def create_bench(pos, rot=0.0):
    """Create a park bench."""
    objs = []
    mw = mat("Bench_Wood", (0.4, 0.25, 0.1, 1), rough=0.9)
    mm = mat("Bench_Metal", (0.15, 0.15, 0.15, 1), rough=0.6, metal=0.5)

    bl = 0.9  # half-length
    bw = 0.15 # seat slat half-width

    # Seat slats (3 planks)
    for i in [-1, 0, 1]:
        objs.append(cube(pos + Vector((i*bw*0.8, 0, 0.2)), (bw, bl, 0.04), mw))

    # Backrest (2 vertical + horizontal)
    objs.append(cube(pos + Vector((0, -bl+0.05, 0.4)), (bw*1.2, 0.03, 0.2), mw))
    objs.append(cube(pos + Vector((0.08, -bl+0.05, 0.3)), (0.03, 0.03, 0.15), mw))
    objs.append(cube(pos + Vector((-0.08, -bl+0.05, 0.3)), (0.03, 0.03, 0.15), mw))

    # Legs (4)
    for side in [-1, 1]:
        for fwd in [-1, 1]:
            objs.append(cyl(pos + Vector((side*0.12, fwd*bl*0.8, 0.08)), 0.02, 0.16, 5, mm))

    return objs


def create_dumpster(pos, rot=0.0):
    """Create a dumpster container."""
    objs = []
    mg = mat("Dumpster_Green", (0.15, 0.35, 0.1, 1), rough=0.7, metal=0.4)
    md = mat("Dumpster_Dark", (0.08, 0.08, 0.08, 1), rough=0.8)

    dw = 0.8  # half-width
    dd = 0.5  # half-depth
    dh = 0.5  # half-height

    # Main body
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (dw, dd, dh)
    o.location = pos + Vector((0, 0, dh))
    o.rotation_euler.z = rot
    apply_obj(o)
    o.data.materials.append(mg)
    objs.append(o)

    # Lid
    bpy.ops.mesh.primitive_cube_add(size=2)
    lid = bpy.context.active_object
    lid.scale = (dw*0.8, dd*0.9, 0.03)
    lid.location = pos + Vector((0.05, 0, dh*2))
    lid.rotation_euler.z = rot
    apply_obj(lid)
    lid.data.materials.append(md)
    objs.append(lid)

    # Ridges on sides
    for i in [-1, 0, 1]:
        objs.append(cube(pos + Vector((i*dw*0.5, dd+0.01, dh*0.5)), (0.02, 0.02, dh*0.6), md))

    return objs


# ============================================================
# TRAFFIC PROP PLACEMENT
# ============================================================

def place_traffic_props(pts):
    """Place traffic props (cars, cones, benches, dumpsters) along road.
    
    Places:
    - ~12 cars parked on both sides of the road
    - ~8 traffic cones near road edges
    - ~6 benches on sidewalks
    - ~4 dumpsters near building zone
    - ~6 water barriers near road edges
    """
    objs = []

    # Helper: skip bridge/tunnel zones
    def is_flat(p):
        return abs(p.z) < 0.5

    # --- Parked cars ---
    for _ in range(12):
        i = random.randint(10, len(pts)-10)
        p = pts[i]
        if not is_flat(p): continue
        _, right, _ = get_road_frame(pts, i)
        side = random.choice([-1, 1])
        dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(0.5, 2.0)
        pos = p + right * side * dist
        pos.z = max(pos.z, 0)
        # Slight random angle to look parked naturally
        rot = math.atan2(right.x, right.y) + random.uniform(-0.15, 0.15)
        objs.extend(create_car(pos, rot))

    # --- Traffic cones ---
    for _ in range(8):
        i = random.randint(5, len(pts)-5)
        p = pts[i]
        if not is_flat(p): continue
        _, right, _ = get_road_frame(pts, i)
        side = random.choice([-1, 1])
        dist = ROAD_WIDTH/2 + random.uniform(0.3, 1.0)
        pos = p + right * side * dist
        pos.z = max(pos.z, 0)
        objs.extend(create_traffic_cone(pos))

    # --- Benches ---
    for _ in range(6):
        i = random.randint(10, len(pts)-10)
        p = pts[i]
        if not is_flat(p): continue
        _, right, _ = get_road_frame(pts, i)
        side = random.choice([-1, 1])
        dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH - 0.5
        pos = p + right * side * dist
        pos.z = max(pos.z, 0)
        rot = math.atan2(right.x, right.y)
        objs.extend(create_bench(pos, rot))

    # --- Dumpsters ---
    for _ in range(4):
        i = random.randint(15, len(pts)-15)
        p = pts[i]
        if not is_flat(p): continue
        _, right, _ = get_road_frame(pts, i)
        side = random.choice([-1, 1])
        dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(1.0, 3.0)
        pos = p + right * side * dist
        pos.z = max(pos.z, 0)
        rot = math.atan2(right.x, right.y) + random.uniform(-0.1, 0.1)
        objs.extend(create_dumpster(pos, rot))

    # --- Water barriers ---
    for _ in range(6):
        i = random.randint(5, len(pts)-5)
        p = pts[i]
        if not is_flat(p): continue
        _, right, _ = get_road_frame(pts, i)
        side = random.choice([-1, 1])
        dist = ROAD_WIDTH/2 + random.uniform(0.5, 1.5)
        pos = p + right * side * dist
        pos.z = max(pos.z, 0)
        rot = math.atan2(right.x, right.y)
        objs.extend(create_water_barrier(pos, rot))

    return objs


# ============================================================
# SCENE SETUP
# ============================================================

def setup_scene(camera_loc=(40, -50, 25), sun_color=(1.0, 1.0, 1.0), use_profile=False):
    """Add sun light and camera to the scene.

    Args:
        camera_loc: Camera position tuple (x, y, z)
        sun_color: Sun light color tuple (r, g, b)
        use_profile: If True, adjusts lighting/camera based on selected artist profile.
    """
    if use_profile:
        cfg = get_profile_config()
        scene_setup = cfg['scene_setup']
        if scene_setup == 'game':
            # Brighter, more contrast for game view
            sun_energy = 5
            sun_angle = (math.radians(60), 0, math.radians(35))
        elif scene_setup == 'film':
            # Softer, more cinematic lighting
            sun_energy = 2
            sun_angle = (math.radians(35), 0, math.radians(45))
        elif scene_setup == 'archviz':
            # Warm, inviting light
            sun_energy = 4
            sun_angle = (math.radians(40), 0, math.radians(25))
            if sun_color == (1.0, 1.0, 1.0):
                sun_color = (1.0, 0.9, 0.75)
        elif scene_setup == 'environment':
            # Natural outdoor light
            sun_energy = 3.5
            sun_angle = (math.radians(50), 0, math.radians(30))
        else:
            sun_energy = 3
            sun_angle = (math.radians(45), 0, math.radians(30))
    else:
        sun_energy = 3
        sun_angle = (math.radians(45), 0, math.radians(30))

    bpy.ops.object.light_add(type='SUN', location=(10, -20, 30))
    sun = bpy.context.active_object
    sun.data.energy = sun_energy
    sun.rotation_euler = sun_angle
    sun.data.color = sun_color

    bpy.ops.object.camera_add(location=camera_loc)
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(70), 0, math.radians(35))
    bpy.context.scene.camera = cam

setup = setup_scene  # Japanese alias

# ============================================================
# EUROPEAN CASTLE ENVIRONMENT
# ============================================================
"""
European Castle Environment - Medieval Fortress Generator
=========================================================
Run inside Blender Scripting tab.
Imports shared functionality from base_environment.py.

Features:
- Square castle with crenellated walls and round corner towers
- Central keep with pitched roof and tower
- Gatehouse with portcullis and drawbridge
- Cobblestone courtyard
- Medieval village houses outside the walls
- Castle flags and banners
- Stone well, market stalls
- Surrounding forest
"""

import sys, os, bpy, math, random
from mathutils import Vector


# Embedded with base_environment below

# ============================================================
# CASTLE CONFIGURATION
# ============================================================
CASTLE_SIZE = 30          # Half-width of castle wall square
WALL_HEIGHT = 8           # Main wall height
WALL_THICKNESS = 1.2      # Wall thickness
TOWER_RADIUS = 2.5        # Corner tower radius
TOWER_HEIGHT = 14         # Corner tower height
KEEP_WIDTH = 10           # Keep half-width
KEEP_DEPTH = 8            # Keep half-depth
KEEP_HEIGHT = 10          # Keep height
BATTLEMENT_COUNT = 36     # Number of crenellations per wall side
MOAT_WIDTH = 4            # Moat half-width
VILLAGE_HOUSE_COUNT = 8   # Number of village houses
TREE_COUNT = 30           # Number of surrounding trees
SEED = 42
random.seed(SEED)

# ============================================================
# CASTLE-SPECIFIC MATERIALS
# ============================================================

def make_castle_stone():
    """Rough gray castle stone with mortar lines."""
    m = bpy.data.materials.new("Castle_Stone"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.92
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-800, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-600, 100)
    n.inputs['Scale'].default_value = 3.5; n.inputs['Detail'].default_value = 8
    n2 = nodes.new('ShaderNodeTexNoise'); n2.location = (-600, -100)
    n2.inputs['Scale'].default_value = 20; n2.inputs['Detail'].default_value = 3
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-400, 0)
    cr.color_ramp.elements[0].color = (0.35, 0.33, 0.3, 1)
    cr.color_ramp.elements[1].color = (0.45, 0.42, 0.38, 1)
    mx = nodes.new('ShaderNodeMixRGB'); mx.location = (-200, 0)
    mx.inputs['Fac'].default_value = 0.4
    mx.inputs['Color1'].default_value = (0.38, 0.36, 0.32, 1)
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], mx.inputs['Color1'])
    links.new(n2.outputs['Fac'], mx.inputs['Fac'])
    links.new(mx.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-200, -250)
    bp.inputs['Strength'].default_value = 0.6
    links.new(n.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    # Add mortar line effect via brick texture
    brick = nodes.new('ShaderNodeTexBrick'); brick.location = (-600, -300)
    brick.inputs['Scale'].default_value = 4
    brick.inputs['Mortar'].default_value = (0.25, 0.23, 0.2, 1)
    brick.inputs['Mortar Size'].default_value = 0.025
    links.new(tc.outputs['Object'], brick.inputs['Vector'])
    mx2 = nodes.new('ShaderNodeMixRGB'); mx2.location = (0, -200)
    mx2.inputs['Fac'].default_value = 0.15
    links.new(brick.outputs['Color'], mx2.inputs['Color2'])
    links.new(mx.outputs['Color'], mx2.inputs['Color1'])
    links.new(mx2.outputs['Color'], bsdf.inputs['Base Color'])
    return m

mat_castle_stone = make_castle_stone

def make_roof_tile():
    """Red/brown clay roof tile texture."""
    m = bpy.data.materials.new("Roof_Tile"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.85
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-700, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-500, 0)
    n.inputs['Scale'].default_value = 15; n.inputs['Detail'].default_value = 6
    n2 = nodes.new('ShaderNodeTexNoise'); n2.location = (-500, -200)
    n2.inputs['Scale'].default_value = 6; n2.inputs['Detail'].default_value = 4
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-300, 0)
    cr.color_ramp.elements[0].color = (0.5, 0.18, 0.08, 1)
    cr.color_ramp.elements[1].color = (0.65, 0.25, 0.1, 1)
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-100, -200)
    bp.inputs['Strength'].default_value = 0.3
    links.new(n2.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m

mat_roof_tile = make_roof_tile

def make_cobblestone():
    """Cobblestone courtyard texture."""
    m = bpy.data.materials.new("Cobblestone"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.95
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-800, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-600, 0)
    n.inputs['Scale'].default_value = 15; n.inputs['Detail'].default_value = 7
    v = nodes.new('ShaderNodeTexVoronoi'); v.location = (-600, -200)
    v.inputs['Scale'].default_value = 8
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-400, 0)
    cr.color_ramp.elements[0].color = (0.3, 0.28, 0.25, 1)
    cr.color_ramp.elements[1].color = (0.5, 0.47, 0.42, 1)
    mx = nodes.new('ShaderNodeMixRGB'); mx.location = (-200, 0)
    mx.inputs['Fac'].default_value = 0.5
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(tc.outputs['Object'], v.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], mx.inputs['Color1'])
    mx.inputs['Color2'].default_value = (0.4, 0.37, 0.33, 1)
    links.new(v.outputs['Distance'], mx.inputs['Fac'])
    links.new(mx.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-200, -300)
    bp.inputs['Strength'].default_value = 0.2
    links.new(n.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m

mat_cobblestone = make_cobblestone

def make_dark_wood():
    """Dark aged wood for doors, beams, drawbridge."""
    m = bpy.data.materials.new("Dark_Wood"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.95
    add_noise_texture(nt, bsdf, (0.2, 0.12, 0.06, 1), scale=6, detail=8, mix_fac=0.4)
    return m

mat_dark_wood = make_dark_wood

def make_banner_red():
    """Red banner with gold trim."""
    return mat("Banner_Red", (0.75, 0.08, 0.05, 1), rough=0.6)

def make_banner_blue():
    """Blue banner with gold trim."""
    return mat("Banner_Blue", (0.1, 0.3, 0.6, 1), rough=0.6)

def make_banner_gold():
    """Gold trim/embroidery."""
    return mat("Banner_Gold", (0.85, 0.65, 0.1, 1), rough=0.4, metal=0.6)

def make_iron():
    """Dark iron for portcullis, hinges."""
    return mat("Castle_Iron", (0.12, 0.12, 0.14, 1), rough=0.5, metal=0.9)

def make_plaster():
    """White/yellow plaster for village houses."""
    m = bpy.data.materials.new("Plaster"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.95
    add_noise_texture(nt, bsdf, (0.85, 0.78, 0.65, 1), scale=8, detail=4, mix_fac=0.2)
    return m

mat_plaster = make_plaster

def make_thatched_roof():
    """Straw/thatched roof for village houses."""
    m = bpy.data.materials.new("Thatch"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 1.0
    add_noise_texture(nt, bsdf, (0.5, 0.4, 0.2, 1), scale=3, detail=10, mix_fac=0.5)
    return m

mat_thatch = make_thatched_roof

# Material caches for this module
_mat_cache = {}

def get_castle_mat(key, creator):
    if key not in _mat_cache:
        _mat_cache[key] = creator()
    return _mat_cache[key]

# ============================================================
# CASTLE ELEMENT GENERATORS
# ============================================================

def make_battlement(pos, width, height):
    """Create a single crenellation (battlement tooth).
    
    Args:
        pos: Vector - center base position
        width: float - half-width of the merlon
        height: float - height of the merlon
    Returns:
        list of objects
    """
    m_stone = get_castle_mat('stone', make_castle_stone)
    objs = []
    # Merlon (raised block)
    objs.append(cube(pos + Vector((0, 0, height/2)), (width, WALL_THICKNESS/2, height/2), m_stone))
    return objs


def create_wall_section(start_pos, end_pos, height, inner_offset=0):
    """Create a wall section with battlements between two points.
    
    Args:
        start_pos: Vector - start of wall
        end_pos: Vector - end of wall
        height: float - wall height
        inner_offset: float - offset toward interior for double wall
    Returns:
        list of objects
    """
    objs = []
    m_stone = get_castle_mat('stone', make_castle_stone)
    
    mid = (start_pos + end_pos) / 2
    diff = end_pos - start_pos
    length = diff.length
    if length < 0.1:
        return objs
    
    direction = diff.normalized()
    angle = math.atan2(direction.x, direction.y)
    
    # Wall body
    bpy.ops.mesh.primitive_cube_add(size=2)
    wall = bpy.context.active_object
    wall.scale = (length/2, WALL_THICKNESS/2, height/2)
    wall.location = mid
    wall.rotation_euler.z = -angle
    apply_obj(wall)
    wall.data.materials.append(m_stone)
    objs.append(wall)
    
    # Battlements (crenellations)
    num_merlons = max(2, int(length / 1.5))
    for i in range(num_merlons):
        t = (i + 0.5) / num_merlons
        bp = start_pos.lerp(end_pos, t)
        bp.z = height  # base of merlon is at wall top
        merlon_width = length / (num_merlons * 2.5)
        is_merlon = i % 2 == 0
        if is_merlon:
            objs.append(cube(bp + Vector((0, 0, 0.6)), (merlon_width*0.8, WALL_THICKNESS/2+0.05, 0.6), m_stone))
    
    return objs


def create_tower(pos, radius, height, num_sides=8, has_flag=True):
    """Create a round castle tower with conical roof and optional flag.
    
    Args:
        pos: Vector - center base position
        radius: float - tower radius
        height: float - tower wall height
        num_sides: int - cylinder sides (8=good balance)
        has_flag: bool - add flag on top
    Returns:
        list of objects
    """
    objs = []
    m_stone = get_castle_mat('stone', make_castle_stone)
    m_roof = get_castle_mat('roof', make_roof_tile)
    
    # Tower body (cylindrical)
    objs.append(cyl(pos + Vector((0, 0, height/2)), radius, height, num_sides, m_stone))
    
    # Stone base ring
    objs.append(cyl(pos + Vector((0, 0, 0.15)), radius + 0.2, 0.3, num_sides, m_stone))
    
    # Conical roof
    roof_base = pos.z + height
    objs.append(cone(pos + Vector((0, 0, roof_base + 1.5)), radius * 0.85, 3.0, num_sides, m_roof))
    
    # Roof finial (small ball on top)
    objs.append(cyl(pos + Vector((0, 0, roof_base + 3.3)), 0.08, 0.15, num_sides, m_roof))
    
    # Battlements at top of tower
    num_merlons = 8
    for i in range(num_merlons):
        ang = (i / num_merlons) * math.pi * 2
        bp = pos + Vector((math.cos(ang) * (radius + 0.1), math.sin(ang) * (radius + 0.1), height))
        objs.append(cube(bp + Vector((0, 0, 0.5)), (0.25, 0.15, 0.5), m_stone))
    
    # Window slits (arrow loops)
    for i in range(3):
        ang = (i / 3) * math.pi * 2 + 0.3
        w_x = math.cos(ang) * (radius + 0.02)
        w_y = math.sin(ang) * (radius + 0.02)
        w_h = random.uniform(0.8, 1.5)
        objs.append(cube(pos + Vector((w_x, w_y, height * 0.6)), (0.04, 0.04, w_h/2),
                         get_castle_mat('iron', make_iron)))
    
    # Flag on top
    if has_flag:
        flag_color = random.choice(['red', 'blue'])
        m_flag = get_castle_mat(f'banner_{flag_color}',
                                make_banner_red if flag_color == 'red' else make_banner_blue)
        m_pole = get_castle_mat('iron', make_iron)
        
        flagpole_top = roof_base + 3.5
        # Pole
        objs.append(cyl(pos + Vector((0, 0, flagpole_top + 0.5)), 0.03, 1.0, 4, m_pole))
        # Flag cloth
        bpy.ops.mesh.primitive_cube_add(size=2)
        flag = bpy.context.active_object
        flag.scale = (0.5, 0.02, 0.25)
        flag.location = pos + Vector((0.3, 0, flagpole_top + 0.6))
        apply_obj(flag)
        flag.data.materials.append(m_flag)
        objs.append(flag)
    
    return objs


def create_keep(center):
    """Create the central keep (main fortress building).
    
    Args:
        center: Vector - center position of the keep
    Returns:
        list of objects
    """
    objs = []
    m_stone = get_castle_mat('stone', make_castle_stone)
    m_roof = get_castle_mat('roof', make_roof_tile)
    m_wood = get_castle_mat('wood', make_dark_wood)
    
    kw = KEEP_WIDTH
    kd = KEEP_DEPTH
    kh = KEEP_HEIGHT
    
    # Main keep body
    objs.append(cube(center + Vector((0, 0, kh/2)), (kw, kd, kh/2), m_stone))
    
    # Stone base trim
    objs.append(cube(center + Vector((0, 0, 0.2)), (kw+0.2, kd+0.2, 0.2), m_stone))
    
    # Central tower rising from keep (taller keep tower)
    tower_h = kh * 0.6
    objs.append(cyl(center + Vector((0, 0, kh + tower_h/2)), kw*0.25, tower_h, 8, m_stone))
    
    # Small roof on keep tower
    objs.append(cone(center + Vector((0, 0, kh + tower_h + 0.5)), kw*0.25*0.85, 1.5, 8, m_roof))
    
    # Keep roof (pitched)
    # Two roof halves
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        roof = bpy.context.active_object
        roof.scale = (kw * 0.55, kd/2, 0.5)
        roof.location = center + Vector((side * kw * 0.4, 0, kh))
        roof.rotation_euler.x = math.radians(side * 35)
        apply_obj(roof)
        roof.data.materials.append(m_roof)
        objs.append(roof)
    
    # Roof ridge beam
    objs.append(cube(center + Vector((0, 0, kh + 0.6)), (0.2, kd/2, 0.1), m_wood))
    
    # Windows on keep
    for side in [-1, 1]:
        for wi in range(3):
            w_x = (wi - 1) * kw * 0.4
            objs.append(cube(center + Vector((w_x, side * kd * 0.85, kh * 0.5)),
                             (0.4, 0.04, 0.6), get_castle_mat('iron', make_iron)))
    
    # Main door (arched)
    door_pos = center + Vector((0, -kd, 0))
    objs.append(cube(door_pos + Vector((0, 0.02, 1.2)), (0.6, 0.02, 1.2), m_wood))
    # Door arch
    objs.append(cube(door_pos + Vector((0, 0.02, 2.5)), (0.8, 0.03, 0.15), m_stone))
    # Door iron hinge details
    for hi in [-0.4, 0.4]:
        objs.append(cube(door_pos + Vector((hi*0.8, 0.04, 1.0)), (0.02, 0.01, 0.06), get_castle_mat('iron', make_iron)))
    
    # Banner on keep tower
    m_banner = get_castle_mat('banner_gold', make_banner_gold)
    objs.append(cyl(center + Vector((0, 0, kh + tower_h + 2)), 0.02, 2, 4, get_castle_mat('iron', make_iron)))
    bpy.ops.mesh.primitive_cube_add(size=2)
    flag = bpy.context.active_object
    flag.scale = (0.6, 0.02, 0.3)
    flag.location = center + Vector((0.4, 0, kh + tower_h + 2.5))
    apply_obj(flag)
    flag.data.materials.append(m_banner)
    objs.append(flag)
    
    return objs


def create_gatehouse(pos, facing_dir):
    """Create a gatehouse with portcullis and drawbridge.
    
    Args:
        pos: Vector - center position of gatehouse
        facing_dir: Vector - direction gate faces (outward)
    Returns:
        list of objects
    """
    objs = []
    m_stone = get_castle_mat('stone', make_castle_stone)
    m_wood = get_castle_mat('wood', make_dark_wood)
    m_iron = get_castle_mat('iron', make_iron)
    m_roof = get_castle_mat('roof', make_roof_tile)
    
    # Angle from facing direction
    angle = math.atan2(facing_dir.x, facing_dir.y)
    
    # Gatehouse walls (two flanking towers)
    tower_spacing = 2.5
    for side in [-1, 1]:
        t_pos = pos + Vector((side * tower_spacing, 0, 0))
        # Flanking tower
        objs.append(cyl(t_pos + Vector((0, 0, 4)), 1.0, 8, 8, m_stone))
        objs.append(cone(t_pos + Vector((0, 0, 8.5)), 0.8, 1.5, 8, m_roof))
    
    # Arch over gateway
    arch_pos = pos + Vector((0, 0, 4))
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=1.5, depth=1.5)
    o = bpy.context.active_object
    o.scale = (1.0, 1.0, 0.05)
    o.location = arch_pos
    o.rotation_euler.x = math.radians(90)
    apply_obj(o)
    o.data.materials.append(m_stone)
    objs.append(o)
    
    # Gateway walls (above arch)
    objs.append(cube(pos + Vector((0, 0, 5.5)), (1.5, 0.4, 1.5), m_stone))
    
    # Portcullis (iron bars)
    for bi in range(5):
        bx = (bi - 2) * 0.25
        objs.append(cyl(pos + Vector((bx, 0.02, 2)), 0.02, 4, 6, m_iron))
    # Horizontal bars
    for hh in [0.5, 1.5, 2.5]:
        objs.append(cube(pos + Vector((0, 0.02, hh)), (0.6, 0.02, 0.03), m_iron))
    # Portcullis frame
    objs.append(cube(pos + Vector((0, 0.03, 2.5)), (0.75, 0.02, 0.06), m_iron))
    objs.append(cube(pos + Vector((0, 0.03, 0.5)), (0.75, 0.02, 0.06), m_iron))
    
    # Drawbridge (angled plank)
    bpy.ops.mesh.primitive_cube_add(size=2)
    bridge = bpy.context.active_object
    bridge.scale = (0.8, 0.5, 0.04)
    bridge.location = pos + Vector((0, -1, -0.5))
    bridge.rotation_euler.x = math.radians(-25)
    apply_obj(bridge)
    bridge.data.materials.append(m_wood)
    objs.append(bridge)
    
    # Drawbridge chains (two thin cylinders angled down)
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=3, radius=0.01, depth=1.5)
        chain = bpy.context.active_object
        chain.location = pos + Vector((side * 0.4, 0, 3))
        chain.rotation_euler.x = math.radians(45 * side)
        apply_obj(chain)
        chain.data.materials.append(m_iron)
        objs.append(chain)
    
    return objs


def create_courtyard(center, size):
    """Create a cobblestone courtyard floor.
    
    Args:
        center: Vector - center of courtyard
        size: float - half-size of courtyard square
    Returns:
        list of objects
    """
    m_cobble = get_castle_mat('cobblestone', make_cobblestone)
    return [cube(center + Vector((0, 0, -0.02)), (size, size, 0.02), m_cobble)]


def create_well(pos):
    """Create a medieval stone well.
    
    Args:
        pos: Vector - center position
    Returns:
        list of objects
    """
    objs = []
    m_stone = get_castle_mat('stone', make_castle_stone)
    m_wood = get_castle_mat('wood', make_dark_wood)
    m_iron = get_castle_mat('iron', make_iron)
    
    # Well ring (stone circle)
    objs.append(cyl(pos + Vector((0, 0, 0.3)), 0.5, 0.6, 8, m_stone))
    objs.append(cyl(pos + Vector((0, 0, 0.25)), 0.35, 0.5, 8, get_castle_mat('roof', make_roof_tile)))
    
    # Support posts
    for ang in [0, math.pi/2]:
        px = pos.x + math.cos(ang) * 0.3
        py = pos.y + math.sin(ang) * 0.3
        objs.append(cyl(Vector((px, py, 0.8)), 0.03, 1.6, 4, m_wood))
    
    # Cross beam
    objs.append(cube(pos + Vector((0, 0, 1.55)), (0.35, 0.03, 0.03), m_wood))
    
    # Rope (thin cylinder)
    objs.append(cyl(pos + Vector((0, 0, 0.8)), 0.005, 0.8, 3, m_iron))
    
    # Bucket (small cylinder)
    objs.append(cyl(pos + Vector((0, 0, 0.2)), 0.08, 0.2, 5, m_wood))
    objs.append(cyl(pos + Vector((0, 0, 0.2)), 0.1, 0.02, 5, get_castle_mat('iron', make_iron)))
    
    return objs


def create_market_stall(pos, rot=0):
    """Create a medieval market stall with canopy.
    
    Args:
        pos: Vector - center position
        rot: float - Z rotation
    Returns:
        list of objects
    """
    objs = []
    m_wood = get_castle_mat('wood', make_dark_wood)
    m_roof = get_castle_mat('roof', make_roof_tile)
    
    # Table
    bpy.ops.mesh.primitive_cube_add(size=2)
    table = bpy.context.active_object
    table.scale = (0.5, 0.3, 0.4)
    table.location = pos + Vector((0, 0, 0.4))
    table.rotation_euler.z = rot
    apply_obj(table)
    table.data.materials.append(m_wood)
    objs.append(table)
    
    # Canopy posts
    for x in [-0.4, 0.4]:
        for y in [-0.25, 0.25]:
            pp = pos + Vector((x, y, 0))
            objs.append(cyl(pp + Vector((0, 0, 0.85)), 0.02, 0.85, 4, m_wood))
    
    # Canopy roof
    bpy.ops.mesh.primitive_cube_add(size=2)
    canopy = bpy.context.active_object
    canopy.scale = (0.55, 0.35, 0.03)
    canopy.location = pos + Vector((0, 0, 1.3))
    canopy.rotation_euler.z = rot
    apply_obj(canopy)
    canopy.data.materials.append(m_roof)
    objs.append(canopy)
    
    # Small items on table (colored cubes as goods)
    for gi in range(3):
        gx = (gi - 1) * 0.15
        goods_color = random.choice([(0.8, 0.6, 0.1, 1), (0.6, 0.1, 0.1, 1), (0.1, 0.5, 0.1, 1)])
        mg = mat(f"Goods_{gi}", goods_color, rough=0.8)
        objs.append(cube(pos + Vector((gx, 0, 0.65)), (0.06, 0.06, 0.04), mg))
    
    return objs


def create_village_house(pos, scale=1.0, rot=0):
    """Create a medieval village house with thatched roof.
    
    Args:
        pos: Vector - center position
        scale: float - size multiplier
        rot: float - Z rotation
    Returns:
        list of objects
    """
    objs = []
    m_plaster = get_castle_mat('plaster', make_plaster)
    m_wood = get_castle_mat('wood', make_dark_wood)
    m_thatch = get_castle_mat('thatch', make_thatched_roof)
    
    hw = 1.5 * scale  # half-width
    hd = 1.2 * scale  # half-depth
    hh = 1.2 * scale  # half-height
    
    # House body
    bpy.ops.mesh.primitive_cube_add(size=2)
    body = bpy.context.active_object
    body.scale = (hw, hd, hh)
    body.location = pos + Vector((0, 0, hh))
    body.rotation_euler.z = rot
    apply_obj(body)
    body.data.materials.append(m_plaster)
    objs.append(body)
    
    # Timber frame beams (dark wood criss-cross)
    for bx in [-1, 1]:
        objs.append(cube(pos + Vector((bx * hw * 0.85, 0, hh)), (0.04, hd*0.8, hh/2), m_wood))
    for by in [-1, 1]:
        objs.append(cube(pos + Vector((0, by * hd * 0.85, hh)), (hw*0.8, 0.04, hh/2), m_wood))
    
    # Cross beams (diagonal)
    objs.append(cube(pos + Vector((0.3*scale, 0, hh*0.5)), (0.04, hd*0.8, 0.04), m_wood))
    objs.append(cube(pos + Vector((-0.3*scale, 0, hh*1.5)), (0.04, hd*0.8, 0.04), m_wood))
    
    # Thatched roof (A-frame)
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        roof = bpy.context.active_object
        roof.scale = (hw * 1.1, hd/2, 0.5 * scale)
        roof.location = pos + Vector((side * hw * 0.3, 0, hh * 1.6))
        roof.rotation_euler.x = math.radians(side * 40)
        apply_obj(roof)
        roof.data.materials.append(m_thatch)
        objs.append(roof)
    
    # Ridge pole
    objs.append(cube(pos + Vector((0, 0, hh * 1.8)), (0.04, hd/2, 0.04), m_wood))
    
    # Door
    objs.append(cube(pos + Vector((0, hd * 0.85, hh * 0.4)), (0.2, 0.02, hh * 0.6), m_wood))
    
    # Window
    objs.append(cube(pos + Vector((hw * 0.35, hd * 0.85, hh * 0.7)), (0.15, 0.02, 0.15), get_castle_mat('iron', make_iron)))
    objs.append(cube(pos + Vector((hw * 0.35, hd * 0.87, hh * 0.7)), (0.1, 0.01, 0.1),
                     mat("Window_Glow", (0.8, 0.7, 0.4, 1), emit=2.0)))
    
    # Chimney (small stack)
    objs.append(cube(pos + Vector((0.8*scale, 0, hh*2.2*scale)), (0.1, 0.1, 0.6*scale), m_plaster))
    objs.append(cube(pos + Vector((0.8*scale, 0, hh*2.5*scale)), (0.12, 0.12, 0.04), m_wood))
    
    # Stone foundation
    objs.append(cube(pos + Vector((0, 0, 0.08)), (hw*1.1, hd*1.1, 0.08), get_castle_mat('stone', make_castle_stone)))
    
    return objs


def create_berry_bush(pos, scale=1.0):
    """Create a small green bush for courtyard."""
    mb = mat("Bush", (0.08, 0.3, 0.06, 1), rough=1.0)
    objs = []
    r = 0.2 * scale
    bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4)
    o = bpy.context.active_object
    o.scale = (r, r, r * 0.7)
    o.location = pos + Vector((0, 0, r * 0.5))
    apply_obj(o)
    o.data.materials.append(mb)
    objs.append(o)
    return objs


def create_tree_at(pos, scale=1.0):
    """Create a low-poly tree at the given position."""
    objs = []
    m_bark = get_mat('bark', make_bark_tex)
    m_leaf1 = get_mat('leaf0', lambda: make_leaf_tex(0))
    m_leaf2 = get_mat('leaf1', lambda: make_leaf_tex(1))
    objs.append(cyl(pos + Vector((0, 0, 1 * scale)), 0.2 * scale, 2 * scale, 6, m_bark))
    objs.append(cone(pos + Vector((0, 0, 2.5 * scale)), 1.8 * scale, 2 * scale, 6, m_leaf1))
    objs.append(cone(pos + Vector((0, 0, 3.8 * scale)), 1.3 * scale, 1.8 * scale, 6, m_leaf2))
    return objs


# ============================================================
# MAIN CASTLE GENERATION
# ============================================================

def main():
    print("=" * 50)
    print("  Generating European Castle Environment...")
    print("=" * 50)
    
    _mat_cache.clear()
    clear_scene()
    
    # Apply artist profile settings from BlenderMCP panel
    cfg = apply_profile_config()
    print(f"  Export Format: {cfg['export_format']}")
    print(f"  Naming Prefix: {cfg['naming_prefix']}")
    
    # Castle center
    cc = Vector((0, 0, 0))
    cs = CASTLE_SIZE
    wh = WALL_HEIGHT
    tr = TOWER_RADIUS
    
    print("[1/12] Courtyard...")
    create_courtyard(cc, cs + 1)
    
    print("[2/12] Corner towers...")
    # Four corner towers
    corners = [
        Vector((-cs + tr, -cs + tr, 0)),
        Vector(( cs - tr, -cs + tr, 0)),
        Vector(( cs - tr,  cs - tr, 0)),
        Vector((-cs + tr,  cs - tr, 0)),
    ]
    for ci, c in enumerate(corners):
        create_tower(c, tr, TOWER_HEIGHT, has_flag=True)
    
    print("[3/12] Curtain walls...")
    # Four wall sections connecting towers
    wall_pairs = [
        (Vector((-cs, -cs, 0)), Vector(( cs, -cs, 0))),  # South
        (Vector(( cs, -cs, 0)), Vector(( cs,  cs, 0))),  # East
        (Vector(( cs,  cs, 0)), Vector((-cs,  cs, 0))),  # North
        (Vector((-cs,  cs, 0)), Vector((-cs, -cs, 0))),  # West
    ]
    for i, (start, end) in enumerate(wall_pairs):
        # Leave gap on south wall for gatehouse
        if i == 0:  # South wall - split into two sections around gate
            gap_half = 3.0
            create_wall_section(start, Vector((-gap_half, -cs, 0)), wh)
            create_wall_section(Vector((gap_half, -cs, 0)), end, wh)
        else:
            create_wall_section(start, end, wh)
    
    print("[4/12] Gatehouse...")
    create_gatehouse(Vector((0, -cs, 0)), Vector((0, -1, 0)))
    
    print("[5/12] Central keep...")
    create_keep(Vector((0, 0, 0)))
    
    print("[6/12] Stone well...")
    create_well(Vector((cs * 0.3, cs * 0.35, 0)))
    
    print("[7/12] Market stalls...")
    # Stalls along the inner walls
    for si in range(4):
        stall_pos = Vector((random.uniform(-cs*0.4, cs*0.4), random.uniform(-cs*0.4, cs*0.4), 0))
        create_market_stall(stall_pos, random.uniform(0, math.pi*2))
    
    print("[8/12] Courtyard bushes...")
    # Small bushes
    for _ in range(6):
        bx = random.uniform(-cs*0.6, cs*0.6)
        by = random.uniform(-cs*0.6, cs*0.6)
        # Don't place on top of keep or well
        if abs(bx) < 4 and abs(by) < 3:
            continue
        create_berry_bush(Vector((bx, by, 0)), random.uniform(0.8, 1.3))
    
    print("[9/12] Village houses...")
    # Houses outside the castle walls
    for hi in range(VILLAGE_HOUSE_COUNT):
        side = random.choice(['north', 'east', 'west'])
        if side == 'north':
            hx = random.uniform(-cs*2.5, cs*2.5)
            hy = cs + random.uniform(2.5, 6)
        elif side == 'east':
            hx = cs + random.uniform(2.5, 6)
            hy = random.uniform(-cs*1.5, cs*1.5)
        else:  # west
            hx = -cs - random.uniform(2.5, 6)
            hy = random.uniform(-cs*1.5, cs*1.5)
        
        # Don't place too close to gatehouse (south side)
        if side == 'south' or (abs(hx) < 5 and hy < -cs - 1):
            continue
        
        create_village_house(Vector((hx, hy, 0)), random.uniform(0.7, 1.2), random.uniform(-0.3, 0.3))
    
    print("[10/12] Moat (water)...")
    # Moat - a flat water plane outside walls (partially under ground plane)
    moat_outer = cs + 2 + MOAT_WIDTH * 2
    m_water = mat("Moat_Water", (0.1, 0.25, 0.3, 1), rough=0.1, metal=0.2)
    bpy.ops.mesh.primitive_cube_add(size=2)
    moat = bpy.context.active_object
    moat.scale = (moat_outer, moat_outer, 0.005)
    moat.location = Vector((0, 0, -0.05))
    apply_obj(moat)
    moat.data.materials.append(m_water)
    
    print("[11/12] Surrounding forest...")
    # Trees placed around the outside
    for _ in range(TREE_COUNT):
        angle = random.uniform(0, math.pi * 2)
        dist = cs + MOAT_WIDTH * 2 + random.uniform(4, 20)
        tx = math.cos(angle) * dist
        ty = math.sin(angle) * dist
        
        # Skip if too close to village houses
        if any(abs(tx - hx) < 2 and abs(ty - hy) < 2 
               for hx, hy in []):  # no easy access to house positions
            continue
        
        tree_scale = random.uniform(0.5, 1.2)
        create_tree_at(Vector((tx, ty, 0)), tree_scale)
    
    print("[12/12] Joining & scene setup...")
    
    # Place ground plane
    create_ground_plane(size=500)
    
    # Join everything
    result = join_all("EuropeanCastle_SingleMesh")
    
    if result:
        v = len(result.data.vertices)
        f = len(result.data.polygons)
        m = len(result.data.materials)
        print(f"  Verts: {v:,} | Faces: {f:,} | Mats: {m}")
    
    # Scene setup with warm golden hour lighting for castle
    setup_scene(camera_loc=(55, -65, 30), sun_color=(1.0, 0.88, 0.7), use_profile=True)
    print("  DONE! Export: File > Export > FBX/glTF")
    print("=" * 50)


main()
