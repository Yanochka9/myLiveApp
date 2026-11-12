"""Reel 2: Lifan X60 — «Они говорили, что китайцы х**ня» (story, young mechanic). v2 after client notes."""
import lib

NAME = 'lifan'
GRADE = 'C+'           # colour chosen by the client (lib.GRADES): C (cold dark) made a touch livelier
SFX_GAIN = 0.55
SUB_MIN = 0.27         # he starts talking ~0.4 s into the hook (lead-in)        # all transition/plate sounds ~5 dB quieter (client)
PROMPT = 'К нам в работу приехал Lifan X60. Пакет сцепления задней передачи, АКПП, вариатор.'
MUSIC, MUSIC_IN = 'FCD0.mov', 3.41          # client's track from «музыка и звуки» (as in DP0), hit on the cut
# hook: slow push-in while he says the line, then ~0.8 s of silence (kept from the take), click, main part
HOOK = dict(src='3994', pieces=[(0.60, 3.35)], face=(0.43, 0.28), zoom_from=1.0, zoom_to=1.28, ease=1.0)
BLEEP = [('3994', 2.14, 2.60)]

A = dict(crop=(0.44, 0.07))          # crop centre for the 1.35x framing (face at ~44 % width)
PHRASES = [
    ('4004', 1.40, 17.20, A),        # К нам в работу приехал Lifan X60 ... сожранный ремень
    ('4004', 37.20, 42.95, A),       # При согласовании ремонта ... ремень
    ('4004', 45.35, 48.40, A),       # А клиент поведал нам историю
    ('4004', 62.75, 70.60, A),       # Как оказалось, владеет более 10 лет ... 2016 году в автосалоне
    ('4007', 2.85, 11.40, A),        # пробег больше 200 тысяч ... замена левой шаровой
    ('4005', 31.45, 35.10, A),       # В остальном была только замена масла
    ('4005', 36.00, 44.00, A),       # И секрет такого долголетия ... по регламенту
    ('4007', 20.80, 25.45, A),       # Но клиент не учёл ... условия эксплуатации
    ('4009', 0.00, 19.50, dict(A, tail=0.15)),   # ... явился гараж клиента, a short beat
    ('gap_meme', 0.0, 2.01),          # Якубович: two whole «Да ладно» (0.95–2.96 of the client's clip, silence on both ends)
    ('4011', 4.55, 21.95, dict(A, head=0.25)),    # short pause, then: Въезд в гараж ... по несколько раз на день
    ('4014', 0.90, 13.10, A),        # Если бы интервал ... пакета сцепления
    ('4016', 0.00, 5.25, dict(A, tail=0.45)),    # Поэтому меняйте масло своевременно, а лучше чуть чаще — pause
    ('4016', 9.75, 13.00, A),        # И следите за состоянием своего автомобиля
]

PHRASEFIX = [('по рекламе', 'ПО *РЕГЛАМЕНТУ'), ('по рекламенту', 'ПО *РЕГЛАМЕНТУ'), ('купил у нее', 'КУПИЛ ЕЁ'),
             ('пакета слиния', 'ПАКЕТА СЦЕПЛЕНИЯ'), ('пакетов пленки', 'ПАКЕТА СЦЕПЛЕНИЯ'), ('находится', 'НАХОДИЛСЯ'),
             ('сожженный', 'СОЖРАННЫЙ'), ('проблемы', 'С ПРОБЛЕМОЙ'), ('хуйня', '*Х**НЯ')]
WORDFIX = {'Elefant': 'LIFAN', 'хуйня.': '*Х**НЯ', 'современная': 'СВОЕВРЕМЕННАЯ', '-60': '–60', '-40,': '–40'}
ACCENT = ['слизанные', 'зубья', 'задиры', 'сожранный', 'ремень', 'гараж', 'задом', 'огромную', 'нагрузку',
          'своевременно', 'чаще', 'регламенту', 'уклоном', 'китайцы']

