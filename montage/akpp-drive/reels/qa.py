"""Safe-zone + face check (BRIEF 6a) for a reel: python3 qa.py lifan
gfx frames (build/<reel>/gfx) and subtitles must stay inside x 150..930, y 280..1420;
nothing may cover the presenter's face (with chin) on A-roll shots."""
import glob, importlib, os, subprocess, sys
import numpy as np, cv2
from PIL import Image
import lib

C = importlib.import_module(sys.argv[1])
R0 = lib.Reel(C)
if hasattr(C, '_hide'):
    C.HIDE = C._hide(R0)
R = lib.Reel(C)
L, Rt, T, B = 150, 930, 280, 1420
bad = []
gdir = R.B + '/gfx'
for f in sorted(glob.glob(gdir + '/*.png'))[::3]:
    n = int(os.path.basename(f)[:5])
    if n >= round(R.TOTAL * lib.FPS):  # stale frame beyond the cut
        continue
    a = np.asarray(Image.open(f))[:, :, 3] > 24
    # full-frame elements (flash, scheme background, end plate blur) are allowed edge to edge
    if a.mean() > 0.6:
        continue
    if not a.any():
        continue
    ys, xs = np.where(a)
    if xs.min() < L or xs.max() > Rt or ys.min() < T or ys.max() > B:
        bad.append(('gfx', n, round(n / lib.FPS, 2), (xs.min(), ys.min(), xs.max(), ys.max())))
out = R.B + '/subs_qa'
os.makedirs(out, exist_ok=True)
for f in glob.glob(out + '/*.png'):
    os.remove(f)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=black:s=1080x1920:r={lib.FPS}:d={R.TOTAL:.2f}',
                '-vf', f"ass={R.B}/subs.ass,select='not(mod(n\\,5))'", '-vsync', '0', f'{out}/%05d.png'], check=True)
for f in sorted(glob.glob(out + '/*.png')):
    a = np.asarray(Image.open(f).convert('L')) > 40
    if not a.any():
        continue
    ys, xs = np.where(a)
    if xs.min() < L or xs.max() > Rt or ys.min() < T or ys.max() > B:
        bad.append(('subs', f, (xs.min(), ys.min(), xs.max(), ys.max())))
import collections
sec = collections.Counter(int(b[2]) if b[0] == 'gfx' else -1 for b in bad)
print('outside, by second:', dict(sec))
for b in bad[:12]:
    print(*b)
print('OK: everything inside the safe zone' if not bad else f'{len(bad)} frames outside the safe zone')
# face
cas = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(R.B + '/base.mp4')
over = []
for s in [s for s in R.shots() if s['kind'] in ('aroll', 'hook')]:
    for n in range(round(s['o0'] * lib.FPS), round(s['o1'] * lib.FPS), 6):
        cap.set(cv2.CAP_PROP_POS_FRAMES, n); ok, fr = cap.read()
        if not ok:
            continue
        gimg = cv2.cvtColor(cv2.resize(fr, (540, 960)), cv2.COLOR_BGR2GRAY)
        fs = cas.detectMultiScale(gimg, 1.1, 5, minSize=(60, 60))
        if len(fs) == 0:
            continue
        x, y, w, h = [v * 2 for v in max(fs, key=lambda r: r[2] * r[3])]
        y1 = y + int(h * 1.15)
        msk = np.zeros((1920, 1080), bool)
        gp = f'{gdir}/{n:05d}.png'
        if os.path.exists(gp):
            ga = np.asarray(Image.open(gp))[:, :, 3] > 24
            if ga.mean() < 0.6:          # a full-frame flash is a transition, not an overlay
                msk |= ga
        sp = f'{out}/{n // 5 + 1:05d}.png'
        if os.path.exists(sp):
            msk |= np.asarray(Image.open(sp).convert('L')) > 40
        if msk[y:y1, x:x + w].any():
            over.append((n, round(n / lib.FPS, 2), (x, y, w, y1 - y)))
for b in over[:40]:
    print('over face:', *b)
print('OK: nothing covers the face' if not over else f'{len(over)} frames with graphics over the face')
