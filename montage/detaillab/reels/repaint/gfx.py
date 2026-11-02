# Графика рилса: объёмный текст за спиной, «пирог» ЛКП с отрывом лака, оригинал vs перекрас,
# иконки, плашки, таймлайн, финал. Всё в безопасной зоне Reels/TikTok: по центру, ширина ≤ 720 px
# (x 180–900), по высоте 250–1560. Читает out/video_raw.mp4 → out/video_gfx.mp4 (субтитры — finish.py).
import numpy as np, subprocess, math, os, random, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from tl import *

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

# ---------- times ----------
T_BR1 = word('2509', 'самый')
T_CAKE = word('2509', 'полиуретановые'); T_STRONG = word('2509', 'сильно'); T_SECOND = word('2509', 'авторичном')
T_PEEL = word('2509', 'подорвать', after=26.0)
T_NEG0 = word('2509', 'и', after=28.0); T_NEGOD = word('2509', 'негодность')
T_Q = word('2509', 'несет')
T_WHERE = word('2509', 'где'); T_PRICE = word('2509', 'стоимость'); T_HOW = word('2509', 'как', after=37.0)
T_PO1 = word('2509', 'поэтому'); T_RANEE = word('2509', 'ранее')
T_DET3 = word('2509', 'детейлинг', 3); T_OTHER = word('2509', 'другие')
T_PO2 = word('2510', 'поэтому'); T_NEW = word('2510', 'новый')
T_NE = word('2510', 'не'); T_SKOL = word('2510', 'скола'); T_KOR = word('2510', 'коррозия')
T_PEREK = word('2510', 'перекрашивали'); T_KLE = word('2510', 'клеиться'); T_LUCH = word('2510', 'лучше')
T_PRI = word('2509', 'приезжайте', 2)
CMP = [s for s in SHOTS if s[2] == 'b' and s[3] == '2516'][0]      # подсъём капота: оригинал/перекрас
T_CMP0, T_CMP1 = CMP[0], CMP[1]

# ---------- 1. объёмный текст за спиной ----------
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

W1 = word3d("ВТОРИЧНЫЙ", 196, (255, 255, 255), (168, 172, 182), (58, 60, 68))
W2 = word3d("ОКРАС?", 270, (255, 228, 145), (178, 128, 28), (96, 64, 12))
MATTE = np.load(f"{OUT}/matte.npy")

def behind(fi, t):
    if t >= T_BR1 or fi >= len(MATTE): return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0))
    out = clamp((T_BR1 - t) / 0.25); push = 1.0 + 0.035 * eio(t / T_BR1)
    for (parts, xs), cy, t0 in [(W1, 400, 0.15), (W2, 640, 0.55)]:
        for i, ((im, adv), x) in enumerate(zip(parts, xs)):
            p = eo((t - t0 - i * 0.05) / 0.4)
            if p <= 0: continue
            put(lay, im, 540 + x * push, cy + 50 * (1 - p), alpha=p * out, scale=(0.7 + 0.3 * p) * push)
    # блик, пробегающий по буквам
    g = (t - 1.5) / 0.9
    if 0 < g < 1:
        a = np.asarray(lay.split()[3], np.float32)
        yy, xx = np.mgrid[0:HT, 0:WD]
        band = np.exp(-((xx + 0.45 * yy - (-300 + g * 1900)) / 55.0) ** 2) * 0.55
        arr = np.asarray(lay, np.float32).copy()
        arr[..., :3] = arr[..., :3] + (255 - arr[..., :3]) * band[..., None] * (a[..., None] / 255)
        lay = Image.fromarray(arr.clip(0, 255).astype(np.uint8), 'RGBA')
    m = Image.fromarray(MATTE[fi]).resize((WD, HT), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2))
    a = np.asarray(lay.split()[3], np.float32) * (1 - np.asarray(m, np.float32) / 255)
    lay.putalpha(Image.fromarray(a.astype(np.uint8)))
    return lay

# ---------- 2. «пирог» ЛКП ----------
X0, Y0, WS = 205, 1500, 360
DX, DY = 110, -62
LAYERS = [('МЕТАЛЛ', (150, 156, 164), 255, 40), ('ГРУНТ', (196, 190, 178), 255, 30),
          ('КРАСКА', (24, 24, 30), 255, 36), ('ЛАК', (190, 215, 235), 130, 26), ('ПЛЁНКА', (255, 238, 180), 85, 26)]
