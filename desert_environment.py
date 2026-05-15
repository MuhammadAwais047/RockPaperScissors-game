"""
Desert Racing Environment - Single Mesh for Blender
====================================================
Run inside Blender Scripting tab.
Imports shared functionality from base_environment.py.

Desert theme: sand terrain, saguaro cacti, gas station, mesa rocks,
adobe-styled bridge & overpass, tumbleweeds, oil barrels.
"""

import sys, os, bpy

# Determine directory containing this script
# Handles __file__ (direct execution), bpy context (Text Editor), and fallbacks
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = None
    try:
        filepath = bpy.context.space_data.text.filepath
        if filepath:
            SCRIPT_DIR = os.path.dirname(os.path.abspath(filepath))
    except (AttributeError, TypeError):
        pass
    if not SCRIPT_DIR:
        SCRIPT_DIR = os.getcwd()

if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from base_environment import *

import math, random
from mathutils import Vector

# ============================================================
# CONFIGURATION (overrides base defaults)
# ============================================================
ROAD_LENGTH = 250
ROAD_WIDTH = 10
LANE_COUNT = 2
TERRAIN_WIDTH = 8
SIDEWALK_WIDTH = 2
DECIMATE_RATIO = 0.6
SEED = 42
random.seed(SEED)


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
mt_dry_bush = make_dry_bush


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
# ROAD PATH (flat desert S-curves, no bridge/tunnel)
# ============================================================
def get_road_points(count=120):
    """Generate road center points with gentle desert S-curves, flat terrain."""
    pts = []
    for i in range(count):
        t = i / (count - 1)
        y = -ROAD_LENGTH/2 + ROAD_LENGTH * t
        x = 10 * math.sin(t * math.pi * 2) * (0.3 + 0.7 * math.sin(t * math.pi))
        z = 0  # Flat desert
        pts.append(Vector((x, y, z)))
    return pts


# Override the base version
road_pts = get_road_points


# ============================================================
# DESERT DECORATIVE ELEMENTS
# ============================================================

def make_saguaro(pos, sc=1.0):
    """Create a saguaro cactus with branching arms."""
    objs = []
    mc = get_mat('cactus', make_cactus_skin)

    h = random.uniform(3.0, 5.5) * sc
    r = 0.12 * sc

    # Main trunk
    objs.append(cyl(pos + Vector((0, 0, h/2)), r, h, 5, mc))

    # Arms (0-3 branches)
    arm_count = random.randint(0, 3)
    arm_angles = [i * 2.4 + random.uniform(0, 0.8) for i in range(arm_count)]
    for ang in arm_angles:
        arm_h = random.uniform(0.8, 2.0) * sc
        arm_base_h = random.uniform(h * 0.3, h * 0.65)
        dx = math.cos(ang) * r * 1.2
        dy = math.sin(ang) * r * 1.2

        # Horizontal arm segment (rotated cylinder)
        arm_len = random.uniform(0.4, 0.9) * sc
        bpy.ops.mesh.primitive_cylinder_add(vertices=5, radius=r * 0.7, depth=arm_len)
        arm_seg = bpy.context.active_object
        arm_seg.location = pos + Vector((dx, dy, arm_base_h))
        arm_seg.rotation_euler.x = math.radians(90)
        arm_seg.rotation_euler.z = ang
        apply_obj(arm_seg)
        arm_seg.data.materials.append(mc)
        objs.append(arm_seg)

        # Vertical arm segment (upright cylinder at arm end)
        arm_angle_2 = ang + random.uniform(-0.3, 0.3)
        arm_end_x = dx + math.cos(arm_angle_2) * r * 0.7
        arm_end_y = dy + math.sin(arm_angle_2) * r * 0.7
        objs.append(cyl(pos + Vector((arm_end_x, arm_end_y, arm_base_h + arm_h/2)), r * 0.7, arm_h, 5, mc))

    return objs


def make_prickly_pear(pos, sc=1.0):
    """Create a prickly pear cactus cluster."""
    objs = []
    mp = mat("PricklyPear", (0.12, 0.4, 0.1, 1), rough=0.85)

    # Cluster of oval pads
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

    # Main body (trapezoid shape using cone + cube)
    taper = 0.6
    objs.append(cube(pos + Vector((0, 0, h/2)), (w/2, d/2, h/2), mr))

    # Tapered base
    objs.append(cone(pos + Vector((0, 0, h * 0.3)), w * taper, h * 0.6, 6, mr))

    # Flat cap
    objs.append(cube(pos + Vector((0, 0, h)), (w/2 + 0.2, d/2 + 0.2, 0.1), mr))

    return objs


