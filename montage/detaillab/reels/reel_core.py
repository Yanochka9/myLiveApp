"""Общий движок рилса DetailLab (дубли спикера + подсъёмы + 2D-графика).

Проект — папка с words.json (tr.py), faces.json, grade.txt, src/IMG_*.MOV, wav/*.wav,
music/client.wav и reel.py, который описывает куски речи, планы и графику.
Сборка: python3 reel.py build && python3 reel.py finish  ->  out/final.mp4
"""
import json, subprocess, os, glob, sys
import numpy as np

FPS = 30
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(f"{HERE}/../assets")
GOLD = '&H37AFD4&'; GOLD2 = '&H5CC8E8&'; DARK = '&H0E0E0E&'
PEAK = {'hit1': 0.21, 'hit2': 0.19, 'hit3': 0.225, 'hit4': 0.115, 'hit5': 0.215}


def ffdur(f):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                          '-of', 'csv=p=0', f]))


def snap(x):
    return round(x * FPS) / FPS


def norm(w):
    return w.lower().strip('.,…?!«»"').replace('ё', 'е')


# ---------------- ASS drawing helpers ----------------
def ts(x):
    x = max(0, x); h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def box(x1, y1, x2, y2, r=26):
    return (f"m {x1+r} {y1} l {x2-r} {y1} b {x2} {y1} {x2} {y1} {x2} {y1+r} l {x2} {y2-r} "
            f"b {x2} {y2} {x2} {y2} {x2-r} {y2} l {x1+r} {y2} b {x1} {y2} {x1} {y2} {x1} {y2-r} "
            f"l {x1} {y1+r} b {x1} {y1} {x1} {y1} {x1+r} {y1}")


def circle(cx, cy, r):
    k = 0.5523 * r
    return (f"m {cx} {cy-r} b {cx+k} {cy-r} {cx+r} {cy-k} {cx+r} {cy} b {cx+r} {cy+k} {cx+k} {cy+r} {cx} {cy+r} "
            f"b {cx-k} {cy+r} {cx-r} {cy+k} {cx-r} {cy} b {cx-r} {cy-k} {cx-k} {cy-r} {cx} {cy-r}")


def check(x, y, s=1.0):
    return f"m {x} {y+14*s} l {x+10*s} {y+26*s} l {x+30*s} {y} l {x+34*s} {y+4*s} l {x+10*s} {y+34*s} l {x-4*s} {y+18*s}"


def cross(cx, cy, r, t=6):
    return (f"m {cx-r} {cy-r+t} l {cx-r+t} {cy-r} l {cx} {cy-t} l {cx+r-t} {cy-r} l {cx+r} {cy-r+t} l {cx+t} {cy} "
            f"l {cx+r} {cy+r-t} l {cx+r-t} {cy+r} l {cx} {cy+t} l {cx-r+t} {cy+r} l {cx-r} {cy+r-t} l {cx-t} {cy}")


def rect(x1, y1, x2, y2):
    return f"m {x1} {y1} l {x2} {y1} l {x2} {y2} l {x1} {y2}"


PIN = ("m 0 -28 b 16 -28 26 -16 26 -2 b 26 14 0 40 0 40 b 0 40 -26 14 -26 -2 b -26 -16 -16 -28 0 -28 "
       "m 0 -12 b -7 -12 -11 -7 -11 -2 b -11 5 -7 9 0 9 b 7 9 11 5 11 -2 b 11 -7 7 -12 0 -12")

STYLES = """Style: Cap,Montserrat ExtraBold,84,&H00FFFFFF,&H00FFFFFF,&H00141414,&H8C000000,0,0,0,0,100,100,1,0,1,3,6,5,180,180,0,1
Style: Shape,Arial,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Small,Montserrat ExtraBold,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,4,0,1,0,3,5,0,0,0,1
Style: Big,Oswald,104,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,3,0,1,0,4,5,0,0,0,1
Style: Item,Montserrat ExtraBold,30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,0,2,4,0,0,0,1
Style: Huge,Oswald,300,&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,0,0,0,0,100,100,0,0,1,0,6,5,0,0,0,1
Style: Days,Montserrat ExtraBold,76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,3,4,0,0,0,1
Style: Num,Oswald,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Step,Montserrat ExtraBold,44,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,0,2,5,0,0,0,1
Style: Chip,Oswald,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,3,5,0,0,0,1
Style: Cta,Oswald,100,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,4,5,0,0,0,1
Style: Addr,Montserrat ExtraBold,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,0,3,4,0,0,0,1
Style: D3,Oswald,150,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,2,0,1,0,0,5,0,0,0,1
Style: Tiny,Montserrat ExtraBold,28,&H00C8C8C8,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,3,0,1,0,2,5,0,0,0,1"""


