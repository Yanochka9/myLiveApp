# Шаблон роликов DetailLab

Монтаж вертикальных видео (ТикТок + нарезка на сторис) в стиле, утверждённом на ролике Leopard.

## Как заказать новый ролик
Напишите Claude в новой сессии:

> Смонтируй видео по шаблону DetailLab. Вот ссылка: https://drive.google.com/file/d/…
> Финальная плашка: «Напиши + в Директ» (или цена/срок)

Достаточно ссылки на файл или на папку в Google Drive (можно «последнее видео в папке»).
Файл должен быть открыт по ссылке. Claude сам найдёт хук, разметит склейки, сделает плашки и пришлёт:
`DetailLab_<name>_TikTok.mp4` и `DetailLab_<name>_Story_1…N.mp4`.

## Состав
- `make_video.py` — весь монтаж: `prep` (скачать, распознать речь, листы кадров) и `build` (смонтировать).
- `examples/*.json` — разметка каждого ролика; `leopard.json` — эталон.
- `assets/look.cube` — цветокоррекция; `assets/fonts` — Montserrat ExtraBold, Inter (OFL);
  `assets/sfx` — звуки переходов из вашего видео-набора; `assets/endcard.png` — заставка с логотипом.
- Музыка качается из Google Drive по `music_drive_id` (папка «музыка и звуки»).

## Зависимости
`ffmpeg` (с libass, lut3d), Python 3 с `numpy`, `Pillow`, `faster-whisper` (`pip install faster-whisper`).
