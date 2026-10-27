#!/usr/bin/env python3
"""Video kit CLI.

  python3 make.py <project.json> fetch            download sources from Drive + music
  python3 make.py <project.json> analyze          transcribe speech + contact sheets of every clip
  python3 make.py <project.json> preview 1.2 7.5  render single frames (draft 3D) -> work/<name>/preview/sheet.jpg
  python3 make.py <project.json> draft            whole video, fast 3D, lower quality
  python3 make.py <project.json> render           final video -> out/<name>.mp4
  python3 make.py <project.json> subs             print subtitle phrases with timings
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kit'))
from common import Project


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    p = Project(sys.argv[1]); cmd = sys.argv[2]; rest = sys.argv[3:]
    if cmd == 'fetch':
        from analyze import fetch; fetch(p)
    elif cmd == 'analyze':
        from analyze import transcribe, sheets
        transcribe(p, rest or None); sheets(p)
    elif cmd == 'words':
        from analyze import report; report(p)
    elif cmd == 'subs':
        from compose import subtitle_groups
        for g in subtitle_groups(p):
            print(f"{g['s']:6.2f}-{g['e']:6.2f}  " + ' | '.join(w[2] for w in g['words']))
    elif cmd == 'preview':
        from compose import preview
        preview(p, [float(x) for x in rest if not x.startswith('--')], draft='--final' not in rest)
    elif cmd == 'draft':
        from compose import render; render(p, draft=True)
    elif cmd == 'render':
        from compose import render; render(p, draft=False)
    else:
        print(__doc__); sys.exit(1)


if __name__ == '__main__':
    main()
