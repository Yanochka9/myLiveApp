"""Замазать гос-номер на proxy: боксы [x, y, w, h] по номеру кадра (30 fps) из json.
Боксы готовят трекером (cv2.TrackerCSRT) + ручными ключами там, где трекер плавает, и проверяют листами кадров.
  python3 -I plate_blur.py <proxy_orig.mov> <boxes.json> <proxy.mov>
make_video.py prep вызывает сам, если в конфиге есть "plate_boxes"."""
import json, subprocess, sys

import cv2
import numpy as np


def blur(src, boxes_path, out):
    B = {int(k): v for k, v in json.load(open(boxes_path)).items()}
    cap = cv2.VideoCapture(src)
    W, H = int(cap.get(3)), int(cap.get(4))
    p = subprocess.Popen(f"ffmpeg -v error -y -f rawvideo -pix_fmt bgr24 -s {W}x{H} -r 30 -i - -i '{src}' -map 0:v -map 1:a? "
                         f"-c:v libx264 -preset veryfast -crf 14 -pix_fmt yuv420p -c:a copy '{out}'", shell=True, stdin=subprocess.PIPE)
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i in B:
            x, y, w, h = B[i]
            px, py = int(w * 0.25) + 12, int(h * 0.35) + 12
            x0, y0, x1, y1 = max(x - px, 0), max(y - py, 0), min(x + w + px, W), min(y + h + py, H)
            roi = f[y0:y1, x0:x1]
            small = cv2.resize(roi, (max(2, (x1 - x0) // 18), max(2, (y1 - y0) // 18)), interpolation=cv2.INTER_AREA)
            bl = cv2.GaussianBlur(cv2.resize(small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR), (0, 0), 9)
            m = np.zeros((y1 - y0, x1 - x0), np.float32)
            cv2.rectangle(m, (x - x0 - px // 3, y - y0 - py // 3), (x - x0 + w + px // 3, y - y0 + h + py // 3), 1, -1)
            m = cv2.GaussianBlur(m, (0, 0), 7)[..., None]
            f[y0:y1, x0:x1] = (bl * m + roi * (1 - m)).astype(np.uint8)
        p.stdin.write(f.tobytes()); i += 1
    p.stdin.close(); p.wait()
    print("plate_blur: frames", i, "blurred", len(B))


if __name__ == "__main__":
    blur(*sys.argv[1:4])