def make_dry_tree(pos, sc=1.0):
    """Create a dead desert tree with twisted branches."""
    objs = []
    mb = get_mat('bark', make_bark_tex)

    h = random.uniform(1.5, 3.0) * sc
    # Trunk
    objs.append(cyl(pos + Vector((0, 0, h/2)), 0.06*sc, h, 5, mb))

    # Sparse branches
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
    """Create a gas station with building, canopy, and pumps.

    Args:
        pos: Vector - center position
        rot: float - rotation around Z axis
    Returns:
        list of objects
    """
    objs = []
    madobe = get_mat('adobe', make_adobe)
    mroof = get_mat('red_rock', make_red_rock)
    mmetal = get_mat('metal', make_metal_tex)
    mglass = mat("Gas_Glass", (0.6, 0.75, 0.85, 1), rough=0.1, metal=0.2)
    mwhite = mat("Gas_White", (0.9, 0.9, 0.9, 1), rough=0.7)
    mred = mat("Gas_Red", (0.8, 0.1, 0.05, 1), rough=0.6)
    msign = mat("Gas_Sign", (0.9, 0.7, 0.1, 1), emit=2.0)

    bw = 3.0  # building half-width
    bd = 2.0  # building half-depth
    bh = 2.0  # building half-height

    # Main building
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (bw, bd, bh)
    o.location = pos + Vector((0, 0, bh))
    o.rotation_euler.z = rot
    apply_obj(o)
    o.data.materials.append(madobe)
    objs.append(o)

    # Roof
    objs.append(cube(pos + Vector((0, 0, bh*2)), (bw+0.2, bd+0.2, 0.1), mroof))

    # Storefront window
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (bw*0.7, 0.03, bh*0.6)
    o.location = pos + Vector((0, bd+0.02, bh*0.7))
    o.rotation_euler.z = rot
    apply_obj(o)
    o.data.materials.append(mglass)
    objs.append(o)

    # Door
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (0.3, 0.03, bh*0.8)
    o.location = pos + Vector((-bw*0.4, bd+0.02, bh*0.8))
    o.rotation_euler.z = rot
    apply_obj(o)
    o.data.materials.append(mwhite)
    objs.append(o)

    # Canopy (4 poles + flat roof)
    canopy_w = bw + 2.0
    canopy_d = bd + 3.0
    canopy_h = bh * 2 + 1.5

    for px in [-canopy_w/2 + 0.3, canopy_w/2 - 0.3]:
        for py in [-canopy_d/2 + 0.3, canopy_d/2 - 0.3]:
            pole_pos = pos + Vector((px, py, 0))
            objs.append(cyl(pole_pos + Vector((0, 0, canopy_h/2)), 0.06, canopy_h, 5, mmetal))

    # Canopy roof
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (canopy_w/2, canopy_d/2, 0.05)
    o.location = pos + Vector((0, 0, canopy_h))
    o.rotation_euler.z = rot
    apply_obj(o)
    o.data.materials.append(mwhite)
    objs.append(o)

    # Canopy red stripe
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (canopy_w/2 + 0.01, 0.06, 0.04)
    o.location = pos + Vector((0, 0, canopy_h + 0.06))
    o.rotation_euler.z = rot
    apply_obj(o)
    o.data.materials.append(mred)
    objs.append(o)

    # Gas pumps (2-3)
    pump_count = 2
    for pi in range(pump_count):
        px = (pi - (pump_count-1)/2) * 1.5
        pump_pos = pos + Vector((px, -canopy_d/2 + 0.8, 0))
        # Pump body
        objs.append(cube(pump_pos + Vector((0, 0, 0.5)), (0.25, 0.15, 0.5), mwhite))
        # Pump top
        objs.append(cube(pump_pos + Vector((0, 0, 0.9)), (0.15, 0.1, 0.05), msign))
        objs.append(cyl(pump_pos + Vector((0, 0, 0.95)), 0.02, 0.05, 5, mmetal))

    # Gas station sign (tall pole)
    sign_pos = pos + Vector((0, -canopy_d/2 - 2, 0))
    objs.append(cyl(sign_pos + Vector((0, 0, 5)), 0.04, 10, 5, mmetal))
    objs.append(cube(sign_pos + Vector((0, 0, 10)), (0.6, 0.08, 0.15), msign))
    objs.append(cube(sign_pos + Vector((0, 0, 9.7)), (1.0, 0.05, 0.05), mwhite))

    return objs


