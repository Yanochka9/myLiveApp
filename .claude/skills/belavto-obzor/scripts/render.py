"""Сборка сторис по конфигу.

  python3 -I render.py config.json

Конфиг (пример — в SKILL.md): workdir (результат prep.py), out, badge (или null),
title, price, pill (или null), subs, cta_word, cta_footer, music (или null).
В субтитрах *звёздочки* выделяют жёлтым, \\n — перенос строки.
"""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from prep import TONEMAP, LOOKS, FRAME, probe  # noqa: E402
FONTS = "/usr/share/fonts/opentype/inter/"
W, H = 1080, 1920
RED, YELLOW_ASS = (229, 33, 43, 255), "&H004DD3FF&"
YELLOW = (255, 211, 77, 255)
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


def rich_ctext(d, y, line, f):
    """Строка по центру с обводкой; *фрагменты* — жёлтым."""
    parts = re.split(r"(\*.+?\*)", line)
    x = (W - sum(d.textlength(p.strip("*"), font=f) for p in parts)) / 2
    for p in parts:
        t = p.strip("*")
        d.text((x, y), t, font=f, fill=YELLOW if p.startswith("*") else "white", stroke_width=2, stroke_fill=(0, 0, 0, 90))
        x += d.textlength(t, font=f)


def make_header(cfg, path):
    """Обзор авто: плашка + модель + цена + «без взноса».
    Говорящая сторис: крупная плашка-рубрика + заголовок-крючок (headline, \\n — перенос, *жёлтым*)."""
    def draw(d):
        if cfg.get("headline"):
            if cfg.get("badge"):
                pill(d, 200, cfg["badge"].upper(), font("Bold", 42), RED, "white", 34, 72)
            lines, size = cfg["headline"].split("\n"), 86
            while size > 56 and max(d.textlength(l.replace("*", ""), font=font("ExtraBold", size)) for l in lines) > 960:
                size -= 4
            for i, line in enumerate(lines):
                rich_ctext(d, 300 + i * (size + 14), line, font("ExtraBold", size))
            return
        if cfg.get("badge"):
            pill(d, 210, cfg["badge"].upper(), font("Bold", 34), RED, "white", 28, 58)
        if cfg.get("title"):
            ctext(d, 288, cfg["title"], font("ExtraBold", 78), stroke=2)
        if cfg.get("price"):
            ctext(d, 382, cfg["price"], font("ExtraBold", 78), stroke=2)
        if cfg.get("pill"):
            pill(d, 486, cfg["pill"], font("Bold", 42), (255, 255, 255, 240), (20, 20, 20, 255), 34, 72)
    img = shadowed(draw)
    if cfg.get("headline"):  # мягкое затемнение сверху, чтобы заголовок читался на светлом потолке/небе
        shade = Image.new("RGBA", (W, H))
        grad = Image.linear_gradient("L").resize((W, 640)).point(lambda v: int((255 - v) * 0.3))
        a = Image.new("L", (W, H)); a.paste(grad, (0, 0)); shade.putalpha(a)
        shade.alpha_composite(img); img = shade
    img.save(path)


def make_cta(cfg, path):
    """cta_q — строка-вопрос, cta_big — две крупные строки, cta_pill — красная плашка
    (по умолчанию «Пишите «cta_word» в директ»)."""
    q = cfg.get("cta_q", "Хотите увидеть вживую?")
    big = cfg.get("cta_big", ["Запишитесь", "на тест-драйв"])
    action = cfg.get("cta_pill") or f"Пишите «{cfg['cta_word']}» в директ"

    def draw(d):
        ctext(d, 700, q, font("SemiBold", 54))
        f_big = font("ExtraBold", 104 if max(map(len, big)) <= 14 else 88)
        for i, line in enumerate(big):
            ctext(d, 790 + i * 120, line, f_big, stroke=2)
        pill(d, 1080, action, font("Bold", 50), RED, "white", 44, 100)
        if cfg.get("cta_footer"):
            ctext(d, 1215, cfg["cta_footer"], font("SemiBold", 40), fill=(255, 255, 255, 230))
    shadowed(draw).save(path)


