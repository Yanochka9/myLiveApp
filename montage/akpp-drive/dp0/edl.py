"""EDL for the DP0/AL4 video: audio cut list, visual shots, and output-time mapping.

Source: IMG_2730.MOV (vertical 4K HLG, 2:19). The master reads a subscriber's question
from his phone, then answers. Several takes of the call-to-action; the last one is used.
"""
import json, os

SP = '/tmp/claude-0/-home-user-myLiveApp/4b9f072b-a840-5f1c-8c66-d2093439bbb6/scratchpad'
SRC = SP + '/src'
STK = SP + '/stock'
MAIN = f'{SRC}/2730.mov'
FPS = 30

def fr(x):  # snap to frame grid
    return round(x * FPS) / FPS

# ---- audio cut list (source time), every cut sits inside a detected pause ----
segs = [
    (9.92, 13.97),                                   # HOOK: "Проехав тысячу километров ... 10-20 км в час"
    (4.00, 5.22), (5.40, 7.62), (7.85, 8.92), (9.03, 9.86),   # "DP0, AL4. Сделали капиталку ... радиатор"
    (18.90, 20.20),                                  # "Что за проблема может быть?"
    (34.12, 37.42), (37.80, 41.05),                  # "Проблема данной коробки ... блок управления"
    (42.42, 45.15),                                  # "Утечка давления может быть по множеству причин"
    (45.50, 48.00),                                  # "Учитывая, что делали капиталку"
    (48.90, 52.58), (52.98, 55.45),                  # кольцо / уплотнение; радиатор
    (67.08, 69.25), (69.55, 71.28),                  # гидроблок, продукты износа
    (71.90, 72.60), (72.88, 74.80), (75.20, 76.00),  # "Поэтому сначала ... падать в аварию"
    (128.08, 131.62), (131.95, 135.15), (135.32, 137.70),  # диагностика, бесплатная, адрес
]
segs = [(fr(a), fr(b)) for a, b in segs]
HOOK_SRC = segs[0]

outs = []
t = 0.0
for a, b in segs:
    outs.append(t)
    t = fr(t + (b - a))
MAIN_DUR = t
END_PLATE = 3.0
TOTAL = fr(MAIN_DUR + END_PLATE)
HOOK_END = outs[1]

def m(src):
    """source time -> output time (snaps to the next kept segment if inside a cut)."""
    best = None
    for (a, b), o in zip(segs, outs):
        if a <= src <= b:
            return fr(o + src - a)
        if src < a and (best is None or a < best[0]):
            best = (a, o)
    return best[1] if best else MAIN_DUR

ANSWER = m(34.12)          # flash: question -> answer

# ---- b-roll windows (source-time bounds) ----
HLG = 'hlg'
broll = [
    # src_from, src_to, file, clip_in, kind, motion
    (5.40, 7.62, f'{SRC}/8842.mov', 6.0, HLG, 'in'),              # капиталку, поменяли масло
    (7.85, 9.86, f'{SRC}/9190.mov', 1.0, HLG, 'out'),             # теплообменник -> радиатор
    (37.80, 41.05, None, 0, 'scheme', None),                      # утечка давления, блок управления
    (45.50, 48.00, f'{SRC}/8842.mov', 26.0, HLG, 'out'),          # делали капиталку
    (50.40, 52.58, f'{SRC}/0784.mov', 0.3, HLG, 'in'),            # 1: кольцо / уплотнение
    (54.00, 55.45, f'{SRC}/9186.mov', 0.6, HLG, 'out'),           # 2: радиатор выносной
    (68.04, 69.25, f'{SRC}/8842.mov', 36.0, HLG, 'in'),           # 3: гидроблок
    (69.55, 71.28, f'{STK}/15056.mp4', 8.3, 'stock', 'out'),      # продукты износа (щуп)
    (72.88, 74.80, f'{STK}/72.mp4', 2.0, 'stock', 'in'),          # ехала нормально
    (130.12, 131.62, f'{STK}/13270.mp4', 0.4, 'stock', 'out'),    # диагностика
]
# crop centre (0..1 of the free width) and exposure fixes for 16:9 stock
STOCK_FIX = {
    '15056': (0.71, ',eq=brightness=0.04:gamma=1.25:contrast=1.05'),
    '72': (0.18, ''),
    '13270': (0.54, ',eq=brightness=-0.08:contrast=1.10:gamma=0.92'),
}

