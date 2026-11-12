"""Intrigue bed for a hook (as approved in DP0): the client's riser (assets/sfx/riser.flac) — its decaying tail,
reversed and gently slowed — flattened onto a straight rising line so it is audible from the very first frame and
swells slightly to the cut. python3 intrigue.py <length_s> <out.wav> [rise_db]"""
import subprocess, sys, wave, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'assets', 'sfx', 'riser.flac')


def build(length, out, rise_db=5.0, src=SRC):
    raw = out + '.raw.wav'
    peak, end, rate = 3.25, 9.0, 0.72
    t = (end - peak) / length / rate
    at = []
    while t > 2.0:
        at.append('atempo=2.0'); t /= 2.0
    while t < 0.5:
        at.append('atempo=0.5'); t /= 0.5
    at.append(f'atempo={t:.4f}')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-af',
                    f"atrim={peak}:{end},asetpts=PTS-STARTPTS,areverse,aresample=48000,asetrate={48000 * rate:.0f},"
                    f"aresample=48000,{','.join(at)},aformat=channel_layouts=stereo", '-ar', '48000', raw], check=True)
    w = wave.open(raw); sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32).reshape(-1, 2) / 32768
    n = int(length * sr)
    a = a[:n] if len(a) >= n else np.pad(a, ((n - len(a), 0), (0, 0)), mode='edge')

    def env(x, win_s=0.5):
        win = int(win_s * sr); p = np.pad((x ** 2).mean(1), (win, win), mode='reflect')
        c = np.cumsum(np.insert(p, 0, 0.0)); h = win // 2                     # moving average via cumulative sum
        ma = (c[win:] - c[:-win]) / win; ma = np.pad(ma, (h, len(p) - len(ma) - h), mode='edge')
        return 10 * np.log10(ma[win:-win] + 1e-12)
    tt = np.arange(n) / sr; target = -rise_db * (1 - tt / length); y = a.copy()
    for _ in range(4):
        e = env(y); e -= e[-int(0.5 * sr):].mean()
        y = y * (10 ** (np.clip(target - e, -24, 24) / 20))[:, None]
    f0, f1 = int(0.05 * sr), int(0.03 * sr)
    y[:f0] *= np.linspace(0, 1, f0)[:, None]; y[-f1:] *= np.linspace(1, 0, f1)[:, None]
    y = y / max(1e-6, np.abs(y).max()) * 0.9
    o = wave.open(out, 'wb'); o.setnchannels(2); o.setsampwidth(2); o.setframerate(sr)
    o.writeframes((y * 32767).astype(np.int16).tobytes()); o.close(); os.remove(raw)
    return out


if __name__ == '__main__':
    print(build(float(sys.argv[1]), sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 5.0))
