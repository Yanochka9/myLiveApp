# Графика рилса: текст за спиной, «пирог» ЛКП с отрывом лака, мем, иконки, таймлайн, финал.
# Читает out/video_raw.mp4, пишет out/video_gfx.mp4 (субтитры — в finish.py).
import numpy as np, subprocess, math, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from tl import *

WD, HT, FPS = 1080, 1920, 30
FA = f"{R0}/../assets/fonts"
def FO(s): return ImageFont.truetype(f"{FA}/Oswald-Bold.ttf", s)
def FM(s): return ImageFont.truetype(f"{FA}/Montserrat-ExtraBold.ttf", s)
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
        bb = tmp.textbbox((0, 0), txt, font=font, stroke_width=stroke); w = bb[2]
    asc, desc = font.getmetrics()
    pad = 30
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
    k = maxw / im.width
    return im.resize((maxw, int(im.height * k)), Image.LANCZOS)

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

def panel(w, h, border=GOLD, alpha=185, r=30):
    def fn(d, k):
        d.rounded_rectangle((3 * k, 3 * k, (w - 3) * k, (h - 3) * k), r * k, fill=DARK + (alpha,), outline=border + (255,), width=3 * k)
    return hires(w, h, fn)

def pill(w, h, fill, alpha=230, outline=None):
    def fn(d, k):
        d.rounded_rectangle((2 * k, 2 * k, (w - 2) * k, (h - 2) * k), h * k // 2, fill=fill + (alpha,),
                            outline=(outline + (255,)) if outline else None, width=3 * k)
    return hires(w, h, fn)

def circle_icon(r, ring=GOLD, fill=DARK, inner=None, alpha=215):
    s = 2 * r + 8
    def fn(d, k):
        d.ellipse((4 * k, 4 * k, (s - 4) * k, (s - 4) * k), fill=fill + (alpha,), outline=ring + (255,), width=4 * k)
        if inner: inner(d, k, s / 2)
    return hires(s, s, fn)

# ---------- icons (draw in k-scaled coords around centre c) ----------
def ic_pin(col):
    def f(d, k, c):
        c *= k; r = 30 * k
        d.ellipse((c - r, c - r - 14 * k, c + r, c + r - 14 * k), fill=col)
        d.polygon([(c - r * 0.86, c - 14 * k + r * 0.5), (c + r * 0.86, c - 14 * k + r * 0.5), (c, c + 46 * k)], fill=col)
        d.ellipse((c - 11 * k, c - 25 * k, c + 11 * k, c - 3 * k), fill=DARK)
    return f
def ic_tag(col):
    def f(d, k, c):
        c *= k
        pts = [(-38, -22), (18, -22), (42, 0), (18, 22), (-38, 22)]
        ang = math.radians(-30)
        P = [(c + (x * math.cos(ang) - y * math.sin(ang)) * k, c + (x * math.sin(ang) + y * math.cos(ang)) * k) for x, y in pts]
        d.polygon(P, fill=col)
        hx, hy = 22, 0; X = c + (hx * math.cos(ang) - hy * math.sin(ang)) * k; Y = c + (hx * math.sin(ang) + hy * math.cos(ang)) * k
        d.ellipse((X - 6 * k, Y - 6 * k, X + 6 * k, Y + 6 * k), fill=DARK)
        fnt = FO(40 * k); d.text((c - 8 * k, c + 2 * k), "?", font=fnt, fill=DARK, anchor='mm')
    return f
def ic_spray(col):
    def f(d, k, c):
        c *= k
        d.rounded_rectangle((c - 20 * k, c - 18 * k, c + 20 * k, c + 44 * k), 8 * k, fill=col)   # баллон
        d.rectangle((c - 9 * k, c - 30 * k, c + 9 * k, c - 18 * k), fill=col)                     # колпачок
        d.rectangle((c - 3 * k, c - 36 * k, c + 14 * k, c - 30 * k), fill=col)                    # сопло
        for i, (dx, dy) in enumerate([(26, -40), (34, -30), (30, -50), (40, -42), (22, -54)]):
            d.ellipse((c + dx * k - 3 * k, c + dy * k - 3 * k, c + dx * k + 3 * k, c + dy * k + 3 * k), fill=col)
    return f
