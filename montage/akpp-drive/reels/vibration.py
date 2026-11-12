"""Reel 1: answer to a question — «Т5 автомат, вибрация при разгоне до 4-й передачи» (young mechanic)."""
import sys
import lib

NAME = 'vibration'
GRADE = 'C+'           # client's colour (as Lifan)
SFX_GAIN = 0.55        # quieter sounds (client)
MUSIC, MUSIC_IN = '8AEA.mov', 0.0     # new track from «музыка и звуки» (6549 was used too much)
PROMPT = 'Т5 автомат, вибрация при разгоне. Гидротрансформатор, планетарные механизмы, гидроблок, поддон, бронзовая стружка.'
# hook: he reads the subscriber's question; air before/after, barely-there push-in, DP0 question card, no riser
HOOK = dict(src='3990', pieces=[(2.85, 7.05)], face=(0.5, 0.22), zoom_from=1.0, zoom_to=1.05, ease='smooth')

A = dict(crop=(0.5, 0.08))
PHRASES = [
    ('3990', 8.40, 13.45, A),     # Чаще всего причиной вибрации является двигатель и подушки
    ('3990', 15.30, 17.80, A),    # Но сама коробка также может быть источником вибрации
    ('3990', 18.60, 21.25, A),    # Особенно если вибрация происходит до конкретной передачи
    ('3990', 39.15, 45.85, A),    # (Поскольку) если бы проблема была в двигателе ... диапазоне разгона; 35.2–37.3 is «она…» + background talk
    ('3990', 56.70, 63.65, A),    # Если дело в коробке ... гидротрансформатор ... планетарные механизмы
    ('3990', 77.75, 85.25, A),    # Рекомендуем обратить внимание на качество масла. Снять поддон ... бронзовой стружки
    ('3990', 85.70, 87.30, A),    # А также металлических включений
    ('3990', 87.70, 92.50, A),    # Это будет свидетельствовать об износе ...
    ('3990', 98.70, 109.40, A),   # А также обратите внимание на качество включения передач ... гидроблоке
    ('3990', 144.50, 148.70, A),  # И если дело всё-таки в коробке, то процесс разрушения уже запущен
    ('3990', 131.00, 136.20, A),  # Поскольку в последующем машина может просто встать на дороге
    ('3990', 248.10, 255.30, A),  # Поэтому наши рекомендации ... У нас диагностика бесплатная
    ('3990', 255.30, 258.05, A),  # Находимся по адресу Дзержинского, 82А
    ('3990', 266.00, 268.20, A),  # Подземный автокомплекс. Запись Директ
]

PHRASEFIX = [('может открыться', 'МОЖЕТ *СКРЫВАТЬСЯ'), ('держитского 82', 'ДЗЕРЖИНСКОГО 82А'), ('в директ', 'В ДИРЕКТ'),
             ('проблем в', 'ПРОБЛЕМА В'), ('попинуется', '*ПИНАЕТСЯ'), ('пинается', '*ПИНАЕТСЯ'), ('держинского', 'ДЗЕРЖИНСКОГО')]
WORDFIX = {}
ACCENT = ['двигатель', 'подушки', 'коробка', 'конкретной', 'гидротрансформатор', 'планетарные', 'масла',
          'бронзовой', 'стружки', 'подергивается', 'гидроблоке', 'запущен', 'встать', 'бесплатная', 'всем']

BROLL = [   # no drilling shots (client); own footage first, then CC images (Wikimedia) and Mixkit
    ('3990', 9.7, 12.5, '4716.mp4', 1.0, 'in', dict(cx=0.45)),       # двигатель и изношенные подушки
    ('3990', 15.4, 17.7, '8842', 3.0, 'out'),                        # сама коробка тоже может быть (gearbox on the bench)
    ('3990', 18.6, 21.25, 'scheme', 0, None),                        # gears chart: only up to 4th
    ('3990', 38.0, 41.6, '17613.mp4', 1.0, 'out', dict(cx=0.5)),     # не зависела бы от конкретной передачи
    ('3990', 42.3, 45.8, '64.mp4', 4.0, 'in', dict(cx=0.5)),         # на всём диапазоне разгона
    ('3990', 59.6, 61.1, 'tc_cut.jpg', 0, 'in', dict(letterbox=True, dy=0)),      # гидротрансформатор (CC BY-SA 3.0)
    ('3990', 61.4, 63.65, 'scheme', 0, None),                        # планетарные механизмы: animated 2D planetary set
    ('3990', 77.75, 80.3, '15056.mp4', 9.5, 'in', dict(cx=0.45)),    # качество масла
    ('3990', 80.7, 82.4, '9190', 2.0, 'out'),                        # снять поддон (gearbox from below, own)
    ('3990', 88.0, 90.3, '0792', 0.5, 'in'),                         # износ планетарных механизмов
    ('3990', 99.5, 104.8, 'scheme', 0, None),                        # качество включения передач / пинки: 2D shift scheme
    ('3990', 106.2, 109.4, '8842', 24.0, 'in'),                      # гидроблок (work on the unit)
    ('3990', 146.3, 148.7, '0786', 1.0, 'in'),                       # процесс разрушения запущен
    ('3990', 133.0, 134.9, '12736.mp4', 30.0, 'in', dict(cx=1.0)),   # встать на дороге (car on the roadside, hazards on)
    ('3990', 134.9, 136.2, '14986.mp4', 3.6, 'out', dict(cx=0.85)),  # с неработающей коробкой (hazard button)
    ('3990', 250.1, 253.4, '9186', 0.5, 'in'),                       # профильный сервис (own service footage)
]

