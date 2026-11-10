"""AKPP Drive reels engine: multi-take A-roll, auto pause cutting, b-roll, gfx, subs, mix.

A reel config (lifan.py, ...) defines:
  NAME, HOOK, PHRASES, BROLL, ACCENT, WORDFIX, HIDE, gfx(R), sfx(R), END_Q
and calls lib.main(config_module).
All times in configs are SOURCE times of a given file; R.m(file, t) maps to output time.
"""
import json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

SP = os.environ.get('AKPP_SP', '/tmp/claude-0/-home-user-myLiveApp/cff86cd6-79d6-5f3c-9f9a-fd6975395de3/scratchpad')
SRC = SP + '/src'
STK = SP + '/stock'
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, '..', 'assets')
FPS = 30
PAD = 0.05          # air kept before speech at every cut
PAD_END = 0.11      # air kept after speech (soft word endings)
MIN_GAP = 0.16      # silences shorter than this stay
END_PLATE = 3.0


def fr(x):
    return round(x * FPS) / FPS


def path(name):
    for k in ('reels', 'broll'):
        p = f'{SRC}/{k}/IMG_{name}.MOV'
        if os.path.exists(p):
            return p
    if os.path.exists(f'{STK}/{name}'):
        return f'{STK}/{name}'
    raise FileNotFoundError(name)


# ---------------------------------------------------------------- speech islands
_sil_cache = {}


def silences(name, thr=-44):
    key = (name, thr)
    if key not in _sil_cache:
        cache = f'{SP}/work/sil_{name}_{-thr}.json'
        if os.path.exists(cache):
            _sil_cache[key] = json.load(open(cache))
        else:
            r = subprocess.run(['ffmpeg', '-i', f'{SP}/wav/IMG_{name}.wav', '-af',
                                f'silencedetect=n={thr}dB:d={MIN_GAP}', '-f', 'null', '-'],
                               capture_output=True, text=True).stderr
            st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r)]
            en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r)]
            sil = list(zip(st, en + [1e9] * (len(st) - len(en))))
            json.dump(sil, open(cache, 'w'))
            _sil_cache[key] = sil
    return _sil_cache[key]


def cut_phrase(name, a, b, thr=-44, keep=()):
    """Split [a,b] at silences; returns list of (a,b) speech pieces with PAD air.
    keep: list of (x,y) source ranges where silences must not be cut."""
    pieces, cur = [], a
    for s0, s1 in silences(name, thr):
        if s1 <= a or s0 >= b:
            continue
        if any(x <= s0 and s1 <= y for x, y in keep):
            continue
        s0c, s1c = max(s0, a), min(s1, b)
        if s0c <= a + 0.001:      # phrase starts in silence
            cur = max(cur, s1c - PAD)
            continue
        if s1c >= b - 0.001:      # phrase ends in silence
            pieces.append((cur, min(b, s0c + PAD_END)))
            cur = None
            break
        pieces.append((cur, s0c + PAD_END))
        cur = s1c - PAD
    if cur is not None and b - cur > 0.05:
        pieces.append((cur, b))
    res = []
    for x, y in pieces:
        if res and x < res[-1][1]:
            res[-1] = (res[-1][0], y); continue
        res.append((x, y))
    return [(fr(x), fr(y)) for x, y in res if y - x > 0.06]


def make_gap(name, dur):
    w = f'{SP}/wav/IMG_{name}.wav'
    if not os.path.exists(w):
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=16000:cl=mono',
                        '-t', f'{dur + 1:.2f}', w], check=True)
    tx = f'{SP}/tx/IMG_{name}.json'
    if not os.path.exists(tx):
        json.dump([], open(tx, 'w'))


