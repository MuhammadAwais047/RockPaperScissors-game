"""
base_environment.py + desert_environment.py — Desert Racing Environment for Blender

Run in Blender via MCP. Generates a full desert racing scene with:
sand terrain, saguaro cacti, gas station, mesa rocks, adobe bridge & overpass,
tumbleweeds, oil barrels, Route 66 diner, and off-road course.
"""

import bpy, bmesh, math, random, sys, os
from mathutils import Vector

# ============================================================
# CONFIGURATION (overridable per theme)
# ============================================================
ROAD_LENGTH = 150
ROAD_WIDTH = 10
LANE_COUNT = 3
TERRAIN_WIDTH = 8
SIDEWALK_WIDTH = 2
DECIMATE_RATIO = 0.4
SEED = 42

# ============================================================
# SCENE MANAGEMENT
# ============================================================

def clear_scene():
    """Remove all objects, meshes, and materials from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    for mat in list(bpy.data.materials): bpy.data.materials.remove(mat)

clear = clear_scene

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

mt = mat


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

add_tex = add_noise_texture


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
    """Dark wood texture."""
    m = bpy.data.materials.new("JP_Wood"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.9
    add_noise_texture(nt, bsdf, (0.3, 0.18, 0.08, 1), scale=12, detail=8, mix_fac=0.4)
    return m

mt_wood = make_wood


def make_tile():
    """Stone tile texture."""
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


# Material cache
_mat_cache = {}
_mc = _mat_cache

def get_mat(key, creator):
    """Cache materials to avoid creating duplicates."""
    if key not in _mat_cache:
        _mat_cache[key] = creator()
    return _mat_cache[key]

gm = get_mat


# ============================================================
# PRIMITIVE HELPERS
# ============================================================

def apply_obj(o):
    """Apply transforms to an object (location, rotation, scale)."""
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.select_set(False)

ap = apply_obj


def cube(loc, scl, material):
    """Create a cube with size=2 (scale = half-dimensions), apply, assign material."""
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = scl; o.location = loc
    apply_obj(o)
    o.data.materials.append(material)
    return o

bx = cube


def cyl(loc, r, h, verts, material):
    """Create a cylinder (max 5 verts), apply, assign material."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=min(verts, 5), radius=r, depth=h)
    o = bpy.context.active_object
    o.location = loc
    apply_obj(o)
    o.data.materials.append(material)
    return o

cy = cyl


def cone(loc, r, h, verts, material):
    """Create a cone (max 5 verts), apply, assign material."""
    bpy.ops.mesh.primitive_cone_add(vertices=min(verts, 5), radius1=r, depth=h)
    o = bpy.context.active_object
    o.location = loc
    apply_obj(o)
    o.data.materials.append(material)
    return o

cn = cone


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

road_pts = get_road_points


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

rd_frame = get_road_frame


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
    """Create terrain strip on one side of the road (uses grass/sand material)."""
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
    o.data.materials.append(get_mat('sand', make_sand))
    return o

make_terrain = create_terrain_side


# ============================================================
# SIDEWALKS
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
# ROAD CURBS
# ============================================================

def create_road_curbs(pts):
    """Add raised curb edges between road surface and sidewalk."""
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

            bpy.ops.mesh.primitive_cube_add(size=1)
            o = bpy.context.active_object
            o.scale = (0.06, ln/2, 0.06)
            o.location = mid; o.rotation_euler.z = -angle
            apply_obj(o); o.data.materials.append(m_curb); objs.append(o)

            bpy.ops.mesh.primitive_cube_add(size=1)
            o2 = bpy.context.active_object
            o2.scale = (0.06, ln/2, 0.03)
            o2.location = mid + Vector((0, 0, 0.12))
            o2.rotation_euler.z = -angle
            apply_obj(o2); o2.data.materials.append(m_curb); objs.append(o2)

    return objs


# ============================================================
# GROUND PLANE
# ============================================================

def create_ground_plane(size=500):
    """Add a large flat plane at z=-0.05 as fallback ground."""
    m_sand = get_mat('sand', make_sand)
    o = cube(Vector((0, 0, -0.05)), (size/2, size/2, 0.05), m_sand)
    o.name = "GroundPlane"
    return o


# ============================================================
# DIRT / OFF-ROAD PATH
# ============================================================

def create_dirt_path(main_pts, branch_idx, side, path_len=30, path_width=1.2, curve_angle=None):
    """Create a dirt/gravel off-road path branching from the main road."""
    m_dirt = get_mat('dirt', make_dirt)
    n_segments = 15
    dirt_pts = []

    p0 = main_pts[min(branch_idx, len(main_pts) - 1)]
    _, right, _ = get_road_frame(main_pts, branch_idx)
    start_pos = p0 + right * side * (ROAD_WIDTH / 2 + SIDEWALK_WIDTH)
    start_pos.z = max(start_pos.z, 0)

    branch_angle = math.atan2(right.x, right.y)
    if side == 1:
        branch_angle += math.pi / 2 + random.uniform(-0.2, 0.2)
    else:
        branch_angle -= math.pi / 2 + random.uniform(-0.2, 0.2)
    if curve_angle is not None:
        branch_angle = curve_angle

    seg_len = path_len / n_segments
    for i in range(n_segments + 1):
        t = i / n_segments
        meander = math.sin(t * math.pi * 2.5) * 1.5 * t
        angle_offset = branch_angle + meander * 0.1
        dx = math.cos(angle_offset) * seg_len * i
        dy = math.sin(angle_offset) * seg_len * i
        pt = Vector((start_pos.x + dx, start_pos.y + dy, 0.01))
        dirt_pts.append(pt)

    mesh = bpy.data.meshes.new("DirtPath")
    bm = bmesh.new()
    rows = []
    for i, p in enumerate(dirt_pts):
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
# TRAFFIC PROPS
# ============================================================

CAR_COLORS = [
    (0.85, 0.05, 0.05, 1),
    (0.1, 0.3, 0.8, 1),
    (0.95, 0.95, 0.95, 1),
    (0.15, 0.15, 0.15, 1),
    (0.6, 0.6, 0.6, 1),
    (0.1, 0.6, 0.1, 1),
    (0.9, 0.6, 0.0, 1),
]

