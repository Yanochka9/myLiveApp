"""Renders one 3D element as a transparent PNG sequence (run as: python3 blender3d.py -- spec.json outdir threads [frames])."""
import bpy, math, sys, os, json
from mathutils import Vector

ARGS = sys.argv[sys.argv.index('--') + 1:]
SPEC = json.load(open(ARGS[0], encoding='utf-8'))
OUT, THREADS = ARGS[1], int(ARGS[2])
ONLY = [int(x) for x in ARGS[3].split(',')] if len(ARGS) > 3 and ARGS[3] else None

KIND, N = SPEC['kind'], SPEC['frames']
C = SPEC['colors']


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo3(t): t = clamp(t); return 1 - (1 - t) ** 3
def eio(t): t = clamp(t); return t * t * (3 - 2 * t)
def eback(t, s=1.4):
    t = clamp(t) - 1; return t * t * ((s + 1) * t + s) + 1


def lin(hexs):
    h = hexs.lstrip('#')
    def f(c):
        c = int(c, 16) / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (f(h[0:2]), f(h[2:4]), f(h[4:6]))


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def mat(name, color, metal, rough, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin(color), 1)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    if coat:
        b.inputs['Coat Weight'].default_value = coat
        b.inputs['Coat Roughness'].default_value = 0.05
    return m


M_FRONT = mat('front', C['front'], C['metallic'], C['roughness'], coat=1.0)
M_SIDE = mat('side', C['side'], 0.85, 0.28)
M_WHITE = mat('white', C['white'], 0.0, 0.2, coat=0.6)
M_DARK = mat('dark', C['dark'], 0.6, 0.25, coat=0.8)


def assign_by_normal(ob, front, side):
    ob.data.materials.clear(); ob.data.materials.append(front); ob.data.materials.append(side)
    for p in ob.data.polygons:
        p.material_index = 0 if p.normal.dot(Vector((0, -1, 0))) > 0.92 else 1


def text_mesh(body, size=1.0, extrude=0.16, bevel=0.025, front=M_FRONT, side=M_SIDE):
    bpy.ops.object.text_add(location=(0, 0, 0))
    t = bpy.context.object
    t.data.body = body; t.data.font = bpy.data.fonts.load(SPEC['font'])
    t.data.size = size; t.data.align_x = 'CENTER'; t.data.align_y = 'CENTER'
    t.data.extrude = extrude; t.data.bevel_depth = bevel; t.data.bevel_resolution = 4
    t.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.convert(target='MESH')
    ob = bpy.context.object
    bpy.ops.object.transform_apply(rotation=True)
    assign_by_normal(ob, front, side)
    return ob


def split_letters(ob):
    """one object per glyph (caps/sides of a glyph are separate loose parts, so cluster them by x)"""
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0005)
    bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
    parts = list(bpy.context.selected_objects)
    def xr(o):
        xs = [(o.matrix_world @ Vector(c)).x for c in o.bound_box]; return min(xs), max(xs)
    parts.sort(key=lambda o: xr(o)[0])
    clusters = []
    for o in parts:
        a, b = xr(o)
        if clusters:
            c = clusters[-1]
            if min(b, c[1]) - max(a, c[2]) > 0.5 * min(b - a, c[1] - c[2]):
                c[0].append(o); c[1] = max(c[1], b); continue
        clusters.append([[o], b, a])
    letters = []
    for objs, _, _ in clusters:
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        L = bpy.context.view_layer.objects.active
        bpy.ops.object.select_all(action='DESELECT'); L.select_set(True)
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        letters.append(L)
    return letters


def group(objs):
    e = bpy.data.objects.new('grp', None); sc.collection.objects.link(e)
    for o in objs: o.parent = e
    return e


def bbox_w(objs):
    xs = [(o.matrix_world @ Vector(c)).x for o in objs for c in o.bound_box]
    return max(xs) - min(xs)