# b-roll at original speed only: (file, src_from, src_to, clip, clip_in, motion[, opt])
BROLL = [
    ('4004', 8.15, 10.0, '9190', 0.8, 'in'),                         # провели дефектовку: снимают коробку (client, DP0 folder)                         # провели дефектовку
    ('4004', 10.25, 13.35, '4019', 0.0, 'out'),                      # слизанные зубья пакета сцепления (main accent)
    ('4004', 14.0, 15.8, '0792', 0.2, 'in'),                           # задиры на валах
    ('4004', 15.8, 17.2, '0786', 0.3, 'out'),                        # сожранный ремень (4025 is iPhone slow-mo)
    ('4004', 39.3, 41.0, '4017', 0.2, 'in'),                           # оба пакета сцеплений
    ('4004', 41.0, 42.95, '0784', 0.4, 'out'),                       # комплект валов и ремень
    ('4004', 46.5, 48.4, '41571.mp4', 0.4, 'in', dict(cx=0.55)),     # историю этого автомобиля
    ('4007', 3.7, 6.7, '2675.mp4', 3.5, 'in', dict(cx=0.5)),         # 200 тысяч км (counter on top)
    ('4005', 31.7, 35.1, '15056.mp4', 4.0, 'out', dict(cx=0.42)),    # замена масла в двигателе и в коробке
    ('4009', 5.5, 9.0, '41571.mp4', 4.4, 'in', dict(cx=0.5)),          # по загородным и проселочным дорогам
    ('gap_meme', 0.0, 2.01, 'yakubovich2.mp4', 0.0, 'in', dict(letterbox=True)),  # meme insert
    ('4011', 6.2, 16.0, 'scheme', 0, None),                          # garage on a slope (2D scheme)
    ('4011', 16.3, 19.3, '4022', 0.4, 'in'),                         # пакет задней передачи — нагрузка
    ('4014', 7.3, 9.7, '0792', 1.4, 'out'),                           # последствий для валов (4026 is iPhone slow-mo)
    ('4014', 10.5, 12.7, '8842', 17.0, 'in'),                        # заменой пакета сцепления
]

END_Q = ['КАК ЧАСТО', 'ВЫ МЕНЯЕТЕ', 'МАСЛО', 'В КОРОБКЕ?']


def _shot(R, name):
    return next(s for s in R.shots() if s['src'] and s['src'].endswith(name) and s['kind'] not in ('aroll', 'hook'))