def ic_chip(col):
    def f(d, k, c):
        c *= k; P = []
        for i in range(14):
            r = (40 if i % 2 == 0 else 16) * k * (0.8 + 0.25 * ((i * 7) % 3) / 2)
            a = i / 14 * 2 * math.pi
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
        d.line([(c - 15 * k, c), (c - 3 * k, c + 13 * k), (c + 18 * k, c - 14 * k)], fill=DARK, width=8 * k)
    return f
def ic_check(col=DARK):
    def f(d, k, c):
        c *= k
        d.line([(c - 22 * k, c + 2 * k), (c - 6 * k, c + 18 * k), (c + 24 * k, c - 16 * k)], fill=col, width=11 * k, joint='curve')
    return f
def ic_cross(col):
    def f(d, k, c):
        c *= k; a = 42 * k
        d.line([(c - a, c - a), (c + a, c + a)], fill=col, width=16 * k)
        d.line([(c - a, c + a), (c + a, c - a)], fill=col, width=16 * k)
    return f

# ---------- times ----------
T_BR1 = word('2509', 'самый')
T_CAKE = word('2509', 'полиуретановые')
T_STRONG = word('2509', 'сильно')
T_SECOND = word('2509', 'авторичном')
T_PEEL = word('2509', 'подорвать', after=26.0)
T_NEG0 = word('2509', 'и', after=28.0)
T_NEGOD = word('2509', 'негодность')
T_Q = word('2509', 'несет')
T_WHERE = word('2509', 'где'); T_PRICE = word('2509', 'стоимость'); T_HOW = word('2509', 'как', after=37.0)
T_PO1 = word('2509', 'поэтому'); T_RANEE = word('2509', 'ранее'); T_ZAV = word('2509', 'заводского')
T_DET3 = word('2509', 'детейлинг', 3); T_OTHER = word('2509', 'другие')
T_PO2 = word('2510', 'поэтому'); T_NEW = word('2510', 'новый'); T_ZAVK = word('2510', 'заводской')
T_NE = word('2510', 'не'); T_SKOL = word('2510', 'скола'); T_KOR = word('2510', 'коррозия')
T_PEREK = word('2510', 'перекрашивали'); T_KLE = word('2510', 'клеиться'); T_LUCH = word('2510', 'лучше')
T_PRI = word('2509', 'приезжайте', 2)
print({k: round(v, 2) for k, v in globals().items() if k.startswith('T_')})

# ---------- 1. текст за спиной ----------
MATTE = np.load(f"{OUT}/matte.npy")
BT1 = fitw(text_img("ВТОРИЧНЫЙ", FO(250), (30, 30, 34, 235), spacing=6, shadow=(6, 10, 90)), 1000)
BT2 = fitw(text_img("ОКРАС?", FO(330), GOLD + (255,), spacing=8, shadow=(6, 12, 120)), 900)
def behind(fi, t):
    if t >= T_BR1 or fi >= len(MATTE): return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0))
    p1 = eo((t - 0.2) / 0.55); p2 = eo((t - 0.45) / 0.6); out = clamp((T_BR1 - t) / 0.2)
    put(lay, BT1, 540, 330 + 40 * (1 - p1), alpha=p1 * out, scale=0.94 + 0.06 * p1)
    put(lay, BT2, 540, 600 + 50 * (1 - p2), alpha=p2 * out, scale=0.92 + 0.08 * p2)
    m = Image.fromarray(MATTE[fi]).resize((WD, HT), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2))
    a = np.asarray(lay.split()[3], np.float32) * (1 - np.asarray(m, np.float32) / 255)
    lay.putalpha(Image.fromarray(a.astype(np.uint8)))
    return lay