# ============================================================
# DESERT-STYLED HIGHWAY OVERPASS (Adobe/Mission)
# ============================================================
def create_overpass(pts):
    """Add a desert-themed highway overpass with adobe arches and tile roof details."""
    objs = []
    m_asphalt = get_mat('asphalt', make_asphalt)
    m_sand = get_mat('sand', make_sand)
    m_adobe = get_mat('adobe', make_adobe)
    m_red_rock = get_mat('red_rock', make_red_rock)
    m_wood = get_mat('wood', make_wood)

    idx = int(0.22 * len(pts))
    p = pts[idx]
    fwd, right, up = get_road_frame(pts, idx)
    angle = math.atan2(right.x, right.y)

    OH = 6.0; OW = ROAD_WIDTH + 8; DT = 0.35

    # 4 Adobe support pillars (square, tapered)
    for side_x in [-1, 1]:
        for side_z in [-1, 1]:
            pos = p + right * side_x * (ROAD_WIDTH/2 + 1.8) + fwd * side_z * 2
            objs.append(cube(pos + Vector((0, 0, OH/2)), (0.35, 0.35, OH/2), m_adobe))
            objs.append(cube(pos + Vector((0, 0, 0.15)), (0.6, 0.6, 0.15), m_red_rock))
            objs.append(cube(pos + Vector((0, 0, OH - 0.1)), (0.55, 0.55, 0.1), m_red_rock))

    # Decorative arch between pillars (along fwd direction)
    for side_x in [-1, 1]:
        for sz in [-1, 1]:
            ap1 = p + right * side_x * (ROAD_WIDTH/2 + 1.8) + fwd * sz * 2
            arch_top = (ap1 + p + fwd * sz * 2) / 2 + Vector((0, 0, OH * 0.6))
            objs.append(cube(arch_top, (0.2, 0.2, 0.15), m_adobe))

    # Main deck
    bpy.ops.mesh.primitive_cube_add(size=2)
    deck = bpy.context.active_object
    deck.scale = (OW/2, 0.35, DT/2)
    deck.location = Vector((p.x, p.y, OH + DT/2))
    deck.rotation_euler.z = -angle; apply_obj(deck)
    deck.data.materials.append(m_asphalt); objs.append(deck)

    # Cross beams (adobe)
    for fwd_off in [-2.0, 0, 2.0]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        o = bpy.context.active_object
        o.scale = (OW/2 - 1.5, 0.12, 0.15)
        bp = p + fwd * fwd_off; bp.z = OH - 0.05
        o.location = bp; o.rotation_euler.z = -angle; apply_obj(o)
        o.data.materials.append(m_adobe); objs.append(o)

    # Guard railings (wood/adobe)
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

    # Tile barriers
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        o = bpy.context.active_object
        o.scale = (OW/2 - 0.3, 0.08, 0.15)
        bp = p + right * side * (OW/2 - 0.15)
        bp.z = OH + DT + 0.15
        o.location = bp; o.rotation_euler.z = -angle; apply_obj(o)
        o.data.materials.append(m_red_rock); objs.append(o)

    # Approach ramps
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
# DESERT-STYLED BRIDGE (Adobe arch bridge)
# ============================================================
def make_bridge_supports(pts):
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
                # Decorative arch detail
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

        # Pole
        objs.append(cyl(pos + Vector((0, 0, 1.5)), 0.04, 3, 5, m_pole))

        if idx % 3 == 0:
            # Large highway sign
            objs.append(cube(pos + Vector((0, 0, 3.0)), (0.5, 0.03, 0.3), m_sign_green))
            if idx % 6 == 0:
                objs.append(cube(pos + Vector((0, 0, 2.5)), (0.35, 0.02, 0.05), m_white))
        elif idx % 3 == 1:
            # Diamond warning sign
            bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius1=0.25, depth=0.03)
            o = bpy.context.active_object
            o.rotation_euler.z = math.radians(45)
            o.location = pos + Vector((0, 0, 3.0))
            apply_obj(o)
            o.data.materials.append(m_sign_warn)
            objs.append(o)
        else:
            # Rectangular info sign
            objs.append(cube(pos + Vector((0, 0, 3.0)), (0.35, 0.03, 0.25), m_sign_brown))

    return objs


