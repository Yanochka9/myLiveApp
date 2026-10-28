"""Layout check before rendering: every element and subtitle inside the TikTok / Instagram Reels safe zone,
and no 2D element over the presenter's face."""
import os, numpy as np, cv2
from common import ROOT, W, H
import compose

# conservative union of TikTok and Reels interface on a 1080x1920 frame
TOP, BOTTOM, SIDE = 210, 1480, 40                  # tabs / header above, caption + music line below
RIGHT_COL = dict(x=930, y0=820, y1=1560)           # like / comment / share / avatar column


def unsafe(box):
    x0, y0, x1, y1 = box
    why = []
    if y0 < TOP: why.append(f'выше {TOP}px (верх интерфейса)')
    if y1 > BOTTOM: why.append(f'ниже {BOTTOM}px (подпись внизу)')
    if x0 < SIDE or x1 > W - SIDE: why.append('у края кадра')
    if x1 > RIGHT_COL['x'] and y1 > RIGHT_COL['y0'] and y0 < RIGHT_COL['y1']: why.append('под кнопками справа')
    return why


def el_size(c, el):
    g, t = c.gfx, el['type']
    if t == 'pill' or t == 'callout': im = g.pill(el['text'], el.get('size', 44), el.get('style', 'accent'), el.get('font', 'xbold'), el.get('icon'))
    elif t == 'gold': im = g.gold(el['text'], el.get('size', 90))
    elif t == 'rank': im = g.rank(el['n'], el.get('size', 100))
    elif t == 'label': im = g.label(el['text'], el.get('size', 40), el.get('font', 'bold'), el.get('color', 'text'))
    elif t == 'photo':
        im = g.photo(el['clip'], float(el.get('src', 0)), tuple(el['crop']), el.get('width', 420), el.get('text', ''), el.get('size', 38), el.get('font', 'xbold'))
        a = np.radians(abs(el.get('tilt', -6)))
        return (im.width * np.cos(a) + im.height * np.sin(a), im.height * np.cos(a) + im.width * np.sin(a))
    elif t == 'icon': return el.get('size', 110), el.get('size', 110)
    elif t == 'counter': return max(el.get('bar', 0), el.get('size', 120) * 0.62 * (len(f"{el['to']:,}") + len(el.get('suffix', '')))), el.get('size', 120) * 1.5
    elif t == '3d':
        from compose import KIND_DEFAULTS
        cw, ch = el.get('canvas', KIND_DEFAULTS[el['kind']]['canvas']); sc = el.get('scale', 1.0)
        if el['kind'] in ('rise', 'spin'): return cw * el.get('frac', KIND_DEFAULTS[el['kind']]['frac']) * sc, ch * 0.45 * sc
        return cw * 0.7 * sc, ch * 0.7 * sc
    else: return None
    return im.width * 0.85, im.height * 0.8      # pills/labels carry a shadow margin


def check(p):
    c = compose.Comp(p, True)
    bad = 0
    print('== безопасная зона TikTok / Reels')
    for el in c.els:
        sz = el_size(c, el)
        if not sz: continue
        x, y = el.get('x', 540), el.get('y', 960)
        box = (x - sz[0] / 2, y - sz[1] / 2, x + sz[0] / 2, y + sz[1] / 2)
        why = unsafe(box)
        if el['type'] == 'callout': why += unsafe((el['point'][0] - 15, el['point'][1] - 15, el['point'][0] + 15, el['point'][1] + 15))
        if why:
            bad += 1
            print(f"  {el['_span'][0]:6.2f} {el['type']:7s} {str(el.get('text', el.get('n', el.get('icon', '')))):26s} "
                  f"({box[0]:.0f},{box[1]:.0f})-({box[2]:.0f},{box[3]:.0f}): {', '.join(why)}")
    s = p.subs
    if s['enabled']:
        f = c.gfx.font(s['font'], s['size']); sp = f.getlength(' ') * 1.25; worst = 0
        for g in c.groups:
            total = sum(f.getlength(t) for _, _, t in g['words']) + sp * (len(g['words']) - 1)
            fit = min(1.0, (W - 2 * s.get('margin', 60)) / (total + s['size'] * 0.44))
            worst = max(worst, (total + s['size'] * 0.44) * fit)
        box = (W / 2 - worst / 2, s['y'] - s['size'] * 0.7, W / 2 + worst / 2, s['y'] + s['size'] * 0.7)
        why = unsafe(box)
        if why: bad += 1; print(f"  субтитры шириной до {worst:.0f}px: {', '.join(why)} -> увеличьте subtitles.margin")
    print('  всё внутри' if not bad else f'  проблем: {bad}')

    print('== лицо ведущей')
    det = cv2.FaceDetectorYN.create(os.path.join(ROOT, 'assets/models/face_yunet.onnx'), '', (W // 2, H // 2), 0.6)
    cache, hits = {}, 0
    for el in c.els:
        if el['type'] in ('3d', 'wipe', 'logo', 'circle'): continue
        a, b = el['_span']
        if a >= p.speech_end: continue
        sz = el_size(c, el)
        if not sz: continue
        x0, y0, x1, y1 = el['x'] - sz[0] / 2, el['y'] - sz[1] / 2, el['x'] + sz[0] / 2, el['y'] + sz[1] / 2
        for T in np.linspace(a + 0.05, b - 0.05, 3):
            it = c.item_at(T)
            if not it.get('aroll'): continue
            k = round(T, 1)
            if k not in cache:
                raw = compose.read_single(p, it, T - it['t0']); z, dx = c.zoom(it, T)
                sm = cv2.resize(cv2.cvtColor(c.crop(raw, z, dx).astype(np.uint8), cv2.COLOR_RGB2BGR), (W // 2, H // 2))
                _, res = det.detect(sm)
                cache[k] = [] if res is None else [tuple(v * 2 for v in r[:4]) for r in res]
            for fx, fy, fw, fh in cache[k]:
                if x0 < fx + fw * 1.15 and x1 > fx - fw * 0.15 and y0 < fy + fh * 1.1 and y1 > fy - fh * 0.25:
                    hits += 1; print(f"  {T:6.2f} {el['type']:7s} {el.get('text', '')} закрывает лицо ({fx:.0f},{fy:.0f})"); break
            else: continue
            break
    print('  лицо свободно' if not hits else f'  перекрытий: {hits}')
