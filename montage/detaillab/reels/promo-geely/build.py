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
PH = {'front0': ('full0', 1216, 0, 1215, 2160, 1.12, 0),
      'head0':  ('full0', 1466, 0, 1215, 2160, 1.18, 0),
      'head6':  ('full6', 977, 620, 1215, 2160, 1.20, 0),
      'side4':  ('full4', 1500, 0, 1215, 2160, 1.06, 300),
      'door5':  ('full5', 1300, 0, 1214, 2159, 1.06, 220),
      'rear7':  ('full7', 1250, 700, 1215, 2160, 1.10, 0),
      'sill4':  ('full4', 1900, 560, 900, 1600, 1.10, -150),
      'lower5': ('full5', 1600, 500, 900, 1600, 1.10, 120),
      'front6': ('full6', 1250, 500, 1339, 2380, 1.12, 0)}

SH = [
    (0.0, 'wide'),                                             # «−10%» за спиной
    (word('2714', 'скидка'), 'close'),
    (word('2714', 'все'), 'p', 'front0'),
    (pstart('2722', 3.28), 'wide'),                            # комплекс «Базовый»
    (word('2722', 'защита'), 'close'),
    (word('2722', 'передняя'), 'p', 'head6'),
    (word('2722', 'капот'), 'p', 'head0'),
    (word('2722', 'крылья'), 'close'),
    (pstart('2722', 18.1), 'wide'),
    (word('2722', 'стойки'), 'p', 'side4'),
    (word('2722', 'полоса'), 'close'),
    (word('2722', 'антиманикюры'), 'p', 'door5'),
    (word('2722', 'канты'), 'wide'),
    (word('2722', 'багажника'), 'p', 'rear7'),
    (word('2724', 'этот'), 'wide'),
    (word('2724', 'порогов'), 'p', 'sill4'),
    (word('2724', 'клиентов'), 'close'),
    (word('2724', 'поскольку'), 'wide'),
    (word('2724', 'резинки'), 'p', 'lower5'),
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
AUTO = True                                     # адаптивный цвет: каждый клип подравниваем под эталон
_NORM = {}
def gpre_for(src):
    if src.endswith('.jpg'): return ''
    if not AUTO: return GPRE
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
    g = np.log(max(m, 0.05)) / np.log(0.42)
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
        segfiles.append(photo('front0', nfr))
    elif kind == 'p':
        segfiles.append(photo(sh[2], nfr))
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