# ============================================================
# ROUTE 66 DINER
# ============================================================
def make_route66_diner(pos, rot=0.0):
    """Create a classic Route 66 roadside diner with neon sign and parking.

    Features: white/pink building, checkerboard trim, large window,
    neon DINER roof sign, Route 66 shield on pole, outdoor tables, parking.
    """
    objs = []
    mwall = mat("Diner_Wall", (0.92, 0.88, 0.82, 1), rough=0.85)
    mtrim = mat("Diner_Trim", (0.75, 0.15, 0.25, 1), rough=0.6)  # Pink/red
    mteal = mat("Diner_Teal", (0.1, 0.55, 0.55, 1), rough=0.6)  # Teal accent
    mroof = mat("Diner_Roof", (0.08, 0.08, 0.12, 1), rough=0.9)
    mglass = mat("Diner_Glass", (0.55, 0.7, 0.85, 1), rough=0.1, metal=0.15)
    mchrome = mat("Diner_Chrome", (0.8, 0.8, 0.85, 1), rough=0.2, metal=0.9)
    mchecker = mat("Diner_Checker", (0.05, 0.05, 0.05, 1), rough=0.7)
    mchecker_w = mat("Diner_Checker_W", (0.95, 0.95, 0.9, 1), rough=0.7)
    mneon = mat("Diner_Neon", (0.9, 0.1, 0.3, 1), emit=6.0)
    mneon_blue = mat("Diner_Neon_B", (0.2, 0.5, 1.0, 1), emit=4.0)
    msign_w = mat("Sign_White", (0.95, 0.95, 0.95, 1), rough=0.7)
    mroad = get_mat('asphalt', make_asphalt)

    dw = 3.5   # building half-width
    dd = 2.0   # building half-depth
    dh = 1.8   # building half-height

    # --- Main building body ---
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (dw, dd, dh)
    o.location = pos + Vector((0, 0, dh))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mwall); objs.append(o)

    # --- Roof cap (angled facade front) ---
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (dw + 0.3, 0.12, 0.25)
    o.location = pos + Vector((0, dd + 0.05, dh*2 - 0.1))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mtrim); objs.append(o)

    # Checkerboard stripe along roof edge
    for cx in range(8):
        ci = cx / 8.0 - 0.5
        is_black = (cx % 2 == 0)
        cm = mchecker if is_black else mchecker_w
        objs.append(cube(pos + Vector((ci * dw * 1.8, dd + 0.05, dh*2 - 0.25)),
                         (dw*0.22, 0.02, 0.04), cm))

    # --- Flat roof ---
    objs.append(cube(pos + Vector((0, 0, dh*2)), (dw+0.2, dd+0.2, 0.06), mroof))

    # --- Large front window ---
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (dw*0.75, 0.03, dh*0.65)
    o.location = pos + Vector((0, dd+0.02, dh*0.7))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mglass); objs.append(o)

    # Window chrome frame
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (dw*0.77, 0.02, dh*0.67)
    o.location = pos + Vector((0, dd+0.025, dh*0.7))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mchrome); objs.append(o)

    # --- Door ---
    objs.append(cube(pos + Vector((-dw*0.55, dd+0.02, dh*0.4)), (0.25, 0.03, dh*0.8), mchrome))
    objs.append(cube(pos + Vector((-dw*0.55, dd+0.04, dh*0.4)), (0.18, 0.02, dh*0.6), mglass))

    # --- Teal accent stripe along the side ---
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (dw*0.85, 0.04, 0.04)
    o.location = pos + Vector((0, dd+0.01, dh*0.3))
    o.rotation_euler.z = rot; apply_obj(o)
    o.data.materials.append(mteal); objs.append(o)

    # --- Neon DINER sign on roof ---
    # Sign backplate
    objs.append(cube(pos + Vector((0, 0, dh*2 + 0.35)), (dw*0.4, 0.08, 0.18), mroof))
    # Neon letters (glowing bars)
    for li, lx in enumerate([-0.4, -0.15, 0.1, 0.35, 0.6]):
        lw = 0.08 if li % 2 == 0 else 0.06
        objs.append(cube(pos + Vector((lx * dw*0.2, 0, dh*2 + 0.45)),
                         (lw, 0.02, 0.08), mneon))
    # Neon glow border
    objs.append(cube(pos + Vector((0, 0.03, dh*2 + 0.5)), (dw*0.35, 0.01, 0.01), mneon))
    objs.append(cube(pos + Vector((0, -0.03, dh*2 + 0.5)), (dw*0.35, 0.01, 0.01), mneon))
    objs.append(cube(pos + Vector((dw*0.35, 0, dh*2 + 0.45)), (0.01, 0.05, 0.1), mneon))
    objs.append(cube(pos + Vector((-dw*0.35, 0, dh*2 + 0.45)), (0.01, 0.05, 0.1), mneon))

    # --- Route 66 shield sign on pole ---
    sign_pos = pos + Vector((dw + 1.0, 0, 0))
    # Pole
    objs.append(cyl(sign_pos + Vector((0, 0, 3.0)), 0.04, 6, 5, mchrome))
    # Shield shape (diamond-ish, using 4-sided cylinder rotated 45 degrees)
    bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius1=0.3, depth=0.03)
    o = bpy.context.active_object
    o.rotation_euler.z = rot + math.radians(45)
    o.location = sign_pos + Vector((0, 0, 4.5))
    apply_obj(o)
    o.data.materials.append(msign_w); objs.append(o)

    # Shield circle overlay
    objs.append(cyl(sign_pos + Vector((0, 0, 4.5)), 0.2, 0.04, 8, mteal))
    objs.append(cyl(sign_pos + Vector((0, 0, 4.5)), 0.12, 0.05, 8, mneon_blue))
    # "66" text (two small circles as simplified numerals)
    for bx in [-0.05, 0.05]:
        objs.append(cyl(sign_pos + Vector((bx, 0, 4.5)), 0.03, 0.04, 6, msign_w))

    # --- Parking spots (asphalt pads) ---
    for pi in range(3):
        px = (pi - 1) * 1.2
        objs.append(cube(pos + Vector((px, -dd - 0.8, 0.01)), (0.5, 0.6, 0.01), mroad))

    # --- Outdoor table with umbrella ---
    table_pos = pos + Vector((dw*0.3, -dd - 0.6, 0))
    # Table
    objs.append(cyl(table_pos + Vector((0, 0, 0.35)), 0.15, 0.02, 6, mchrome))
    objs.append(cyl(table_pos + Vector((0, 0, 0.36)), 0.02, 0.35, 5, mchrome))
    # Umbrella
    objs.append(cyl(table_pos + Vector((0, 0, 0.36)), 0.01, 0.8, 5, mchrome))
    objs.append(cone(table_pos + Vector((0, 0, 1.2)), 0.35, 0.4, 6, mtrim))

    # --- 2 chairs ---
    for ci in [-0.3, 0.3]:
        chair_pos = Vector((table_pos.x + ci, table_pos.y + 0.25, 0))
        objs.append(cube(chair_pos + Vector((0, 0, 0.22)), (0.08, 0.08, 0.22), mchrome))
        objs.append(cube(chair_pos + Vector((0, 0, 0.42)), (0.12, 0.08, 0.02), mtrim))

    # --- 1-2 parked cars using base create_car ---
    for ci in range(2):
        px = (ci - 0.5) * 1.5
        car_pos = pos + Vector((px, -dd - 2.2, 0))
        objs.extend(create_car(car_pos, rot + random.uniform(-0.1, 0.1)))

    # --- Small cactus decoration by door ---
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
    # Rings
    for zh in [0.1, 0.5, 0.8]:
        objs.append(cyl(pos + Vector((0, 0, zh)), 0.21, 0.03, 8, mring))

    return objs


