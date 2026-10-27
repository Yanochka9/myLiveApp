"""Сборка сторис по конфигу.

  python3 -I render.py config.json

Конфиг (пример — в SKILL.md): workdir (результат prep.py), out, badge (или null),
title, price, pill (или null), subs, cta_word, cta_footer, music (или null).
В субтитрах *звёздочки* выделяют жёлтым, \\n — перенос строки.
"""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = "/usr/share/fonts/opentype/inter/"
W, H = 1080, 1920
RED, YELLOW_ASS = (229, 33, 43, 255), "&H004DD3FF&"
CTA_DUR = 2.8


def font(weight, size):
    return ImageFont.truetype(FONTS + f"Inter-{weight}.otf", size)


def shadowed(draw_fn):
    """Рисует слой и подкладывает под него мягкую тень."""
    top = Image.new("RGBA", (W, H)); draw_fn(ImageDraw.Draw(top))
    sh = Image.new("RGBA", (W, H)); sh.putalpha(top.getchannel("A").point(lambda a: int(a * 0.55)))
    base = Image.new("RGBA", (W, H)); base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)), (0, 4))
    base.alpha_composite(top)
    return base


def ctext(d, y, text, f, fill="white", stroke=0):
    d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=(0, 0, 0, 90))


def pill(d, y, text, f, bg, fg, padx, h):
    tw = d.textlength(text, font=f); asc, desc = f.getmetrics(); x0 = (W - tw) / 2 - padx
    d.rounded_rectangle([x0, y, x0 + tw + 2 * padx, y + h], radius=h / 2, fill=bg)
    d.text((x0 + padx, y + (h - asc - desc) / 2 - 1), text, font=f, fill=fg)


def make_header(cfg, path):
    def draw(d):
        if cfg.get("badge"):
            pill(d, 210, cfg["badge"].upper(), font("Bold", 34), RED, "white", 28, 58)
        ctext(d, 288, cfg["title"], font("ExtraBold", 78), stroke=2)
        ctext(d, 382, cfg["price"], font("ExtraBold", 78), stroke=2)
        if cfg.get("pill"):
            pill(d, 486, cfg["pill"], font("Bold", 42), (255, 255, 255, 240), (20, 20, 20, 255), 34, 72)
    shadowed(draw).save(path)


def make_cta(cfg, path):
    def draw(d):
        ctext(d, 700, "Хотите увидеть вживую?", font("SemiBold", 54))
        ctext(d, 790, "Запишитесь", font("ExtraBold", 104), stroke=2)
        ctext(d, 910, "на тест-драйв", font("ExtraBold", 104), stroke=2)
        pill(d, 1080, f"Пишите «{cfg['cta_word']}» в директ", font("Bold", 50), RED, "white", 44, 100)
        if cfg.get("cta_footer"):
            ctext(d, 1215, cfg["cta_footer"], font("SemiBold", 40), fill=(255, 255, 255, 230))
    shadowed(draw).save(path)


def ts(t):
    t = max(t, 0); return f"0:{int(t // 60):02d}:{t % 60:05.2f}"