# ---------------------------------------------------------------- reel timeline
class Reel:
    def __init__(self, C):
        self.C = C
        self.name = C.NAME
        self.B = f'{SP}/build/{self.name}'
        os.makedirs(self.B + '/shots', exist_ok=True)
        h = C.HOOK
        self.segs = []      # (file, a, b, phrase_index)
        for x in h.get('pieces') or cut_phrase(h['src'], h['a'], h['b'], h.get('thr', -44)):
            self.segs.append((h['src'], fr(x[0]), fr(x[1]), -1))
        for i, p in enumerate(C.PHRASES):
            name, a, b = p[:3]
            opt = p[3] if len(p) > 3 else {}
            if name.startswith('gap'):      # silent insert (meme etc.), covered by b-roll
                make_gap(name, b)
                self.segs.append((name, 0.0, fr(b), i))
                continue
            for x, y in cut_phrase(name, a, b, opt.get('thr', -44), opt.get('keep', ())):
                self.segs.append((name, x, y, i))
        self.outs, t = [], 0.0
        for s in self.segs:
            self.outs.append(t)
            t = fr(t + s[2] - s[1])
        self.MAIN = t
        self.TOTAL = fr(t + END_PLATE)
        self.HOOK_END = self.outs[next(i for i, s in enumerate(self.segs) if s[3] >= 0)]

    def m(self, name, t, phrase=None):
        """source time -> output time. If t falls in a cut, snap to next kept piece."""
        cand = []   # (distance, output time)
        for (f, a, b, pi), o in zip(self.segs, self.outs):
            if f != name or (phrase is not None and pi != phrase):
                continue
            if a - 0.001 <= t <= b + 0.001:
                return fr(o + min(max(t, a), b) - a)
            if t < a:
                cand.append((a - t, o))
            else:
                cand.append((t - b, fr(o + b - a)))
        if not cand or min(cand)[0] > 1.5:
            raise ValueError(f'{name}@{t} not in reel')
        return min(cand)[1]

    def has(self, name, t):
        return any(f == name and a <= t <= b for f, a, b, _ in self.segs)

    # ---- words in output time
    def words(self):
        """words of the EDITED voice track (re-transcribed), in output time."""
        if getattr(self, '_words', None) is not None:
            return self._words
        import hashlib
        h = hashlib.md5(json.dumps(self.segs).encode()).hexdigest()[:10]
        cache = f'{self.B}/voice_words_{h}.json'
        if os.path.exists(cache):
            self._words = [tuple(x) for x in json.load(open(cache))]
            return self._words
        if os.environ.get('AKPP_FAST_WORDS'):
            return self.words_src()
        v = voice_only(self)
        from faster_whisper import WhisperModel
        import wave, numpy as np
        mdl = WhisperModel('large-v3', device='cpu', compute_type='int8', cpu_threads=4)
        wf = wave.open(v); a = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
        segs, _ = mdl.transcribe(a, language='ru', word_timestamps=True, beam_size=5,
                                 initial_prompt=getattr(self.C, 'PROMPT', None))
        ws = []
        for sg in segs:
            for w in sg.words:
                ws.append((fr(w.start), w.word.strip(), 'out', w.start))
        json.dump(ws, open(cache, 'w'), ensure_ascii=False)
        self._words = ws
        return ws

    def words_src(self):
        out = []
        files = {f for f, *_ in self.segs}
        for f in files:
            tx = json.load(open(f'{SP}/tx/IMG_{f}.json'))
            pcs = [(i, a, b) for i, (ff, a, b, pi) in enumerate(self.segs) if ff == f]
            for s in tx:
                for w0, w1, w, p in s['w']:
                    best = max(pcs, key=lambda x: min(w1, x[2]) - max(w0, x[1]))
                    i, a, b = best
                    if min(w1, b) - max(w0, a) <= 0.02:
                        continue
                    out.append((fr(self.outs[i] + max(w0, a) - a), w.strip(), f, w0))
        out.sort()
        ded = out
        self._words = ded
        return ded

    # ---- shots
    def shots(self):
        if getattr(self, '_shots', None) is not None:
            return [dict(s) for s in self._shots]
        self._shots = self._build_shots()
        return [dict(s) for s in self._shots]

    def _build_shots(self):
        C = self.C
        wins = []
        for b in C.BROLL:
            name, t0, t1, clip, cin, motion = b[:6]
            opt = b[6] if len(b) > 6 else {}
            o0 = self.m(name, t0) if isinstance(t0, (int, float)) else t0[0]
            o1 = self.m(name, t1) if isinstance(t1, (int, float)) else t1[0]
            wins.append(dict(o0=o0, o1=o1, kind=opt.get('kind', 'hlg' if not clip.endswith(('.mp4', '.jpg', '.png')) and clip != 'scheme' else ('scheme' if clip == 'scheme' else 'stock')),
                             src=None if clip == 'scheme' else path(clip), cin=cin, motion=motion, opt=opt))
        wins.sort(key=lambda w: w['o0'])
        # glue windows separated by tiny A-roll slivers
        for p, q in zip(wins, wins[1:]):
            if q['o0'] - p['o1'] < 0.35:
                p['o1'] = q['o0']
        shots = [dict(o0=0.0, o1=self.HOOK_END, kind='hook', src=path(C.HOOK['src']),
                      cin=self.segs[0][1], opt=C.HOOK)]
        # hook may have several pieces: render as separate hook shots
        if len([s for s in self.segs if s[3] < 0]) > 1:
            shots = []
            for (f, a, b, pi), o in zip(self.segs, self.outs):
                if pi < 0:
                    shots.append(dict(o0=o, o1=fr(o + b - a), kind='hook', src=path(f), cin=a, opt=C.HOOK))
        for (f, a, b, pi), o in zip(self.segs, self.outs):
            if pi < 0 or f.startswith('gap'):
                continue
            o1 = fr(o + b - a)
            pieces = [(o, o1)]
            for w in wins:
                nxt = []
                for p0, p1 in pieces:
                    if w['o1'] <= p0 or w['o0'] >= p1:
                        nxt.append((p0, p1)); continue
                    if w['o0'] > p0: nxt.append((p0, w['o0']))
                    if w['o1'] < p1: nxt.append((w['o1'], p1))
                pieces = nxt
            for p0, p1 in pieces:
                if p1 - p0 < 1 / FPS:
                    continue
                popt = C.PHRASES[pi][3] if len(C.PHRASES[pi]) > 3 else {}
                shots.append(dict(o0=p0, o1=p1, kind='aroll', src=path(f), name=f, cin=fr(a + p0 - o),
                                  phrase=pi, opt=popt))
        shots += wins
        last = self.segs[-1]
        shots.append(dict(o0=self.MAIN, o1=self.TOTAL, kind='endplate', src=path(last[0]),
                          cin=max(0, last[2] - 0.3), opt={}))
        shots.sort(key=lambda s: s['o0'])
        merged = []
        for s in shots:   # absorb A-roll slivers
            if s['kind'] == 'aroll' and s['o1'] - s['o0'] < 0.3 and merged and merged[-1]['kind'] != 'hook':
                merged[-1]['o1'] = s['o1']; continue
            merged.append(s)
        shots = merged
        # split long A-roll shots (> ~2.3 s) into near-equal pieces for framing changes
        out = []
        for s in shots:
            d = s['o1'] - s['o0']
            if s['kind'] == 'aroll' and d > 2.4:
                n = int(d // 1.9) + (1 if d % 1.9 > 0.9 else 0)
                n = max(2, n)
                cuts = [fr(s['o0'] + d * k / n) for k in range(1, n)]
                cuts = [self.snap_word(c, s) for c in cuts]
                edges = [s['o0']] + cuts + [s['o1']]
                for e0, e1 in zip(edges, edges[1:]):
                    if e1 - e0 < 0.5:
                        continue
                    x = dict(s); x['o0'] = e0; x['o1'] = e1; x['cin'] = fr(s['cin'] + e0 - s['o0'])
                    out.append(x)
                if out[-1]['o1'] != s['o1']:
                    out[-1]['o1'] = s['o1']
            else:
                out.append(s)
        shots = out
        # contiguous fix-up
        for p, q in zip(shots, shots[1:]):
            if abs(p['o1'] - q['o0']) > 1e-6:
                p['o1'] = q['o0']
        z, prev, acc = 1, None, 0.0
        for s in shots:
            if s['kind'] == 'aroll':
                d = s['o1'] - s['o0']
                adj = prev is not None and prev['kind'] == 'aroll' and abs(prev['o1'] - s['o0']) < 1e-6
                if adj and (acc < 1.1 or d < 0.6):
                    acc += d          # keep framing: too soon for another change
                else:
                    z = 1 - z; acc = d
                s['zoom'] = z
            prev = s
        return shots

    def snap_word(self, t, s):
        """move a split point to the closest word start inside the shot."""
        ws = [w[0] for w in self.words() if s['o0'] + 0.6 < w[0] < s['o1'] - 0.6]
        if not ws:
            return t
        return min(ws, key=lambda x: abs(x - t))


# ---------------------------------------------------------------- video
GRADE = ("eq=saturation=0.82:contrast=1.06:brightness=-0.01,"
         "curves=all='0/0.03 0.25/0.22 0.75/0.78 1/0.97',colorbalance=bs=0.03:bm=0.01:rh=0.01")
TONEMAP = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=mobius:desat=0:param=0.4,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def motion(kind, n, cx='iw/2', cy='ih/2'):
    punch = "0.16*pow(max(0\\,1-on/6)\\,2)"
    drift = f"0.07*on/{n}" if kind == 'in' else f"0.07*(1-on/{n})"
    return (f"zoompan=z='1+{punch}+{drift}':d=1:x='{cx}-(iw/zoom/2)':y='{cy}-(ih/zoom/2)'"
            f":s=1080x1920:fps={FPS}")


def shot_cmd(R, i, s):
    n = round((s['o1'] - s['o0']) * FPS)
    out = f"{R.B}/shots/{i:03d}.mp4"
    k, o = s['kind'], s.get('opt', {})
    pre = ['ffmpeg', '-loglevel', 'error', '-y']
    enc = ['-frames:v', str(n), '-an', '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'fast',
           '-crf', '17', '-r', str(FPS), out]
    if k == 'scheme':
        return pre + ['-f', 'lavfi', '-i', f'color=c=0x0d0d10:s=1080x1920:r={FPS}'] + enc, out
    inp = ['-ss', f"{s['cin']:.3f}", '-i', s['src']]
    if k == 'hook':
        # aggressive push-in toward the face while the line is said
        z1 = o.get('zoom_to', 1.55)
        fx, fy = o.get('face', (0.5, 0.2))
        ease = f"pow(({s['o0']:.3f}+on/{FPS})/{R.HOOK_END:.3f}\\,1.6)"
        shake = o.get('shake_at')
        sh = ''
        if shake is not None:
            f0 = round((shake - s['o0']) * FPS)
            sh = f"+12*sin(on*2.1)*between(on\\,{f0}\\,{f0 + 8})"
        vf = (f"{TONEMAP},fps={FPS},scale=1440:2560:flags=lanczos,"
              f"zoompan=z='{o.get('zoom_from', 1.0)}+({z1}-{o.get('zoom_from', 1.0)})*{ease}':d=1:"
              f"x='iw*{fx}-(iw/zoom/2){sh}':y='ih*{fy}-(ih/zoom*{fy})':s=1080x1920:fps={FPS},"
              f"{GRADE},eq=contrast=1.08:saturation=0.9,vignette=PI/4.5,unsharp=5:5:0.4")
    elif k == 'aroll':
        cw, ch = 1600, 2844
        cx, cy = o.get('crop', (0.5, 0.06))   # crop centre x (fraction), top y (fraction)
        base = o.get('base')                  # optional base crop for wide (tight sources)
        if s['zoom'] == 0:
            if base:
                bw = int(2160 / base); bh = int(3840 / base)
                crop = f"crop={bw}:{bh}:{int(2160 * o.get('bx', 0.5) - bw / 2)}:{int(3840 * o.get('by', 0.0))},scale=1080:1920"
            else:
                crop = "scale=1080:1920"
        else:
            z = o.get('z', 1.35)
            if base:
                z = z * base
            cw, ch = int(2160 / z) // 2 * 2, int(3840 / z) // 2 * 2
            x = max(0, min(2160 - cw, int(2160 * cx - cw / 2)))
            y = max(0, min(3840 - ch, int(3840 * cy)))
            crop = f"crop={cw}:{ch}:{x}:{y},scale=1080:1920"
        vf = f"{TONEMAP},fps={FPS},{crop}:flags=lanczos,{GRADE},unsharp=5:5:0.35"
    elif k == 'stock':
        cx = o.get('cx', 0.5)
        extra = o.get('extra', '')
        if s['src'].endswith(('.jpg', '.png')):
            inp = ['-loop', '1', '-i', s['src']]
        vf = (f"fps={FPS},crop='min(iw\\,ih*9/16)':'min(ih\\,iw*16/9)':'(iw-min(iw\\,ih*9/16))*{cx}':'(ih-min(ih\\,iw*16/9))/2'{extra},"
              f"scale=1296:2304:flags=lanczos,unsharp=5:5:0.5,{GRADE},noise=alls=6:allf=t,{motion(s['motion'], n)}")
    elif k == 'hlg':
        cx, cy = o.get('c', ('iw/2', 'ih/2'))
        if isinstance(cx, float): cx = f'iw*{cx}'
        if isinstance(cy, float): cy = f'ih*{cy}'
        sc = o.get('scale', 1296)
        sp = f"setpts={o['slow']}*PTS," if o.get('slow') else ''
        vf = (f"{sp}{TONEMAP},fps={FPS},scale={sc}:{int(sc * 16 / 9)}:flags=lanczos,{GRADE}{o.get('extra', '')},"
              f"{motion(s['motion'], n, cx, cy)}")
    elif k == 'endplate':
        vf = (f"{TONEMAP},trim=end_frame=1,loop=loop=-1:size=1,setpts=N/{FPS}/TB,fps={FPS},scale=1080:1920,"
              "gblur=sigma=28,eq=brightness=-0.22:saturation=0.5")
    vf += ',tpad=stop_mode=clone:stop_duration=6'
    return pre + inp + ['-vf', vf] + enc, out


def render_shots(R, only=()):
    shots = R.shots()
    jobs = [shot_cmd(R, i, s) for i, s in enumerate(shots) if not only or i in only]

    def run(j):
        c, out = j
        r = subprocess.run(c, capture_output=True, text=True)
        print(('FAIL ' + r.stderr[-600:]) if r.returncode else 'ok', os.path.basename(out), flush=True)
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(run, jobs))
    with open(f'{R.B}/shots/list.txt', 'w') as f:
        for i in range(len(shots)):
            f.write(f"file '{R.B}/shots/{i:03d}.mp4'\n")
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i',
                    f'{R.B}/shots/list.txt', '-c', 'copy', f'{R.B}/base.mp4'], check=True)


