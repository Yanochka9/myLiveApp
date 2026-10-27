"""Word-by-word subtitles (ASS) in output time. '*' marks red accent words, '-' hides a token."""
from edl import m, HOOK_END, MAIN_DUR, segs, SP

TOKENS = """
0.00 ЕСЛИ БЫ
0.28 МАСЛО
0.56 БЫЛО
0.70 ЗАМЕНЕНО
1.06 *ПРАВИЛЬНО
1.56 ВАРИАТОР
1.88 БЫ ЕЩЁ
2.26 *30 ТЫСЯЧ
2.98 ПРОШЁЛ
3.42 *100%
5.30 ДРУЗЬЯ,
5.66 УЧИТЕСЬ
6.16 *НА ЧУЖИХ
6.54 *ОШИБКАХ
6.96 А НЕ НА
7.20 СВОИХ
7.58 А В ДАННОМ
8.02 СЛУЧАЕ
8.30 НА ОШИБКАХ
8.92 НАШЕГО
9.12 КЛИЕНТА
9.72 КОТОРЫЙ
10.14 ХОТЕЛ
10.42 СДЕЛАТЬ
10.94 ДЛЯ СВОЕЙ
11.22 МАШИНЫ
11.54 КАК ЛУЧШЕ
11.96 И ПОМЕНЯТЬ
12.82 МАСЛО
13.20 В СВОЁМ
13.46 ВАРИАТОРЕ
13.98 НО СДЕЛАЛ
14.48 ЭТО
14.72 *САМОСТОЯТЕЛЬНО
15.38 У СЕБЯ
15.56 В ГАРАЖЕ
16.12 И В
16.48 РЕЗУЛЬТАТЕ
16.94 НЕДОСТАТКА
17.40 ИНФОРМАЦИИ
18.10 ЗАЛИЛ
18.94 *НЕ ТО
19.32 *МАСЛО
19.84 А ТАКЖЕ
20.56 *НЕПРАВИЛЬНО
20.98 ВЫСТАВИЛ
21.36 УРОВЕНЬ
21.76 МАСЛА
22.12 В РЕЗУЛЬТАТЕ
22.74 ЧЕГО
22.92 КОРОБКА
23.48 ПРОСТО
23.68 *СГОРЕЛА
24.46 В РЕЗУЛЬТАТЕ
24.90 ЧЕГО
25.08 ПРИШЛОСЬ
25.64 МЕНЯТЬ
26.18 *ГИДРОБЛОК
26.82 *НАСОС
28.00 НО
28.14 НАИБОЛЬШИЙ
28.70 УЩЕРБ
28.88 ПОЛУЧИЛИ
29.40 *ВАЛЫ
29.86 *И ЦЕПЬ
30.60 ЭТО ВИДНО
30.98 ПО ХАРАКТЕРНЫМ
32.12 *ЧЁРНЫМ
32.52 *ПОЛОСАМ
32.98 НА РАБОЧЕЙ
33.96 ЧАСТИ
34.20 ВАЛА
34.90 ЭТО
35.04 *ЗАДИРЫ
35.78 ОНИ
36.16 ПРОИЗОШЛИ
36.66 В РЕЗУЛЬТАТЕ
37.24 *ПРОБУКСОВКИ
38.06 ЦЕПИ
38.46 ПО ВАЛУ
39.32 ИЗ-ЗА
39.46 *НЕХВАТКИ
39.78 *ДАВЛЕНИЯ
40.80 ТО ЖЕ САМОЕ
41.22 МЫ МОЖЕМ
41.58 НАБЛЮДАТЬ
42.10 НА ВСЕЙ
42.66 РАБОЧЕЙ
43.04 ПОВЕРХНОСТИ
43.38 *ЦЕПИ
44.90 ДАННЫЕ
45.08 ДЕТАЛИ
45.36 НАМ ПРИШЛОСЬ
45.74 ЗАМЕНИТЬ
46.20 ЧТО
46.46 ОБОШЛОСЬ
46.88 КЛИЕНТУ
47.28 -В 20 РАЗ
47.96 -ДОРОЖЕ
48.50 ЧЕМ ЕСЛИ БЫ
49.16 ОН ПРОСТО
49.46 ЗАМЕНИЛ
49.86 МАСЛО
50.16 У НАС
51.00 ПОЭТОМУ
51.20 МЕНЯЙТЕ
51.66 МАСЛО
52.02 НЕ ТОЛЬКО
52.34 *СВОЕВРЕМЕННО
53.55 НО И
53.78 *В ПРАВИЛЬНОМ
54.32 *МЕСТЕ
54.72 НАПРИМЕР
55.32 НА ДЗЕРЖИНСКОГО
55.84 82А
56.68 *В АКПП ДРАЙВ
"""

def ts(t):
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"

def build():
    toks = []
    for line in TOKENS.strip().splitlines():
        t, w = line.split(' ', 1)
        toks.append((m(float(t)), w))
    ev = []
    for i, (t0, w) in enumerate(toks):
        nxt = toks[i + 1][0] if i + 1 < len(toks) else MAIN_DUR
        if t0 < HOOK_END <= nxt:
            nxt = HOOK_END  # hook words stop at the flash
        t1 = min(nxt, t0 + 1.4)
        if w.startswith('-') or t1 <= t0:
            continue
        red = w.startswith('*')
        w = w.lstrip('*')
        size = 96 if len(w) <= 10 else int(96 * 10 / len(w))
        if red:
            size = int(size * 1.12)
        style = 'R' if red else 'W'
        anim = r"{\fscx78\fscy78\t(0,90,\fscx106\fscy106)\t(90,170,\fscx100\fscy100)}"
        ev.append(f"Dialogue: 0,{ts(t0)},{ts(t1)},{style},,0,0,0,,{{\\pos(540,1190)\\fs{size}}}{anim}{w}")
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: W,Unbounded Black,78,&H00FFFFFF,&H00FFFFFF,&H50000000,&H78000000,1,0,0,0,100,100,1,0,1,5,4,5,40,40,0,1
Style: R,Unbounded Black,78,&H002F29F0,&H002F29F0,&H50000000,&H78000000,1,0,0,0,100,100,1,0,1,5,4,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    open(SP + '/build/subs.ass', 'w').write(head + '\n'.join(ev) + '\n')
    return toks

if __name__ == '__main__':
    toks = build()
    print(len(toks), 'tokens; last', toks[-1])