def prep_broll(cfg, wd):
    """Подсъёмы: тот же тонмаппинг/грейд/кадр, что в prep.py; звук подсъёма не используется (голос идёт дальше)."""
    # Каждый подсъём режется ровно на (конец − начало) кадров 30 fps. Подсъёмы, идущие подряд (стык ≤ 1 кадра),
    # склеиваются в ОДИН файл и накладываются одним overlay: на стыке двух отдельных overlay проскакивал
    # кадр с ведущей (было не раз: Soul → BMW в «Подарке», ряд кроссоверов → Qashqai в «Зиме»).
    # Стыки дублей ведущей (в кадрах, по реальному числу кадров clip_N): край подсъёма в ≤ 3 кадрах от стыка
    # притягивается к нему — иначе между подсъёмом и следующим дублем мелькал 1 кадр соседнего дубля.
    # concat ставит следующий дубль после самого длинного потока (звук бывает длиннее видео на долю кадра),
    # а недостающий кадр заполняет повтором последнего кадра предыдущего дубля — он и мелькал.
    # Поэтому стык = начало дубля по words.json, округлённое вверх до кадра.
    # Точное время стыка не угадать до кадра, поэтому подсъём у стыка перекрывает его с запасом 1 кадр:
    # начало — на кадр раньше стыка, конец — на кадр позже.
    import math
    clips = json.load(open(f"{wd}/words.json"))["clips"]
    jt = [sum(c["dur"] for c in clips[:i]) * 30 for i in range(1, len(clips))]
    snap_s = lambda f: next((math.floor(j) - 1 for j in jt if abs(f - j) <= 3), f)
    snap_e = lambda f: next((math.ceil(j) + 1 for j in jt if abs(f - j) <= 3), f)
    parts = []
    for k, b in enumerate(cfg.get("broll", []), 1):
        _, trc, _ = probe(b["src"])
        tin = {"arib-std-b67": "arib-std-b67", "smpte2084": "smpte2084"}.get(trc)
        vf = (TONEMAP.format(tin=tin) + "," if tin else "format=yuv420p,") + LOOKS[cfg.get("look", "cold")] + "," + FRAME
        fs, fe = snap_s(round(b["s"] * 30)), snap_e(round(b["e"] * 30))
        if parts and 0 <= fs - parts[-1][2] <= 1:
            fs = parts[-1][2]  # стык вплотную, без дырки в кадр
        dst = f"{wd}/broll_{k}.mov"
        # +0.3 с запаса на входе, затем ровно fe − fs кадров на выходе
        ff("-ss", str(b["ss"]), "-t", f"{(fe - fs) / 30 + 0.3:.3f}", "-i", b["src"], "-an",
           "-vf", vf + f",trim=end_frame={fe - fs},setpts=N/(30*TB)", "-r", "30",
           "-c:v", "libx264", "-crf", "14", "-preset", "fast", dst)
        n = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                                "stream=nb_read_frames", "-of", "csv=p=0", dst], capture_output=True, text=True).stdout.strip())
        if n < fe - fs:
            raise SystemExit(f"подсъём {b['src']}: {n} кадров вместо {fe - fs} — исходник короче окна, сдвинь ss/e")
        parts.append((dst, fs, fe))
    groups = []
    for p in parts:
        if groups and groups[-1][-1][2] == p[1]:
            groups[-1].append(p)
        else:
            groups.append([p])
    out = []
    for g, grp in enumerate(groups, 1):
        if len(grp) == 1:
            path = grp[0][0]
        else:
            path = f"{wd}/broll_grp_{g}.mov"
            ins = sum((["-i", p[0]] for p in grp), [])
            ff(*ins, "-filter_complex", "".join(f"[{i}:v]" for i in range(len(grp))) + f"concat=n={len(grp)}:v=1:a=0,setpts=N/(30*TB)[v]",
               "-map", "[v]", "-r", "30", "-c:v", "libx264", "-crf", "14", "-preset", "fast", path)
        out.append((path, grp[0][1] / 30, grp[-1][2] / 30))
    return out


