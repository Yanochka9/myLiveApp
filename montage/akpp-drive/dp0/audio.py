"""Audio mix: raw voice (no processing), quiet SFX from the client's pack on key moments,
hook drone, music bed ~13 dB under the voice. Levels are relative to the measured voice.

python3 audio.py            -> build/mix.wav (with music)
python3 audio.py --no-music -> build/mix_nomusic.wav
"""
import re, subprocess, sys, os
from edl import segs, MAIN, HOOK_END, MAIN_DUR, TOTAL, SP
import json

T = json.load(open(SP + '/build/gfx.json'))
SFX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'sfx')
# client's track from Drive «музыка и звуки» (copy_FCD0D4FD…mov), starts on a strong hit at 3.41 s
MUS, MUS_IN, MUS_LUFS = SP + '/music/FCD0.wav', 3.41, -21.4   # LUFS after highpass 110 Hz
PEAK = {'riser': 3.06, 'click1': .11, 'click2': .14, 'click3': .11, 'click4': .16, 'click5': .06,
        'scheme-glitch': .39, 'scheme-static': .47}
with_music = '--no-music' not in sys.argv
B = SP + '/build'
out = B + ('/mix.wav' if with_music else '/mix_nomusic.wav')

def lufs(path):
    r = subprocess.run(['ffmpeg', '-i', path, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1])

inputs, chains, labels = [], [], []
idx = 0
def add_input(path, pre=()):
    global idx
    inputs.extend([*pre, '-i', path]); idx += 1; return idx - 1

# --- voice: straight cuts with 12 ms micro-fades, nothing else ---
v = add_input(MAIN)
parts = []
for i, (a, b) in enumerate(segs):
    chains.append(f"[{v}:a:0]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,"
                  f"afade=t=out:st={b - a - 0.012:.4f}:d=0.012[s{i}]")
    parts.append(f"[s{i}]")
chains.append(f"{''.join(parts)}concat=n={len(segs)}:v=0:a=1,aresample=48000,aformat=channel_layouts=stereo,"
              f"apad=whole_dur={TOTAL:.3f}[voice]")
labels.append('[voice]')

# --- sfx: only key moments ---
ev = []  # (time of peak, id, gain)
ev.append((HOOK_END + 0.02, 'click3', 0.03))                # question -> answer (on the flash, barely audible)
ev.append((T['scheme'][0], 'scheme-glitch', 0.033))         # hydraulic scheme
ev.append((T['scheme'][2], 'scheme-static', 0.05))          # leak
ev.append((T['scheme'][3] + 0.1, 'click5', 0.04))           # control unit alarm
for (lt, _, _), c in zip(T['reasons'][:3], ['click1', 'click4', 'click2']):
    ev.append((lt, c, 0.04))
ev.append((T['free'][0] + 0.25, 'click2', 0.05))            # БЕСПЛАТНО
ev.append((T['address'][0] + 0.3, 'click3', 0.045))
for j in range(4):                                          # end plate lines
    ev.append((MAIN_DUR + 0.25 + j * 0.12, ['click1', 'click5', 'click4', 'click3'][j], 0.035))
ev.append((MAIN_DUR + 1.05, 'click1', 0.03))
for n, (t, sid, vol) in enumerate(ev):
    ext = 'mp3' if sid.startswith('scheme') else 'flac'
    i = add_input(f'{SFX}/{sid}.{ext}')
    d = t - PEAK[sid]
    pre = f"atrim=start={-d:.3f}," if d < 0 else ""
    chains.append(f"[{i}:a]{pre}aresample=48000,aformat=channel_layouts=stereo,volume={vol},"
                  f"adelay={int(max(0, d) * 1000)}:all=1[e{n}]")
    labels.append(f'[e{n}]')

# --- question: intrigue bed from the first frame to the flash. The riser's build is stretched over the
# whole question and its level evened out (dynaudnorm), so it is audible from the start, then a gentle
# lift into the flash. Quiet: ~24 dB under the voice, ~20 dB at the end.
RISE = PEAK['riser']
from intrigue import build as build_intrigue
bed = build_intrigue(f'{SFX}/riser.flac', B + '/intrigue.wav')
bl = lufs(bed)
VOICE_LUFS = -28.0
g0 = g1 = 10 ** ((VOICE_LUFS - 17 - bl) / 20)   # shape is in the file: ~-21 dB under the voice at the start, ~-10 at the flash (voice is quieter there)
print(f'intrigue bed {bl:.1f} LUFS -> gain {g0:.3f}..{g1:.3f}')
i = add_input(bed)
ramp = f"{g0:.4f}+({g1:.4f}-{g0:.4f})*clip((t-{HOOK_END - 3:.3f})/3\\,0\\,1)"
chains.append(f"[{i}:a]volume='{ramp}':eval=frame,afade=t=in:d=0.3,afade=t=out:st={HOOK_END - 0.15:.3f}:d=0.15[rise]")
i = add_input(f'{SFX}/riser.flac')
chains.append(f"[{i}:a]atrim={RISE:.3f}:{RISE + 2.0:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
              f"volume=0.012,afade=t=out:st=0.4:d=1.6,adelay={int(HOOK_END * 1000)}:all=1[risetail]")
labels += ['[rise]', '[risetail]']

# --- music: starts on the first frame after the hook, ~13.5 dB under the voice, up on the end plate ---
if with_music:
    vtmp = B + '/voice_only.wav'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', MAIN, '-filter_complex_script', '/dev/stdin',
                    '-map', '[voice]', vtmp], input=';\n'.join(chains[:len(segs) + 1]), text=True, check=True)
    vl = lufs(vtmp)
    bedg = 10 ** ((vl - 17.0 - MUS_LUFS) / 20)
    top = 10 ** ((vl - 1.0 - MUS_LUFS) / 20)
    print(f'voice {vl:.1f} LUFS -> music bed gain {bedg:.3f}, end plate {top:.3f}')
    i = add_input(MUS, ('-ss', str(MUS_IN)))
    md = TOTAL - HOOK_END
    vol = f"{bedg:.4f}+({top:.4f}-{bedg:.4f})*clip((t-{MAIN_DUR - HOOK_END - 0.3:.3f})/0.6\\,0\\,1)"
    chains.append(f"[{i}:a]atrim=0:{md:.3f},aresample=48000,aformat=channel_layouts=stereo,highpass=f=110,"
                  f"volume='{vol}':eval=frame,afade=t=out:st={md - 0.8:.3f}:d=0.8,"
                  f"adelay={int(HOOK_END * 1000)}:all=1[mus]")
    labels.append('[mus]')

chains.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first,aresample=48000[out]")
script = B + '/mix.filter'
open(script, 'w').write(';\n'.join(chains))
cmd = ['ffmpeg', '-loglevel', 'error', '-y', *inputs, '-filter_complex_script', script,
       '-map', '[out]', '-t', f'{TOTAL:.3f}', '-ac', '2', '-ar', '48000', out]
r = subprocess.run(cmd, capture_output=True, text=True)
print(r.stderr[-1500:] or 'ok', len(ev), 'sfx events ->', out)
