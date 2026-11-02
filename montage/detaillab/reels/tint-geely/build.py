"""Рилс «Тонировка Geely» (DetailLab) — один длинный дубль спикера (IMG_2504) + 19 подсъёмов процесса.

Основан на шаблоне ../build.py + ../finish.py (Leopard), но всё в одном файле и с двумя вариантами:
  python3 build.py hook     — хук «За полтора-два часа…» в начале, наезд, вспышка, дальше по порядку
  python3 build.py nohook   — сразу «Итак, всем привет…»
Исходники: $TINT_SRC (по умолчанию /tmp/detaillab-video/tint/src: IMG_2504.MOV и IMG_25xx.MOV),
расшифровка: $TINT_WORK/words_medium.json (python3 ../tr.py medium 2504 в $TINT_WORK).
Цвет: HDR (HLG) → SDR, затем ../../assets/r5_light.cube (утверждён клиентом). Голос — шумодав RNNoise.
"""
import json, os, subprocess, sys

VAR = sys.argv[1] if len(sys.argv) > 1 else 'nohook'
HOOK = VAR == 'hook'
S = os.path.dirname(os.path.abspath(__file__))
A = os.path.normpath(f"{S}/../../assets")
WORK = os.environ.get('TINT_WORK', '/tmp/detaillab-video/tint')
SRC = os.environ.get('TINT_SRC', f"{WORK}/src")
OUT = f"{WORK}/out_{VAR}"; os.makedirs(OUT, exist_ok=True)
FPS = 30
END_DUR = 3.4
TAIL = 0.2
MAIN = '2504'
W = json.load(open(f"{WORK}/words_medium.json"))[MAIN]
HDR = open(f"{S}/../grade_hdr_to_sdr.txt").read().strip()   # первым: после zoompan zscale падает
LOOK = f"lut3d={A}/r5_light.cube,unsharp=5:5:0.4"
MUSIC_ID = '19CPc_GsOVXSTSU7amm4dPYcFdRAPm0Eq'  # «музыка и звуки», Chill Coffee Flow (другой трек, чем в историях)
MUSIC_DB = -30                                     # тише: клиент просил


def run(cmd):
    subprocess.run(cmd, check=True)


