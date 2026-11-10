"""Адаптивный цвет DetailLab: один и тот же итоговый вид при разном свете в исходниках.

Как работает (утверждено клиентом 03.11.2026):
  1. Каждый клип переводится HDR→SDR (если снят в HLG) — строка 1 `assets/grade_client.txt`.
  2. НОРМАЛИЗАЦИЯ под клип: замеряем сам клип (8 кадров) и подтягиваем к эталону
     `assets/grade_ref.json` (исходники рилса «Крашеный элемент», на которых утверждён цвет):
       • баланс белого — по нейтральным (серым/белым) пикселям, а не по всему кадру;
       • яркость — кривая по перцентилям (тени/середина/света), с силой STRENGTH и ограничением сдвига;
       • насыщенность — по цветным пикселям, тоже частично.
     Тёмный клип станет светлее, жёлтый — нейтральнее, но не «в ноль»: сюжет кадра (чёрная машина, белая стена)
     тоже влияет на цифры, поэтому подтягиваем частично и с пределами.
  3. Поверх — ОДИНАКОВЫЙ для всех стиль клиента (строка 2 `grade_client.txt`).

CLI:
  python3 autograde.py ref  <клипы...>     — пересчитать эталон (делать только по просьбе)
  python3 autograde.py norm <клип>         — фильтр нормализации для клипа
  python3 autograde.py full <клип>         — полная цепочка: HDR + нормализация + стиль
"""
import json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
A = f"{HERE}/assets"
REF = f"{A}/grade_ref.json"
CLIENT = open(f"{A}/grade_client.txt").read().replace("ASSETS/", f"{A}/").split("\n")
HDR, STYLE = CLIENT[0].strip(), CLIENT[1].strip()
STRENGTH = 0.65          # насколько тянуть к эталону (1 — полностью)
MAX_SHIFT = 0.10         # максимум сдвига точки кривой (доля 0..1)
PS = [2, 10, 25, 50, 75, 90, 98]


def is_hlg(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=color_transfer',
                          '-of', 'csv=p=0', path], capture_output=True, text=True).stdout
    return 'arib-std-b67' in out


def frames(path, n=8, extra=''):
    d = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]))
    pre = f"{HDR}," if is_hlg(path) else ""
    out = []
    for i in range(n):
        t = d * (i + 0.5) / n
        b = subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', path, '-frames:v', '1', '-vf',
                                     f"{pre}scale=270:480{(',' + extra) if extra else ''},format=rgb24", '-f', 'rawvideo', '-'])
        out.append(np.frombuffer(b, np.uint8).reshape(480, 270, 3))
    return np.stack(out).astype(np.float32) / 255


def stats(x):
    Y = x @ np.array([.2126, .7152, .0722])
    mx, mn = x.max(-1), x.min(-1); sat = (mx - mn) / (mx + 1e-4)
    neu = (sat < 0.12) & (Y > 0.2) & (Y < 0.92)
    col = (sat > 0.15) & (Y > 0.08)
    rgb_neu = x[neu].mean(0) if neu.sum() > 500 else x.reshape(-1, 3).mean(0)
    return {'lum': [float(np.percentile(Y, p)) for p in PS],
            'neutral': [float(v) for v in rgb_neu / rgb_neu.mean()],
            'sat': float(sat[col].mean()) if col.sum() > 500 else float(sat.mean())}


def make_ref(paths):
    xs = np.concatenate([frames(p) for p in paths])
    s = stats(xs); s['from'] = [os.path.basename(p) for p in paths]
    json.dump(s, open(REF, 'w'), ensure_ascii=False, indent=1)
    return s


def norm_filter(path, strength=STRENGTH):
    ref = json.load(open(REF))
    x = frames(path)
    s = stats(x)
    # 1) баланс белого: множители каналов, чтобы нейтральные пиксели легли как в эталоне
    g = np.array(ref['neutral']) / np.array(s['neutral'])
    g = 1 + (g - 1) * strength
    g = np.clip(g / g.mean(), 0.88, 1.12)
    wb = f"colorchannelmixer=rr={g[0]:.4f}:gg={g[1]:.4f}:bb={g[2]:.4f}"
    # 2) яркость по перцентилям (после баланса)
    x2 = np.clip(x * g, 0, 1); s2 = stats(x2)
    pts = [(0.0, 0.0)]
    for a, b in zip(s2['lum'], ref['lum']):
        y = a + np.clip((b - a) * strength, -MAX_SHIFT, MAX_SHIFT)
        if a - pts[-1][0] > 0.04 and y > pts[-1][1] + 0.01 and a < 0.93 and y < 0.95:
            pts.append((a, y))
    pts.append((1.0, 1.0))
    # pchip — монотонная кривая: без «перелёта» у белого (natural давала зелёные пересветы)
    curve = "curves=interp=pchip:m='" + ' '.join(f'{a:.3f}/{b:.3f}' for a, b in pts) + "'"
    # 3) насыщенность
    k = 1 + (ref['sat'] / max(1e-3, s['sat']) - 1) * strength * 0.6   # цвет сильнее зависит от сюжета — тянем слабее
    k = float(np.clip(k, 0.9, 1.15))
    return f"{wb},{curve},eq=saturation={k:.3f}", {'gains': g.round(3).tolist(), 'sat': round(k, 3),
                                                    'lum_clip': [round(v, 3) for v in s['lum']]}


def full_chain(path):
    """HDR (если надо) + нормализация клипа + стиль клиента — для одного исходника."""
    nf, _ = norm_filter(path)
    return (f"{HDR}," if is_hlg(path) else "") + nf, STYLE


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'ref':
        print(json.dumps(make_ref(args), ensure_ascii=False))
    elif cmd == 'norm':
        f, info = norm_filter(args[0]); print(f); print(info, file=sys.stderr)
    elif cmd == 'full':
        pre, st = full_chain(args[0]); print(pre); print(st)