class Reel:
    def __init__(self, P):
        self.P = P; self.SRC = f"{P}/src"; self.OUT = f"{P}/out"
        os.makedirs(self.OUT, exist_ok=True)
        self.W = json.load(open(f"{P}/words.json"))
        self.FACES = json.load(open(f"{P}/faces.json"))
        g = open(f"{P}/grade.txt").read().strip().replace("$A", ASSETS).replace("ASSETS/", ASSETS + "/").split("\n")
        self.AUTO = g[0].strip() == 'AUTO'
        self.GRADE = g[0].strip() if not self.AUTO else None
        self.GEXTRA = g[1].strip() if self.AUTO and len(g) > 1 else ''
        self._norm = {}
        self.ZC = 1.42; self.TAIL = 0.2; self.END_DUR = 3.4
        self.hook_z = (1.36, 1.46)
        self.pieces = []; self.hook_clip = None; self.TAIL_AT = None
        self._vad = {}; self._dur = {}
        self.L = []  # ASS events

    # ---------- voice ----------
    def vad(self, c):
        if c in self._vad:
            return self._vad[c]
        x = np.frombuffer(open(f"{self.P}/wav/{c}.wav", 'rb').read()[44:], dtype='int16').astype(float) / 32768
        h = 320; m = len(x) // h
        r = 20 * np.log10(np.sqrt((x[:m * h].reshape(m, h) ** 2).mean(1)) + 1e-9)
        rr = r[r > -100]; floor = np.percentile(rr, 10); peak = np.percentile(rr, 95)
        self._vad[c] = (r > floor + 0.35 * (peak - floor), m)
        return self._vad[c]

    def segs(self, c, a, b):
        v, m = self.vad(c)
        out = []; cur = None
        for i in range(int(a / 0.02), min(m, int(b / 0.02))):
            t = i * 0.02
            if v[i]:
                if cur is None: cur = [t, t]
                cur[1] = t + 0.02
            elif cur and t - cur[1] > 0.28:
                out.append(cur); cur = None
        if cur: out.append(cur)
        return [[max(a, s - 0.08), min(b, e + 0.12)] for s, e in out if e - s > 0.06]

    def ranges(self, R):
        """R: [(clip, a, b[, 'hook'])] — куски дублей по порядку."""
        t = 0.0
        for r in R:
            c, a, b = r[:3]
            for s, e in self.segs(c, a, b):
                n = max(1, round((e - s) * FPS))
                self.pieces.append((c, s, s + n / FPS, t)); t += n / FPS
            if len(r) > 3 and r[3] == 'hook':
                self.hook_clip = c; self.TAIL_AT = t; t += self.TAIL
        self.VOICE_END = t; self.TOTAL = t + self.END_DUR
        for p in self.pieces:
            print(f"  {p[0]} {p[1]:7.2f}-{p[2]:7.2f} -> {p[3]:6.2f}")
        print("VOICE_END %.2f TOTAL %.2f" % (self.VOICE_END, self.TOTAL))

    def omap(self, c, x):
        for pc, s, e, o in self.pieces:
            if pc == c and x < e:
                return o + max(0.0, x - s)
        raise ValueError((c, x))

    def inside(self, c, w):
        mid = (w[0] + w[1]) / 2
        return any(pc == c and (s - 0.05 <= w[0] < e or s <= mid < e) for pc, s, e, o in self.pieces)

    def w(self, c, txt, after=0.0):
        """выходное время слова txt в дубле c (первое после секунды after исходника)"""
        for wd in self.W[c]:
            nw, nt = norm(wd[2]), norm(txt)
            if wd[0] >= after - 0.01 and (nw == nt or (len(nt) > 3 and nw.startswith(nt))) and self.inside(c, wd):
                pc = [p for p in self.pieces if p[0] == c and wd[0] < p[2]][0]
                return self.omap(c, max(wd[0], pc[1]))
        raise KeyError((c, txt, after))

    def src_end(self, c, x):
        """выходное время исходной секунды x (зажато в ближайший кусок, не перескакивает в следующий диапазон)"""
        best = min((p for p in self.pieces if p[0] == c), key=lambda p: 0 if p[1] <= x <= p[2] else min(abs(x - p[1]), abs(x - p[2])))
        pc, s, e, o = best
        return o + min(max(0.0, x - s), e - s)

    # ---------- video ----------
    def dur(self, c):
        if c not in self._dur:
            self._dur[c] = ffdur(f"{self.SRC}/IMG_{c}.MOV")
        return self._dur[c]

    def face(self, c, s=None, e=None):
        tr = [t for t in self.FACES[c] if t[1] is not None]
        sel = [t for t in tr if s is None or s - 0.5 <= t[0] <= e + 0.5] or tr
        return float(np.median([t[1] for t in sel])), float(np.median([t[2] for t in sel]))

    def grade_for(self, src):
        """AUTO: HDR→SDR + нормализация клипа под эталон (autograde) + фирменный стиль + правка; иначе grade.txt"""
        P = "setparams=color_primaries=bt2020:color_trc=arib-std-b67:colorspace=bt2020nc:range=tv,"
        if not self.AUTO:
            return P + self.GRADE
        if src not in self._norm:
            sys.path.insert(0, os.path.dirname(HERE))
            import autograde
            nf, _ = autograde.norm_filter(src)
            self._norm[src] = (P + autograde.HDR + "," + nf + "," + autograde.STYLE.replace("ASSETS/", ASSETS + "/")
                               + ("," + self.GEXTRA if self.GEXTRA else ""))
        return self._norm[src]

    def render(self, src, ss, nfr, vf, post=''):
        out = f"{self.OUT}/seg{len(self.segfiles):03d}.mp4"
        cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', f"{ss:.3f}", '-i', src, '-an',
               '-vf', f"{vf},scale=1080:1920:flags=lanczos,setsar=1,fps={FPS},{self.grade_for(src)}{post},format=yuv420p",
               '-frames:v', str(nfr), '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', out]
        subprocess.run(cmd, check=True)
        self.segfiles.append(out)

    def zp(self, fx, fy, z):
        return (f"zoompan=z='{z}':d=1:s=1080x1920:fps={FPS}:"
                f"x='max(0,min(iw-iw/zoom,iw*{fx:.3f}-iw/zoom/2))':y='max(0,min(ih-ih/zoom,ih*{fy:.3f}-ih/zoom*0.30))'")

    def zexpr(self, kind, off, tot):
        """плавный наезд на весь план (непрерывно через склейки кусков речи)"""
        n = f"(on+{off})"; T = max(1, tot - 1)
        if kind == 'wide':
            return f"1.0+0.06*{n}/{T}"
        if kind == 'close':
            return f"{self.ZC}+0.07*{n}/{T}"
        if kind == 'intro':   # резкий наезд в начале ролика, потом медленный дрейф
            N1 = 14
            return f"if(lt({n},{N1}),1.0+0.32*sin(PI/2*{n}/{N1}),1.32+0.06*({n}-{N1})/{max(1, tot-N1)})"
        raise ValueError(kind)

    def zoom(self, c, fxy, nfr, off, tot):
        fx, fy = fxy; hz = self.hook_z
        n = f"(on+{off})"
        if len(hz) == 3:      # начало со спикера: резкий наезд z0→zm, потом zm→z1
            N1 = 14
            z = f"if(lt({n},{N1}),{hz[0]}+({hz[1]}-{hz[0]})*sin(PI/2*{n}/{N1}),{hz[1]}+({hz[2]}-{hz[1]})*({n}-{N1})/{max(1, tot-N1)})"
        else:
            z0, z1 = hz
            z = f"({z0}+({z1}-{z0})*(1-cos(PI*{n}/{max(1, tot-1)}))/2)"
        return self.zp(fx, fy, z)

    def speaker(self, a, b, kind, post_first=''):
        parts = []
        for pc, s, e, o in self.pieces:
            lo, hi = max(a, o), min(b, o + (e - s))
            nfr = round((hi - lo) * FPS)
            if nfr > 0:
                parts.append((pc, s, e, o, lo, nfr))
        tot = sum(p[5] for p in parts); off = 0
        for k, (pc, s, e, o, lo, nfr) in enumerate(parts):
            fx, fy = self.face(pc, s, e)
            self.render(f"{self.SRC}/IMG_{pc}.MOV", s + (lo - o), nfr, self.zp(fx, fy, self.zexpr(kind, off, tot)),
                        post=post_first if k == 0 else '')
            off += nfr

    def build(self, SH, end_clip, end_ss=0.0):
        SH = [(snap(x[0]),) + tuple(x[1:]) for x in SH] + [(snap(self.VOICE_END), 'end')]
        self.segfiles = []
        hook_n = {}
        for i, sh in enumerate(SH):
            a = sh[0]; b = SH[i + 1][0] if i + 1 < len(SH) else snap(self.TOTAL)
            kind = sh[1]; nfr = round((b - a) * FPS)
            if nfr <= 0:
                continue
            flash_in = ",fade=t=in:st=0:d=0.22:color=white" if i > 0 and SH[i - 1][1] == 'tail' else ''
            if kind == 'end':
                self.render(f"{self.SRC}/IMG_{end_clip}.MOV", end_ss, nfr,
                            f"crop=iw/1.08:ih/1.08,tpad=stop_mode=clone:stop_duration={self.END_DUR},"
                            f"zoompan=z='1+0.08*on/{nfr}':d=1:s=1080x1920:fps={FPS}:"
                            f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'")
            elif kind in ('hook', 'tail'):
                hp = [p for p in self.pieces if p[0] == self.hook_clip and p[3] < self.TAIL_AT]
                fxy = self.face(self.hook_clip, hp[0][1], hp[-1][2])
                if kind == 'hook':
                    hook_n['n'] = nfr; hook_n['tot'] = nfr + round(self.TAIL * FPS)
                    # hook pieces are contiguous enough: play from the source time under `a`
                    pc, s, e, o = ([p for p in hp if p[3] <= a + 1e-6] or hp[:1])[-1]
                    self.render(f"{self.SRC}/IMG_{pc}.MOV", s + (a - o), nfr,
                                self.zoom(pc, fxy, nfr, 0, hook_n['tot']))
                else:
                    pc, s, e, o = hp[-1]
                    self.render(f"{self.SRC}/IMG_{pc}.MOV", e, nfr,
                                self.zoom(pc, fxy, nfr, hook_n['n'], hook_n['tot']),
                                post=f",fade=t=out:st={(nfr-4)/FPS:.3f}:d={4/FPS:.3f}:color=white")
            elif kind == 'b':
                _, _, c, ss, fb = sh
                nb = min(nfr, int((self.dur(c) - ss - 0.05) * FPS))
                z = (f"1.05+0.07*on/{max(1, nb-1)}" if i % 2 else f"1.12-0.07*on/{max(1, nb-1)}")
                self.render(f"{self.SRC}/IMG_{c}.MOV", ss, nb,
                            f"zoompan=z='{z}':d=1:s=1080x1920:fps={FPS}:x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'", post=flash_in)
                if nb < nfr:
                    self.speaker(a + nb / FPS, b, fb)
            else:
                self.speaker(a, b, kind, post_first=flash_in)
            print(f"shot {i} {kind} {a:.2f}-{b:.2f}", flush=True)
        with open(f"{self.OUT}/list.txt", 'w') as f:
            for p in self.segfiles:
                f.write(f"file '{p}'\n")
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f"{self.OUT}/list.txt",
                        '-c', 'copy', f"{self.OUT}/video_raw.mp4"], check=True)
        json.dump({'pieces': self.pieces, 'shots': [list(x) for x in SH], 'total': self.TOTAL},
                  open(f"{self.OUT}/timeline.json", 'w'), ensure_ascii=False)

    @property
    def FLASH(self):
        return None if self.TAIL_AT is None else self.TAIL_AT + self.TAIL

    # ---------- audio ----------
    def audio(self, sfx, music_db=-25, music_off=0.0):
        f = []; ins = []
        for i, (c, s, e, o) in enumerate(self.pieces):
            ins += ['-i', f"{self.SRC}/IMG_{c}.MOV"]
            d = e - s
            f.append(f"[{i}:a]atrim={s:.4f}:{e:.4f},asetpts=PTS-STARTPTS,aresample=48000,"
                     f"aformat=channel_layouts=mono,afade=t=in:d=0.012,afade=t=out:st={d-0.02:.4f}:d=0.02,"
                     f"adelay={int(round(o*1000))}:all=1[v{i}]")
        n = len(self.pieces); T = self.TOTAL
        f.append(''.join(f"[v{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,"
                 "highpass=f=80,lowpass=f=14000,"
                 "acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2,"
                 f"apad=whole_dur={T:.3f},atrim=0:{T:.3f},asplit=2[voice][key]")
        mf = sorted(glob.glob(f"{self.P}/music/client.*"))
        if mf:
            ins += ['-i', mf[0]]
            f.append(f"[{n}:a]atrim=start={music_off:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
                     f"volume={music_db}dB,afade=t=in:d=0.4,afade=t=out:st={T-1.2:.3f}:d=1.2,apad,atrim=0:{T:.3f}[mus]")
            f.append("[key]aformat=channel_layouts=stereo[keys];"
                     "[mus][keys]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350:makeup=1[musd]")
        else:
            f.append("[key]anullsink")
        k = n + (1 if mf else 0)
        mix = ['[voice]'] + (['[musd]'] if mf else [])
        for j, (nm, t, g) in enumerate(sfx):
            fp = f"{HERE}/sfx/{nm}.wav"
            ins += ['-i', fp if os.path.exists(fp) else f"{ASSETS}/sfx/{nm}.mp3"]
            extra = ''
            if nm == 'riser_hook' and self.FLASH:
                extra = f"afade=t=out:st={self.FLASH - t - 0.02:.3f}:d=0.06,"
            t -= PEAK.get(nm, 0.0); trim = ''
            if t < 0:
                trim = f"atrim=start={-t:.3f},asetpts=PTS-STARTPTS,"; t = 0
            f.append(f"[{k}:a]{trim}{extra}volume={g}dB,adelay={int(t*1000)}:all=1,"
                     f"aformat=channel_layouts=stereo,aresample=48000[s{j}]")
            mix.append(f"[s{j}]"); k += 1
        f.append(''.join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,"
                 f"atrim=0:{T:.3f},loudnorm=I=-14:TP=-1.0:LRA=9[aout]")
        subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(f),
                        '-map', '[aout]', '-ar', '48000', '-ac', '2', f"{self.OUT}/audio.wav"], check=True)

    # ---------- subtitles / graphics ----------
    def D(self, layer, a, b, style, text):
        self.L.append(f"Dialogue: {layer},{ts(a)},{ts(b)},{style},,0,0,0,,{text}")

    def S(self, layer, a, b, tags, path):
        self.D(layer, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\bord0\\shad0{tags}}}{{\\p1}}{path}{{\\p0}}")

    def captions(self, fix, goldw, short, y_of=lambda t: 1050, skip=()):
        ws = []; seen = set()
        for pc, s, e, o in self.pieces:
            for i, w in enumerate(self.W[pc]):
                if (pc, i) in seen or not self.inside(pc, w):
                    continue
                if not (s - 0.05 <= w[0] < e or s <= (w[0] + w[1]) / 2 < e):
                    continue
                seen.add((pc, i))
                raw = norm(w[2])
                if raw in skip:
                    continue
                if raw.startswith('-') and ws:
                    ws[-1][1] += raw.upper(); continue
                txt = fix.get(raw, raw).upper()
                ws.append([self.omap(pc, max(w[0], s)), txt, raw in goldw or norm(txt) in goldw])
        ws.sort(key=lambda x: x[0])
        groups = []; i = 0
        while i < len(ws):
            g = [ws[i]]
            while norm(g[-1][1]) in short and i + 1 < len(ws) and len(g) < 3:
                i += 1; g.append(ws[i])
            groups.append(g); i += 1
        for j, g in enumerate(groups):
            st = g[0][0]
            en = groups[j + 1][0][0] if j + 1 < len(groups) else self.VOICE_END
            en = min(en, st + 1.4)
            if self.FLASH and st < self.FLASH <= en:
                en = self.FLASH - 0.05
            txt = ' '.join((f"{{\\c{GOLD}}}{w[1]}{{\\c&HFFFFFF&}}" if w[2] else w[1]) for w in g)
            n = sum(len(w[1]) for w in g) + len(g) - 1
            k = min(100, int(100 * 12 / max(1, n)))  # длинные слова ужимаем, чтобы влезли в ширину
            self.D(5, st, en, 'Cap', f"{{\\pos(540,{y_of(st)})\\fad(40,0)\\fscx{k*88//100}\\fscy{k*88//100}"
                                     f"\\t(0,110,\\fscx{k}\\fscy{k})}}{txt}")

    POP = "\\fad(180,200)\\fscx92\\fscy92\\t(0,220,\\fscx100\\fscy100)"

    def plate(self, a, b, small, big, y1=1140, y2=1370):
        an = self.POP + f"\\org(540,{(y1+y2)//2})"
        self.S(1, a, b, f"\\1c&H101010&\\1a&H50&\\3c{GOLD}\\bord3{an}", box(180, y1, 900, y2))
        self.D(2, a, b, 'Small', f"{{\\pos(540,{y1+58}){an}}}{small}")
        self.D(2, a, b, 'Big', f"{{\\pos(540,{y1+150})\\c{GOLD}{an}}}{big}")

    def checklist(self, a, b, items, title='ЧТО ВХОДИТ В КОМПЛЕКС', top=1080, row=62, per_col=5):
        rows = (len(items) + 1) // 2 if len(items) > per_col else len(items)
        rows = max(rows, min(per_col, len(items)))
        self.S(1, a, b, f"\\1c{DARK}\\1a&H48&\\3c{GOLD}\\bord3\\fad(250,250)", box(180, top, 900, top + 82 + row * rows))
        self.D(2, a, b, 'Small', f"{{\\pos(540,{top+44})\\c{GOLD}\\fad(250,250)}}{title}")
        for k, (name, t0) in enumerate(items):
            col, r = k // rows, k % rows
            x = 220 + col * 345; y = top + 82 + row * r + row / 2 - 4
            self.S(2, t0, b, f"\\1c{GOLD}\\fad(150,250)", circle(x, y, 17))
            self.S(3, t0, b, "\\1c&H101010&\\fad(150,250)", check(x - 11, y - 10, 0.62))
            self.D(2, t0, b, 'Item', f"{{\\an4\\pos({x+28},{y})\\fad(150,250)}}{name}")

    def endcard(self):
        a = self.VOICE_END; b = self.TOTAL
        self.S(3, a + 0.15, b, f"\\1a&HFF&\\3c{GOLD}\\bord5\\fad(400,0)", circle(540, 700, 268))
        self.D(4, a + 0.45, b, 'Cta', f"{{\\pos(540,1110)\\c{GOLD}\\fad(250,0)\\fscx90\\fscy90\\t(0,200,\\fscx100\\fscy100)}}ПИШИТЕ В DIRECT")
        self.D(4, a + 0.65, b, 'Small', f"{{\\pos(540,1200)\\fad(250,0)}}РАССЧИТАЕМ СТОИМОСТЬ")
        self.D(4, a + 0.85, b, 'Shape', f"{{\\an7\\pos(232,1330)\\1c{GOLD}\\bord0\\shad0\\fad(250,0)}}{{\\p1}}{PIN}{{\\p0}}")
        self.D(4, a + 0.85, b, 'Addr', f"{{\\an4\\pos(275,1335)\\fad(250,0)}}ПР-Т ДЗЕРЖИНСКОГО, 82А")
        self.D(4, a + 0.95, b, 'Tiny', f"{{\\pos(540,1405)\\fad(250,0)}}МИНСК · 9:00–21:00 · БЕЗ ВЫХОДНЫХ")

    def write_ass(self):
        head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n"
                "ScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
                "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                + STYLES + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        open(f"{self.OUT}/subs.ass", 'w').write(head + '\n'.join(self.L) + '\n')

    def final(self, name='final.mp4'):
        a = self.VOICE_END; T = self.TOTAL
        logo = (f"[1:v]scale=500:500,format=rgba,eq=brightness=0.07:contrast=1.18:saturation=1.25:gamma=1.08,"
                f"geq=r='min(255,r(X,Y)+150*exp(-pow((X+0.6*Y-(T-{a+0.9:.3f})*1100)/45,2)))':"
                f"g='min(255,g(X,Y)+140*exp(-pow((X+0.6*Y-(T-{a+0.9:.3f})*1100)/45,2)))':"
                f"b='min(255,b(X,Y)+110*exp(-pow((X+0.6*Y-(T-{a+0.9:.3f})*1100)/45,2)))':a='alpha(X,Y)',"
                f"fade=t=in:st={a+0.1:.3f}:d=0.45:alpha=1[lg]")
        fc = (f"{logo};[0:v]drawbox=x=0:y=0:w=iw:h=ih:color=black@0.45:t=fill:enable='gte(t,{a:.3f})'[bg];"
              f"[bg][lg]overlay=290:450:enable='gte(t,{a+0.1:.3f})'[v1];"
              f"[v1]subtitles={self.OUT}/subs.ass:fontsdir={ASSETS}/fonts,format=yuv420p[v]")
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f"{self.OUT}/video_raw.mp4",
                        '-loop', '1', '-framerate', '30', '-t', f"{T:.3f}", '-i', f"{HERE}/brand/logo.png",
                        '-i', f"{self.OUT}/audio.wav", '-filter_complex', fc, '-map', '[v]', '-map', '2:a',
                        '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-maxrate', '10M', '-bufsize', '20M',
                        '-profile:v', 'high', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest',
                        f"{self.OUT}/{name}"], check=True)