# ---------------------------------------------------------------- subtitles
GLUE = {'в', 'во', 'на', 'с', 'со', 'к', 'ко', 'и', 'а', 'но', 'по', 'за', 'до', 'из', 'от', 'у', 'о', 'об',
        'не', 'же', 'бы', 'ли', 'под', 'для', 'при', 'что', 'как', 'это', 'то', 'так', 'уже', 'мы', 'он', 'её',
        'ее', 'нам', 'их', 'чем', 'чуть'}


def norm(w):
    return re.sub(r'[^\w\-%]', '', w.lower())


def tokens(R):
    C = R.C
    fix = getattr(C, 'WORDFIX', {})
    acc = {norm(x) for x in getattr(C, 'ACCENT', ())}
    hide = getattr(C, 'HIDE', [])      # list of (t0,t1) output windows without subs
    ws = list(R.words())
    for old, new in getattr(C, 'PHRASEFIX', []):
        o = [norm(x) for x in old.split()]; nw = new.split()
        i = 0
        while i <= len(ws) - len(o):
            if [norm(w[1]) for w in ws[i:i + len(o)]] == o:
                times = [w[0] for w in ws[i:i + len(o)]]
                rep = [(times[min(j, len(times) - 1)] if j < len(times) else times[-1] + 0.2 * (j - len(times) + 1),
                        x, 'fix', 0) for j, x in enumerate(nw)]
                ws[i:i + len(o)] = rep; i += len(rep)
            else:
                i += 1
    toks, buf = [], None
    for t, w, f, st in ws:
        key = (f, round(st, 2))
        wd = fix.get(key, fix.get(w.strip(), fix.get(norm(w), w)))
        if wd == '':
            continue
        clean = re.sub(r'[.,!?…:;«»"]', '', wd).upper().replace('Ё', 'Ё')
        red = norm(w) in acc or key in acc or wd.startswith('*')
        clean = clean.lstrip('*')
        if buf:
            toks.append((buf[0], buf[1] + ' ' + clean, buf[2] or red))
            buf = None
            continue
        if norm(w) in GLUE and len(clean) <= 4:
            buf = (t, clean, red)
            continue
        toks.append((t, clean, red))
    if buf:
        toks.append(buf)
    for t, w, r in getattr(C, 'EXTRA_TOKENS', []):
        toks.append((t, w, r))
    toks.sort()
    toks = [x for x in toks if not any(a <= x[0] < b for a, b in hide)]
    return toks