# ---------- куски голоса: из слов, паузы ≤ ~0.3 с ----------
def wav16(path):
    import numpy as np, wave
    wf = wave.open(path)
    return np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def energy():
    import numpy as np
    x = wav16(f"{WORK}/wav/{MAIN}.wav"); h = 160
    return 20 * np.log10(np.sqrt((x[:len(x) // h * h].reshape(-1, h) ** 2).mean(1)) + 1e-9)


DB = energy()


def onset(t, lo):
    """Whisper ставит начало слова поздно — ищем реальное начало звука перед ним."""
    i0, i1 = max(int((t - 0.35) * 100), int(lo * 100)), int((t + 0.03) * 100)
    q = None
    for i in range(i0, i1):
        if DB[i] < -60:
            q = i
        elif DB[i] > -50 and q is not None:
            return min(t, i / 100)
    return t


def ranges_from_words(a, b, gap=0.35):
    ws = [w for w in W if a <= w[0] < b]
    out, cur = [], None
    for w in ws:
        if cur and w[0] - cur[1] <= gap:
            cur[1] = w[1]
        else:
            if cur:
                out.append(cur)
            cur = [w[0], w[1]]
    if cur:
        out.append(cur)
    res = []
    for s, e in out:
        s = onset(s, res[-1][1] if res else a) - 0.06
        e += 0.15
        # Whisper ошибается на 0.1–0.5 с: расширяем кусок по реальному звуку до тишины (начало ≤0.4 с, конец ≤0.35 с)
        lo = res[-1][1] if res else a
        k = 0
        while k < 40 and s - 0.01 > lo and DB[int((s - 0.01) * 100)] > -44:
            s -= 0.01; k += 1
        k = 0
        while k < 35 and e + 0.01 < b and DB[int(e * 100)] > -44:
            e += 0.01; k += 1
        s, e = max(a, s), min(b, e)
        if res and s - res[-1][1] < 0.12:      # слиплись — один кусок
            res[-1][1] = e
        else:
            res.append([s, e])
    # Whisper растягивает слова на паузы — режем ещё и по реальной тишине (≥0.35 с тише −50 дБ), запас 0.1 с
    out = []
    for s, e in res:
        cur, i, i1 = s, int(s * 100), int(e * 100)
        while i < i1:
            if DB[i] < -50:
                j = i
                while j < i1 and DB[j] < -50:
                    j += 1
                if j - i >= 35 and j < i1:
                    out.append([cur, i / 100 + 0.1]); cur = j / 100 - 0.1
                i = j
            else:
                i += 1
        out.append([cur, e])
    return [r for r in out if r[1] - r[0] > 0.15]


VID_END = 91.5
HOOK_R = (55.6, 58.5)          # «За полтора-два часа мы можем затонировать вашу машину»
BODY = [(1.6, VID_END)]        # «Давай.» (команда оператору) не берём
if HOOK:
    BODY = [(1.6, HOOK_R[0]), (HOOK_R[1], VID_END)]  # фраза хука второй раз не звучит

pieces, t = [], 0.0            # (clip, s, e, out)
def add(a, b):
    global t
    for s, e in ranges_from_words(a, b):
        n = max(1, round((e - s) * FPS))
        pieces.append((MAIN, s, s + n / FPS, t)); t += n / FPS

TAIL_AT = None
if HOOK:
    add(*HOOK_R)
    TAIL_AT = t; t += TAIL
for a, b in BODY:
    add(a, b)
VOICE_END = t
TOTAL = VOICE_END + END_DUR
FLASH = (TAIL_AT + TAIL) if HOOK else None


def omap(ts):
    """время в исходнике → время в ролике; в вырезанной паузе — начало следующего куска"""
    for pc, s, e, o in pieces:
        if s - 0.2 <= ts < e:
            return o + max(0.0, ts - s)
    nxt = [(s, o) for pc, s, e, o in pieces if s > ts]
    return min(nxt)[1] if nxt else None


def word(txt, k=1):
    n = 0
    for w in W:
        if w[2].lower().strip('.,…?!') == txt.lower():
            n += 1
            if n == k:
                r = omap(w[0])
                if r is None:
                    raise KeyError((txt, k))
                return r
    raise KeyError((txt, k))


def has(txt, k=1):
    try:
        word(txt, k); return True
    except KeyError:
        return False


def snap(x):
    return round(x * FPS) / FPS


# ---------- раскадровка ----------
# ('wide'|'close'|'punch') — спикер; ('b', clip, src_start, fallback) — подсъём в родной скорости
SH = []
if HOOK:
    SH += [(0.0, 'b', '2528', 0.3, 'close'),          # вода на стекле, мастер за стеклом
           (word('часа'), 'hook'),                     # склейка на спикера + наезд
           (TAIL_AT, 'tail')]
SH += [(word('итак'), 'wide'),
       (word('сегодня'), 'close'),
       (word('geely'), 'b', '2537', 0.4, 'wide'),     # синяя Geely с тёмным стеклом
       (word('поэтому'), 'wide'),
       (word('знайте'), 'close'),
       (word('процесс'), 'b', '2527', 0.2, 'wide'),   # вода на стекле
       (word('тонировщик'), 'b', '2528', 0.0, 'wide'),
       (word('значит'), 'close'),
       (word('для'), 'b', '2522', 0.3, 'wide'),       # бумага на двери
       (word('карты'), 'b', '2526', 0.4, 'wide'),
       (word('хочется'), 'wide'),
       (word('принципе'), 'close'),
       (word('получается'), 'b', '2534', 0.5, 'wide'),  # выгонка воды
       (word('сколько'), 'wide'),
       (word('по', 2), 'close'),
       (word('поэтому', 2), 'b', '2530', 0.2, 'wide'),   # выкройка на стекле
       (word('клеятся'), 'b', '2532', 0.3, 'wide'),      # плёнка на стекло
       (word('соответственно'), 'close'),
       ]
if not HOOK:
    SH += [(word('за'), 'punch')]                      # «За полтора-два часа…» — наезд
SH += [(word('с', 2), 'b', '2505', 0.2, 'wide'),       # «С учётом… подготовки»: мойка стекла
       (word('думаю'), 'close'),
       (word('красивый'), 'b', '2536', 0.3, 'wide'),
       (word('котором'), 'wide'),
       (word('солнечные'), 'b', '2535', 1.0, 'wide'),
       (word('тонируем'), 'close'),
       (word('лучшая'), 'b', '2533', 0.2, 'wide'),
       (word('просто'), 'wide'),
       (word('будете'), 'punch'),
       (word('приезжайте'), 'close'),
       (VOICE_END, 'end')]
SH = sorted([(snap(x[0]),) + x[1:] for x in SH], key=lambda x: x[0])


def split_long(sh, end, maxlen=3.2):
    """план спикера длиннее maxlen — меняем общий ↔ крупный на слове ближе к середине"""
    wt = sorted(snap(omap(w[0])) for w in W if omap(w[0]) is not None)
    out = []
    for i, x in enumerate(sh):
        out.append(x)
        b = sh[i + 1][0] if i + 1 < len(sh) else end
        if x[1] not in ('wide', 'close'):
            continue
        a, kind = x[0], x[1]
        while b - a > maxlen:
            mid = a + (b - a) / 2 if b - a < 2 * maxlen else a + maxlen * 0.75
            cand = [t for t in wt if a + 1.2 < t < b - 1.2]
            if not cand:
                break
            t = min(cand, key=lambda t: abs(t - mid))
            kind = 'close' if kind == 'wide' else 'wide'
            out.append((t, kind)); a = t
    return out


SH = split_long(SH, snap(VOICE_END))
SH[0] = (0.0,) + SH[0][1:]   # первый план — с первого кадра

FACE = (0.44, 0.30)
ZC = 1.42
DUR = {}


def dur(c):
    if c not in DUR:
        DUR[c] = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                                '-of', 'csv=p=0', f"{SRC}/IMG_{c}.MOV"]))
    return DUR[c]


idx = 0
def render(src, ss, nfr, vf, post=''):
    global idx
    out = f"{OUT}/seg{idx:03d}.mp4"; idx += 1
    run(['ffmpeg', '-v', 'error', '-y', '-ss', f"{ss:.3f}", '-i', src, '-an',
         '-vf', f"{HDR},{vf},scale=1080:1920:flags=lanczos,setsar=1,fps={FPS},{LOOK}{post},format=yuv420p",
         '-frames:v', str(nfr), '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', out])
    return out


def crop(kind):
    if kind == 'wide':
        return "crop=iw:ih"
    fx, fy = FACE
    return (f"crop=iw/{ZC}:ih/{ZC}:'max(0,min(iw-iw/{ZC},iw*{fx}-iw/{ZC}/2))':"
            f"'max(0,min(ih-ih/{ZC},ih*{fy}-ih/{ZC}*0.30))'")


def zoom(z0, z1, nfr, off=0, tot=None):
    fx, fy = FACE
    tot = tot or nfr
    z = f"({z0}+({z1}-{z0})*(1-cos(PI*(on+{off})/{max(1, tot - 1)}))/2)"
    return (f"scale=2160:3840,zoompan=z='{z}':d=1:s=2160x3840:fps={FPS}:"
            f"x='max(0,min(iw-iw/zoom,iw*{fx}-iw/zoom/2))':y='max(0,min(ih-ih/zoom,ih*{fy}-ih/zoom*0.30))'")


segfiles = []
def speaker(a, b, kind, post_first=''):
    first = True
    for pc, s, e, o in pieces:
        lo, hi = max(a, o), min(b, o + (e - s))
        nfr = round((hi - lo) * FPS)
        if nfr <= 0:
            continue
        vf = crop(kind) if kind != 'punch' else zoom(1.0, 1.18, nfr)
        segfiles.append(render(f"{SRC}/IMG_{pc}.MOV", s + (lo - o), nfr, vf, post=post_first if first else ''))
        first = False


def build_video():
    hook_n = {}
    for i, sh in enumerate(SH):
        a = sh[0]
        b = SH[i + 1][0] if i + 1 < len(SH) else snap(TOTAL)
        kind = sh[1]
        nfr = round((b - a) * FPS)
        if nfr <= 0:
            continue
        flash_in = ",fade=t=in:st=0:d=0.22:color=white" if i > 0 and SH[i - 1][1] == 'tail' else ''
        if kind == 'end':
            segfiles.append(render(f"{SRC}/IMG_2537.MOV", 0.3, nfr,
                                   f"crop=iw/1.08:ih/1.08,tpad=stop_mode=clone:stop_duration={END_DUR},"
                                   f"scale=2160:3840,zoompan=z='1+0.08*on/{nfr}':d=1:s=2160x3840:fps={FPS}:"
                                   f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"))
        elif kind == 'hook':
            hook_n['tot'] = nfr + round(TAIL * FPS)
            speaker_hook = [p for p in pieces if p[3] < TAIL_AT]
            done = 0
            for pc, s, e, o in speaker_hook:
                lo, hi = max(a, o), min(b, o + (e - s))
                k = round((hi - lo) * FPS)
                if k > 0:
                    segfiles.append(render(f"{SRC}/IMG_{pc}.MOV", s + (lo - o), k,
                                           zoom(1.36, 1.46, k, done, hook_n['tot'])))
                    done += k
            hook_n['n'] = done
        elif kind == 'tail':
            pc, s, e, o = [p for p in pieces if p[3] < TAIL_AT][-1]
            segfiles.append(render(f"{SRC}/IMG_{pc}.MOV", e, nfr,
                                   zoom(1.36, 1.46, nfr, hook_n['n'], hook_n['tot']),
                                   post=f",fade=t=out:st={(nfr - 4) / FPS:.3f}:d={4 / FPS:.3f}:color=white"))
        elif kind == 'b':
            _, _, c, ss, fb = sh
            nb = min(nfr, int((dur(c) - ss - 0.05) * FPS))
            segfiles.append(render(f"{SRC}/IMG_{c}.MOV", ss, nb, "crop=iw/1.06:ih/1.06", post=flash_in))
            if nb < nfr:
                speaker(a + nb / FPS, b, fb)
        else:
            speaker(a, b, kind, post_first=flash_in)
        print(f"shot {i} {kind} {a:.2f}-{b:.2f}", flush=True)
    with open(f"{OUT}/list.txt", 'w') as f:
        f.writelines(f"file '{p}'\n" for p in segfiles)
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f"{OUT}/list.txt",
         '-c', 'copy', f"{OUT}/video_raw.mp4"])


# ---------- звук ----------
def build_audio():
    f, ins = [], []
    for i, (c, s, e, o) in enumerate(pieces):
        ins += ['-i', f"{SRC}/IMG_{c}.MOV"]
        d = e - s
        f.append(f"[{i}:a]atrim={s:.4f}:{e:.4f},asetpts=PTS-STARTPTS,aresample=48000,"
                 f"aformat=channel_layouts=mono,afade=t=in:d=0.012,afade=t=out:st={d - 0.02:.4f}:d=0.02,"
                 f"adelay={int(round(o * 1000))}:all=1[v{i}]")
    n = len(pieces)
    f.append(''.join(f"[v{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,"
             f"highpass=f=80,arnndn=m={A}/sh.rnnn:mix=1,"
             "agate=threshold=0.02:ratio=4:attack=5:release=200:range=0.12,lowpass=f=14000,"
             "acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2,"
             f"apad=whole_dur={TOTAL:.3f},atrim=0:{TOTAL:.3f},asplit=2[voice][key]")
    music = f"{WORK}/music_{MUSIC_ID[:6]}.wav"
    if not os.path.exists(music):
        run(['curl', '-sSL', '-o', f"{WORK}/music_src_{MUSIC_ID[:6]}.mov",
             f"https://drive.usercontent.google.com/download?id={MUSIC_ID}&export=download&confirm=t"])
        run(['ffmpeg', '-v', 'error', '-y', '-i', f"{WORK}/music_src_{MUSIC_ID[:6]}.mov", '-vn', '-ac', '2', '-ar', '48000', music])
    ins += ['-ss', '8', '-i', music]
    f.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,volume={MUSIC_DB}dB,"
             f"afade=t=in:d=0.4,afade=t=out:st={TOTAL - 1.2:.3f}:d=1.2,apad,atrim=0:{TOTAL:.3f}[mus]")
    f.append("[key]aformat=channel_layouts=stereo[keys];"
             "[mus][keys]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350:makeup=1[musd]")
    sfx = []
    if HOOK:
        sfx += [('riser_hook', 0.0, -31), ('hit2', FLASH - 0.03, -5)]
    for t0, kind in [(x[0], x[1]) for x in SH]:
        if kind == 'b' and t0 > (FLASH or 0) + 0.3:
            sfx.append(('hit4', t0, -27))                 # тихий щелчок на подсъёме
        if kind == 'punch':
            sfx.append(('hit1', t0, -24))
    for nm, t0, g in GFX_SFX:
        sfx.append((nm, t0, g))
    sfx.append(('hit5', VOICE_END + 0.1, -18))
    PEAK = {'hit1': 0.21, 'hit2': 0.19, 'hit3': 0.225, 'hit4': 0.115, 'hit5': 0.215}
    k = n + 1
    mix = ['[voice]', '[musd]']
    for j, (nm, t0, g) in enumerate(sfx):
        ins += ['-i', f"{S}/../sfx/{nm}.wav"]
        extra = f"afade=t=out:st={FLASH - t0 - 0.02:.3f}:d=0.06," if nm == 'riser_hook' else ''
        t0 -= PEAK.get(nm, 0.0)
        trim = ''
        if t0 < 0:
            trim = f"atrim=start={-t0:.3f},asetpts=PTS-STARTPTS,"; t0 = 0
        f.append(f"[{k}:a]{trim}{extra}volume={g}dB,adelay={int(t0 * 1000)}:all=1,"
                 f"aformat=channel_layouts=stereo,aresample=48000[s{j}]")
        mix.append(f"[s{j}]"); k += 1
    f.append(''.join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,"
             f"atrim=0:{TOTAL:.3f},loudnorm=I=-14:TP=-1.0:LRA=9,aresample=48000[aout]")
    run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(f),
         '-map', '[aout]', '-ar', '48000', '-ac', '2', f"{OUT}/audio.wav"])


