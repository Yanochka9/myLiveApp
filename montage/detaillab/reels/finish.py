import json, subprocess, os
S = os.path.dirname(os.path.abspath(__file__))
SRC = f"{S}/src"; OUT = f"{S}/out"
TL = json.load(open(f"{OUT}/timeline.json"))
pieces = TL['pieces']; VOICE_END = TL['voice_end']; TOTAL = TL['total']
W = json.load(open(f"{S}/words_medium.json"))

def omap(c, ts):
    for pc, s, e, o in pieces:
        if pc == c and ts < e:
            return o + max(0.0, ts - s)
    return None

def inside(c, ts):
    return any(pc == c and s - 0.05 <= ts < e for pc, s, e, o in pieces)

def word(c, txt, k=1):
    n = 0
    for w in W[c]:
        if w[2].lower().strip('.,…') == txt.lower():
            n += 1
            if n == k:
                return omap(c, w[0])
    raise KeyError((c, txt, k))

# ================= AUDIO =================
def build_audio():
    f = []; ins = []
    for i, (c, s, e, o) in enumerate(pieces):
        ins += ['-i', f"{SRC}/IMG_{c}.MOV"]
        d = e - s
        f.append(f"[{i}:a]atrim={s:.4f}:{e:.4f},asetpts=PTS-STARTPTS,aresample=48000,"
                 f"aformat=channel_layouts=mono,afade=t=in:d=0.012,afade=t=out:st={d-0.02:.4f}:d=0.02[v{i}]")
    n = len(pieces)
    # place every piece at its own offset (there is a silent beat after the hook)
    for i, (c, s, e, o) in enumerate(pieces):
        f[i] = f[i].replace(f"[v{i}]", f",adelay={int(round(o*1000))}:all=1[v{i}]")
    f.append(''.join(f"[v{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,"
             "highpass=f=80,lowpass=f=14000,"
             "acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2,"
             f"apad=whole_dur={TOTAL:.3f},atrim=0:{TOTAL:.3f},asplit=2[voice][key]")
    flash = TL['tail_at'] + TL['tail']
    # music: only a track the client provided (music/client.*); none otherwise
    import glob
    mf = sorted(glob.glob(f"{S}/music/client.*"))
    if mf:
        ins += ['-i', mf[0]]
        f.append(f"[{n}:a]atrim=start={MUSIC_OFF:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
                 f"volume={MUSIC_DB}dB,afade=t=in:d=0.4,afade=t=out:st={TOTAL-1.2:.3f}:d=1.2,apad,atrim=0:{TOTAL:.3f}[mus]")
        f.append("[key]aformat=channel_layouts=stereo[keys];"
                 "[mus][keys]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350:makeup=1[musd]")
    else:
        f.append("[key]anullsink")
    items = ['передней', 'оптики', 'стоек', 'зеркал', 'кантика', 'внутренних', 'погрузочные', 'канты']
    # sfx (file, time, gain_db): only sounds from the client's transition pack, kept low
    sfx = [('riser_hook', 0.0, -31),                  # quiet build from the first frame to the clack
           ('hit2', flash - 0.03, -5),                      # clack on the flash
           ('hit5', word('1380', 'комплекса') + 0.1, -22),
           ('hit1', word('1381', 'помимо') + 0.1, -22)]
    sfx += [('hit4', word('1381', w), -26) for w in items]
    sfx += [('hit3', word('1384', 'три'), -20)]
    sfx += [('hit1', word('1384', w), -24) for w in ('демонтаж', 'оклейка', 'обратный')]
    sfx += [('hit5', VOICE_END + 0.1, -18)]
    PEAK = {'hit1': 0.21, 'hit2': 0.19, 'hit3': 0.225, 'hit4': 0.115, 'hit5': 0.215}
    k = n + (1 if mf else 0)
    mix = ['[voice]'] + (['[musd]'] if mf else [])
    for j, (nm, t, g) in enumerate(sfx):
        ins += ['-i', f"{S}/sfx/{nm}.wav"]
        trim = ''
        if t < 0:
            trim = f"atrim=start={-t:.3f},asetpts=PTS-STARTPTS,"; t = 0
        extra = ''
        if nm in ('riser', 'riser_end', 'riser_hook'):
            extra = f"afade=t=out:st={flash - t - 0.02:.3f}:d=0.06,"
        t -= PEAK.get(nm, 0.0)
        if t < 0 and not trim:
            trim = f"atrim=start={-t:.3f},asetpts=PTS-STARTPTS,"; t = 0
        f.append(f"[{k}:a]{trim}{extra}volume={g}dB,adelay={int(t*1000)}:all=1,"
                 f"aformat=channel_layouts=stereo,aresample=48000[s{j}]")
        mix.append(f"[s{j}]"); k += 1
    f.append(''.join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,"
             f"atrim=0:{TOTAL:.3f},loudnorm=I=-14:TP=-1.0:LRA=9[aout]")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(f),
                    '-map', '[aout]', '-ar', '48000', '-ac', '2', f"{OUT}/audio.wav"], check=True)

