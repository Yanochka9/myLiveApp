# Моменты графики (те же, что в gfx.py) и звуки под них
from tl import *
T_CAKE = word('2509', 'полиуретановые'); T_STRONG = word('2509', 'сильно'); T_SECOND = word('2509', 'авторичном')
T_PEEL = word('2509', 'подорвать', after=26.0); T_NEGOD = word('2509', 'негодность'); T_Q = word('2509', 'несет')
T_WHERE = word('2509', 'где'); T_PRICE = word('2509', 'стоимость'); T_HOW = word('2509', 'как', after=37.0)
T_RANEE = word('2509', 'ранее'); T_DET3 = word('2509', 'детейлинг', 3); T_OTHER = word('2509', 'другие')
T_NEW = word('2510', 'новый'); T_NE = word('2510', 'не'); T_SKOL = word('2510', 'скола'); T_KOR = word('2510', 'коррозия')
T_PEREK = word('2510', 'перекрашивали'); T_KLE = word('2510', 'клеиться'); T_LUCH = word('2510', 'лучше')

# (файл из sfx/, время, дБ) — только звуки клиента, тихо
SFX = [('hit4', T_CAKE + 0.3 + i * 0.3 + 0.25, -27) for i in range(5)]
SFX += [('hit1', T_STRONG, -24), ('hit5', T_SECOND, -22), ('hit3', T_PEEL + 0.2, -19),
        ('hit2', T_NEGOD - 0.1, -17), ('hit1', T_Q, -24),
        ('hit2', MEME_AT, -9), ('hit3', MEME_AT + 0.5, -14),
        ('hit4', T_WHERE, -25), ('hit4', T_PRICE, -25), ('hit4', T_HOW, -25),
        ('hit1', T_RANEE, -24), ('hit1', T_DET3 + 0.1, -24), ('hit4', T_OTHER + 0.1, -25),
        ('hit5', T_NEW + 0.1, -22), ('hit1', T_NE, -25),
        ('hit4', T_SKOL, -23), ('hit4', T_KOR, -23), ('hit4', T_PEREK, -23), ('hit3', T_KLE, -21),
        ('hit5', T_LUCH, -21), ('hit5', VOICE_END + 0.1, -18), ('hit1', VOICE_END + 0.7, -24)]