def ts(t):
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def subs(R):
    toks = tokens(R)
    hide = getattr(R.C, 'HIDE', [])
    ev = []
    for i, (t0, w, red) in enumerate(toks):
        nxt = toks[i + 1][0] if i + 1 < len(toks) else R.MAIN
        if t0 < R.HOOK_END <= nxt:
            nxt = R.HOOK_END
        for a, b in hide:
            if t0 < a < nxt:
                nxt = a
        t1 = min(nxt, t0 + 1.3)
        if t1 - t0 < 0.05:
            continue
        size = 96 if len(w) <= 10 else int(96 * 10 / len(w))
        if red:
            size = int(size * 1.12)
        style = 'R' if red else 'W'
        anim = r"{\fscx78\fscy78\t(0,90,\fscx106\fscy106)\t(90,170,\fscx100\fscy100)}"
        ev.append(f"Dialogue: 0,{ts(t0)},{ts(t1)},{style},,0,0,0,,{{\\pos(540,1190)\\fs{size}}}{anim}{w}")
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: W,Unbounded Black,78,&H00FFFFFF,&H00FFFFFF,&H50000000,&H78000000,1,0,0,0,100,100,1,0,1,5,4,5,40,40,0,1
Style: R,Unbounded Black,78,&H002F29F0,&H002F29F0,&H50000000,&H78000000,1,0,0,0,100,100,1,0,1,5,4,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    open(R.B + '/subs.ass', 'w').write(head + '\n'.join(ev) + '\n')
    with open(R.B + '/subs.txt', 'w') as f:
        for t, w, r in toks:
            f.write(f"{t:6.2f} {'*' if r else ' '}{w}\n")


