# Рилс «Акция Geely EX2 −10%» — видеоряд (DetailLab, 04.11.2026)
# Спикер: ../src/IMG_2722/2714/2724/2727. Подсъёмов не было — фото EX2 с Wikimedia Commons (stock/, CREDITS.txt)
# с наездом/проездом камеры. Из основного кадра ничего не вырезаем (просьба клиента).
import json, subprocess, os, sys
import numpy as np
S = os.path.dirname(os.path.abspath(__file__)); R0 = os.path.dirname(S)
SRC = f"{R0}/src"; OUT = f"{S}/out"; os.makedirs(OUT, exist_ok=True)
FPS = 30
SP = 1.08
END_DUR = 3.6
W = json.load(open(f"{S}/words_medium.json"))
SEGS = json.load(open(f"{S}/segs.json"))
FACES = json.load(open(f"{S}/faces.json"))

# ---------- кусочки речи ----------
pieces = []; t = 0.0
for c, s, e in SEGS:
    n = max(1, round((e - s) / SP * FPS))
    pieces.append((c, s, s + n / FPS * SP, t)); t += n / FPS
VOICE_END = t; TOTAL = VOICE_END + END_DUR

def omap(c, ts):
    for pc, s, e, o in pieces:
        if pc == c and s - 0.06 <= ts < e:
            return o + max(0.0, ts - s) / SP
    for pc, s, e, o in pieces:              # слово чуть раньше куска (whisper спешит) — начало куска
        if pc == c and ts < s and s - ts < 1.0:
            return o
    raise ValueError((c, ts))

def word(c, txt, k=1, after=0.0):
    n = 0
    for w in W[c]:
        if w[0] < after: continue
        if w[2].lower().strip('.,…?!') == txt.lower():
            n += 1
            if n == k: return omap(c, w[0])
    raise KeyError((c, txt, k))
def pstart(c, s0):
    return [o for pc, s, e, o in pieces if pc == c and abs(s - s0) < 0.05][0]
def snap(x): return round(x * FPS) / FPS

# ---------- фото-подсъёмы: (файл, x0, y0, w, h, наезд до, сдвиг по x в px исходника) ----------
PH = {  # крупные планы деталей EX2 (фото Commons): (файл, x0, y0, w, h, наезд до, сдвиг x)
      'badge0':  ('full0', 2380, 382, 1000, 1778, 1.12, 0),     # шильдик GEELY EX2
      'head0':   ('full0', 1430, 80, 900, 1600, 1.15, 0),       # фара
      'hood0':   ('full0', 1900, 0, 1000, 1778, 1.10, -120),    # капот
      'fender4': ('full4', 1910, 320, 900, 1600, 1.10, 0),      # крыло
      'pillar4': ('full0', 760, 0, 800, 1422, 1.10, 0),          # стойка (кремовая — без наклейки)
      'roof5':   ('full5', 1630, 0, 900, 1600, 1.08, 150),      # крыша
      'handle5': ('full5', 1458, 266, 700, 1244, 1.15, 0),      # ручка (антиманикюр)
      'edge5':   ('full5', 2020, 489, 800, 1422, 1.10, 0),      # кант двери
      'tail7':   ('full7', 1130, 462, 1100, 1956, 1.10, 0),     # кромка крышки багажника
      'sill4':   ('full4', 920, 738, 800, 1422, 1.10, 120),     # порог
      'lower5':  ('full5', 1800, 738, 800, 1422, 1.10, 0),      # низ двери (резинки)
      'front6':  ('full6', 1250, 500, 1339, 2380, 1.12, 0)}

