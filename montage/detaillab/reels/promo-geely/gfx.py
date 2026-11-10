# Графика рилса «Акция Geely EX2 −10%»: объёмное «−10%» за спиной, плашка акции, схема зон «Базового»,
# цепочка «резинки → камушки → трут ЛКП», призыв и финал. Безопасная зона: ширина ≤ 720 по центру, y 250–1560.
import numpy as np, subprocess, math, sys
from PIL import Image, ImageDraw, ImageFilter
from gfx_base import *

def pst(c, s0): return [o for pc, s, e, o in pieces if pc == c and abs(s - s0) < 0.05][0]
T_SKID = word('2709', 'скидка'); T_INTRO = pst('2722', 0.66); T_BAZ = pst('2722', 3.28); T_ZASCH = word('2722', 'защита')
T_OPT = word('2722', 'передняя'); T_KAP = word('2722', 'капот'); T_KRYL = word('2722', 'крылья')
T_STOI = word('2722', 'стойки'); T_POL = word('2722', 'полоса'); T_ANTI = word('2722', 'антиманикюры')
T_KANT = word('2722', 'канты'); T_BAG = word('2722', 'багажника')
T_P0 = pst('2724', 2.38); T_POROG = word('2724', 'порогов'); T_PRISP = word('2724', 'приспускаем')
T_POSK = word('2724', 'поскольку'); T_REZ = word('2724', 'резинки'); T_KAM = word('2724', 'камушки')
T_PROT = word('2724', 'протирать'); T_C0 = pst('2727', 0.44); T_PODR = word('2727', 'подробностями')
T_ZHD = word('2727', 'ждем'); T_PROSP = word('2727', 'проспект')
PHOTO_SHOTS = [(a, b) for a, b, kind, *r in SHOTS if kind == 'p']
print({k: round(v, 2) for k, v in globals().items() if k.startswith('T_')})