# ---------------------------------------------------------------- gfx
def render_gfx(R, frames=()):
    tl = dict(fps=FPS, total=R.TOTAL, main=R.MAIN, hook_end=R.HOOK_END, ev=R.C.gfx(R),
              end_q=R.C.END_Q, logo=os.path.abspath(os.path.join(ASSETS, 'logo.png')))
    json.dump(tl, open(R.B + '/gfx.json', 'w'), ensure_ascii=False, indent=1)
    subprocess.run(['node', os.path.join(HERE, 'render_gfx.cjs'), R.B, *map(str, frames)], check=True)


# ---------------------------------------------------------------- audio
SFXD = os.path.join(ASSETS, 'sfx')
PEAK = {'riser': 4.0, 'click1': .11, 'click2': .13, 'click3': .10, 'click4': .16, 'click5': .13,
        'scheme-glitch': .04, 'boom': .25, 'scheme-static': .38, 'chirp': 0.0, 'chirp2': 0.0}


def sfx_path(sid):
    if sid == 'boom':
        return f'{SP}/web/boom.wav'
    if sid.startswith('chirp'):
        return f'{SP}/web/bird/{"23" if sid == "chirp" else "21"}.mp3'
    ext = 'mp3' if sid.startswith('scheme') else 'flac'
    return os.path.join(SFXD, f'{sid}.{ext}')


