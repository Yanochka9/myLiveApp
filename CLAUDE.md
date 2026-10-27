# Правила проекта

- Все изменения коммитить и пушить сразу в `main` (`git push origin HEAD:main`).
- Хостинг — Netlify (`netlify.toml`), данные — Firebase Firestore.
- Оформление: светлые розовые тона, Apple-стиль, блёстки и блики; без резких анимаций.
- Монтаж видео: следовать разбору в `montage/STYLE.md`. Ролики АКПП Драйв — строго по `montage/akpp-drive/BRIEF.md` (ассеты в `montage/akpp-drive/assets/`, эталонные скрипты в `montage/akpp-drive/variator/`).
- Сторис Белавтоцентра («мини-обзор авто», «машина дня», исходники машин для Белавто) — строго по шаблону `.claude/skills/belavto-story/SKILL.md` (скрипты `prep.py`/`render.py` там же). Прочитай его перед монтажом. Шаблон лежит в скрытой папке `.claude`, обычный поиск его может не найти.
- Ролики DetailLab (детейлинг, «смонтируй по шаблону DetailLab / как Leopard») — строго по `.claude/skills/detaillab-video/SKILL.md` (код и ассеты в `montage/detaillab/`, эталон `montage/detaillab/examples/leopard.json`). Рилс из нескольких дублей + подсъёмов — по `montage/detaillab/reels/README.md`.
