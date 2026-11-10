"""Проверка готового ролика перед отправкой:  python3 -I check.py VIDEO.mp4 [...]

  - вспышки: отрезок в 1–3 кадра между двумя сменами картинки (кадр соседнего дубля на стыке подсъёма);
  - дёрганье: кадр повторился посреди движения (подсъём «как замедленный»);
  - паузы: тишина в речи дольше 0.5 с (обычно — начало дубля до первого слова).
Выход 1, если что-то нашлось. В обзорах с быстрыми проходками камеры «вспышки» бывают ложными — смотри кадры.
"""
import subprocess, sys
import numpy as np


def frames(f):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", f, "-vf", "crop=1080:900:0:500,scale=64:54,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 54, 64).astype(float)


def main():
    from faster_whisper.vad import get_speech_timestamps, VadOptions
    bad_any = False
    for f in sys.argv[1:]:
        v = frames(f)
        d = [abs(v[i] - v[i - 1]).mean() for i in range(1, len(v))]
        cuts = [i + 1 for i, x in enumerate(d) if x > 18]
        flash = [round(cuts[j] / 30, 2) for j in range(1, len(cuts) - 1)
                 if cuts[j + 1] - cuts[j] <= 3 and cuts[j] - cuts[j - 1] > 4
                 and (j + 2 >= len(cuts) or cuts[j + 2] - cuts[j + 1] > 4)]
        judder = [round((i + 1) / 30, 2) for i in range(1, len(d) - 1) if d[i] < 0.1 and d[i - 1] > 0.5 and d[i + 1] > 0.5]
        raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", f, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                             capture_output=True).stdout
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        ts = get_speech_timestamps(a, VadOptions(min_silence_duration_ms=250, speech_pad_ms=0))
        gaps = [(round(x["end"] / 16000, 2), round(y["start"] / 16000, 2)) for x, y in zip(ts, ts[1:])
                if (y["start"] - x["end"]) / 16000 > 0.5]
        ok = not (flash or judder or gaps)
        bad_any |= not ok
        print(f"{f.split('/')[-1]}: {'OK' if ok else 'ЕСТЬ ПРОБЛЕМЫ'}  вспышки={flash} дёрганье={judder[:10]} паузы={gaps}")
    sys.exit(1 if bad_any else 0)


if __name__ == "__main__":
    main()