def shade(c, f): return tuple(int(clamp(v * f, 0, 255)) for v in c)
def slab(d, k, x, yb, th, col, a, outline=None):
    x *= k; yb *= k; th *= k; w = WS * k; dx = DX * k; dy = DY * k
    front = [(x, yb), (x + w, yb), (x + w, yb - th), (x, yb - th)]
    side = [(x + w, yb), (x + w + dx, yb + dy), (x + w + dx, yb + dy - th), (x + w, yb - th)]
    topf = [(x, yb - th), (x + w, yb - th), (x + w + dx, yb - th + dy), (x + dx, yb - th + dy)]
    d.polygon(side, fill=shade(col, 0.68) + (a,)); d.polygon(front, fill=col + (a,)); d.polygon(topf, fill=shade(col, 1.22) + (a,))
    ol = (outline or shade(col, 1.4)) + (255 if outline else 120,)
    d.line(front + [front[0]], fill=ol, width=2 * k); d.line([front[2], topf[3], topf[2], side[1]], fill=ol, width=2 * k)

CAKE_PANEL = panel(SAFE_W, 470, alpha=228)
_TT = {}
def title(txt, col):
    if (txt, col) not in _TT: _TT[(txt, col)] = fitw(text_img(txt, FI(30), col + (255,), spacing=1), 660)
    return _TT[(txt, col)]
_LB = {}
def label(txt, col):
    if (txt, col) not in _LB: _LB[(txt, col)] = text_img(txt, FI(23), col + (255,), spacing=1)
    return _LB[(txt, col)]

