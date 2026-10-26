"""Audio mix: cut voice, SFX on transitions, hook drone, workshop ambience, music bed."""
import json, subprocess, sys
from edl import segs, outs, m, HOOK_END, MAIN_DUR, TOTAL, SP, build_shots
from gfx_t import T

SRC = SP + '/src'; SFX = SP + '/assets/sfx'; MUS = SP + '/assets/music/267.mp3'
PEAK = {'1143': .55, '1430': .14, '1457': .38, '1474': 1.17, '1486': .62, '1489': .72, '1490': .72,
        '1492': 1.08, '166': .30, '2299': .09, '2568': 0, '2595': .04, '3005': .03, '790': 2.49}
with_music = '--no-music' not in sys.argv
out = SP + ('/build/mix.wav' if with_music else '/build/mix_nomusic.wav')

inputs, chains, labels = [], [], []
def inp(path, *pre):
    inputs.extend([*pre, '-i', path]); return len(inputs_idx) if False else None

idx = 0
def add_input(path, pre=()):
    global idx
    inputs.extend([*pre, '-i', path]); idx += 1; return idx - 1

# --- voice ---
v = add_input(f'{SRC}/D5CB.mov')
parts = []
for i, (a, b) in enumerate(segs):
    chains.append(f"[{v}:a:0]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,"
                  f"afade=t=out:st={b - a - 0.012:.4f}:d=0.012[s{i}]")
    parts.append(f"[s{i}]")
chains.append(f"{''.join(parts)}concat=n={len(segs)}:v=0:a=1,highpass=f=80,afftdn=nf=-32,"
              f"acompressor=threshold=-22dB:ratio=3:attack=5:release=90:makeup=2,"
              f"apad=whole_dur={TOTAL:.3f}[voice]")
labels.append('[voice]')

# --- sfx events: user's transition pack (B2B2.mov), quiet, only on key moments ---
B2 = SP + '/assets/b2'
PEAK.update({'riser': 4.0, 'click1': .11, 'click2': .13, 'click3': .10, 'click4': .16, 'click5': .13})
ev = []  # (time_of_peak, id, vol)
shots = build_shots()
ev.append((HOOK_END, 'riser', 0.034))                       # hook -> main
ev.append((T['header'][0] + 0.05, 'click1', 0.04))
ev.append((T['flashes'][1], 'click2', 0.05))                # "сгорела"
ev.append((T['ellipse'][2] + 0.12, 'click4', 0.04))         # ЗАДИРЫ
ev.append((T['scheme'][0], '2595', 0.033))                   # variator scheme
ev.append((T['scheme'][2], '1457', 0.05))
ev.append((T['chain'][2], 'click5', 0.04))                  # ИЗНОС ЦЕПИ
ev.append((T['counter'][1], 'click2', 0.05))                # ×20
ev.append((T['address'][0] + 0.3, 'click3', 0.045))
for j in range(4):                                          # end plate lines
    ev.append((MAIN_DUR + 0.25 + j * 0.12, ['click1', 'click5', 'click4', 'click3'][j], 0.035))
ev.append((MAIN_DUR + 1.05, 'click1', 0.03))
for n, (t, sid, vol) in enumerate(ev):
    path = f'{B2}/{sid}.wav' if sid in ('riser',) or sid.startswith('click') else f'{SFX}/{sid}.mp3'
    i = add_input(path)
    d = max(0, t - PEAK[sid])
    chains.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol},"
                  f"adelay={int(d * 1000)}:all=1[e{n}]")
    labels.append(f'[e{n}]')

# --- hook drone ---
i = add_input(f'{SFX}/2749.mp3', ('-ss', '20'))
chains.append(f"[{i}:a]atrim=0:{HOOK_END + 0.4:.3f},aresample=48000,aformat=channel_layouts=stereo,"
              f"volume=0.05,afade=t=in:d=1.0,afade=t=out:st={HOOK_END - 0.1:.3f}:d=0.5[drone]")
labels.append('[drone]')

# --- workshop ambience under the bench shots ---
for n, s in enumerate(x for x in shots if x['src'] and '8842' in x['src']):
    i = add_input(f'{SRC}/8842.mov', ('-ss', f"{s['cin']:.3f}"))
    d = s['o1'] - s['o0']
    chains.append(f"[{i}:a:0]atrim=0:{d:.3f},aresample=48000,aformat=channel_layouts=stereo,volume=0.25,"
                  f"afade=t=in:d=0.15,afade=t=out:st={d - 0.2:.3f}:d=0.2,adelay={int(s['o0'] * 1000)}:all=1[amb{n}]")
    labels.append(f'[amb{n}]')

# --- music: faint intro under the hook, drop on the flash, audible bed under the voice ---
if with_music:
    i = add_input(MUS, ('-ss', f'{11.64 - HOOK_END:.3f}'))
    vol = (f"if(lt(t\\,{HOOK_END:.3f})\\,0.19\\,0.19+(0.5-0.19)*clip((t-{MAIN_DUR - 0.3:.3f})/0.6\\,0\\,1))")
    chains.append(f"[{i}:a]atrim=0:{TOTAL:.3f},aresample=48000,aformat=channel_layouts=stereo,highpass=f=110,"
                  f"volume='{vol}':eval=frame,afade=t=in:d=1.2,afade=t=out:st={TOTAL - 0.8:.3f}:d=0.8[mus]")
    labels.append('[mus]')

chains.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first,"
              f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[out]")
script = SP + '/build/mix.filter'
open(script, 'w').write(';\n'.join(chains))
cmd = ['ffmpeg', '-loglevel', 'error', '-y', *inputs, '-filter_complex_script', script,
       '-map', '[out]', '-t', f'{TOTAL:.3f}', '-ac', '2', '-ar', '48000', out]
r = subprocess.run(cmd, capture_output=True, text=True)
print(r.stderr[-1500:] or 'ok', len(ev), 'sfx events ->', out)