# ---------- субтитры и 2D-графика ----------
GOLD = '&H37AFD4&'; GOLD2 = '&H5CC8E8&'
X1, X2 = 180, 900              # безопасная зона TikTok: плашки по центру, не правее x=900
FIX = {'geely': 'GEELY', 'mclaren': 'GEELY', 'quantum': 'QUANTUM', 'dt': 'DETAIL', 'lab': 'LAB',
       'отсталкиваются': 'отстёгиваются', 'отмалили': 'отмыли', 'все': 'всё', 'учётом': 'учётом',
       'плёнка': 'плёнка', 'часика': 'часика', 'до': 'в'}
GOLDW = {'geely', 'quantum', '5', 'минимальный', 'разбор', 'сложностей', 'полтора', 'полтора-два', 'часа',
         'четыре', 'салон', 'лучшая', 'цена-качество', 'шоколаде', 'lab', 'тонировке', 'результат'}
SHORT = {'в', 'у', 'на', 'и', 'по', 'за', 'мы', 'из', 'а', 'под', 'нам', 'нас', 'с', 'о', 'к', 'не', 'то', 'это'}
GFX_SFX = []


def ts(x):
    x = max(0, x); h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def caption_events():
    ws = []
    for w in W:
        t0 = omap(w[0])
        if t0 is None or not any(s - 0.2 <= w[0] < e for _, s, e, _ in pieces):
            continue
        raw = w[2].strip('.,…?!').lower()
        if raw in ('давай',):
            continue
        if raw.startswith('-') and ws:
            ws[-1][1] += raw.upper(); continue
        if raw == 'dt':
            raw = 'detail'
        txt = FIX.get(raw, raw).upper()
        if raw == 'lab' and ws and ws[-1][1] == 'DETAIL':
            ws[-1][1] = 'DETAILLAB'; ws[-1][2] = True; continue
        if raw == '%' and ws:
            ws[-1][1] += '%'; continue
        ws.append([t0, txt, raw in GOLDW])
    groups, i = [], 0
    while i < len(ws):
        g = [ws[i]]
        while g[-1][1].lower() in SHORT and i + 1 < len(ws) and len(g) < 3:
            i += 1; g.append(ws[i])
        groups.append(g); i += 1
    ev = []
    for j, g in enumerate(groups):
        st = max(0, g[0][0] - 0.06)
        en = groups[j + 1][0][0] - 0.06 if j + 1 < len(groups) else VOICE_END
        en = min(en, st + 1.4, VOICE_END)
        if FLASH and st < FLASH <= en:
            en = FLASH - 0.05
        txt = ' '.join((f"{{\\c{GOLD}}}{w[1]}{{\\c&HFFFFFF&}}" if w[2] else w[1]) for w in g)
        ev.append((st, en, txt))
    return ev