def cake(t):
    if not (T_CAKE <= t < T_NEG0): return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0))
    out = clamp((T_NEG0 - t) / 0.25); pin_ = eo((t - T_CAKE) / 0.3)
    put(lay, CAKE_PANEL, 540, 1320, alpha=0.95 * pin_ * out, scale=0.96 + 0.04 * pin_)
    second = t >= T_SECOND; peel = eio((t - T_PEEL) / 0.9) if t >= T_PEEL else 0.0
    if peel > 0: ttl = title('ЛАК ОТРЫВАЕТСЯ С ПЛЁНКОЙ', RED)
    elif second: ttl = title('ВТОРИЧНЫЙ ОКРАС', RED)
    elif t >= T_STRONG: ttl = title('ПЛЁНКА СИЛЬНО ЛИПНЕТ К ЛАКУ', GOLD)
    else: ttl = title('ИЗ ЧЕГО СОСТОИТ ПОКРЫТИЕ', GOLD)
    put(lay, ttl, 540, 1128, alpha=pin_ * out)
    K = 2
    base = Image.new('RGBA', (WD * K, HT * K), (0, 0, 0, 0)); bd = ImageDraw.Draw(base)
    stack = Image.new('RGBA', (WD * K, HT * K), (0, 0, 0, 0)); sd = ImageDraw.Draw(stack)
    yb = Y0; ys = []
    for i, (nm, col, a, th) in enumerate(LAYERS):
        p = eo((t - (T_CAKE + 0.3 + i * 0.3)) / 0.4)
        if p <= 0: ys.append(None); yb -= th; continue
        c = col; ol = None
        if nm == 'КРАСКА' and second: c = (46, 26, 26); ol = RED
        slab(bd if i < 2 else sd, K, X0, yb - (1 - p) * 110, th, c, int(a * p), outline=ol)
        ys.append((yb - th / 2 - (1 - p) * 110, p)); yb -= th
    if peel > 0:
        cut = X0 + WS * 0.42
        mask = Image.new('L', stack.size, 0); md = ImageDraw.Draw(mask)
        zz = [(cut * K, 0)]; rnd = random.Random(7)
        for y in range(1280, 1520, 12):
            zz.append(((cut + rnd.uniform(-9, 9)) * K, y * K))
        zz += [(cut * K, HT * K), (WD * K, HT * K), (WD * K, 0)]
        md.polygon(zz, fill=255)
        right = Image.new('RGBA', stack.size, (0, 0, 0, 0)); right.paste(stack, (0, 0), mask)
        left = stack.copy(); la = np.asarray(left.split()[3]).copy(); la[np.asarray(mask) > 0] = 0
        left.putalpha(Image.fromarray(la))
        piv = (cut * K, (Y0 - 70) * K)
        right = right.rotate(-24 * peel, resample=Image.BICUBIC, center=piv, translate=(14 * peel * K, -55 * peel * K))
        base.alpha_composite(left); base.alpha_composite(right)
        if peel > 0.3:
            ImageDraw.Draw(base).line([((cut + 4) * K, (Y0 - 70) * K), ((cut + 32) * K, (Y0 - 86) * K)],
                                      fill=RED + (int(255 * peel),), width=4 * K)
    else:
        base.alpha_composite(stack)
    base = base.resize((WD, HT), Image.LANCZOS)
    if out < 1 or pin_ < 1:
        base.putalpha(base.split()[3].point(lambda v: int(v * out * pin_)))
    lay.alpha_composite(base)
    lx = X0 + WS + DX + 14
    for i, (nm, col, a, th) in enumerate(LAYERS):
        if ys[i] is None: continue
        y, p = ys[i]; txt, c = nm, WHITE
        if nm == 'КРАСКА' and second: txt, c = 'ПЕРЕКРАС', RED
        if nm == 'ПЛЁНКА' and T_STRONG <= t: c = GOLD
        im = label(txt, c)
        put(lay, im, lx + im.width / 2, y + DY / 2 - (6 if i == 4 else 0) + (3 if i == 3 else 0), alpha=p * out)
    if T_STRONG <= t < T_SECOND + 0.6 and ys[4]:
        pulse = 0.5 + 0.5 * math.sin((t - T_STRONG) * 9)
        g = Image.new('RGBA', (WD, HT), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        yl = Y0 - sum(l[3] for l in LAYERS[:4])
        gd.line([(X0, yl), (X0 + WS, yl), (X0 + WS + DX, yl + DY)], fill=GOLD2 + (int(255 * (0.4 + 0.6 * pulse)),), width=6)
        g = g.filter(ImageFilter.GaussianBlur(3)); g.putalpha(g.split()[3].point(lambda v: int(v * out)))
        lay.alpha_composite(g)
    return lay

# ---------- 3. «элемент испорчен» ----------
STAMP = circle_icon(70, ring=RED, inner=ic_cross(RED + (255,)), sc=0.75)
def _st():
    tx = text_img("ЭЛЕМЕНТ ИСПОРЧЕН", FO(54), WHITE + (255,), spacing=2)
    p = pill(tx.width + 80, tx.height + 40, DARK, 215, outline=RED); p.alpha_composite(tx, (40, 20)); return p
STAMP_T = _st()
def stamp(t):
    a, b = T_NEGOD - 0.15, T_Q
    al = fade(t, a, b, 0.18, 0.2)
    if al <= 0: return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0)); p = eo((t - a) / 0.25)
    put(lay, STAMP, 540, 1220, alpha=al, scale=1.15 - 0.15 * p)
    put(lay, STAMP_T, 540, 1350, alpha=al * eo((t - a - 0.1) / 0.25))
    return lay

# ---------- плашки ----------
def plate2(l1, l2, c2=GOLD):
    t1 = fitw(text_img(l1, FI(32), WHITE + (255,), spacing=1), 640)
    t2 = fitw(text_img(l2, FO(64), c2 + (255,), spacing=2), 640)
    w = min(SAFE_W, max(t1.width, t2.width) + 80); h = 36 + t1.height + 18 + t2.height + 34
    p = panel(w, h)
    p.alpha_composite(t1, ((w - t1.width) // 2, 34)); p.alpha_composite(t2, ((w - t2.width) // 2, 34 + t1.height + 18))
    return p
PL_Q = plate2("КТО НЕСЁТ", "ОТВЕТСТВЕННОСТЬ?")
PL_GAR = plate2("ДЕТЕЙЛИНГ НЕ ОТВЕЧАЕТ", "ЗА СНЯТИЕ ПЛЁНКИ")
def show_plate(t, im, a, b, y=1290):
    al = fade(t, a, b, 0.22, 0.2)
    if al <= 0: return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0)); p = eo((t - a) / 0.25)
    put(lay, im, 540, y + 20 * (1 - p), alpha=al, scale=0.95 + 0.05 * p)
    return lay

