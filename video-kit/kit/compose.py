"""Builds the edit from a project config: cuts, masks, 3D, 2D graphics, subtitles, grade, audio."""
import os, json, math, subprocess, functools, time
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from common import Project, ROOT, KIT, FPS, W, H, spec_hash, hexrgb
from analyze import probe, ensure_masks, mask_dir, MASK_FPS

DW, DH = 1296, 2304            # decode size, headroom for zoom
BASEZ = W / DW


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo3(t): t = clamp(t); return 1 - (1 - t) ** 3
def eio(t): t = clamp(t); return t * t * (3 - 2 * t)
def eback(t, s=1.6):
    t = clamp(t) - 1; return t * t * ((s + 1) * t + s) + 1


# ================================================================== 3D elements
KIND_DEFAULTS = {
    'rise': dict(canvas=[1080, 800], frac=0.92, fade_bottom=0.28, font='black_italic'),
    'spin': dict(canvas=[1080, 560], frac=0.86, fade_bottom=0.0, font='black_italic'),
    'badge': dict(canvas=[720, 560], frac=0.75, fade_bottom=0.0, font='black_italic'),
    'slab': dict(canvas=[1000, 520], frac=0.8, fade_bottom=0.0, font='black'),
    'pin': dict(canvas=[460, 620], frac=0.62, fade_bottom=0.0, font='black'),
}


def spec3d(p, el, draft=False):
    a, b = p.span(el)
    d = dict(KIND_DEFAULTS[el['kind']], **{k: el[k] for k in ('canvas', 'frac', 'font', 'extrude', 'stagger', 'sweep', 'fade_bottom') if k in el})
    spec = dict(kind=el['kind'], text=el.get('text', ''), font=p.font(d['font']), frames=int(round((b - a) * FPS)) + 1,
                canvas=d['canvas'], frac=d['frac'], colors=p.theme['3d'], samples=6 if draft else 14)
    for k in ('extrude', 'stagger', 'sweep'):
        if k in d: spec[k] = d[k]
    return spec, d['fade_bottom']


def dir3d(spec):
    return os.path.join(ROOT, 'cache3d', f"{spec['kind']}-{spec_hash(spec)}")