def make_road_barrier(pos, rot=0.0):
    """Create a red/white desert road barrier (low adobe wall)."""
    objs = []
    mw = mat("Barrier_White", (0.9, 0.9, 0.85, 1), rough=0.8)
    mr = mat("Barrier_Red", (0.7, 0.15, 0.05, 1), rough=0.8)

    # Low barrier wall
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.scale = (0.4, 0.12, 0.2)
    o.location = pos + Vector((0, 0, 0.25))
    o.rotation_euler.z = rot
    apply_obj(o)
    o.data.materials.append(mw)
    objs.append(o)

    # Red stripes
    for x_off in [-0.2, 0, 0.2]:
        objs.append(cube(pos + Vector((x_off, 0, 0.25)), (0.06, 0.13, 0.2), mr))

    return objs


# ============================================================
# DESERT SCENERY PLACEMENT
# ============================================================
def place_desert_scenery(pts):
    """Place cacti, mesas, dry trees, and tumbleweeds along the road.
    
    With narrow terrain (TERRAIN_WIDTH=8), objects stay close to the road
    for a tight, game-focused Traffic Racer camera view.
    """
    objs = []

    # Saguaro cacti (reduced: 10 per side instead of 40)
    for side in [-1, 1]:
        for _ in range(10):
            i = random.randint(5, len(pts)-6)
            p = pts[i]
            _, right, _ = get_road_frame(pts, i)
            dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(2, TERRAIN_WIDTH - 1)
            pos = p + right * side * dist; pos.z = 0
            objs.extend(make_saguaro(pos, random.uniform(0.6, 1.0)))

    # Prickly pear cacti (reduced: 5 per side instead of 20)
    for side in [-1, 1]:
        for _ in range(5):
            i = random.randint(5, len(pts)-6)
            p = pts[i]
            _, right, _ = get_road_frame(pts, i)
            dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(1, TERRAIN_WIDTH - 1)
            pos = p + right * side * dist; pos.z = 0
            objs.extend(make_prickly_pear(pos, random.uniform(0.6, 1.0)))

    # Mesa rock formations (reduced: 3 per side instead of 8, placed closer)
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

    # Dead trees (reduced: 4 per side instead of 15)
    for side in [-1, 1]:
        for _ in range(4):
            i = random.randint(5, len(pts)-6)
            p = pts[i]
            _, right, _ = get_road_frame(pts, i)
            dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(1, TERRAIN_WIDTH - 2)
            pos = p + right * side * dist; pos.z = 0
            objs.extend(make_dry_tree(pos, random.uniform(0.6, 1.0)))

    # Tumbleweeds (reduced: 8 instead of 25)
    for _ in range(8):
        i = random.randint(5, len(pts)-6)
        p = pts[i]
        _, right, _ = get_road_frame(pts, i)
        side = random.choice([-1, 1])
        dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(1, TERRAIN_WIDTH - 1)
        pos = p + right * side * dist; pos.z = 0
        objs.extend(make_tumbleweed(pos, random.uniform(0.4, 0.8)))

    # Gas station (1 along the road, placed closer to road)
    gas_i = len(pts) // 4
    if gas_i < len(pts):
        p = pts[gas_i]; _, right, _ = get_road_frame(pts, gas_i)
        side = 1
        dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(2, 4)
        pos = p + right * side * dist; pos.z = 0
        rot = math.atan2(right.x, right.y)
        objs.extend(make_gas_station(pos, rot))

    # Route 66 diner (opposite side, placed closer to road)
    diner_i = len(pts) * 3 // 4
    if diner_i < len(pts):
        p = pts[diner_i]; _, right, _ = get_road_frame(pts, diner_i)
        side = -1
        dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(2, 4)
        pos = p + right * side * dist; pos.z = 0
        rot = math.atan2(right.x, right.y) + math.pi  # flip 180° to face road since side=-1
        objs.extend(make_route66_diner(pos, rot))

    return objs


