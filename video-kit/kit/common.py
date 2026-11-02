"""Project config, theme and time helpers shared by every step of the kit."""
import json, os, re, copy, hashlib

KIT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(KIT)
FPS, W, H = 30, 1080, 1920
INTER = '/usr/share/fonts/opentype/inter'

DEFAULT_THEME = {
    'accent': '#E20E2A',          # main colour: pills, highlighted subtitle word, flashes
    'accent_light': '#FF3448',    # top of the pill gradient
    'dark': '#280608',            # dark pills
    'light': '#FFFFFF',           # light pills
    'text': '#FFFFFF',
    'on_accent': '#FFFFFF',
    'on_light': '#E20E2A',        # text on light pills (accent by default; dark for light accents like gold)
    'paper': '#FAF8F4',           # frame of 'photo' polaroid cards       # text and check icon on accent pills (dark for light accents like gold)
    'link': '#FF4658',            # site / url colour on the end card
    'fonts': {
        'black': f'{INTER}/InterDisplay-Black.otf',
        'xbold': f'{INTER}/InterDisplay-ExtraBold.otf',
        'bold': f'{INTER}/InterDisplay-Bold.otf',
        'semibold': f'{INTER}/InterDisplay-SemiBold.otf',
        'black_italic': f'{INTER}/InterDisplay-BlackItalic.otf',
    },
    'vignette': 0.22,             # 0 = off
    'glow': 10,                   # soft accent glow in the top-right corner, 0 = off
    'flash': '#FF4050',           # colour of the soft "flash" transition
    '3d': {                       # materials of every 3D element
        'front': '#ED2030', 'side': '#700012', 'metallic': 0.35, 'roughness': 0.16,
        'white': '#F9F7F7', 'dark': '#300006',
    },
}

DEFAULT_SUBS = {
    'enabled': True, 'font': 'black', 'size': 64, 'y': 1330, 'color': '#FFFFFF',
    'highlight': 'accent', 'highlight_text': '#FFFFFF', 'mode': 'karaoke',
    'max_words': 3, 'max_chars': 17, 'uppercase': False, 'shadow': 0.55,
    'box': True,                  # False: the active word only changes colour (highlight_text), no plate behind it
    'margin': 150,                # side margin: phrases stay clear of the TikTok / Reels button column
    'replace': {}, 'merge': [],
}

DEFAULT_GRADE = {'gamma': 1.08, 'contrast': 1.05, 'saturation': 1.06, 'warmth': 0.015, 'cool_shadows': 0.02,
                 'lut': None, 'lut_mix': 1.0}   # lut: .cube file applied before eq/colorbalance, lut_mix: its strength 0..1


def deep_merge(a, b):
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def hexrgb(s):
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def spec_hash(obj):
    return hashlib.sha1(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def norm_word(w):
    return re.sub(r'[^\w\-]', '', w.lower().replace('ё', 'е'))


class Project:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.dir = os.path.dirname(self.path)
        self.cfg = json.load(open(self.path, encoding='utf-8'))
        c = self.cfg
        self.name = c.get('name') or os.path.splitext(os.path.basename(path))[0]
        self.work = os.path.join(ROOT, 'work', self.name)
        os.makedirs(self.work, exist_ok=True)
        self.src_dir = self.rel(c.get('sources', {}).get('dir', f'work/{self.name}/src'), root=True)
        self.theme = deep_merge(DEFAULT_THEME, c.get('theme'))
        self.subs = deep_merge(DEFAULT_SUBS, c.get('subtitles'))
        self.grade = deep_merge(DEFAULT_GRADE, c.get('grade'))
        self.output = self.rel(c.get('output', f'out/{self.name}.mp4'), root=True)
        self.out_crop = (c.get('frame') or {}).get('crop')   # [x, y, w, h]: e.g. [0, 420, 1080, 1080] for a 1:1 video
        self._words = None
        self.build_timeline()

    # paths in the config are relative to video-kit/ (root=True) or to the project file
    def rel(self, p, root=False):
        if os.path.isabs(p): return p
        return os.path.normpath(os.path.join(ROOT if root else self.dir, p))

    def asset(self, p):
        for base in (self.dir, ROOT):
            q = os.path.normpath(os.path.join(base, p))
            if os.path.exists(q): return q
        return p

    def clip(self, name):
        return os.path.join(self.src_dir, name)

    def color(self, v):
        if isinstance(v, (list, tuple)): return tuple(v)
        if v in self.theme and isinstance(self.theme[v], str): v = self.theme[v]
        return hexrgb(v)

    def font(self, key):
        return self.asset(self.theme['fonts'].get(key, key))

    # ---------------------------------------------------------------- timeline
    def build_timeline(self):
        c = self.cfg
        self.aroll = []
        T = 0.0
        for i, a in enumerate(c['aroll']):
            d = a['out'] - a['in']
            self.aroll.append(dict(a, idx=i, t0=T, t1=T + d))
            T += d
        self.speech_end = T
        ec = c.get('endcard')
        self.total = T + (ec['duration'] if ec else 0.0)

    def words(self):
        """spoken words in output time: [start, end, text, aroll_index]"""
        if self._words is not None: return self._words
        out = []
        for a in self.aroll:
            p = os.path.join(self.work, 'words', a['clip'] + '.json')
            if not os.path.exists(p): continue
            for s, e, t in json.load(open(p, encoding='utf-8')):
                if s >= a['in'] - 0.05 and s < a['out'] - 0.05:
                    out.append([a['t0'] + max(s, a['in']) - a['in'], a['t0'] + min(e, a['out']) - a['in'], t, a['idx']])
        self._words = out
        return out

    def t(self, v, ref=None):
        """time value: number | 'w:слово#2+0.1' (start of 2nd spoken 'слово' +0.1s) |
        'we:слово' (end of the word) | '+1.5' (relative to ref) | 'end' (video end)"""
        if v is None: return None
        if isinstance(v, (int, float)): return float(v)
        v = v.strip()
        if v == 'end': return self.total
        if v == 'speech_end': return self.speech_end
        if v[0] in '+-' and ref is not None: return ref + float(v)
        m = re.match(r'^(w|we):(.+?)(?:#(\d+))?([+-]\d+(?:\.\d+)?)?$', v)
        if not m: raise ValueError(f'bad time: {v}')
        kind, word, n, off = m.group(1), norm_word(m.group(2)), int(m.group(3) or 1), float(m.group(4) or 0)
        hits = [w for w in self.words() if word in norm_word(w[2])]
        if len(hits) < n: raise ValueError(f'word "{m.group(2)}" (#{n}) not found in transcript')
        w = hits[n - 1]
        return (w[0] if kind == 'w' else w[1]) + off

    def span(self, el):
        a = self.t(el['at'])
        b = self.t(el.get('until', '+1.5'), ref=a)
        return a, b
