# Снижение насыщенности только оранжевых тонов (как HSL «оранжевый» в CapCut) → .cube
import numpy as np, colorsys, sys
def band(h):                       # h в градусах; оранжевый центр ~28°, мягкие края
    d = np.minimum(np.abs(h - 28), 360 - np.abs(h - 28))
    return np.clip(1 - (d - 12) / 18, 0, 1)
def apply(rgb, amt):               # rgb 0..1, amt 0..1 — на сколько убрать насыщенность оранжевого
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(-1); mn = rgb.min(-1); d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    w = band(h) * amt * np.clip(d * 4, 0, 1)
    Y = (rgb @ np.array([.299, .587, .114]))[..., None]
    return rgb + (Y - rgb) * w[..., None]
def cube(path, amt, n=33):
    g = np.linspace(0, 1, n); B, G, R = np.meshgrid(g, g, g, indexing='ij')
    out = apply(np.stack([R, G, B], -1), amt).reshape(-1, 3)
    with open(path, 'w') as f:
        f.write(f"LUT_3D_SIZE {n}\n"); f.writelines(f"{x:.6f} {y:.6f} {z:.6f}\n" for x, y, z in out)
if __name__ == '__main__':
    cube(sys.argv[1], float(sys.argv[2]))