# ================= SUBTITLES / GRAPHICS =================
FLASH = TL['tail_at'] + TL['tail']
MUSIC_OFF = 0.0; MUSIC_DB = -25
GOLD = '&H37AFD4&'; GOLD2 = '&H5CC8E8&'
def ts(x):
    x = max(0, x); h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"

FIX = {'сходят': 'входят', 'работы': 'работ', 'леопард': 'LEOPARD', 'direct': 'DIRECT',
       'погрузочные': 'погрузочной', 'зоны': 'зоны', 'пленочку': 'плёночку',
       'поочередно': 'поочерёдно', 'кантика': 'кантиков', 'максимальный': 'МАКСИМАЛЬНЫЙ',
       'максимально': 'МАКСИМАЛЬНЫЙ'}
GOLDW = {'весь', 'частям', 'leopard', 'максимальный', 'полностью', 'каждый', 'элемент',
         'оптики', 'три', 'рабочих', 'дня', 'direct', 'стоек', 'зеркал', 'порогов', 'дверей'}
SHORT = {'в', 'у', 'на', 'и', 'по', 'за', 'мы', 'из', 'а', 'под', 'все', 'нам', 'нас'}

def caption_events():
    ws = []
    for c in ['1377', '1380', '1381', '1384', '1387']:
        for i, w in enumerate(W[c]):
            if not inside(c, w[0]):
                continue
            t0 = omap(c, w[0])
            raw = w[2].strip('.,…').lower()
            if c == '1380' and raw == 'комплекса':
                raw = 'комплекс'
            if raw in ('-за',):
                ws[-1][1] += '-ЗА'; continue
            txt = FIX.get(raw, raw).upper()
            ws.append([t0, txt, raw in GOLDW or txt.lower() in GOLDW])
    # group short words with the next one
    groups = []; i = 0
    while i < len(ws):
        g = [ws[i]]
        while g[-1][1].lower() in SHORT and i + 1 < len(ws) and len(g) < 3:
            i += 1; g.append(ws[i])
        groups.append(g); i += 1
    ev = []
    for j, g in enumerate(groups):
        st = g[0][0]
        en = groups[j + 1][0][0] if j + 1 < len(groups) else VOICE_END
        en = min(en, st + 1.4)
        if st < FLASH <= en:
            en = FLASH - 0.05
        txt = ' '.join((f"{{\\c{GOLD}}}{w[1]}{{\\c&HFFFFFF&}}" if w[2] else w[1]) for w in g)
        ev.append((st, en, txt))
    return ev

def box(x1, y1, x2, y2, r=26):
    # rounded rectangle path
    return (f"m {x1+r} {y1} l {x2-r} {y1} b {x2} {y1} {x2} {y1} {x2} {y1+r} l {x2} {y2-r} "
            f"b {x2} {y2} {x2} {y2} {x2-r} {y2} l {x1+r} {y2} b {x1} {y2} {x1} {y2} {x1} {y2-r} "
            f"l {x1} {y1+r} b {x1} {y1} {x1} {y1} {x1+r} {y1}")

