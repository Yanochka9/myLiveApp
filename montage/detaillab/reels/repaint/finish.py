# Звук (голос + музыка + щелчки) и субтитры, финальный экспорт out/final.mp4
import subprocess, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tl import *
import gfx_times as G

SRC = f"{R0}/src"
MUSIC_OFF = 1.0; MUSIC_DB = -24
GOLD = '&H37AFD4&'

# ================= ЗВУК =================
def build_audio():
    f = []; ins = []
    for i, (c, s, e, o) in enumerate(pieces):
        ins += ['-i', f"{SRC}/IMG_{c}.MOV"]
        d = (e - s) / SP
        f.append(f"[{i}:a]atrim={s:.4f}:{e:.4f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=mono,"
                 f"atempo={SP},afade=t=in:d=0.012,afade=t=out:st={d-0.02:.4f}:d=0.02,adelay={int(round(o*1000))}:all=1[v{i}]")
    n = len(pieces)
    f.append(''.join(f"[v{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,"
             f"highpass=f=80,arnndn=m={R0}/../assets/sh.rnnn:mix=1.0,agate=threshold=0.012:ratio=3:attack=3:release=120:range=0.25,lowpass=f=14000,"
             "acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2,"
             f"apad=whole_dur={TOTAL:.3f},atrim=0:{TOTAL:.3f},asplit=2[voice][key]")
    ins += ['-i', f"{R0}/music/client.wav"]
    # на меме музыка на секунду «проваливается» (комичная пауза), в финале — громче
    f.append(f"[{n}:a]atrim=start={MUSIC_OFF:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
             f"volume={MUSIC_DB}dB,"
             f"volume='if(gte(t,{VOICE_END:.3f}),2.4,1)':eval=frame,"
             f"afade=t=in:d=0.4,afade=t=out:st={TOTAL-1.2:.3f}:d=1.2,apad,atrim=0:{TOTAL:.3f}[mus]")
    f.append("[key]aformat=channel_layouts=stereo[keys];"
             "[mus][keys]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350:makeup=1[musd]")
    sfx = G.SFX
    PEAK = {'hit1': 0.21, 'hit2': 0.19, 'hit3': 0.225, 'hit4': 0.115, 'hit5': 0.215}
    k = n + 1; mix = ['[voice]', '[musd]']
    for j, (nm, t, g) in enumerate(sfx):
        ins += ['-i', f"{R0}/sfx/{nm}.wav"]
        t -= PEAK.get(nm, 0.0); trim = ''
        if t < 0: trim = f"atrim=start={-t:.3f},asetpts=PTS-STARTPTS,"; t = 0
        f.append(f"[{k}:a]{trim}volume={g}dB,adelay={int(t*1000)}:all=1,aformat=channel_layouts=stereo,aresample=48000[s{j}]")
        mix.append(f"[s{j}]"); k += 1
    f.append(''.join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,"
             f"atrim=0:{TOTAL:.3f},loudnorm=I=-14:TP=-1.0:LRA=9[aout]")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(f),
                    '-map', '[aout]', '-ar', '48000', '-ac', '2', f"{OUT}/audio.wav"], check=True)

# ================= СУБТИТРЫ =================
def ts(x):
    x = max(0, x); h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"

FIX = {'влепают': 'влипают', 'авторичном': 'вторичном', 'dtlab': 'DETAILLAB', 'пленки': 'плёнки',
       'приезжайте@39.24': 'приезжаете', 'нет': 'НЕТ', 'придет': 'придёт', 'несет': 'несёт', 'еще': 'ещё'}
GOLDW = {'покрашен', 'детейлингу', 'полиуретановые', 'плёнки', 'защитой', 'лаку', 'вторичном', 'окрасе',
         'лакокрасочное', 'негодность', 'ответственности', 'нет', 'стоимость', 'окрашенный', 'заводского',
         'ответственность', 'новый', 'заводской', 'скола', 'коррозия', 'перекрашивали', 'сразу', 'detaillab',
         'сильно', 'не'}
GOLD_ONCE = {'не': ('2510', 6.68, 'Не')}          # «Не ждите» — золотом только здесь
SHORT = {'в', 'у', 'на', 'и', 'по', 'за', 'мы', 'из', 'а', 'под', 'все', 'нам', 'нас', 'не', 'к', 'об', 'ли',
         'как', 'для', 'при', 'вы', 'он', 'это', 'что', 'со'}

def caption_events():
    ws = []; seen = set()
    for pc, s, e, o in pieces:
        for w in W[pc]:
            key = (pc, w[0], w[2])
            # whisper часто ставит начало слова раньше звука — берём слово, если оно заходит в кусок
            if not (w[0] < e - 0.05 and w[1] > s + 0.08) or key in seen: continue
            seen.add(key)
            t0 = omap(pc, max(w[0], s)); raw = w[2].strip('.,…?').lower()
            txt = FIX.get(f"{raw}@{w[0]}", FIX.get(raw, raw))
            if raw == '-то' and ws: ws[-1][1] += '-ТО'; continue
            gold = txt.lower() in GOLDW
            if raw in GOLD_ONCE: gold = GOLD_ONCE[raw] == key
            ws.append([t0, txt.upper(), gold, w[1]])
    groups = []; i = 0
    while i < len(ws):
        g = [ws[i]]
        while g[-1][1].lower() in SHORT and i + 1 < len(ws) and len(g) < 3:
            i += 1; g.append(ws[i])
        groups.append(g); i += 1
    ev = []
    for j, g in enumerate(groups):
        st = g[0][0]
        nxt = groups[j + 1][0][0] if j + 1 < len(groups) else VOICE_END
        en = min(nxt, st + 1.3, VOICE_END)
        if st < MEME_AT <= en: en = MEME_AT
        txt = ' '.join((f"{{\\c{GOLD}}}{w[1]}{{\\c&HFFFFFF&}}" if w[2] else w[1]) for w in g)
        ev.append((st, en, txt))
    return ev

def build_ass():
    L = []
    for st, en, txt in caption_events():
        import re
        plain = re.sub(r'{[^}]*}', '', txt)
        k = min(100, int(100 * 700 / max(1, len(plain) * 0.66 * 80)))      # не шире 700 px (безопасная зона)
        L.append(f"Dialogue: 5,{ts(st)},{ts(en)},Cap,,0,0,0,,{{\\pos(540,1000)\\fad(40,0)\\fscx{int(k*0.86)}\\fscy{int(k*0.86)}\\t(0,110,\\fscx{k}\\fscy{k})}}{txt}")
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat ExtraBold,80,&H00FFFFFF,&H00FFFFFF,&H00141414,&H8C000000,0,0,0,0,100,100,1,0,1,3,6,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    open(f"{OUT}/subs.ass", 'w').write(head + '\n'.join(L) + '\n')

def final():
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f"{OUT}/video_gfx.mp4", '-i', f"{OUT}/audio.wav",
                    '-vf', f"subtitles={OUT}/subs.ass:fontsdir={R0}/../assets/fonts,format=yuv420p",
                    '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
                    '-maxrate', '10M', '-bufsize', '20M', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest',
                    f"{OUT}/final.mp4"], check=True)

if __name__ == '__main__':
    build_audio(); build_ass()
    if '--no-video' not in sys.argv: final()
    print('done')