def create_car(pos, rot=0.0):
    """Create a low-poly car with body, cabin, and 4 wheels."""
    objs = []
    car_color = random.choice(CAR_COLORS)
    mc = mat("Car_Body", car_color, rough=0.4, metal=0.6)
    mw = mat("Car_Window", (0.2, 0.3, 0.5, 1), rough=0.1, metal=0.3)
    mt = mat("Car_Tire", (0.08, 0.08, 0.08, 1), rough=0.95)
    ml = mat("Car_Light", (0.95, 0.9, 0.7, 1), emit=1.0)

    cl = 2.2; cw = 0.9; ch = 0.25

    bpy.ops.mesh.primitive_cube_add(size=2)
    body = bpy.context.active_object
    body.scale = (cl, cw, ch)
    body.location = pos + Vector((0, 0, ch))
    body.rotation_euler.z = rot
    apply_obj(body)
    body.data.materials.append(mc)
    objs.append(body)

    bpy.ops.mesh.primitive_cube_add(size=2)
    cab = bpy.context.active_object
    cab_h = 0.2
    cab.scale = (cl*0.5, cw*0.7, cab_h)
    cab.location = pos + Vector((0, 0, ch*2 + cab_h))
    cab.rotation_euler.z = rot
    apply_obj(cab)
    cab.data.materials.append(mw)
    objs.append(cab)

    for side in [-1, 1]:
        for ax in [-1, 1]:
            wh_pos = pos + Vector((ax * cl * 0.7, side * (cw + 0.15), ch * 0.3))
            objs.append(cyl(wh_pos, 0.12, 0.12, 5, mt))

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


# ============================================================
# SCENE SETUP
# ============================================================

def setup_scene(camera_loc=(40, -50, 25), sun_color=(1.0, 1.0, 1.0)):
    """Add sun light and camera to the scene."""
    bpy.ops.object.light_add(type='SUN', location=(10, -20, 30))
    sun = bpy.context.active_object
    sun.data.energy = 3
    sun.rotation_euler = (math.radians(45), 0, math.radians(30))
    sun.data.color = sun_color

    bpy.ops.object.camera_add(location=camera_loc)
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(70), 0, math.radians(35))
    bpy.context.scene.camera = cam


# ============================================================
# DESERT-SPECIFIC MATERIALS
# ============================================================

def make_adobe():
    """Adobe/mud brick texture for desert buildings."""
    m = bpy.data.materials.new("Adobe_Tex"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.95
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-700, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-500, 0)
    n.inputs['Scale'].default_value = 6; n.inputs['Detail'].default_value = 4
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-300, 0)
    cr.color_ramp.elements[0].color = (0.55, 0.3, 0.12, 1)
    cr.color_ramp.elements[1].color = (0.65, 0.38, 0.18, 1)
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-100, -200)
    bp.inputs['Strength'].default_value = 0.3
    links.new(n.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m


def make_dry_bush():
    """Dry desert bush/shrub texture."""
    m = bpy.data.materials.new("DryBush_Tex"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 1.0
    add_noise_texture(nt, bsdf, (0.25, 0.18, 0.05, 1), scale=12, detail=6, mix_fac=0.3)
    return m

mat_dry_bush = make_dry_bush


def make_cactus_skin():
    """Saguaro cactus green skin with ridges."""
    m = bpy.data.materials.new("Cactus_Tex"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.8
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-700, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-500, 0)
    n.inputs['Scale'].default_value = 30; n.inputs['Detail'].default_value = 3
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-300, 0)
    cr.color_ramp.elements[0].color = (0.1, 0.35, 0.08, 1)
    cr.color_ramp.elements[1].color = (0.15, 0.45, 0.1, 1)
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], bsdf.inputs['Base Color'])
    return m

mt_cactus = make_cactus_skin


# ============================================================
# CONFIGURATION (desert overrides)
# ============================================================
ROAD_LENGTH = 150
ROAD_WIDTH = 10
LANE_COUNT = 2
TERRAIN_WIDTH = 8
SIDEWALK_WIDTH = 2
DECIMATE_RATIO = 0.4
SEED = 42
random.seed(SEED)


# ============================================================
# ROAD PATH (flat desert S-curves)
# ============================================================
def get_desert_road_points(count=120):
    """Generate road center points with gentle desert S-curves, flat terrain."""
    pts = []
    for i in range(count):
        t = i / (count - 1)
        y = -ROAD_LENGTH/2 + ROAD_LENGTH * t
        x = 10 * math.sin(t * math.pi * 2) * (0.3 + 0.7 * math.sin(t * math.pi))
        z = 0
        pts.append(Vector((x, y, z)))
    return pts


# ============================================================
# DESERT DECORATIVE ELEMENTS
# ============================================================

def make_saguaro(pos, sc=1.0):
    """Create a saguaro cactus with branching arms."""
    objs = []
    mc = get_mat('cactus', make_cactus_skin)

    h = random.uniform(3.0, 5.5) * sc
    r = 0.12 * sc

    objs.append(cyl(pos + Vector((0, 0, h/2)), r, h, 5, mc))

    arm_count = random.randint(0, 3)
    arm_angles = [i * 2.4 + random.uniform(0, 0.8) for i in range(arm_count)]
    for ang in arm_angles:
        arm_h = random.uniform(0.8, 2.0) * sc
        arm_base_h = random.uniform(h * 0.3, h * 0.65)
        dx = math.cos(ang) * r * 1.2
        dy = math.sin(ang) * r * 1.2

        arm_len = random.uniform(0.4, 0.9) * sc
        bpy.ops.mesh.primitive_cylinder_add(vertices=5, radius=r * 0.7, depth=arm_len)
        arm_seg = bpy.context.active_object
        arm_seg.location = pos + Vector((dx, dy, arm_base_h))
        arm_seg.rotation_euler.x = math.radians(90)
        arm_seg.rotation_euler.z = ang
        apply_obj(arm_seg)
        arm_seg.data.materials.append(mc)
        objs.append(arm_seg)

        arm_angle_2 = ang + random.uniform(-0.3, 0.3)
        arm_end_x = dx + math.cos(arm_angle_2) * r * 0.7
        arm_end_y = dy + math.sin(arm_angle_2) * r * 0.7
        objs.append(cyl(pos + Vector((arm_end_x, arm_end_y, arm_base_h + arm_h/2)), r * 0.7, arm_h, 5, mc))

    return objs


