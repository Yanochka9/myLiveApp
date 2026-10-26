"""Render every visual shot of the EDL to a 1080x1920/30fps intermediate, then concat."""
import subprocess, os, sys, json
from concurrent.futures import ThreadPoolExecutor
from edl import build_shots, FPS, SP

OUT = SP + '/build/shots'
os.makedirs(OUT, exist_ok=True)

GRADE = ("eq=saturation=0.82:contrast=1.06:brightness=-0.01,"
         "curves=all='0/0.03 0.25/0.22 0.75/0.78 1/0.97',colorbalance=bs=0.03:bm=0.01:rh=0.01")
TONEMAP = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=mobius:desat=0:param=0.4,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")

def motion(kind, n):
    """zoompan expression: short punch on entry, then slow push-in or pull-out."""
    punch = f"0.16*pow(max(0\\,1-on/6)\\,2)"
    drift = f"0.07*on/{n}" if kind == 'in' else f"0.07*(1-on/{n})"
    return (f"zoompan=z='1+{punch}+{drift}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s=1080x1920:fps={FPS}")

def cmd(i, s):
    n = round((s['o1'] - s['o0']) * FPS)
    out = f"{OUT}/{i:03d}.mp4"
    k = s['kind']
    pre = ['ffmpeg', '-loglevel', 'error', '-y']
    if k == 'scheme':
        return pre + ['-f', 'lavfi', '-i', f'color=c=0x0d0d10:s=1080x1920:r={FPS}', '-frames:v', str(n),
                      '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '17', out], out
    inp = ['-ss', f"{s['cin']:.3f}", '-i', s['src']]
    if k == 'hook':
        vf = (f"fps={FPS},scale=1440:2560,"
              f"zoompan=z='1+0.16*on/{n}':d=1:x='iw/2-(iw/zoom/2)':y='ih*0.3-(ih/zoom*0.3)':s=1080x1920:fps={FPS},"
              "hue=s=0.12,eq=contrast=0.92:brightness=-0.05,curves=all='0/0.07 1/0.9',"
              "noise=alls=24:allf=t,vignette=PI/3.6")
    elif k == 'aroll':
        crop = "scale=1080:1920" if s['zoom'] == 0 else "crop=1600:2844:280:230,scale=1080:1920"
        vf = f"fps={FPS},{crop}:flags=lanczos,{GRADE},unsharp=5:5:0.35"
    elif k == 'stock':
        cx = "(iw-ih*9/16)*0.68" if '33324' in s['src'] else "(iw-ih*9/16)/2"
        extra = ",eq=brightness=-0.10:contrast=1.18:gamma=0.9" if '33324' in s['src'] else ""
        vf = (f"fps={FPS},crop=ih*9/16:ih:{cx}:0{extra},scale=1296:2304:flags=lanczos,unsharp=5:5:0.6,{GRADE},"
              f"noise=alls=7:allf=t,{motion(s['motion'], n)}")
    elif k == 'hlg':
        vf = f"{TONEMAP},fps={FPS},scale=1296:2304:flags=lanczos,{GRADE},{motion(s['motion'], n)}"
    elif k == 'endplate':
        vf = (f"trim=end_frame=1,loop=loop=-1:size=1,setpts=N/{FPS}/TB,fps={FPS},scale=1080:1920,"
              "gblur=sigma=28,eq=brightness=-0.22:saturation=0.5")
    return pre + inp + ['-vf', vf, '-frames:v', str(n), '-an', '-pix_fmt', 'yuv420p',
                        '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-r', str(FPS), out], out

if __name__ == '__main__':
    shots = build_shots()
    only = set(map(int, sys.argv[1:]))
    jobs = [cmd(i, s) for i, s in enumerate(shots) if not only or i in only]
    def run(j):
        c, out = j
        r = subprocess.run(c, capture_output=True, text=True)
        if r.returncode: print('FAIL', out, r.stderr[-800:])
        else:
            got = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                                  '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', out],
                                 capture_output=True, text=True).stdout.strip()
            print('ok', os.path.basename(out), got)
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(run, jobs))
    with open(f'{OUT}/list.txt', 'w') as f:
        for i in range(len(shots)):
            f.write(f"file '{OUT}/{i:03d}.mp4'\n")
    json.dump(shots, open(SP + '/build/shots.json', 'w'), indent=1)
