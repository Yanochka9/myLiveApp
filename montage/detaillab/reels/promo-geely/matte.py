# маска спикера (MODNet, Apache-2.0) для текста «за спиной» в первые секунды
import onnxruntime as ort, numpy as np, subprocess, sys, os
S = os.path.dirname(os.path.abspath(__file__))
T1 = float(sys.argv[1]); W_, H_ = 1080, 1920
sess = ort.InferenceSession(f'{S}/models/modnet.onnx')
n = int(round(T1 * 30))
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', f'{S}/out/video_raw.mp4', '-frames:v', str(n),
                      '-vf', 'scale=288:512', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
ms = []
for i in range(n):
    b = p.stdout.read(288 * 512 * 3)
    if len(b) < 288 * 512 * 3: break
    x = np.frombuffer(b, np.uint8).reshape(512, 288, 3).astype(np.float32) / 255
    x = (x - 0.5) / 0.5
    m = sess.run(None, {'input': x.transpose(2, 0, 1)[None]})[0][0, 0]
    ms.append((m * 255).astype(np.uint8))
np.save(f'{S}/out/matte.npy', np.stack(ms))
print(len(ms), 'frames')