# split long A-roll shots at a word boundary (framing change without a time jump)
SPLITS = [35.10, 43.48, 49.92, 53.12, 67.54, 74.10, 129.38, 133.44]

def build_shots():
    wins = [(m(a), m(b), f, ci, k, mo) for a, b, f, ci, k, mo in broll]
    glued = []
    for w in wins:
        if glued and w[0] - glued[-1][1] < 0.25:
            p = glued[-1]
            glued[-1] = (p[0], w[0], *p[2:])
        glued.append(w)
    shots = [dict(o0=0.0, o1=HOOK_END, kind='hook', src=MAIN, cin=HOOK_SRC[0])]
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
            shots.append(dict(o0=p0, o1=p1, kind='aroll', src=MAIN, cin=fr(a + p0 - o)))
    for w in glued:
        shots.append(dict(o0=w[0], o1=w[1], kind=w[4], src=w[2], cin=w[3], motion=w[5]))
    shots.append(dict(o0=MAIN_DUR, o1=TOTAL, kind='endplate', src=MAIN, cin=137.5))
    shots.sort(key=lambda s: s['o0'])
    merged = []
    for s in shots:
        if s['kind'] == 'aroll' and s['o1'] - s['o0'] < 0.25 and merged:
            merged[-1]['o1'] = s['o1']; continue
        merged.append(s)
    shots = merged
    # merge consecutive A-roll pieces (a removed pause between them) into one shot list entry
    # but keep them separate so every jump-cut changes framing
    out = []
    for s in shots:
        cut = [m(x) for x in SPLITS if s['kind'] == 'aroll' and s['o0'] + 0.6 < m(x) < s['o1'] - 0.6]
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
    for p, q in zip(shots, shots[1:]):
        assert abs(p['o1'] - q['o0']) < 1e-6, (p, q)
    return shots

def gfx_timeline():
    shots = build_shots()
    def shot(name, cin=None):
        return next(s for s in shots if s['src'] and name in s['src'] and s['kind'] != 'aroll'
                    and (cin is None or abs(s['cin'] - cin) < 0.01))
    sch = next(s for s in shots if s['kind'] == 'scheme')
    r1, r2, r3 = shot('0784'), shot('9186'), shot('8842', 36.0)
    oil = shot('15056')
    return dict(
        fps=FPS, total=TOTAL, main=MAIN_DUR, hook=HOOK_END,
        card=[0.10, HOOK_END],
        counter=[m(10.12), m(10.80), m(12.94), HOOK_END],      # 0 -> 1000 KM, then 10-20 KM/Ч
        flashes=[HOOK_END, ANSWER, MAIN_DUR],
        header=[HOOK_END + 0.15, m(7.85)],
        scheme=[sch['o0'], sch['o1'], m(38.46), m(39.70)],
        reasons=[[m(50.64), r1['o0'], r1['o1']], [m(54.04), r2['o0'], r2['o1']],
                 [m(68.50), r3['o0'], r3['o1']], m(71.90)],
        oil=[oil['o0'], oil['o1'], m(70.18)],
        free=[m(131.98), m(133.18)],
        address=[m(135.32), MAIN_DUR],
        endplate=[MAIN_DUR, TOTAL],
    )

if __name__ == '__main__':
    for s in build_shots():
        print(f"{s['o0']:6.2f}-{s['o1']:6.2f} {s['o1']-s['o0']:5.2f} {s['kind']:8} "
              f"{os.path.basename(s['src'] or '-'):10} in={s['cin']:.2f} {s.get('zoom','')}{s.get('motion','') or ''}")
    print('main', MAIN_DUR, 'total', TOTAL, 'hook_end', HOOK_END)
    print(json.dumps(gfx_timeline()))
