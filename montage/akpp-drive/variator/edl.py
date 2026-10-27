"""EDL for the CVT video: audio cut list, visual shots, and output-time mapping."""
import json, os

SP = '/tmp/claude-0/-home-user-myLiveApp/75b90058-7218-5b2d-9670-da814b9070c8/scratchpad'
SRC = SP + '/src'
STK = SP + '/assets/stock'
FPS = 30

def fr(x):  # snap to frame grid
    return round(x * FPS) / FPS

# ---- audio cut list (source = D5CB) ----
HOOK_END_SRC = 4.22
MAIN_START = 5.30
END_SRC = 57.93
silences = [(9.57, 10.00), (12.07, 12.45), (13.91, 14.19), (16.11, 16.46), (18.26, 18.70),
            (19.88, 20.33), (22.17, 22.50), (24.17, 24.50), (26.76, 27.22), (27.57, 28.10),
            (30.26, 30.65), (34.68, 34.95), (35.82, 36.11), (38.53, 39.00), (40.27, 40.83),
            (43.87, 44.94), (50.47, 51.06), (52.96, 53.60), (54.74, 54.98), (56.80, 57.21)]
PAD = 0.05
segs = [(0.0, HOOK_END_SRC)]
cur = MAIN_START
for a, b in silences:
    segs.append((cur, a + PAD))
    cur = b - PAD
segs.append((cur, END_SRC))
segs = [(fr(a), fr(b)) for a, b in segs]

# output start of each segment
outs = []
t = 0.0
for a, b in segs:
    outs.append(t)
    t = fr(t + (b - a))
MAIN_DUR = t
END_PLATE = 3.0
TOTAL = fr(MAIN_DUR + END_PLATE)

def m(src):
    """source time -> output time (snaps into the next segment if inside a cut)."""
    for (a, b), o in zip(segs, outs):
        if src < a:
            return o
        if src <= b:
            return fr(o + src - a)
    return MAIN_DUR

HOOK_END = m(HOOK_END_SRC)

# ---- b-roll windows (source-time bounds) ----
HLG = 'hlg'
broll = [
    # src_from, src_to, file, clip_in, kind, motion
    (12.40, 13.97, f'{SRC}/8842.mov', 2.0, HLG, 'in'),
    (13.97, 16.11, f'{STK}/13260.mp4', 2.0, 'stock', 'out'),
    (18.10, 19.88, f'{STK}/41937.mp4', 1.0, 'stock', 'in'),
    (22.92, 24.17, f'{STK}/33324.mp4', 9.3, 'stock', 'in'),
    (24.50, 26.00, f'{SRC}/9190.mov', 1.0, HLG, 'out'),
    (26.00, 27.57, f'{SRC}/9186.mov', 0.5, HLG, 'in'),
    (28.10, 30.26, f'{SRC}/8842.mov', 17.6, HLG, 'out'),
    (30.65, 32.52, f'{SRC}/0784.mov', 0.3, HLG, 'in'),
    (32.52, 35.82, f'{SRC}/0792.mov', 0.0, HLG, 'in'),
    (36.11, 40.27, None, 0, 'scheme', None),
    (40.83, 42.38, f'{SRC}/0787.mov', 0.5, HLG, 'out'),
    (42.38, 43.87, f'{SRC}/0788.mov', 1.0, HLG, 'in'),
    (44.94, 46.20, f'{SRC}/0786.mov', 0.0, HLG, 'out'),
]