def box(x1, y1, x2, y2, r=26):
    return (f"m {x1 + r} {y1} l {x2 - r} {y1} b {x2} {y1} {x2} {y1} {x2} {y1 + r} l {x2} {y2 - r} "
            f"b {x2} {y2} {x2} {y2} {x2 - r} {y2} l {x1 + r} {y2} b {x1} {y2} {x1} {y2} {x1} {y2 - r} "
            f"l {x1} {y1 + r} b {x1} {y1} {x1} {y1} {x1 + r} {y1}")


def circle(cx, cy, r):
    k = 0.5523 * r
    return (f"m {cx} {cy - r} b {cx + k} {cy - r} {cx + r} {cy - k} {cx + r} {cy} b {cx + r} {cy + k} {cx + k} {cy + r} {cx} {cy + r} "
            f"b {cx - k} {cy + r} {cx - r} {cy + k} {cx - r} {cy} b {cx - r} {cy - k} {cx - k} {cy - r} {cx} {cy - r}")


def check(x, y, s=1.0):
    return f"m {x} {y + 14 * s} l {x + 10 * s} {y + 26 * s} l {x + 30 * s} {y} l {x + 34 * s} {y + 4 * s} l {x + 10 * s} {y + 34 * s} l {x - 4 * s} {y + 18 * s}"