def make_prickly_pear(pos, sc=1.0):
    """Create a prickly pear cactus cluster."""
    objs = []
    mp = mat("PricklyPear", (0.12, 0.4, 0.1, 1), rough=0.85)

    pad_count = random.randint(3, 6)
    for i in range(pad_count):
        dx = random.uniform(-0.2, 0.2) * sc
        dy = random.uniform(-0.2, 0.2) * sc
        pad_h = random.uniform(0.08, 0.15) * sc
        pad_w = random.uniform(0.06, 0.12) * sc
        pad_z = random.uniform(0.05, 0.25) * sc
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4)
        o = bpy.context.active_object
        o.scale = (pad_w, pad_w, pad_h)
        o.location = pos + Vector((dx, dy, pad_z))
        apply_obj(o)
        o.data.materials.append(mp)
        objs.append(o)

    return objs


def make_tumbleweed(pos, sc=1.0):
    """Create a dry tumbleweed ball."""
    objs = []
    mb = get_mat('bush', make_dry_bush)
    r = random.uniform(0.15, 0.35) * sc
    bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4)
    o = bpy.context.active_object
    o.scale = (r, r * random.uniform(0.8, 1.2), r * random.uniform(0.6, 0.9))
    o.location = pos + Vector((0, 0, r * 0.3))
    apply_obj(o)
    o.data.materials.append(mb)
    objs.append(o)
    return objs


def make_mesa(pos, w, d, h, sc=1.0):
    """Create a mesa (flat-topped rock formation)."""
    objs = []
    mr = get_mat('red_rock', make_red_rock)

    taper = 0.6
    objs.append(cube(pos + Vector((0, 0, h/2)), (w/2, d/2, h/2), mr))
    objs.append(cone(pos + Vector((0, 0, h * 0.3)), w * taper, h * 0.6, 6, mr))
    objs.append(cube(pos + Vector((0, 0, h)), (w/2 + 0.2, d/2 + 0.2, 0.1), mr))

    return objs


def make_dry_tree(pos, sc=1.0):
    """Create a dead desert tree with twisted branches."""
    objs = []
    mb = get_mat('bark', make_bark_tex)

    h = random.uniform(1.5, 3.0) * sc
    objs.append(cyl(pos + Vector((0, 0, h/2)), 0.06*sc, h, 5, mb))

    for ang in [0, 1.8, 3.2, 4.5]:
        bh = random.uniform(h * 0.5, h * 0.9)
        bl = random.uniform(0.3, 0.8) * sc
        dx = math.cos(ang) * bl/2
        dy = math.sin(ang) * bl/2
        objs.append(cyl(pos + Vector((dx, dy, bh)), 0.03*sc, bl, 4, mb))

    return objs


# ============================================================
# GAS STATION
# ============================================================
def make_gas_station(pos, rot=0.0):
    """Create a gas station with building, canopy, and pumps."""
    objs = []
    madobe = get_mat('adobe', make_adobe)
    mroof = get_mat('red_rock', make_red_rock)
    mmetal = get_mat('metal', make_metal_tex)
    mglass = mat("Gas_Glass", (0.6, 0.75, 0.85, 1), rough=0.1, metal=0.2)
    mwhite = mat("Gas_White", (0.9, 0.9, 0.9, 1), rough=0.7)
    mred = mat("Gas_Red", (0.8, 0.1, 0.05, 1), rough=0.6)
    msign = mat("Gas_Sign", (0.9, 0.7, 0.1, 1), emit=2.0)

    bw = 3.0; bd = 2.0; bh = 2.0

    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (bw, bd, bh)
    o.location = pos + Vector((0, 0, bh))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(madobe); objs.append(o)

    objs.append(cube(pos + Vector((0, 0, bh*2)), (bw+0.2, bd+0.2, 0.1), mroof))

    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (bw*0.7, 0.03, bh*0.6)
    o.location = pos + Vector((0, bd+0.02, bh*0.7))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mglass); objs.append(o)

    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (0.3, 0.03, bh*0.8)
    o.location = pos + Vector((-bw*0.4, bd+0.02, bh*0.8))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mwhite); objs.append(o)

    canopy_w = bw + 2.0; canopy_d = bd + 3.0; canopy_h = bh * 2 + 1.5

    for px in [-canopy_w/2 + 0.3, canopy_w/2 - 0.3]:
        for py in [-canopy_d/2 + 0.3, canopy_d/2 - 0.3]:
            pole_pos = pos + Vector((px, py, 0))
            objs.append(cyl(pole_pos + Vector((0, 0, canopy_h/2)), 0.06, canopy_h, 5, mmetal))

    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (canopy_w/2, canopy_d/2, 0.05)
    o.location = pos + Vector((0, 0, canopy_h))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mwhite); objs.append(o)

    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (canopy_w/2 + 0.01, 0.06, 0.04)
    o.location = pos + Vector((0, 0, canopy_h + 0.06))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mred); objs.append(o)

    pump_count = 2
    for pi in range(pump_count):
        px = (pi - (pump_count-1)/2) * 1.5
        pump_pos = pos + Vector((px, -canopy_d/2 + 0.8, 0))
        objs.append(cube(pump_pos + Vector((0, 0, 0.5)), (0.25, 0.15, 0.5), mwhite))
        objs.append(cube(pump_pos + Vector((0, 0, 0.9)), (0.15, 0.1, 0.05), msign))
        objs.append(cyl(pump_pos + Vector((0, 0, 0.95)), 0.02, 0.05, 5, mmetal))

    sign_pos = pos + Vector((0, -canopy_d/2 - 2, 0))
    objs.append(cyl(sign_pos + Vector((0, 0, 5)), 0.04, 10, 5, mmetal))
    objs.append(cube(sign_pos + Vector((0, 0, 10)), (0.6, 0.08, 0.15), msign))
    objs.append(cube(sign_pos + Vector((0, 0, 9.7)), (1.0, 0.05, 0.05), mwhite))

    return objs


