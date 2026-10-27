"""DetailLab — монтаж вертикальных роликов по шаблону (ТикТок + сторис).

Шаблон (утверждён на ролике Leopard):
  • цвет — LUT по референсам CapCut (assets/look.cube): темнее, холоднее, глубокие тени;
  • хук (триггерная фраза) → белая вспышка + звук «вжух» → вся машина по порядку;
  • фразы целиком, режем только паузы > 0.5 с; развороты камеры закрываем планами машины;
  • субтитры: Montserrat ExtraBold, строчные, белые, над плашкой;
  • плашки: тёмные с золотой рамкой (Inter Black), под субтитрами, по одной на тему;
  • мягкие вспышки + щелчки на смене плашек; тихая музыка из «музыка и звуки»;
  • после последнего слова ≥1 с, затем заставка DetailLab.

Шаги:
  python3 -I make_video.py prep  <config.json>   скачать, транскрибировать, листы кадров
  python3 -I make_video.py build <config.json>   смонтировать ТикТок + сторис
"""
import json, os, re, subprocess, sys, wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
A = f"{HERE}/assets"
FONTS = f"{A}/fonts"
W, H, FPS = 1080, 1920, 30
GOLD = (242, 193, 78)
GRADE = f"lut3d={A}/look.cube,eq=contrast=1.03:saturation=1.04,unsharp=5:5:0.4"
PLATE_HOLD = 2.5             # сколько висит плашка темы (последняя — до конца)
PLATE_FADE = 0.3


def grade(cfg):
    """LUT с силой lut_mix (1.0 — как Leopard; под другой свет обычно 0.4–0.6)."""
    mix = cfg.get("lut_mix", 1.0)
    if mix >= 1:
        return GRADE
    return (f"split[g0][g1];[g1]lut3d={A}/look.cube[g2];[g0][g2]blend=all_mode=normal:all_opacity={mix},"
            f"eq=contrast=1.05,unsharp=5:5:0.4")
SUB_Y, PLATE_Y = 1205, 1268
GAP, KEEP = 0.50, 0.14       # паузы длиннее GAP сжимаем, у слова оставляем KEEP
ENDCARD = 1.6
FLASH_LEAD = 1.4             # длина нарастания «вжуха» до вспышки
FIX = {"ее": "её", "пленки": "плёнки", "пленка": "плёнка", "пленочку": "плёнку", "идем": "идём",
       "антимоникюрчики": "антиманикюр", "антимуникюрчики": "антиманикюр"}


def run(cmd):
    print("+", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)


def dur(f):
    return float(subprocess.check_output(f"ffprobe -v error -show_entries format=duration -of csv=p=0 '{f}'", shell=True))


def drive_download(file_id, path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        run(f"curl -sSL -o '{path}' 'https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t'")


def load(cfg_path):
    cfg = json.load(open(cfg_path))
    cfg["work"] = cfg.get("work") or f"/tmp/detaillab-video/{cfg['name']}"
    os.makedirs(f"{cfg['work']}/seg", exist_ok=True)
    os.makedirs(cfg.get("out") or f"{cfg['work']}/out", exist_ok=True)
    cfg["out"] = cfg.get("out") or f"{cfg['work']}/out"
    return cfg


# ---------------- prep ----------------
def prep(cfg):
    w = cfg["work"]
    src = f"{w}/source.mov"
    drive_download(cfg["source_drive_id"], src)
    run(f"ffmpeg -v error -y -i '{src}' -map 0:v:0 -map 0:a:0 -vf scale={W}:{H}:flags=lanczos,fps={FPS} "
        f"-c:v libx264 -preset veryfast -crf 14 -pix_fmt yuv420p -c:a pcm_s16le {w}/proxy.mov")
    run(f"ffmpeg -v error -y -i {w}/proxy.mov -vn -ac 1 -ar 16000 {w}/audio.wav")
    from faster_whisper import WhisperModel
    wf = wave.open(f"{w}/audio.wav")
    a = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    segs, _ = WhisperModel("small", device="cpu", compute_type="int8").transcribe(a, language="ru", word_timestamps=True)
    out = []
    for s in segs:
        print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}")
        out.append({"start": s.start, "end": s.end, "text": s.text,
                    "words": [{"w": x.word, "s": x.start, "e": x.end} for x in s.words]})
    json.dump(out, open(f"{w}/words.json", "w"), ensure_ascii=False)
    # листы кадров с таймкодами — искать развороты камеры, пальцы в кадре, хорошие планы
    total = dur(f"{w}/proxy.mov")
    for i, st in enumerate(range(0, int(total) + 1, 16)):
        run(f"ffmpeg -v error -y -ss {st} -t 16 -i {w}/proxy.mov -vf \"fps=2,scale=160:-1,"
            f"drawtext=fontfile={FONTS}/Inter-Bold.otf:text='%{{eif\\:t+{st}\\:d}}.%{{eif\\:mod(t*10\\,10)\\:d}}':fontcolor=yellow:fontsize=28:x=5:y=5,"
            f"tile=8x4\" -frames:v 1 {w}/sheet_{i:02d}.jpg")
    print("WORK", w)