def make_ass(subs, main_dur, path):
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Inter ExtraBold,62,&H00FFFFFF,&H00FFFFFF,&H64000000,&H82000000,0,0,0,0,100,100,0,0,1,3,3,2,60,60,460,204

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for s in subs:
        text = s["t"].replace("\n", "\\N")
        text = re.sub(r"\*(.+?)\*", lambda m: "{\\c" + YELLOW_ASS + "}" + m[1] + "{\\c&H00FFFFFF&}", text)
        lines.append(f"Dialogue: 0,{ts(s['s'])},{ts(min(s['e'], main_dur))},Sub,,0,0,0,,{{\\fad(120,0)}}{text}")
    open(path, "w").write(head + "\n".join(lines) + "\n")


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def main():
    cfg = json.load(open(sys.argv[1]))
    wd = cfg["workdir"]; meta = json.load(open(f"{wd}/words.json"))
    main_dur = meta["main_dur"]; n = len(meta["clips"]); total = main_dur + CTA_DUR
    make_header(cfg, f"{wd}/header.png"); make_cta(cfg, f"{wd}/cta.png"); make_ass(cfg["subs"], main_dur, f"{wd}/subs.ass")

    # финальный экран: стоп-кадр плавно размывается, сверху появляется призыв
    ff("-loop", "1", "-t", str(CTA_DUR), "-framerate", "30", "-i", f"{wd}/last.png",
       "-loop", "1", "-t", str(CTA_DUR), "-framerate", "30", "-i", f"{wd}/cta.png", "-filter_complex",
       "[0]format=yuv420p,split[s][b];[b]gblur=sigma=22,eq=brightness=-0.2[bb];"
       "[s][bb]xfade=transition=fade:duration=0.5:offset=0,format=rgba[bg];"
       "[1]format=rgba,fade=in:st=0.15:d=0.45:alpha=1[t];[bg][t]overlay=format=auto,format=yuv420p",
       "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-an", f"{wd}/cta.mov")

    inputs = sum((["-i", f"{wd}/clip_{k}.mov"] for k in range(1, n + 1)), [])
    cat = "".join(f"[{k}:v][{k}:a]" for k in range(n))
    i_cta, i_head, i_tap = n, n + 1, n + 2
    extra = ["-i", f"{wd}/cta.mov", "-loop", "1", "-framerate", "30", "-t", f"{main_dur:.3f}", "-i", f"{wd}/header.png",
             "-i", f"{HERE}/../assets/tap.wav"]
    tap_ms = int((main_dur + 0.15) * 1000)
    graph = (
        f"{cat}concat=n={n}:v=1:a=1[mv][ma];"
        f"[mv]trim=duration={main_dur:.3f},setpts=PTS-STARTPTS,unsharp=5:5:0.4[mv2];"
        f"[{i_head}]format=rgba,fade=in:st=0:d=0.3:alpha=1,fade=out:st={main_dur - 0.36:.2f}:d=0.36:alpha=1[hd];"
        f"[mv2][hd]overlay=format=auto,ass={wd}/subs.ass:fontsdir={FONTS},format=yuv420p[mvs];"
        f"[mvs][{i_cta}:v]concat=n=2:v=1:a=0[v];"
        f"[ma]highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=10:release=150,"
        f"loudnorm=I=-15:TP=-2:LRA=11,aresample=48000,apad,atrim=0:{total:.3f},asplit[voice][key];"
        f"[{i_tap}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={tap_ms}|{tap_ms},volume=0.5,"
        f"apad,atrim=0:{total:.3f}[fx];"
    )
    mix_inputs = "[voice][fx]"; count = 2
    if cfg.get("music"):
        extra += ["-i", cfg["music"]]
        off = cfg.get("music_offset", 5)
        graph += (f"[{n + 3}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=start={off}:duration={total:.3f},"
                  f"asetpts=PTS-STARTPTS,volume=0.06,afade=t=in:d=0.6,afade=t=out:st={total - 1.44:.2f}:d=1.44[mus];"
                  f"[mus][key]sidechaincompress=threshold=0.03:ratio=3:attack=30:release=600[musd];")
        mix_inputs += "[musd]"; count = 3
    else:
        graph += "[key]anullsink;"
    graph += f"{mix_inputs}amix=inputs={count}:normalize=0,alimiter=limit=0.89[a]"

    ff(*inputs, *extra, "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
       "-c:v", "libx264", "-profile:v", "high", "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p",
       "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-r", "30",
       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cfg["out"])
    ff("-i", cfg["out"], "-vf", "fps=1/1.5,scale=200:-2,tile=8x2", "-frames:v", "1", f"{wd}/final_sheet.jpg")
    print(f"готово: {cfg['out']} ({total:.1f} с); кадры для проверки: {wd}/final_sheet.jpg")


if __name__ == "__main__":
    main()
