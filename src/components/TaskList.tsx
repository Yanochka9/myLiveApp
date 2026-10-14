import { useState } from 'react'
import { useStore } from '../data/StoreContext'
import type { Area, Task } from '../data/types'
import { useEditors } from './Editors'
import { IconCheck, IconPlus } from './Icons'
import { SkeletonRows } from './Spinner'
import { SparkleBurst, useBurst } from './Sparkles'

export type AreaFilter = Area | 'all'

const AREA_LABEL: Record<Area, string> = { work: 'Работа', life: 'Личное' }

function TaskRow({ task }: { task: Task }) {
  const store = useStore()
  const { editTask } = useEditors()
  const [burst, fire] = useBurst()
  return (
    <div className={task.done ? 'task done' : 'task'}>
      <button
        type="button"
        role="checkbox"
        aria-checked={task.done}
        aria-label={task.done ? 'Отметить как невыполненную' : 'Отметить как выполненную'}
        className={`check ${task.area}`}
        onClick={() => {
          if (!task.done) fire()
          void store.updateTask(task.id, { done: !task.done })
        }}
      >
        <IconCheck />
        {burst > 0 && <SparkleBurst key={burst} />}
      </button>
      <button type="button" className="task-body" onClick={() => editTask({ task })}>
        <div className="task-title">{task.title}</div>
        <div className="task-sub">
          {task.time && <span>{task.time}</span>}
          <span className={`area ${task.area}`}>{AREA_LABEL[task.area]}</span>
          {task.details && <span className="details">{task.details}</span>}
        </div>
      </button>
    </div>
  )
}

/** Быстрое добавление как в «Напоминаниях»: ввёл — Enter — задача в списке. */
function QuickAdd({ date, area }: { date: string; area: Area }) {
  const store = useStore()
  const [title, setTitle] = useState('')
  return (
    <form
      className="quick-add"
      onSubmit={(e) => {
        e.preventDefault()
        const t = title.trim()
        if (!t) return
        void store.addTask({ title: t, date, time: null, area, details: '' })
        setTitle('')
      }}
    >
      <span className="plus" aria-hidden>
        <IconPlus />
      </span>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder={area === 'work' ? 'Рабочая задача' : 'Личное дело'}
        aria-label="Новая задача"
        enterKeyHint="done"
      />
    </form>
  )
}

interface Props {
  date: string
  tasks: Task[]
  loading: boolean
  filter: AreaFilter
}

export function TaskList({ date, tasks, loading, filter }: Props) {
  const visible = filter === 'all' ? tasks : tasks.filter((t) => t.area === filter)
  const quickArea: Area = filter === 'life' ? 'life' : 'work'

  // Скелетон только при самой первой загрузке — дальше данные приходят из кэша без мигания.
  if (loading && tasks.length === 0) return <SkeletonRows />

  return (
    <div className="list fade-in">
      {visible.length === 0 && (
        <div className="empty">
          <strong>Свободный день</strong>
          Добавьте задачу ниже
        </div>
      )}
      {visible.map((t) => (
        <TaskRow key={t.id} task={t} />
      ))}
      <QuickAdd date={date} area={quickArea} />
    </div>
  )
}

export function TaskProgress({ tasks }: { tasks: Task[] }) {
  if (tasks.length === 0) return null
  const done = tasks.filter((t) => t.done).length
  return (
    <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={tasks.length} aria-valuenow={done}>
      <i style={{ transform: `scaleX(${done / tasks.length})` }} />
    </div>
  )
}