# ============================================================
# DESERT OVERPASS
# ============================================================
def create_desert_overpass(pts):
    """Add a desert-themed highway overpass with adobe arches and tile roof details."""
    objs = []
    m_asphalt = get_mat('asphalt', make_asphalt)
    m_adobe = get_mat('adobe', make_adobe)
    m_red_rock = get_mat('red_rock', make_red_rock)
    m_wood = get_mat('wood', make_wood)

    idx = int(0.22 * len(pts))
    p = pts[idx]
    fwd, right, up = get_road_frame(pts, idx)
    angle = math.atan2(right.x, right.y)

    OH = 6.0; OW = ROAD_WIDTH + 8; DT = 0.35

    for side_x in [-1, 1]:
        for side_z in [-1, 1]:
            pos = p + right * side_x * (ROAD_WIDTH/2 + 1.8) + fwd * side_z * 2
            objs.append(cube(pos + Vector((0, 0, OH/2)), (0.35, 0.35, OH/2), m_adobe))
            objs.append(cube(pos + Vector((0, 0, 0.15)), (0.6, 0.6, 0.15), m_red_rock))
            objs.append(cube(pos + Vector((0, 0, OH - 0.1)), (0.55, 0.55, 0.1), m_red_rock))

    for side_x in [-1, 1]:
        for sz in [-1, 1]:
            ap1 = p + right * side_x * (ROAD_WIDTH/2 + 1.8) + fwd * sz * 2
            arch_top = (ap1 + p + fwd * sz * 2) / 2 + Vector((0, 0, OH * 0.6))
            objs.append(cube(arch_top, (0.2, 0.2, 0.15), m_adobe))

    bpy.ops.mesh.primitive_cube_add(size=2)
    deck = bpy.context.active_object
    deck.scale = (OW/2, 0.35, DT/2)
    deck.location = Vector((p.x, p.y, OH + DT/2))
    deck.rotation_euler.z = -angle; apply_obj(deck)
    deck.data.materials.append(m_asphalt); objs.append(deck)

    for fwd_off in [-2.0, 0, 2.0]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        o = bpy.context.active_object
        o.scale = (OW/2 - 1.5, 0.12, 0.15)
        bp = p + fwd * fwd_off; bp.z = OH - 0.05
        o.location = bp; o.rotation_euler.z = -angle; apply_obj(o)
        o.data.materials.append(m_adobe); objs.append(o)

    for side in [-1, 1]:
        for fwd_off in range(-3, 4):
            pp = p + right * side * (OW/2 - 0.3) + fwd * fwd_off
            pp.z = OH + DT + 0.35
            objs.append(cube(pp, (0.04, 0.04, 0.6), m_wood))

        for rail_h in [0.25, 0.5]:
            bpy.ops.mesh.primitive_cube_add(size=2)
            o = bpy.context.active_object
            o.scale = (OW/2, 0.04, 0.03)
            rp = p + right * side * (OW/2 - 0.3)
            rp.z = OH + DT + rail_h
            o.location = rp; o.rotation_euler.z = -angle; apply_obj(o)
            o.data.materials.append(m_wood); objs.append(o)

    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        o = bpy.context.active_object
        o.scale = (OW/2 - 0.3, 0.08, 0.15)
        bp = p + right * side * (OW/2 - 0.15)
        bp.z = OH + DT + 0.15
        o.location = bp; o.rotation_euler.z = -angle; apply_obj(o)
        o.data.materials.append(m_red_rock); objs.append(o)

    RAMP_LEN = 12; RAMP_W = 4.0; segs = 6
    for side in [-1, 1]:
        for s in range(segs):
            t0 = s/segs; t1 = (s+1)/segs; tm = (t0+t1)/2
            sh = OH * (t1 - t0) / 2; sch = OH * tm / 2
            rp = p + right * side * (OW/2 + tm * RAMP_LEN); rp.z = sch
            sl = RAMP_LEN / segs

            bpy.ops.mesh.primitive_cube_add(size=2)
            o = bpy.context.active_object
            o.scale = (sl/2, RAMP_W/2, max(sh, 0.05))
            o.location = rp; o.rotation_euler.z = -angle; apply_obj(o)
            o.data.materials.append(m_asphalt); objs.append(o)

            for rs in [-1, 1]:
                bpy.ops.mesh.primitive_cube_add(size=2)
                o = bpy.context.active_object
                o.scale = (sl/2, 0.06, max(sh, 0.05))
                wp = rp + fwd * rs * (RAMP_W/2 + 0.1); wp.z = sch
                o.location = wp; o.rotation_euler.z = -angle; apply_obj(o)
                o.data.materials.append(m_adobe); objs.append(o)

        ep = p + right * side * (OW/2 + RAMP_LEN); ep.z = 0.15
        objs.append(cube(ep, (0.3, RAMP_W/2, 0.15), m_adobe))

        for rs in [-1, 1]:
            for si in range(segs):
                t = (si + 0.5) / segs
                pp = p + right * side * (OW/2 + t * RAMP_LEN) + fwd * rs * (RAMP_W/2 + 0.05)
                pp.z = OH * t / 2 + 0.25
                objs.append(cube(pp, (0.04, 0.04, 0.3), m_wood))

    return objs