# ============================================================
# DESERT PROPS PLACEMENT
# ============================================================
def place_desert_props(pts):
    """Place oil barrels and road barriers along the road."""
    objs = []

    # Oil barrels (reduced: 6 instead of 12)
    for _ in range(6):
        i = random.randint(10, len(pts)-10)
        p = pts[i]
        _, right, _ = get_road_frame(pts, i)
        side = random.choice([-1, 1])
        dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(1, 3)
        pos = p + right * side * dist; pos.z = 0
        rot = math.atan2(right.x, right.y) + random.uniform(-0.2, 0.2)
        objs.extend(make_oil_barrel(pos, rot))

    # Road barriers (reduced: 4 instead of 8)
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
# CAMPFIRE (off-road destination)
# ============================================================
def make_campfire(pos):
    """Create a small campfire site — fire ring, logs, and embers."""
    objs = []
    m_stone = get_mat('red_rock', make_red_rock)
    m_log = get_mat('wood', make_wood)
    m_fire = mat("Campfire_Ember", (0.9, 0.3, 0.05, 1), emit=4.0)
    m_glow = mat("Campfire_Glow", (1.0, 0.6, 0.1, 1), emit=2.0)

    # Fire ring (6 small stones in a circle)
    for i in range(6):
        ang = (i / 6) * math.pi * 2
        rx = math.cos(ang) * 0.25
        ry = math.sin(ang) * 0.25
        rsize = random.uniform(0.06, 0.1)
        objs.append(cube(pos + Vector((rx, ry, rsize * 0.5)), (rsize, rsize, rsize), m_stone))

    # Logs (crossed)
    for ang in [0, math.pi / 3, -math.pi / 3]:
        lx = math.cos(ang) * 0.12
        ly = math.sin(ang) * 0.12
        bpy.ops.mesh.primitive_cylinder_add(vertices=5, radius=0.02, depth=0.3)
        o = bpy.context.active_object
        o.location = pos + Vector((lx, ly, 0.04))
        o.rotation_euler.x = math.radians(80)
        o.rotation_euler.z = ang
        apply_obj(o)
        o.data.materials.append(m_log)
        objs.append(o)

    # Ember glow / fire center
    objs.append(cone(pos + Vector((0, 0, 0.06)), 0.08, 0.15, 5, m_fire))
    objs.append(cone(pos + Vector((0, 0, 0.16)), 0.05, 0.12, 5, m_glow))

    return objs


