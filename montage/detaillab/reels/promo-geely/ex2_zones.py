# Вырезанная EX2 (фото Commons full4) + зоны «Базового» в координатах дисплея 960×540 исходного фото
import numpy as np
from PIL import Image
ZONES = [  # (подпись, ключ, список фигур)
    ('ПЕРЕДНЯЯ ОПТИКА', 'оптика', [('poly', [(655, 228), (705, 240), (780, 258), (770, 272), (720, 270), (668, 248)])]),
    ('КАПОТ ЦЕЛИКОМ', 'капот', [('line', [(505, 190), (620, 188), (760, 200), (905, 222), (930, 238)])]),
    ('КРЫЛЬЯ ЧАСТИЧНО', 'крылья', [('arc', (590, 395, 108, 195, 335)), ('arc', (95, 352, 88, 195, 330))]),
    ('СТОЙКИ ЧАСТИЧНО', 'стойки', [('line', [(442, 78), (497, 182)]), ('line', [(290, 88), (276, 178)])]),
    ('ПОЛОСА НА КРЫШУ', 'полоса', [('line', [(330, 67), (560, 75)])]),
    ('АНТИМАНИКЮРЫ', 'антиманикюры', [('cap', (125, 208)), ('cap', (306, 221))]),
    ('КАНТЫ ДВЕРЕЙ', 'канты', [('line', [(97, 178), (110, 350)]), ('line', [(275, 98), (272, 372)]), ('line', [(496, 190), (492, 396)])]),
    ('КАНТ КРЫШКИ БАГАЖНИКА', 'багажника', [('line', [(112, 96), (80, 140), (62, 200)])]),
]
def make_cut(src='stock/full4.jpg', out='stock/ex2_side_cut.png'):
    import cv2
    from rembg import remove, new_session
    im = Image.open(src).convert('RGB')
    c = np.array(remove(im, session=new_session('isnet-general-use')))
    x0, y0, x1, y1 = [v * 4 for v in (420, 80, 470, 100)]           # наклейка «664» на стекле
    rgb = np.ascontiguousarray(c[..., :3]); mask = np.zeros(rgb.shape[:2], np.uint8)
    reg = rgb[y0:y1, x0:x1].astype(int)
    mask[y0:y1, x0:x1][(reg[..., 0] > 150) & (reg[..., 0] - reg[..., 2] > 60)] = 255
    mask = cv2.dilate(mask, np.ones((15, 15), np.uint8))
    c[..., :3] = cv2.inpaint(rgb, mask, 9, cv2.INPAINT_TELEA)
    img = Image.fromarray(c); bb = img.getbbox(); img.crop(bb).save(out)
    return bb
