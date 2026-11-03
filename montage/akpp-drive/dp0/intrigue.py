"""Intrigue bed for the question: the client's sound from «музыка и звуки» (start of copy_B2B2…mov = riser.flac),
without heavy time-stretching. Its long decaying tail, reversed, is a natural slow swell; it is slowed gently
(tape-style, -4.7 semitones, plus a mild tempo change) to span the whole question, and its level is shaped so it is
audible from the first frame and rises evenly to the flash (+10 dB over the question)."""
import subprocess, sys, wave
import numpy as np
from edl import HOOK_END, SP

def build(src, out, length=HOOK_END, rise_db=10.0):
    raw = SP + '/build/intrigue_raw.wav'
    peak, end = 3.25, 11.6                      # tail of the riser (peak -> fade)
    span = end - peak
    f = span / length                           # overall speed factor
    rate = 0.76; tempo = f / rate              # asetrate part (pitch) x atempo part (mild)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-af',
                    f"atrim={peak}:{end},asetpts=PTS-STARTPTS,areverse,aresample=48000,"
                    f"asetrate={48000 * rate:.0f},aresample=48000,atempo={tempo:.4f},aformat=channel_layouts=stereo",
                    '-ar', '48000', raw], check=True)
    w = wave.open(raw); n = w.getnframes(); sr = w.getframerate()
    a = np.frombuffer(w.readframes(n), np.int16).astype(np.float32).reshape(-1, 2) / 32768
    a = a[:int(length * sr)]
    if len(a) < int(length * sr):
        a = np.pad(a, ((int(length * sr) - len(a), 0), (0, 0)))
    win = int(0.4 * sr)
    e = np.sqrt(np.convolve((a ** 2).mean(1), np.ones(win) / win, 'same')) + 1e-5
    t = np.arange(len(a)) / sr
    target_db = -rise_db + rise_db * (t / length) ** 1.3        # rising curve, 0 dB at the flash
    env_db = 20 * np.log10(e / e[-int(0.3 * sr):].mean())
    gain = 10 ** (np.clip(target_db - env_db, -40, 40) / 20)
    gain = np.convolve(gain, np.ones(win) / win, 'same')
    y = a * gain[:, None]
    fade = int(0.25 * sr); y[:fade] *= np.linspace(0, 1, fade)[:, None]
    y = np.clip(y, -1, 1)
    o = wave.open(out, 'wb'); o.setnchannels(2); o.setsampwidth(2); o.setframerate(sr)
    o.writeframes((y * 32767).astype(np.int16).tobytes()); o.close()
    return out

if __name__ == '__main__':
    print(build(sys.argv[1], sys.argv[2]))