def mix(R, music=None):
    C = R.C
    inputs, chains, labels = [], [], []
    idx = [0]

    def add(p, pre=()):
        inputs.extend([*pre, '-i', p]); idx[0] += 1; return idx[0] - 1
    srcs = {}
    parts = []
    bleeps = getattr(C, 'BLEEP', [])   # (file, src_t0, src_t1)
    for i, (f, a, b, pi) in enumerate(R.segs):
        if f not in srcs:
            srcs[f] = add(f'{SP}/wav/IMG_{f}.wav')
        mute = ''
        for bf, b0, b1 in bleeps:
            if bf == f and b0 < b and b1 > a:
                mute += f",volume=0:enable='between(t\\,{max(0, b0 - a):.3f}\\,{b1 - a:.3f})'"
        chains.append(f"[{srcs[f]}:a]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS{mute},afade=t=in:d=0.012,"
                      f"afade=t=out:st={b - a - 0.012:.4f}:d=0.012,aresample=48000[s{i}]")
        parts.append(f'[s{i}]')
    chains.append(f"{''.join(parts)}concat=n={len(parts)}:v=0:a=1,aformat=channel_layouts=stereo,"
                  f"apad=whole_dur={R.TOTAL:.3f}[voice]")
    labels.append('[voice]')
    for n, e in enumerate(C.sfx(R)):
        t, sid, vol = e[:3]
        dur = e[3] if len(e) > 3 else None
        i = add(sfx_path(sid))
        d = max(0, t - PEAK.get(sid, 0))
        tr = f"atrim=0:{dur},afade=t=out:st={max(0, dur - 0.06)}:d=0.06," if dur else ''
        chains.append(f"[{i}:a]{tr}aresample=48000,aformat=channel_layouts=stereo,volume={vol},"
                      f"adelay={int(d * 1000)}:all=1[e{n}]")
        labels.append(f'[e{n}]')
    for n, (ca, chit) in enumerate(getattr(C, 'COUNTERS', lambda R: [])(R)):
        D = (chit - ca) / 10
        i = add(f"aevalsrc=0.5*sin(2*PI*(650+95*floor(t/{D:.4f}))*t)*exp(-38*mod(t\\,{D:.4f}))*lt(t\\,{10 * D:.4f}):s=48000:d={10 * D + 0.1:.3f}",
                ('-f', 'lavfi'))
        chains.append(f"[{i}:a]aformat=channel_layouts=stereo,volume=0.05,adelay={int(ca * 1000)}:all=1[b{n}]")
        labels.append(f'[b{n}]')
    if music:
        i = add(music, ('-ss', str(getattr(C, 'MUSIC_IN', 0))))
        md = R.TOTAL - R.HOOK_END
        vol = f"0.10+(0.4-0.10)*clip((t-{R.MAIN - R.HOOK_END - 0.3:.3f})/0.6\\,0\\,1)"
        chains.append(f"[{i}:a]atrim=0:{md:.3f},aresample=48000,aformat=channel_layouts=stereo,highpass=f=110,"
                      f"volume='{vol}':eval=frame,afade=t=out:st={md - 0.8:.3f}:d=0.8,"
                      f"adelay={int(R.HOOK_END * 1000)}:all=1[mus]")
        labels.append('[mus]')
    chains.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first[out]")
    script = R.B + '/mix.filter'
    open(script, 'w').write(';\n'.join(chains))
    out = R.B + ('/mix.wav' if music else '/mix_nomusic.wav')
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *inputs, '-filter_complex_script', script,
                        '-map', '[out]', '-t', f'{R.TOTAL:.3f}', '-ac', '2', '-ar', '48000', out],
                       capture_output=True, text=True)
    print(r.stderr[-1500:] or 'mix ok', out)
    return out