def sun(cx, cy, r):
    d = circle(cx, cy, r)
    import math
    for k in range(8):
        a = k * math.pi / 4
        x0, y0 = cx + math.cos(a) * (r + 12), cy + math.sin(a) * (r + 12)
        x1, y1 = cx + math.cos(a) * (r + 34), cy + math.sin(a) * (r + 34)
        nx, ny = -math.sin(a) * 5, math.cos(a) * 5
        d += f" m {x0 + nx:.0f} {y0 + ny:.0f} l {x1 + nx:.0f} {y1 + ny:.0f} l {x1 - nx:.0f} {y1 - ny:.0f} l {x0 - nx:.0f} {y0 - ny:.0f}"
    return d


STYLE_FONT = {'Huge': ('Oswald-Bold.ttf', 230, 0), 'Days': ('Montserrat-ExtraBold.ttf', 64, 2),
              'Item2': ('Montserrat-ExtraBold.ttf', 54, 1), 'Item': ('Montserrat-ExtraBold.ttf', 40, 1),
              'Big': ('Oswald-Bold.ttf', 116, 3), 'Small': ('Montserrat-ExtraBold.ttf', 46, 4)}

LIBASS_K = {'Oswald-Bold.ttf': 0.564, 'Montserrat-ExtraBold.ttf': 0.643}


def tw(style, text):
    """ширина строки в пикселях кадра — как её нарисует libass (шрифт и межбуквенный интервал стиля)"""
    from PIL import ImageFont
    f, size, sp = STYLE_FONT[style]
    font = ImageFont.truetype(f"{A}/fonts/{f}", size)
    k = LIBASS_K[f]                  # libass рисует шрифт мельче, чем PIL того же размера (замерено)
    x0, _, x1, _ = font.getbbox(text)
    return (x1 - x0) * k + sp * (len(text) - 1)


