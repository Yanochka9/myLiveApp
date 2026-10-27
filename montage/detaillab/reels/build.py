import json, subprocess, os, sys
S = os.path.dirname(os.path.abspath(__file__))
SRC = f"{S}/src"; OUT = f"{S}/out"; os.makedirs(OUT, exist_ok=True)
FPS = 30
W = json.load(open(f"{S}/words_medium.json"))
SEGS = json.load(open(f"{S}/segs.json"))
ORDER = ['1377', '1380', '1381', '1384', '1387']
END_DUR = 3.4
TAIL_SRC = 0.2           # seconds of source after the hook, at native speed
TAIL = TAIL_SRC          # beat between hook and the rest

# ---------- voice pieces, snapped to frames ----------
pieces = []  # (clip, s, e, out)
t = 0.0
for c in ORDER:
    for s, e in SEGS[c]:
        n = max(1, round((e - s) * FPS))
        pieces.append((c, s, s + n / FPS, t))
        t += n / FPS
    if c == '1377':
        TAIL_AT = t
        t += TAIL
VOICE_END = t
TOTAL = VOICE_END + END_DUR

def omap(c, ts):
    for pc, s, e, o in pieces:
        if pc == c and ts < e:
            return o + max(0.0, ts - s)
    raise ValueError((c, ts))

def word(c, txt, k=1):
    n = 0
    for w in W[c]:
        if w[2].lower().strip('.,…') == txt.lower():
            n += 1
            if n == k:
                return omap(c, w[0])
    raise KeyError((c, txt, k))

def snap(x): return round(x * FPS) / FPS

# ---------- shots ----------
# ('b', clip, src_start, fallback) b-roll at native speed; if the shot is longer
# than the clip, the remainder falls back to the speaker shot named in fallback
SH = [
    (0.0, 'b', '1389', 0.3, 'close'),
    (word('1377', 'бампер'), 'b', '1388', 0.2, 'close'),
    (word('1377', 'весь'), 'hook'),
    (TAIL_AT, 'tail'),
    (word('1380', 'сегодня'), 'wide'),
    (word('1380', 'приехал'), 'close'),
    (word('1380', 'комплекса'), 'wide'),
    (word('1380', 'из'), 'close'),
    (word('1380', 'передний'), 'b', '1390', 0.0, 'wide'),
    (word('1380', 'чтобы'), 'wide'),
    (word('1380', 'каждый'), 'b', '1399', 0.0, 'close'),
    (word('1380', 'нужно', 2), 'close'),
    (word('1380', 'пластиковые'), 'b', '1391', 0.0, 'close'),
    (word('1380', 'дабы'), 'wide'),
    (word('1380', 'заложить'), 'b', '1394', 0.0, 'close'),
    (word('1381', 'помимо'), 'close'),
    (word('1381', 'оптики'), 'b', '1395', 0.0, 'wide'),
    (word('1381', 'оклейка'), 'wide'),
    (word('1381', 'стоек'), 'b', '1393', 0.0, 'wide'),
    (word('1381', 'зеркал'), 'b', '1396', 0.0, 'wide'),
    (word('1381', 'кантика'), 'b', '1397', 0.0, 'wide'),
    (word('1381', 'дверей'), 'b', '1401', 0.0, 'wide'),
    (word('1381', 'внутренних'), 'b', '1398', 0.0, 'close'),
    (word('1381', 'погрузочные'), 'close'),
    (word('1384', 'данный'), 'close'),
    (word('1384', 'три'), 'wide'),
    (word('1384', 'который'), 'close'),
    (word('1384', 'оклейка'), 'b', '1400', 0.0, 'wide'),
    (word('1384', 'и'), 'wide'),
    (word('1387', 'а'), 'close'),
    (word('1387', 'пишите'), 'wide'),
    (VOICE_END, 'end'),
]
SH = [(snap(x[0]),) + x[1:] for x in SH]

FACE = {'1377': (0.62, 0.33), '1380': (0.62, 0.28), '1381': (0.42, 0.31),
        '1384': (0.45, 0.33), '1387': (0.55, 0.34)}
ZC = 1.42
GRADE = open(f"{S}/grade.txt").read().strip().replace("../assets", f"{S}/../assets")
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
           '-vf', f"{pre}{vf},scale=1080:1920:flags=lanczos,setsar=1,fps={FPS},{GRADE}{post},format=yuv420p",
           '-frames:v', str(nfr), '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', out]
    subprocess.run(cmd, check=True)
    return out

