import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { Area, Note, Task } from '../data/types'
import { TaskEditor } from './TaskEditor'
import { NoteEditor } from './NoteEditor'

export type TaskDraft = { task: Task } | { date: string; area: Area }

interface Editors {
  editTask: (draft: TaskDraft) => void
  editNote: (note: Note | null) => void
}

const Ctx = createContext<Editors | null>(null)

export const useEditors = () => {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('EditorsProvider is missing')
  return ctx
}

/** Одна шторка задачи и одна шторка заметки на всё приложение. */
export function EditorsProvider({ children }: { children: ReactNode }) {
  const [task, setTask] = useState<{ open: boolean; draft: TaskDraft | null; key: number }>({ open: false, draft: null, key: 0 })
  const [note, setNote] = useState<{ open: boolean; note: Note | null; key: number }>({ open: false, note: null, key: 0 })

  const editTask = useCallback((draft: TaskDraft) => setTask((s) => ({ open: true, draft, key: s.key + 1 })), [])
  const editNote = useCallback((n: Note | null) => setNote((s) => ({ open: true, note: n, key: s.key + 1 })), [])
  const closeTask = useCallback(() => setTask((s) => ({ ...s, open: false })), [])
  const closeNote = useCallback(() => setNote((s) => ({ ...s, open: false })), [])

  const value = useMemo(() => ({ editTask, editNote }), [editTask, editNote])

  return (
    <Ctx.Provider value={value}>
      {children}
      {task.draft && <TaskEditor key={task.key} open={task.open} draft={task.draft} onClose={closeTask} />}
      <NoteEditor key={note.key} open={note.open} note={note.note} onClose={closeNote} />
    </Ctx.Provider>
  )
}