def build_ass():
    L = []
    def D(layer, a, b, style, text):
        L.append(f"Dialogue: {layer},{ts(a)},{ts(b)},{style},,0,0,0,,{text}")
    shape = lambda d: f"{{\\p1}}{d}{{\\p0}}"
    pop = "\\fad(160,200)\\fscx90\\fscy90\\t(0,200,\\fscx100\\fscy100)"
    panel = lambda a, b, y1, y2: D(1, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c&H0E0E0E&\\1a&H48&\\3c{GOLD}\\bord3\\shad0\\fad(180,200)}}" + shape(box(X1, y1, X2, y2)))

    for st, en, txt in caption_events():
        D(5, st, en, 'Cap', f"{{\\pos(540,1040)\\fad(40,0)\\fscx88\\fscy88\\t(0,110,\\fscx100\\fscy100)}}{txt}")

    # Раскладка считается по реальной ширине текста (PIL с теми же шрифтами), группа «иконка + текст»
    # центрируется по x=540 внутри плашки X1..X2, по вертикали — по центру плашки.
    def row(icon_w, lines, gap=34):
        w = icon_w + (gap if icon_w else 0) + max(tw(st, tx) for st, tx in lines)
        x0 = round(540 - w / 2)
        return x0, x0 + icon_w + (gap if icon_w else 0)

    def two_lines(a1, a2, b, x, cy, top, bottom, d=42):
        (st1, tx1, c1), (st2, tx2, c2) = top, bottom
        D(2, a1, b, st1, f"{{\\an4\\pos({x},{cy - d})\\c{c1}\\fad(200,200)}}{tx1}")
        D(2, a2, b, st2, f"{{\\an4\\pos({x},{cy + d})\\c{c2}\\fad(200,200)}}{tx2}")

    WHITE = '&HFFFFFF&'
    PANEL_BIG, PANEL_LOW = (1140, 1400), (1150, 1330)

    def check_icon(a, b, cx, cy):
        D(2, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c{GOLD}\\bord0\\shad0{pop}\\org({cx},{cy})}}" + shape(circle(cx, cy, 44)))
        D(3, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c&H101010&\\bord0\\shad0\\fad(160,200)}}" + shape(check(cx - 16, cy - 18, 1.0)))

    # 1) 5 % · ПЛЁНКА QUANTUM
    a = word('5') - 0.05; b = word('для') - 0.1
    y1, y2 = PANEL_BIG; cy = (y1 + y2) // 2
    panel(a, b, y1, y2)
    x0, xt = row(tw('Huge', '5%'), [('Days', 'ПЛЁНКА'), ('Days', 'QUANTUM')], gap=30)
    D(2, a, b, 'Huge', f"{{\\an4\\pos({x0},{cy})\\c{GOLD}{pop}}}5%")
    two_lines(a + 0.25, word('quantum') - 0.05, b, xt, cy, ('Days', 'ПЛЁНКА', WHITE), ('Days', 'QUANTUM', GOLD))
    GFX_SFX.extend([('hit3', a, -20), ('hit1', word('quantum'), -24)])

    # 2) Минимальный разбор, 3) Без сложностей — галочка
    for w0, w1, t1, t2, snd in [('минимальный', 'карты', 'МИНИМАЛЬНЫЙ', 'РАЗБОР', 'hit3'),
                                ('никаких', 'получается', 'БЕЗ', 'СЛОЖНОСТЕЙ', 'hit1')]:
        a = word(w0) - 0.05; b = word(w1) - 0.05
        y1, y2 = PANEL_LOW; cy = (y1 + y2) // 2
        panel(a, b, y1, y2)
        x0, xt = row(88, [('Item2', t1), ('Item2', t2)])
        check_icon(a, b, x0 + 44, cy)
        two_lines(a, a, b, xt, cy, ('Item2', t1, WHITE), ('Item2', t2, GOLD), d=32)
        GFX_SFX.append((snd, a, -22))

    # 4) Таймер «1,5 часа» — часы контуром, стрелка крутится
    a = word('полтора') - 0.05; b = word('поэтому', 2) - 0.05
    y1, y2 = PANEL_BIG; cy = (y1 + y2) // 2
    panel(a, b, y1, y2)
    R = 70
    x0, xt = row(2 * R, [('Days', '1,5 ЧАСА'), ('Item2', 'НА ТОНИРОВКУ')])
    cx = x0 + R
    D(2, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1a&HFF&\\3c{GOLD}\\bord8\\shad0{pop}\\org({cx},{cy})}}" + shape(circle(cx, cy, R - 4)))
    D(3, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c{GOLD}\\bord0\\shad0\\fad(160,200)}}" + shape(circle(cx, cy, 8)))
    D(3, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c{GOLD}\\bord0\\shad0\\fad(160,200)}}"
      + shape(f"m {cx - 4} {cy} l {cx - 4} {cy - R + 26} l {cx + 4} {cy - R + 26} l {cx + 4} {cy}"))
    D(3, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c{GOLD}\\bord0\\shad0\\fad(160,200)\\org({cx},{cy})\\frz0\\t(0,{int((b - a) * 1000)},\\frz-270)}}"
      + shape(f"m {cx} {cy - 4} l {cx + R - 22} {cy - 4} l {cx + R - 22} {cy + 4} l {cx} {cy + 4}"))
    two_lines(a + 0.1, a + 0.3, b, xt, cy, ('Days', '1,5 ЧАСА', GOLD), ('Item2', 'НА ТОНИРОВКУ', WHITE))
    GFX_SFX.append(('hit3', a, -20))

    # 5) (без хука) «За 1,5–2 часа»
    if not HOOK:
        a = word('за') - 0.05; b = word('с', 2) - 0.1
        y1, y2 = PANEL_LOW; cy = (y1 + y2) // 2
        panel(a, b, y1, y2)
        D(2, a, b, 'Days', f"{{\\an5\\pos(540,{cy})\\c{GOLD}{pop}}}1,5–2 ЧАСА")
        GFX_SFX.append(('hit1', a, -24))

    # 6) «4 часа с подготовкой»
    a = word('четыре') - 0.05; b = word('красивый') - 0.05
    y1, y2 = PANEL_BIG; cy = (y1 + y2) // 2
    panel(a, b, y1, y2)
    x0, xt = row(tw('Huge', '4'), [('Days', 'ЧАСА'), ('Item2', 'С ПОДГОТОВКОЙ')], gap=30)
    D(2, a, b, 'Huge', f"{{\\an4\\pos({x0},{cy})\\c{GOLD}{pop}}}4")
    two_lines(a + 0.2, a + 0.35, b, xt, cy, ('Days', 'ЧАСА', WHITE), ('Item2', 'С ПОДГОТОВКОЙ', WHITE))
    GFX_SFX.append(('hit3', a, -20))

    # 7) Солнце — салон не выгорает
    a = word('солнечные') - 0.05; b = word('тонируем') - 0.05
    y1, y2 = PANEL_BIG; cy = (y1 + y2) // 2
    panel(a, b, y1, y2)
    x0, xt = row(150, [('Item2', 'САЛОН'), ('Days', 'НЕ ВЫГОРАЕТ')], gap=30)
    cx = x0 + 75
    D(2, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c{GOLD}\\bord0\\shad0{pop}\\org({cx},{cy})\\t(0,{int((b - a) * 1000)},\\frz40)}}" + shape(sun(cx, cy, 36)))
    two_lines(a + 0.15, a + 0.3, b, xt, cy, ('Item2', 'САЛОН', WHITE), ('Days', 'НЕ ВЫГОРАЕТ', GOLD))
    GFX_SFX.append(('hit1', a, -24))

    # 8) QUANTUM — цена/качество
    a = word('quantum', 2) - 0.05; b = word('ну') - 0.05 if has('ну') else word('будете') - 0.1
    panel(a, b, 1130, 1420)
    D(2, a, b, 'Small', f"{{\\an5\\pos(540,1185)\\fad(200,200)}}ПЛЁНКИ")
    D(2, a, b, 'Big', f"{{\\an5\\pos(540,1272)\\c{GOLD}{pop}}}QUANTUM")
    t1 = word('цена') - 0.05
    x0, xt = row(44, [('Item', 'ЦЕНА · КАЧЕСТВО')], gap=16)
    D(2, t1, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c{GOLD}\\bord0\\shad0\\fad(150,200)}}" + shape(circle(x0 + 22, 1365, 22)))
    D(3, t1, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c&H101010&\\bord0\\shad0\\fad(150,200)}}" + shape(check(x0 + 8, 1352, 0.78)))
    D(2, t1, b, 'Item', f"{{\\an4\\pos({xt},1365)\\fad(150,200)}}ЦЕНА · КАЧЕСТВО")
    GFX_SFX.extend([('hit3', a, -20), ('hit4', t1, -24)])

    # концовка
    a = VOICE_END; b = TOTAL
    D(3, a + 0.15, b, 'Shape', f"{{\\an7\\pos(0,0)\\1a&HFF&\\3c{GOLD}\\bord5\\shad0\\fad(400,0)}}" + shape(circle(540, 700, 268)))
    D(4, a + 0.45, b, 'Cta', f"{{\\pos(540,1110)\\c{GOLD}\\fad(250,0)\\fscx90\\fscy90\\t(0,200,\\fscx100\\fscy100)}}ПИШИТЕ В DIRECT")
    D(4, a + 0.65, b, 'Small', f"{{\\pos(540,1200)\\fad(250,0)}}РАССЧИТАЕМ СТОИМОСТЬ")
    pin = "m 0 -28 b 16 -28 26 -16 26 -2 b 26 14 0 40 0 40 b 0 40 -26 14 -26 -2 b -26 -16 -16 -28 0 -28 m 0 -12 b -7 -12 -11 -7 -11 -2 b -11 5 -7 9 0 9 b 7 9 11 5 11 -2 b 11 -7 7 -12 0 -12"
    D(4, a + 0.85, b, 'Shape', f"{{\\an7\\pos(205,1330)\\1c{GOLD}\\bord0\\shad0\\fad(250,0)}}" + shape(pin))
    D(4, a + 0.85, b, 'Addr', f"{{\\an4\\pos(250,1335)\\fad(250,0)}}ПР-Т ДЗЕРЖИНСКОГО, 82А")
    D(4, a + 0.95, b, 'Tiny', f"{{\\pos(540,1405)\\fad(250,0)}}МИНСК · 9:00–21:00 · БЕЗ ВЫХОДНЫХ")

    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat ExtraBold,88,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,1,0,1,0,6,5,70,70,0,1
