# Речь рилса «Акция Geely EX2»: (клип, от, до) в порядке монтажа
import numpy as np, json, os
S = os.path.dirname(os.path.abspath(__file__)); R0 = os.path.dirname(S)
R = [('2714', 0.62, 5.2),    # На эти автомобили у нас скидка 10% на все комплексы оклейки — СНАЧАЛА (просьба клиента)
     ('2722', 0.6, 3.0),     # Сегодня у нас в оклейке Geely EX2
     ('2722', 3.28, 12.3),   # комплекс оклейки «Базовый», в который входит … крылья частично
     ('2722', 18.1, 27.3),   # а также такие зоны как стойки … канты крышки багажника
     ('2724', 2.38, 17.75),  # А также в этот комплекс … протирать ЛКП
     ('2727', 0.42, 8.2)]    # Успейте оклеить … Дзержинского, 82А
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