# ---------- 4. оригинал vs перекрас на капоте ----------
SEAM = [(0.0, (270, 0), (1080, 1642)), (1.0, (227, 0), (994, 1920)),
        (2.0, (302, 0), (648, 1920)), (3.0, (410, 0), (540, 1920))]   # шов крыло/капот по кадрам
def seam_at(tl):
    tl = clamp(tl, 0, 3.0)
    for (t0, a0, b0), (t1, a1, b1) in zip(SEAM, SEAM[1:]):
        if t0 <= tl <= t1:
            k = eio((tl - t0) / (t1 - t0))
            lerp = lambda p, q: (p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k)
            return lerp(a0, a1), lerp(b0, b1)
    return SEAM[-1][1], SEAM[-1][2]
def seam_x(a, b, y): return a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1])
def tagpill(l1, l2, col, icon):
    t1 = text_img(l1, FO(46), col + (255,), spacing=2); t2 = text_img(l2, FI(20), WHITE + (255,), spacing=1)
    ck = circle_icon(24, ring=col, fill=col, inner=icon, alpha=255, sc=0.55)
    w = max(t1.width, t2.width) + ck.width + 52; h = t1.height + t2.height + 40
    p = panel(w, h, border=col, alpha=210, r=20)
    p.alpha_composite(ck, (16, (h - ck.height) // 2)); x = 16 + ck.width + 14
    p.alpha_composite(t1, (x, 14)); p.alpha_composite(t2, (x, 14 + t1.height + 10))
    return p
TAG_OR = tagpill("ОРИГИНАЛ", "ЗАВОДСКОЙ БЛЕСК", GOLD, ic_check())
TAG_RE = tagpill("ПЕРЕКРАС", "ГЛЯНЕЦ БЕЗ БЛЕСКА", RED, ic_cross(DARK + (255,)))
def compare(t):
    if not (T_CMP0 <= t < T_CMP1): return None
    tl = t - T_CMP0; out = clamp((T_CMP1 - t) / 0.2)
    a, b = seam_at(tl)
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0))
    # блик по оригинальному (левому) элементу
    g = (tl % 1.6) / 1.6
    yy, xx = np.mgrid[0:HT:2, 0:WD:2]
    sx = a[0] + (b[0] - a[0]) * (yy - a[1]) / (b[1] - a[1])
    left = (xx < sx - 6).astype(np.float32)
    band = np.exp(-((xx - 0.6 * yy - (-1200 + g * 2600)) / 70.0) ** 2) * 0.45 * left * clamp(tl / 0.3) * out
    gl = np.zeros((HT // 2, WD // 2, 4), np.uint8); gl[..., :3] = 255; gl[..., 3] = (band * 255).astype(np.uint8)
    lay.alpha_composite(Image.fromarray(gl, 'RGBA').resize((WD, HT), Image.BILINEAR))
    # пунктир по шву
    p = eo(tl / 0.5); d = ImageDraw.Draw(lay)
    L = math.hypot(b[0] - a[0], b[1] - a[1]); n = int(L / 34)
    for i in range(int(n * p)):
        u0, u1 = i / n, (i + 0.55) / n
        d.line([(a[0] + (b[0] - a[0]) * u0, a[1] + (b[1] - a[1]) * u0), (a[0] + (b[0] - a[0]) * u1, a[1] + (b[1] - a[1]) * u1)],
               fill=WHITE + (int(230 * out),), width=5)
    y = 1180; xs = seam_x(a, b, y)
    q1 = eo((tl - 0.25) / 0.3); q2 = eo((tl - 0.6) / 0.3)
    xl = clamp(xs - TAG_OR.width / 2 - 30, 110 + TAG_OR.width / 2, 970 - TAG_OR.width / 2)
    xr = clamp(xs + TAG_RE.width / 2 + 30, 110 + TAG_RE.width / 2, 970 - TAG_RE.width / 2)
    if xr - xl < (TAG_OR.width + TAG_RE.width) / 2 + 10:      # шов у края — ставим метки друг под другом
        put(lay, TAG_OR, 540, 1120 + 20 * (1 - q1), alpha=q1 * out)
        put(lay, TAG_RE, 540, 1280 + 20 * (1 - q2), alpha=q2 * out)
    else:
        put(lay, TAG_OR, xl, y + 20 * (1 - q1), alpha=q1 * out)
        put(lay, TAG_RE, xr, y + 160 + 20 * (1 - q2), alpha=q2 * out)
    return lay

# ---------- 5. где / за сколько / как ----------
ICONS3 = [(circle_icon(64, inner=ic_pin(GOLD + (255,)), sc=0.7), "ГДЕ?", T_WHERE),
          (circle_icon(64, inner=ic_tag(GOLD + (255,)), sc=0.7), "ЗА СКОЛЬКО?", T_PRICE),
          (circle_icon(64, inner=ic_spray(GOLD + (255,)), sc=0.7), "КАК?", T_HOW)]
ICONS3 = [(a, text_img(b, FI(26), WHITE + (255,), spacing=1, shadow=(3, 6, 170)), c) for a, b, c in ICONS3]
def icons3(t):
    end = T_PO1
    if not (T_WHERE - 0.1 <= t < end): return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0)); out = clamp((end - t) / 0.2)
    for i, (ic, lb, t0) in enumerate(ICONS3):
        p = eo((t - t0 + 0.05) / 0.25)
        if p <= 0: continue
        x = 310 + i * 230
        put(lay, ic, x, 1260 + 24 * (1 - p), alpha=p * out, scale=0.85 + 0.15 * p)
        put(lay, lb, x, 1360 + 24 * (1 - p), alpha=p * out)
    return lay

