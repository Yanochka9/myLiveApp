"""High-quality person + car masks for spotlight / behind-layer shots.

BiRefNet keyframes at 15 fps (optionally a second pass on a crop, for a car cut off by the frame edge),
a light temporal median, then every 30 fps frame is snapped to the picture with a guided filter.
Result: work/<name>/masks_hq/<clip>/<round(t*30)>.png, picked up automatically by Comp.mask()."""
import os, sys, glob, json, subprocess, numpy as np, cv2
from common import W, H

KEY_FPS, OUT_FPS = 15, 30


def frames(p, clip, a, b, fps, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for f in glob.glob(os.path.join(out_dir, '*.png')): os.remove(f)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a:.4f}', '-i', p.clip(clip), '-t', f'{b - a:.4f}',
                    '-vf', f'fps={fps},scale={W}:{H}', os.path.join(out_dir, '%05d.png')], check=True)
    return sorted(glob.glob(os.path.join(out_dir, '*.png')))


def keyframes(p, clip, a, b, model, crops, batch=6):
    """raw BiRefNet masks at KEY_FPS, index = round(t*KEY_FPS); runs in short-lived subprocesses (the model leaks memory)"""
    kd = os.path.join(p.work, 'masks_hq_key', clip); os.makedirs(kd, exist_ok=True)
    tmp = os.path.join(p.work, 'hq_tmp_key')
    fs = frames(p, clip, a, b, KEY_FPS, tmp)
    i0 = int(round(a * KEY_FPS))
    jobs = [(f, os.path.join(kd, f'{i0 + k:05d}.png'), (i0 + k) / KEY_FPS) for k, f in enumerate(fs)]
    jobs = [j for j in jobs if not os.path.exists(j[1])]
    for s in range(0, len(jobs), batch):
        part = [(f, o, [c for c in crops if c[0] <= t < c[1]]) for f, o, t in jobs[s:s + batch]]
        code = ('import sys,json\nfrom rembg import new_session, remove\nfrom PIL import Image, ImageChops\n'
                f'S=new_session({model!r})\n'
                'for f,o,cr in json.loads(sys.argv[1]):\n'
                '  im=Image.open(f).convert("RGB"); m=remove(im,session=S,only_mask=True).convert("L")\n'
                '  for _,_,(x,y,w,h) in cr:\n'
                '    c=remove(im.crop((x,y,x+w,y+h)),session=S,only_mask=True).convert("L")\n'
                '    full=Image.new("L",m.size,0); full.paste(c,(x,y)); m=ImageChops.lighter(m,full)\n'
                '  m.save(o); print("mask",o,flush=True)\n')
        subprocess.run([sys.executable, '-I', '-c', code, json.dumps(part)], check=True, cwd='/tmp')
    return kd, i0, i0 + len(fs) - 1


def guided(I, p_, r, eps):
    mean = lambda x: cv2.boxFilter(x, -1, (r, r))
    mI, mp = mean(I), mean(p_)
    a = (mean(I * p_) - mI * mp) / (mean(I * I) - mI * mI + eps)
    b = mp - a * mI
    return mean(a) * I + mean(b)


def refine(p, clip, a, b, kd, k0, k1, r=10, eps=1e-4, shrink=2):
    od = os.path.join(p.work, 'masks_hq', clip); os.makedirs(od, exist_ok=True)
    key = {}
    for k in range(k0, k1 + 1):
        m = cv2.imread(os.path.join(kd, f'{k:05d}.png'), cv2.IMREAD_GRAYSCALE)
        if m is not None: key[k] = m.astype(np.float32) / 255
    ks = sorted(key)
    sm = {}
    for i, k in enumerate(ks):   # temporal median of three keyframes: removes one-frame dropouts without lag
        nb = [key[ks[j]] for j in (i - 1, i, i + 1) if 0 <= j < len(ks)]
        sm[k] = np.median(np.stack(nb), 0) if len(nb) == 3 else key[k]
    fs = frames(p, clip, a, b, OUT_FPS, os.path.join(p.work, 'hq_tmp_out'))
    j0 = int(round(a * OUT_FPS))
    for n, f in enumerate(fs):
        t = (j0 + n) / OUT_FPS; x = t * KEY_FPS
        lo = max(ks[0], min(ks[-1], int(np.floor(x)))); hi = min(ks[-1], lo + 1); w = min(1.0, max(0.0, x - lo))
        m = sm[lo] * (1 - w) + sm[hi] * w
        I = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
        q = np.clip(guided(I, m, r, eps), 0, 1)
        q = np.clip((q - 0.35) / 0.3, 0, 1); q = q * q * (3 - 2 * q)          # crisp but soft-edged
        if shrink: q = cv2.erode(q, np.ones((2 * shrink + 1, 2 * shrink + 1), np.uint8))   # no light rim around the subject
        q = cv2.GaussianBlur(q, (0, 0), 1.0)
        cv2.imwrite(os.path.join(od, f'{j0 + n:05d}.png'), (q * 255).astype(np.uint8))
    print('hq masks', clip, len(fs), '->', od)


def hqmask(p, clip, a, b, model='birefnet-general-lite', crops=()):
    kd, k0, k1 = keyframes(p, clip, a, b, model, list(crops))
    refine(p, clip, a, b, kd, k0, k1)
