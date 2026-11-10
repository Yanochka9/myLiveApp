"""fetch sources, transcribe speech, contact sheets, segmentation masks."""
import os, re, json, glob, subprocess, math
import numpy as np
from common import Project, W, H

VIDEO_EXT = ('.mov', '.mp4', '.m4v')


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                          'format=duration:stream=codec_type,color_transfer', '-of', 'json', path],
                         stdout=subprocess.PIPE, check=True).stdout
    d = json.loads(out)
    st = d.get('streams', [])
    return dict(duration=float(d['format']['duration']),
                audio=any(s['codec_type'] == 'audio' for s in st),
                hdr=any(s.get('color_transfer') in ('arib-std-b67', 'smpte2084') for s in st))


def list_clips(p):
    return sorted(f for f in os.listdir(p.src_dir) if f.lower().endswith(VIDEO_EXT))


# ------------------------------------------------------------------ fetch
def fetch(p):
    src = p.cfg.get('sources', {})
    os.makedirs(p.src_dir, exist_ok=True)
    if src.get('drive_folder'):
        import gdown
        files = gdown.download_folder(url=src['drive_folder'], output=p.src_dir, quiet=False, remaining_ok=True)
        print('downloaded', len(files or []), 'files to', p.src_dir)
    m = p.cfg.get('music', {})
    if m.get('search') and not os.path.exists(p.asset(m.get('file', '-'))):
        out = os.path.join(p.work, 'music.%(ext)s')
        for q in ([m['search']] if isinstance(m['search'], str) else m['search']):
            r = subprocess.run(['yt-dlp', '--no-warnings', '-f', 'bestaudio', '-o', out, f'scsearch1:{q}'])
            hits = glob.glob(os.path.join(p.work, 'music.*'))
            if hits:
                print('music:', hits[0], '-> set "music.file" to this path'); break
        else:
            print('music not found; put an mp3/m4a next to the project and set "music.file"')


# ------------------------------------------------------------------ transcription
def speech_onset(wav_path):
    import wave
    w = wave.open(wav_path)
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    hop = 320
    rms = np.sqrt(np.convolve(a ** 2, np.ones(hop) / hop, 'same')[::hop])
    above = np.where(rms > 10 ** (-35 / 20))[0]
    return (above[0] * hop / 16000.0 if len(above) else 0.0), a


def transcribe(p, clips=None, model_name=None):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name or p.cfg.get('asr_model', 'large-v3'), device='cpu', compute_type='int8')
    lang = p.cfg.get('language', 'ru')
    wd = os.path.join(p.work, 'words'); os.makedirs(wd, exist_ok=True)
    clips = clips or [c for c in list_clips(p) if probe(p.clip(c))['audio'] and probe(p.clip(c))['duration'] >= 3]
    for c in clips:
        out = os.path.join(wd, c + '.json')
        if os.path.exists(out):
            continue
        wav = os.path.join(p.work, 'tmp.wav')
        sh(['ffmpeg', '-v', 'error', '-y', '-i', p.clip(c), '-vn', '-ac', '1', '-ar', '16000', wav])
        onset, audio = speech_onset(wav)
        segs, _ = model.transcribe(audio, language=lang, word_timestamps=True, beam_size=5)
        ws = [[round(w.start, 2), round(w.end, 2), w.word.strip()] for s in segs for w in s.words]
        if ws and ws[0][0] < onset - 0.05:      # whisper often stretches the first word over leading silence
            ws[0][0] = round(onset, 2)
            nxt = ws[1][0] if len(ws) > 1 else ws[0][1]
            if ws[0][1] <= ws[0][0] + 0.1 or ws[0][1] > nxt:
                ws[0][1] = round(min(onset + 0.35, max(nxt, onset + 0.1)), 2)
            if len(ws) > 1: ws[1][0] = max(ws[1][0], ws[0][1])
        json.dump(ws, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    report(p)


def report(p):
    """print every transcribed clip with word timings: this is what the project config is written from"""
    wd = os.path.join(p.work, 'words')
    for f in sorted(glob.glob(os.path.join(wd, '*.json'))):
        ws = json.load(open(f, encoding='utf-8'))
        c = os.path.basename(f)[:-5]
        print(f'\n== {c}  ({probe(p.clip(c))["duration"]:.2f}s)')
        print('   ' + ' '.join(w[2] for w in ws))
        print('   ' + ' '.join(f'{w[2]}[{w[0]:.2f}-{w[1]:.2f}]' for w in ws))


# ------------------------------------------------------------------ contact sheets
def sheets(p):
    from PIL import Image, ImageDraw
    sd = os.path.join(p.work, 'sheets'); os.makedirs(sd, exist_ok=True)
    rows = []
    for c in list_clips(p):
        d = probe(p.clip(c))['duration']
        n = 6
        out = os.path.join(sd, c + '.jpg')
        if not os.path.exists(out):
            sh(['ffmpeg', '-v', 'error', '-y', '-i', p.clip(c), '-vf', f'fps={n}/{d},scale=150:-2,tile={n}x1',
                '-frames:v', '1', out])
        rows.append((c, d, out))
    pages = []
    for i in range(0, len(rows), 6):
        ims = [(c, d, Image.open(o)) for c, d, o in rows[i:i + 6]]
        Wd = max(im.width for _, _, im in ims); Ht = sum(im.height + 24 for _, _, im in ims)
        page = Image.new('RGB', (Wd, Ht), 'white'); dr = ImageDraw.Draw(page); y = 0
        for c, d, im in ims:
            dr.text((4, y + 5), f'{c}  {d:.1f}s', fill='black'); page.paste(im, (0, y + 24)); y += im.height + 24
        pp = os.path.join(sd, f'_page{i // 6 + 1}.jpg'); page.save(pp, quality=82); pages.append(pp)
    print('\n'.join(pages))


# ------------------------------------------------------------------ masks
MASK_FPS = 15


def mask_dir(p, clip):
    return os.path.join(p.work, 'masks', clip)


def ensure_masks(p, ranges, model='isnet-general-use'):
    """ranges: [(clip, src_from, src_to)] -> grayscale masks at 15 fps, file index = round(src_t*15)"""
    todo = []
    for clip, a, b in ranges:
        md = mask_dir(p, clip); os.makedirs(md, exist_ok=True)
        i0, i1 = max(0, int(math.floor(a * MASK_FPS)) - 1), int(math.ceil(b * MASK_FPS)) + 1
        miss = [i for i in range(i0, i1 + 1) if not os.path.exists(os.path.join(md, f'{i:05d}.png'))]
        if miss: todo.append((clip, miss))
    if not todo: return
    from rembg import new_session, remove
    from PIL import Image
    sess = new_session(model)
    tmp = os.path.join(p.work, 'mask_tmp'); os.makedirs(tmp, exist_ok=True)
    for clip, miss in todo:
        a, b = miss[0], miss[-1]
        for f in glob.glob(os.path.join(tmp, '*.png')): os.remove(f)
        sh(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a / MASK_FPS:.4f}', '-i', p.clip(clip), '-t', f'{(b - a + 1) / MASK_FPS:.4f}',
            '-vf', f'fps={MASK_FPS},scale={W}:{H}', os.path.join(tmp, '%05d.png')])
        frames = sorted(glob.glob(os.path.join(tmp, '*.png')))
        for k, f in enumerate(frames):
            idx = a + k
            if idx not in miss: continue
            remove(Image.open(f), session=sess, only_mask=True).save(os.path.join(mask_dir(p, clip), f'{idx:05d}.png'))
        print('masks', clip, len(frames), flush=True)