def build_shots():
    wins = [(m(a), m(b), f, ci, k, mo) for a, b, f, ci, k, mo in broll]
    # glue windows that only have a removed pause (or <0.25s of A-roll) between them
    glued = []
    for w in wins:
        if glued and w[0] - glued[-1][1] < 0.25:
            p = glued[-1]
            glued[-1] = (p[0], w[0], *p[2:])
        glued.append(w)
    shots = []
    # hook
    shots.append(dict(o0=0.0, o1=HOOK_END, kind='hook', src=f'{SRC}/D5CB.mov', cin=0.0))
    # A-roll pieces = segment pieces not covered by windows
    zoom = 0
    for (a, b), o in zip(segs[1:], outs[1:]):
        o1 = fr(o + b - a)
        pieces = [(o, o1)]
        for w in glued:
            nxt = []
            for p0, p1 in pieces:
                if w[1] <= p0 or w[0] >= p1:
                    nxt.append((p0, p1)); continue
                if w[0] > p0: nxt.append((p0, w[0]))
                if w[1] < p1: nxt.append((w[1], p1))
            pieces = nxt
        for p0, p1 in pieces:
            if p1 - p0 < 1 / FPS: continue
            shots.append(dict(o0=p0, o1=p1, kind='aroll', src=f'{SRC}/D5CB.mov',
                              cin=fr(a + p0 - o), zoom=zoom % 2))
            zoom += 1
    for w in glued:
        shots.append(dict(o0=w[0], o1=w[1], kind=w[4], src=w[2], cin=w[3], motion=w[5]))
    shots.append(dict(o0=MAIN_DUR, o1=TOTAL, kind='endplate', src=f'{SRC}/D5CB.mov', cin=57.5))
    shots.sort(key=lambda s: s['o0'])
    # absorb A-roll slivers into the preceding shot
    merged = []
    for s in shots:
        if s['kind'] == 'aroll' and s['o1'] - s['o0'] < 0.25 and merged:
            merged[-1]['o1'] = s['o1']; continue
        merged.append(s)
    shots = merged
    # split long A-roll shots at a word boundary (framing change without a time jump)
    SPLITS = [7.58, 48.50]
    out = []
    for s in shots:
        cut = [m(x) for x in SPLITS if s['kind'] == 'aroll' and s['o0'] + 0.8 < m(x) < s['o1'] - 0.8
               and abs((s['cin'] + m(x) - s['o0']) - x) < 0.05]
        if cut:
            c = cut[0]
            a = dict(s); a['o1'] = c
            b = dict(s); b['o0'] = c; b['cin'] = fr(s['cin'] + c - s['o0'])
            out += [a, b]
        else:
            out.append(s)
    shots = out
    z = 0
    for s in shots:
        if s['kind'] == 'aroll':
            s['zoom'] = z % 2; z += 1
    # sanity: contiguous coverage
    for p, q in zip(shots, shots[1:]):
        assert abs(p['o1'] - q['o0']) < 1e-6, (p, q)
    return shots

if __name__ == '__main__':
    shots = build_shots()
    for s in shots:
        print(f"{s['o0']:6.2f}-{s['o1']:6.2f} {s['o1']-s['o0']:5.2f} {s['kind']:8} {os.path.basename(s['src'] or '-'):10} in={s['cin']:.2f} {s.get('zoom','')}{s.get('motion','') or ''}")
    print('main', MAIN_DUR, 'total', TOTAL, 'hook_end', HOOK_END)

def gfx_timeline():
    shots = build_shots()
    def shot(name):
        return next(s for s in shots if s['src'] and name in s['src'] and s['kind'] != 'aroll')
    s0792 = shot('0792'); s0787 = shot('0787'); s0788 = shot('0788')
    sch = next(s for s in shots if s['kind'] == 'scheme')
    return dict(
        fps=FPS, total=TOTAL, main=MAIN_DUR,
        rec=[0, HOOK_END],
        flashes=[HOOK_END, m(23.68), MAIN_DUR],
        header=[m(5.30) + 0.15, m(12.40)],
        ellipse=[s0792['o0'] + 0.25, s0792['o1'], m(35.04)],
        scheme=[sch['o0'], sch['o1'], m(37.24), m(39.46)],
        chain=[s0787['o0'] + 0.15, s0788['o1'], m(41.58)],
        counter=[m(46.46), m(47.64), m(47.96), m(50.40)],
        address=[m(55.32), MAIN_DUR],
        endplate=[MAIN_DUR, TOTAL],
    )