def spk_crop(c, kind):
    if kind == 'wide':
        return "crop=iw:ih"
    fx, fy = FACE[c]
    return (f"crop=iw/{ZC}:ih/{ZC}:'max(0,min(iw-iw/{ZC},iw*{fx}-iw/{ZC}/2))':"
            f"'max(0,min(ih-ih/{ZC},ih*{fy}-ih/{ZC}*0.30))'")

def zoom(c, z0, z1, nfr, off=0, tot=None):
    fx, fy = FACE[c]
    tot = tot or nfr
    z = f"({z0}+({z1}-{z0})*(1-cos(PI*(on+{off})/{max(1, tot-1)}))/2)"
    return (f"zoompan=z='{z}':d=1:s=2160x3840:fps={FPS}:"
            f"x='max(0,min(iw-iw/zoom,iw*{fx}-iw/zoom/2))':y='max(0,min(ih-ih/zoom,ih*{fy}-ih/zoom*0.30))'")

segfiles = []
def speaker(a, b, kind, post_first=''):
    """speaker footage for [a,b), split across voice pieces"""
    first = True
    for pc, s, e, o in pieces:
        lo, hi = max(a, o), min(b, o + (e - s))
        nfr = round((hi - lo) * FPS)
        if nfr <= 0:
            continue
        segfiles.append(render(f"{SRC}/IMG_{pc}.MOV", s + (lo - o), nfr, spk_crop(pc, kind),
                               post=post_first if first else ''))
        first = False

hook_z = (1.36, 1.46)
HOOK_N = {}
for i, sh in enumerate(SH):
    a = sh[0]
    b = SH[i + 1][0] if i + 1 < len(SH) else snap(TOTAL)
    kind = sh[1]
    nfr = round((b - a) * FPS)
    flash_in = ",fade=t=in:st=0:d=0.22:color=white" if i > 0 and SH[i - 1][1] == 'tail' else ''
    if kind == 'end':
        # native speed, then hold the last frame; slow push-in over the whole card
        segfiles.append(render(f"{SRC}/IMG_1392.MOV", 0.0, nfr,
                               f"crop=iw/1.08:ih/1.08,tpad=stop_mode=clone:stop_duration={END_DUR},"
                               f"scale=2160:3840,zoompan=z='1+0.08*on/{nfr}':d=1:s=2160x3840:fps={FPS}:"
                               f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"))
    elif kind == 'hook':
        pc, s, e, o = [p for p in pieces if p[0] == '1377'][-1]
        HOOK_N['n'] = nfr; HOOK_N['tot'] = nfr + round(TAIL * FPS)
        segfiles.append(render(f"{SRC}/IMG_1377.MOV", s + (a - o), nfr, zoom('1377', hook_z[0], hook_z[1], nfr, 0, HOOK_N['tot'])))
    elif kind == 'tail':
        pc, s, e, o = [p for p in pieces if p[0] == '1377'][-1]
        segfiles.append(render(f"{SRC}/IMG_1377.MOV", e, nfr,
                               zoom('1377', hook_z[0], hook_z[1], nfr, HOOK_N['n'], HOOK_N['tot']),
                               post=f",fade=t=out:st={(nfr-4)/FPS:.3f}:d={4/FPS:.3f}:color=white"))
    elif kind == 'b':
        _, _, c, ss, fb = sh
        avail = dur(c) - ss - 0.05
        nb = min(nfr, int(avail * FPS))
        segfiles.append(render(f"{SRC}/IMG_{c}.MOV", ss, nb, "crop=iw/1.06:ih/1.06", post=flash_in))
        if nb < nfr:
            speaker(a + nb / FPS, b, fb)
    else:
        speaker(a, b, kind, post_first=flash_in)
    print(f"shot {i} {kind} {a:.2f}-{b:.2f}", flush=True)

with open(f"{OUT}/list.txt", 'w') as f:
    for p in segfiles:
        f.write(f"file '{p}'\n")
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f"{OUT}/list.txt",
                '-c', 'copy', f"{OUT}/video_raw.mp4"], check=True)

json.dump({'pieces': pieces, 'shots': [list(x) for x in SH], 'voice_end': VOICE_END, 'total': TOTAL,
           'tail_at': TAIL_AT, 'tail': TAIL},
          open(f"{OUT}/timeline.json", 'w'), ensure_ascii=False)
print("VOICE_END", VOICE_END, "TOTAL", TOTAL, "TAIL_AT", TAIL_AT)
