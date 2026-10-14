import type { Note, Store, Task } from './types'
import { sortNotes, sortTasks } from './sort'

// Демо-режим без Firebase: всё хранится в localStorage этого устройства.
const KEY = 'den.demo.v1'

interface Db {
  notes: Note[]
  tasks: Task[]
}

const listeners = new Set<() => void>()

function read(): Db {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) return JSON.parse(raw) as Db
  } catch {
    /* повреждённые данные — начинаем заново */
  }
  return { notes: [], tasks: [] }
}

function write(mutate: (db: Db) => void) {
  const db = read()
  mutate(db)
  try {
    localStorage.setItem(KEY, JSON.stringify(db))
  } catch {
    /* приватный режим / переполнение — данные останутся только в памяти вкладки */
  }
  listeners.forEach((l) => l())
}

function subscribe(fn: () => void) {
  listeners.add(fn)
  fn()
  return () => {
    listeners.delete(fn)
  }
}

const id = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36)

export const localStore: Store = {
  watchNotes(onData) {
    return subscribe(() => onData(sortNotes(read().notes)))
  },
  watchTasks(from, to, onData) {
    return subscribe(() => onData(sortTasks(read().tasks.filter((t) => t.date >= from && t.date <= to))))
  },
  async addNote(input) {
    const now = Date.now()
    write((db) => db.notes.push({ id: id(), ...input, createdAt: now, updatedAt: now }))
  },
  async updateNote(noteId, patch) {
    write((db) => {
      db.notes = db.notes.map((n) => (n.id === noteId ? { ...n, ...patch, updatedAt: Date.now() } : n))
    })
  },
  async deleteNote(noteId) {
    write((db) => {
      db.notes = db.notes.filter((n) => n.id !== noteId)
    })
  },
  async addTask(input) {
    write((db) => db.tasks.push({ id: id(), ...input, done: false, createdAt: Date.now() }))
  },
  async updateTask(taskId, patch) {
    write((db) => {
      db.tasks = db.tasks.map((t) => (t.id === taskId ? { ...t, ...patch } : t))
    })
  },
  async deleteTask(taskId) {
    write((db) => {
      db.tasks = db.tasks.filter((t) => t.id !== taskId)
    })
  },
}