# ============================================================
# DESERT BRIDGE
# ============================================================
def make_desert_bridge(pts):
    """Add desert-styled bridge with adobe arch supports."""
    objs = []
    m_adobe = get_mat('adobe', make_adobe)
    m_red_rock = get_mat('red_rock', make_red_rock)
    m_wood = get_mat('wood', make_wood)

    for i, p in enumerate(pts):
        if p.z < 1.0: continue
        _, right, _ = get_road_frame(pts, i)

        if i % 10 == 0:
            for side in [-1, 1]:
                pp = p + right * side * (ROAD_WIDTH/2 - 1)
                objs.append(cube(Vector((pp.x, pp.y, p.z/2)), (0.5, 0.5, p.z/2), m_adobe))
                arch_pos = Vector((pp.x, pp.y, p.z * 0.7))
                objs.append(cube(arch_pos, (0.4, 0.15, 0.1), m_red_rock))
            objs.append(cube(Vector((p.x, p.y, p.z - 0.3)), (ROAD_WIDTH/2 + 0.5, 0.4, 0.3), m_adobe))

        if i % 4 == 0:
            for side in [-1, 1]:
                pp = p + right * side * (ROAD_WIDTH/2 + 0.1)
                objs.append(cube(pp + Vector((0, 0, 0.5)), (0.05, 0.05, 0.5), m_wood))

    return objs


# ============================================================
# DESERT ROAD SIGNS
# ============================================================
def make_desert_signs(pts):
    """Place desert-themed road signs along the road."""
    objs = []
    m_pole = mat("Sign_Pole", (0.3, 0.25, 0.2, 1), rough=0.9)
    m_sign_warn = mat("Sign_Warn", (0.9, 0.7, 0.1, 1), rough=0.7)
    m_sign_brown = mat("Sign_Brown", (0.4, 0.25, 0.1, 1), rough=0.8)
    m_sign_green = mat("Sign_Green", (0.15, 0.5, 0.1, 1), rough=0.7)
    m_white = mat("Sign_White", (0.95, 0.95, 0.95, 1), rough=0.7)

    sign_interval = len(pts) // 10
    for idx in range(10):
        i = idx * sign_interval
        if i >= len(pts): break
        p = pts[i]
        _, right, _ = get_road_frame(pts, i)
        side = 1 if idx % 2 == 0 else -1

        pos = p + right * side * (ROAD_WIDTH/2 + SIDEWALK_WIDTH + 0.5)

        objs.append(cyl(pos + Vector((0, 0, 1.5)), 0.04, 3, 5, m_pole))

        if idx % 3 == 0:
            objs.append(cube(pos + Vector((0, 0, 3.0)), (0.5, 0.03, 0.3), m_sign_green))
            if idx % 6 == 0:
                objs.append(cube(pos + Vector((0, 0, 2.5)), (0.35, 0.02, 0.05), m_white))
        elif idx % 3 == 1:
            bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=0.25, depth=0.03)
            o = bpy.context.active_object
            o.rotation_euler.z = math.radians(45)
            o.location = pos + Vector((0, 0, 3.0))
            apply_obj(o)
            o.data.materials.append(m_sign_warn)
            objs.append(o)
        else:
            objs.append(cube(pos + Vector((0, 0, 3.0)), (0.35, 0.03, 0.25), m_sign_brown))

    return objs


# ============================================================
# ROUTE 66 DINER
# ============================================================
def make_route66_diner(pos, rot=0.0):
    """Create a classic Route 66 roadside diner with neon sign and parking."""
    objs = []
    mwall = mat("Diner_Wall", (0.92, 0.88, 0.82, 1), rough=0.85)
    mtrim = mat("Diner_Trim", (0.75, 0.15, 0.25, 1), rough=0.6)
    mteal = mat("Diner_Teal", (0.1, 0.55, 0.55, 1), rough=0.6)
    mroof = mat("Diner_Roof", (0.08, 0.08, 0.12, 1), rough=0.9)
    mglass = mat("Diner_Glass", (0.55, 0.7, 0.85, 1), rough=0.1, metal=0.15)
    mchrome = mat("Diner_Chrome", (0.8, 0.8, 0.85, 1), rough=0.2, metal=0.9)
    mchecker = mat("Diner_Checker", (0.05, 0.05, 0.05, 1), rough=0.7)
    mchecker_w = mat("Diner_Checker_W", (0.95, 0.95, 0.9, 1), rough=0.7)
    mneon = mat("Diner_Neon", (0.9, 0.1, 0.3, 1), emit=6.0)
    mneon_blue = mat("Diner_Neon_B", (0.2, 0.5, 1.0, 1), emit=4.0)
    msign_w = mat("Sign_White", (0.95, 0.95, 0.95, 1), rough=0.7)
    mroad = get_mat('asphalt', make_asphalt)

    dw = 3.5; dd = 2.0; dh = 1.8

    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (dw, dd, dh)
    o.location = pos + Vector((0, 0, dh))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mwall); objs.append(o)

    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (dw + 0.3, 0.12, 0.25)
    o.location = pos + Vector((0, dd + 0.05, dh*2 - 0.1))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mtrim); objs.append(o)

    for cx in range(8):
        ci = cx / 8.0 - 0.5
        is_black = (cx % 2 == 0)
        cm = mchecker if is_black else mchecker_w
        objs.append(cube(pos + Vector((ci * dw * 1.8, dd + 0.05, dh*2 - 0.25)),
                         (dw*0.22, 0.02, 0.04), cm))

    objs.append(cube(pos + Vector((0, 0, dh*2)), (dw+0.2, dd+0.2, 0.06), mroof))

    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (dw*0.75, 0.03, dh*0.65)
    o.location = pos + Vector((0, dd+0.02, dh*0.7))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mglass); objs.append(o)

    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (dw*0.77, 0.02, dh*0.67)
    o.location = pos + Vector((0, dd+0.025, dh*0.7))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mchrome); objs.append(o)

    objs.append(cube(pos + Vector((-dw*0.55, dd+0.02, dh*0.4)), (0.25, 0.03, dh*0.8), mchrome))
    objs.append(cube(pos + Vector((-dw*0.55, dd+0.04, dh*0.4)), (0.18, 0.02, dh*0.6), mglass))

    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (dw*0.85, 0.04, 0.04)
    o.location = pos + Vector((0, dd+0.01, dh*0.3))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mteal); objs.append(o)

    objs.append(cube(pos + Vector((0, 0, dh*2 + 0.35)), (dw*0.4, 0.08, 0.18), mroof))
    for li, lx in enumerate([-0.4, -0.15, 0.1, 0.35, 0.6]):
        lw = 0.08 if li % 2 == 0 else 0.06
        objs.append(cube(pos + Vector((lx * dw*0.2, 0, dh*2 + 0.45)),
                         (lw, 0.02, 0.08), mneon))
    objs.append(cube(pos + Vector((0, 0.03, dh*2 + 0.5)), (dw*0.35, 0.01, 0.01), mneon))
    objs.append(cube(pos + Vector((0, -0.03, dh*2 + 0.5)), (dw*0.35, 0.01, 0.01), mneon))
    objs.append(cube(pos + Vector((dw*0.35, 0, dh*2 + 0.45)), (0.01, 0.05, 0.1), mneon))
    objs.append(cube(pos + Vector((-dw*0.35, 0, dh*2 + 0.45)), (0.01, 0.05, 0.1), mneon))

    sign_pos = pos + Vector((dw + 1.0, 0, 0))
    objs.append(cyl(sign_pos + Vector((0, 0, 3.0)), 0.04, 6, 5, mchrome))
    bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=0.3, depth=0.03)
    o = bpy.context.active_object
    o.rotation_euler.z = rot + math.radians(45)
    o.location = sign_pos + Vector((0, 0, 4.5))
    apply_obj(o)
    o.data.materials.append(msign_w); objs.append(o)

    objs.append(cyl(sign_pos + Vector((0, 0, 4.5)), 0.2, 0.04, 8, mteal))
    objs.append(cyl(sign_pos + Vector((0, 0, 4.5)), 0.12, 0.05, 8, mneon_blue))
    for bx in [-0.05, 0.05]:
        objs.append(cyl(sign_pos + Vector((bx, 0, 4.5)), 0.03, 0.04, 6, msign_w))

    for pi in range(3):
        px = (pi - 1) * 1.2
        objs.append(cube(pos + Vector((px, -dd - 0.8, 0.01)), (0.5, 0.6, 0.01), mroad))

    table_pos = pos + Vector((dw*0.3, -dd - 0.6, 0))
    objs.append(cyl(table_pos + Vector((0, 0, 0.35)), 0.15, 0.02, 6, mchrome))
    objs.append(cyl(table_pos + Vector((0, 0, 0.36)), 0.02, 0.35, 5, mchrome))
    objs.append(cyl(table_pos + Vector((0, 0, 0.36)), 0.01, 0.8, 5, mchrome))
    objs.append(cone(table_pos + Vector((0, 0, 1.2)), 0.35, 0.4, 6, mtrim))

    for ci in [-0.3, 0.3]:
        chair_pos = Vector((table_pos.x + ci, table_pos.y + 0.25, 0))
        objs.append(cube(chair_pos + Vector((0, 0, 0.22)), (0.08, 0.08, 0.22), mchrome))
        objs.append(cube(chair_pos + Vector((0, 0, 0.42)), (0.12, 0.08, 0.02), mtrim))

    for ci in range(2):
        px = (ci - 0.5) * 1.5
        car_pos = pos + Vector((px, -dd - 2.2, 0))
        objs.extend(create_car(car_pos, rot + random.uniform(-0.1, 0.1)))

    cactus_pos = pos + Vector((-dw*0.8, dd + 0.3, 0))
    mc = get_mat('cactus', make_cactus_skin)
    objs.append(cyl(cactus_pos + Vector((0, 0, 0.4)), 0.04, 0.8, 5, mc))

    return objs


