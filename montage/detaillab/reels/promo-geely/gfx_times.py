# Моменты графики (как в gfx.py) и тихие звуки клиента под них
from tl import *
def pst(c, s0): return [o for pc, s, e, o in pieces if pc == c and abs(s - s0) < 0.05][0]
T_SKID = word('2709', 'скидка'); T_BAZ = pst('2722', 3.28)
ZONES_T = [word('2722', w) for w in ('передняя', 'капот', 'крылья', 'стойки', 'полоса', 'антиманикюры', 'канты', 'багажника')]
T_POROG = word('2724', 'порогов'); T_PRISP = word('2724', 'приспускаем')
CHAIN_T = [word('2724', w) for w in ('резинки', 'камушки', 'протирать')]
T_C0 = pst('2727', 0.44); T_PODR = word('2727', 'подробностями'); T_PROSP = word('2727', 'проспект')

SFX = [('hit4', 0.15, -24), ('hit5', word('2709', 'все') - 0.05, -22),
       ('hit2', T_SKID - 0.03, -12),                       # вспышка на «скидка»
       ('hit1', T_BAZ + 0.05, -24)]
SFX += [('hit4', t, -25) for t in ZONES_T]
SFX += [('hit1', T_POROG, -24), ('hit1', T_PRISP, -24)]
SFX += [('hit4', t, -23) for t in CHAIN_T[:2]] + [('hit3', CHAIN_T[2], -21)]
SFX += [('hit5', T_C0, -20), ('hit1', T_PODR, -24), ('hit1', T_PROSP, -25),
        ('hit5', VOICE_END + 0.1, -18), ('hit1', VOICE_END + 0.7, -24)]
