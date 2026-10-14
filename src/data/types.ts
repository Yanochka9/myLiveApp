export type Area = 'work' | 'life'

export type NoteTint = 'plain' | 'yellow' | 'green' | 'blue' | 'pink'

export interface Note {
  id: string
  text: string
  tint: NoteTint
  pinned: boolean
  createdAt: number
  updatedAt: number
}

export interface Task {
  id: string
  title: string
  /** Локальная дата YYYY-MM-DD */
  date: string
  /** HH:mm или null — «в течение дня» */
  time: string | null
  area: Area
  done: boolean
  details: string
  createdAt: number
}

export type NoteInput = Pick<Note, 'text' | 'tint' | 'pinned'>
export type TaskInput = Pick<Task, 'title' | 'date' | 'time' | 'area' | 'details'>

export type Unsubscribe = () => void

export interface Store {
  watchNotes(onData: (notes: Note[]) => void, onError: (e: Error) => void): Unsubscribe
  /** Задачи в диапазоне дат включительно */
  watchTasks(from: string, to: string, onData: (tasks: Task[]) => void, onError: (e: Error) => void): Unsubscribe
  addNote(input: NoteInput): Promise<void>
  updateNote(id: string, patch: Partial<NoteInput>): Promise<void>
  deleteNote(id: string): Promise<void>
  addTask(input: TaskInput): Promise<void>
  updateTask(id: string, patch: Partial<TaskInput & { done: boolean }>): Promise<void>
  deleteTask(id: string): Promise<void>
}

export interface AppUser {
  uid: string
  email: string | null
}
