# Рилс «Крашеный элемент и плёнка» — сборка видеоряда (DetailLab, 02.11.2026)
# Исходники: ../src/IMG_*.MOV, расшифровка ../words_medium.json, речь — segs.json (vad.py)
import json, subprocess, os
import numpy as np
S = os.path.dirname(os.path.abspath(__file__)); R0 = os.path.dirname(S)
SRC = f"{R0}/src"; OUT = f"{S}/out"; os.makedirs(OUT, exist_ok=True)
FPS = 30
SP = 1.08                      # лёгкое ускорение речи и картинки спикера
MEME = 0.0                     # мем убран по просьбе клиента
END_DUR = 3.6
W = json.load(open(f"{R0}/words_medium.json"))
SEGS = json.load(open(f"{S}/segs.json"))

def wav(n):
    x = np.frombuffer(open(f"{R0}/wav/{n}.wav", 'rb').read()[44:], dtype='int16').astype(float) / 32768
    return x
def quiet(n, t, win=0.14):
    """точка минимальной энергии около t (чтобы не резать по слову)"""
    x = wav(n); h = 160
    i0 = int((t - win) * 16000); i1 = int((t + win) * 16000)
    seg = x[i0:i1]; m = len(seg) // h
    e = (seg[:m*h].reshape(m, h) ** 2).mean(1)
    return round((i0 + int(np.argmin(e)) * h + h / 2) / 16000, 3)

# микро-вырезки: повтор «подорвать лак,» и «соответственно,»
CUTS = [('2509', 24.7, quiet('2509', 26.16, 0.04)),
        ('2509', 44.9, quiet('2509', 45.71, 0.04))]
segs = []
for c, s, e in SEGS:
    parts = [[s, e]]
    for cc, a, b in CUTS:
        if cc != c: continue
        np_ = []
        for p in parts:
            if b <= p[0] or a >= p[1]: np_.append(p)
            else:
                if a > p[0]: np_.append([p[0], a])
                if b < p[1]: np_.append([b, p[1]])
        parts = np_
    segs += [[c, p[0], p[1]] for p in parts if p[1] - p[0] > 0.05]
# разрез после «Конечно нет.» — туда встаёт мем
SPLIT = quiet('2509', 34.02, 0.08)
segs2 = []
for c, s, e in segs:
    if c == '2509' and s < SPLIT < e:
        segs2 += [[c, s, SPLIT], [c, SPLIT, e]]
    else:
        segs2.append([c, s, e])
segs = segs2

# ---------- кусочки речи, по кадрам ----------
pieces = []  # (clip, s, e, out)
t = 0.0
MEME_AT = None
for c, s, e in segs:
    n = max(1, round((e - s) / SP * FPS))
    pieces.append((c, s, s + n / FPS * SP, t))
    t += n / FPS
    if c == '2509' and abs(e - SPLIT) < 1e-6 and MEME_AT is None:
        MEME_AT = t; t += MEME
VOICE_END = t
TOTAL = VOICE_END + END_DUR

def omap(c, ts):
    for pc, s, e, o in pieces:
        if pc == c and s - 0.06 <= ts < e:
            return o + max(0.0, ts - s) / SP
    raise ValueError((c, ts))

def word(c, txt, k=1, after=0.0):
    n = 0
    for w in W[c]:
        if w[0] < after: continue
        if w[2].lower().strip('.,…?') == txt.lower():
            n += 1
            if n == k:
                return omap(c, w[0])
    raise KeyError((c, txt, k))

def snap(x): return round(x * FPS) / FPS

# ---------- планы ----------
# ('b', clip, src_start, fallback) — подсъём в родной скорости
SH = [
    (0.0, 'wide'),
    (word('2509', 'что', 1), 'close'),
    (word('2509', 'самый'), 'b', '2515', 0.0, 'wide'),
    (word('2509', 'полиуретановые'), 'close'),              # «пирог» слоёв
    (word('2509', 'когда', 2), 'wide'),
    (word('2509', 'есть'), 'close'),                         # отрыв лака
    (word('2509', 'и', 1, after=28), 'b', '2512', 0.3, 'wide'),
    (word('2509', 'несет'), 'wide'),
    (word('2509', 'конечно'), 'close'),
    (MEME_AT + MEME, 'wide'),                                # «мы не знаем где…»
    (word('2509', 'поэтому', 1), 'close'),
    (word('2509', 'ранее'), 'b', '2516', 0.0, 'close'),       # оригинал vs перекрас
    (word('2509', 'детейлинг', 3), 'wide'),
    (word('2509', 'ответственность', 1), 'close'),
    (word('2509', 'другие'), 'wide'),
    (word('2510', 'поэтому'), 'close'),
    (word('2510', 'новый'), 'b', '2518', 0.0, 'wide'),
    (word('2510', 'не'), 'close'),                           # таймлайн скол → коррозия
    (word('2510', 'потом', 2), 'wide'),
    (word('2510', 'лучше'), 'close'),
    (word('2509', 'приезжайте', 2), 'b', '2520', 0.0, 'close'),
    (VOICE_END, 'end'),
]
SH = [(snap(x[0]),) + x[1:] for x in SH]
SH.sort(key=lambda x: x[0])