def blank(): return Image.new('RGBA', (WD, HT), (0, 0, 0, 0))
def plate2(l1, l2, c2=GOLD):
    t1 = fitw(text_img(l1, FI(32), WHITE + (255,), spacing=1), 640)
    t2 = fitw(text_img(l2, FO(66), c2 + (255,), spacing=2), 640)
    w = min(SAFE_W, max(t1.width, t2.width) + 80); h = 36 + t1.height + 18 + t2.height + 34
    p = panel(w, h)
    p.alpha_composite(t1, ((w - t1.width) // 2, 34)); p.alpha_composite(t2, ((w - t2.width) // 2, 34 + t1.height + 18))
    return p
def chip(txt, fs=28, check=True, col=GOLD):
    tx = fitw(text_img(txt, FI(fs), WHITE + (255,), spacing=1), SAFE_W - 120)
    w = tx.width + (110 if check else 70); h = 84
    p = pill(w, h, DARK, 215, outline=col)
    x = 35
    if check:
        ck = circle_icon(26, ring=col, fill=col, inner=ic_check(), alpha=255, sc=0.6)
        p.alpha_composite(ck, (14, (h - ck.height) // 2)); x = 84
    p.alpha_composite(tx, (x, (h - tx.height) // 2))
    return p
def show(t, im, a, b, top=1072):
    al = fade(t, a, b, 0.22, 0.2)
    if al <= 0: return None
    lay = blank(); p = eo((t - a) / 0.25)
    put(lay, im, 540, top + im.height / 2 + 20 * (1 - p), alpha=al, scale=0.95 + 0.05 * p)
    return lay

# ---------- 1. «GEELY EX2 / −10%» объёмно за спиной ----------
W1 = word3d("GEELY EX2", 96, (255, 255, 255), (170, 174, 184), (58, 60, 68), maxw=520)
W2 = word3d("−10%", 220, (255, 228, 145), (178, 128, 28), (96, 64, 12), maxw=600)
MATTE = np.load(f"{OUT}/matte.npy")
BX = 540          # в этом дубле спикер по центру — надпись над головой (y 250–480)
def behind(fi, t):
    return None   # «за головой» клиенту не понравилось — крупное «−10%» спереди (promo_big)
    if t >= T_INTRO or fi >= len(MATTE): return None
    lay = blank(); out = clamp((T_INTRO - t) / 0.25); push = 1.0 + 0.035 * eio(t / T_INTRO)
    for (parts, xs), cy, t0 in [(W1, 285, 0.15), (W2, 400, 0.45)]:
        for i, ((im, adv), x) in enumerate(zip(parts, xs)):
            p = eo((t - t0 - i * 0.05) / 0.4)
            if p <= 0: continue
            put(lay, im, BX + x * push, cy + 50 * (1 - p), alpha=p * out, scale=(0.7 + 0.3 * p) * push)
    g = (t - 1.4) / 0.9
    if 0 < g < 1:
        a = np.asarray(lay.split()[3], np.float32); yy, xx = np.mgrid[0:HT, 0:WD]
        band = np.exp(-((xx + 0.45 * yy - (-300 + g * 1900)) / 55.0) ** 2) * 0.55
        arr = np.asarray(lay, np.float32).copy()
        arr[..., :3] = arr[..., :3] + (255 - arr[..., :3]) * band[..., None] * (a[..., None] / 255)
        lay = Image.fromarray(arr.clip(0, 255).astype(np.uint8), 'RGBA')
    m = Image.fromarray(MATTE[fi]).resize((WD, HT), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2))
    a = np.asarray(lay.split()[3], np.float32) * (1 - np.asarray(m, np.float32) / 255)
    lay.putalpha(Image.fromarray(a.astype(np.uint8)))
    return lay


# ---------- 1b. начало: «АКЦИЯ ДЛЯ GEELY EX2» → 3D «−10%» (Blender) → «НА ВСЕ КОМПЛЕКСЫ ОКЛЕЙКИ» ----------
T_V0 = pst('2709', 0.52); T_VSK = word('2709', 'скидка'); T_VVSE = word('2709', 'все')
L1a = word3d("АКЦИЯ", 190, (255, 236, 160), (190, 140, 30), (100, 70, 14), maxw=SAFE_W)
L1b = fitw(text_img("ДЛЯ GEELY EX2", FO(92), WHITE + (255,), spacing=4, shadow=(5, 10, 170)), SAFE_W)
L3 = plate2("НА ВСЕ КОМПЛЕКСЫ", "ОКЛЕЙКИ ПЛЁНКОЙ")
import glob as _glob
B3D = [Image.open(p).convert('RGBA') for p in sorted(_glob.glob(f"{OUT}/b3d/*.png"))]
B3D = [fitw(im.crop(im.getbbox()) if im.getbbox() else im, 720) for im in B3D]
def _goldify(im):   # Blender-кадр → насыщенное золото (яркость сохраняем, цвет — градиент тёмное→светлое золото)
    a = np.asarray(im, np.float32); L = (a[..., :3] @ np.array([.3, .59, .11])) / 255
    lo = np.array([120, 78, 12]); hi = np.array([255, 226, 140])
    rgb = lo + (hi - lo) * np.clip(L ** 1.15, 0, 1)[..., None]
    out = np.concatenate([rgb, a[..., 3:4]], -1).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')
B3D = [_goldify(im) for im in B3D]
GRAD = None
def promo_big(t):
    global GRAD
    a, b = 0.0, T_INTRO
    if not (a <= t < b): return None
    out = clamp((b - t) / 0.25)
    if GRAD is None:      # мягкое затемнение снизу, чтобы надписи читались на любом фоне
        yy = np.linspace(0, 1, HT)[:, None]; al = np.clip((yy - 0.38) / 0.18, 0, 1) * 0.62
        arr = np.zeros((HT, WD, 4), np.uint8); arr[..., 3] = (al * 255).astype(np.uint8).repeat(WD, 1)
        GRAD = Image.fromarray(arr, 'RGBA')
    lay = GRAD.copy(); lay.putalpha(lay.split()[3].point(lambda v: int(v * out * eo(t / 0.3))))
    if t >= T_VSK - 0.1 and B3D:
        k = min(len(B3D) - 1, int((t - (T_VSK - 0.1)) * FPS))
        p2 = eo((t - (T_VSK - 0.1)) / 0.3)
        put(lay, B3D[k], 540, 1110, alpha=p2 * out, scale=0.75 + 0.25 * p2)
    if t >= T_VVSE - 0.05:
        p3 = eo((t - (T_VVSE - 0.05)) / 0.3)
        put(lay, L3, 540, 1300 + L3.height / 2 + 20 * (1 - p3), alpha=p3 * out)
    return lay

# ---------- 2. акция / комплекс ----------
PL_PROMO = plate2("АКЦИЯ ДЛЯ GEELY EX2", "−10% НА ВСЕ КОМПЛЕКСЫ")
CH_BAZ = plate2("ЧТО ВХОДИТ В КОМПЛЕКС", "«БАЗОВЫЙ»")

# ---------- 3. зоны «Базового» на настоящей EX2 (вырезана из фото, ex2_zones.py) ----------
import json as _json, ex2_zones as _z
_BB = _json.load(open(f"{S}/stock/ex2_side_cut.json"))
_CAR = Image.open(f"{S}/stock/ex2_side_cut.png").convert('RGBA')
CW = 700; _sc = CW / _CAR.width; CH = int(_CAR.height * _sc)
CAR = _CAR.resize((CW, CH), Image.LANCZOS)
_a = np.asarray(CAR, np.float32).copy(); _a[..., :3] *= 0.82; CARD = Image.fromarray(_a.astype(np.uint8), 'RGBA')
def _P(x, y): return ((x * 4 - _BB[0]) * _sc, (y * 4 - _BB[1]) * _sc)
def _zone(i, k=2):
    im = Image.new('RGBA', (CW * k, CH * k), (0, 0, 0, 0)); d = ImageDraw.Draw(im); col = GOLD2 + (255,)
    for kind, a in _z.ZONES[i][2]:
        if kind == 'poly': d.polygon([tuple(v * k for v in _P(*p)) for p in a], fill=GOLD2 + (175,), outline=col, width=3 * k)
        elif kind == 'line': d.line([tuple(v * k for v in _P(*p)) for p in a], fill=col, width=7 * k, joint='curve')
        elif kind == 'cap':
            x, y = _P(*a); d.rounded_rectangle(((x - 17) * k, (y - 6) * k, (x + 17) * k, (y + 6) * k), 6 * k, fill=col)
        elif kind == 'arc':
            cx, cy, r, a0, a1 = a; x, y = _P(cx, cy); rr = r * 4 * _sc
            d.arc(((x - rr) * k, (y - rr) * k, (x + rr) * k, (y + rr) * k), a0, a1, fill=col, width=8 * k)
    im = im.resize((CW, CH), Image.LANCZOS); gl = im.filter(ImageFilter.GaussianBlur(9))
    o = Image.new('RGBA', (CW, CH), (0, 0, 0, 0)); o.alpha_composite(gl); o.alpha_composite(gl); o.alpha_composite(im); return o
ZWORD = {'оптика': 'передняя', 'капот': 'капот', 'крылья': 'крылья', 'стойки': 'стойки', 'полоса': 'полоса',
         'антиманикюры': 'антиманикюры', 'канты': 'канты', 'багажника': 'багажника'}
ZONES = [(n, word('2722', ZWORD[key])) for n, key, _ in _z.ZONES]
ZL = [_zone(i) for i in range(len(ZONES))]
ZLBL = [fitw(text_img(n, FO(54), GOLD + (255,), spacing=2, shadow=(3, 6, 170)), 640) for n, _ in ZONES]
TTL = text_img("ЧТО ВХОДИТ В «БАЗОВЫЙ»", FI(26), (215, 215, 215, 255), spacing=1)
PNL = panel(SAFE_W, CH + 170, alpha=225)
def scheme(t):
    a, b = T_ZASCH, T_P0
    if not (a <= t < b): return None
    out = clamp((b - t) / 0.25); pin = eo((t - a) / 0.35)
    card = PNL.copy(); card.alpha_composite(TTL, ((SAFE_W - TTL.width) // 2, 22))
    # машина «въезжает» и чуть поворачивается к камере
    car = CARD
    card.alpha_composite(car, ((SAFE_W - CW) // 2, 66))
    cur = None
    for i, (n, t0) in enumerate(ZONES):
        p = eo((t - t0 + 0.05) / 0.25)
        if p <= 0: continue
        pulse = 1.0 if t - t0 > 0.6 else 0.7 + 0.3 * math.sin((t - t0) * 20)
        z = ZL[i].copy(); z.putalpha(z.split()[3].point(lambda v: int(v * p * pulse)))
        card.alpha_composite(z, ((SAFE_W - CW) // 2, 66)); cur = i
    if cur is not None:
        lb = ZLBL[cur]; q = eo((t - ZONES[cur][1]) / 0.2)
        lb2 = lb.copy(); lb2.putalpha(lb2.split()[3].point(lambda v: int(v * q)))
        card.alpha_composite(lb2, ((SAFE_W - lb.width) // 2, card.height - lb.height - 26))
    lay = blank(); put(lay, card, 540, 1068 + card.height / 2 + 24 * (1 - pin), alpha=pin * out, scale=0.94 + 0.06 * pin)
    return lay

# ---------- 4. пороги ----------
CH_POROG = chip("ВНУТРЕННИЕ ПОРОГИ — ТОЖЕ В КОМПЛЕКСЕ", 26)
CH_PRISP = chip("ВЛАДЕЛЬЦАМ GEELY — ОПУСКАЕМ НИЖЕ", 26)
def ic_rubber(col):
    def f(d, k, c):
        c *= k; d.rounded_rectangle((c - 34 * k, c - 12 * k, c + 34 * k, c + 12 * k), 12 * k, outline=col, width=int(8 * k))
    return f
def ic_pebbles(col):
    def f(d, k, c):
        c *= k
        for dx, dy, r in [(-20, 6, 12), (4, -10, 10), (20, 10, 13), (-4, 18, 8)]:
            d.ellipse((c + (dx - r) * k, c + (dy - r) * k, c + (dx + r) * k, c + (dy + r) * k), fill=col)
    return f
def ic_scratch(col):
    def f(d, k, c):
        c *= k; P = [(-34, 14), (-18, -10), (-4, 10), (10, -12), (24, 8), (36, -8)]
        d.line([(c + x * k, c + y * k) for x, y in P], fill=col, width=int(7 * k), joint='curve')
    return f
CHAIN = [("РЕЗИНКИ", ic_rubber, T_REZ, GOLD), ("КАМУШКИ", ic_pebbles, T_KAM, GOLD), ("ТРУТ ЛКП", ic_scratch, T_PROT, RED)]
CX = [330, 540, 750]; CY = 1072 + 105
CH_PANEL = panel(SAFE_W, 250)
C_OFF = [circle_icon(50, ring=(110, 110, 110), inner=f((150, 150, 150, 255)), sc=0.8) for _, f, _, _ in CHAIN]
C_ON = [circle_icon(50, ring=col, inner=f(col + (255,)), sc=0.8) for _, f, _, col in CHAIN]
C_LBL = [(text_img(n, FI(24), (160, 160, 160, 255), spacing=1), text_img(n, FI(24), col + (255,), spacing=1)) for n, _, _, col in CHAIN]
def chain(t):
    a, b = T_POSK, T_C0
    if not (a <= t < b): return None
    lay = blank(); out = clamp((b - t) / 0.25); pin = eo((t - a) / 0.3)
    put(lay, CH_PANEL, 540, 1072 + CH_PANEL.height / 2, alpha=0.95 * pin * out)
    d = ImageDraw.Draw(lay)
    d.line([(CX[0], CY), (CX[-1], CY)], fill=(90, 90, 90, int(220 * pin * out)), width=5)
    for i in range(1, 3):
        p = eo((t - CHAIN[i][2] + 0.1) / 0.35)
        if p > 0: d.line([(CX[i - 1], CY), (CX[i - 1] + (CX[i] - CX[i - 1]) * p, CY)], fill=CHAIN[i][3] + (int(255 * out),), width=6)
    for i, (n, f, t0, col) in enumerate(CHAIN):
        p = eo((t - t0 + 0.05) / 0.25)
        put(lay, C_OFF[i], CX[i], CY, alpha=pin * out * (1 - p))
        if p > 0: put(lay, C_ON[i], CX[i], CY, alpha=p * out, scale=1.12 - 0.12 * p)
        put(lay, C_LBL[i][0], CX[i], CY + 82, alpha=pin * out * (1 - p))
        if p > 0: put(lay, C_LBL[i][1], CX[i], CY + 82, alpha=p * out)
    return lay

# ---------- 5. призыв ----------
PL_CTA = plate2("УСПЕЙТЕ ОКЛЕИТЬ ВЫГОДНО", "−10% НА GEELY EX2")
CH_DIRECT = chip("ПОДРОБНОСТИ АКЦИИ — В DIRECT", 28)
def ch_addr():
    tx = text_img("ПР-Т ДЗЕРЖИНСКОГО, 82А", FI(28), WHITE + (255,), spacing=1)
    w = tx.width + 100; h = 84; p = pill(w, h, DARK, 215, outline=GOLD)
    pin = hires(30, 40, lambda d, k: (d.ellipse((2 * k, 2 * k, 28 * k, 28 * k), fill=GOLD + (255,)),
                                      d.polygon([(5 * k, 21 * k), (25 * k, 21 * k), (15 * k, 39 * k)], fill=GOLD + (255,)),
                                      d.ellipse((10 * k, 9 * k, 20 * k, 19 * k), fill=DARK + (255,))))
    p.alpha_composite(pin, (26, (h - 40) // 2)); p.alpha_composite(tx, (70, (h - tx.height) // 2)); return p
CH_ADDR = ch_addr()

# ---------- 6. финал ----------
LOGO = logo_img()
E1 = text_img("−10% НА ОКЛЕЙКУ", FO(84), WHITE + (255,), spacing=2, shadow=(4, 8, 150))
E2 = text_img("GEELY EX2", FO(96), GOLD + (255,), spacing=3, shadow=(4, 8, 150))
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
    lay = Image.new('RGBA', (WD, HT), (0, 0, 0, int(160 * eo((t - a) / 0.35))))
    p = eo((t - a - 0.05) / 0.45); lg = LOGO
    g = (t - a - 0.8) / 0.7
    if 0 < g < 1:
        lg = LOGO.copy(); sh = Image.new('RGBA', lg.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        x = -150 + g * (lg.width + 300)
        sd.polygon([(x, 0), (x + 50, 0), (x - 100, lg.height), (x - 150, lg.height)], fill=(255, 255, 255, 120))
        sh = sh.filter(ImageFilter.GaussianBlur(14))
        sh.putalpha(Image.fromarray(np.minimum(np.asarray(sh.split()[3]), np.asarray(lg.split()[3]))))
        lg.alpha_composite(sh)
    put(lay, lg, 540, 600, alpha=p, scale=0.9 + 0.1 * p)
    for im, y, d0 in [(E1, 890, 0.35), (E2, 1000, 0.5), (E3, 1150, 0.7), (E4, 1270, 0.9), (E5, 1330, 1.0)]:
        q = eo((t - a - d0) / 0.35)
        if im is E4:
            put(lay, PIN, 540 - E4.width / 2 - 28, y, alpha=q); put(lay, im, 540 + 14, y + 16 * (1 - q), alpha=q)
        else:
            put(lay, im, 540, y + 16 * (1 - q), alpha=q, scale=(0.92 + 0.08 * q) if im is E3 else 1.0)
    return lay

# ---------- вспышка на «скидке», блик по фото ----------
def flash_fx(fr, t):
    k = clamp(1 - abs(t - T_SKID) / 0.12) * 0.55 if abs(t - T_SKID) < 0.12 else 0
    if k > 0: fr = (fr.astype(np.float32) * (1 - k) + 255 * k).astype(np.uint8)
    return fr
def glint(t):
    for a, b in PHOTO_SHOTS:
        if a <= t < b:
            g = (t - a) / max(0.6, b - a)
            yy, xx = np.mgrid[0:HT:2, 0:WD:2]
            band = np.exp(-((xx - 0.55 * yy - (-900 + g * 2200)) / 80.0) ** 2) * 0.22
            gl = np.zeros((HT // 2, WD // 2, 4), np.uint8); gl[..., :3] = 255; gl[..., 3] = (band * 255).astype(np.uint8)
            return Image.fromarray(gl, 'RGBA').resize((WD, HT), Image.BILINEAR)
    return None

ELEMS = [scheme, chain, endcard, promo_big,
         lambda t: show(t, CH_BAZ, T_BAZ + 0.05, T_ZASCH - 0.05),
         lambda t: show(t, CH_POROG, T_POROG, T_PRISP - 0.05),
         lambda t: show(t, CH_PRISP, T_PRISP, T_POSK - 0.05),
         lambda t: show(t, PL_CTA, T_C0, T_PODR - 0.05),
         lambda t: show(t, CH_DIRECT, T_PODR, T_PROSP - 0.05),
         lambda t: show(t, CH_ADDR, T_PROSP, VOICE_END)]

def main():
    part = None
    if len(sys.argv) > 1 and sys.argv[1] == '--part':
        part = (int(sys.argv[2]), int(sys.argv[3])); only = []
    else:
        only = [float(x) for x in sys.argv[1:]]
    nfr = int(round(TOTAL * FPS)); f0, f1 = 0, nfr
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
        fr = flash_fx(fr, t)
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