Style: Shape,Arial,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Small,Montserrat ExtraBold,46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,4,0,1,0,3,5,0,0,0,1
Style: Big,Oswald,116,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,3,0,1,0,4,5,0,0,0,1
Style: Item,Montserrat ExtraBold,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,0,2,4,0,0,0,1
Style: Item2,Montserrat ExtraBold,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,0,2,4,0,0,0,1
Style: Huge,Oswald,230,&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,0,0,0,0,100,100,0,0,1,0,6,5,0,0,0,1
Style: Days,Montserrat ExtraBold,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,3,4,0,0,0,1
Style: Cta,Oswald,120,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,4,5,0,0,0,1
Style: Addr,Montserrat ExtraBold,50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,0,3,4,0,0,0,1
Style: Tiny,Montserrat ExtraBold,36,&H00C8C8C8,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,3,0,1,0,2,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    open(f"{OUT}/subs.ass", 'w').write(head + '\n'.join(L) + '\n')


def final():
    a = VOICE_END
    logo = (f"[1:v]scale=500:500,format=rgba,eq=brightness=0.07:contrast=1.18:saturation=1.25:gamma=1.08,"
            f"geq=r='min(255,r(X,Y)+150*exp(-pow((X+0.6*Y-(T-{a + 0.9:.3f})*1100)/45,2)))':"
            f"g='min(255,g(X,Y)+140*exp(-pow((X+0.6*Y-(T-{a + 0.9:.3f})*1100)/45,2)))':"
            f"b='min(255,b(X,Y)+110*exp(-pow((X+0.6*Y-(T-{a + 0.9:.3f})*1100)/45,2)))':a='alpha(X,Y)',"
            f"fade=t=in:st={a + 0.1:.3f}:d=0.45:alpha=1[lg]")
    fc = (f"{logo};[0:v]drawbox=x=0:y=0:w=iw:h=ih:color=black@0.45:t=fill:enable='gte(t,{a:.3f})'[bg];"
          f"[bg][lg]overlay=290:450:enable='gte(t,{a + 0.1:.3f})'[v1];"
          f"[v1]subtitles={OUT}/subs.ass:fontsdir={A}/fonts,format=yuv420p[v]")
    name = f"{WORK}/DetailLab_Tonirovka_Geely_{'s_hukom' if HOOK else 'bez_huka'}.mp4"
    run(['ffmpeg', '-v', 'error', '-y', '-i', f"{OUT}/video_raw.mp4",
         '-loop', '1', '-framerate', '30', '-t', f"{TOTAL:.3f}", '-i', f"{S}/../brand/logo.png",
         '-i', f"{OUT}/audio.wav", '-filter_complex', fc, '-map', '[v]', '-map', '2:a',
         '-c:v', 'libx264', '-preset', 'slow', '-b:v', '5500k', '-maxrate', '7M', '-bufsize', '14M',  # ~60 МБ: больше не скачивалось
         '-profile:v', 'high', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', name])
    print("OUT", name)
    return name


def stories(name):
    """сторис: 5 частей по смыслу, режем перед началом фразы"""
    cuts = [0.0] + [max(0.0, word(*w) - 0.12) for w in STORY_CUTS] + [TOTAL]
    for k in range(len(cuts) - 1):
        out = f"{WORK}/DetailLab_Tonirovka_Geely_Story_{k + 1}.mp4"
        run(['ffmpeg', '-v', 'error', '-y', '-ss', f"{cuts[k]:.3f}", '-i', name, '-t', f"{cuts[k + 1] - cuts[k]:.3f}",
             '-c:v', 'libx264', '-preset', 'slow', '-b:v', '6M', '-maxrate', '7M', '-bufsize', '14M', '-pix_fmt', 'yuv420p',
             '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out])
        print("STORY", k + 1, round(cuts[k + 1] - cuts[k], 2))


# 1) Geely, 5 %, Quantum  2) разбор, без сложностей  3) время 1,5–2 часа  4) 4 часа, результат, солнце  5) Quantum, концовка
STORY_CUTS = [('для',), ('сколько',), ('с', 2), ('тонируем',)]


if __name__ == '__main__':
    json.dump({'pieces': pieces, 'shots': [list(x) for x in SH], 'voice_end': VOICE_END, 'total': TOTAL},
              open(f"{OUT}/timeline.json", 'w'), ensure_ascii=False)
    print(VAR, "VOICE_END", round(VOICE_END, 2), "TOTAL", round(TOTAL, 2), "shots", len(SH), flush=True)
    if 'plan' in sys.argv:
        for x in SH:
            print(x)
        sys.exit()
    build_ass()       # заполняет GFX_SFX — до звука
    build_video()
    build_audio()
    name = final()
    if not HOOK:
        stories(name)
