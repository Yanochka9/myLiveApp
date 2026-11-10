# 3D «−10%»: золотой металл с фаской, лёгкий поворот, прозрачный фон → out/b3d/####.png
import bpy, math, sys, os
OUT = sys.argv[sys.argv.index('--') + 1]; N = 60
FONT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../assets/fonts/Oswald-Bold.ttf'))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 900, 420
sc.render.film_transparent = True; sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
sc.frame_start, sc.frame_end = 1, N
bpy.ops.object.text_add(); t = bpy.context.object; t.data.body = '−10%'
t.data.font = bpy.data.fonts.load(FONT); t.data.align_x = 'CENTER'; t.data.align_y = 'CENTER'
t.data.extrude = 0.12; t.data.bevel_depth = 0.025; t.data.bevel_resolution = 4; t.data.size = 1.6
m = bpy.data.materials.new('gold'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (1.0, 0.78, 0.30, 1); b.inputs['Metallic'].default_value = 1.0; b.inputs['Roughness'].default_value = 0.16
t.data.materials.append(m)
t.rotation_euler = (math.radians(90), 0, 0)
for f, a in [(1, -24), (N, 8)]:
    t.rotation_euler[2] = math.radians(a); t.keyframe_insert('rotation_euler', frame=f)
for fc in t.animation_data.action.fcurves if hasattr(t.animation_data.action, 'fcurves') else []:
    for k in fc.keyframe_points: k.interpolation = 'SINE'
bpy.ops.object.camera_add(location=(0, -6.2, 0.25), rotation=(math.radians(88), 0, 0)); sc.camera = bpy.context.object
sc.camera.data.lens = 70
for loc, en, sz in [((-3, -4, 4), 2200, 3), ((4, -3, 1), 1300, 2), ((0, 3, 3), 1200, 4), ((0, -5, -2), 600, 6)]:
    bpy.ops.object.light_add(type='AREA', location=loc); L = bpy.context.object; L.data.energy = en; L.data.size = sz
    d = L.location.normalized(); L.rotation_euler = (0, 0, 0)
    L.rotation_mode = 'QUATERNION'; L.rotation_quaternion = (-L.location).to_track_quat('-Z', 'Y')
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.08, 0.08, 0.1, 1); bg.inputs['Strength'].default_value = 1.4
sc.render.filepath = OUT + '/'
bpy.ops.render.render(animation=True)