# ---------- 2. «пирог» ЛКП ----------
X0, Y0, WS = 170, 1660, 500          # передний левый нижний угол, ширина плиты
DX, DY = 150, -86                    # глубина (изометрия)
LAYERS = [('МЕТАЛЛ', (150, 156, 164), 255, 54), ('ГРУНТ', (196, 190, 178), 255, 40),
          ('КРАСКА', (24, 24, 30), 255, 48), ('ЛАК', (190, 215, 235), 130, 36), ('ПЛЁНКА', (255, 238, 180), 85, 36)]
def shade(c, f): return tuple(int(clamp(v * f, 0, 255)) for v in c)
def slab(d, k, x, yb, th, col, a, outline=None, top=True):
    x *= k; yb *= k; th *= k; w = WS * k; dx = DX * k; dy = DY * k
    front = [(x, yb), (x + w, yb), (x + w, yb - th), (x, yb - th)]
    side = [(x + w, yb), (x + w + dx, yb + dy), (x + w + dx, yb + dy - th), (x + w, yb - th)]
    topf = [(x, yb - th), (x + w, yb - th), (x + w + dx, yb - th + dy), (x + dx, yb - th + dy)]
    d.polygon(side, fill=shade(col, 0.68) + (a,))
    d.polygon(front, fill=col + (a,))
    if top: d.polygon(topf, fill=shade(col, 1.22) + (a,))
    ol = (outline or shade(col, 1.4)) + (255 if outline else 120,)
    d.line(front + [front[0]], fill=ol, width=2 * k)
    d.line([front[2], topf[3], topf[2], side[1]], fill=ol, width=2 * k) if top else None

CAKE_PANEL = panel(960, 600, alpha=228)
TITLES = {}
def title(txt, col):
    key = (txt, col)
    if key not in TITLES: TITLES[key] = text_img(txt, FM(40), col + (255,), spacing=2)
    return TITLES[key]
LBL = {}
def label(txt, col):
    key = (txt, col)
    if key not in LBL: LBL[key] = text_img(txt, FM(32), col + (255,), spacing=1)
    return LBL[key]