def ts(t):
    t = max(t, 0); return f"0:{int(t // 60):02d}:{t % 60:05.2f}"


def make_ass(subs, main_dur, path, hl_scale=100):
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
        text = re.sub(r"\*(.+?)\*", lambda m: "{\\c" + YELLOW_ASS + f"\\fscx{hl_scale}\\fscy{hl_scale}}}" + m[1] + "{\\c&H00FFFFFF&\\fscx100\\fscy100}", text)
        lines.append(f"Dialogue: 0,{ts(s['s'])},{ts(min(s['e'], main_dur))},Sub,,0,0,0,,{{\\fad(120,0)}}{text}")
    open(path, "w").write(head + "\n".join(lines) + "\n")


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def main():
    cfg = json.load(open(sys.argv[1]))
    wd = cfg["workdir"]; meta = json.load(open(f"{wd}/words.json"))
    main_dur = meta["main_dur"]; n = len(meta["clips"])
    # хвост после последнего слова не нужен: там ведущая уже опускает/поворачивает камеру
    last_png = f"{wd}/last.png"
    if meta["words"] and meta["words"][-1]["e"] + 0.35 < main_dur - 0.05:
        main_dur = round(meta["words"][-1]["e"] + 0.35, 3)
        lc = meta["clips"][-1]; last_png = f"{wd}/last_cut.png"
        ff("-ss", f"{max(0, main_dur - lc['start'] - 0.1):.3f}", "-i", f"{wd}/clip_{lc['clip']}.mov",
           "-frames:v", "1", last_png)
    total = main_dur + CTA_DUR
    face = cfg.get("face_vf")  # обработка только кадров с ведущей (не подсъёмов), напр. мягкое сглаживание кожи
    post = cfg.get("post_vf")  # общий доводчик картинки поверх всего (тени/чёткость)
    sharpen = cfg.get("sharpen", 0.4)
    # шумодав RNNoise (assets/sh.rnnn), denoise — доля обработанного сигнала (0.6 — мягко).
    # FFT-шумодав (afftdn) делал голос глухим, «как из динамика телефона», — не использовать.
    dn = cfg.get("denoise") or 0
    dn = 0.6 if dn is True else dn
    denoise_f = f"arnndn=m={HERE}/../assets/sh.rnnn:mix={dn}," if dn else ""
    make_header(cfg, f"{wd}/header.png"); make_cta(cfg, f"{wd}/cta.png"); make_ass(cfg["subs"], main_dur, f"{wd}/subs.ass", cfg.get("hl_scale", 100))
    broll = prep_broll(cfg, wd)

    # финальный экран: стоп-кадр плавно размывается, сверху появляется призыв
    ff("-loop", "1", "-t", str(CTA_DUR), "-framerate", "30", "-i", last_png,
       "-loop", "1", "-t", str(CTA_DUR), "-framerate", "30", "-i", f"{wd}/cta.png", "-filter_complex",
       f"[0]{face + ',' if face else ''}{post + ',' if post else ''}format=yuv420p,split[s][b];[b]gblur=sigma=22,eq=brightness=-0.2[bb];"
       "[s][bb]xfade=transition=fade:duration=0.5:offset=0,format=rgba[bg];"
       "[1]format=rgba,fade=in:st=0.15:d=0.45:alpha=1[t];[bg][t]overlay=format=auto,format=yuv420p",
       "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-an", f"{wd}/cta.mov")

    inputs = sum((["-i", f"{wd}/clip_{k}.mov"] for k in range(1, n + 1)), [])
    cat = "".join(f"[{k}:v][{k}:a]" for k in range(n))
    i_cta, i_head, i_tap = n, n + 1, n + 2
    extra_b = []
    extra = ["-i", f"{wd}/cta.mov", "-loop", "1", "-framerate", "30", "-t", f"{main_dur:.3f}", "-i", f"{wd}/header.png",
             "-i", f"{HERE}/../assets/tap.wav"]
    tap_ms = int((main_dur + 0.15) * 1000)
    base = n + 3 + (1 if cfg.get("music") else 0)
    bro = ""
    # кадры подсъёма и окно enable сдвинуты на полкадра раньше сетки 30 fps: если метки попадают ровно на сетку,
    # из-за округления overlay то повторяет, то пропускает кадр (подсъём «дёргается», кажется замедленным),
    # а на стыке двух подсъёмов подряд проскакивает один кадр с ведущей
    hf = 0.5 / 30
    for j, (path, bs, be) in enumerate(broll):
        extra_b.append(path)
        bro += (f"[{base + j}:v]setpts=N/(30*TB)+{bs - hf:.4f}/TB[b{j}];"
                f"[mvb{j}][b{j}]overlay=enable='between(t,{bs - hf:.4f},{be - hf:.4f})':eof_action=repeat[mvb{j + 1}];")
    graph = (
        f"{cat}concat=n={n}:v=1:a=1[mv][ma];"
        f"[mv]trim=duration={main_dur:.3f},setpts=PTS-STARTPTS{',' + face if face else ''}[mvb0];{bro}"
        f"[mvb{len(broll)}]{post + ',' if post else ''}unsharp=5:5:{sharpen}[mv2];"
        f"[{i_head}]format=rgba,fade=in:st=0:d=0.3:alpha=1,fade=out:st={main_dur - 0.36:.2f}:d=0.36:alpha=1[hd];"
        f"[mv2][hd]overlay=format=auto,ass={wd}/subs.ass:fontsdir={FONTS},format=yuv420p[mvs];"
        f"[mvs][{i_cta}:v]concat=n=2:v=1:a=0[v];"
        f"[ma]atrim=0:{main_dur:.3f},highpass=f=80,{denoise_f}acompressor=threshold=-20dB:ratio=3:attack=10:release=150,"
        f"loudnorm=I=-15:TP=-2:LRA=11,aresample=48000,apad,atrim=0:{total:.3f},asplit[voice][key];"
        f"[{i_tap}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={tap_ms}|{tap_ms},volume=0.5,"
        f"apad,atrim=0:{total:.3f}[fx];"
    )
    mix_inputs = "[voice][fx]"; count = 2
    if cfg.get("music"):
        extra += ["-i", cfg["music"]]
        off = cfg.get("music_offset", 5)
        graph += (f"[{n + 3}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=start={off}:duration={total:.3f},"
                  f"asetpts=PTS-STARTPTS,volume={cfg.get('music_vol', 0.06)},afade=t=in:d=0.6,afade=t=out:st={total - 1.44:.2f}:d=1.44[mus];"
                  f"[mus][key]sidechaincompress=threshold=0.03:ratio={cfg.get('duck_ratio', 3)}:attack=30:release=600[musd];")
        mix_inputs += "[musd]"; count = 3
    else:
        graph += "[key]anullsink;"
    graph += f"{mix_inputs}amix=inputs={count}:normalize=0,alimiter=limit=0.89[a]"

    extra += sum((["-i", p] for p in extra_b), [])
    ff(*inputs, *extra, "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
       "-c:v", "libx264", "-profile:v", "high", "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p",
       "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-r", "30",
       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cfg["out"])
    ff("-i", cfg["out"], "-vf", "fps=1/1.5,scale=200:-2,tile=8x2", "-frames:v", "1", f"{wd}/final_sheet.jpg")
    print(f"готово: {cfg['out']} ({total:.1f} с); кадры для проверки: {wd}/final_sheet.jpg")


if __name__ == "__main__":
    main()