# ============================================================
# DESERT PROPS
# ============================================================
def make_oil_barrel(pos, rot=0.0):
    """Create an oil barrel."""
    objs = []
    mm = mat("Barrel_Metal", (0.35, 0.2, 0.05, 1), rough=0.6, metal=0.7)
    mring = mat("Barrel_Ring", (0.15, 0.15, 0.15, 1), rough=0.5, metal=0.8)

    objs.append(cyl(pos + Vector((0, 0, 0.45)), 0.2, 0.9, 8, mm))
    for zh in [0.1, 0.5, 0.8]:
        objs.append(cyl(pos + Vector((0, 0, zh)), 0.21, 0.03, 8, mring))
    return objs


def make_road_barrier(pos, rot=0.0):
    """Create a red/white desert road barrier (low adobe wall)."""
    objs = []
    mw = mat("Barrier_White", (0.9, 0.9, 0.85, 1), rough=0.8)
    mr = mat("Barrier_Red", (0.7, 0.15, 0.05, 1), rough=0.8)

    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (0.4, 0.12, 0.2)
    o.location = pos + Vector((0, 0, 0.25))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mw); objs.append(o)

    for x_off in [-0.2, 0, 0.2]:
        objs.append(cube(pos + Vector((x_off, 0, 0.25)), (0.06, 0.13, 0.2), mr))
    return objs


# ============================================================
# CAMPFIRE
# ============================================================
def make_campfire(pos):
    """Create a small campfire site — fire ring, logs, and embers."""
    objs = []
    m_stone = get_mat('red_rock', make_red_rock)
    m_log = get_mat('wood', make_wood)
    m_fire = mat("Campfire_Ember", (0.9, 0.3, 0.05, 1), emit=4.0)
    m_glow = mat("Campfire_Glow", (1.0, 0.6, 0.1, 1), emit=2.0)

    for i in range(6):
        ang = (i / 6) * math.pi * 2
        rx = math.cos(ang) * 0.25
        ry = math.sin(ang) * 0.25
        rsize = random.uniform(0.06, 0.1)
        objs.append(cube(pos + Vector((rx, ry, rsize * 0.5)), (rsize, rsize, rsize), m_stone))

    for ang in [0, math.pi / 3, -math.pi / 3]:
        lx = math.cos(ang) * 0.12
        ly = math.sin(ang) * 0.12
        bpy.ops.mesh.primitive_cylinder_add(vertices=5, radius=0.02, depth=0.3)
        o = bpy.context.active_object
        o.location = pos + Vector((lx, ly, 0.04))
        o.rotation_euler.x = math.radians(80)
        o.rotation_euler.z = ang
        apply_obj(o)
        o.data.materials.append(m_log); objs.append(o)

    objs.append(cone(pos + Vector((0, 0, 0.06)), 0.08, 0.15, 5, m_fire))
    objs.append(cone(pos + Vector((0, 0, 0.16)), 0.05, 0.12, 5, m_glow))
    return objs


