# Общие помощники графики (из repaint/gfx.py): объёмный текст за спиной, «пирог» ЛКП с отрывом лака, оригинал vs перекрас,
# иконки, плашки, таймлайн, финал. Всё в безопасной зоне Reels/TikTok: по центру, ширина ≤ 720 px
# (x 180–900), по высоте 250–1560. Читает out/video_raw.mp4 → out/video_gfx.mp4 (субтитры — finish.py).
import numpy as np, subprocess, math, os, random, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from tl import *  # noqa

WD, HT, FPS = 1080, 1920, 30
SAFE_W = 720
FA = f"{R0}/../assets/fonts"
def FO(s): return ImageFont.truetype(f"{FA}/Oswald-Bold.ttf", s)
def FM(s): return ImageFont.truetype(f"{FA}/Montserrat-ExtraBold.ttf", s)
def FI(s): return ImageFont.truetype(f"{FA}/Inter-Black.otf", s)
GOLD = (212, 175, 55); GOLD2 = (236, 205, 110); RED = (226, 64, 64); WHITE = (255, 255, 255)
DARK = (14, 14, 14)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo(p): p = clamp(p); return 1 - (1 - p) ** 3
def eio(p): p = clamp(p); return p * p * (3 - 2 * p)
def fade(t, a, b, fi=0.22, fo=0.2):
    if t < a or t >= b: return 0.0
    return clamp((t - a) / fi) * clamp((b - t) / fo)

