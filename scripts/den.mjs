#!/usr/bin/env node
// Управление данными планера из терминала через REST API Firebase.
// Входит под аккаунтом пользователя — правила Firestore пускают только в его данные.
//
//   DEN_EMAIL=... DEN_PASSWORD=... node scripts/den.mjs <команда>
//
//   list                                   — все заметки и задачи
//   note "текст" [--tint pink] [--unpin]   — новая заметка (tint: plain|yellow|green|blue|pink)
//   task "название" --date 2026-10-15 [--time 10:00] [--area work|life] [--details "..."]
//   done <taskId> | undone <taskId>
//   rm-note <id> | rm-task <id>
//   import file.json                       — {"notes":[...],"tasks":[...]} пачкой

const API_KEY = process.env.DEN_API_KEY || 'AIzaSyCWdqG0U1qh-iy7TLB7n-RoxemlW3DBJAU'
const PROJECT = process.env.DEN_PROJECT || 'myliveapp-8d16a'
const FS = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents`

const { DEN_EMAIL: email, DEN_PASSWORD: password } = process.env
if (!email || !password) {
  console.error('Нужны DEN_EMAIL и DEN_PASSWORD')
  process.exit(1)
}

async function req(url, opts = {}) {
  const res = await fetch(url, { ...opts, headers: { 'Content-Type': 'application/json', ...opts.headers } })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(`${res.status} ${body.error?.message ?? body.error?.status ?? ''}`)
  return body
}

const auth = await req(`https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${API_KEY}`, {
  method: 'POST',
  body: JSON.stringify({ email, password, returnSecureToken: true }),
})
const H = { Authorization: `Bearer ${auth.idToken}` }
const base = `${FS}/users/${auth.localId}`

// Firestore REST <-> обычные объекты
const enc = (v) =>
  v === null ? { nullValue: null }
  : typeof v === 'boolean' ? { booleanValue: v }
  : typeof v === 'number' ? (Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v })
  : { stringValue: String(v) }
const dec = (f) =>
  'nullValue' in f ? null : 'booleanValue' in f ? f.booleanValue : 'integerValue' in f ? Number(f.integerValue)
  : 'doubleValue' in f ? f.doubleValue : f.stringValue
const toFields = (o) => ({ fields: Object.fromEntries(Object.entries(o).map(([k, v]) => [k, enc(v)])) })
const fromDoc = (d) => ({ id: d.name.split('/').pop(), ...Object.fromEntries(Object.entries(d.fields ?? {}).map(([k, v]) => [k, dec(v)])) })

async function listCol(col) {
  const out = []
  let pageToken = ''
  do {
    const r = await req(`${base}/${col}?pageSize=300${pageToken ? `&pageToken=${pageToken}` : ''}`, { headers: H })
    out.push(...(r.documents ?? []).map(fromDoc))
    pageToken = r.nextPageToken ?? ''
  } while (pageToken)
  return out
}
const create = (col, data) => req(`${base}/${col}`, { method: 'POST', headers: H, body: JSON.stringify(toFields(data)) }).then(fromDoc)
const patch = (col, id, data) =>
  req(`${base}/${col}/${id}?${Object.keys(data).map((k) => `updateMask.fieldPaths=${k}`).join('&')}`, {
    method: 'PATCH', headers: H, body: JSON.stringify(toFields(data)),
  })
// precondition: без неё Firestore «успешно» удаляет и несуществующий документ
const remove = (col, id) => req(`${base}/${col}/${id}?currentDocument.exists=true`, { method: 'DELETE', headers: H })

const newNote = (n) => {
  const now = Date.now()
  return { text: n.text, tint: n.tint ?? 'plain', pinned: n.pinned ?? true, createdAt: now, updatedAt: now }
}
const newTask = (t) => ({
  title: t.title, date: t.date, time: t.time ?? null, area: t.area ?? 'work',
  done: t.done ?? false, details: t.details ?? '', createdAt: Date.now(),
})

const [cmd, ...rest] = process.argv.slice(2)
const flag = (name) => {
  const i = rest.indexOf(`--${name}`)
  return i >= 0 ? rest[i + 1] : undefined
}
const has = (name) => rest.includes(`--${name}`)

switch (cmd) {
  case 'list': {
    const [notes, tasks] = await Promise.all([listCol('notes'), listCol('tasks')])
    console.log(`Заметки (${notes.length}):`)
    for (const n of notes) console.log(`  ${n.id}  ${n.pinned ? '📌' : '  '} [${n.tint}] ${n.text.replace(/\n/g, ' / ')}`)
    console.log(`Задачи (${tasks.length}):`)
    for (const t of tasks.sort((a, b) => (a.date + (a.time ?? '99')).localeCompare(b.date + (b.time ?? '99'))))
      console.log(`  ${t.id}  ${t.done ? '✓' : '○'} ${t.date} ${t.time ?? '     '} ${t.area === 'work' ? 'Работа' : 'Личное'}  ${t.title}${t.details ? ' — ' + t.details : ''}`)
    break
  }
  case 'note':
    console.log('+', (await create('notes', newNote({ text: rest[0], tint: flag('tint'), pinned: !has('unpin') }))).id)
    break
  case 'task':
    console.log('+', (await create('tasks', newTask({ title: rest[0], date: flag('date'), time: flag('time'), area: flag('area'), details: flag('details') }))).id)
    break
  case 'done':
  case 'undone':
    await patch('tasks', rest[0], { done: cmd === 'done' })
    console.log('ok')
    break
  case 'rm-note':
    await remove('notes', rest[0]); console.log('удалено'); break
  case 'rm-task':
    await remove('tasks', rest[0]); console.log('удалено'); break
  case 'import': {
    const { readFile } = await import('node:fs/promises')
    const data = JSON.parse(await readFile(rest[0], 'utf8'))
    for (const n of data.notes ?? []) await create('notes', newNote(n))
    for (const t of data.tasks ?? []) await create('tasks', newTask(t))
    console.log(`добавлено: заметок ${data.notes?.length ?? 0}, задач ${data.tasks?.length ?? 0}`)
    break
  }
  default:
    console.error('Команды: list | note | task | done | undone | rm-note | rm-task | import')
    process.exit(1)
}