# ============================================================
# OFF-ROAD DRIVING COURSE
# ============================================================
def make_off_road_course(pos):
    """Create a small off-road driving course at the end of a dirt path."""
    objs = []
    m_dirt = get_mat('dirt', make_dirt)
    m_cone_orange = mat("Course_Cone_O", (0.95, 0.4, 0.05, 1), rough=0.7)
    m_barrier = mat("Course_Barrier", (0.7, 0.15, 0.05, 1), rough=0.8)
    m_jump = mat("Course_Jump", (0.5, 0.35, 0.2, 1), rough=1.0)

    track_a = 6.0; track_b = 4.0; track_w = 1.2; n_track_pts = 32

    track_pts = []
    for i in range(n_track_pts):
        t = (i / n_track_pts) * math.pi * 2
        tx = pos.x + track_a * math.cos(t)
        ty = pos.y + track_b * math.sin(t)
        track_pts.append(Vector((tx, ty, 0.01)))

    mesh = bpy.data.meshes.new("OffRoadTrack")
    bm = bmesh.new(); rows = []
    for i, p in enumerate(track_pts):
        if i < n_track_pts - 1:
            fwd = (track_pts[i + 1] - track_pts[i]).normalized()
        else:
            fwd = (track_pts[0] - track_pts[i]).normalized()
        up = Vector((0, 0, 1)); r = fwd.cross(up).normalized()
        if r.length < 0.01: r = Vector((1, 0, 0))
        to_center = pos - p; to_center.z = 0
        if to_center.length > 0.01: inward_dir = to_center.normalized()
        else: inward_dir = -r
        rows.append((bm.verts.new(p + inward_dir * track_w),
                     bm.verts.new(p - inward_dir * track_w * 1.2)))
    bm.verts.ensure_lookup_table()
    for i in range(len(rows) - 1):
        bm.faces.new([rows[i][0], rows[i + 1][0], rows[i + 1][1], rows[i][1]])
    bm.faces.new([rows[-1][0], rows[0][0], rows[0][1], rows[-1][1]])
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new("OffRoadTrack", mesh)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(m_dirt); objs.append(o)

    for ang in [math.pi * 0.3, math.pi * 1.7]:
        jx = pos.x + track_a * 0.6 * math.cos(ang)
        jy = pos.y + track_b * 0.6 * math.sin(ang)
        ramp_pos = Vector((jx, jy, 0))
        bpy.ops.mesh.primitive_cube_add(size=2)
        ramp = bpy.context.active_object
        ramp.scale = (0.6, 0.4, 0.15)
        ramp.location = ramp_pos + Vector((0, 0, 0.15))
        ramp_dir_angle = ang + math.pi / 2
        ramp.rotation_euler.z = ramp_dir_angle; apply_obj(ramp)
        ramp.data.materials.append(m_jump); objs.append(ramp)

        bpy.ops.mesh.primitive_cube_add(size=2)
        ramp_top = bpy.context.active_object
        ramp_top.scale = (0.4, 0.25, 0.04)
        ramp_top.location = ramp_pos + Vector((0, 0, 0.3))
        ramp_top.rotation_euler.z = ramp_dir_angle; apply_obj(ramp_top)
        ramp_top.data.materials.append(m_jump); objs.append(ramp_top)

    slalom_start_angle = math.pi * 0.8
    slalom_end_angle = math.pi * 1.6
    for step_i in range(5):
        t = slalom_start_angle + (slalom_end_angle - slalom_start_angle) * (step_i / 4)
        sx = pos.x + track_a * 0.85 * math.cos(t)
        sy = pos.y + track_b * 0.85 * math.sin(t)
        cone_pos = Vector((sx, sy, 0))
        offset_dir = 1 if step_i % 2 == 0 else -1
        cone_pos += Vector((offset_dir * 0.3, 0, 0))
        objs.append(cone(cone_pos + Vector((0, 0, 0.35)), 0.08, 0.3, 5, m_cone_orange))
        objs.append(cube(cone_pos + Vector((0, 0, 0.02)), (0.12, 0.12, 0.02), m_cone_orange))

    for step_i in range(8):
        t = (step_i / 8) * math.pi * 2
        for side_scale in [0.5, 1.5]:
            bx = pos.x + track_a * side_scale * math.cos(t)
            by = pos.y + track_b * side_scale * math.sin(t)
            b_pos = Vector((bx, by, 0))
            objs.append(cube(b_pos + Vector((0, 0, 0.12)), (0.15, 0.15, 0.12), m_barrier))

    entry_angle = math.pi * 2.3
    ex = pos.x + track_a * 1.8 * math.cos(entry_angle)
    ey = pos.y + track_b * 1.8 * math.sin(entry_angle)
    stage_pos = Vector((ex, ey, 0.01))
    objs.append(cube(stage_pos, (1.5, 1.0, 0.01), m_dirt))

    return objs