# ============================================================
# OFF-ROAD DRIVING COURSE
# ============================================================
def make_off_road_course(pos):
    """Create a small off-road driving course at the end of a dirt path.

    Features:
    - Oval dirt track (8x12m loop) with packed dirt surface
    - Two small jump ramps
    - Cone slalom section
    - Barrier markers around the track edges
    - Small staging/parking area
    """
    objs = []
    m_dirt = get_mat('dirt', make_dirt)
    m_cone_orange = mat("Course_Cone_O", (0.95, 0.4, 0.05, 1), rough=0.7)
    m_cone_white = mat("Course_Cone_W", (0.95, 0.95, 0.95, 1), rough=0.7)
    m_barrier = mat("Course_Barrier", (0.7, 0.15, 0.05, 1), rough=0.8)
    m_jump = mat("Course_Jump", (0.5, 0.35, 0.2, 1), rough=1.0)

    # --- Oval dirt track ---
    # Generate track centerline as an oval
    track_a = 6.0  # semi-major axis (X direction)
    track_b = 4.0  # semi-minor axis (Y direction)
    track_w = 1.2  # half-width of the track strip
    n_track_pts = 32  # number of points around the oval

    track_pts = []
    for i in range(n_track_pts):
        t = (i / n_track_pts) * math.pi * 2
        # Parametric oval
        tx = pos.x + track_a * math.cos(t)
        ty = pos.y + track_b * math.sin(t)
        track_pts.append(Vector((tx, ty, 0.01)))

    # Create the oval track strip (double-sided: inner and outer edges)
    # Each point becomes two vertices: inner edge and outer edge
    mesh = bpy.data.meshes.new("OffRoadTrack")
    bm = bmesh.new()
    rows = []
    for i, p in enumerate(track_pts):
        # Determine the local radial direction
        if i < n_track_pts - 1:
            fwd = (track_pts[i + 1] - track_pts[i]).normalized()
        else:
            fwd = (track_pts[0] - track_pts[i]).normalized()
        up = Vector((0, 0, 1))
        r = fwd.cross(up).normalized()
        if r.length < 0.01:
            r = Vector((1, 0, 0))
        # Offset toward center vs outward
        # Use vector from oval center to this point for consistent radial direction
        to_center = pos - p
        to_center.z = 0
        if to_center.length > 0.01:
            inward_dir = to_center.normalized()
        else:
            inward_dir = -r
        rows.append((
            bm.verts.new(p + inward_dir * track_w),   # inner edge
            bm.verts.new(p - inward_dir * track_w * 1.2)  # outer edge (slightly wider)
        ))
    bm.verts.ensure_lookup_table()
    for i in range(len(rows) - 1):
        bm.faces.new([rows[i][0], rows[i + 1][0], rows[i + 1][1], rows[i][1]])
    # Close the loop
    bm.faces.new([rows[-1][0], rows[0][0], rows[0][1], rows[-1][1]])
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new("OffRoadTrack", mesh)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(m_dirt)
    objs.append(o)

    # --- Jump ramps (2 dirt mounds on opposite sides of the track) ---
    for ang in [math.pi * 0.3, math.pi * 1.7]:
        jx = pos.x + track_a * 0.6 * math.cos(ang)
        jy = pos.y + track_b * 0.6 * math.sin(ang)
        ramp_pos = Vector((jx, jy, 0))

        # Ramp base (trapezoidal dirt mound)
        bpy.ops.mesh.primitive_cube_add(size=2)
        ramp = bpy.context.active_object
        ramp.scale = (0.6, 0.4, 0.15)
        ramp.location = ramp_pos + Vector((0, 0, 0.15))
        # Rotate to point along the track direction
        ramp_dir_angle = ang + math.pi / 2
        ramp.rotation_euler.z = ramp_dir_angle
        apply_obj(ramp)
        ramp.data.materials.append(m_jump)
        objs.append(ramp)

        # Ramp top surface (sloped)
        bpy.ops.mesh.primitive_cube_add(size=2)
        ramp_top = bpy.context.active_object
        ramp_top.scale = (0.4, 0.25, 0.04)
        ramp_top.location = ramp_pos + Vector((0, 0, 0.3))
        ramp_top.rotation_euler.z = ramp_dir_angle
        apply_obj(ramp_top)
        ramp_top.data.materials.append(m_jump)
        objs.append(ramp_top)

    # --- Cone slalom section (along one side of the oval) ---
    slalom_start_angle = math.pi * 0.8
    slalom_end_angle = math.pi * 1.6
    for step_i in range(5):
        t = slalom_start_angle + (slalom_end_angle - slalom_start_angle) * (step_i / 4)
        sx = pos.x + track_a * 0.85 * math.cos(t)
        sy = pos.y + track_b * 0.85 * math.sin(t)
        cone_pos = Vector((sx, sy, 0))
        # Alternate sides for slalom zigzag
        offset_dir = 1 if step_i % 2 == 0 else -1
        cone_pos += Vector((offset_dir * 0.3, 0, 0))
        # Cone body
        objs.append(cone(cone_pos + Vector((0, 0, 0.35)), 0.08, 0.3, 5, m_cone_orange))
        objs.append(cube(cone_pos + Vector((0, 0, 0.02)), (0.12, 0.12, 0.02), m_cone_orange))

    # --- Track edge barriers (interior and exterior markers) ---
    for step_i in range(8):
        t = (step_i / 8) * math.pi * 2
        for side_scale in [0.5, 1.5]:  # inner and outer edge markers
            bx = pos.x + track_a * side_scale * math.cos(t)
            by = pos.y + track_b * side_scale * math.sin(t)
            b_pos = Vector((bx, by, 0))
            # Small barrier block
            objs.append(cube(b_pos + Vector((0, 0, 0.12)), (0.15, 0.15, 0.12), m_barrier))

    # --- Staging area (dirt pad connected to the path end) ---
    # Dirty parking area near the entry point of the course
    entry_angle = math.pi * 2.3  # Bottom-right quadrant
    ex = pos.x + track_a * 1.8 * math.cos(entry_angle)
    ey = pos.y + track_b * 1.8 * math.sin(entry_angle)
    stage_pos = Vector((ex, ey, 0.01))
    objs.append(cube(stage_pos, (1.5, 1.0, 0.01), m_dirt))

    return objs


