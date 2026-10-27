"""Подготовка исходников для сторис «мини-обзор авто».

  python3 -I prep.py WORKDIR clip1.MOV clip2.MOV ...

Для каждого клипа (в переданном порядке):
  - HDR (HLG/PQ с iPhone) → SDR, цветокоррекция бренда, 1080×1920, 30 fps;
  - обрезка тишины в начале и конце (оставляет 0.1 с запаса), чтобы не было пауз на стыках;
  - расшифровка голоса по словам (faster-whisper).
Результат в WORKDIR: clip_N.mov, last.png, sheet.jpg (кадры для проверки), words.json.
"""
import json, os, re, subprocess, sys

GRADE = ("eq=saturation=0.8:contrast=1.06,"
         "colorbalance=rs=-0.03:bs=0.05:rm=-0.03:bm=0.03:rh=-0.03:bh=0.03")
TONEMAP = ("zscale=tin={tin}:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203,format=gbrpf32le,"
           "zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
FRAME = "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,fps=30"


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def probe(path):
    out = json.loads(run("ffprobe", "-v", "error", "-show_entries",
                         "format=duration:stream=codec_type,color_transfer",
                         "-of", "json", path).stdout)
    v = next(s for s in out["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in out["streams"])
    return float(out["format"]["duration"]), v.get("color_transfer", ""), has_audio


def speech_bounds(path, dur):
    """Начало и конец речи по silencedetect; без речи — весь клип."""
    log = subprocess.run(["ffmpeg", "-i", path, "-af", "silencedetect=n=-35dB:d=0.15", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    a, b = 0.0, dur
    if starts and starts[0] < 0.05 and ends:
        a = max(0.0, ends[0] - 0.1)
    if starts and starts[-1] > a and (len(ends) < len(starts) or ends[-1] >= dur - 0.05):
        b = min(dur, starts[-1] + 0.1)
    return (a, b) if b - a > 0.5 else (0.0, dur)


def main():
    work, clips = sys.argv[1], sys.argv[2:]
    os.makedirs(work, exist_ok=True)
    from faster_whisper import WhisperModel
    import numpy as np
    model = WhisperModel("small", device="cpu", compute_type="int8")

    words, offset, parts = [], 0.0, []
    for i, src in enumerate(clips, 1):
        dur, trc, has_audio = probe(src)
        a, b = speech_bounds(src, dur) if has_audio else (0.0, dur)
        tin = {"arib-std-b67": "arib-std-b67", "smpte2084": "smpte2084"}.get(trc)
        vf = (TONEMAP.format(tin=tin) + "," if tin else "format=yuv420p,") + GRADE + "," + FRAME
        out = f"{work}/clip_{i}.mov"
        # клип без звука получает тишину, чтобы склейка аудио не ломалась
        silent_in = [] if has_audio else ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        silent_map = [] if has_audio else ["-map", "0:v", "-map", "1:a", "-shortest"]
        run("ffmpeg", "-v", "error", "-y", "-i", src, *silent_in, "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
            *silent_map, "-vf", vf, "-c:v", "libx264", "-crf", "14", "-preset", "fast",
            "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", out)
        clip_dur, _, _ = probe(out)
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", out, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        audio16 = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
        segs, _ = model.transcribe(audio16, language="ru", word_timestamps=True)
        for s in segs:
            for w in s.words:
                words.append({"w": w.word.strip(), "s": round(w.start + offset, 2), "e": round(w.end + offset, 2), "clip": i})
        parts.append({"clip": i, "src": src, "trim": [round(a, 2), round(b, 2)], "start": round(offset, 2), "dur": round(clip_dur, 3)})
        offset += clip_dur

    last = f"{work}/clip_{len(clips)}.mov"
    run("ffmpeg", "-v", "error", "-y", "-sseof", "-0.4", "-i", last, "-update", "1", f"{work}/last.png")
    cat = "".join(f"[{k}:v]" for k in range(len(clips)))
    inputs = sum((["-i", f"{work}/clip_{k}.mov"] for k in range(1, len(clips) + 1)), [])
    run("ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex",
        f"{cat}concat=n={len(clips)}:v=1:a=0,fps=1/1.5,scale=200:-2,tile=8x2", "-frames:v", "1", f"{work}/sheet.jpg")

    json.dump({"main_dur": round(offset, 3), "clips": parts, "words": words},
              open(f"{work}/words.json", "w"), ensure_ascii=False, indent=1)
    print(f"main_dur={offset:.2f}s, clips={len(clips)}, words={len(words)}")
    print(" ".join(f"{w['w']}@{w['s']}" for w in words))


if __name__ == "__main__":
    main()
