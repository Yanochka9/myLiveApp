# Cover for projects/top3.json: run after the render (uses the final 3D frames in cache3d/). Writes work/top3/cover/cover_A.jpg, cover_B.jpg
import sys, subprocess, numpy as np
sys.path.insert(0, '/home/user/myLiveApp/video-kit/kit')
from PIL import Image, ImageDraw, ImageFilter
from common import Project, W, H
import compose
p = Project('/home/user/myLiveApp/video-kit/projects/top3.json'); g = compose.Gfx(p)
OUT = '/home/user/myLiveApp/video-kit/work/top3/cover/'
C = '/home/user/myLiveApp/video-kit/cache3d/'

def frame(clip, t):
    vf = f"scale={W}:{H}:flags=bicubic,{compose.grade_filter(p, clip)},format=rgb24"
    buf = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', p.clip(clip), '-vf', vf, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         stdout=subprocess.PIPE, check=True).stdout
    return Image.fromarray(np.frombuffer(buf, np.uint8).reshape(H, W, 3)).convert('RGBA')

def last3d(d, n):
    return Image.open(f'{C}{d}/{n - 1:04d}.png').convert('RGBA')

def put(dst, im, cx, cy, sc=1.0):
    if sc != 1: im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
    dst.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def shade(im, top=0.0, bottom=0.0, y0=0.3):
    a = np.zeros((H, W), np.float32); yy = np.linspace(0, 1, H)[:, None]
    a += top * np.clip(1 - yy / y0, 0, 1) ** 1.5
    a += bottom * np.clip((yy - (1 - y0)) / y0, 0, 1) ** 1.5
    ov = Image.new('RGBA', (W, H), (*p.color('dark'), 0)); ov.putalpha(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)))
    im.alpha_composite(ov); return im

def vignette(im):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - 0.3 * np.clip(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2, 0, 1) ** 1.3
    arr = np.asarray(im).astype(np.float32); arr[..., :3] *= v[..., None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), 'RGBA')

# ---------- A: presenter + title
a = vignette(shade(frame('IMG_2176.MOV', 1.3), top=0.55, bottom=0.75, y0=0.38))
top3 = last3d('rise-aa86c2eaee0e', 129)
put(a, top3, 540, 520, 0.95)
put(a, g.gold('АВТО БЕЗ ПРОБЕГА', 76), 540, 330)
put(a, g.pill('ПО РБ', 46, 'dark', 'xbold', None), 540, 700)
y = 1170
for n, name in [(1, 'VOLKSWAGEN JETTA'), (2, 'CHEVROLET TRAILBLAZER'), (3, 'BUICK ENCORE GX')]:
    r = g.rank(n, 52, name); put(a, r, 540, y); y += 120
put(a, g.pill('от 1 100 BYN/мес · без первого взноса', 40, 'accent', 'xbold', None), 540, 1530)
a.convert('RGB').save(OUT + 'cover_A.jpg', quality=93)

# ---------- B: three cars stacked + title
b = Image.new('RGBA', (W, H), (*p.color('dark'), 255))
strips = [('IMG_2217.MOV', 0.6, 1, 'rise-80d21ce501df', 65, 'VOLKSWAGEN'),
          ('IMG_2208.MOV', 0.6, 2, 'rise-211a30b0a669', 66, 'CHEVROLET'),
          ('IMG_2184.MOV', 1.0, 3, 'rise-7c360b86f60e', 72, 'BUICK')]
y0, sh = 580, 330
for i, (clip, t, n, d, fr, brand) in enumerate(strips):
    f = frame(clip, t); cy = {'IMG_2217.MOV': 1150, 'IMG_2208.MOV': 1050, 'IMG_2184.MOV': 1080}[clip]
    crop = f.crop((0, cy - sh // 2 - 40, W, cy + sh // 2 - 40))
    top_y = y0 + i * (sh + 14); b.alpha_composite(crop, (0, top_y))
    grad = np.zeros((sh, W), np.float32); grad[:] = np.clip(1 - np.linspace(0, 1, W) / 0.55, 0, 1)[None, :] * 0.75
    ov = Image.new('RGBA', (W, sh), (*p.color('dark'), 0)); ov.putalpha(Image.fromarray((grad * 255).astype(np.uint8))); b.alpha_composite(ov, (0, top_y))
    put(b, g.rank(n, 50, brand), 290, top_y + 80)
    put(b, last3d(d, fr), 330, top_y + 215, 0.46)
    ImageDraw.Draw(b).rectangle((0, top_y + sh, W, top_y + sh + 14), fill=(*p.color('accent'), 255))
put(b, top3, 540, 455, 0.72)
put(b, g.gold('БЕЗ ПРОБЕГА ПО РБ', 60), 540, 310)
put(b, g.pill('от 1 100 BYN/мес · без первого взноса', 42, 'accent', 'xbold', None), 540, 1640)
b = vignette(b)
b.convert('RGB').save(OUT + 'cover_B.jpg', quality=93)

# side-by-side with the Instagram grid crop (3:4, centre) marked
sheet = Image.new('RGB', (W * 2 + 40, H), 'white')
for i, f in enumerate(['cover_A.jpg', 'cover_B.jpg']):
    im = Image.open(OUT + f).convert('RGB'); d = ImageDraw.Draw(im)
    d.rectangle((0, 240, W - 1, 1680), outline=(255, 60, 60), width=6)
    sheet.paste(im, (i * (W + 40), 0))
sheet.resize((sheet.width // 3, sheet.height // 3)).save(OUT + 'covers_check.jpg', quality=88)
print('ok')