def voice_only(R):
    """edited voice at 16 kHz mono (bleeps muted) for re-transcription."""
    parts, chains, inputs, srcs = [], [], [], {}
    for i, (f, a, b, pi) in enumerate(R.segs):
        if f not in srcs:
            srcs[f] = len(srcs); inputs += ['-i', f'{SP}/wav/IMG_{f}.wav']
        chains.append(f"[{srcs[f]}:a]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS[s{i}]"); parts.append(f'[s{i}]')
    chains.append(f"{''.join(parts)}concat=n={len(parts)}:v=0:a=1[out]")
    out = R.B + '/voice16.wav'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *inputs, '-filter_complex', ';'.join(chains),
                    '-map', '[out]', '-ac', '1', '-ar', '16000', out], check=True)
    return out


def loudness_gain(wav, target=-15.0):
    r = subprocess.run(['ffmpeg', '-i', wav, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1])
    return target - I


def final(R, wav, out):
    g = loudness_gain(wav)
    fc = (f"[0:v][1:v]overlay=0:0:format=auto,ass={R.B}/subs.ass,format=yuv420p[v];"
          f"[2:a]volume={g:.2f}dB,alimiter=limit=0.84:level=false:attack=3:release=60[a]")
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f'{R.B}/base.mp4',
                    '-framerate', str(FPS), '-i', f'{R.B}/gfx/%05d.png', '-i', wav,
                    '-filter_complex', fc, '-map', '[v]', '-map', '[a]', '-t', f'{R.TOTAL:.3f}',
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-r', str(FPS),
                    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
    print('final', out, f'gain {g:.1f} dB')


