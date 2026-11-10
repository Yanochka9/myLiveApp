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
# The subscriber's question is read in full (card on screen), then the answer.
segs = [
    (2.96, 3.45), (4.00, 5.22), (5.40, 7.62), (7.85, 8.92), (9.03, 13.97),   # question, part 1
    (14.40, 18.16), (18.90, 20.20),                  # "... и в стабильной езде. Что за проблема может быть?"
    (34.12, 37.42), (37.80, 41.05),                  # "Проблема данной коробки ... блок управления"
    (42.42, 45.15),                                  # "Утечка давления может быть по множеству причин"
    (45.50, 48.00),                                  # "Учитывая, что делали капиталку"
    (48.90, 52.58), (52.98, 55.45),                  # кольцо / уплотнение; радиатор
    (67.08, 69.25), (69.55, 71.28),                  # гидроблок, продукты износа
    (71.90, 72.60), (72.88, 74.80), (75.20, 76.00),  # "Поэтому сначала ... падать в аварию"
    (128.08, 131.62), (131.95, 135.15), (135.32, 137.70),  # диагностика, бесплатная, адрес
]
segs = [(fr(a), fr(b)) for a, b in segs]
Q_SEGS = 7                       # the first 7 segments are the question

outs = []
t = 0.0
for a, b in segs:
    outs.append(t)
    t = fr(t + (b - a))
MAIN_DUR = t
END_PLATE = 3.0
TOTAL = fr(MAIN_DUR + END_PLATE)
HOOK_END = outs[Q_SEGS]          # end of the question = flash, music starts here

def m(src):
    """source time -> output time (snaps to the next kept segment if inside a cut)."""
    best = None
    for (a, b), o in zip(segs, outs):
        if a <= src <= b:
            return fr(o + src - a)
        if src < a and (best is None or a < best[0]):
            best = (a, o)
    return best[1] if best else MAIN_DUR

ANSWER = HOOK_END

# ---- b-roll windows (source-time bounds) ----
# Only parts / tools / boxes; no people. Stock where we have no own footage.
# The client's own footage is used only for diagnostics (9190).
HLG = 'hlg'
IMG = f'{SP}/img'
broll = [
    # src_from, src_to, file, clip_in, kind, motion
    (5.40, 7.62, f'{IMG}/f1gear.jpg', 0, 'image', 'in'),          # капиталку
    (7.85, 9.86, f'{IMG}/radiator.jpg', 0, 'image', 'out'),       # теплообменник -> радиатор
    (9.92, 11.26, f'{STK}/17613.mp4', 3.0, 'stock', 'in'),        # тысячу километров (одометр)
    (12.94, 14.90, f'{STK}/2675.mp4', 1.0, 'stock', 'out'),       # 10-20 км/ч
    (16.48, 18.16, f'{STK}/3304.mp4', 4.0, 'stock', 'in'),        # в пробках, в стабильной езде
    (37.80, 41.05, None, 0, 'scheme', None),                      # утечка давления, блок управления
    (45.50, 48.00, f'{STK}/12341.mp4', 3.0, 'stock', 'out'),      # делали капиталку (шестерни)
    (50.38, 52.58, None, 0, 'ring', None),                        # 1: тефлоновое кольцо (графика)
    (54.00, 55.45, None, 0, 'cooler', None),                      # 2: радиатор выносной (графика)
    (68.04, 69.25, None, 0, 'clog', None),                        # 3: гидроблок забит (графика)
    (69.55, 71.28, f'{STK}/15056.mp4', 8.3, 'stock', 'out'),      # продукты износа (щуп)
    (72.88, 74.80, f'{STK}/14945.mp4', 1.0, 'stock', 'in'),       # ехала нормально (селектор АКПП)
    (74.54, 76.00, f'{IMG}/cel1.jpg', 0, 'image', 'in'),          # падать в аварию (чек на приборке)
    (130.12, 131.62, f'{SRC}/9190.mov', 1.0, HLG, 'out'),         # диагностика (наш подсъём)
]
# crop centre (0..1 of the free width) and exposure fixes for 16:9 stock / images
STOCK_FIX = {
    '15056': (0.71, ',eq=brightness=0.04:gamma=1.25:contrast=1.05'),
    '14945': (0.37, ''),
    '12341': (0.55, ',eq=brightness=0.06:gamma=1.35:contrast=1.05'),
    '17613': (0.62, ''),
    '2675': (0.66, ''),
    '3304': (0.45, ''),
    'f1gear': (0.52, ''),
    'radiator': (0.55, ''),
    'cel1': (0.50, ''),
}

# split long A-roll shots at a word boundary (framing change without a time jump)
SPLITS = [4.52, 15.42, 35.10, 43.48, 49.92, 53.12, 67.54, 74.10, 129.38, 133.44]

def build_shots():
    wins = [(m(a), m(b), f, ci, k, mo) for a, b, f, ci, k, mo in broll]
    glued = []
    for w in wins:
        if glued and w[0] - glued[-1][1] < 0.25:
            p = glued[-1]
            glued[-1] = (p[0], w[0], *p[2:])
        glued.append(w)
    shots = []
    for (a, b), o in zip(segs, outs):
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

# subscriber's question as shown on the card: (source time the word is spoken, word, key)
CARD_WORDS = """
3.01 Здравствуйте.
4.04 *DP0,
4.52 *AL4.
5.45 Сделали
5.68 *капиталку,
6.14 после
6.32 обкатки
6.80 поменяли
7.10 масло.
7.91 Теплообменник
8.32 вырезали,
9.03 поставили
9.38 *радиатор.
9.95 Проехав
10.12 *1000 км,
10.86 коробка
11.26 начала
11.42 уходить
11.82 *в
11.90 *аварию
12.18 на
12.28 малой
12.48 скорости,
12.94 *10–20 км/ч.
14.65 Перед
14.74 этим
14.90 отъездил
15.42 пару
15.66 часов
15.86 без
16.14 проблем
16.48 и
16.70 в
16.80 пробках,
17.18 и
17.38 в
17.44 стабильной
17.72 езде.
19.12 Что
19.16 за
19.26 проблема
19.66 может
19.82 быть?
"""

def gfx_timeline():
    shots = build_shots()
    def win(kind=None, name=None):
        return next(s for s in shots if (kind and s['kind'] == kind) or
                    (name and s['src'] and name in s['src'] and s['kind'] != 'aroll'))
    words = []
    for line in CARD_WORDS.strip().splitlines():
        t, w = line.split(' ', 1)
        words.append([m(float(t)), w.lstrip('*'), w.startswith('*')])
    sch, ring, clog = win('scheme'), win('ring'), win('clog')
    cool, oil = win('cooler'), win(name='15056')
    return dict(
        fps=FPS, total=TOTAL, main=MAIN_DUR, hook=HOOK_END,
        card=dict(a=-0.5, b=HOOK_END, words=words),
        flashes=[HOOK_END, MAIN_DUR],
        scheme=[sch['o0'], sch['o1'], m(38.46), m(39.70)],
        ring=[ring['o0'], ring['o1'], m(51.12)],
        clog=[clog['o0'], clog['o1']],
        cooler=[cool['o0'], cool['o1'], m(54.40)],
        reasons=[[m(50.64), None, None], [m(54.04), None, None], [m(68.50), None, None], m(71.90)],
        reasons_vis=[[ring['o0'], ring['o1']], [cool['o0'], cool['o1']], [clog['o0'], clog['o1']], [oil['o0'], oil['o1']]],
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