def circle(cx, cy, r):
    k = 0.5523 * r
    return (f"m {cx} {cy-r} b {cx+k} {cy-r} {cx+r} {cy-k} {cx+r} {cy} b {cx+r} {cy+k} {cx+k} {cy+r} {cx} {cy+r} "
            f"b {cx-k} {cy+r} {cx-r} {cy+k} {cx-r} {cy} b {cx-r} {cy-k} {cx-k} {cy-r} {cx} {cy-r}")

def check(x, y, s=1.0):
    return f"m {x} {y+14*s} l {x+10*s} {y+26*s} l {x+30*s} {y} l {x+34*s} {y+4*s} l {x+10*s} {y+34*s} l {x-4*s} {y+18*s}"

def build_ass():
    L = []
    def D(layer, a, b, style, text):
        L.append(f"Dialogue: {layer},{ts(a)},{ts(b)},{style},,0,0,0,,{text}")
    shape = lambda d: f"{{\\p1}}{d}{{\\p0}}"

    t_list0 = word('1381', 'помимо'); t_list1 = omap('1381', 15.0) + 0.6
    capY_low = (t_list0, t_list1)
    for st, en, txt in caption_events():
        low = capY_low[0] <= st < capY_low[1]
        y = 990 if low else 1050
        D(5, st, en, 'Cap', f"{{\\pos(540,{y})\\fad(40,0)\\fscx88\\fscy88\\t(0,110,\\fscx100\\fscy100)}}{txt}")

    # --- badge: КОМПЛЕКС МАКСИМАЛЬНЫЙ
    a = word('1380', 'комплекса') + 0.1; b = word('1380', 'передний') - 0.05
    an = "\\fad(180,200)\\fscx92\\fscy92\\t(0,220,\\fscx100\\fscy100)"
    D(1, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c&H101010&\\1a&H50&\\3c{GOLD}\\bord4\\shad0{an}\\org(540,1255)}}" + shape(box(150, 1140, 930, 1370)))
    D(2, a, b, 'Small', f"{{\\pos(540,1202){an}\\org(540,1255)}}КОМПЛЕКС")
    D(2, a, b, 'Big', f"{{\\pos(540,1295)\\c{GOLD}{an}\\org(540,1255)}}МАКСИМАЛЬНЫЙ")

    # --- checklist
    items = [('ПЕРЕДНЯЯ ЧАСТЬ', word('1381', 'передней')), ('ОПТИКА', word('1381', 'оптики')),
             ('СТОЙКИ', word('1381', 'стоек')), ('ЗЕРКАЛА', word('1381', 'зеркал')),
             ('КАНТЫ ДВЕРЕЙ', word('1381', 'кантика')), ('ВНУТРЕННИЕ ПОРОГИ', word('1381', 'внутренних')),
             ('ЗОНА ПОГРУЗКИ', word('1381', 'погрузочные')), ('КАНТЫ БАГАЖНИКА', word('1381', 'канты'))]
    a = t_list0 + 0.1; b = t_list1
    top = 1080; row = 66
    D(1, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c&H0E0E0E&\\1a&H48&\\3c{GOLD}\\bord3\\shad0\\fad(250,250)}}" + shape(box(80, top, 1000, top + 82 + row * 4)))
    D(2, a, b, 'Small', f"{{\\pos(540,{top+44})\\c{GOLD}\\fad(250,250)}}ЧТО ВХОДИТ В КОМПЛЕКС")
    for k, (name, t0) in enumerate(items):
        col, r = k // 4, k % 4
        x = 135 + col * 455; y = top + 82 + row * r + row / 2 - 4
        D(2, t0, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c{GOLD}\\bord0\\shad0\\fad(150,250)}}" + shape(circle(x, y, 21)))
        D(3, t0, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c&H101010&\\bord0\\shad0\\fad(150,250)}}" + shape(check(x - 14, y - 13, 0.78)))
        D(2, t0, b, 'Item', f"{{\\an4\\pos({x+38},{y})\\fad(150,250)}}{name}")

    # --- 3 рабочих дня
    a = word('1384', 'три') - 0.05; b = word('1384', 'который') - 0.02
    D(1, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c&H0E0E0E&\\1a&H48&\\3c{GOLD}\\bord3\\shad0\\fad(150,0)}}" + shape(box(120, 1140, 960, 1420)))
    D(2, a, b, 'Huge', f"{{\\an6\\pos(450,1288)\\c{GOLD}\\fad(120,0)\\fscx70\\fscy70\\t(0,200,\\fscx100\\fscy100)}}3")
    D(2, a, b, 'Days', f"{{\\an4\\pos(490,1280)\\fad(200,0)}}РАБОЧИХ\\NДНЯ")

    # --- timeline демонтаж → оклейка → монтаж
    a = word('1384', 'который'); b = omap('1384', 10.0) + 0.3
    steps = [('ДЕМОНТАЖ', word('1384', 'демонтаж')), ('ОКЛЕЙКА', word('1384', 'оклейка')),
             ('МОНТАЖ', word('1384', 'обратный'))]
    xs = [250, 540, 830]; y = 1245
    D(1, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c&H0E0E0E&\\1a&H48&\\3c{GOLD}\\bord3\\shad0\\fad(0,200)}}" + shape(box(120, 1140, 960, 1420)))
    D(2, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c&H808080&\\1a&H60&\\bord0\\shad0\\fad(200,200)}}" + shape(f"m 250 {y-3} l 830 {y-3} l 830 {y+3} l 250 {y+3}"))
    for k, (name, t0) in enumerate(steps):
        x = xs[k]
        if k:
            # gold line fill from previous node
            D(3, t0, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c{GOLD}\\bord0\\shad0\\clip(0,0,{xs[k-1]},1920)\\t(0,350,\\clip(0,0,{x},1920))\\fad(0,200)}}" + shape(f"m {xs[k-1]} {y-4} l {x} {y-4} l {x} {y+4} l {xs[k-1]} {y+4}"))
        D(3, a, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c&H1A1A1A&\\3c&H808080&\\bord3\\shad0\\fad(200,200)}}" + shape(circle(x, y, 40)))
        D(4, t0, b, 'Shape', f"{{\\an7\\pos(0,0)\\1c{GOLD}\\3c{GOLD2}\\bord3\\shad0\\fad(120,200)}}" + shape(circle(x, y, 40)))
        D(5, a, t0, 'Num', f"{{\\pos({x},{y+2})\\c&HB0B0B0&\\fad(200,0)}}{k+1}")
        D(5, t0, b, 'Num', f"{{\\pos({x},{y+2})\\c&H101010&\\fad(0,200)}}{k+1}")
        D(4, a, t0, 'Step', f"{{\\pos({x},{y+95})\\c&HB0B0B0&\\fad(200,0)}}{name}")
        D(4, t0, b, 'Step', f"{{\\pos({x},{y+95})\\c{GOLD}\\fad(0,200)}}{name}")

    # --- end card
    a = VOICE_END; b = TOTAL
    # (dark end-card backdrop is drawn in final() underneath the logo)
    D(3, a + 0.15, b, 'Shape', f"{{\\an7\\pos(0,0)\\1a&HFF&\\3c{GOLD}\\bord5\\shad0\\fad(400,0)}}" + shape(circle(540, 700, 268)))
    D(4, a + 0.45, b, 'Cta', f"{{\\pos(540,1110)\\c{GOLD}\\fad(250,0)\\fscx90\\fscy90\\t(0,200,\\fscx100\\fscy100)}}ПИШИТЕ В DIRECT")
    D(4, a + 0.65, b, 'Small', f"{{\\pos(540,1200)\\fad(250,0)}}РАССЧИТАЕМ СТОИМОСТЬ")
    pin = "m 0 -28 b 16 -28 26 -16 26 -2 b 26 14 0 40 0 40 b 0 40 -26 14 -26 -2 b -26 -16 -16 -28 0 -28 m 0 -12 b -7 -12 -11 -7 -11 -2 b -11 5 -7 9 0 9 b 7 9 11 5 11 -2 b 11 -7 7 -12 0 -12"
    D(4, a + 0.85, b, 'Shape', f"{{\\an7\\pos(205,1330)\\1c{GOLD}\\bord0\\shad0\\fad(250,0)}}" + shape(pin))
    D(4, a + 0.85, b, 'Addr', f"{{\\an4\\pos(250,1335)\\fad(250,0)}}ПР-Т ДЗЕРЖИНСКОГО, 82А")
    D(4, a + 0.95, b, 'Tiny', f"{{\\pos(540,1405)\\fad(250,0)}}МИНСК · 9:00–21:00 · БЕЗ ВЫХОДНЫХ")

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat ExtraBold,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,1,0,1,0,6,5,70,70,0,1
Style: Shape,Arial,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Small,Montserrat ExtraBold,50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,4,0,1,0,3,5,0,0,0,1
Style: Big,Oswald,120,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,3,0,1,0,4,5,0,0,0,1
Style: Item,Montserrat ExtraBold,36,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,0,2,4,0,0,0,1
Style: Huge,Oswald,300,&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,0,0,0,0,100,100,0,0,1,0,6,5,0,0,0,1
Style: Days,Montserrat ExtraBold,76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,3,4,0,0,0,1
Style: Num,Oswald,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Step,Montserrat ExtraBold,44,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,0,2,5,0,0,0,1
Style: Cta,Oswald,130,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,4,5,0,0,0,1
Style: Addr,Montserrat ExtraBold,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,0,3,4,0,0,0,1
Style: Tiny,Montserrat ExtraBold,38,&H00C8C8C8,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,3,0,1,0,2,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    open(f"{OUT}/subs.ass", 'w').write(head + '\n'.join(L) + '\n')

