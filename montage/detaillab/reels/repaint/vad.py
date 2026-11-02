# speech pieces for the "repaint" reel: (clip, from, to) in playback order
import numpy as np, json, os
S = os.path.dirname(os.path.abspath(__file__)); R0 = os.path.dirname(S)
R = [('2509', 1.0, 50.35), ('2509', 58.45, 60.7), ('2510', 0.9, 16.3), ('2509', 61.93, 65.6)]
out = []
for n, a, b in R:
    x = np.frombuffer(open(f'{R0}/wav/{n}.wav', 'rb').read()[44:], dtype='int16').astype(float) / 32768
    h = 320; m = len(x) // h; r = 20 * np.log10(np.sqrt((x[:m*h].reshape(m, h)**2).mean(1)) + 1e-9)
    rr = r[r > -100]; floor = np.percentile(rr, 10); peak = np.percentile(rr, 95); thr = floor + 0.35 * (peak - floor)
    v = r > thr; t = np.arange(m) * 0.02
    segs = []; cur = None
    for i in range(int(a / 0.02), min(m, int(b / 0.02))):
        if v[i]:
            if cur is None: cur = [t[i], t[i]]
            cur[1] = t[i] + 0.02
        elif cur and t[i] - cur[1] > 0.28: segs.append(cur); cur = None
    if cur: segs.append(cur)
    segs = [[n, round(max(a, s - 0.08), 2), round(min(b, e + 0.12), 2)] for s, e in segs if e - s > 0.06]
    out += segs
    print(n, a, b, ' '.join(f"{s:.2f}-{e:.2f}" for _, s, e in segs), 'total=%.2f' % sum(e - s for _, s, e in segs))
json.dump(out, open(f'{S}/segs.json', 'w'))
print('ALL', round(sum(e - s for _, s, e in out), 2))