def cake(t):
    if not (T_CAKE <= t < T_NEG0): return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0))
    out = clamp((T_NEG0 - t) / 0.25); pin_ = eo((t - T_CAKE) / 0.3)
    put(lay, CAKE_PANEL, 540, 1440, alpha=0.95 * pin_ * out, scale=0.96 + 0.04 * pin_)
    second = t >= T_SECOND; peel = eio((t - T_PEEL) / 0.9) if t >= T_PEEL else 0.0
    # заголовок
    if peel > 0: ttl = title('ЛАК ОТРЫВАЕТСЯ С ПЛЁНКОЙ', RED)
    elif second: ttl = title('ВТОРИЧНЫЙ ОКРАС', RED)
    elif t >= T_STRONG: ttl = title('ПЛЁНКА СИЛЬНО ЛИПНЕТ К ЛАКУ', GOLD)
    else: ttl = title('ИЗ ЧЕГО СОСТОИТ ПОКРЫТИЕ', GOLD)
    put(lay, ttl, 540, 1192, alpha=pin_ * out)
    # слои
    K = 2
    base = Image.new('RGBA', (WD * K, HT * K), (0, 0, 0, 0)); bd = ImageDraw.Draw(base)
    stack = Image.new('RGBA', (WD * K, HT * K), (0, 0, 0, 0)); sd = ImageDraw.Draw(stack)
    yb = Y0; ys = []
    for i, (nm, col, a, th) in enumerate(LAYERS):
        p = eo((t - (T_CAKE + 0.3 + i * 0.3)) / 0.4)
        if p <= 0: ys.append(None); yb -= th; continue
        c = col; ol = None
        if nm == 'КРАСКА' and second: c = (46, 26, 26); ol = RED
        dd = bd if i < 2 else sd
        slab(dd, K, X0, yb - (1 - p) * 140, th, c, int(a * p), outline=ol)
        ys.append((yb - th / 2 - (1 - p) * 140, p)); yb -= th
    # отрыв: правая часть «краска+лак+плёнка» поднимается с рваным краем
    if peel > 0:
        cut = X0 + WS * 0.42
        mask = Image.new('L', stack.size, 0); md = ImageDraw.Draw(mask)
        zz = [(cut * K, 0)]
        rnd = random.Random(7)
        for y in range(1300, 1700, 14):
            zz.append(((cut + rnd.uniform(-12, 12)) * K, y * K))
        zz += [(cut * K, HT * K), (WD * K, HT * K), (WD * K, 0)]
        md.polygon(zz, fill=255)
        right = Image.new('RGBA', stack.size, (0, 0, 0, 0)); right.paste(stack, (0, 0), mask)
        left = stack.copy(); la = np.asarray(left.split()[3]).copy(); la[np.asarray(mask) > 0] = 0
        left.putalpha(Image.fromarray(la))
        piv = (cut * K, (Y0 - 94) * K)
        right = right.rotate(-26 * peel, resample=Image.BICUBIC, center=piv,
                             translate=(18 * peel * K, -70 * peel * K))
        base.alpha_composite(left); base.alpha_composite(right)
        # красная трещина на грунте
        if peel > 0.3:
            bd2 = ImageDraw.Draw(base)
            bd2.line([((cut + 4) * K, (Y0 - 94) * K), ((cut + 40) * K, (Y0 - 94 - 20) * K)], fill=RED + (int(255 * peel),), width=5 * K)
    else:
        base.alpha_composite(stack)
    base = base.resize((WD, HT), Image.LANCZOS)
    if out < 1 or pin_ < 1:
        a = base.split()[3].point(lambda v: int(v * out * pin_)); base.putalpha(a)
    lay.alpha_composite(base)
    # подписи справа
    lx = X0 + WS + DX + 18
    for i, (nm, col, a, th) in enumerate(LAYERS):
        if ys[i] is None: continue
        y, p = ys[i]
        txt, c = nm, WHITE
        if nm == 'КРАСКА' and second: txt, c = 'ПЕРЕКРАС', RED
        if nm == 'ПЛЁНКА' and T_STRONG <= t: c = GOLD
        im = label(txt, c)
        put(lay, im, lx + im.width / 2, y + DY / 2 - (10 if i == 4 else 0) + (4 if i == 3 else 0), alpha=p * out)
    # пульс сцепления между лаком и плёнкой
    if T_STRONG <= t < T_SECOND + 0.6 and ys[4]:
        pulse = 0.5 + 0.5 * math.sin((t - T_STRONG) * 9)
        g = Image.new('RGBA', (WD, HT), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        yl = Y0 - sum(l[3] for l in LAYERS[:4])
        gd.line([(X0, yl), (X0 + WS, yl), (X0 + WS + DX, yl + DY)], fill=GOLD2 + (int(255 * (0.4 + 0.6 * pulse)),), width=7)
        g = g.filter(ImageFilter.GaussianBlur(3))
        a = g.split()[3].point(lambda v: int(v * out)); g.putalpha(a)
        lay.alpha_composite(g)
    return lay

# ---------- 3. «элемент испорчен» ----------
STAMP = circle_icon(100, ring=RED, inner=ic_cross(RED + (255,)))
def _st():
    tx = text_img("ЭЛЕМЕНТ ИСПОРЧЕН", FO(76), WHITE + (255,), spacing=3)
    p = pill(tx.width + 100, tx.height + 50, DARK, 215, outline=RED); p.alpha_composite(tx, (50, 25)); return p
STAMP_T = _st()
def stamp(t):
    a, b = T_NEGOD - 0.15, T_Q
    al = fade(t, a, b, 0.18, 0.2)
    if al <= 0: return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0)); p = eo((t - a) / 0.25)
    put(lay, STAMP, 540, 1300, alpha=al, scale=1.2 - 0.2 * p)
    put(lay, STAMP_T, 540, 1470, alpha=al * eo((t - a - 0.1) / 0.25))
    return lay