# ---------- 6. все детейлеры так же / заводской лак ----------
def chip_check(txt, fs=28):
    tx = fitw(text_img(txt, FI(fs), WHITE + (255,), spacing=1), SAFE_W - 120)
    w = tx.width + 110; h = 84
    p = pill(w, h, DARK, 215, outline=GOLD)
    ck = circle_icon(26, ring=GOLD, fill=GOLD, inner=ic_check(), alpha=255, sc=0.6)
    p.alpha_composite(ck, (14, (h - ck.height) // 2)); p.alpha_composite(tx, (84, (h - tx.height) // 2))
    return p
CHIP_ALL = chip_check("ВСЕ ДЕТЕЙЛЕРЫ ДЕЛАЮТ ТАК ЖЕ")
def badge_factory():
    t1 = text_img("ЗАВОДСКОЙ ЛАК", FO(72), WHITE + (255,), spacing=2)
    t2 = text_img("ЛУЧШЕЕ ВРЕМЯ ДЛЯ ОКЛЕЙКИ", FI(24), GOLD + (255,), spacing=1)
    ck = circle_icon(44, ring=GOLD, fill=GOLD, inner=ic_check(), alpha=255, sc=0.95)
    w = min(SAFE_W, max(t1.width, t2.width) + ck.width + 90); h = 180
    p = panel(w, h)
    p.alpha_composite(ck, (28, (h - ck.height) // 2)); x = 28 + ck.width + 26
    p.alpha_composite(t1, (x, 34)); p.alpha_composite(t2, (x, 34 + t1.height + 18))
    return p
BADGE = badge_factory()

# ---------- 7. таймлайн ----------
TL_NODES = [("СКОЛ", ic_chip, T_SKOL), ("КОРРОЗИЯ", ic_rust, T_KOR),
            ("ПЕРЕКРАС", ic_spray, T_PEREK), ("ОКЛЕЙКА", ic_shield, T_KLE)]
TLX = [270, 450, 630, 810]; TLY = 1260
TL_PANEL = panel(SAFE_W, 270)
TL_OFF = [circle_icon(46, ring=(110, 110, 110), inner=f((150, 150, 150, 255)), sc=0.7) for _, f, _ in TL_NODES]
TL_ON = [circle_icon(46, ring=(RED if i < 3 else GOLD), sc=0.7,
                     inner=f(((210, 90, 60, 255) if i == 1 else (RED + (255,)) if i < 3 else (GOLD + (255,)))))
         for i, (_, f, _) in enumerate(TL_NODES)]
TL_LBL = [(text_img(n, FI(22), (160, 160, 160, 255), spacing=1), text_img(n, FI(22), (RED if i < 3 else GOLD) + (255,), spacing=1))
          for i, (n, _, _) in enumerate(TL_NODES)]
SRAZU = chip_check("ЛУЧШЕ — СРАЗУ", 30)
def timeline(t):
    a, b = T_NE, T_PRI
    if not (a <= t < b): return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0)); out = clamp((b - t) / 0.25); pin_ = eo((t - a) / 0.3)
    put(lay, TL_PANEL, 540, 1290, alpha=0.95 * pin_ * out)
    d = ImageDraw.Draw(lay)
    d.line([(TLX[0], TLY), (TLX[-1], TLY)], fill=(90, 90, 90, int(220 * pin_ * out)), width=5)
    for i in range(1, 4):
        p = eo((t - TL_NODES[i][2] + 0.1) / 0.35)
        if p > 0:
            d.line([(TLX[i - 1], TLY), (TLX[i - 1] + (TLX[i] - TLX[i - 1]) * p, TLY)], fill=(RED if i < 3 else GOLD) + (int(255 * out),), width=6)
    for i, (nm, f, t0) in enumerate(TL_NODES):
        p = eo((t - t0 + 0.05) / 0.25)
        put(lay, TL_OFF[i], TLX[i], TLY, alpha=pin_ * out * (1 - p))
        if p > 0: put(lay, TL_ON[i], TLX[i], TLY, alpha=p * out, scale=1.12 - 0.12 * p)
        put(lay, TL_LBL[i][0], TLX[i], TLY + 78, alpha=pin_ * out * (1 - p))
        if p > 0: put(lay, TL_LBL[i][1], TLX[i], TLY + 78, alpha=p * out)
    if t >= T_LUCH:
        p = eo((t - T_LUCH) / 0.3)
        put(lay, SRAZU, 540, 1490 + 16 * (1 - p), alpha=p * out)
    return lay

# ---------- 8. финал (компактный, в безопасной зоне) ----------
def logo_img(size=330):
    im = Image.open(f"{R0}/brand/logo.png").convert('RGBA')
    m = Image.new('L', (im.width * 2, im.height * 2), 0)
    ImageDraw.Draw(m).ellipse((40, 40, im.width * 2 - 40, im.height * 2 - 40), fill=255)
    im.putalpha(m.resize(im.size, Image.LANCZOS)); im = im.resize((size, size), Image.LANCZOS)
    ring = hires(size + 30, size + 30, lambda d, k: d.ellipse((3 * k, 3 * k, (size + 27) * k, (size + 27) * k), outline=GOLD + (255,), width=4 * k))
    ring.alpha_composite(im, (15, 15)); return ring
LOGO = logo_img()
E1 = text_img("ЗАВОДСКОЙ ЛАК?", FO(84), WHITE + (255,), spacing=2, shadow=(4, 8, 150))
E2 = text_img("КЛЕИМ СРАЗУ", FO(84), GOLD + (255,), spacing=2, shadow=(4, 8, 150))
def cta():
    tx = text_img("ПИШИТЕ В DIRECT", FO(50), DARK + (255,), spacing=2)
    p = pill(tx.width + 90, 96, GOLD, 255); p.alpha_composite(tx, (45, (96 - tx.height) // 2)); return p
E3 = cta()
E4 = text_img("ПР-Т ДЗЕРЖИНСКОГО, 82А", FI(34), WHITE + (255,), spacing=1, shadow=(3, 6, 170))
E5 = text_img("МИНСК · 9:00–21:00 · БЕЗ ВЫХОДНЫХ", FI(24), (215, 215, 215, 255), spacing=1, shadow=(3, 6, 170))
PIN = hires(42, 56, lambda d, k: (d.ellipse((4 * k, 3 * k, 38 * k, 37 * k), fill=GOLD + (255,)),
                                  d.polygon([(7 * k, 28 * k), (35 * k, 28 * k), (21 * k, 55 * k)], fill=GOLD + (255,)),
                                  d.ellipse((14 * k, 13 * k, 28 * k, 27 * k), fill=DARK + (255,))))
def endcard(t):
    a = VOICE_END
    if t < a: return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, int(150 * eo((t - a) / 0.35))))
    p = eo((t - a - 0.05) / 0.45); lg = LOGO
    g = (t - a - 0.8) / 0.7
    if 0 < g < 1:
        lg = LOGO.copy(); sh = Image.new('RGBA', lg.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        x = -150 + g * (lg.width + 300)
        sd.polygon([(x, 0), (x + 50, 0), (x - 100, lg.height), (x - 150, lg.height)], fill=(255, 255, 255, 120))
        sh = sh.filter(ImageFilter.GaussianBlur(14))
        sh.putalpha(Image.fromarray(np.minimum(np.asarray(sh.split()[3]), np.asarray(lg.split()[3]))))
        lg.alpha_composite(sh)
    put(lay, lg, 540, 620, alpha=p, scale=0.9 + 0.1 * p)
    for im, y, d0 in [(E1, 910, 0.35), (E2, 1010, 0.5), (E3, 1150, 0.7), (E4, 1270, 0.9), (E5, 1330, 1.0)]:
        q = eo((t - a - d0) / 0.35)
        if im is E4:
            put(lay, PIN, 540 - E4.width / 2 - 28, y, alpha=q); put(lay, im, 540 + 14, y + 16 * (1 - q), alpha=q)
        else:
            put(lay, im, 540, y + 16 * (1 - q), alpha=q, scale=(0.92 + 0.08 * q) if im is E3 else 1.0)
    return lay

# ---------- main ----------
ELEMS = [cake, stamp, compare, icons3, timeline, endcard,
         lambda t: show_plate(t, PL_Q, T_Q - 0.05, MEME_AT + MEME + 0.3),
         lambda t: show_plate(t, PL_GAR, T_DET3 + 0.1, T_OTHER - 0.05),
         lambda t: show_plate(t, CHIP_ALL, T_OTHER + 0.1, T_PO2 - 0.05),
         lambda t: show_plate(t, BADGE, T_NEW + 0.1, T_NE - 0.05)]

def main():
    part = None
    if len(sys.argv) > 1 and sys.argv[1] == '--part':
        part = (int(sys.argv[2]), int(sys.argv[3])); only = []
    else:
        only = [float(x) for x in sys.argv[1:]]      # превью: python3 gfx.py 12.0 20.5
    nfr = int(round(TOTAL * FPS))
    f0, f1 = 0, nfr
    if part: f0 = nfr * part[0] // part[1]; f1 = nfr * (part[0] + 1) // part[1]
    frames = [int(round(x * FPS)) for x in only] if only else range(f0, f1)
    outp = f'{OUT}/gfx_part{part[0]}.mp4' if part else f'{OUT}/video_gfx.mp4'
    if not only:
        enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WD}x{HT}',
                                '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
                                '-pix_fmt', 'yuv420p', outp], stdin=subprocess.PIPE)
        dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{f0 / FPS:.4f}', '-i', f'{OUT}/video_raw.mp4',
                                '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    last = None
    for fi in frames:
        t = fi / FPS
        if only:
            fr = np.frombuffer(subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', f'{OUT}/video_raw.mp4',
                                                        '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']), np.uint8).reshape(HT, WD, 3)
        else:
            b = dec.stdout.read(WD * HT * 3)
            fr = last if len(b) < WD * HT * 3 else np.frombuffer(b, np.uint8).reshape(HT, WD, 3)
            last = fr
        lays = [x for x in [behind(fi, t)] + [e(t) for e in ELEMS] if x is not None]
        if lays:
            ov = lays[0]
            for l in lays[1:]: ov.alpha_composite(l)
            o = np.asarray(ov, np.float32); a = o[..., 3:4] / 255
            fr = (fr.astype(np.float32) * (1 - a) + o[..., :3] * a).astype(np.uint8)
        if only:
            Image.fromarray(fr).save(f'{OUT}/prev_{t:05.2f}.jpg', quality=88)
        else:
            enc.stdin.write(fr.tobytes())
            if fi % 150 == 0: print('frame', fi, '/', f1, flush=True)
    if not only:
        enc.stdin.close(); enc.wait(); dec.kill()
    print('done')

if __name__ == '__main__':
    main()
