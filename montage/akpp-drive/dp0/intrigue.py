"""Intrigue bed for the question: the client's sound from «музыка и звуки» (start of copy_B2B2…mov = riser.flac),
without heavy time-stretching (atempo x5 sounded robotic). The audible part of its decaying tail, reversed, is a natural
slow swell; it is slowed gently (tape-style plus a mild tempo change) to span the whole question. Its level is then
pulled onto a straight rising line: audible from the first frame, +rise_db up to the flash, never loud."""
import subprocess, sys, wave
import numpy as np
from edl import HOOK_END, SP

def _env_db(x, sr, win_s=0.75):
    win = int(win_s * sr)
    p = np.pad((x ** 2).mean(1), (win, win), mode='reflect')
    e = np.convolve(p, np.ones(win) / win, 'same')[win:-win]
    return 10 * np.log10(e + 1e-12)

def build(src, out, length=HOOK_END, rise_db=5.0):
    raw = SP + '/build/intrigue_raw.wav'
    peak, end = 3.25, 9.0                       # audible part of the riser's tail
    f = (end - peak) / length
    rate = 0.72; tempo = f / rate              # -5.7 semitones tape slow-down x mild atempo
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-af',
                    f"atrim={peak}:{end},asetpts=PTS-STARTPTS,areverse,aresample=48000,"
                    f"asetrate={48000 * rate:.0f},aresample=48000,atempo={tempo:.4f},aformat=channel_layouts=stereo",
                    '-ar', '48000', raw], check=True)
    w = wave.open(raw); sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32).reshape(-1, 2) / 32768
    n = int(length * sr)
    a = a[:n] if len(a) >= n else np.pad(a, ((n - len(a), 0), (0, 0)), mode='edge')
    t = np.arange(n) / sr
    target = -rise_db * (1 - t / length)        # dB, 0 at the flash
    y = a.copy()
    for _ in range(4):                          # converge the envelope onto the target line
        env = _env_db(y, sr)
        env -= env[-int(0.75 * sr):].mean()
        corr = np.clip(target - env, -24, 24)
        y = y * (10 ** (corr / 20))[:, None]
    fade = int(0.2 * sr); y[:fade] *= np.linspace(0, 1, fade)[:, None]
    y = y / max(1e-6, np.abs(y).max()) * 0.9
    o = wave.open(out, 'wb'); o.setnchannels(2); o.setsampwidth(2); o.setframerate(sr)
    o.writeframes((y * 32767).astype(np.int16).tobytes()); o.close()
    return out

if __name__ == '__main__':
    print(build(sys.argv[1], sys.argv[2]))