def setup(objs):
    Wc, Hc = SPEC['canvas']
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = SPEC.get('samples', 14); sc.cycles.use_denoising = True
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.03
    sc.cycles.max_bounces = 6; sc.cycles.glossy_bounces = 3
    sc.render.threads_mode = 'FIXED'; sc.render.threads = THREADS
    sc.render.resolution_x = Wc; sc.render.resolution_y = Hc; sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'
    D = bbox_w(objs) / (SPEC['frac'] * 36.0 / 50.0)
    cam = bpy.data.cameras.new('cam'); cam.lens = 50; cam.sensor_fit = 'HORIZONTAL'; cam.sensor_width = 36
    co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    co.location = (0, -D, 0); co.rotation_euler = (math.pi / 2, 0, 0)
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    grad = nt.nodes.new('ShaderNodeTexGradient'); tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, math.pi / 2, 0)
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.02, 0.0, 0.0, 1); ramp.color_ramp.elements[1].color = (1.0, 0.9, 0.9, 1)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], grad.inputs['Vector'])
    nt.links.new(grad.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.9
    s = D / 12.0
    for loc, en, size, rot in [((-4 * s, -6 * s, 6 * s), 2600, 6, (50, 0, -35)), ((6 * s, -4 * s, -2 * s), 900, 4, (100, 0, 55)),
                               ((0, 6 * s, 3 * s), 1800, 6, (-60, 0, 0))]:
        l = bpy.data.lights.new('a', 'AREA'); l.energy = en * s * s; l.size = size * s
        o = bpy.data.objects.new('a', l); sc.collection.objects.link(o)
        o.location = loc; o.rotation_euler = tuple(math.radians(r) for r in rot)


def render(fn):
    os.makedirs(OUT, exist_ok=True)
    for f in (ONLY if ONLY is not None else range(N)):
        p = os.path.join(OUT, f'{f:04d}.png')
        if os.path.exists(p): continue
        fn(f)
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        print('frame', f, flush=True)


# ------------------------------------------------------------------ kinds
if KIND in ('rise', 'spin'):
    # letters rise and flip up one by one; 'spin' keeps turning slowly (end-card title)
    letters = split_letters(text_mesh(SPEC['text'], extrude=SPEC.get('extrude', 0.16)))
    g = group(letters)
    base = {l.name: l.location.copy() for l in letters}
    setup(letters)
    st = SPEC.get('stagger', 2)
    a0, a1 = SPEC.get('sweep', [-10, 6] if KIND == 'rise' else [-14, 14])
    def fn(f):
        for i, l in enumerate(letters):
            p = eo3((f - i * st) / 15.0); b = base[l.name]
            l.location = (b.x, b.y, b.z - 1.3 * (1 - p))
            l.rotation_euler = (math.radians(95) * (1 - p), 0, 0)
        u = f / max(1, N - 1)
        g.rotation_euler = (math.radians(4 if KIND == 'rise' else 6), 0,
                            math.radians(a0 + (a1 - a0) * (eio(u) if KIND == 'rise' else u)))
    render(fn)

elif KIND == 'badge':
    ob = text_mesh(SPEC['text'], extrude=0.3, bevel=0.03)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1.0, depth=0.18, rotation=(math.pi / 2, 0, 0), location=(0, 0.2, 0))
    disc = bpy.context.object
    tw = bbox_w([ob])
    disc.scale = (max(1.15, tw * 0.62), 1, 0.62); bpy.ops.object.transform_apply(scale=True)
    bv = disc.modifiers.new('b', 'BEVEL'); bv.width = 0.05; bv.segments = 4
    disc.data.materials.append(M_DARK)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.05, rotation=(math.pi / 2, 0, 0), location=(0, 0.1, 0))
    ring = bpy.context.object; ring.scale = (max(1.15, tw * 0.62), 1, 0.62); ring.data.materials.append(M_FRONT)
    g = group([ob, disc, ring])
    setup([disc])
    def fn(f):
        p = eback(f / 14.0, 1.2)
        g.rotation_euler = (math.radians(8), 0, math.radians(-200 * (1 - eo3(f / 14.0)) + 12 * math.sin(f / 9.0)))
        s = 0.2 + 0.8 * p; g.scale = (s, s, s)
    render(fn)

elif KIND == 'slab':
    tx = text_mesh(SPEC['text'], size=1.0, extrude=0.08, bevel=0.012, front=M_WHITE, side=M_WHITE)
    tw = bbox_w([tx])
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.12, 0))
    slab = bpy.context.object; slab.scale = (tw + 1.1, 0.22, 1.5); bpy.ops.object.transform_apply(scale=True)
    bv = slab.modifiers.new('b', 'BEVEL'); bv.width = 0.45; bv.segments = 10; bv.limit_method = 'NONE'
    slab.data.materials.append(M_FRONT)
    tx.location = (0, -0.08, 0)
    g = group([slab, tx])
    setup([slab])
    def fn(f):
        p = eback(f / 16.0, 1.3)
        g.rotation_euler = (math.radians(-85 * (1 - eo3(f / 16.0)) + 3 * math.sin(f / 10.0)), 0,
                            math.radians(-8 + 6 * math.sin(f / 14.0)))
        s = 0.3 + 0.7 * p; g.scale = (s, s, s)
    render(fn)

elif KIND == 'pin':
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0, location=(0, 0, 0.9))
    head = bpy.context.object
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=0.001, radius2=0.86, depth=1.6, location=(0, 0, -0.35))
    tip = bpy.context.object
    for o in (head, tip): o.data.materials.append(M_FRONT)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.42, location=(0, -0.72, 0.95))
    dot = bpy.context.object; dot.scale = (1, 0.45, 1); dot.data.materials.append(M_WHITE)
    for o in (head, tip, dot):
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.shade_smooth()
    g = group([head, tip, dot])
    setup([head])
    def fn(f):
        drop = 1 - eback(f / 14.0, 1.6)
        g.location = (0, 0, 3.0 * drop + 0.12 * math.sin(f / 8.0))
        g.rotation_euler = (math.radians(6), 0, math.radians(-120 * drop + 28 * math.sin(f / 11.0)))
    render(fn)
else:
    raise SystemExit(f'unknown 3D kind {KIND}')
