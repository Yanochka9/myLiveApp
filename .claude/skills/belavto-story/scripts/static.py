"""Статичная сторис-продолжение (кадр под нативный стикер Instagram).

  python3 -I static.py static.json

Конфиг:
  bg        — картинка или видео (из видео берётся кадр bg_time, по умолчанию последний);
  bg_time   — секунда кадра из видео (необязательно);
  blur      — true: фон сильно размыт и затемнён (по умолчанию), false: фон читается, лишь слегка смягчён;
  badge     — красная плашка-рубрика сверху (или null);
  title     — главный текст, \\n — перенос, *звёздочки* — жёлтым;
  sub       — строка под заголовком (или null);
  sticker   — poll / question / quiz / link / dm / null: под стикер оставляется пустая зона;
  footer    — подпись снизу (по умолчанию «Белавтоцентр»);
  out       — путь к PNG. Рядом пишется *_preview.png с отмеченной зоной стикера.
"""
import json, os, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import W, H, RED, font, shadowed, pill  # noqa: E402

YELLOW = (255, 211, 77, 255)
STICKER = {"poll": "ОПРОС", "question": "ВОПРОС", "quiz": "ВИКТОРИНА", "link": "ССЫЛКА", "dm": "НАПИСАТЬ"}
ZONE = (140, 1080, W - 140, 1440)  # между текстом и полем ответа — нижние 340 px не занимаем


def load_bg(cfg):
    src = cfg["bg"]
    if src.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        img = Image.open(src)
    else:
        tmp = tempfile.mktemp(suffix=".png")
        seek = ["-ss", str(cfg["bg_time"])] if "bg_time" in cfg else ["-sseof", "-0.3"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", *seek, "-i", src, "-frames:v", "1",
                        "-vf", "zscale=t=linear:npl=100,tonemap=hable,zscale=t=bt709:m=bt709:r=tv,format=rgb24",
                        tmp], check=False)
        if not os.path.exists(tmp):  # SDR-исходник — без тонмаппинга
            subprocess.run(["ffmpeg", "-v", "error", "-y", *seek, "-i", src, "-frames:v", "1", tmp], check=True)
        img = Image.open(tmp)
    img = img.convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    img = ImageEnhance.Color(img.crop((x, y, x + W, y + H))).enhance(0.8)
    if cfg.get("blur", True):
        img = ImageEnhance.Brightness(img.filter(ImageFilter.GaussianBlur(28))).enhance(0.7)
    else:  # фон читается (скрин сайта, машина), но текст поверх остаётся контрастным
        img = ImageEnhance.Brightness(img.filter(ImageFilter.GaussianBlur(5))).enhance(0.45)
    return img.convert("RGBA")


def rich_line(d, y, line, f):
    """Строка по центру; *фрагменты* — жёлтым."""
    parts = re.split(r"(\*.+?\*)", line)
    total = sum(d.textlength(p.strip("*"), font=f) for p in parts)
    x = (W - total) / 2
    for p in parts:
        t = p.strip("*")
        d.text((x, y), t, font=f, fill=YELLOW if p.startswith("*") else "white",
               stroke_width=2, stroke_fill=(0, 0, 0, 90))
        x += d.textlength(t, font=f)


def main():
    cfg = json.load(open(sys.argv[1]))
    img = load_bg(cfg)
    lines = cfg["title"].split("\n")
    f_title = font("ExtraBold", 96 if max(len(l.replace("*", "")) for l in lines) <= 16 else 78)
    step = f_title.size + 18
    y0 = (ZONE[1] - 60 - len(lines) * step - (90 if cfg.get("sub") else 0)) if cfg.get("sticker") else 760

    def draw(d):
        if cfg.get("badge"):
            pill(d, 260, cfg["badge"].upper(), font("Bold", 34), RED, "white", 28, 58)
        for i, line in enumerate(lines):
            rich_line(d, y0 + i * step, line, f_title)
        if cfg.get("sub"):
            rich_line(d, y0 + len(lines) * step + 20, cfg["sub"], font("SemiBold", 48))
        foot = cfg.get("footer", "Белавтоцентр")
        if foot:
            rich_line(d, 1500, foot, font("SemiBold", 40))
    img.alpha_composite(shadowed(draw))
    img.convert("RGB").save(cfg["out"])

    if cfg.get("sticker"):
        prev = img.copy(); d = ImageDraw.Draw(prev)
        for x in range(ZONE[0], ZONE[2], 40):
            d.line([x, ZONE[1], x + 20, ZONE[1]], fill="white", width=4)
            d.line([x, ZONE[3], x + 20, ZONE[3]], fill="white", width=4)
        for y in range(ZONE[1], ZONE[3], 40):
            d.line([ZONE[0], y, ZONE[0], y + 20], fill="white", width=4)
            d.line([ZONE[2], y, ZONE[2], y + 20], fill="white", width=4)
        label = "СТИКЕР: " + STICKER.get(cfg["sticker"], cfg["sticker"].upper())
        f = font("Bold", 40)
        d.text(((W - d.textlength(label, font=f)) / 2, (ZONE[1] + ZONE[3]) / 2 - 24), label, font=f, fill="white")
        prev.convert("RGB").save(re.sub(r"\.png$", "", cfg["out"]) + "_preview.png")
    print(f"готово: {cfg['out']}")


if __name__ == "__main__":
    main()
