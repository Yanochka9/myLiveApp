"""Belavto cover style: dark cool desaturated frame, strong vignette, chrome condensed title, yellow price."""
import sys, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
W, H = 1080, 1920
FONT = '/home/user/myLiveApp/video-kit/assets/fonts/Oswald-Bold.ttf'
TM = 'zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,'

def frame(path, t, zoom=1.0, cy=0.62):
    vf = f"{TM}scale={int(W*zoom)}:{int(H*zoom)},crop={W}:{H}:(iw-{W})/2:(ih-{H})*{cy},eq=saturation=0.5:contrast=1.15:gamma=1.02:brightness=0.0,colorbalance=bs=0.10:bm=0.05:rh=-0.03,format=rgb24"
    buf = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', path, '-vf', vf, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32)

def mood(a):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.55 * np.clip(((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H * 0.68) / (H * 0.6)) ** 2, 0, 1) ** 1.4
    top = 1 - 0.45 * np.clip(1 - yy / (H * 0.42), 0, 1) ** 1.3          # darker ceiling under the title
    a = a * (vig * top)[..., None]
    lum = a.mean(2, keepdims=True); a = a * 0.85 + lum * 0.15 + np.array([-4, 0, 10], np.float32)  # cool steel cast
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert('RGBA')

def grad_text(text, size, stops, outline=(10, 12, 16), ow=0.035, track=0):
    f = ImageFont.truetype(FONT, size); bb = f.getbbox(text); o = max(3, int(size * ow))
    w, h = bb[2] - bb[0] + 2 * o + 40, bb[3] - bb[1] + 2 * o + 40
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).text((20 + o - bb[0], 20 + o - bb[1]), text, font=f, fill=255)
    so = Image.new('L', (w, h), 0); ImageDraw.Draw(so).text((20 + o - bb[0], 20 + o - bb[1]), text, font=f, fill=255, stroke_width=o, stroke_fill=255)
    ys = np.linspace(0, 1, h); g = np.zeros((h, w, 3), np.float32)
    top_px, bot_px = (20 + o) / h, (h - 20 - o) / h
    u = np.clip((ys - top_px) / (bot_px - top_px), 0, 1)
    pos = [s[0] for s in stops]; cols = np.array([s[1] for s in stops], np.float32)
    for k in range(3): g[..., k] = np.interp(u, pos, cols[:, k])[:, None]
    fill = Image.fromarray(g.astype(np.uint8)).convert('RGBA'); fill.putalpha(m)
    im = Image.new('RGBA', (w, h), (*outline, 0)); im.putalpha(so); im.alpha_composite(fill)
    sh = Image.new('RGBA', (w + 60, h + 60), (0, 0, 0, 0)); a = so.point(lambda v: int(v * 0.75))
    blk = Image.new('RGBA', (w, h), (0, 0, 0, 255)); blk.putalpha(a); sh.paste(blk, (30, 42), blk)
    sh = sh.filter(ImageFilter.GaussianBlur(16)); sh.alpha_composite(im, (30, 30))
    return sh

CHROME = [(0, (250, 252, 255)), (0.42, (205, 210, 218)), (0.5, (120, 126, 136)), (0.62, (225, 228, 234)), (1, (150, 155, 165))]
YELLOW = [(0, (255, 236, 110)), (0.5, (255, 214, 40)), (1, (232, 168, 10))]
WHITE = [(0, (255, 255, 255)), (1, (214, 218, 226))]

def tall(im, k=1.22):
    return im.resize((im.width, int(im.height * k)), Image.LANCZOS)

def put(dst, im, cx, cy):
    dst.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def cover(src, t, out, title, sub=None, price=None, title_size=320, zoom=1.0, cy=0.5):
    """title stays inside the Instagram 3:4 grid crop (y 240-1680); long titles shrink to the frame width"""
    im = mood(frame(src, t, zoom, cy))
    ti = tall(grad_text(title, title_size, CHROME))
    if ti.width > W - 40: ti = ti.resize((W - 40, int(ti.height * (W - 40) / ti.width)), Image.LANCZOS)
    put(im, ti, 540, 470)
    y = 470 + ti.height / 2 + 40
    if sub: s = grad_text(sub, 96, WHITE, ow=0.03); put(im, s, 540, y + s.height / 2 - 40); y += s.height - 30
    if price: put(im, grad_text(price, 110, YELLOW), 540, y + 70)
    im.convert('RGB').save(out, quality=94)

if __name__ == '__main__':
    # python3 -I kit/cover.py <clip> <second> <out.jpg> "ТОП 3" ["Без пробега по РБ"] ["1100 BYN/мес"]
    a = sys.argv[1:]
    cover(a[0], float(a[1]), a[2], a[3], a[4] if len(a) > 4 else None, a[5] if len(a) > 5 else None)
    print(a[2])