SH = [
    (0.0, 'wide'),                                             # скидка 10% (большое «−10%» спереди)
    (pstart('2722', 0.66), 'close'),                           # «Сегодня у нас в оклейке Geely EX2»
    (word('2722', 'geely'), 'p', 'badge0'),
    (pstart('2722', 3.28), 'wide'),                            # комплекс «Базовый»
    (word('2722', 'защита'), 'close'),
    (word('2722', 'передняя'), 'p', 'head0'),
    (word('2722', 'капот'), 'p', 'hood0'),
    (word('2722', 'крылья'), 'b', '9310', 0.6),               # видео клиента: арка крупно
    (pstart('2722', 19.24), 'wide'),
    (word('2722', 'стойки'), 'p', 'pillar4'),
    (word('2722', 'полоса'), 'p', 'roof5'),
    (word('2722', 'антиманикюры'), 'p', 'handle5'),
    (word('2722', 'канты'), 'p', 'edge5'),
    (word('2722', 'багажника'), 'p', 'tail7'),
    (word('2724', 'этот'), 'wide'),
    (word('2724', 'порогов'), 'b', '9311', 0.0),              # видео клиента: порог крупно
    (word('2724', 'клиентов'), 'close'),
    (word('2724', 'поскольку'), 'wide'),
    (word('2724', 'резинки'), 'b', '9311', 1.0),
    (word('2724', 'камушки'), 'close'),
    (word('2724', 'протирать'), 'wide'),
    (pstart('2727', 0.44), 'close'),
    (word('2727', 'подробностями'), 'p', 'front6'),
    (word('2727', 'ждем'), 'wide'),
    (VOICE_END, 'end'),
]
SH = [(snap(x[0]),) + x[1:] for x in SH]
SH.sort(key=lambda x: x[0])

ZC = 1.35
_g = open(f"{S}/grade.txt").read().replace("ASSETS/", f"{R0}/../assets/").split("\n")
GPRE = _g[0].strip(); GRADE = _g[1].strip()
AUTO = False   # цвет — LUT, подогнанный по скриншоту клиента из CapCut (assets/client_capcut_nov4.cube)
# светлые дубли темнее ДО цвета клиента (как «Экспозиция» в CapCut: оттенки не сдвигаются; кривая поверх LUT давала фиолетовый)
CLIP_EXPO = {'2724': 0.80, '2727': 0.68}
def pre_expo(k):
    xs = np.linspace(0, 1, 12); y = np.minimum((xs ** 2.2 * k) ** (1 / 2.2), 1)
    return "curves=interp=pchip:all='" + ' '.join(f'{a:.3f}/{b:.3f}' for a, b in zip(xs, y)) + "'"
_NORM = {}
def gpre_for(src):
    if src.endswith('.jpg'): return ''
    if not AUTO:
        c = os.path.basename(src)[4:8]
        return GPRE + (f",{pre_expo(CLIP_EXPO[c])}" if c in CLIP_EXPO else "")
    if src not in _NORM:
        sys.path.insert(0, f"{R0}/..")
        import autograde
        nf, info = autograde.norm_filter(src); print('autograde', os.path.basename(src), info, flush=True)
        _NORM[src] = (f"{GPRE}," if (GPRE and autograde.is_hlg(src)) else "") + nf
    return _NORM[src]

idx = 0
def render(src, ss, nfr, vf, speed=1.0, still=False):
    global idx
    out = f"{OUT}/seg{idx:03d}.mp4"; idx += 1
    pre = f"setpts=(PTS-STARTPTS)/{speed}," if speed != 1.0 else ""
    inp = ['-loop', '1', '-i', src] if still else ['-ss', f"{ss:.3f}", '-i', src]
    g = gpre_for(src)
    cmd = ['ffmpeg', '-v', 'error', '-y', *inp, '-an',
           '-vf', f"{(g + ',') if g else ''}{pre}{vf},scale=1080:1920:flags=lanczos,setsar=1,fps={FPS},{GRADE},format=yuv420p",
           '-frames:v', str(nfr), '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', out]
    subprocess.run(cmd, check=True)
    return out

def face(pc, s):
    k = min(FACES, key=lambda k: (k.split('@')[0] != pc, abs(float(k.split('@')[1]) - s)))
    fx, _, _, fy = FACES[k]; return fx, fy