# ============================================================
# DIRT PATH PLACEMENT (off-road)
# ============================================================
def place_desert_dirt_paths(pts):
    """Place 2-3 dirt paths branching from the main road into the desert."""
    objs = []

    # Path 1: Branches right, leads to a campfire site
    branch_1 = int(len(pts) * 0.15)
    _, end1 = create_dirt_path(pts, branch_1, side=1, path_len=25, path_width=1.0)
    objs.extend(make_campfire(end1))
    # A few rocks around the campfire
    for _ in range(4):
        ang = random.uniform(0, math.pi * 2)
        dist = random.uniform(0.4, 0.8)
        rp = end1 + Vector((math.cos(ang) * dist, math.sin(ang) * dist, 0))
        rs = random.uniform(0.06, 0.12)
        objs.append(cube(rp + Vector((0, 0, rs * 0.5)), (rs, rs, rs), get_mat('red_rock', make_red_rock)))

    # Path 2: Branches left, leads to an off-road driving course
    branch_2 = int(len(pts) * 0.45)
    _, end2 = create_dirt_path(pts, branch_2, side=-1, path_len=28, path_width=0.9)
    objs.extend(make_off_road_course(end2))

    # Path 3: Branches right toward a mesa area
    branch_3 = int(len(pts) * 0.75)
    _, end3 = create_dirt_path(pts, branch_3, side=1, path_len=18, path_width=0.8)
    # A couple of oil barrels at the end
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

    # Apply artist profile settings from BlenderMCP panel
    cfg = apply_profile_config()
    print(f"  Export Format: {cfg['export_format']}")
    print(f"  Naming Prefix: {cfg['naming_prefix']}")

    pts = get_road_points(120)

    print("[1/13] Road surface..."); create_road_mesh(pts)
    print("[2/13] Lane markings..."); create_curved_markings(pts, LANE_COUNT)
    print("[3/13] Sidewalks...")
    for s in [-1, 1]: create_sidewalk_side(pts, s)
    print("[4/13] Road curbs..."); create_road_curbs(pts)
    print("[5/13] Ground plane..."); create_ground_plane()
    print("[6/13] Sand terrain...")
    for s in [-1, 1]: create_terrain_side(pts, s)
    print("[7/13] Bridge..."); make_bridge_supports(pts)
    print("[8/13] Overpass..."); create_overpass(pts)
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
    setup_scene(camera_loc=(18, -25, 12), sun_color=(1.0, 0.85, 0.65), use_profile=True)
    print("DONE! Export: File > Export > FBX/glTF")


if __name__ == "__main__":
    main()