def final():
    a = VOICE_END
    # logo with fade-in and a soft glint sweep
    logo = (f"[1:v]scale=500:500,format=rgba,eq=brightness=0.07:contrast=1.18:saturation=1.25:gamma=1.08,"
            f"geq=r='min(255,r(X,Y)+150*exp(-pow((X+0.6*Y-(T-{a+0.9:.3f})*1100)/45,2)))':"
            f"g='min(255,g(X,Y)+140*exp(-pow((X+0.6*Y-(T-{a+0.9:.3f})*1100)/45,2)))':"
            f"b='min(255,b(X,Y)+110*exp(-pow((X+0.6*Y-(T-{a+0.9:.3f})*1100)/45,2)))':a='alpha(X,Y)',"
            f"fade=t=in:st={a+0.1:.3f}:d=0.45:alpha=1[lg]")
    fc = (f"{logo};[0:v]drawbox=x=0:y=0:w=iw:h=ih:color=black@0.45:t=fill:enable='gte(t,{a:.3f})'[bg];"
          f"[bg][lg]overlay=290:450:enable='gte(t,{a+0.1:.3f})'[v1];"
          f"[v1]subtitles={OUT}/subs.ass:fontsdir={S}/../assets/fonts,format=yuv420p[v]")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f"{OUT}/video_raw.mp4",
                    '-loop', '1', '-framerate', '30', '-t', f"{TOTAL:.3f}", '-i', f"{S}/brand/logo.png",
                    '-i', f"{OUT}/audio.wav", '-filter_complex', fc, '-map', '[v]', '-map', '2:a',
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest',
                    f"{OUT}/final.mp4"], check=True)

if __name__ == '__main__':
    build_audio(); build_ass(); final()
    print('done')