# ---------- helpers ----------
def text_img(txt, font, fill, stroke=0, sfill=(0, 0, 0), spacing=0, shadow=None):
    tmp = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    if spacing:
        ws = [tmp.textbbox((0, 0), ch, font=font, stroke_width=stroke)[2] for ch in txt]
        w = sum(ws) + spacing * (len(txt) - 1)
    else:
        w = tmp.textbbox((0, 0), txt, font=font, stroke_width=stroke)[2]
    asc, desc = font.getmetrics(); pad = 30
    im = Image.new('RGBA', (int(w) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if spacing:
        x = pad
        for ch, cw in zip(txt, ws):
            d.text((x, pad), ch, font=font, fill=fill, stroke_width=stroke, stroke_fill=sfill); x += cw + spacing
    else:
        d.text((pad, pad), txt, font=font, fill=fill, stroke_width=stroke, stroke_fill=sfill)
    im = im.crop(im.getbbox())
    if shadow:
        off, blur, alpha = shadow
        sh = Image.new('RGBA', (im.width + 4 * blur + off, im.height + 4 * blur + off), (0, 0, 0, 0))
        a = im.split()[3].point(lambda v: v * alpha // 255)
        blk = Image.new('RGBA', im.size, (0, 0, 0, 255)); blk.putalpha(a)
        sh.paste(blk, (2 * blur + off, 2 * blur + off), blk)
        sh = sh.filter(ImageFilter.GaussianBlur(blur))
        sh.alpha_composite(im, (2 * blur, 2 * blur)); im = sh
    return im

def fitw(im, maxw):
    if im.width <= maxw: return im
    return im.resize((maxw, max(1, int(im.height * maxw / im.width))), Image.LANCZOS)

def put(canvas, im, cx, cy, alpha=1.0, scale=1.0, rot=0.0):
    if alpha <= 0.003: return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1.0:
        a = im.split()[3].point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def hires(w, h, fn, k=2):
    im = Image.new('RGBA', (w * k, h * k), (0, 0, 0, 0)); fn(ImageDraw.Draw(im), k)
    return im.resize((w, h), Image.LANCZOS)

def panel(w, h, border=GOLD, alpha=200, r=24, bw=2):
    def fn(d, k):
        d.rounded_rectangle((2 * k, 2 * k, (w - 2) * k, (h - 2) * k), r * k, fill=DARK + (alpha,), outline=border + (255,), width=bw * k)
    return hires(w, h, fn)

def pill(w, h, fill, alpha=230, outline=None):
    def fn(d, k):
        d.rounded_rectangle((2 * k, 2 * k, (w - 2) * k, (h - 2) * k), h * k // 2, fill=fill + (alpha,),
                            outline=(outline + (255,)) if outline else None, width=2 * k)
    return hires(w, h, fn)

def circle_icon(r, ring=GOLD, fill=DARK, inner=None, alpha=215, sc=1.0):
    s = 2 * r + 8
    def fn(d, k):
        d.ellipse((4 * k, 4 * k, (s - 4) * k, (s - 4) * k), fill=fill + (alpha,), outline=ring + (255,), width=3 * k)
        if inner: inner(d, k * sc, s / 2 / sc)
    return hires(s, s, fn)

# ---------- icons (k-scaled, centre c) ----------
def ic_pin(col):
    def f(d, k, c):
        c *= k; r = 30 * k
        d.ellipse((c - r, c - r - 14 * k, c + r, c + r - 14 * k), fill=col)
        d.polygon([(c - r * 0.86, c - 14 * k + r * 0.5), (c + r * 0.86, c - 14 * k + r * 0.5), (c, c + 46 * k)], fill=col)
        d.ellipse((c - 11 * k, c - 25 * k, c + 11 * k, c - 3 * k), fill=DARK)
    return f
def ic_tag(col):
    def f(d, k, c):
        c *= k; ang = math.radians(-30)
        R = lambda x, y: (c + (x * math.cos(ang) - y * math.sin(ang)) * k, c + (x * math.sin(ang) + y * math.cos(ang)) * k)
        d.polygon([R(-38, -22), R(18, -22), R(42, 0), R(18, 22), R(-38, 22)], fill=col)
        X, Y = R(22, 0); d.ellipse((X - 6 * k, Y - 6 * k, X + 6 * k, Y + 6 * k), fill=DARK)
        d.text((c - 8 * k, c + 2 * k), "?", font=FO(int(40 * k)), fill=DARK, anchor='mm')
    return f
def ic_spray(col):
    def f(d, k, c):
        c *= k
        d.rounded_rectangle((c - 20 * k, c - 18 * k, c + 20 * k, c + 44 * k), 8 * k, fill=col)
        d.rectangle((c - 9 * k, c - 30 * k, c + 9 * k, c - 18 * k), fill=col)
        d.rectangle((c - 3 * k, c - 36 * k, c + 14 * k, c - 30 * k), fill=col)
        for dx, dy in [(26, -40), (34, -30), (30, -50), (40, -42), (22, -54)]:
            d.ellipse((c + dx * k - 3 * k, c + dy * k - 3 * k, c + dx * k + 3 * k, c + dy * k + 3 * k), fill=col)
    return f
def ic_chip(col):
    def f(d, k, c):
        c *= k; P = []
        for i in range(14):
            r = (40 if i % 2 == 0 else 16) * k * (0.8 + 0.25 * ((i * 7) % 3) / 2); a = i / 14 * 2 * math.pi
            P.append((c + r * math.cos(a), c + r * math.sin(a)))
        d.polygon(P, fill=col)
    return f
def ic_rust(col):
    def f(d, k, c):
        c *= k; rnd = random.Random(3)
        for i in range(16):
            r = rnd.uniform(6, 15) * k; x = c + rnd.uniform(-34, 34) * k; y = c + rnd.uniform(-30, 30) * k
            d.ellipse((x - r, y - r, x + r, y + r), fill=col)
    return f
def ic_shield(col):
    def f(d, k, c):
        c *= k
        d.polygon([(c, c - 44 * k), (c + 36 * k, c - 30 * k), (c + 32 * k, c + 14 * k), (c, c + 44 * k),
                   (c - 32 * k, c + 14 * k), (c - 36 * k, c - 30 * k)], fill=col)
        d.line([(c - 15 * k, c), (c - 3 * k, c + 13 * k), (c + 18 * k, c - 14 * k)], fill=DARK, width=int(8 * k))
    return f
def ic_check(col=DARK):
    def f(d, k, c):
        c *= k
        d.line([(c - 22 * k, c + 2 * k), (c - 6 * k, c + 18 * k), (c + 24 * k, c - 16 * k)], fill=col, width=int(11 * k), joint='curve')
    return f
def ic_cross(col):
    def f(d, k, c):
        c *= k; a = 40 * k
        d.line([(c - a, c - a), (c + a, c + a)], fill=col, width=int(15 * k))
        d.line([(c - a, c + a), (c + a, c - a)], fill=col, width=int(15 * k))
    return f


def char3d(ch, font, top, bot, side, depth=16):
    asc, desc = font.getmetrics(); pad = depth + 40
    bb = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), ch, font=font)
    w = bb[2] + 2 * pad; h = asc + desc + 2 * pad
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).text((pad, pad), ch, font=font, fill=255)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    # мягкая тень на стену
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sm = m.filter(ImageFilter.GaussianBlur(10)).point(lambda v: v * 110 // 255)
    sh.paste((0, 0, 0, 255), (depth + 8, depth + 12), sm); im.alpha_composite(sh)
    # экструзия (борт буквы)
    for i in range(depth, 0, -1):
        f = 0.55 + 0.45 * (1 - i / depth)
        col = tuple(int(c * f) for c in side) + (255,)
        im.paste(col, (int(i * 0.75), int(i * 0.95)), m)
    # лицевая грань — вертикальный градиент
    grad = np.zeros((h, w, 4), np.uint8)
    ys = np.clip((np.arange(h) - pad) / max(1, asc), 0, 1)[:, None]
    for c in range(3): grad[..., c] = (top[c] * (1 - ys) + bot[c] * ys).astype(np.uint8)
    grad[..., 3] = np.asarray(m)
    face = Image.fromarray(grad, 'RGBA'); im.alpha_composite(face)
    # фаска: светлый верхний край
    edge = np.clip(np.asarray(m, np.int16) - np.asarray(m.transform(m.size, Image.AFFINE, (1, 0, 0, 0, 1, 3)), np.int16), 0, 255).astype(np.uint8)
    hl = Image.new('RGBA', (w, h), (255, 255, 255, 0)); hl.putalpha(Image.fromarray(edge).point(lambda v: v * 170 // 255))
    im.alpha_composite(hl)
    return im, bb[2]

def word3d(txt, size, top, bot, side, track=4, maxw=860):
    font = FO(size)
    parts = [char3d(ch, font, top, bot, side) for ch in txt]
    total = sum(adv for _, adv in parts) + track * (len(txt) - 1)
    k = min(1.0, maxw / total)
    if k < 1.0:
        return word3d(txt, int(size * k), top, bot, side, track, maxw)
    xs = []; x = -total / 2
    for im, adv in parts:
        xs.append(x + adv / 2); x += adv + track
    return parts, xs


def logo_img(size=330):
    im = Image.open(f"{R0}/brand/logo.png").convert('RGBA')
    m = Image.new('L', (im.width * 2, im.height * 2), 0)
    ImageDraw.Draw(m).ellipse((40, 40, im.width * 2 - 40, im.height * 2 - 40), fill=255)
    im.putalpha(m.resize(im.size, Image.LANCZOS)); im = im.resize((size, size), Image.LANCZOS)
    ring = hires(size + 30, size + 30, lambda d, k: d.ellipse((3 * k, 3 * k, (size + 27) * k, (size + 27) * k), outline=GOLD + (255,), width=4 * k))
    ring.alpha_composite(im, (15, 15)); return ring