# ============================================================
# DESERT SCENERY PLACEMENT
# ============================================================
def place_desert_scenery(pts):
    """Place cacti, mesas, dry trees, tumbleweeds, gas station, and diner.
    
    With narrow terrain (TERRAIN_WIDTH=8), objects stay close to the road
    for a tight, game-focused Traffic Racer camera view.
    """
    objs = []

    for side in [-1, 1]:
        for _ in range(10):
            i = random.randint(5, len(pts)-6)
            p = pts[i]
            _, right, _ = get_road_frame(pts, i)
            dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(2, TERRAIN_WIDTH - 1)
            pos = p + right * side * dist; pos.z = 0
            objs.extend(make_saguaro(pos, random.uniform(0.6, 1.0)))

    for side in [-1, 1]:
        for _ in range(5):
            i = random.randint(5, len(pts)-6)
            p = pts[i]
            _, right, _ = get_road_frame(pts, i)
            dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(1, TERRAIN_WIDTH - 1)
            pos = p + right * side * dist; pos.z = 0
            objs.extend(make_prickly_pear(pos, random.uniform(0.6, 1.0)))

    sp = len(pts) // 8
    for side in [-1, 1]:
        for mi in range(3):
            i = mi * sp + random.randint(0, max(1, sp//3))
            if i >= len(pts): continue
            p = pts[i]
            _, right, _ = get_road_frame(pts, i)
            dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(2, TERRAIN_WIDTH - 2)
            pos = p + right * side * dist; pos.z = 0
            w = random.uniform(1.5, 3.0); d = random.uniform(1.5, 3.0); h = random.uniform(1.0, 2.5)
            objs.extend(make_mesa(pos, w, d, h, random.uniform(0.6, 1.2)))

    for side in [-1, 1]:
        for _ in range(4):
            i = random.randint(5, len(pts)-6)
            p = pts[i]
            _, right, _ = get_road_frame(pts, i)
            dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(1, TERRAIN_WIDTH - 2)
            pos = p + right * side * dist; pos.z = 0
            objs.extend(make_dry_tree(pos, random.uniform(0.6, 1.0)))

    for _ in range(8):
        i = random.randint(5, len(pts)-6)
        p = pts[i]
        _, right, _ = get_road_frame(pts, i)
        side = random.choice([-1, 1])
        dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(1, TERRAIN_WIDTH - 1)
        pos = p + right * side * dist; pos.z = 0
        objs.extend(make_tumbleweed(pos, random.uniform(0.4, 0.8)))

    gas_i = len(pts) // 4
    if gas_i < len(pts):
        p = pts[gas_i]; _, right, _ = get_road_frame(pts, gas_i)
        side = 1
        dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(2, 4)
        pos = p + right * side * dist; pos.z = 0
        rot = math.atan2(right.x, right.y)
        objs.extend(make_gas_station(pos, rot))

    diner_i = len(pts) * 3 // 4
    if diner_i < len(pts):
        p = pts[diner_i]; _, right, _ = get_road_frame(pts, diner_i)
        side = -1
        dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(2, 4)
        pos = p + right * side * dist; pos.z = 0
        rot = math.atan2(right.x, right.y) + math.pi
        objs.extend(make_route66_diner(pos, rot))

    return objs


# ============================================================
# DESERT PROPS PLACEMENT
# ============================================================
def place_desert_props(pts):
    """Place oil barrels and road barriers along the road."""
    objs = []

    for _ in range(6):
        i = random.randint(10, len(pts)-10)
        p = pts[i]
        _, right, _ = get_road_frame(pts, i)
        side = random.choice([-1, 1])
        dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(1, 3)
        pos = p + right * side * dist; pos.z = 0
        rot = math.atan2(right.x, right.y) + random.uniform(-0.2, 0.2)
        objs.extend(make_oil_barrel(pos, rot))

    for _ in range(4):
        i = random.randint(10, len(pts)-10)
        p = pts[i]
        _, right, _ = get_road_frame(pts, i)
        side = random.choice([-1, 1])
        dist = ROAD_WIDTH/2 + random.uniform(0.5, 1.5)
        pos = p + right * side * dist; pos.z = 0
        rot = math.atan2(right.x, right.y)
        objs.extend(make_road_barrier(pos, rot))

    return objs


# ============================================================
# DIRT PATH PLACEMENT (off-road)
# ============================================================
def place_desert_dirt_paths(pts):
    """Place 2-3 dirt paths branching from the main road into the desert."""
    objs = []

    branch_1 = int(len(pts) * 0.15)
    _, end1 = create_dirt_path(pts, branch_1, side=1, path_len=25, path_width=1.0)
    objs.extend(make_campfire(end1))
    for _ in range(4):
        ang = random.uniform(0, math.pi * 2)
        dist = random.uniform(0.4, 0.8)
        rp = end1 + Vector((math.cos(ang) * dist, math.sin(ang) * dist, 0))
        rs = random.uniform(0.06, 0.12)
        objs.append(cube(rp + Vector((0, 0, rs * 0.5)), (rs, rs, rs), get_mat('red_rock', make_red_rock)))

    branch_2 = int(len(pts) * 0.45)
    _, end2 = create_dirt_path(pts, branch_2, side=-1, path_len=28, path_width=0.9)
    objs.extend(make_off_road_course(end2))

    branch_3 = int(len(pts) * 0.75)
    _, end3 = create_dirt_path(pts, branch_3, side=1, path_len=18, path_width=0.8)
    for bi in range(2):
        b_pos = end3 + Vector(((bi - 0.5) * 0.6, 0.3, 0))
        objs.extend(make_oil_barrel(b_pos, random.uniform(0, math.pi)))

    return objs


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 50)
    print("Generating Desert Racing Environment with Textures...")
    print("=" * 50)
    _mat_cache.clear()
    clear_scene()

    pts = get_desert_road_points(120)

    print("[1/13] Road surface..."); create_road_mesh(pts)
    print("[2/13] Lane markings..."); create_curved_markings(pts, LANE_COUNT)
    print("[3/13] Sidewalks...")
    for s in [-1, 1]: create_sidewalk_side(pts, s)
    print("[4/13] Road curbs..."); create_road_curbs(pts)
    print("[5/13] Ground plane..."); create_ground_plane()
    print("[6/13] Sand terrain...")
    for s in [-1, 1]: create_terrain_side(pts, s)
    print("[7/13] Bridge..."); make_desert_bridge(pts)
    print("[8/13] Overpass..."); create_desert_overpass(pts)
    print("[9/13] Desert signs..."); make_desert_signs(pts)
    print("[10/13] Desert scenery (cacti, mesas, trees, gas station)...")
    place_desert_scenery(pts)
    print("[11/13] Props (barrels, barriers)..."); place_desert_props(pts)
    print("[12/13] Dirt paths (off-road)..."); place_desert_dirt_paths(pts)
    print("[13/13] Joining & scene setup...")
    result = join_all("DesertRacing_SingleMesh")
    if result:
        v = len(result.data.vertices); f = len(result.data.polygons)
        m = len(result.data.materials)
        print(f"Verts: {v} | Faces: {f} | Mats: {m}")
    setup_scene(camera_loc=(18, -25, 12), sun_color=(1.0, 0.85, 0.65))
    print("DONE! Export: File > Export > FBX/glTF")

main()
