import type { Note, Task } from './types'

export function sortNotes(notes: Note[]): Note[] {
  return [...notes].sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.updatedAt - a.updatedAt)
}

/** Сначала незавершённые, затем по времени (без времени — в конце), затем по созданию. */
export function sortTasks(tasks: Task[]): Task[] {
  return [...tasks].sort((a, b) => {
    if (a.done !== b.done) return a.done ? 1 : -1
    if (a.time !== b.time) {
      if (a.time === null) return 1
      if (b.time === null) return -1
      return a.time < b.time ? -1 : 1
    }
    return a.createdAt - b.createdAt
  })
}
