"""Safe-zone check for TikTok + Reels: nothing (graphics or subtitles) may leave x 150..930, y 280..1420.

python3 qa_safe.py   (after: QA=1 GFX_OUT=$SP/build node render_gfx.cjs  and  python3 subs.py)
Prints every frame/subtitle whose visible pixels cross the box, and exits 1 if any do.
"""
import glob, os, subprocess, sys
import numpy as np
from PIL import Image
from edl import SP, FPS, TOTAL
L, R, T, B = 150, 930, 280, 1420
bad = []
for f in sorted(glob.glob(SP + '/build/gfx_qa/*.png'))[::3]:
    a = np.asarray(Image.open(f))[:, :, 3] > 24
    if not a.any():
        continue
    ys, xs = np.where(a)
    box = (xs.min(), ys.min(), xs.max(), ys.max())
    if box[0] < L or box[2] > R or box[1] < T or box[3] > B:
        bad.append(('gfx', os.path.basename(f), box))
# subtitles: render the ASS over black, sample every 5th frame
out = SP + '/build/subs_qa'
os.makedirs(out, exist_ok=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=black:s=1080x1920:r={FPS}:d={TOTAL:.2f}',
                '-vf', f"ass={SP}/build/subs.ass,select='not(mod(n\\,5))'", '-vsync', '0', f'{out}/%05d.png'], check=True)
for f in sorted(glob.glob(out + '/*.png')):
    a = np.asarray(Image.open(f).convert('L')) > 40
    if not a.any():
        continue
    ys, xs = np.where(a)
    box = (xs.min(), ys.min(), xs.max(), ys.max())
    if box[0] < L or box[2] > R or box[1] < T or box[3] > B:
        bad.append(('subs', os.path.basename(f), box))
for b in bad:
    print(*b)
print('OK: everything inside the safe zone' if not bad else f'{len(bad)} frames outside the safe zone')
sys.exit(1 if bad else 0)
