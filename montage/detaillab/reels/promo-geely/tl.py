import json, os
S = os.path.dirname(os.path.abspath(__file__)); R0 = os.path.dirname(S)
OUT = f"{S}/out"
TL = json.load(open(f"{OUT}/timeline.json"))
W = json.load(open(f"{S}/words_medium.json"))
pieces = TL['pieces']; SP = TL['sp']
VOICE_END = TL['voice_end']; TOTAL = TL['total']; MEME_AT = TL['meme_at']; MEME = TL['meme']
SHOTS = TL['shots']

def omap(c, ts):
    for pc, s, e, o in pieces:
        if pc == c and s - 0.06 <= ts < e:
            return o + max(0.0, ts - s) / SP
    return None

def inside(c, ts):
    return any(pc == c and s - 0.05 <= ts < e for pc, s, e, o in pieces)

def word(c, txt, k=1, after=0.0):
    n = 0
    for w in W[c]:
        if w[0] < after: continue
        if w[2].lower().strip('.,…?') == txt.lower():
            n += 1
            if n == k:
                r = omap(c, w[0])
                if r is None: raise KeyError(('cut', c, txt, k))
                return r
    raise KeyError((c, txt, k))

def shot_start(i): return SHOTS[i][0]
def shot_at(t):
    for a, b, kind, *rest in SHOTS:
        if a <= t < b: return (a, b, kind)
    return None