# ---------- плашки (тёмная, золотая рамка) ----------
def plate2(l1, l2, c2=GOLD, w=900):
    t1 = text_img(l1, FM(44), WHITE + (255,), spacing=2); t2 = text_img(l2, FO(96), c2 + (255,), spacing=3)
    w = max(w, t1.width + 90, t2.width + 90)
    h = 60 + t1.height + 22 + t2.height + 44
    p = panel(w, h)
    p.alpha_composite(t1, ((w - t1.width) // 2, 52)); p.alpha_composite(t2, ((w - t2.width) // 2, 52 + t1.height + 24))
    return p
PL_Q = plate2("КТО НЕСЁТ", "ОТВЕТСТВЕННОСТЬ?")
PL_RAN = plate2("РАНЕЕ ОКРАШЕННЫЙ ЭЛЕМЕНТ", "НЕ ЗАВОДСКОЙ ОКРАС", c2=RED)
PL_GAR = plate2("ДЕТЕЙЛИНГ НЕ ОТВЕЧАЕТ", "ЗА СНЯТИЕ ПЛЁНКИ")
def show_plate(t, im, a, b, y=1330):
    al = fade(t, a, b, 0.22, 0.2)
    if al <= 0: return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0)); p = eo((t - a) / 0.25)
    put(lay, im, 540, y + 24 * (1 - p), alpha=al, scale=0.95 + 0.05 * p)
    return lay

# ---------- 6. где / за сколько / как ----------
ICONS3 = [(circle_icon(92, inner=ic_pin(GOLD + (255,))), "ГДЕ?", T_WHERE),
          (circle_icon(92, inner=ic_tag(GOLD + (255,))), "ЗА СКОЛЬКО?", T_PRICE),
          (circle_icon(92, inner=ic_spray(GOLD + (255,))), "КАК?", T_HOW)]
ICONS3 = [(a, text_img(b, FM(38), WHITE + (255,), spacing=1, shadow=(3, 6, 170)), c) for a, b, c in ICONS3]
def icons3(t):
    end = T_PO1
    if not (T_WHERE - 0.1 <= t < end): return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0)); out = clamp((end - t) / 0.2)
    for i, (ic, lb, t0) in enumerate(ICONS3):
        p = eo((t - t0 + 0.05) / 0.25)
        if p <= 0: continue
        x = 220 + i * 320
        put(lay, ic, x, 1300 + 30 * (1 - p), alpha=p * out, scale=0.85 + 0.15 * p)
        put(lay, lb, x, 1430 + 30 * (1 - p), alpha=p * out)
    return lay

