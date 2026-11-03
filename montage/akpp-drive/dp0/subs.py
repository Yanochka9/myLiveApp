"""Word-by-word subtitles (ASS) in output time. '*' marks red accent words, '-' hides a token."""
from edl import m, HOOK_END, MAIN_DUR, segs, SP

TOKENS = """
9.93 ПРОЕХАВ
10.12 -ТЫСЯЧУ
10.44 -КИЛОМЕТРОВ
10.86 КОРОБКА
11.26 НАЧАЛА
11.42 УХОДИТЬ
11.82 *В АВАРИЮ
12.18 НА МАЛОЙ
12.48 СКОРОСТИ
12.94 -10–20 КМ/Ч
4.04 -DP0,
4.52 -AL4
5.45 СДЕЛАЛИ
5.68 *КАПИТАЛКУ
6.14 ПОСЛЕ
6.32 ОБКАТКИ
6.80 ПОМЕНЯЛИ
7.10 МАСЛО
7.91 *ТЕПЛООБМЕННИК
8.32 ВЫРЕЗАЛИ
9.03 ПОСТАВИЛИ
9.38 *РАДИАТОР
19.12 ЧТО ЗА
19.26 ПРОБЛЕМА
19.66 МОЖЕТ
19.82 БЫТЬ?
34.20 ПРОБЛЕМА
34.48 ДАННОЙ
34.78 КОРОБКИ
35.10 ПРИ УХОДЕ
35.68 *В АВАРИЮ
35.98 БЕЗ
36.20 ПРОБУКСОВОК
36.80 И ПИНКОВ
37.85 ЧАЩЕ
37.96 ВСЕГО
38.14 ЯВЛЯЕТСЯ
38.46 -УТЕЧКА
39.16 -ДАВЛЕНИЯ
39.52 КОТОРУЮ
39.70 ФИКСИРУЕТ
40.22 БЛОК
40.38 УПРАВЛЕНИЯ
42.48 *УТЕЧКА
42.70 *ДАВЛЕНИЯ
43.00 МОЖЕТ
43.48 БЫТЬ
43.72 ПО МНОЖЕСТВУ
44.56 ПРИЧИН
45.58 УЧИТЫВАЯ
46.60 ЧТО
46.74 ДЕЛАЛИ
47.14 *КАПИТАЛКУ
48.95 МОГЛИ
49.06 БАНАЛЬНО
49.92 *ЗАКУСИТЬ
50.38 ГДЕ-ТО
50.64 ТЕФЛОНОВОЕ
51.12 *КОЛЬЦО
51.46 ЛИБО
51.74 *УПЛОТНЕНИЕ
53.05 МОГЛИ
53.12 *НЕПРАВИЛЬНО
53.62 УСТАНОВИТЬ
54.04 РАДИАТОР
54.76 ВЫНОСНОЙ
67.15 ТАКЖЕ
67.24 ПРОСТО
67.54 МОГ
67.70 *ЗАБИТЬСЯ
68.50 ГИДРОБЛОК
69.61 НЕДОМЫТЫМИ
70.18 -ПРОДУКТАМИ
70.84 -ИЗНОСА
71.97 ПОЭТОМУ
72.93 СНАЧАЛА
73.00 КОРОБКА
73.44 ЕХАЛА
73.66 НОРМАЛЬНО
74.10 А ПОТОМ
74.54 СТАЛА
75.28 *ПАДАТЬ
75.58 *В АВАРИЮ
128.15 В ЛЮБОМ
128.32 СЛУЧАЕ
128.60 ДЛЯ
128.96 ВЫЯСНЕНИЯ
129.38 ТОЧНОЙ
129.72 ПРИЧИНЫ
130.12 ПОТРЕБУЕТСЯ
130.84 *ДИАГНОСТИКА
132.00 У НАС
132.16 ОНА
132.36 -БЕСПЛАТНАЯ
133.18 ТАК ЧТО
133.44 ПРИЕЗЖАЙТЕ
133.82 К НАМ
134.12 *В АКПП ДРАЙВ
135.36 ПРОСПЕКТ
135.56 ДЗЕРЖИНСКОГО
135.96 82А
136.70 ПОДЗЕМНЫЙ
137.10 АВТОКОМПЛЕКС
"""

def ts(t):
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"

def build():
    toks = []
    for line in TOKENS.strip().splitlines():
        t, w = line.split(' ', 1)
        toks.append((m(float(t)), w))
    toks.sort(key=lambda x: x[0])
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
