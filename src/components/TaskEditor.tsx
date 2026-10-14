import { useState } from 'react'
import { useStore } from '../data/StoreContext'
import type { Area } from '../data/types'
import type { TaskDraft } from './Editors'
import { Sheet } from './Sheet'
import { Segmented } from './Segmented'
import { Switch } from './Switch'
import { IconCalendar, IconClock } from './Icons'

const AREAS: { value: Area; label: string }[] = [
  { value: 'work', label: 'Работа' },
  { value: 'life', label: 'Личное' },
]

export function TaskEditor({ open, draft, onClose }: { open: boolean; draft: TaskDraft; onClose: () => void }) {
  const store = useStore()
  const existing = 'task' in draft ? draft.task : null

  const [title, setTitle] = useState(existing?.title ?? '')
  const [details, setDetails] = useState(existing?.details ?? '')
  const [date, setDate] = useState(existing?.date ?? ('date' in draft ? draft.date : ''))
  const [hasTime, setHasTime] = useState(Boolean(existing?.time))
  const [time, setTime] = useState(existing?.time ?? '09:00')
  const [area, setArea] = useState<Area>(existing?.area ?? ('area' in draft ? draft.area : 'work'))

  const canSave = title.trim().length > 0 && Boolean(date)

  const save = () => {
    if (!canSave) return
    const data = { title: title.trim(), details: details.trim(), date, time: hasTime ? time : null, area }
    if (existing) void store.updateTask(existing.id, data)
    else void store.addTask(data)
    onClose()
  }

  const remove = () => {
    if (existing) void store.deleteTask(existing.id)
    onClose()
  }

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={existing ? 'Задача' : 'Новая задача'}
      left={
        <button type="button" className="text-btn" onClick={onClose}>
          Отмена
        </button>
      }
      right={
        <button type="button" className="text-btn bold" disabled={!canSave} onClick={save}>
          {existing ? 'Готово' : 'Добавить'}
        </button>
      }
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save()
        }}
      >
        <div className="form-group">
          <input
            className="field title"
            placeholder="Название"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus={!existing}
            enterKeyHint="done"
          />
          <textarea className="field" placeholder="Заметки к задаче" value={details} onChange={(e) => setDetails(e.target.value)} rows={3} />
        </div>

        <div className="form-group" style={{ padding: 8 }}>
          <Segmented ariaLabel="Сфера" value={area} options={AREAS} onChange={setArea} />
        </div>

        <div className="form-group">
          <div className="form-row">
            <span className="icon" style={{ background: 'var(--accent)' }}>
              <IconCalendar />
            </span>
            <label htmlFor="task-date">Дата</label>
            <input id="task-date" type="date" value={date} required onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="form-row">
            <span className="icon" style={{ background: 'var(--work)' }}>
              <IconClock />
            </span>
            <span className="label">Время</span>
            {hasTime && <input aria-label="Время" type="time" value={time} onChange={(e) => setTime(e.target.value)} />}
            <Switch checked={hasTime} onChange={setHasTime} label="Указать время" />
          </div>
        </div>

        {existing && (
          <button type="button" className="danger-btn pressable" onClick={remove}>
            Удалить задачу
          </button>
        )}
      </form>
    </Sheet>
  )
}
