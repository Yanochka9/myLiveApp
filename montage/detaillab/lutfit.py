"""Подгонка цвета по паре кадров «наш кадр → кадр клиента» (скриншот CapCut) в 3D-LUT (.cube).
Кривые по каналам (монотонные) + плавная 3D-поправка остатка (повторяет HSL-правки клиента).
python3 lutfit.py <наш_кадр.png> <кадр_клиента.png> <out.cube>"""
import sys, numpy as np
from PIL import Image, ImageFilter
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter
def load(p, size=(540, 960)):
    return np.asarray(Image.open(p).convert('RGB').resize(size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(2)), float) / 255
def fit(src, dst, out, n=33, G=12):
    b = src.reshape(-1, 3); e = dst.reshape(-1, 3)
    # 1) монотонные кривые по каналам (медианы по бинам)
    curves = []
    for c in range(3):
        bins = np.linspace(0, 1, 26); xs = [0.0]; ys = [0.0]
        for lo, hi in zip(bins[:-1], bins[1:]):
            m = (b[:, c] >= lo) & (b[:, c] < hi)
            if m.sum() > 150: xs.append(np.median(b[m, c])); ys.append(np.median(e[m, c]))
        xs.append(1.0); ys.append(max(ys[-1], min(1.0, ys[-1] + (1 - xs[-2]))) if len(ys) > 1 else 1.0)
        ys = np.maximum.accumulate(np.clip(ys, 0, 1)); xs = np.array(xs)
        keep = np.r_[True, np.diff(xs) > 1e-3]
        curves.append(PchipInterpolator(xs[keep], ys[keep]))
    cb = np.stack([curves[c](b[:, c]) for c in range(3)], -1)
    # 2) остаток — плавная 3D-поправка по цвету
    r = e - cb
    idx = np.clip((cb * (G - 1)).round().astype(int), 0, G - 1)
    S = np.zeros((G, G, G, 3)); N = np.zeros((G, G, G))
    np.add.at(S, (idx[:, 0], idx[:, 1], idx[:, 2]), r); np.add.at(N, (idx[:, 0], idx[:, 1], idx[:, 2]), 1)
    Ss = np.stack([gaussian_filter(S[..., k], 1.2) for k in range(3)], -1); Ns = gaussian_filter(N, 1.2)
    res = Ss / (Ns[..., None] + 1e-6) * np.clip(Ns / 40, 0, 1)[..., None]     # где данных нет — поправка к нулю
    # 3) таблица
    g = np.linspace(0, 1, n); Bg, Gg, Rg = np.meshgrid(g, g, g, indexing='ij')
    rgb = np.stack([Rg, Gg, Bg], -1).reshape(-1, 3)
    c1 = np.stack([curves[c](rgb[:, c]) for c in range(3)], -1)
    from scipy.interpolate import RegularGridInterpolator
    ax = np.linspace(0, 1, G)
    corr = np.stack([RegularGridInterpolator((ax, ax, ax), res[..., k])(np.clip(c1, 0, 1)) for k in range(3)], -1)
    lut = np.clip(c1 + corr, 0, 1)
    with open(out, 'w') as f:
        f.write(f"LUT_3D_SIZE {n}\n"); f.writelines(f"{x:.6f} {y:.6f} {z:.6f}\n" for x, y, z in lut)
    return lut
if __name__ == '__main__':
    fit(load(sys.argv[1]), load(sys.argv[2]), sys.argv[3])