END_Q = ['А У ВАС', 'БЫЛА ВИБРАЦИЯ', 'ПРИ РАЗГОНЕ?']


CARD_KEY = {'т5', 'вибрация', '4', '4.'}
CARD_FIX = {'Проблем': 'Проблема', 'быть.': 'быть?'}


def _card_words(R):
    """the question exactly as he reads it, timed by the re-transcribed voice"""
    out = []
    for t, w, *_ in R.words():
        if t >= R.HOOK_END - 0.05:
            break
        w = CARD_FIX.get(w, w)
        out.append([t, w, w.lower().strip('.,?!') in CARD_KEY or w.lower() in CARD_KEY])
    return out


def _schemes(R):
    return [s for s in R.shots() if s['kind'] == 'scheme'][:3]   # gears, planetary, shifts (in time order)


def gfx(R):
    m = R.m
    sch, pl, sf = _schemes(R)
    return [
        dict(type='qcard', t0=-0.5, t1=R.HOOK_END, words=_card_words(R), size=40),   # DP0-style subscriber question card
        dict(type='flash', t=R.HOOK_END),
        dict(type='versus', t0=R.HOOK_END + 0.1, t1=m('3990', 9.7), a='ДВИГАТЕЛЬ', b='КОРОБКА', tw=m('3990', 8.6), y=1130),
        dict(type='gears', t0=sch['o0'], t1=sch['o1'], upto=4, lt=sch['o0'] + 1.0, label='ДО 4-Й → ПРОВЕРЯЕМ КОРОБКУ'),
        dict(type='planet', t0=pl['o0'], t1=pl['o1'], wt=pl['o0'] + 0.9, label='ИЗНОС → ВИБРАЦИЯ'),
        # what to check, as the master says it: low, near the subtitles, stacked 3D plates
        dict(type='steps', t0=m('3990', 80.75), t1=m('3990', 92.6), y=1000, dy=112, title='ПРОВЕРЬТЕ МАСЛО', lastRed=True,
             rows=[['СНИМИТЕ ПОДДОН', m('3990', 80.75)], ['БРОНЗОВАЯ СТРУЖКА?', m('3990', 83.5)],
                   ['МЕТАЛЛ В МАСЛЕ?', m('3990', 85.8)], ['= ИЗНОС ПЛАНЕТАРКИ И ГТР', m('3990', 89.0)]]),
        dict(type='shift', t0=sf['o0'], t1=sf['o1'], shifts=[m('3990', 102.2), m('3990', 103.2), m('3990', 104.2)]),
        dict(type='flash', t=m('3990', 144.55)),
        dict(type='big3d', t0=m('3990', 254.0), t1=m('3990', 255.35), text='0 BYN', sub='ДИАГНОСТИКА БЕСПЛАТНО', y=1130, size=170),
        dict(type='address', t0=m('3990', 255.3), t1=R.MAIN, text='Дзержинского, 82А'),
    ]


def sfx(R):
    m = R.m
    sch, pl, sf = _schemes(R)
    ev = [
        (0.0, 'intrigue_vib', 0.007),                           # barely audible bed under the question, whole first shot
        (R.HOOK_END, 'click1', 0.04),                           # into the answer (no riser)
        (sch['o0'], 'scheme-glitch', 0.03), (sch['o0'] + 1.0, 'click4', 0.04),
        (pl['o0'], 'scheme-glitch', 0.03), (pl['o0'] + 0.9, 'scheme-static', 0.035),
        (m('3990', 80.75), 'click2', 0.035), (m('3990', 83.5), 'click3', 0.035), (m('3990', 85.8), 'click5', 0.035), (m('3990', 89.0), 'click4', 0.04),
        (sf['o0'], 'scheme-glitch', 0.03),
        (m('3990', 102.2), 'click1', 0.04), (m('3990', 103.2), 'click1', 0.04), (m('3990', 104.2), 'click1', 0.04),
        (m('3990', 144.55), 'click2', 0.045),
        (m('3990', 254.0), 'click3', 0.04),
        (m('3990', 255.3) + 0.3, 'click1', 0.04),
    ]
    for j in range(len(END_Q)):
        ev.append((R.MAIN + 0.25 + j * 0.12, ['click1', 'click5', 'click4', 'click3'][j], 0.035))
    ev.append((R.MAIN + 1.05, 'click1', 0.03))
    return ev


if __name__ == '__main__':
    R0 = lib.Reel(sys.modules[__name__])
    HIDE = [(0.0, R0.HOOK_END), (R0.m('3990', 255.3), R0.MAIN)]   # question card / spoken address shown as plates
    lib.main(sys.modules[__name__])