def ensure_3d(p, els, frames=None, draft=False, parallel=2):
    """render missing frames; frames = {id(el): [frame indices]} for previews, None = everything"""
    jobs = []
    for el in els:
        spec, _ = spec3d(p, el, draft)
        out = dir3d(spec); os.makedirs(out, exist_ok=True)
        need = range(spec['frames']) if frames is None else frames.get(id(el), [])
        miss = [f for f in need if not os.path.exists(os.path.join(out, f'{f:04d}.png'))]
        if not miss: continue
        sp = os.path.join(out, 'spec.json'); json.dump(spec, open(sp, 'w', encoding='utf-8'), ensure_ascii=False)
        jobs.append((el.get('text') or el['kind'], sp, out, None if frames is None else miss))
    running = []
    thr = max(1, (os.cpu_count() or 4) // parallel)
    while jobs or running:
        while jobs and len(running) < parallel:
            name, sp, out, miss = jobs.pop(0)
            cmd = ['python3', '-I', os.path.join(KIT, 'blender3d.py'), '--', sp, out, str(thr)]
            if miss is not None: cmd.append(','.join(map(str, miss)))
            print('3D render:', name, 'all frames' if miss is None else f'{len(miss)} frames', flush=True)
            running.append(subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        for r in running[:]:
            if r.poll() is not None:
                running.remove(r)
                if r.returncode: raise SystemExit('blender render failed')
        time.sleep(0.5)


class Seq:
    def __init__(self, p, el, draft):
        spec, fade = spec3d(p, el, draft)
        self.dir, self.n, self.fade = dir3d(spec), spec['frames'], fade
        self.cache = {}

    def get(self, i):
        i = max(0, min(self.n - 1, i))
        if i in self.cache: return self.cache[i]
        a = cv2.imread(os.path.join(self.dir, f'{i:04d}.png'), cv2.IMREAD_UNCHANGED)
        if a is None: return None
        a = cv2.cvtColor(a, cv2.COLOR_BGRA2RGBA)
        if self.fade > 0:
            h = a.shape[0]; k = int(h * self.fade)
            ramp = np.ones(h, np.float32); ramp[h - k:] = np.linspace(1, 0, k) ** 1.5
            a[..., 3] = (a[..., 3] * ramp[:, None]).astype(np.uint8)
        if len(self.cache) > 6: self.cache.clear()
        self.cache[i] = a
        return a


# ================================================================== 2D drawing
class Gfx:
    def __init__(self, p):
        self.p = p

    @functools.lru_cache(maxsize=None)
    def font(self, key, size):
        return ImageFont.truetype(self.p.font(key), size)

    def rounded_grad(self, w, h, r, c1, c2):
        g = np.zeros((h, w, 4), np.float32)
        t = np.linspace(0, 1, h)[:, None]
        for i in range(3): g[..., i] = c1[i] * (1 - t) + c2[i] * t
        m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
        g[..., 3] = np.asarray(m, np.float32)
        hl = np.clip(1 - np.linspace(0, 1, h) / 0.5, 0, 1)[:, None] * 0.22
        g[..., :3] = g[..., :3] * (1 - hl[..., None]) + 255 * hl[..., None]
        return Image.fromarray(g.astype(np.uint8), 'RGBA')

    def shadow(self, im, blur=14, off=(0, 8), op=0.35):
        pad = blur * 2 + max(abs(off[0]), abs(off[1]))
        out = Image.new('RGBA', (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
        a = im.split()[3].point(lambda v: int(v * op))
        blk = Image.new('RGBA', im.size, (30, 0, 6, 255)); blk.putalpha(a)
        out.paste(blk, (pad + off[0], pad + off[1]), blk)
        out = out.filter(ImageFilter.GaussianBlur(blur))
        out.alpha_composite(im, (pad, pad))
        return out

    @functools.lru_cache(maxsize=None)
    def pill(self, text, size=44, style='accent', font='xbold', icon=None):
        p = self.p
        f = self.font(font, size)
        bb = f.getbbox(text); cap = f.getbbox('НЁ')
        tw, th = bb[2] - bb[0], cap[3] - cap[1]
        padx, pady = int(size * 0.77), int(size * 0.41)
        iw = int(size * 1.15) if icon else 0
        w, h = tw + padx * 2 + iw, th + pady * 2
        if style == 'accent':
            bg = self.rounded_grad(w, h, h // 2, p.color('accent_light'), p.color('accent')); fg = p.color('on_accent')
        elif style == 'light':
            l = p.color('light'); bg = self.rounded_grad(w, h, h // 2, l, tuple(int(c * 0.93) for c in l)); fg = p.color('on_light')
        else:
            dk = p.color('dark'); bg = self.rounded_grad(w, h, h // 2, tuple(min(255, c + 22) for c in dk), dk); fg = p.color('text')
        d = ImageDraw.Draw(bg)
        d.text((padx + iw - bb[0], pady - cap[1]), text, font=f, fill=fg)
        if icon == 'check':
            cx, cy, r = padx + iw * 0.38, h / 2, size * 0.42
            circ, cc = (p.color('on_accent'), p.color('accent')) if style == 'accent' else (p.color('accent'), p.color('on_accent'))
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=circ)
            d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.35)],
                   fill=cc, width=max(3, size // 9), joint='curve')
        return self.shadow(bg)

    @functools.lru_cache(maxsize=None)
    def label(self, text, size, font='bold', color='text'):
        f = self.font(font, size); bb = f.getbbox(text)
        im = Image.new('RGBA', (bb[2] - bb[0] + 20, bb[3] - bb[1] + 20), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10 - bb[0], 10 - bb[1]), text, font=f, fill=self.p.color(color))
        return self.shadow(im, blur=10, off=(0, 5), op=0.45)

    @functools.lru_cache(maxsize=None)
    def photo(self, clip, src, crop, width, text, size, font):
        """graded still of a clip framed as a polaroid with a caption; crop = (x, y, w, h) in the 1080x1920 frame"""
        p = self.p
        vf = f"scale={W}:{H}:flags=bicubic,{grade_filter(p, clip)},format=rgb24"
        buf = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{src:.3f}', '-i', p.clip(clip), '-vf', vf, '-frames:v', '1',
                              '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE, check=True).stdout
        fr = Image.fromarray(np.frombuffer(buf, np.uint8).reshape(H, W, 3))
        x, y, cw, ch = crop
        ph = fr.crop((x, y, x + cw, y + ch)).resize((width, int(width * ch / cw)), Image.LANCZOS)
        m = int(width * 0.05); cap = int(size * 2.1) if text else m
        card = Image.new('RGBA', (width + 2 * m, ph.height + m + cap), (*p.color('paper'), 255))
        card.paste(ph, (m, m))
        if text:
            f = self.font(font, size); bb = f.getbbox(text)
            while bb[2] - bb[0] > width and size > 16:   # caption shrinks to the photo width
                size -= 2; f = self.font(font, size); bb = f.getbbox(text)
            ImageDraw.Draw(card).text((m - bb[0], ph.height + m + (cap - (bb[3] - bb[1])) // 2 - bb[1]), text, font=f, fill=p.color('dark'))
        return card

    @functools.lru_cache(maxsize=None)
    def gold(self, text, size, font='black', outline=0.06):
        """text filled with the accent gradient (light top -> accent bottom), dark outline, soft shadow"""
        p = self.p; f = self.font(font, size); bb = f.getbbox(text); ow = max(2, int(size * outline))
        w, h = bb[2] - bb[0] + 2 * ow + 20, bb[3] - bb[1] + 2 * ow + 20
        m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).text((10 + ow - bb[0], 10 + ow - bb[1]), text, font=f, fill=255)
        o = Image.new('L', (w, h), 0)
        ImageDraw.Draw(o).text((10 + ow - bb[0], 10 + ow - bb[1]), text, font=f, fill=255, stroke_width=ow, stroke_fill=255)
        g = self.rounded_grad(w, h, 0, p.color('accent_light'), p.color('accent'))
        im = Image.new('RGBA', (w, h), (*p.color('dark'), 0)); im.putalpha(o)
        g.putalpha(m); im.alpha_composite(g)
        return self.shadow(im, blur=12, off=(0, 6), op=0.45)

    @functools.lru_cache(maxsize=None)
    def rank(self, n, size, word='МЕСТО'):
        """place badge: gold disc with a big digit + dark pill with the word, overlapping"""
        p = self.p; D = int(size * 1.7)
        disc = self.rounded_grad(D, D, D // 2, p.color('accent_light'), p.color('accent'))
        f = self.font('black', int(size * 1.15)); bb = f.getbbox(str(n))
        ImageDraw.Draw(disc).text(((D - (bb[2] - bb[0])) / 2 - bb[0], (D - (bb[3] - bb[1])) / 2 - bb[1]), str(n), font=f, fill=p.color('dark'))
        fw = self.font('black', int(size * 0.55)); wb = fw.getbbox(word); cap = fw.getbbox('НЁ')
        ph = int(size * 0.95); pw = (wb[2] - wb[0]) + int(size * 0.9) + D // 2
        dk = p.color('dark'); pill = self.rounded_grad(pw, ph, ph // 2, tuple(min(255, c + 22) for c in dk), dk)
        ImageDraw.Draw(pill).text((D // 2 + int(size * 0.4) - wb[0], (ph - (cap[3] - cap[1])) / 2 - cap[1]), word, font=fw, fill=p.color('light'))
        im = Image.new('RGBA', (D // 2 + pw, D), (0, 0, 0, 0))
        im.alpha_composite(pill, (D // 2, (D - ph) // 2)); im.alpha_composite(disc, (0, 0))
        return self.shadow(im, blur=16, off=(0, 8), op=0.4)

    @functools.lru_cache(maxsize=None)
    def icon(self, kind, size, color):
        im = doodle(kind, size, (*self.p.color(color), 255), (*self.p.color('dark'), 255))
        return self.shadow(im, blur=8, off=(0, 4), op=0.35)

    @functools.lru_cache(maxsize=None)
    def image(self, path):
        a = cv2.imread(self.p.asset(path), cv2.IMREAD_UNCHANGED)
        if a is None: raise SystemExit(f'image not found: {path}')
        return cv2.cvtColor(a, cv2.COLOR_BGRA2RGBA if a.shape[2] == 4 else cv2.COLOR_BGR2RGBA)


def blend(dst, im, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.003 or scale <= 0.01 or im is None: return
    a = np.asarray(im) if not isinstance(im, np.ndarray) else im
    if abs(scale - 1) > 1e-3:
        a = cv2.resize(a, (max(1, int(a.shape[1] * scale)), max(1, int(a.shape[0] * scale))),
                       interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    h, w = a.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb: return
    sub = a[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    al = sub[..., 3:4] / 255.0 * alpha
    dst[ya:yb, xa:xb] = dst[ya:yb, xa:xb] * (1 - al) + sub[..., :3] * al


def pop(T, t0, t1, fin=0.28, fout=0.18):
    if T < t0 or T > t1: return 0, 0
    u, v = (T - t0) / fin, (t1 - T) / fout
    s = 0.6 + 0.4 * eback(u, 1.8) if u < 1 else 1.0
    if v < 1: s *= 1 + 0.06 * (1 - v)
    return s, min(clamp(u * 1.6), clamp(v))


def draw_line(dst, p0, p1, prog, alpha, col, dot_col, width=5):
    if alpha <= 0 or prog <= 0: return
    x, y = p0[0] + (p1[0] - p0[0]) * prog, p0[1] + (p1[1] - p0[1]) * prog
    lay = np.zeros((H, W), np.uint8)
    cv2.line(lay, (int(p0[0]), int(p0[1])), (int(x), int(y)), 255, width, cv2.LINE_AA)
    if prog >= 0.98: cv2.circle(lay, (int(p1[0]), int(p1[1])), 13, 255, -1, cv2.LINE_AA)
    ys, xs = np.where(lay > 0)
    if len(ys) == 0: return
    ya, yb, xa, xb = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    al = lay[ya:yb, xa:xb].astype(np.float32)[..., None] / 255 * alpha
    dst[ya:yb, xa:xb] = dst[ya:yb, xa:xb] * (1 - al) + np.array(col, np.float32) * al
    if prog >= 0.98:
        cv2.circle(dst, (int(p1[0]), int(p1[1])), 7, tuple(float(c) for c in dot_col), -1, cv2.LINE_AA)


def wobble_ellipse(cx, cy, rx, ry, seed=0, turns=1.12, n=120):
    """hand-drawn ellipse: slightly irregular radius, overshoots the start like a marker stroke"""
    rs = np.random.RandomState(seed); ph = rs.uniform(0, 6.28, 3); t = np.linspace(0, turns * 2 * np.pi, n) - 0.6
    k = 1 + 0.035 * np.sin(2 * t + ph[0]) + 0.02 * np.sin(3 * t + ph[1]) + 0.04 * t / (turns * 2 * np.pi)
    return np.stack([cx + rx * k * np.cos(t), cy + ry * k * np.sin(t)], 1)


def draw_stroke(dst, pts, prog, alpha, col, width):
    if alpha <= 0 or prog <= 0: return
    pts = pts[:max(2, int(len(pts) * clamp(prog)))].astype(np.int32)
    lay = np.zeros((H, W), np.uint8)
    cv2.polylines(lay, [pts], False, 255, width, cv2.LINE_AA)
    ys, xs = np.where(lay > 0)
    if len(ys) == 0: return
    ya, yb, xa, xb = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    al = lay[ya:yb, xa:xb].astype(np.float32)[..., None] / 255 * alpha
    dst[ya:yb, xa:xb] = dst[ya:yb, xa:xb] * (1 - al) + np.array(col, np.float32) * al


def doodle(kind, size, fill, line):
    """small hand-drawn style icon: snow, spark, sun, flame, heart"""
    S = size * 2; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = S / 2; lw = max(4, S // 22)
    if kind == 'snow':   # dark under-stroke, colour on top
        for col, w in ((line, lw * 3), (fill, lw * 1.6)):
            for k in range(6):
                a = k * np.pi / 3; x, y = c + np.cos(a) * S * 0.42, c + np.sin(a) * S * 0.42
                d.line([(c, c), (x, y)], fill=col, width=int(w))
                for sgn in (-1, 1):
                    b = a + sgn * 0.7; mx, my = c + np.cos(a) * S * 0.27, c + np.sin(a) * S * 0.27
                    d.line([(mx, my), (mx + np.cos(b) * S * 0.13, my + np.sin(b) * S * 0.13)], fill=col, width=int(w))
    elif kind == 'spark':
        r1, r2 = S * 0.45, S * 0.11
        pts = [(c + (r1 if k % 2 == 0 else r2) * np.cos(k * np.pi / 4 - np.pi / 2), c + (r1 if k % 2 == 0 else r2) * np.sin(k * np.pi / 4 - np.pi / 2)) for k in range(8)]
        d.polygon(pts, fill=fill, outline=line, width=lw)
    elif kind == 'sun':
        for col, w in ((line, lw * 3), (fill, lw * 1.6)):
            for k in range(8):
                a = k * np.pi / 4
                d.line([(c + np.cos(a) * S * 0.3, c + np.sin(a) * S * 0.3), (c + np.cos(a) * S * 0.44, c + np.sin(a) * S * 0.44)], fill=col, width=int(w))
        r = S * 0.21; d.ellipse((c - r, c - r, c + r, c + r), fill=fill, outline=line, width=lw)
    elif kind == 'flame':
        t = np.linspace(0, 2 * np.pi, 80)   # teardrop with the point up, smaller one inside
        drop = lambda a, b, oy: [(c + a * np.sin(u) * np.sin(u / 2), c + oy - b * np.cos(u)) for u in t]
        d.polygon(drop(S * 0.34, S * 0.42, S * 0.04), fill=fill, outline=line, width=lw)
        d.polygon(drop(S * 0.15, S * 0.2, S * 0.24), fill=(255, 255, 255, 235))
    elif kind == 'heart':
        t = np.linspace(0, 2 * np.pi, 80)
        pts = [(c + S * 0.026 * 16 * np.sin(u) ** 3, c - S * 0.026 * (13 * np.cos(u) - 5 * np.cos(2 * u) - 2 * np.cos(3 * u) - np.cos(4 * u))) for u in t]
        d.polygon(pts, fill=fill, outline=line, width=lw)
    elif kind == 'paw':
        d.ellipse((c - S * 0.2, c - S * 0.02, c + S * 0.2, c + S * 0.34), fill=fill, outline=line, width=lw)
        for dx, dy in ((-0.3, -0.12), (-0.11, -0.3), (0.11, -0.3), (0.3, -0.12)):
            x, y = c + dx * S, c + dy * S; r = S * 0.1
            d.ellipse((x - r, y - r * 1.2, x + r, y + r * 1.2), fill=fill, outline=line, width=lw)
    elif kind == 'bag':
        d.arc((c - S * 0.18, c - S * 0.4, c + S * 0.18, c - S * 0.04), 180, 360, fill=line, width=lw * 2)
        d.rounded_rectangle((c - S * 0.36, c - S * 0.2, c + S * 0.36, c + S * 0.38), S * 0.08, fill=fill, outline=line, width=lw)
    elif kind == 'stroller':
        d.pieslice((c - S * 0.36, c - S * 0.38, c + S * 0.24, c + S * 0.22), 180, 360, fill=fill, outline=line, width=lw)
        d.rectangle((c - S * 0.36, c - S * 0.08, c + S * 0.24, c + S * 0.12), fill=fill, outline=line, width=lw)
        d.line([(c + S * 0.24, c - S * 0.08), (c + S * 0.42, c - S * 0.36)], fill=line, width=lw)
        for x in (-0.24, 0.12):
            r = S * 0.1; d.ellipse((c + x * S - r, c + S * 0.24 - r, c + x * S + r, c + S * 0.24 + r), fill=fill, outline=line, width=lw)
    elif kind == 'mute':
        d.polygon([(c - S * 0.4, c - S * 0.12), (c - S * 0.24, c - S * 0.12), (c - S * 0.02, c - S * 0.34), (c - S * 0.02, c + S * 0.34),
                   (c - S * 0.24, c + S * 0.12), (c - S * 0.4, c + S * 0.12)], fill=fill, outline=line, width=lw)
        for col, w in ((line, lw * 3), (fill, int(lw * 1.6))):
            d.line([(c + S * 0.1, c - S * 0.16), (c + S * 0.42, c + S * 0.16)], fill=col, width=w)
            d.line([(c + S * 0.1, c + S * 0.16), (c + S * 0.42, c - S * 0.16)], fill=col, width=w)
    return im.resize((size, size), Image.LANCZOS)


def fmt_num(v, sep='\u2009'):
    return f'{int(round(v)):,}'.replace(',', sep)


# ================================================================== subtitles
def subtitle_groups(p):
    s = p.subs
    raw = [list(w) for w in p.words()]
    merges = [[t.lower() for t in m] for m in s['merge']]
    ws, i = [], 0
    while i < len(raw):
        w = raw[i]
        while i + 1 < len(raw) and raw[i + 1][3] == w[3] and (
                raw[i + 1][2].startswith('-') or [w[2].lower().strip('.,!?'), raw[i + 1][2].lower().strip('.,!?')] in merges):
            nxt = raw[i + 1]
            sep = '' if nxt[2].startswith('-') or [w[2].lower(), nxt[2].lower().strip('.,!?')] in merges else ' '
            w = [w[0], nxt[1], w[2] + sep + nxt[2], w[3]]; i += 1
        t = w[2]
        for a, b in s['replace'].items(): t = t.replace(a, b)
        ws.append([w[0], w[1], t, w[3]]); i += 1
    groups, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w)
        txt = ' '.join(x[2] for x in cur)
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        brk = (w[2][-1] in '.,!?' or nxt is None or nxt[0] - w[1] > 0.25 or nxt[3] != w[3]
               or len(cur) >= s['max_words'] or len(txt) > s['max_chars'])
        if brk and nxt is not None and len(cur) > 1 and len(w[2]) <= 2 and w[2][-1] not in '.,!?':
            groups.append(cur[:-1]); cur = [w]; continue
        if brk: groups.append(cur); cur = []
    if cur: groups.append(cur)
    res = []
    for gi, g in enumerate(groups):
        e = g[-1][1] + 0.18
        if gi + 1 < len(groups): e = min(e, groups[gi + 1][0][0])
        words = [(a, b, t.rstrip('.,!?').upper() if s['uppercase'] else t.rstrip('.,!?')) for a, b, t, _ in g]
        res.append(dict(s=g[0][0], e=e, words=words))
    return res


def draw_subs(dst, T, groups, gfx, p):
    s = p.subs
    if not s['enabled'] or T >= p.speech_end: return
    g = next((g for g in groups if g['s'] <= T < g['e']), None)
    if g is None: return
    f = gfx.font(s['font'], s['size'])
    sp = f.getlength(' ') * 1.25
    parts = [(t, f.getlength(t), a, b) for a, b, t in g['words']]
    total = sum(x[1] for x in parts) + sp * (len(parts) - 1)
    u = (T - g['s']) / 0.16
    gs, ga = 0.88 + 0.12 * eo3(u), clamp(u * 1.5)
    if ga <= 0: return
    CW = int(max(W, total + s['size'] * 2))
    can = Image.new('RGBA', (CW, int(s['size'] * 3.4)), (0, 0, 0, 0)); d = ImageDraw.Draw(can)
    asc = f.getbbox('НЁ')[1]; th = f.getbbox('Нy')[3] - asc; cy = can.height / 2
    hl = p.color(s['highlight']); x = CW / 2 - total / 2
    for i, (t, w, a, b) in enumerate(parts):
        active = (a - 0.04 <= T < max(b, a + 0.12) + 0.06) if s['mode'] == 'karaoke' else (s['mode'] == 'first' and i == 0)
        if active:
            k = eo3((T - a + 0.04) / 0.1) if s['mode'] == 'karaoke' else 1
            pad = s['size'] * 0.22
            d.rounded_rectangle((x - pad, cy - th / 2 - pad * 0.85, x + w + pad, cy + th / 2 + pad), int(s['size'] * 0.28),
                                fill=(*hl, int(255 * k)))
        col = p.color(s['highlight_text']) if active else p.color(s['color'])
        d.text((x, cy - th / 2 - asc), t, font=f, fill=col)
        x += w + sp
    fit = min(1.0, (W - 2 * s.get('margin', 60)) / (total + s['size'] * 0.44))   # long phrases shrink to fit the frame
    blend(dst, gfx.shadow(can, blur=12, off=(0, 6), op=s['shadow']), W / 2, s['y'], gs * fit, ga)


# ================================================================== video track
def zoom_fn(z):
    a, b = (z, z) if isinstance(z, (int, float)) else z
    return lambda u: a + (b - a) * eio(u)


def build_items(p):
    """base video track in output time: A-roll pieces with cutaways laid over them, then the end card"""
    cuts = []
    for c in p.cfg.get('cutaways', []):
        t0, t1 = p.t(c['at']), p.t(c['until'], ref=p.t(c['at']))
        cuts.append(dict(clip=c['clip'], src=c.get('src', 0.0), t0=t0, t1=t1, span=(t0, t1), zoom=zoom_fn(c.get('zoom', [1.04, 1.12])),
                         drift=c.get('drift'), dy=c.get('dy', 0.0), tin=c.get('tin'), speed=c.get('speed', 1.0), cut=True))
    cuts.sort(key=lambda c: c['t0'])
    items = []
    for a in p.aroll:
        pieces = [(a['t0'], a['t1'])]
        for c in cuts:
            nxt = []
            for s, e in pieces:
                if c['t1'] <= s or c['t0'] >= e: nxt.append((s, e)); continue
                if c['t0'] > s: nxt.append((s, c['t0']))
                if c['t1'] < e: nxt.append((c['t1'], e))
            pieces = nxt
        for s, e in pieces:
            if e - s < 1 / FPS: continue
            tin = a.get('tin') if abs(s - a['t0']) < 1e-6 else next((c.get('tout') for c in p.cfg.get('cutaways', [])
                                                                       if abs(p.t(c['until'], ref=p.t(c['at'])) - s) < 1e-6), None)
            items.append(dict(clip=a['clip'], src=a['in'] + (s - a['t0']), t0=s, t1=e, span=(a['t0'], a['t1']),
                              zoom=zoom_fn(a.get('zoom', [1.0, 1.06])), drift=None, dy=a.get('dy', 0.0), tin=tin, speed=1.0, aroll=True))
    items += cuts
    ec = p.cfg.get('endcard')
    if ec:
        items.append(dict(clip=ec['clip'], src=ec.get('src', 0.0), t0=p.speech_end, t1=p.total, span=(p.speech_end, p.total),
                          zoom=zoom_fn(ec.get('zoom', [1.06, 1.14])), drift=None, dy=ec.get('dy', 0.0), tin=ec.get('tin', 'flash'),
                          speed=ec.get('speed', 0.55), end=ec))
    items.sort(key=lambda i: i['t0'])
    return items


def grade_filter(p, clip):
    g = p.grade
    tone = ''
    if probe(p.clip(clip))['hdr']:
        tone = ('zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,'
                'zscale=t=bt709:m=bt709:r=tv,format=yuv420p,')
    if g.get('lut'):
        lut = p.asset(g['lut']).replace('\\', '/').replace(':', '\\:')
        mix = clamp(float(g.get('lut_mix', 1.0)))
        tone += (f"lut3d=file='{lut}'," if mix >= 0.999 else
                 f"split[gx][gy];[gy]lut3d=file='{lut}'[gl];[gx][gl]blend=all_expr='A*{1 - mix:.3f}+B*{mix:.3f}',")
    return (tone + f"eq=gamma={g['gamma']}:contrast={g['contrast']}:saturation={g['saturation']},"
            f"colorbalance=rs={-g['cool_shadows'] / 2}:bs={g['cool_shadows']}:rh={g['warmth']}:bh={-g['warmth'] / 1.5}")


def decode_cmd(p, it, src, nframes):
    sp = it['speed']
    vf = f"scale={DW}:{DH}:flags=bicubic,fps={FPS / sp},{grade_filter(p, it['clip'])},format=rgb24"
    if sp != 1: vf += f',setpts=PTS/{sp}'
    return ['ffmpeg', '-v', 'error', '-ss', f'{src:.3f}', '-i', p.clip(it['clip']), '-vf', vf,
            '-frames:v', str(nframes), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']


class Reader:
    def __init__(self, p, it):
        n = int(round((it['t1'] - it['t0']) * FPS)) + 2
        self.proc = subprocess.Popen(decode_cmd(p, it, it['src'], n), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     bufsize=DW * DH * 3 * 2)
        self.last = None

    def read(self):
        buf = self.proc.stdout.read(DW * DH * 3)
        if len(buf) == DW * DH * 3: self.last = np.frombuffer(buf, np.uint8).reshape(DH, DW, 3)
        return self.last

    def close(self):
        self.proc.stdout.close(); self.proc.wait()


def read_single(p, it, lt):
    buf = subprocess.run(decode_cmd(p, dict(it, speed=1.0), it['src'] + lt * it['speed'], 1), stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL).stdout
    return np.frombuffer(buf, np.uint8).reshape(DH, DW, 3)


# ================================================================== compositor
class Comp:
    def __init__(self, p, draft=False):
        self.p, self.draft = p, draft
        self.items = build_items(p)
        self.gfx = Gfx(p)
        self.groups = subtitle_groups(p)
        self.els = p.cfg.get('elements', [])
        for el in self.els: el['_span'] = p.span(el)
        self.seqs = {}
        self.punch = [(p.t(x['at']), x.get('amount', 0.05)) for x in p.cfg.get('punch', [])]
        self.mask_fix = p.cfg.get('mask_cleanup', {})
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        v = p.theme['vignette']
        self.vig = (1 - v * np.clip(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2, 0, 1) ** 1.3)[..., None]
        self.glowmap = np.exp(-(((xx - W * 0.85) / (W * 0.6)) ** 2 + ((yy - H * 0.2) / (H * 0.45)) ** 2))[..., None]
        acc = np.array(p.color('accent'), np.float32) / 255
        self.glow_col = acc * p.theme['glow']
        fl = np.array(p.color('flash'), np.float32) / 255
        self.flash_col = fl
        self.flash_ts = [it['t0'] for it in self.items if it.get('tin') == 'flash']
        self.zoom_cuts = [it['t0'] for it in self.items if it.get('tin') == 'zoom']

    # ---- 3D
    def els3d(self): return [e for e in self.els if e['type'] == '3d']

    def seq(self, el):
        k = id(el)
        if k not in self.seqs: self.seqs[k] = Seq(self.p, el, self.draft)
        return self.seqs[k]

    def frame3d(self, el, T):
        return self.seq(el).get(int(round((T - el['_span'][0]) * FPS)))

    # ---- masks
    def mask_ranges(self, times=None):
        """source ranges of A-roll that need a person/car mask (behind-layer elements)"""
        rng = []
        for el in self.els:
            if el.get('layer') != 'behind': continue
            a, b = el['_span']
            for it in self.items:
                if not it.get('aroll'): continue
                s, e = max(a, it['t0']), min(b, it['t1'])
                if s >= e: continue
                if times is not None:
                    ts = [t for t in times if s <= t < e]
                    for t in ts: rng.append((it['clip'], it['src'] + t - it['t0'], it['src'] + t - it['t0']))
                else:
                    rng.append((it['clip'], it['src'] + s - it['t0'], it['src'] + e - it['t0']))
        return rng

    @functools.lru_cache(maxsize=6)
    def mask_png(self, clip, idx):
        f = os.path.join(mask_dir(self.p, clip), f'{idx:05d}.png')
        if not os.path.exists(f): return None
        m = cv2.imread(f, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
        for x0, y0, x1, y1 in self.mask_fix.get(clip, []): m[y0:y1, x0:x1] = 0
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        m = np.clip((m - 0.35) / 0.4, 0, 1)
        return cv2.GaussianBlur(m, (0, 0), 2.2)

    def mask(self, clip, src_t):
        x = src_t * MASK_FPS; i0 = int(math.floor(x)); f = x - i0
        a, b = self.mask_png(clip, i0), self.mask_png(clip, i0 + 1)
        if a is None or b is None: return a if b is None else b
        return a * (1 - f) + b * f

    # ---- transforms
    def zoom(self, it, T):
        s0, s1 = it['span']
        z = it['zoom']((T - s0) / max(1e-3, s1 - s0))
        for tp, amt in self.punch:
            if it['t0'] <= tp < it['t1'] and T > tp: z *= 1 + amt * eo3((T - tp) / 0.18)
        lt = T - it['t0']
        if it.get('tin') == 'zoom' and lt < 0.2: z *= 1 + 0.16 * (1 - eo3(lt / 0.2))
        if any(abs(c - it['t1']) < 1e-6 for c in self.zoom_cuts) and it['t1'] - T < 0.12:
            z *= 1 + 0.14 * eio(1 - (it['t1'] - T) / 0.12)
        dx = 0.0
        if it.get('drift'):
            d = it['drift']; dx = d[0] + (d[1] - d[0]) * eio(lt / (it['t1'] - it['t0']))
        return z, dx

    @staticmethod
    def crop(frame, z, dx, dy=0.0):
        """dy: vertical framing in output px (positive = show a lower part of the source)"""
        s = BASEZ * z
        M = np.array([[s, 0, W / 2 - s * (DW / 2 + dx / BASEZ)], [0, s, H / 2 - s * (DH / 2 + dy / BASEZ)]], np.float32)
        return cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    @staticmethod
    def crop_mask(m, z, dx, dy=0.0):
        M = np.array([[z, 0, W / 2 - z * (W / 2 + dx)], [0, z, H / 2 - z * (H / 2 + dy)]], np.float32)
        return cv2.warpAffine(m, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

    @staticmethod
    def zoom_blur(img, amt):
        if amt < 0.01: return img
        acc = img.astype(np.float32)
        for k in (1, 2, 3):
            s = 1 + amt * k / 3
            M = np.array([[s, 0, W / 2 * (1 - s)], [0, s, H / 2 * (1 - s)]], np.float32)
            acc += cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return acc / 4

    # ---- elements
    def draw_el(self, dst, el, T, z=1.0, dx=0.0, behind=False):
        a, b = el['_span']
        x, y, sc = el.get('x', 540), el.get('y', 960), el.get('scale', 1.0)
        if behind:   # anchored to the scene: follow the camera zoom
            x, y, sc = W / 2 + (x - W / 2 - dx) * z, H / 2 + (y - H / 2) * z, sc * z
        t = el['type']; g = self.gfx
        if t == '3d':
            fr = self.frame3d(el, T)
            alpha = clamp((b - T) / 0.15) * (clamp((T - a) / 0.06) if el['kind'] in ('badge', 'slab', 'pin') else 1)
            blend(dst, fr, x, y, sc, alpha)
            return
        s, al = pop(T, a, b)
        if t == 'pill':
            blend(dst, g.pill(el['text'], el.get('size', 44), el.get('style', 'accent'), el.get('font', 'xbold'), el.get('icon')), x, y, s * sc, al)
        elif t == 'label':
            blend(dst, g.label(el['text'], el.get('size', 40), el.get('font', 'bold'), el.get('color', 'text')), x, y, s * sc, al)
        elif t == 'callout':
            pt = el['point']
            draw_line(dst, (x, y + 40), pt, eo3((T - a - 0.1) / 0.3), al, self.p.color('text'), self.p.color('accent'))
            blend(dst, g.pill(el['text'], el.get('size', 44), el.get('style', 'accent'), el.get('font', 'xbold'), el.get('icon')), x, y, s, al)
        elif t == 'logo':
            blend(dst, g.image(el['file']), x, y, s * sc, al)
        elif t == 'circle':   # marker circle drawn around a detail
            u, v = (T - a) / el.get('draw', 0.35), clamp((b - T) / 0.2)
            pts = wobble_ellipse(x, y, el.get('rx', 160), el.get('ry', 110), seed=int(a * 100))
            draw_stroke(dst, pts, eo3(u), v * clamp(u * 4), self.p.color(el.get('color', 'accent')), el.get('width', 9))
        elif t == 'icon':     # doodle icon pops and gently rocks
            im = g.icon(el['icon'], el.get('size', 110), el.get('color', 'accent'))
            ang = 8 * np.sin((T - a) * 4.2) * el.get('rock', 1.0)
            blend(dst, im.rotate(ang, resample=Image.BICUBIC, expand=True), x, y, s * sc, al)
        elif t == 'counter':  # number runs up to its value; style 'gold' + optional odometer bar under it
            u = eo3((T - a) / el.get('dur', 0.8))
            txt = el.get('prefix', '') + fmt_num(el.get('from', 0) + (el['to'] - el.get('from', 0)) * u) + el.get('suffix', '')
            im = g.gold(txt, el.get('size', 120)) if el.get('style') == 'gold' else g.label(txt, el.get('size', 120), el.get('font', 'black'), el.get('color', 'text'))
            blend(dst, im, x, y, s * sc, al)
            if el.get('bar'):
                bw, bh = el['bar'], max(10, el.get('size', 120) // 9); by = y + el.get('size', 120) * 0.72
                bg = g.rounded_grad(bw, bh, bh // 2, self.p.color('dark'), self.p.color('dark'))
                blend(dst, bg, x, by, s, al * 0.8)
                fw = max(bh, int(bw * u))
                fg = g.rounded_grad(fw, bh, bh // 2, self.p.color('accent_light'), self.p.color('accent'))
                blend(dst, fg, x - bw / 2 + fw / 2, by, s, al)
        elif t == 'gold':     # gradient-filled title text
            blend(dst, g.gold(el['text'], el.get('size', 90), el.get('font', 'black')), x, y, s * sc, al)
        elif t == 'rank':     # place badge
            blend(dst, g.rank(el['n'], el.get('size', 100), el.get('word', 'МЕСТО')), x, y, s * sc, al)
        elif t == 'measure':  # dimension line grows from the middle to both ends, ticks + gold label
            u, v = eo3((T - a) / el.get('draw', 0.5)), clamp((b - T) / 0.2)
            x0, x1, yy = el['x0'], el['x1'], el['y']; cx = (x0 + x1) / 2; half = (x1 - x0) / 2 * u
            col = self.p.color(el.get('color', 'accent')); w = el.get('width', 8)
            for xa, xb in ((cx, cx - half), (cx, cx + half)):
                draw_stroke(dst, np.array([[xa, yy], [xb, yy]]), 1.0, v, col, w)
            if u > 0.98:
                for xe in (x0, x1): draw_stroke(dst, np.array([[xe, yy - 34], [xe, yy + 34]]), 1.0, v, col, w)
            if el.get('text'):
                blend(dst, g.gold(el['text'], el.get('size', 110)), cx, yy - el.get('size', 110) * 0.75, s, al * clamp(u * 1.5))
        elif t == 'wipe':     # wavy colour bands sweep across the cut, optional big text while covered
            self.draw_wipe(dst, el, T, a, b)
        elif t == 'photo':   # polaroid drops in with a swing and settles at its tilt
            u, v = clamp((T - a) / 0.45), clamp((b - T) / 0.22)
            im = g.photo(el['clip'], float(el.get('src', 0.0)), tuple(el.get('crop', (90, 560, 900, 900))), el.get('width', 420),
                         el.get('text', ''), el.get('size', 38), el.get('font', 'xbold'))
            ang = el.get('tilt', -6) + (1 - eback(u, 1.4)) * el.get('swing', 12)
            im = g.shadow(im.rotate(ang, expand=True, resample=Image.BICUBIC), blur=18, off=(0, 12), op=0.4)
            blend(dst, im, x, y - (1 - eo3(u)) * 170, sc * (0.92 + 0.08 * eo3(u)) * (1 + 0.04 * (1 - v)), min(clamp(u * 2.5), v))

    def draw_wipe(self, dst, el, T, a, b):
        p = self.p; n = el.get('bands', 5); u = (T - a) / (b - a)
        cols = [p.color(c) for c in el.get('colors', ['accent', 'accent_light', 'paper'])]
        bw = W / n + 2; cover = 0.0
        for i in range(n):
            d = i * 0.04
            ui = clamp((u - d) / 0.38); uo = clamp((u - 0.6 - d) / 0.24)
            top = H * (1 - eio(ui)) - (H + 200) * eio(uo)   # slides up into the frame, then on up and out
            if ui <= 0 or top > H: continue
            yy = np.arange(0, H, 8, dtype=np.float32)
            x0 = i * W / n
            wave = 22 * np.sin(yy / 140 + T * 6)   # same wave on every edge, so neighbouring bands meet without gaps
            poly = np.concatenate([np.stack([x0 + wave, yy], 1), np.stack([x0 + bw + wave[::-1], yy[::-1]], 1)])
            m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [poly.astype(np.int32)], 255)
            m[:max(0, int(top))] = 0; bot = int(top + H + 200)
            if bot < H: m[bot:] = 0
            al = m.astype(np.float32)[..., None] / 255
            dst[:] = dst * (1 - al) + np.array(cols[i % len(cols)], np.float32) * al
            cover += al.mean()
        if el.get('text') and cover > 0.6:
            k = clamp((cover - 0.6) / 0.3)
            im = self.gfx.label(el['text'], el.get('size', 150), el.get('font', 'black'), el.get('text_color', 'dark'))
            blend(dst, im, W / 2, H * 0.45, 0.9 + 0.1 * k, k)

    def render(self, T, it, raw):
        p = self.p
        lt = T - it['t0']
        z, dx = self.zoom(it, T); dy = it.get('dy', 0.0)
        base = self.crop(raw, z, dx, dy).astype(np.float32)
        if it.get('tin') == 'zoom' and lt < 0.2: base = self.zoom_blur(base, 0.06 * (1 - eo3(lt / 0.2)))
        if any(abs(c - it['t1']) < 1e-6 for c in self.zoom_cuts) and it['t1'] - T < 0.12:
            base = self.zoom_blur(base, 0.05 * eio(1 - (it['t1'] - T) / 0.12))
        ec = it.get('end')
        if ec:
            base = cv2.GaussianBlur(base, (0, 0), ec.get('blur', 14))
            lum = base.mean(2, keepdims=True)
            tint = np.array(p.color(ec.get('tint', 'accent')), np.float32) * 0.66
            base = base * ec.get('darken', 0.38) + lum * 0.12 + tint * 0.35 * (lum / 255)
        out = base.copy()
        active = [e for e in self.els if e['_span'][0] <= T < e['_span'][1]]
        behind = [e for e in active if e.get('layer') == 'behind']
        if behind and it.get('aroll'):
            for el in behind: self.draw_el(out, el, T, z, dx, behind=True)
            m = self.mask(it['clip'], it['src'] + lt)
            if m is not None:
                m = self.crop_mask(m, z, dx, dy)[..., None]
                out = out * (1 - m) + base * m
        for el in active:
            if el.get('layer') != 'behind': self.draw_el(out, el, T)
        draw_subs(out, T, self.groups, self.gfx, p)
        for ft in self.flash_ts:
            d = abs(T - ft)
            if d < 0.2:
                k = (1 - d / 0.2) ** 2 * 0.45
                out = out + (255 - out) * (self.glowmap * k) * self.flash_col
        out = out * self.vig + self.glowmap * self.glow_col
        return np.clip(out, 0, 255).astype(np.uint8)

    def item_at(self, T):
        for it in self.items:
            if it['t0'] <= T < it['t1']: return it
        return self.items[-1]


# ================================================================== audio
def loudness(path, a=None, b=None, gain_db=0.0):
    cmd = ['ffmpeg', '-hide_banner']
    if a is not None: cmd += ['-ss', str(a), '-to', str(b)]
    cmd += ['-i', path, '-vn', '-af', f'volume={gain_db}dB,ebur128=peak=sample', '-f', 'null', '-']
    err = subprocess.run(cmd, stderr=subprocess.PIPE, text=True).stderr
    summ = err[err.rfind('Summary'):]
    I = float(summ.split('I:')[1].split('LUFS')[0]); pk = float(summ.split('Peak:')[1].split('dBFS')[0])
    return I, pk


def build_audio(p, out):
    v = p.cfg.get('voice', {}); target = v.get('target_lufs', -17.5)
    inputs, filt, labels = [], [], []
    for i, a in enumerate(p.aroll):
        I, pk = loudness(p.clip(a['clip']), a['in'], a['out'])
        gain = a.get('gain_db', min(target - I, -0.5 - pk))     # one static gain per take, no other processing
        inputs += ['-i', p.clip(a['clip'])]
        d = a['out'] - a['in']
        filt.append(f"[{i}:a]atrim={a['in']}:{a['out']},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                    f"volume={gain:.2f}dB,afade=t=in:d=0.01,afade=t=out:st={d - 0.012:.3f}:d=0.012[v{i}]")
        labels.append(f'[v{i}]')
        print(f"voice {a['clip']}: {I:.1f} LUFS -> gain {gain:+.1f} dB")
    k = len(p.aroll); T = p.total
    filt.append(''.join(labels) + f'concat=n={k}:v=0:a=1,apad=whole_dur={T}[voice]')
    m = p.cfg.get('music')
    if m and m.get('file'):
        inputs += ['-i', p.asset(m['file'])]
        st, vol, ev = m.get('start', 0.0), m.get('volume', 0.14), m.get('end_volume', 0.42)
        se = p.speech_end
        expr = f"if(lt(t,{se - 0.15}),{vol},if(lt(t,{se + 0.25}),{vol}+(t-{se - 0.15})/0.4*{ev - vol},{ev}))"
        filt.append(f"[{k}:a]atrim={st}:{st + T},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                    f"afade=t=in:d=0.05,volume='{expr}':eval=frame,afade=t=out:st={T - 1.0}:d=1.0[mus]")
        mix = ['[voice]', '[mus]']
    else:
        mix = ['[voice]']
    n_in = k + (1 if len(mix) > 1 else 0)
    for j, fx in enumerate(p.cfg.get('sfx', [])):   # transition sounds: 'peak' (s inside the file) lands on 'at'
        at = p.t(fx['at']); pk = fx.get('peak', 0.0); d = at - pk
        inputs += ['-i', p.asset(fx['file'])]
        trim = f'atrim=start={-d:.3f},asetpts=PTS-STARTPTS,' if d < 0 else ''
        filt.append(f"[{n_in + j}:a]{trim}aformat=sample_rates=48000:channel_layouts=stereo,volume={fx.get('gain', 0.1)},"
                    f"adelay={max(d, 0) * 1000:.0f}:all=1[fx{j}]")
        mix.append(f'[fx{j}]')
    if len(mix) > 1:
        filt.append(''.join(mix) + f'amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.97:level=false[out]')
    else:
        filt.append('[voice]alimiter=limit=0.97:level=false[out]')
    subprocess.run(['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', ';'.join(filt), '-map', '[out]',
                    '-t', str(T), '-c:a', 'pcm_s16le', out], check=True)
    I, pk = loudness(out)
    print(f'mix: {I:.1f} LUFS, peak {pk:.1f} dBFS')


# ================================================================== entry points
def preview(p, times, draft=True):
    c = Comp(p, draft)
    ensure_masks(p, c.mask_ranges(times))
    need = {}
    for el in c.els3d():
        a, b = el['_span']
        fr = [int(round((T - a) * FPS)) for T in times if a <= T < b]
        if fr: need[id(el)] = sorted(set(max(0, f) for f in fr))
    ensure_3d(p, [e for e in c.els3d() if id(e) in need], frames=need, draft=draft)
    od = os.path.join(p.work, 'preview'); os.makedirs(od, exist_ok=True)
    files = []
    for T in times:
        it = c.item_at(T)
        fr = c.render(T, it, read_single(p, it, T - it['t0']))
        f = os.path.join(od, f't{T:06.2f}.jpg')
        if p.out_crop:
            x, y, w, h = p.out_crop; fr = fr[y:y + h, x:x + w]
        cv2.imwrite(f, cv2.cvtColor(np.ascontiguousarray(fr), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88]); files.append(f)
    cols = min(6, len(files)); rows = math.ceil(len(files) / cols)
    tw, th = (360, round(360 * p.out_crop[3] / p.out_crop[2])) if p.out_crop else (270, 480)
    sheet = Image.new('RGB', (cols * tw, rows * th))
    for i, f in enumerate(files): sheet.paste(Image.open(f).resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
    sp = os.path.join(od, 'sheet.jpg'); sheet.save(sp, quality=88)
    print(sp)


def render(p, draft=False):
    c = Comp(p, draft)
    ensure_masks(p, c.mask_ranges())
    ensure_3d(p, c.els3d(), draft=draft)
    mix = os.path.join(p.work, 'mix.wav'); build_audio(p, mix)
    out = p.output if not draft else p.output.replace('.mp4', '_draft.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                            '-i', '-', '-i', mix, *(['-vf', 'crop={2}:{3}:{0}:{1}'.format(*p.out_crop)] if p.out_crop else []),
                            '-c:v', 'libx264', '-preset', 'veryfast' if draft else 'slow',
                            '-crf', '22' if draft else '16', '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709',
                            '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart',
                            '-c:a', 'aac', '-b:a', '256k', '-shortest', out], stdin=subprocess.PIPE)
    nf = int(round(p.total * FPS)); cur = rd = None
    for fi in range(nf):
        T = fi / FPS; it = c.item_at(T)
        if it is not cur:
            if rd: rd.close()
            cur, rd = it, Reader(p, it)
        enc.stdin.write(c.render(T, it, rd.read()).tobytes())
        if fi % 60 == 0: print(f'frame {fi}/{nf}', flush=True)
    rd.close(); enc.stdin.close(); enc.wait()
    print('DONE', out)
    return out