# ---------- 9. так работают все ----------
def chip_check(txt):
    tx = text_img(txt, FM(40), WHITE + (255,), spacing=1)
    w = tx.width + 150; h = 104
    p = pill(w, h, DARK, 215, outline=GOLD)
    ck = circle_icon(34, ring=GOLD, fill=GOLD, inner=ic_check(), alpha=255)
    p.alpha_composite(ck, (14, (h - ck.height) // 2)); p.alpha_composite(tx, (110, (h - tx.height) // 2))
    return p
CHIP_ALL = chip_check("ТАК РАБОТАЮТ ВСЕ ДЕТЕЙЛИНГИ")

# ---------- 10. заводской лак ----------
def badge_factory():
    t1 = text_img("ЗАВОДСКОЙ ЛАК", FO(104), WHITE + (255,), spacing=3)
    t2 = text_img("ЛУЧШЕЕ ВРЕМЯ ДЛЯ ОКЛЕЙКИ", FM(38), GOLD + (255,), spacing=1)
    ck = circle_icon(62, ring=GOLD, fill=GOLD, inner=ic_check(), alpha=255)
    w = max(t1.width, t2.width) + ck.width + 120; h = 250
    p = panel(w, h)
    p.alpha_composite(ck, (40, (h - ck.height) // 2))
    x = 40 + ck.width + 36
    p.alpha_composite(t1, (x, 48)); p.alpha_composite(t2, (x, 48 + t1.height + 26))
    return p
BADGE = badge_factory()

# ---------- 11. таймлайн скол → коррозия → перекрас → оклейка ----------
TL_NODES = [("СКОЛ", ic_chip, T_SKOL), ("КОРРОЗИЯ", ic_rust, T_KOR),
            ("ПЕРЕКРАС", ic_spray, T_PEREK), ("ОКЛЕЙКА", ic_shield, T_KLE)]
TLX = [165, 395, 625, 855]; TLY = 1300
TL_PANEL = panel(1000, 380)
TL_OFF = [circle_icon(66, ring=(110, 110, 110), inner=f((150, 150, 150, 255))) for _, f, _ in TL_NODES]
TL_ON = [circle_icon(66, ring=(RED if i < 3 else GOLD), inner=f(((210, 90, 60, 255) if i == 1 else (RED + (255,)) if i < 3 else (GOLD + (255,)))))
         for i, (_, f, _) in enumerate(TL_NODES)]
TL_LBL = [(text_img(n, FM(32), (160, 160, 160, 255), spacing=1), text_img(n, FM(32), (RED if i < 3 else GOLD) + (255,), spacing=1))
          for i, (n, _, _) in enumerate(TL_NODES)]
SRAZU = chip_check("ЛУЧШЕ — СРАЗУ")
def timeline(t):
    a, b = T_NE, T_PRI
    if not (a <= t < b): return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, 0)); out = clamp((b - t) / 0.25); pin_ = eo((t - a) / 0.3)
    put(lay, TL_PANEL, 540, 1350, alpha=0.95 * pin_ * out)
    d = ImageDraw.Draw(lay)
    d.line([(TLX[0], TLY), (TLX[-1], TLY)], fill=(90, 90, 90, int(220 * pin_ * out)), width=6)
    for i in range(1, 4):
        p = eo((t - TL_NODES[i][2] + 0.1) / 0.35)
        if p > 0:
            x1 = TLX[i - 1] + (TLX[i] - TLX[i - 1]) * p
            d.line([(TLX[i - 1], TLY), (x1, TLY)], fill=(RED if i < 3 else GOLD) + (int(255 * out),), width=8)
    for i, (nm, f, t0) in enumerate(TL_NODES):
        p = eo((t - t0 + 0.05) / 0.25)
        put(lay, TL_OFF[i], TLX[i], TLY, alpha=pin_ * out * (1 - p))
        if p > 0: put(lay, TL_ON[i], TLX[i], TLY, alpha=p * out, scale=1.12 - 0.12 * p)
        put(lay, TL_LBL[i][0], TLX[i], TLY + 108, alpha=pin_ * out * (1 - p))
        if p > 0: put(lay, TL_LBL[i][1], TLX[i], TLY + 108, alpha=p * out)
    if t >= T_LUCH:
        p = eo((t - T_LUCH) / 0.3)
        put(lay, SRAZU, 540, 1610 + 20 * (1 - p), alpha=p * out)
    return lay

# ---------- 12. финал ----------
def logo_img():
    im = Image.open(f"{R0}/brand/logo.png").convert('RGBA')
    m = Image.new('L', (im.width * 2, im.height * 2), 0)
    ImageDraw.Draw(m).ellipse((40, 40, im.width * 2 - 40, im.height * 2 - 40), fill=255)
    im.putalpha(m.resize(im.size, Image.LANCZOS))
    im = im.resize((470, 470), Image.LANCZOS)
    ring = hires(510, 510, lambda d, k: d.ellipse((4 * k, 4 * k, 506 * k, 506 * k), outline=GOLD + (255,), width=6 * k))
    ring.alpha_composite(im, (20, 20))
    return ring
LOGO = logo_img()
E1 = text_img("ЗАВОДСКОЙ ЛАК?", FO(118), WHITE + (255,), spacing=3, shadow=(4, 8, 150))
E2 = text_img("КЛЕИМ СРАЗУ", FO(118), GOLD + (255,), spacing=3, shadow=(4, 8, 150))
def cta():
    tx = text_img("ПИШИТЕ В DIRECT", FO(72), DARK + (255,), spacing=3)
    p = pill(tx.width + 120, 128, GOLD, 255); p.alpha_composite(tx, (60, (128 - tx.height) // 2)); return p
E3 = cta()
E4 = text_img("ПР-Т ДЗЕРЖИНСКОГО, 82А", FM(50), WHITE + (255,), spacing=1, shadow=(3, 6, 170))
E5 = text_img("МИНСК · 9:00–21:00 · БЕЗ ВЫХОДНЫХ", FM(36), (210, 210, 210, 255), spacing=2, shadow=(3, 6, 170))
PIN = hires(60, 80, lambda d, k: ic_pin(GOLD + (255,))(d, k, 40) if False else (
    d.ellipse((6 * k, 4 * k, 54 * k, 52 * k), fill=GOLD + (255,)),
    d.polygon([(10 * k, 40 * k), (50 * k, 40 * k), (30 * k, 78 * k)], fill=GOLD + (255,)),
    d.ellipse((20 * k, 18 * k, 40 * k, 38 * k), fill=DARK + (255,))))
def endcard(t):
    a = VOICE_END
    if t < a: return None
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, int(150 * eo((t - a) / 0.35))))
    p = eo((t - a - 0.05) / 0.45)
    lg = LOGO
    # блик по логотипу
    g = (t - a - 0.8) / 0.7
    if 0 < g < 1:
        lg = LOGO.copy(); sh = Image.new('RGBA', lg.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        x = -200 + g * (lg.width + 400)
        sd.polygon([(x, 0), (x + 70, 0), (x - 130, lg.height), (x - 200, lg.height)], fill=(255, 255, 255, 120))
        sh = sh.filter(ImageFilter.GaussianBlur(18))
        a_ = np.minimum(np.asarray(sh.split()[3]), np.asarray(lg.split()[3])); sh.putalpha(Image.fromarray(a_))
        lg.alpha_composite(sh)
    put(lay, lg, 540, 560, alpha=p, scale=0.9 + 0.1 * p)
    for im, y, d0 in [(E1, 965, 0.35), (E2, 1095, 0.5), (E3, 1265, 0.7), (E4, 1415, 0.9), (E5, 1495, 1.0)]:
        q = eo((t - a - d0) / 0.35)
        if im is E4:
            put(lay, PIN, 540 - E4.width / 2 - 40, y, alpha=q)
            put(lay, im, 540 + 20, y + 20 * (1 - q), alpha=q)
        else:
            put(lay, im, 540, y + 20 * (1 - q), alpha=q, scale=(0.92 + 0.08 * q) if im is E3 else 1.0)
    return lay

# ---------- мем: ч/б, наезд, подпись ----------
M1 = fitw(text_img("МОИ ПОЛНОМОЧИЯ", FO(132), WHITE + (255,), stroke=8, spacing=2), 1000)
M2 = text_img("ВСЁ", FO(260), WHITE + (255,), stroke=10, spacing=4)
VIG = None
def meme_frame(fr, t):
    global VIG
    a = MEME_AT; p = (t - a) / MEME
    g = fr.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    g = np.clip((g - 128) * 1.25 + 120, 0, 255)
    if VIG is None:
        yy, xx = np.mgrid[0:HT, 0:WD]; r = np.sqrt(((xx - 540) / 540) ** 2 + ((yy - 900) / 1100) ** 2)
        VIG = np.clip(1.15 - 0.55 * r ** 2, 0.25, 1).astype(np.float32)
    g = g * VIG + np.random.default_rng(int(t * 30)).normal(0, 7, g.shape)
    im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert('RGB')
    z = 1.03 + 0.06 * eio(p)                       # запас под тряску
    sx = 9 * math.sin(t * 70) if t - a < 0.2 else 0
    w2, h2 = WD / z, HT / z
    bx = clamp((WD - w2) / 2 + sx, 0, WD - w2); by = clamp((HT - h2) * 0.35, 0, HT - h2)
    im = im.resize((WD, HT), Image.BICUBIC, box=(bx, by, bx + w2, by + h2))
    im = im.convert('RGBA')
    put(im, M1, 540, 300, alpha=eo((t - a - 0.05) / 0.12), scale=1.0)
    q = eo((t - a - 0.5) / 0.12)
    put(im, M2, 540, 1500, alpha=q, scale=1.3 - 0.3 * q)
    # мягкая вспышка на входе
    fl = clamp(1 - (t - a) / 0.15) * 0.55
    arr = np.asarray(im.convert('RGB'), np.float32)
    arr = arr * (1 - fl) + 255 * fl
    return arr.astype(np.uint8)

# ---------- main loop ----------
ELEMS = [cake, stamp, icons3, timeline, endcard,
         lambda t: show_plate(t, PL_Q, T_Q - 0.05, MEME_AT),
         lambda t: show_plate(t, PL_RAN, T_RANEE, T_DET3 - 0.05),
         lambda t: show_plate(t, PL_GAR, T_DET3 + 0.1, T_OTHER - 0.05),
         lambda t: show_plate(t, CHIP_ALL, T_OTHER + 0.1, T_PO2 - 0.05, y=1310),
         lambda t: show_plate(t, BADGE, T_NEW + 0.1, T_NE - 0.05, y=1330)]

def main():
    import sys
    part = None
    if len(sys.argv) > 1 and sys.argv[1] == '--part':
        part = (int(sys.argv[2]), int(sys.argv[3])); only = []
    else:
        only = [float(x) for x in sys.argv[1:]]      # быстрые превью: python3 gfx.py 12.0 20.5
    nfr = int(round(TOTAL * FPS))
    f0, f1 = 0, nfr
    if part:
        f0 = nfr * part[0] // part[1]; f1 = nfr * (part[0] + 1) // part[1]
    frames = [int(round(x * FPS)) for x in only] if only else range(f0, f1)
    outp = f'{OUT}/gfx_part{part[0]}.mp4' if part else f'{OUT}/video_gfx.mp4'
    if not only:
        enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WD}x{HT}',
                                '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
                                '-pix_fmt', 'yuv420p', outp], stdin=subprocess.PIPE)
        dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{f0 / FPS:.4f}', '-i', f'{OUT}/video_raw.mp4', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                               stdout=subprocess.PIPE)
    for fi in frames:
        t = fi / FPS
        if only:
            fr = np.frombuffer(subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', f'{OUT}/video_raw.mp4',
                                                        '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']), np.uint8).reshape(HT, WD, 3)
        else:
            b = dec.stdout.read(WD * HT * 3)
            if len(b) < WD * HT * 3:
                fr = last
            else:
                fr = np.frombuffer(b, np.uint8).reshape(HT, WD, 3)
            last = fr
        if MEME_AT <= t < MEME_AT + MEME:
            fr = meme_frame(fr, t)
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
        enc.stdin.close(); enc.wait()
    print('done')

if __name__ == '__main__':
    main()