# ---------------- build ----------------
def words_all(cfg):
    return [x for s in json.load(open(f"{cfg['work']}/words.json")) for x in s["words"]]


def split_pauses(a, b, allw):
    ws = [x for x in allw if a <= (x["s"] + x["e"]) / 2 <= b]
    parts, st = [], a
    for w0, w1 in zip(ws, ws[1:]):
        if w1["s"] - w0["e"] > GAP:
            parts.append((st, w0["e"] + KEEP)); st = w1["s"] - KEEP
    parts.append((st, b))
    return parts


def norm(w, fix):
    raw = w.strip().strip(",.!?").lower()
    return fix.get(raw, raw)


def ass_time(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def build_subs(timeline, allw, fix, path):
    items = []
    for si, (a, b, o) in enumerate(timeline):
        for x in allw:
            if a <= (x["s"] + x["e"]) / 2 <= b:
                items.append([o + max(x["s"], a) - a, o + min(x["e"], b) - a, norm(x["w"], fix), si])
    items = [i for i in items if i[2]]
    groups, cur = [], []
    for it in items:  # 1–2 слова, не через склейку
        if cur and (len(cur) == 2 or it[3] != cur[-1][3] or len(" ".join(c[2] for c in cur + [it])) > 14 or it[0] - cur[-1][1] > 0.3):
            groups.append(cur); cur = []
        cur.append(it)
    if cur:
        groups.append(cur)
    end_body = timeline[-1][2] + timeline[-1][1] - timeline[-1][0]
    lines = []
    for gi, g in enumerate(groups):
        st = g[0][0]
        en = groups[gi + 1][0][0] if gi + 1 < len(groups) else g[-1][1] + 0.3
        en = min(en, g[-1][1] + 0.5, end_body)
        txt = " ".join(w[2] for w in g).lower()
        lines.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Sub,,0,0,0,,{{\\q2\\pos(540,{SUB_Y})\\fscx94\\fscy94\\t(0,90,\\fscx100\\fscy100)}}{txt}")
    head = f"""[Script Info]
PlayResX: {W}
PlayResY: {H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Montserrat ExtraBold,74,&H00FFFFFF,&H00FFFFFF,&H50000000,&H64000000,0,0,0,0,100,100,0,0,1,1.2,2.5,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    open(path, "w").write(head + "\n".join(lines) + "\n")


def plate_png(lines, path):
    """Тёмная плашка с золотой рамкой: верхняя строка белая, нижняя золотая."""
    from PIL import ImageFilter
    f1 = ImageFont.truetype(f"{FONTS}/Inter-Black.otf", 58)
    pad_x, pad_y, gap = 54, 34, 14
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    sizes = [tmp.textbbox((0, 0), l, font=f1) for l in lines]
    tw = max(b[2] - b[0] for b in sizes)
    th = sum(b[3] - b[1] for b in sizes) + gap * (len(lines) - 1)
    bw, bh = min(tw + pad_x * 2, W - 120), th + pad_y * 2
    img = Image.new("RGBA", (bw + 24, bh + 24), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((12, 16, bw + 12, bh + 16), 36, fill=(0, 0, 0, 110))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((12, 12, bw + 12, bh + 12), 36, fill=(14, 14, 16, 205), outline=GOLD + (255,), width=3)
    y = 12 + pad_y
    for i, (l, b) in enumerate(zip(lines, sizes)):
        col = GOLD + (255,) if i == len(lines) - 1 else (255, 255, 255, 255)
        d.text((12 + (bw - (b[2] - b[0])) / 2 - b[0], y - b[1]), l, font=f1, fill=col)
        y += (b[3] - b[1]) + gap
    img.save(path)


def build(cfg):
    w, out = cfg["work"], cfg["out"]
    proxy = f"{w}/proxy.mov"
    allw = words_all(cfg)
    fix = {**FIX, **cfg.get("fix_words", {})}
    tag = cfg["name"]

    segs = []
    for a, b, v, z, part, plate in cfg["edl"]:
        for pa, pb in split_pauses(a, b, allw):
            segs.append((pa, pb, None if v is None else v + (pa - a), z, part, plate))
    files, timeline, meta, o = [], [], [], 0.0
    for i, (a, b, v, z, part, plate) in enumerate(segs):
        d = b - a
        f = f"{w}/seg/s{i:03d}.mov"
        vs = a if v is None else v
        run(f"ffmpeg -v error -y -ss {vs:.3f} -t {d:.3f} -i {proxy} -ss {a:.3f} -t {d:.3f} -i {proxy} -map 0:v -map 1:a "
            f"-vf \"crop=iw/{z}:ih/{z},scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS},{grade(cfg)}\" "
            f"-af afade=t=in:d=0.015,afade=t=out:st={max(d - 0.025, 0):.3f}:d=0.025 "
            f"-c:v libx264 -preset fast -crf 15 -pix_fmt yuv420p -c:a pcm_s16le -ar 48000 -ac 2 -shortest {f}")
        dd = dur(f)
        files.append(f); timeline.append((a, a + dd, o)); meta.append((o, o + dd, part, plate)); o += dd
    body = o

    # заставка: размытый кадр + логотип
    run(f"ffmpeg -v error -y -ss {cfg.get('endcard_bg_time', segs[-1][0])} -i {proxy} -frames:v 1 -vf \"{grade(cfg)}\" {w}/last.png")
    run(f"ffmpeg -v error -y -loop 1 -t {ENDCARD} -i {w}/last.png -loop 1 -t {ENDCARD} -i {A}/endcard.png "
        f"-f lavfi -t {ENDCARD} -i anullsrc=r=48000:cl=stereo "
        f"-filter_complex \"[0]scale={W}:{H},boxblur=30:3,eq=brightness=-0.3,fps={FPS}[bg];[1]format=rgba,fade=t=in:st=0:d=0.35:alpha=1[l];[bg][l]overlay=0:0,format=yuv420p[v]\" "
        f"-map [v] -map 2:a -c:v libx264 -preset fast -crf 15 -c:a pcm_s16le {w}/endcard.mov")
    files.append(f"{w}/endcard.mov")
    with open(f"{w}/list.txt", "w") as fh:
        fh.writelines(f"file '{f}'\n" for f in files)
    run(f"ffmpeg -v error -y -f concat -safe 0 -i {w}/list.txt -c copy {w}/joined.mov")
    total = body + ENDCARD
    build_subs(timeline, allw, fix, f"{w}/subs.ass")

    spans, firsts = {}, []
    for st, en, part, plate in meta:
        if plate:
            if plate not in spans:
                firsts.append(st)
            s0, e0 = spans.get(plate, (st, en))
            spans[plate] = (min(s0, st), max(e0, en))
    hook = cfg.get("hook_plate", "hook")
    hook_end = spans[hook][1]

    music = f"{w}/music.wav"
    if not os.path.exists(music):
        drive_download(cfg["music_drive_id"], f"{w}/music_src.mov")
        run(f"ffmpeg -v error -y -i {w}/music_src.mov -vn -ac 2 -ar 48000 {music}")
    inputs = [f"-i {w}/joined.mov", f"-ss {cfg.get('music_start', 8)} -i {music}", f"-i {A}/sfx/flash.mp3"]
    pops = [t for t in firsts if t > hook_end + 0.5] + [body]
    for k in range(len(pops)):
        inputs.append(f"-i {A}/sfx/{'s5' if k == len(pops) - 1 else ('s2' if k % 2 == 0 else 's4')}.mp3")
    chain, last, n = [], "[0:v]", len(inputs)
    last_plate = max(spans, key=lambda g: spans[g][0])
    for grp, lines in cfg["plates"].items():
        if grp not in spans:
            continue
        p = f"{w}/plate_{grp}.png"
        plate_png(lines, p)
        st, en = spans[grp]
        if grp == hook:
            if not cfg.get("hook_plate_show", False):  # хук без плашки
                continue
            en = hook_end - 0.05
        elif grp != last_plate:
            en = min(en, st + cfg.get("plate_hold", PLATE_HOLD))
        inputs.append(f"-loop 1 -t {total:.2f} -i {p}")
        fade = f",fade=t=in:st={st:.2f}:d=0.25:alpha=1"
        if grp != last_plate:
            fade += f",fade=t=out:st={en - PLATE_FADE:.2f}:d={PLATE_FADE}:alpha=1"
        chain.append(f"[{n}:v]format=rgba{fade}[p{n}]")
        chain.append(f"{last}[p{n}]overlay=(W-w)/2:{PLATE_Y}:enable='between(t,{st:.2f},{en:.2f})'[v{n}]")
        last = f"[v{n}]"; n += 1
    for k, (t, peak, din, dout) in enumerate([(hook_end, 1.0, 0.12, 0.30)] + [(t, 0.6, 0.06, 0.22) for t in pops]):
        chain.append(f"color=c=white:s={W}x{H}:d={total:.2f}:r={FPS},format=rgba,"
                     f"fade=t=in:st={max(t - din, 0):.2f}:d={din}:alpha=1,fade=t=out:st={t:.2f}:d={dout}:alpha=1,colorchannelmixer=aa={peak}[fl{k}]")
        chain.append(f"{last}[fl{k}]overlay=0:0:enable='between(t,{max(t - din - 0.01, 0):.2f},{t + dout + 0.02:.2f})'[vf{k}]")
        last = f"[vf{k}]"
    chain.append(f"{last}ass={w}/subs.ass:fontsdir={FONTS}[vout]")
    # голос без шумодава; aresample после loudnorm обязателен (иначе 192 кГц и обрезанный конец)
    chain.append("[0:a]highpass=f=95,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=120:makeup=2,"
                 "loudnorm=I=-13:TP=-1.5:LRA=8,aresample=48000,asplit=2[voice][sc]")
    chain.append(f"[1:a]aresample=48000,atrim=0:{total:.2f},volume={cfg.get('music_vol', 0.22)},"
                 f"afade=t=in:d=1.0,afade=t=out:st={total - 1.5:.2f}:d=1.5[mus]")
    chain.append("[mus][sc]sidechaincompress=threshold=0.05:ratio=2.5:attack=40:release=600[duck]")
    fl = int((hook_end - FLASH_LEAD) * 1000)
    fx = [f"[2:a]aresample=48000,volume=0.45,adelay={fl}|{fl}[fx0]"]
    for k, t in enumerate(pops):
        fx.append(f"[{3 + k}:a]aresample=48000,volume={0.32 if k == len(pops) - 1 else 0.24},adelay={int(t * 1000)}|{int(t * 1000)}[fx{k + 1}]")
    chain += fx
    labels = "".join(f"[fx{k}]" for k in range(len(fx)))
    chain.append(f"[voice][duck]{labels}amix=inputs={2 + len(fx)}:duration=longest:normalize=0,atrim=0:{total:.2f},alimiter=limit=0.95[aout]")
    with open(f"{w}/fc.txt", "w") as fh:
        fh.write(";\n".join(chain))
    final = f"{out}/DetailLab_{tag}_TikTok.mp4"
    enc = "-c:v libx264 -preset slow -crf 20 -maxrate 9M -bufsize 18M -profile:v high -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart"
    run(f"ffmpeg -v error -y {' '.join(inputs)} -filter_complex_script {w}/fc.txt -map [vout] -map [aout] {enc} {final}")

    bounds, prev = [], None
    for st, en, part, plate in meta:
        if part != prev:
            bounds.append(st); prev = part
    bounds.append(total)
    for k in range(len(bounds) - 1):
        run(f"ffmpeg -v error -y -ss {bounds[k]:.3f} -i {final} -t {bounds[k + 1] - bounds[k]:.3f} {enc} {out}/DetailLab_{tag}_Story_{k + 1}.mp4")
    print("TOTAL", round(total, 2), "HOOK_END", round(hook_end, 2), "BOUNDS", [round(b, 2) for b in bounds], "OUT", out)


if __name__ == "__main__":
    cmd, cfg_path = sys.argv[1], sys.argv[2]
    {"prep": prep, "build": build}[cmd](load(cfg_path))