def gfx(R):
    m = R.m
    d = _shot(R, '4019.MOV')
    sch = next(s for s in R.shots() if s['kind'] == 'scheme')
    return [
        dict(type='flash', t=R.HOOK_END),
        dict(type='header', t0=R.HOOK_END + 0.1, t1=m('4004', 8.1), text='LIFAN X60', sub='НЕТ ЗАДНЕЙ ПЕРЕДАЧИ', y=1150),
        # the main accent: worn teeth on the clutch disc
        # follows the smooth inner edge of the brown disc (measured on the rendered shot)
        dict(type='ellipse', t0=d['o0'] + 0.1, t1=d['o1'], cx=540, rx=370, ry=64, rot=0, kt0=d['o0'],
             cy=[(0.0, 892), (0.1, 893), (0.2, 872), (0.3, 840), (0.4, 825), (0.5, 811), (0.6, 799), (0.7, 784), (0.8, 772), (0.9, 770), (1.0, 764), (1.1, 761), (1.2, 760), (1.3, 757), (1.4, 754), (1.5, 752), (1.6, 753), (1.7, 755), (1.8, 751), (1.9, 742), (2.0, 732), (2.1, 728), (2.2, 724), (2.3, 725), (2.4, 718), (2.5, 721), (2.6, 723), (2.7, 727), (2.8, 745), (2.9, 747), (3.0, 747), (3.2, 747)],   # rim of the brown disc, tracked on the rendered shot (shot-relative s, y px)
             label='ЗУБЬЯ СЛИЗАНЫ', lx=540, ly=1120, lt=d['o0'] + 0.5, size=50),
        dict(type='big3d', t0=m('4004', 64.3), t1=m('4004', 66.15), text='10+', sub='ЛЕТ ВЛАДЕНИЯ', y=1170, size=190),
        dict(type='big3d', t0=m('4004', 66.3), t1=m('4004', 70.6), text='2016', sub='НОВАЯ ИЗ САЛОНА', y=1170, size=170),
        dict(type='counter', t0=m('4007', 3.7), hit=m('4007', 5.4), t1=m('4007', 6.75), to=200000, step=1000,
             label='КМ ПРОБЕГА', size=108, y=1120),
        dict(type='flash', t=m('4007', 20.85)),
        dict(type='garage', t0=sch['o0'], t1=sch['o1'], ta=m('4011', 14.4), tr=m('4011', 14.4) + 0.6),
        dict(type='interval', t0=m('4014', 1.5), t1=m('4014', 7.2), title='ЗАМЕНА МАСЛА КАЖДЫЕ',
             old='50–60 ТЫС. КМ', new='30–40 ТЫС. КМ', tx=m('4014', 5.0), tn=m('4014', 5.4), y=1010),
        dict(type='address', t0=m('4016', 10.0), t1=R.MAIN, y=1240),
    ]


# hide subtitles where the same text is shown big by gfx
def _hide(R):
    m = R.m
    sch = next(s for s in R.shots() if s['kind'] == 'scheme')
    d = _shot(R, '4019.MOV')
    return [(R.HOOK_END, m('4004', 8.1)), (d['o0'], d['o1']), (m('4004', 64.3), m('4004', 70.6)),
            (m('4007', 3.7), m('4007', 6.75)), (m('4014', 1.5), m('4014', 7.2)), (sch['o0'], sch['o1']),
            (m('gap_meme', 0.0), m('gap_meme', 2.01))]


def sfx(R):
    m = R.m
    sch = next(s for s in R.shots() if s['kind'] == 'scheme')
    d = _shot(R, '4019.MOV')
    ev = [
        (0.0, 'riser_hook2', 0.023),                             # DP0-style intrigue bed: audible from the first frame, rises to the cut, ~-32 LUFS final
        (m('3994', 2.14), 'beep', 0.18),                         # classic quiet censor «пик» over the swear word
        (R.HOOK_END, 'click1', 0.045),                           # click after the pause, no riser
        (d['o0'] + 0.6, 'click4', 0.045),                        # ЗУБЬЯ СЛИЗАНЫ
        (m('4004', 64.3), 'click2', 0.04), (m('4004', 66.3), 'click3', 0.04),   # 10+ / 2016
        (m('4007', 5.4), 'click2', 0.05),                        # 200 000
        (m('4007', 20.85), 'click5', 0.045),                     # twist flash
        (m('gap_meme', 0.0), 'yakubovich2', 0.05),        # meme sound (original)
        (sch['o0'], 'scheme-glitch', 0.033),
        (m('4011', 14.4), 'scheme-static', 0.05),
        (m('4014', 5.0), 'click4', 0.045),                       # strike
        (m('4016', 10.0) + 0.3, 'click3', 0.045),                # address
    ]
    for j in range(len(END_Q)):
        ev.append((R.MAIN + 0.25 + j * 0.12, ['click1', 'click5', 'click4', 'click3'][j], 0.035))
    ev.append((R.MAIN + 1.05, 'click1', 0.03))
    return ev


def COUNTERS(R):
    return []          # no counter blips (client: sounded cheap)


if __name__ == '__main__':
    import sys
    R0 = lib.Reel(sys.modules[__name__])
    HIDE = _hide(R0)
    lib.main(sys.modules[__name__])
