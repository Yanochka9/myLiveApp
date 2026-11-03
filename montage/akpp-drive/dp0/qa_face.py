"""Face check: no graphics or subtitles over the presenter's face (A-roll shots).
python3 qa_face.py  (after qa_safe.py has rendered gfx_qa and subs_qa)"""
import glob, os, sys, json
import numpy as np, cv2
from PIL import Image
from edl import SP, FPS, build_shots
shots = [s for s in build_shots() if s['kind'] == 'aroll']
cas = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(SP + '/build/base.mp4')
bad = []
for s in shots:
    for n in range(round(s['o0'] * FPS), round(s['o1'] * FPS), 6):
        cap.set(cv2.CAP_PROP_POS_FRAMES, n); ok, fr = cap.read()
        if not ok: continue
        g = cv2.cvtColor(cv2.resize(fr, (540, 960)), cv2.COLOR_BGR2GRAY)
        f = cas.detectMultiScale(g, 1.1, 5, minSize=(80, 80))
        if len(f) == 0: continue
        x, y, w, h = [v * 2 for v in max(f, key=lambda r: r[2] * r[3])]
        y1 = y + int(h * 1.15)                       # face incl. chin
        m = np.zeros((1920, 1080), bool)
        gp = f'{SP}/build/gfx_qa/{n:05d}.png'
        if os.path.exists(gp): m |= np.asarray(Image.open(gp))[:, :, 3] > 24
        sp = f'{SP}/build/subs_qa/{n // 5 + 1:05d}.png'
        if os.path.exists(sp): m |= np.asarray(Image.open(sp).convert('L')) > 40
        if m[y:y1, x:x + w].any():
            bad.append((n, round(n / FPS, 2), (x, y, w, y1 - y)))
for b in bad: print('over face:', *b)
print('OK: nothing covers the face' if not bad else f'{len(bad)} frames with graphics over the face')
sys.exit(1 if bad else 0)