def spk_crop(pc, s, kind):
    if kind == 'wide':
        return "crop=iw/1.06:ih/1.06:(iw-iw/1.06)/2:0"
    fx, fy = face(pc, s)
    return (f"crop=iw/{ZC}:ih/{ZC}:'max(0,min(iw-iw/{ZC},iw*{fx}-iw/{ZC}/2))':"
            f"'max(0,min(ih-ih/{ZC},ih*{fy}-ih/{ZC}*0.30))'")

def photo_gamma(f, x0, y0, w, h):
    """подравнять яркость фото (уличные серые — тёмные) к середине эталона"""
    from PIL import Image
    im = Image.open(f"{S}/stock/{f}.jpg").convert('L').crop((x0, y0, x0 + w, y0 + h)).resize((200, 360))
    m = np.median(np.asarray(im, float) / 255)
    g = np.log(max(m, 0.05)) / np.log(0.40)          # фото не светлее кадров спикера после LUT
    return float(np.clip(g, 0.75, 1.6))

def photo(key, nfr):
    f, x0, y0, w, h, z, dx = PH[key]
    g = photo_gamma(f, x0, y0, w, h)
    k = 2160 / w
    vf = (f"crop={w}:{h}:{x0}:{y0},scale=2160:3840,"
          f"zoompan=z='1+({z}-1)*on/{nfr}':x='iw/2-iw/zoom/2+{dx*k:.1f}*on/{nfr}':y='ih/2-ih/zoom/2':d=1:s=2160x3840:fps={FPS},"
          f"eq=gamma={g:.3f}")
    return render(f"{S}/stock/{f}.jpg", 0, nfr, vf, still=True)

segfiles = []
def speaker(a, b, kind):
    for pc, s, e, o in pieces:
        oe = o + (e - s) / SP
        lo, hi = max(a, o), min(b, oe)
        nfr = round((hi - lo) * FPS)
        if nfr <= 0: continue
        segfiles.append(render(f"{SRC}/IMG_{pc}.MOV", s + (lo - o) * SP, nfr, spk_crop(pc, s, kind), speed=SP))

shotlog = []
for i, sh in enumerate(SH):
    a = sh[0]; b = SH[i + 1][0] if i + 1 < len(SH) else snap(TOTAL)
    kind = sh[1]; nfr = round((b - a) * FPS)
    if nfr <= 0: continue
    if kind == 'end':
        segfiles.append(photo('front6', nfr))
    elif kind == 'p':
        segfiles.append(photo(sh[2], nfr))
    elif kind == 'b':
        clip, ss = sh[2], sh[3]
        d = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f"{SRC}/IMG_{clip}.MOV"]))
        nb = min(nfr, int((d - ss - 0.05) * FPS))
        segfiles.append(render(f"{SRC}/IMG_{clip}.MOV", ss, nb, "crop=iw/1.04:ih/1.04,scale=2160:3840,"
                               f"zoompan=z='1+0.05*on/{max(1,nb)}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=2160x3840:fps={FPS}"))
        if nb < nfr: segfiles.append(photo('front6', nfr - nb))
    else:
        speaker(a, b, kind)
    shotlog.append([a, b, kind] + list(sh[2:]))
    print(f"shot {i} {kind} {a:.2f}-{b:.2f} {sh[2:] if len(sh) > 2 else ''}", flush=True)

with open(f"{OUT}/list.txt", 'w') as f:
    for p in segfiles: f.write(f"file '{p}'\n")
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f"{OUT}/list.txt",
                '-c', 'copy', f"{OUT}/video_raw.mp4"], check=True)
json.dump({'pieces': pieces, 'shots': shotlog, 'voice_end': VOICE_END, 'total': TOTAL,
           'meme_at': 0.0, 'meme': 0.0, 'sp': SP}, open(f"{OUT}/timeline.json", 'w'), ensure_ascii=False)
print("VOICE_END", round(VOICE_END, 2), "TOTAL", round(TOTAL, 2))