FACE = {'2509': (0.48, 0.27), '2510': (0.50, 0.26)}
ZC = 1.42
# grade.txt: 1-я строка — перевод HDR→SDR (до кропа/zoompan) или пусто, 2-я — цвет (кривые/LUT)
_g = open(f"{S}/grade.txt").read().replace("../assets", f"{R0}/../assets").replace("ASSETS/", f"{R0}/../assets/").split("\n")
GPRE = _g[0].strip(); GRADE = _g[1].strip()
# Новые рилсы: AUTO = True — у каждого клипа своя нормализация света под эталон (../../autograde.py),
# стиль GRADE общий. Этот рилс утверждён без неё (он сам — эталон), поэтому здесь False.
AUTO = False
_NORM = {}
def gpre_for(src):
    if not AUTO: return GPRE
    if src not in _NORM:
        import sys; sys.path.insert(0, f"{R0}/..")
        import autograde
        nf, _ = autograde.norm_filter(src)
        _NORM[src] = (f"{GPRE}," if (GPRE and autograde.is_hlg(src)) else "") + nf
    return _NORM[src]
DUR = {}
def dur(c):
    if c not in DUR:
        DUR[c] = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                                '-of', 'csv=p=0', f"{SRC}/IMG_{c}.MOV"]))
    return DUR[c]

idx = 0
def render(src, ss, nfr, vf, speed=1.0, post=''):
    global idx
    out = f"{OUT}/seg{idx:03d}.mp4"; idx += 1
    pre = f"setpts=(PTS-STARTPTS)/{speed}," if speed != 1.0 else ""
    cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', f"{ss:.3f}", '-i', src, '-an',
           '-vf', f"{(gpre_for(src) + ',') if gpre_for(src) else ''}{pre}{vf},scale=1080:1920:flags=lanczos,setsar=1,fps={FPS},{GRADE}{post},format=yuv420p",
           '-frames:v', str(nfr), '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', out]
    subprocess.run(cmd, check=True)
    return out

def spk_crop(c, kind):
    if kind == 'wide':
        return "crop=iw/1.06:ih/1.06:(iw-iw/1.06)/2:0"
    fx, fy = FACE[c]
    return (f"crop=iw/{ZC}:ih/{ZC}:'max(0,min(iw-iw/{ZC},iw*{fx}-iw/{ZC}/2))':"
            f"'max(0,min(ih-ih/{ZC},ih*{fy}-ih/{ZC}*0.30))'")

segfiles = []
def speaker(a, b, kind):
    for pc, s, e, o in pieces:
        oe = o + (e - s) / SP
        lo, hi = max(a, o), min(b, oe)
        nfr = round((hi - lo) * FPS)
        if nfr <= 0:
            continue
        segfiles.append(render(f"{SRC}/IMG_{pc}.MOV", s + (lo - o) * SP, nfr, spk_crop(pc, kind), speed=SP))

shotlog = []
for i, sh in enumerate(SH):
    a = sh[0]
    b = SH[i + 1][0] if i + 1 < len(SH) else snap(TOTAL)
    kind = sh[1]
    nfr = round((b - a) * FPS)
    if nfr <= 0: continue
    if kind == 'end':
        # глянцевый борт машины, медленный наезд под финальную плашку
        segfiles.append(render(f"{SRC}/IMG_2518.MOV", 0.0, nfr,
                               f"crop=iw/1.08:ih/1.08,tpad=stop_mode=clone:stop_duration={END_DUR},"
                               f"scale=2160:3840,zoompan=z='1+0.07*on/{nfr}':d=1:s=2160x3840:fps={FPS}:"
                               f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"))
    elif kind == 'meme':
        # стоп-кадр спикера на «нет» (дальше в gfx.py — ч/б, наезд, подпись)
        pc, s, e, o = [p for p in pieces if p[3] < a][-1]
        segfiles.append(render(f"{SRC}/IMG_{pc}.MOV", e - 0.12, nfr,
                               spk_crop(pc, 'close') + f",trim=end_frame=1,tpad=stop_mode=clone:stop_duration={MEME+0.5}"))
    elif kind == 'b':
        _, _, c, ss, fb = sh
        avail = dur(c) - ss - 0.05
        nb = min(nfr, int(avail * FPS))
        segfiles.append(render(f"{SRC}/IMG_{c}.MOV", ss, nb, "crop=iw/1.06:ih/1.06"))
        if nb < nfr:
            speaker(a + nb / FPS, b, fb)
    else:
        speaker(a, b, kind)
    shotlog.append([a, b, kind] + list(sh[2:]))
    print(f"shot {i} {kind} {a:.2f}-{b:.2f}", flush=True)

with open(f"{OUT}/list.txt", 'w') as f:
    for p in segfiles:
        f.write(f"file '{p}'\n")
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f"{OUT}/list.txt",
                '-c', 'copy', f"{OUT}/video_raw.mp4"], check=True)

json.dump({'pieces': pieces, 'shots': shotlog, 'voice_end': VOICE_END, 'total': TOTAL,
           'meme_at': MEME_AT, 'meme': MEME, 'sp': SP},
          open(f"{OUT}/timeline.json", 'w'), ensure_ascii=False)
print("VOICE_END", round(VOICE_END, 2), "TOTAL", round(TOTAL, 2), "MEME_AT", round(MEME_AT, 2))
