# День — планер работы и личной жизни

Веб-приложение под iPhone: ставится на экран «Домой» и открывается как обычное приложение, без адресной строки. Оформлено в светлых розовых тонах, с лёгкими тенями и бликами. Данные хранятся в Firebase Firestore и доступны офлайн.

## Что внутри

- **День.** Лента недели, план на выбранный день с фильтром «Работа / Личное», прогресс и быстрое добавление задачи (ввести текст и нажать Enter).
- **Заметки.** Не привязаны к датам. Закреплённые заметки видны на экране «День» для любой даты.
- **Календарь.** Месяц с цветными точками: работа и личное. Нажмите на день, и под календарём откроется его план.
- **Профиль.** Аккаунт, статус синхронизации, подсказка по установке.

Стек: Vite, React 19, TypeScript, Firebase (Auth и Firestore с офлайн-кэшем), PWA (service worker и manifest).

## Быстрый старт

```bash
npm install
npm run dev
```

Пока Firebase не настроен, приложение работает в **демо-режиме**: данные хранятся в localStorage этого устройства.

## Подключение Firebase

1. Создайте проект в [Firebase Console](https://console.firebase.google.com).
2. **Build → Authentication → Sign-in method**: включите **Email/Password**.
3. **Build → Firestore Database**: создайте базу в production mode.
4. **Firestore → Rules**: вставьте содержимое [`firestore.rules`](firestore.rules). Каждый пользователь видит только свои данные. Можно опубликовать и через CLI: `npx firebase-tools deploy --only firestore:rules`.
5. **Project settings → General → Your apps → Web app**: скопируйте конфиг в `.env.local` по образцу [`.env.example`](.env.example).
6. **Authentication → Settings → Authorized domains**: добавьте домен Vercel, например `my-app.vercel.app`.

Структура данных:

```
users/{uid}/notes/{id}  text, tint, pinned, createdAt, updatedAt
users/{uid}/tasks/{id}  title, date (YYYY-MM-DD), time (HH:mm|null), area (work|life), done, details, createdAt
```

## Деплой на Vercel

1. Импортируйте репозиторий в Vercel. Фреймворк Vite определится сам, настройки лежат в [`vercel.json`](vercel.json).
2. **Settings → Environment Variables**: добавьте все `VITE_FIREBASE_*` из `.env.example`.
3. Задеплойте проект.

## Установка на iPhone

Откройте сайт в Safari, нажмите «Поделиться», затем «На экран „Домой“» и «Добавить».
