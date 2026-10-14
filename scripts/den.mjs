#!/usr/bin/env node
// Управление данными планера из терминала с полным (admin) доступом к проекту Firebase.
//
//   GOOGLE_APPLICATION_CREDENTIALS=/путь/к/ключу.json DEN_USER=почта@пример.ru node scripts/den.mjs <команда>
//
// Ключ сервисного аккаунта НЕ хранится в репозитории (см. .gitignore).
//
//   users                                  — список аккаунтов
//   create-user <почта> <пароль>           — завести аккаунт
//   list                                   — заметки и задачи пользователя DEN_USER
//   note "текст" [--tint pink] [--unpin]   — новая заметка (tint: plain|yellow|green|blue|pink)
//   task "название" --date 2026-10-15 [--time 10:00] [--area work|life] [--details "..."]
//   done <taskId> | undone <taskId>
//   rm-note <id> | rm-task <id>
//   import file.json                       — {"notes":[...],"tasks":[...]} пачкой

import { readFile } from 'node:fs/promises'
import { applicationDefault, initializeApp } from 'firebase-admin/app'
import { getAuth } from 'firebase-admin/auth'
import { getFirestore } from 'firebase-admin/firestore'

initializeApp({ credential: applicationDefault(), projectId: process.env.DEN_PROJECT || 'myliveapp-8d16a' })
const auth = getAuth()
const db = getFirestore()

const [cmd, ...rest] = process.argv.slice(2)
const flag = (name) => {
  const i = rest.indexOf(`--${name}`)
  return i >= 0 ? rest[i + 1] : undefined
}
const has = (name) => rest.includes(`--${name}`)

async function userRef() {
  const email = process.env.DEN_USER
  if (!email) throw new Error('Укажите DEN_USER=почта пользователя')
  const user = await auth.getUserByEmail(email)
  return db.doc(`users/${user.uid}`)
}

const newNote = (n) => {
  const now = Date.now()
  return { text: n.text, tint: n.tint ?? 'plain', pinned: n.pinned ?? true, createdAt: now, updatedAt: now }
}
const newTask = (t) => ({
  title: t.title,
  date: t.date,
  time: t.time ?? null,
  area: t.area ?? 'work',
  done: t.done ?? false,
  details: t.details ?? '',
  createdAt: Date.now(),
})

/** Удаляет один документ; ошибка, если его нет. */
async function removeOne(col, id) {
  const ref = (await userRef()).collection(col).doc(id)
  if (!(await ref.get()).exists) throw new Error(`Нет такого документа: ${col}/${id}`)
  await ref.delete()
  console.log('удалено')
}

switch (cmd) {
  case 'users': {
    for (const u of (await auth.listUsers(1000)).users) console.log(`${u.email}  ${u.uid}  создан ${u.metadata.creationTime}`)
    break
  }
  case 'create-user': {
    const u = await auth.createUser({ email: rest[0], password: rest[1] })
    console.log('создан', u.email, u.uid)
    break
  }
  case 'list': {
    const ref = await userRef()
    const [notes, tasks] = await Promise.all([ref.collection('notes').get(), ref.collection('tasks').get()])
    console.log(`Заметки (${notes.size}):`)
    notes.forEach((d) => {
      const n = d.data()
      console.log(`  ${d.id}  ${n.pinned ? '📌' : '  '} [${n.tint}] ${n.text.replace(/\n/g, ' / ')}`)
    })
    console.log(`Задачи (${tasks.size}):`)
    tasks.docs
      .map((d) => ({ id: d.id, ...d.data() }))
      .sort((a, b) => (a.date + (a.time ?? '99')).localeCompare(b.date + (b.time ?? '99')))
      .forEach((t) =>
        console.log(
          `  ${t.id}  ${t.done ? '✓' : '○'} ${t.date} ${t.time ?? '     '} ${t.area === 'work' ? 'Работа' : 'Личное'}  ${t.title}${t.details ? ' — ' + t.details : ''}`,
        ),
      )
    break
  }
  case 'note': {
    const doc = await (await userRef()).collection('notes').add(newNote({ text: rest[0], tint: flag('tint'), pinned: !has('unpin') }))
    console.log('+', doc.id)
    break
  }
  case 'task': {
    const doc = await (await userRef())
      .collection('tasks')
      .add(newTask({ title: rest[0], date: flag('date'), time: flag('time'), area: flag('area'), details: flag('details') }))
    console.log('+', doc.id)
    break
  }
  case 'done':
  case 'undone':
    await (await userRef()).collection('tasks').doc(rest[0]).update({ done: cmd === 'done' })
    console.log('ok')
    break
  case 'rm-note':
    await removeOne('notes', rest[0])
    break
  case 'rm-task':
    await removeOne('tasks', rest[0])
    break
  case 'import': {
    const data = JSON.parse(await readFile(rest[0], 'utf8'))
    const ref = await userRef()
    const batch = db.batch()
    for (const n of data.notes ?? []) batch.set(ref.collection('notes').doc(), newNote(n))
    for (const t of data.tasks ?? []) batch.set(ref.collection('tasks').doc(), newTask(t))
    await batch.commit()
    console.log(`добавлено: заметок ${data.notes?.length ?? 0}, задач ${data.tasks?.length ?? 0}`)
    break
  }
  default:
    console.error('Команды: users | create-user | list | note | task | done | undone | rm-note | rm-task | import')
    process.exit(1)
}
