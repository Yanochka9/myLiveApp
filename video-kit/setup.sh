#!/bin/bash
# Зависимости шаблона монтажа. ffmpeg и шрифт Inter должны быть в системе.
set -e
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo "нужен ffmpeg"; exit 1; }
pip install -q -r requirements.txt
python3 -c "import bpy, cv2, rembg, faster_whisper; print('ok: blender', bpy.app.version_string)"