def contact(R, video, out, step=1.0):
    n = int(R.TOTAL / step) + 1
    cols = 10
    rows = (n + cols - 1) // cols
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', video, '-vf',
                    f"fps=1/{step},scale=162:288,drawtext=text='%{{pts\\:hms}}':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6,"
                    f"tile={cols}x{rows}", '-frames:v', '1', out], check=True)


def main(C):
    R = Reel(C)
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'plan'
    if cmd == 'plan':
        for s in R.shots():
            print(f"{s['o0']:6.2f}-{s['o1']:6.2f} {s['o1'] - s['o0']:5.2f} {s['kind']:8} "
                  f"{os.path.basename(s['src'] or '-'):14} in={s['cin']:.2f} {s.get('zoom', '')}{s.get('motion', '') or ''}")
        print('main', R.MAIN, 'total', R.TOTAL, 'hook_end', R.HOOK_END)
    elif cmd == 'words':
        for t, w, f, st in R.words():
            print(f'{t:6.2f} {w:16} {f} {st:.2f}')
    elif cmd == 'shots':
        render_shots(R, tuple(map(int, sys.argv[2:])))
    elif cmd == 'subs':
        subs(R)
    elif cmd == 'gfx':
        render_gfx(R, tuple(map(int, sys.argv[2:])))
    elif cmd == 'mix':
        mix(R, sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == 'final':
        os.makedirs(SP + '/out', exist_ok=True)
        wav = mix(R)
        final(R, wav, f'{SP}/out/{C.NAME}_nomusic.mp4')
        contact(R, f'{SP}/out/{C.NAME}_nomusic.mp4', f'{R.B}/contact.jpg', 0.5 if R.TOTAL < 40 else 1.0)
    elif cmd in ('all', 'post'):
        if cmd == 'all':
            render_shots(R)
        subs(R); render_gfx(R)
        os.makedirs(SP + '/out', exist_ok=True)
        wav = mix(R)
        final(R, wav, f'{SP}/out/{C.NAME}_nomusic.mp4')
        contact(R, f'{SP}/out/{C.NAME}_nomusic.mp4', f'{R.B}/contact.jpg')
    return R
